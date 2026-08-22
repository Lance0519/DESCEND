from __future__ import annotations

import json
import math
from pathlib import Path

from flask import current_app

from .feature_builder import (
    TARGETS,
    build_base_features,
    build_family_lineage_data,
    build_key_factors,
    build_recommendations,
    build_risk_breakdown,
    build_target_features,
)
from .modeling import (
    DEFAULT_FEATURE_MEANS,
    DEFAULT_FEATURE_STDS,
    DEFAULT_RANDOM_SEED,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    TARGET_DEFINITION,
    TARGET_SCOPE_NOTE,
    load_pipeline,
    predict_probability,
    predict_probability_tree_ensemble,
    top_features,
    train_model_from_dataset_path,
    utc_now_iso,
)
from .recommendation_llm import maybe_llm_recommendations
from .soft_adjust import apply_soft_adjustment


RISK_LOW_MAX = 0.34
RISK_MODERATE_MAX = 0.67
RISK_THRESHOLD_RATIONALE = (
    "Risk bands use equal-width probability tertiles for communication: "
    "Low 0%-33% (probability < 0.34), Medium 34%-66% (0.34 <= p < 0.67), "
    "High 67%-100% (p >= 0.67). These are thesis operational cutoffs for a "
    "non-diagnostic prototype, not universal clinical thresholds."
)
ONSET_HORIZON_NOTE = (
    "Illustrative years-to-possible-onset range derived from the awareness probability "
    "and current age for educational communication only. It is not a clinical forecast, "
    "diagnosis timeline, or guarantee of if/when Type 2 diabetes will occur."
)
# When calibrated probability sits just below the Low ceiling but structured pedigree
# burden is high, the displayed respondent band is upgraded to Moderate (probability unchanged).
PEDIGREE_BAND_MIN_PROBABILITY = 0.24
PEDIGREE_BAND_MAX_FOR_LOW_UPGRADE = RISK_LOW_MAX
LINEAGE_INDEX_FOR_BAND_UPGRADE = 2.1
WEIGHTED_FAMILY_FOR_BAND_UPGRADE = 2.1
PEDIGREE_BAND_NOTE = (
    "Overall band may read Moderate when probability is borderline-low but lineageRiskIndex, "
    "weightedFamilyScore, and first/second-degree positives indicate strong hereditary burden; "
    "the numeric probability is still the model output."
)
PREDICTION_SCOPE_NOTE = (
    "The model estimates respondent-level T2DM risk from survey features (including sex via "
    "user_is_male). The displayed respondent percentage blends that ML probability with an "
    "explicit structural susceptibility channel (lineage indices, hereditary load, BMI and "
    "metabolic stress) so pedigree-heavy profiles are not capped by conservatively calibrated "
    "tree probabilities alone. Child percentages are heuristic scenario projections "
    "from the blended respondent score: male vs female scenarios use a small communicative "
    "spread, and stronger lineage burden scales child scenarios upward (not separately trained "
    "offspring targets). Do not read them as validated offspring probabilities."
)

# Structural blend: pulls overall susceptibility toward a lineage/metabolic channel when burden
# is high, without discarding the learned model (communicative scale for this prototype).
_STRUCT_LIN_WEIGHT = 0.58
_STRUCT_MET_WEIGHT = 0.42
_STRUCT_P_STRUCT_FLOOR = 0.04
_STRUCT_P_STRUCT_SCALE = 0.90
_STRUCT_P_STRUCT_EXP = 1.05
_BLEND_W_BASE = 0.12
_BLEND_W_COEF = 0.70
_BLEND_W_MAX = 0.82
_LOGIT_EPS = 1e-7


def _logit(p: float) -> float:
    x = min(1.0 - _LOGIT_EPS, max(_LOGIT_EPS, float(p)))
    return math.log(x / (1.0 - x))


