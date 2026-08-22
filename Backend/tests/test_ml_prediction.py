"""Tests for the ML prediction pipeline: feature building, risk banding, prediction, and training."""

import csv
import json
import math
import tempfile
from pathlib import Path

import pytest

from descend.ml.feature_builder import (
    build_base_features,
    build_family_lineage_data,
    build_key_factors,
    build_recommendations,
    build_risk_breakdown,
    compute_bmi,
    derive_family_metrics,
    normalize_family_status,
)
from descend.ml.modeling import (
    EXTRA_TREES_CONFIG,
    FEATURE_COLUMNS,
    GROUP_COLUMN,
    GROUP_COLUMN_CANDIDATES,
    TARGET_COLUMN,
    _build_training_pipeline,
    _build_xyg,
    build_trained_artifact,
    calculate_metrics,
    compute_crossvalidation_metrics,
    compute_holdout_metrics,
    predict_probability,
    predict_probability_tree_ensemble,
    read_dataset_rows,
    roc_auc,
    sigmoid,
    stratified_group_holdout_split,
    train_model_from_dataset_path,
)
from descend.ml.predictor import (
    RISK_LOW_MAX,
    RISK_MODERATE_MAX,
    _risk_band,
    get_model_evaluation,
    predict_assessment,
    respondent_probability_from_scenario_lookup,
    respondent_probability_structural_blend,
    respondent_risk_band_for_display,
)


_SYNTH_BASE_FEATURES = {
    "age": 40.0,
    "bmi": 26.0,
    "user_is_male": 0.0,
    "physical_activity_score": 1.0,
    "hypertension_status": 0.0,
    "parent_has_t2dm": 0.0,
    "siblings_diabetes_count": 0.0,
    "aunts_uncles_score": 0.0,
    "weightedFamilyScore": 0.0,
    "lineageRiskIndex": 0.0,
    "metabolic_risk_index": 43.0,
    "hereditary_load_index": 0.2,
    "activity_metabolic_index": 1.0,
    "propagationProbability": 0.12,
}


def _write_synthetic_training_csv(
    path: Path,
    outcomes: list[int],
    *,
    family_id: list[int] | None = None,
    source_patient_id: list[int] | None = None,
    source_record_id: list[int] | None = None,
) -> None:
    n = len(outcomes)
    if n < 10:
        raise ValueError("synthetic dataset must have at least 10 rows")
    optional_cols: list[str] = []
    if family_id is not None:
        assert len(family_id) == n
        optional_cols.append("family_id")
    if source_patient_id is not None:
        assert len(source_patient_id) == n
        optional_cols.append("source_patient_id")
    if source_record_id is not None:
        assert len(source_record_id) == n
        optional_cols.append("source_record_id")
    headers = list(FEATURE_COLUMNS) + [TARGET_COLUMN] + optional_cols
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for i in range(n):
            row = {
                **{k: _SYNTH_BASE_FEATURES[k] for k in FEATURE_COLUMNS},
                TARGET_COLUMN: int(outcomes[i]),
            }
            if family_id is not None:
                row["family_id"] = int(family_id[i])
            if source_patient_id is not None:
                row["source_patient_id"] = int(source_patient_id[i])
            if source_record_id is not None:
                row["source_record_id"] = int(source_record_id[i])
            writer.writerow(row)


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def dataset_path():
    backend = Path(__file__).resolve().parent.parent
    path = backend / "ml" / "datasets" / "processed" / "training_dataset.csv"
    if not path.exists():
        pytest.skip("training_dataset.csv not found")
    return path


@pytest.fixture(scope="session")
def dataset_rows(dataset_path):
    rows, group_col = read_dataset_rows(dataset_path)
    return rows


# ── BMI ───────────────────────────────────────────────────────────────────

class TestNormalizeFamilyStatus:
    def test_positive_negative_aliases(self):
        assert normalize_family_status("Positive") == "yes"
        assert normalize_family_status("negative") == "no"
        assert normalize_family_status("YES") == "yes"
        assert normalize_family_status(1) == "yes"
        assert normalize_family_status(0) == "no"
        assert normalize_family_status("unsure") == "unknown"


class TestBmiCalculation:
    def test_normal_bmi(self):
        bmi = compute_bmi(170, 70)
        assert 23.0 < bmi < 25.0

    def test_obese_bmi(self):
        bmi = compute_bmi(160, 100)
        assert bmi > 30

    def test_underweight_bmi(self):
        bmi = compute_bmi(180, 50)
        assert bmi < 18.5

    def test_zero_height_safeguard(self):
        bmi = compute_bmi(0, 70)
        assert bmi > 0


# ── Risk banding ──────────────────────────────────────────────────────────

class TestRiskBanding:
    def test_respondent_band_upgrades_borderline_low_with_strong_pedigree(self):
        derived = {
            "lineageRiskIndex": 2.88,
            "weightedFamilyScore": 3.5,
            "firstDegreeYesCount": 2,
            "secondDegreeYesCount": 3,
        }
        band, adjusted = respondent_risk_band_for_display(0.329, derived)
        assert adjusted is True
        assert band == "Moderate"

    def test_respondent_band_stays_low_when_probability_too_small(self):
        derived = {
            "lineageRiskIndex": 2.88,
            "weightedFamilyScore": 3.5,
            "firstDegreeYesCount": 2,
            "secondDegreeYesCount": 3,
        }
        band, adjusted = respondent_risk_band_for_display(0.18, derived)
        assert adjusted is False
        assert band == "Low"

    def test_low_risk(self):
        assert _risk_band(0.10) == "Low"
        assert _risk_band(0.33) == "Low"

    def test_moderate_risk(self):
        assert _risk_band(0.34) == "Moderate"
        assert _risk_band(0.50) == "Moderate"
        assert _risk_band(0.66) == "Moderate"

    def test_high_risk(self):
        assert _risk_band(0.67) == "High"
        assert _risk_band(0.99) == "High"

    def test_boundary_low_moderate(self):
        assert _risk_band(RISK_LOW_MAX - 0.01) == "Low"
        assert _risk_band(RISK_LOW_MAX) == "Moderate"

    def test_boundary_moderate_high(self):
        assert _risk_band(RISK_MODERATE_MAX - 0.01) == "Moderate"
        assert _risk_band(RISK_MODERATE_MAX) == "High"


class TestStructuralBlend:
    def test_heavy_lineage_raises_blended_probability(self):
        base = {
            "hereditary_load_index": 3.8,
            "metabolic_risk_index": 95.0,
            "hypertension_status": 1.0,
            "bmi": 31.0,
        }
        derived = {
            "bmi": 31.0,
            "lineageRiskIndex": 3.4,
            "weightedFamilyScore": 2.9,
            "firstDegreeYesCount": 2,
        }
        blended = respondent_probability_structural_blend(0.30, base, derived)
        assert blended > 0.30
        assert blended <= 1.0

    def test_minimal_burden_stays_near_model(self):
        base = {
            "hereditary_load_index": 0.2,
            "metabolic_risk_index": 22.0,
            "hypertension_status": 0.0,
            "bmi": 22.0,
        }
        derived = {
            "bmi": 22.0,
            "lineageRiskIndex": 0.0,
            "weightedFamilyScore": 0.0,
            "firstDegreeYesCount": 0,
        }
        blended = respondent_probability_structural_blend(0.12, base, derived)
        assert 0.08 <= blended <= 0.18


# ── Family metrics ────────────────────────────────────────────────────────

class TestFamilyMetrics:
    def test_all_negative_family(self):
        history = {m: "no" for m in [
            "maternalGrandmother", "maternalGrandfather",
            "paternalGrandmother", "paternalGrandfather",
            "mother", "father",
        ]}
        metrics = derive_family_metrics(history)
        assert metrics["weightedFamilyScore"] == 0.0
        assert metrics["firstDegreeYesCount"] == 0
        assert metrics["secondDegreeYesCount"] == 0

    def test_both_parents_positive(self):
        history = {
            "maternalGrandmother": "no", "maternalGrandfather": "no",
            "paternalGrandmother": "no", "paternalGrandfather": "no",
            "mother": "yes", "father": "yes",
        }
        metrics = derive_family_metrics(history)
        assert metrics["firstDegreeYesCount"] == 2
        assert metrics["weightedFamilyScore"] > 0

    def test_all_unknown_family(self):
        history = {m: "unknown" for m in [
            "maternalGrandmother", "maternalGrandfather",
            "paternalGrandmother", "paternalGrandfather",
            "mother", "father",
        ]}
        metrics = derive_family_metrics(history)
        assert metrics["unknownRelativesCount"] == 6
        assert 0 < metrics["weightedFamilyScore"]

    def test_maternal_paternal_split(self):
        history = {
            "maternalGrandmother": "yes", "maternalGrandfather": "yes",
            "paternalGrandmother": "no", "paternalGrandfather": "no",
            "mother": "yes", "father": "no",
        }
        metrics = derive_family_metrics(history)
        assert metrics["maternalScore"] > metrics["paternalScore"]

    def test_lineage_risk_index_increases_with_second_degree_and_extended(self):
        history = {
            "maternalGrandmother": "yes",
            "maternalGrandfather": "yes",
            "paternalGrandmother": "no",
            "paternalGrandfather": "no",
            "mother": "no",
            "father": "no",
        }
        low = derive_family_metrics(history, extended_diabetes_count=0)
        high = derive_family_metrics(history, extended_diabetes_count=4)
        assert high["lineageRiskIndex"] >= low["lineageRiskIndex"]
        assert high["secondDegreeYesCount"] == 2

    def test_grandparents_only_still_yields_lineage_signal(self):
        history = {
            "maternalGrandmother": "yes",
            "maternalGrandfather": "yes",
            "paternalGrandmother": "yes",
            "paternalGrandfather": "yes",
            "mother": "no",
            "father": "no",
        }
        metrics = derive_family_metrics(history, extended_diabetes_count=0)
        assert metrics["lineageRiskIndex"] > 1.0
        assert metrics["weightedFamilyScore"] >= 2.0