def _inv_logit(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _structural_lineage_severity(derived_metrics: dict, base_features: dict) -> float:
    lri = float(derived_metrics.get("lineageRiskIndex") or 0.0)
    wfs = float(derived_metrics.get("weightedFamilyScore") or 0.0)
    hli = float(base_features.get("hereditary_load_index") or 0.0)
    fd = int(derived_metrics.get("firstDegreeYesCount") or 0)
    return min(
        1.0,
        0.32 * min(lri / 3.15, 1.0)
        + 0.26 * min(wfs / 2.7, 1.0)
        + 0.24 * min(hli / 3.4, 1.0)
        + 0.18 * min(fd / 2.0, 1.0),
    )


def _structural_metabolic_severity(derived_metrics: dict, base_features: dict) -> float:
    bmi = float(derived_metrics.get("bmi") or base_features.get("bmi") or 24.0)
    hyp = float(base_features.get("hypertension_status") or 0.0)
    mri = float(base_features.get("metabolic_risk_index") or 0.0)
    bmi_excess = max(0.0, (bmi - 24.9) / 15.0)
    return min(
        1.0,
        0.45 * min(mri / 105.0, 1.0)
        + 0.40 * min(bmi_excess, 1.0)
        + 0.15 * min(hyp, 1.0),
    )


def respondent_probability_structural_blend(
    model_probability: float,
    base_features: dict,
    derived_metrics: dict,
) -> float:
    """Combine calibrated ML probability with explicit structural susceptibility (logit blend).

    When lineage and metabolic burden are low, the output stays close to ``model_probability``.
    When burden is high, the blend allows materially higher respondent percentages so bands and
    gauges align better with multi-factor hereditary risk communication.
    """
    p = max(0.0, min(1.0, float(model_probability)))
    lin = _structural_lineage_severity(derived_metrics, base_features)
    met = _structural_metabolic_severity(derived_metrics, base_features)
    combined = min(
        1.0,
        _STRUCT_LIN_WEIGHT * lin + _STRUCT_MET_WEIGHT * met,
    )
    p_struct = _STRUCT_P_STRUCT_FLOOR + _STRUCT_P_STRUCT_SCALE * (combined**_STRUCT_P_STRUCT_EXP)
    p_struct = max(0.0, min(1.0, p_struct))

    w = min(_BLEND_W_MAX, _BLEND_W_BASE + _BLEND_W_COEF * (combined**0.95))
    blended = _inv_logit((1.0 - w) * _logit(p) + w * _logit(p_struct))
    return round(max(0.0, min(1.0, blended)), 4)
DEFAULT_PREVALENCE = 0.075

# Heuristic only — ExtraTrees model does not include scenario sex; training is respondent-level.
SCENARIO_GRANDCHILD_FACTOR = 0.92
SCENARIO_MALE_RELATIVE_RISK = 1.048
LINEAGE_SCENARIO_MULT_MIN = 1.0
LINEAGE_SCENARIO_MULT_MAX = 1.48


def _lineage_scenario_multiplier(derived_metrics: dict) -> float:
    """Larger when lineageRiskIndex / weighted tree / degree positives are higher (capped)."""
    lri = float(derived_metrics.get("lineageRiskIndex") or 0.0)
    wfs = float(derived_metrics.get("weightedFamilyScore") or 0.0)
    fd = int(derived_metrics.get("firstDegreeYesCount") or 0)
    sd = int(derived_metrics.get("secondDegreeYesCount") or 0)
    severity = min(
        1.0,
        0.42 * min(lri / 3.15, 1.0)
        + 0.28 * min(wfs / 2.8, 1.0)
        + 0.20 * (fd / 2.0)
        + 0.10 * (sd / 4.0),
    )
    return round(
        LINEAGE_SCENARIO_MULT_MIN
        + (LINEAGE_SCENARIO_MULT_MAX - LINEAGE_SCENARIO_MULT_MIN) * severity,
        4,
    )


def _project_target_probability(
    base_probability: float,
    target,
    lineage_scenario_multiplier: float = 1.0,
) -> float:
    """Heuristic projection for UI scenarios only — not learned from descendant labels.

    Training uses respondent outcome only. Generational distance applies a fixed attenuation;
    male vs female scenario rows use a small symmetric spread around the respondent probability.
    ``lineage_scenario_multiplier`` (>=1) increases all descendant scenarios when family burden is high.
    """
    base_probability = max(0.0, min(1.0, float(base_probability)))
    gen = int(getattr(target, "generation_depth", 1) or 1)
    is_male = int(getattr(target, "target_is_male", 0) or 0)

    gen_factor = SCENARIO_GRANDCHILD_FACTOR if gen > 1 else 1.0
    sex_factor = SCENARIO_MALE_RELATIVE_RISK if is_male == 1 else 1.0 / SCENARIO_MALE_RELATIVE_RISK
    lm = max(1.0, min(float(lineage_scenario_multiplier), LINEAGE_SCENARIO_MULT_MAX + 0.25))

    adjusted = base_probability * gen_factor * sex_factor * lm
    return round(max(0.0, min(1.0, adjusted)), 4)


def respondent_probability_from_scenario_lookup(
    lookup: dict[str, float],
    lineage_scenario_multiplier: float | None = None,
) -> float:
    """Recover respondent-level probability from stored scenario projections (inverse of projection).

    When child scenarios were scaled by ``lineage_scenario_multiplier``, pass the same value so
    history averages match the stored respondent score.
    """
    lm = max(1.0, float(lineage_scenario_multiplier or 1.0))
    male_c = lookup.get("male_child")
    female_c = lookup.get("female_child")
    if male_c is not None and female_c is not None:
        r1 = float(male_c) / SCENARIO_MALE_RELATIVE_RISK
        r2 = float(female_c) * SCENARIO_MALE_RELATIVE_RISK
        core = max(0.0, min(1.0, (r1 + r2) / 2.0))
        return max(0.0, min(1.0, core / lm))
    values = [float(v) for v in lookup.values() if v is not None]
    if not values:
        return 0.0
    return sum(values) / len(values)


def _default_model_config() -> dict:
    coefficients = {
        "age": 0.52,
        "user_is_male": 0.02,
        "bmi": 0.44,
        "hypertension_status": 0.18,
        "physical_activity_score": -0.18,
        "parent_has_t2dm": 0.76,
        "siblings_diabetes_count": 0.18,
        "aunts_uncles_score": 0.1,
    }
    return {
        "modelType": "extra_trees_classifier",
        "intercept": round(math.log(DEFAULT_PREVALENCE / (1.0 - DEFAULT_PREVALENCE)), 6),
        "coefficients": coefficients,
        "preprocessing": {
            "means": DEFAULT_FEATURE_MEANS,
            "stds": DEFAULT_FEATURE_STDS,
        },
        "metadata": {
            "source": "prototype-fallback-baseline",
            "modelType": "extra_trees_classifier",
            "trainedAt": utc_now_iso(),
            "datasetRows": 0,
            "trainRows": 0,
            "evaluationRows": 0,
            "assumedPrevalence": DEFAULT_PREVALENCE,
            "evaluationMethod": None,
            "splitStrategy": None,
            "evaluationStatus": "unvalidated-prototype",
            "requiredColumns": FEATURE_COLUMNS,
            "targetColumn": TARGET_COLUMN,
            "metrics": None,
            "topFeatures": top_features(coefficients),
            "riskThresholds": {
                "lowMax": RISK_LOW_MAX,
                "moderateMax": RISK_MODERATE_MAX,
            },
            "riskThresholdRationale": RISK_THRESHOLD_RATIONALE,
            "targetDefinition": TARGET_DEFINITION,
            "targetScopeNote": TARGET_SCOPE_NOTE,
        },
    }


def _train_and_save_model(model_path: Path) -> dict:
    artifact = _default_model_config()
    model_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
    return artifact


_cached_pipeline = None
_cached_pipeline_path = None


def _load_or_create_model() -> dict:
    model_path = Path(current_app.config["MODEL_PATH"])
    model_path.parent.mkdir(parents=True, exist_ok=True)

    if model_path.exists():
        return json.loads(model_path.read_text(encoding="utf-8"))

    return _train_and_save_model(model_path)


def _get_pipeline():
    """Load the sklearn pipeline, caching it in memory for the process lifetime."""
    global _cached_pipeline, _cached_pipeline_path
    model_path = Path(current_app.config["MODEL_PATH"])
    pipeline_path = model_path.with_suffix(".joblib")
    pipeline_path_str = str(pipeline_path)

    if _cached_pipeline is not None and _cached_pipeline_path == pipeline_path_str:
        return _cached_pipeline

    pipeline = load_pipeline(model_path)
    if pipeline is not None:
        _cached_pipeline = pipeline
        _cached_pipeline_path = pipeline_path_str
    return pipeline


def _risk_band(probability: float) -> str:
    if probability >= RISK_MODERATE_MAX:
        return "High"
    if probability >= RISK_LOW_MAX:
        return "Moderate"
    return "Low"


def build_onset_horizon(probability: float, age: float | int | None) -> dict:
    """
    Map awareness probability to an illustrative years-until-possible-onset window.

    Higher probability → shorter horizon. Uses current age for possible ages and
    calendar year bounds. Communicative thesis prototype only — not clinical timing.
    """
    p = max(0.0, min(1.0, float(probability)))
    mid = 2.0 + 36.0 * ((1.0 - p) ** 1.25)
    mid = max(2.0, min(40.0, mid))
    spread = max(2.0, min(8.0, mid * 0.28))
    years_min = max(1, int(round(mid - spread)))
    years_max = min(45, int(round(mid + spread)))
    if years_max < years_min:
        years_max = years_min

    current_age = None
    try:
        if age is not None:
            current_age = int(float(age))
    except (TypeError, ValueError):
        current_age = None
    if current_age is not None:
        current_age = max(1, min(120, current_age))

    year_now = datetime.utcnow().year
    payload: dict = {
        "illustrative": True,
        "yearsMin": years_min,
        "yearsMax": years_max,
        "midYears": int(round(mid)),
        "probability": round(p, 4),
        "riskBand": _risk_band(p),
        "calendarYearMin": year_now + years_min,
        "calendarYearMax": year_now + years_max,
        "note": ONSET_HORIZON_NOTE,
    }
    if current_age is not None:
        payload["fromAge"] = current_age
        payload["possibleAgeMin"] = current_age + years_min
        payload["possibleAgeMax"] = current_age + years_max
    return payload


def _prediction_percentage(predictions: list, key: str) -> float | None:
    for p in predictions:
        if p.get("key") == key:
            v = p.get("percentage")
            return float(v) if v is not None else None
    return None


def build_scenario_probabilities(predictions: list) -> dict:
    """Scenario % tree for UI: same underlying values as ``predictions`` / ``chartData``."""

    fc = _prediction_percentage(predictions, "female_child")
    mc = _prediction_percentage(predictions, "male_child")
    return {
        "childRisk": {"female": fc, "male": mc},
    }


def build_future_generations() -> dict:
    """Pedigree Gen 4 topology only; percentages come from ``scenarioProbabilities``."""

    children = [
        {
            "key": "child_female",
            "label": "Daughter",
            "gender": "female",
            "generation": 4,
            "isProjected": True,
        },
        {
            "key": "child_male",
            "label": "Son",
            "gender": "male",
            "generation": 4,
            "isProjected": True,
        },
    ]
    return {"children": children}


def risk_band_for_probability(probability: float) -> str:
    return _risk_band(probability)


def respondent_risk_band_for_display(
    probability: float,
    derived_metrics: dict | None,
) -> tuple[str, bool]:
    """Return (display_band, upgraded) for the respondent row only.

    Upgrades Low→Moderate when *p* is in a borderline window below ``RISK_LOW_MAX`` but
    lineage-derived metrics show strong multi-generational burden (communicative alignment
    with the pedigree panel; does not change stored probability).
    """
    p = max(0.0, min(1.0, float(probability)))
    base = _risk_band(p)
    if derived_metrics is None or base != "Low":
        return base, False
    if not (PEDIGREE_BAND_MIN_PROBABILITY <= p < PEDIGREE_BAND_MAX_FOR_LOW_UPGRADE):
        return base, False
    lri = float(derived_metrics.get("lineageRiskIndex") or 0.0)
    wfs = float(derived_metrics.get("weightedFamilyScore") or 0.0)
    fd = int(derived_metrics.get("firstDegreeYesCount") or 0)
    sd = int(derived_metrics.get("secondDegreeYesCount") or 0)
    if (
        lri >= LINEAGE_INDEX_FOR_BAND_UPGRADE
        and wfs >= WEIGHTED_FAMILY_FOR_BAND_UPGRADE
        and (fd >= 1 or sd >= 3)
    ):
        return "Moderate", True
    return base, False


def train_model_from_dataset(dataset_path: Path, model_path: Path) -> dict:
    global _cached_pipeline, _cached_pipeline_path
    _cached_pipeline = None
    _cached_pipeline_path = None
    return train_model_from_dataset_path(dataset_path, model_path, seed=DEFAULT_RANDOM_SEED)


def get_model_evaluation() -> dict:
    artifact = _load_or_create_model()
    metadata = artifact.get("metadata", {})

    metrics = metadata.get("cvMetrics") or metadata.get("metrics")
    metrics_std = metadata.get("cvMetricsStd") or metadata.get("metricsStd")
    train_rows = metadata.get("cvTrainRows") or metadata.get("trainRows", 0)
    eval_rows = metadata.get("cvTestRows") or metadata.get("evaluationRows")
    top_feats = metadata.get("topFeaturesRanked") or metadata.get("topFeatures")
    if top_feats and isinstance(top_feats, list) and top_feats and isinstance(top_feats[0], (list, tuple)):
        top_feats = [{"feature": f, "coefficient": round(c, 4)} for f, c in top_feats]
    if not top_feats:
        top_feats = top_features(artifact.get("coefficients", {}))

    return {
        "source": metadata.get("source", "prototype-fallback-baseline"),
        "trainedAt": metadata.get("trainedAt", utc_now_iso()),
        "datasetRows": metadata.get("datasetRows", 0),
        "trainRows": train_rows,
        "evaluationRows": eval_rows,
        "modelAlgorithm": metadata.get("modelAlgorithm", artifact.get("modelAlgorithm")),
        "algorithmComparison": metadata.get("algorithmComparison"),
        "modelType": metadata.get("modelType", artifact.get("modelType", "extra_trees_classifier")),
        "evaluationMethod": metadata.get("evaluationMethod"),
        "splitStrategy": metadata.get("splitStrategy"),
        "evaluationStatus": metadata.get("evaluationStatus", "unvalidated-prototype"),
        "metrics": metrics,
        "metricsStd": metrics_std,
        "cvFoldDetails": metadata.get("cvFoldDetails"),
        "datasetWarnings": metadata.get("datasetWarnings", []),
        "requiredColumns": metadata.get("requiredColumns", FEATURE_COLUMNS),
        "targetColumn": metadata.get("targetColumn", TARGET_COLUMN),
        "topFeatures": top_feats,
        "riskThresholds": {"lowMax": RISK_LOW_MAX, "moderateMax": RISK_MODERATE_MAX},
        "riskThresholdRationale": RISK_THRESHOLD_RATIONALE,
        "targetDefinition": metadata.get("targetDefinition", TARGET_DEFINITION),
        "targetScopeNote": metadata.get("targetScopeNote", TARGET_SCOPE_NOTE),
        "predictionScopeNote": PREDICTION_SCOPE_NOTE,
        "probabilityCalibration": metadata.get("probabilityCalibration"),
        "metricsAnalysis": metadata.get("metricsAnalysis"),
        "cvMetricConfidenceIntervals95": metadata.get("cvMetricConfidenceIntervals95"),
        "performanceGoalsAssessment": metadata.get("performanceGoalsAssessment"),
        "holdoutWilsonCi95": (
            (metadata.get("holdoutMetrics") or {}).get("testBinomialWilsonCi95")
            if metadata.get("holdoutMetrics")
            else None
        ),
    }


def predict_assessment(payload: dict) -> dict:
    artifact = _load_or_create_model()
    pipeline = _get_pipeline()

    base_features, derived_metrics = build_base_features(payload)
    personal = payload.get("personalInfo", {})
    family_history = payload.get("familyHistory", {})

    predictions = []
    probability_map = {}

    if pipeline is not None:
        model_probability = predict_probability_tree_ensemble(base_features, pipeline)
    else:
        model_probability = predict_probability(base_features, artifact)

    model_probability = max(0.0, min(1.0, float(model_probability)))
    respondent_probability = respondent_probability_structural_blend(
        model_probability, base_features, derived_metrics
    )
    respondent_probability, soft_adjustment = apply_soft_adjustment(
        respondent_probability, payload
    )
    lineage_scenario_mult = _lineage_scenario_multiplier(derived_metrics)

    for target in TARGETS:
        probability = _project_target_probability(
            respondent_probability, target, lineage_scenario_mult
        )
        prediction = {
            "key": target.key,
            "label": target.label,
            "probability": probability,
            "percentage": round(probability * 100, 1),
            "riskBand": _risk_band(probability),
        }
        predictions.append(prediction)
        probability_map[target.key] = prediction["percentage"]

    rp = round(respondent_probability, 4)
    mp = round(model_probability, 4)
    overall_band, band_pedigree_adjusted = respondent_risk_band_for_display(
        respondent_probability, derived_metrics
    )

    key_factors = build_key_factors(derived_metrics, personal)
    baseline_recommendations = build_recommendations(derived_metrics, personal, family_history)
    recommendations, recommendations_provenance = maybe_llm_recommendations(
        baseline_recommendations,
        derived_metrics=derived_metrics,
        key_factors=key_factors,
        summary={
            "overallRiskBand": overall_band,
            "averagePercentage": round(respondent_probability * 100, 1),
        },
        personal=personal,
        family_history=family_history,
    )

    return {
        "predictions": predictions,
        "predictionScopeNote": PREDICTION_SCOPE_NOTE,
        "scenarioLineageMultiplier": lineage_scenario_mult,
        "summary": {
            "overallRiskBand": overall_band,
            "pedigreeAdjustedRiskBand": band_pedigree_adjusted,
            "modelAverageProbability": mp,
            "modelAveragePercentage": round(model_probability * 100, 1),
            "averageProbability": rp,
            "averagePercentage": round(respondent_probability * 100, 1),
            "riskThresholds": {
                "lowMax": RISK_LOW_MAX,
                "moderateMax": RISK_MODERATE_MAX,
            },
            "thresholdRationale": RISK_THRESHOLD_RATIONALE,
            **(
                {"pedigreeBandNote": PEDIGREE_BAND_NOTE}
                if band_pedigree_adjusted
                else {}
            ),
        },
        "softAdjustment": soft_adjustment,
        "features": {"bmi": derived_metrics.get("bmi")},
        "derivedMetrics": derived_metrics,
        "keyFactors": key_factors,
        "recommendations": recommendations,
        "recommendationsProvenance": recommendations_provenance,
        "riskBreakdown": build_risk_breakdown(base_features, derived_metrics),
        "familyLineage": build_family_lineage_data(family_history, personal),
        "chartData": probability_map,
        "scenarioProbabilities": build_scenario_probabilities(predictions),
        "futureGenerations": build_future_generations(),
        "onsetHorizon": build_onset_horizon(respondent_probability, personal.get("age")),
        "modelEvaluation": get_model_evaluation(),
    }