# ── Feature building ──────────────────────────────────────────────────────

class TestBuildBaseFeatures:
    def test_returns_expected_keys(self, app, sample_assessment_payload):
        with app.app_context():
            features, derived = build_base_features(sample_assessment_payload)
            for col in FEATURE_COLUMNS:
                assert col in features, f"Missing feature: {col}"
            assert "bmi" in derived
            assert "weightedFamilyScore" in derived

    def test_male_flag(self, app):
        with app.app_context():
            payload = {
                "personalInfo": {"age": 30, "sex": "male", "heightCm": 170, "weightKg": 70},
                "familyHistory": {},
            }
            features, _ = build_base_features(payload)
            assert features["user_is_male"] == 1.0

    def test_female_flag(self, app):
        with app.app_context():
            payload = {
                "personalInfo": {"age": 30, "sex": "female", "heightCm": 160, "weightKg": 55},
                "familyHistory": {},
            }
            features, _ = build_base_features(payload)
            assert features["user_is_male"] == 0.0

    def test_hereditary_load_nonzero_without_diabetic_parent(self, app):
        """Extended family + grandparent T2DM should lift hereditary_load_index even if parents are 'no'."""
        with app.app_context():
            payload = {
                "personalInfo": {
                    "age": 40,
                    "sex": "female",
                    "heightCm": 165,
                    "weightKg": 65,
                    "diagnosedHypertension": "no",
                    "fatherHypertension": "no",
                    "motherHypertension": "no",
                },
                "familyHistory": {
                    "maternalGrandmother": "yes",
                    "maternalGrandfather": "yes",
                    "paternalGrandmother": "no",
                    "paternalGrandfather": "no",
                    "mother": "no",
                    "father": "no",
                    "motherGdmDuringIndexPregnancy": "no",
                    "siblingsCount": 3,
                    "siblingsDiabetesCount": 1,
                    "paternalAuntsUnclesCount": 4,
                    "paternalAuntsUnclesDiabetesCount": 0,
                    "maternalAuntsUnclesCount": 3,
                    "maternalAuntsUnclesDiabetesCount": 1,
                    "physicalActivityScore": 2,
                    "dietQualityScore": 2,
                },
            }
            features, _ = build_base_features(payload)
            assert features["parent_has_t2dm"] == 0.0
            assert features["hereditary_load_index"] > 0.05
            assert features["lineageRiskIndex"] >= 0.9


# ── Sigmoid and metrics ──────────────────────────────────────────────────

class TestSigmoidAndMetrics:
    def test_sigmoid_midpoint(self):
        assert sigmoid(0) == pytest.approx(0.5, abs=1e-6)

    def test_sigmoid_large_positive(self):
        assert sigmoid(100) == 1.0

    def test_sigmoid_large_negative(self):
        assert sigmoid(-100) == 0.0

    def test_roc_auc_perfect(self):
        labels = [0, 0, 1, 1]
        scores = [0.1, 0.2, 0.8, 0.9]
        assert roc_auc(labels, scores) == 1.0

    def test_roc_auc_random(self):
        labels = [0, 1, 0, 1]
        scores = [0.5, 0.5, 0.5, 0.5]
        assert roc_auc(labels, scores) == 0.5

    def test_calculate_metrics_perfect(self):
        labels = [0, 0, 1, 1]
        scores = [0.1, 0.2, 0.8, 0.9]
        m = calculate_metrics(labels, scores, threshold=0.5)
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1Score"] == 1.0

    def test_calculate_metrics_all_wrong(self):
        labels = [0, 0, 1, 1]
        scores = [0.9, 0.8, 0.1, 0.2]
        m = calculate_metrics(labels, scores, threshold=0.5)
        assert m["accuracy"] == 0.0
        assert m["recall"] == 0.0

    def test_calculate_metrics_returns_required_keys(self):
        labels = [0, 1, 0, 1]
        scores = [0.3, 0.7, 0.4, 0.6]
        m = calculate_metrics(labels, scores, threshold=0.5)
        for key in [
            "accuracy",
            "precision",
            "recall",
            "f1Score",
            "specificity",
            "rocAuc",
            "prAuc",
            "brierScore",
            "truePositives",
            "trueNegatives",
            "falsePositives",
            "falseNegatives",
        ]:
            assert key in m


class TestBuildFamilyLineageData:
    @staticmethod
    def _minimal_family_history():
        return {
            "maternalGrandmother": "no",
            "maternalGrandfather": "no",
            "paternalGrandmother": "no",
            "paternalGrandfather": "no",
            "mother": "no",
            "father": "no",
        }

    def _user_node(self, personal: dict):
        data = build_family_lineage_data(self._minimal_family_history(), personal)
        return next(n for n in data["nodes"] if n.get("isRespondent"))

    def test_respondent_yes_no_unsure_maps_to_lineage_status(self):
        assert self._user_node({"diagnosedT2dm": "yes"})["status"] == "yes"
        assert self._user_node({"diagnosedT2dm": "no"})["status"] == "no"
        assert self._user_node({"diagnosedT2dm": "unsure"})["status"] == "unknown"

    def test_respondent_status_accepts_snake_case_when_camel_missing(self):
        assert self._user_node({"diagnosed_t2dm": "yes"})["status"] == "yes"

    def test_respondent_sex_sets_gender_on_user_node(self):
        assert self._user_node({"diagnosedT2dm": "no", "sex": "male"}).get("gender") == "male"
        assert self._user_node({"diagnosedT2dm": "no", "sex": "female"}).get("gender") == "female"
        assert "gender" not in self._user_node({"diagnosedT2dm": "no"})


# ── Predict assessment (integration) ─────────────────────────────────────

class TestPredictAssessment:
    def test_returns_expected_structure(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            assert "predictionScopeNote" in result
            assert "respondent" in result["predictionScopeNote"].lower()
            assert "summary" in result
            assert "modelAverageProbability" in result["summary"]
            assert "modelAveragePercentage" in result["summary"]
            assert "predictions" in result
            assert "derivedMetrics" in result
            assert "keyFactors" in result
            assert "recommendations" in result
            assert "recommendationsProvenance" in result
            assert result["recommendationsProvenance"].get("source") in ("rules", "llm")
            assert "riskBreakdown" in result
            assert "familyLineage" in result
            assert "chartData" in result
            assert "scenarioProbabilities" in result
            sp = result["scenarioProbabilities"]
            assert "childRisk" in sp and sp["childRisk"]["female"] is not None
            assert "grandchildRisk" not in sp
            assert "futureGenerations" in result
            fg = result["futureGenerations"]
            assert "children" in fg and len(fg["children"]) == 2
            assert "grandchildren" not in fg
            assert fg["children"][0]["key"] == "child_female"
            assert "modelEvaluation" in result
            assert "scenarioLineageMultiplier" in result
            assert result["scenarioLineageMultiplier"] >= 1.0

    def test_two_prediction_targets(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            assert len(result["predictions"]) == 2
            keys = {p["key"] for p in result["predictions"]}
            assert keys == {"male_child", "female_child"}

    def test_probabilities_in_valid_range(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            for pred in result["predictions"]:
                assert 0.0 <= pred["probability"] <= 1.0
                assert pred["riskBand"] in ("Low", "Moderate", "High")

    def test_child_sex_spread(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            preds = {p["key"]: p["probability"] for p in result["predictions"]}
            assert preds["male_child"] != preds["female_child"]

    def test_male_female_child_scenarios_differ(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            preds = {p["key"]: p["probability"] for p in result["predictions"]}
            assert preds["male_child"] > preds["female_child"]

    def test_respondent_probability_matches_summary(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            preds = {p["key"]: p["probability"] for p in result["predictions"]}
            inferred = respondent_probability_from_scenario_lookup(
                preds,
                result.get("scenarioLineageMultiplier"),
            )
            assert abs(inferred - result["summary"]["averageProbability"]) < 1e-4

    def test_summary_risk_band_valid(self, app, sample_assessment_payload):
        with app.app_context():
            result = predict_assessment(sample_assessment_payload)
            assert result["summary"]["overallRiskBand"] in ("Low", "Moderate", "High")
            assert "pedigreeAdjustedRiskBand" in result["summary"]
            assert 0.0 <= result["summary"]["averageProbability"] <= 1.0

    def test_heavier_lineage_raises_scenario_multiplier_and_child_projection(self, app):
        personal = {
            "age": 40,
            "isFilipino": "yes",
            "sex": "male",
            "heightCm": 175,
            "weightKg": 82,
            "diagnosedT2dm": "no",
            "diagnosedT2dmConfirmationMethod": "not_applicable",
            "diagnosedHypertension": "no",
            "fatherHypertension": "no",
            "motherHypertension": "no",
        }
        light = {
            "personalInfo": personal,
            "familyHistory": {
                "maternalGrandmother": "no",
                "maternalGrandfather": "no",
                "paternalGrandmother": "no",
                "paternalGrandfather": "no",
                "mother": "no",
                "father": "no",
                "motherGdmDuringIndexPregnancy": "no",
                "siblingsCount": 0,
                "siblingsDiabetesCount": 0,
                "paternalAuntsUnclesCount": 0,
                "paternalAuntsUnclesDiabetesCount": 0,
                "maternalAuntsUnclesCount": 0,
                "maternalAuntsUnclesDiabetesCount": 0,
                "physicalActivityScore": 3,
                "dietQualityScore": 2,
            },
        }
        heavy = {
            "personalInfo": personal,
            "familyHistory": {
                "maternalGrandmother": "yes",
                "maternalGrandfather": "yes",
                "paternalGrandmother": "yes",
                "paternalGrandfather": "yes",
                "mother": "yes",
                "father": "yes",
                "motherGdmDuringIndexPregnancy": "no",
                "siblingsCount": 4,
                "siblingsDiabetesCount": 2,
                "paternalAuntsUnclesCount": 4,
                "paternalAuntsUnclesDiabetesCount": 2,
                "maternalAuntsUnclesCount": 4,
                "maternalAuntsUnclesDiabetesCount": 2,
                "physicalActivityScore": 3,
                "dietQualityScore": 2,
            },
        }
        with app.app_context():
            r_light = predict_assessment(light)
            r_heavy = predict_assessment(heavy)
        assert r_heavy["scenarioLineageMultiplier"] >= r_light["scenarioLineageMultiplier"]
        heavy_male_child = next(p["probability"] for p in r_heavy["predictions"] if p["key"] == "male_child")
        light_male_child = next(p["probability"] for p in r_light["predictions"] if p["key"] == "male_child")
        assert heavy_male_child >= light_male_child - 1e-6


# ── Model evaluation endpoint mapping ────────────────────────────────────

class TestGetModelEvaluation:
    def test_returns_expected_keys(self, app):
        with app.app_context():
            evaluation = get_model_evaluation()
            assert "source" in evaluation
            assert "trainedAt" in evaluation
            assert "datasetRows" in evaluation
            assert "requiredColumns" in evaluation
            assert "targetColumn" in evaluation
            assert "riskThresholds" in evaluation
            assert evaluation["riskThresholds"]["lowMax"] == RISK_LOW_MAX
            assert evaluation["riskThresholds"]["moderateMax"] == RISK_MODERATE_MAX

    def test_trained_model_returns_metrics(self, app, dataset_path):
        """After training, get_model_evaluation must return non-null metrics."""
        with app.app_context():
            from flask import current_app
            model_path = Path(current_app.config["MODEL_PATH"])

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_model = Path(tmpdir) / "test_model.json"
                current_app.config["MODEL_PATH"] = str(tmp_model)
                try:
                    from descend.ml.predictor import train_model_from_dataset
                    train_model_from_dataset(dataset_path, tmp_model)

                    evaluation = get_model_evaluation()
                    assert evaluation["metrics"] is not None, "metrics should not be None after training"
                    assert "accuracy" in evaluation["metrics"]
                    assert "recall" in evaluation["metrics"]
                    assert "rocAuc" in evaluation["metrics"]
                    assert evaluation["metricsStd"] is not None
                    assert evaluation["datasetRows"] > 0
                    assert evaluation["evaluationStatus"] == "evaluated_with_cv_and_holdout"
                finally:
                    current_app.config["MODEL_PATH"] = str(model_path)


# ── Key factors & recommendations ─────────────────────────────────────────

class TestBuildKeyFactors:
    def test_returns_list(self, app):
        with app.app_context():
            factors = build_key_factors(
                {"bmi": 31, "firstDegreeYesCount": 1, "secondDegreeYesCount": 0},
                {"sex": "male"},
            )
            assert isinstance(factors, list)
            assert len(factors) <= 4

    def test_high_bmi_factor(self, app):
        with app.app_context():
            factors = build_key_factors(
                {"bmi": 32, "firstDegreeYesCount": 0, "secondDegreeYesCount": 0},
                {"sex": "female"},
            )
            assert any("BMI" in f for f in factors)


class TestBuildRecommendations:
    def test_returns_list(self, app):
        with app.app_context():
            recs = build_recommendations(
                {"bmi": 22, "firstDegreeYesCount": 0, "secondDegreeYesCount": 0},
                {},
                {},
            )
            assert isinstance(recs, list)
            assert len(recs) >= 1

    def test_high_bmi_recommendation(self, app):
        with app.app_context():
            recs = build_recommendations(
                {"bmi": 30, "firstDegreeYesCount": 0, "secondDegreeYesCount": 0},
                {},
                {},
            )
            assert any("Weight" in r["title"] or "weight" in r["title"] for r in recs)


class TestRecommendationLlmFallback:
    def test_skips_llm_without_api_key(self, app, monkeypatch):
        from descend.ml.recommendation_llm import maybe_llm_recommendations

        monkeypatch.delenv("T2DM_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("T2DM_GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("T2DM_LLM_PROVIDER", raising=False)

        with app.app_context():
            baseline = [
                {
                    "title": "Maintain healthy routines",
                    "description": "Continue balanced nutrition.",
                    "priority": "low",
                }
            ]
            out, prov = maybe_llm_recommendations(
                baseline,
                derived_metrics={"bmi": 22.0},
                key_factors=[],
                summary={"overallRiskBand": "Low", "averagePercentage": 30.0},
                personal={"age": 40, "sex": "female"},
                family_history={},
            )
            assert out == baseline
            assert prov["source"] == "rules"


class TestBuildRiskBreakdown:
    def test_returns_five_categories(self, app, sample_assessment_payload):
        with app.app_context():
            features, derived = build_base_features(sample_assessment_payload)
            breakdown = build_risk_breakdown(features, derived)
            assert len(breakdown) == 5
            keys = {item["key"] for item in breakdown}
            assert "family_history" in keys
            assert "bmi_status" in keys


# ── Dataset loading ───────────────────────────────────────────────────────

class TestDatasetLoading:
    def test_read_dataset_rows(self, dataset_path):
        rows, group_col = read_dataset_rows(dataset_path)
        assert len(rows) >= 10
        assert group_col == "source_patient_id"
        for row in rows:
            for col in FEATURE_COLUMNS:
                assert col in row, f"Missing column {col} in dataset row"
            assert TARGET_COLUMN in row
            assert row[TARGET_COLUMN] in (0, 1)

    def test_dataset_has_both_classes(self, dataset_rows):
        labels = {row[TARGET_COLUMN] for row in dataset_rows}
        assert labels == {0, 1}, "Dataset must contain both positive and negative outcomes"

    def test_dataset_class_balance(self, dataset_rows):
        pos = sum(1 for r in dataset_rows if r[TARGET_COLUMN] == 1)
        neg = len(dataset_rows) - pos
        ratio = min(pos, neg) / max(pos, neg)
        assert ratio >= 0.3, f"Severe class imbalance: ratio={ratio:.2f}"


class TestGroupingColumnResolution:
    """Training CSV grouping: source_patient_id is preferred when present (see GROUP_COLUMN_CANDIDATES)."""

    def test_candidates_prioritize_source_patient_id(self):
        assert GROUP_COLUMN_CANDIDATES[0] == "source_patient_id"

    def test_prefers_source_patient_id_when_all_group_columns_present(self, tmp_path: Path):
        n = 12
        path = tmp_path / "train.csv"
        _write_synthetic_training_csv(
            path,
            [i % 2 for i in range(n)],
            family_id=[1] * 6 + [2] * 6,
            source_patient_id=[10] * 6 + [20] * 6,
            source_record_id=[100] * 6 + [200] * 6,
        )
        rows, group_col = read_dataset_rows(path)
        assert group_col == "source_patient_id"
        for i, row in enumerate(rows):
            expected_spid = 10 if i < 6 else 20
            assert row[GROUP_COLUMN] == expected_spid
            assert row[GROUP_COLUMN] != ([1] * 6 + [2] * 6)[i]

    def test_uses_family_id_when_source_patient_id_absent(self, tmp_path: Path):
        n = 12
        path = tmp_path / "train.csv"
        fids = [3] * 4 + [4] * 4 + [5] * 4
        _write_synthetic_training_csv(
            path,
            [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
            family_id=fids,
            source_record_id=list(range(900, 900 + n)),
        )
        rows, group_col = read_dataset_rows(path)
        assert group_col == "family_id"
        for row, fid in zip(rows, fids):
            assert row[GROUP_COLUMN] == fid

    def test_uses_source_record_id_when_only_that_present(self, tmp_path: Path):
        n = 12
        path = tmp_path / "train.csv"
        srids = list(range(50, 50 + n))
        _write_synthetic_training_csv(
            path,
            [i % 2 for i in range(n)],
            source_record_id=srids,
        )
        rows, group_col = read_dataset_rows(path)
        assert group_col == "source_record_id"
        for row, srid in zip(rows, srids):
            assert row[GROUP_COLUMN] == srid

    def test_row_index_fallback_when_no_group_column(self, tmp_path: Path):
        n = 12
        path = tmp_path / "train.csv"
        _write_synthetic_training_csv(path, [i % 2 for i in range(n)])
        rows, group_col = read_dataset_rows(path)
        assert group_col == "row_index_fallback"
        for i, row in enumerate(rows):
            assert row[GROUP_COLUMN] == i + 1

    def test_stratified_holdout_no_shared_source_patient_id(self, tmp_path: Path):
        """Families keyed by source_patient_id must not appear in both train and test."""
        n = 16
        path = tmp_path / "train.csv"
        # Four single-label groups; holdout can assign some groups to test only.
        spid = (
            [101] * 4
            + [102] * 4
            + [201] * 4
            + [202] * 4
        )
        outcomes = [0] * 8 + [1] * 8
        _write_synthetic_training_csv(
            path,
            outcomes,
            source_patient_id=spid,
        )
        rows, group_col = read_dataset_rows(path)
        assert group_col == "source_patient_id"
        train_rows, test_rows = stratified_group_holdout_split(rows, test_size=0.25, seed=42)
        train_g = {int(r[GROUP_COLUMN]) for r in train_rows}
        test_g = {int(r[GROUP_COLUMN]) for r in test_rows}
        assert train_g.isdisjoint(test_g)
        assert len(train_rows) + len(test_rows) == n

    def test_crossvalidation_runs_with_shared_source_patient_id_groups(self, tmp_path: Path):
        """StratifiedGroupKFold path: same source_patient_id must not leak across train/eval in a fold."""
        n_groups = 10
        path = tmp_path / "train.csv"
        spid: list[int] = []
        outcomes: list[int] = []
        for g in range(n_groups):
            pid = 600 + g
            label = g % 2
            spid.extend([pid, pid])
            outcomes.extend([label, label])
        _write_synthetic_training_csv(path, outcomes, source_patient_id=spid)
        rows, group_col = read_dataset_rows(path)
        assert group_col == "source_patient_id"
        cv = compute_crossvalidation_metrics(rows, k=5, seed=42, cv_repeats=1)
        assert cv["foldCount"] == 5
        for fold in cv["foldDetails"]:
            assert fold["groupOverlapCount"] == 0


# ── Training pipeline ────────────────────────────────────────────────────

class TestTrainingPipeline:
    def test_build_xyg(self, dataset_rows):
        features, labels, groups = _build_xyg(dataset_rows)
        assert len(features) == len(labels) == len(groups)
        assert all(len(f) == len(FEATURE_COLUMNS) for f in features)
        assert all(label in (0, 1) for label in labels)

    def test_pipeline_trains_and_predicts(self, dataset_rows):
        features, labels, _ = _build_xyg(dataset_rows)
        pipeline = _build_training_pipeline(seed=42)
        pipeline.fit(features, labels)
        proba = pipeline.predict_proba(features)
        assert proba.shape == (len(features), 2)
        assert all(0.0 <= p <= 1.0 for p in proba[:, 1])

    def test_pipeline_config_matches(self):
        pipeline = _build_training_pipeline(seed=42)
        model = pipeline.named_steps["model"]
        assert model.n_estimators == EXTRA_TREES_CONFIG["n_estimators"]
        assert model.max_depth == EXTRA_TREES_CONFIG["max_depth"]
        assert model.min_samples_leaf == EXTRA_TREES_CONFIG["min_samples_leaf"]

    def test_predict_probability_tree_ensemble(self, dataset_rows):
        features, labels, _ = _build_xyg(dataset_rows)
        pipeline = _build_training_pipeline(seed=42)
        pipeline.fit(features, labels)

        sample_features = {col: features[0][i] for i, col in enumerate(FEATURE_COLUMNS)}
        prob = predict_probability_tree_ensemble(sample_features, pipeline)
        assert 0.0 <= prob <= 1.0


# ── Cross-validation ──────────────────────────────────────────────────────

class TestCrossValidation:
    def test_cv_returns_expected_structure(self, dataset_rows):
        cv = compute_crossvalidation_metrics(dataset_rows, k=3, seed=42)
        assert "foldCount" in cv
        assert "meanMetrics" in cv
        assert "stdMetrics" in cv
        assert "foldDetails" in cv
        assert "scoringConfig" in cv
        assert cv["foldCount"] >= 2

    def test_cv_metrics_in_valid_range(self, dataset_rows):
        cv = compute_crossvalidation_metrics(dataset_rows, k=3, seed=42)
        for key in [
            "accuracy",
            "precision",
            "recall",
            "f1Score",
            "specificity",
            "rocAuc",
            "prAuc",
            "brierScore",
        ]:
            assert 0.0 <= cv["meanMetrics"][key] <= 1.0
            assert 0.0 <= cv["stdMetrics"][key] <= 1.0
        assert "metricConfidenceIntervals95" in cv
        assert "recall" in cv["metricConfidenceIntervals95"]

    def test_cv_no_group_leakage(self, dataset_rows):
        cv = compute_crossvalidation_metrics(dataset_rows, k=3, seed=42)
        for fold in cv["foldDetails"]:
            assert fold["groupOverlapCount"] == 0, "Group leakage detected in CV fold"


# ── Hold-out test ─────────────────────────────────────────────────────────

class TestHoldout:
    def test_holdout_split_disjoint(self, dataset_rows):
        train, test = stratified_group_holdout_split(dataset_rows, test_size=0.2, seed=42)
        assert len(train) > 0
        assert len(test) > 0
        assert len(train) + len(test) == len(dataset_rows)

    def test_holdout_both_classes(self, dataset_rows):
        train, test = stratified_group_holdout_split(dataset_rows, test_size=0.2, seed=42)
        train_labels = {r[TARGET_COLUMN] for r in train}
        test_labels = {r[TARGET_COLUMN] for r in test}
        assert train_labels == {0, 1}
        assert test_labels == {0, 1}

    def test_holdout_metrics_valid(self, dataset_rows):
        train, test = stratified_group_holdout_split(dataset_rows, test_size=0.2, seed=42)
        holdout = compute_holdout_metrics(train, test, seed=42)
        assert "testMetrics" in holdout
        assert "trainMetrics" in holdout
        assert "overfitGap" in holdout
        assert "testBinomialWilsonCi95" in holdout
        assert "referenceThresholdsOnHoldout" in holdout
        wilson = holdout["testBinomialWilsonCi95"]
        assert "recallSensitivity" in wilson
        rs = wilson["recallSensitivity"]
        assert rs["ci95Low"] <= rs["estimate"] + 1e-6
        assert rs["estimate"] <= rs["ci95High"] + 1e-6
        for key in [
            "accuracy",
            "precision",
            "recall",
            "f1Score",
            "specificity",
            "rocAuc",
            "prAuc",
            "brierScore",
        ]:
            assert 0.0 <= holdout["testMetrics"][key] <= 1.0


# ── Full artifact build ──────────────────────────────────────────────────

class TestBuildTrainedArtifact:
    def test_artifact_structure(self, dataset_rows):
        artifact = build_trained_artifact(dataset_rows, seed=42)
        assert artifact["modelType"] == "extra_trees_classifier"
        assert artifact.get("modelAlgorithm") == "extra_trees"
        meta = artifact["metadata"]
        assert meta.get("modelAlgorithm") == "extra_trees"
        assert meta["evaluationStatus"] == "evaluated_with_cv_and_holdout"
        assert meta["cvMetrics"] is not None
        assert meta["cvMetricsStd"] is not None
        assert meta["holdoutMetrics"] is not None
        assert meta["leakageChecks"] is not None
        assert meta["datasetProfile"] is not None
        assert "metricsAnalysis" in meta
        assert "recommendedReportingOrder" in meta["metricsAnalysis"]
        assert meta.get("cvMetricConfidenceIntervals95")

    def test_artifact_leakage_checks_pass(self, dataset_rows):
        artifact = build_trained_artifact(dataset_rows, seed=42)
        leakage = artifact["metadata"]["leakageChecks"]
        assert leakage["labelShuffleCheck"]["status"] == "ok"
        assert leakage["cvSplitterUsed"] in ("StratifiedKFold", "StratifiedGroupKFold")

    def test_artifact_feature_importances(self, dataset_rows):
        artifact = build_trained_artifact(dataset_rows, seed=42)
        importances = artifact["metadata"]["featureImportances"]
        for col in FEATURE_COLUMNS:
            assert col in importances
            assert importances[col] >= 0.0

    def test_artifact_cv_metrics_keys(self, dataset_rows):
        artifact = build_trained_artifact(dataset_rows, seed=42)
        cv_metrics = artifact["metadata"]["cvMetrics"]
        for key in [
            "accuracy",
            "precision",
            "recall",
            "f1Score",
            "specificity",
            "rocAuc",
            "prAuc",
            "brierScore",
        ]:
            assert key in cv_metrics


    def test_compare_algorithms_metadata(self, dataset_rows):
        artifact = build_trained_artifact(
            dataset_rows, seed=42, compare_algorithms=True
        )
        comp = artifact["metadata"].get("algorithmComparison")
        assert comp is not None
        assert comp["primaryAlgorithm"] == "extra_trees"
        assert comp["alternateAlgorithm"] == "hist_gradient_boosting"
        assert "recall" in comp["alternateCvMeanMetrics"]


# ── Train and serialize ───────────────────────────────────────────────────

class TestTrainAndSerialize:
    def test_train_model_from_dataset_path(self, dataset_path):
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.json"
            artifact = train_model_from_dataset_path(dataset_path, model_path, seed=42)

            assert model_path.exists(), "JSON artifact not created"
            pipeline_path = model_path.with_suffix(".joblib")
            assert pipeline_path.exists(), "joblib pipeline not created"

            loaded = json.loads(model_path.read_text(encoding="utf-8"))
            assert loaded["modelType"] == "extra_trees_classifier"
            assert loaded["metadata"]["datasetRows"] > 0

    def test_serialized_pipeline_predicts(self, dataset_path):
        import joblib
        with tempfile.TemporaryDirectory() as tmpdir:
            model_path = Path(tmpdir) / "test_model.json"
            train_model_from_dataset_path(dataset_path, model_path, seed=42)

            pipeline = joblib.load(model_path.with_suffix(".joblib"))
            payload = {
                "personalInfo": {
                    "age": 30,
                    "sex": "male",
                    "heightCm": 170,
                    "weightKg": 72,
                    "diagnosedHypertension": "no",
                    "fatherHypertension": "no",
                    "motherHypertension": "no",
                },
                "familyHistory": {
                    "mother": "no",
                    "father": "no",
                    "siblingsCount": 2,
                    "siblingsDiabetesCount": 1,
                    "paternalAuntsUnclesCount": 2,
                    "paternalAuntsUnclesDiabetesCount": 0,
                    "maternalAuntsUnclesCount": 2,
                    "maternalAuntsUnclesDiabetesCount": 1,
                    "physicalActivityScore": 2,
                },
            }
            base_features, _ = build_base_features(payload)
            sample = [[float(base_features.get(col, 0.0)) for col in FEATURE_COLUMNS]]
            proba = pipeline.predict_proba(sample)
            assert 0.0 <= proba[0][1] <= 1.0

