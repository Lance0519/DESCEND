from __future__ import annotations

import re
from dataclasses import dataclass


STATUS_MAP = {"yes": 1.0, "no": 0.0, "unknown": 0.35}
DIAGNOSIS_MAP = {"yes": 1.0, "no": 0.0, "unsure": 0.35}
SIBLING_MAP = {"yes": 1.0, "no": 0.0, "unknown": 0.35, "no_siblings": 0.0}
SEX_MAP = {"female": 0.0, "male": 1.0}

FAMILY_ORDER = [
    "maternalGrandmother",
    "maternalGrandfather",
    "paternalGrandmother",
    "paternalGrandfather",
    "mother",
    "father",
]


@dataclass(frozen=True)
class TargetSpec:
    key: str
    label: str
    generation_depth: int
    target_is_male: int


TARGETS = [
    TargetSpec("male_child", "Male Child", 1, 1),
    TargetSpec("female_child", "Female Child", 1, 0),
]

FAMILY_LABELS = {
    "maternalGrandmother": "Maternal Grandmother",
    "maternalGrandfather": "Maternal Grandfather",
    "paternalGrandmother": "Paternal Grandmother",
    "paternalGrandfather": "Paternal Grandfather",
    "mother": "Mother",
    "father": "Father",
    "siblings": "Siblings",
    "auntsUncles": "Aunts / Uncles",
    "user": "User",
}


def _status_from_count(count: int) -> float:
    return 1.0 if count > 0 else 0.0


def compute_bmi(height_cm: float, weight_kg: float) -> float:
    height_m = max(height_cm / 100.0, 0.1)
    return round(weight_kg / (height_m**2), 2)


def _safe_non_negative_int(value, fallback: int = 0) -> int:
    try:
        parsed = int(float(value))
        return max(parsed, 0)
    except (TypeError, ValueError):
        return fallback


def _map_physical_activity_to_model(value) -> float:
    """Normalize survey coding to model scale.

    Survey coding (source of truth):
    - 1: rarely/never
    - 2: 1-2x/week
    - 3: 3-4x/week
    - 4: 5+x/week

    Model scale kept compatible with existing calibration:
    - 0: low, 1: moderate, 2: high
    """
    try:
        raw = int(float(value))
    except (TypeError, ValueError):
        return 1.0

    if raw <= 0:
        return 0.0
    if raw == 1:
        return 0.0
    if raw in {2, 3}:
        return 1.0
    return 2.0


def _map_diet_quality_to_model(value) -> float:
    """Normalize survey coding to model scale.

    Survey coding: 1=poor, 2=average, 3=balanced
    Model scale:   0=poor, 1=average, 2=balanced
    """
    try:
        raw = int(float(value))
    except (TypeError, ValueError):
        return 1.0

    if raw in {1, 2, 3}:
        return float(raw - 1)
    return 1.0


def _map_hypertension_for_model(value) -> float:
    """Map hypertension for prediction — mirrors prepare_training_dataset.map_hypertension."""
    text = str(value).strip().lower() if value is not None else ""
    if "not sure" in text or "unsure" in text or "unknown" in text:
        return 0.35
    if text.startswith("yes"):
        return 1.0
    if text.startswith("no"):
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return 0.35
    try:
        raw = int(float(match.group(0)))
    except ValueError:
        return 0.35
    if raw == 1:
        return 1.0
    if raw == 0:
        return 0.0
    if raw == 99:
        return 0.35
    return 0.35


def normalize_family_status(value) -> str:
    """Map UI/API variants to yes | no | unknown for six-pedigree T2DM fields."""
    if value is None:
        return "unknown"
    t = str(value).strip().lower()
    if t in {"yes", "y", "true", "1", "positive"}:
        return "yes"
    if t in {"no", "n", "false", "0", "negative"}:
        return "no"
    if t in {"unknown", "unsure", "not sure", "na", "n/a"}:
        return "unknown"
    return "unknown"


from .graph import build_family_graph, derive_family_metrics  # noqa: F401


def _compute_hereditary_load_index(
    parent_has_t2dm: float,
    first_degree_yes: int,
    second_degree_yes: int,
    weighted_family_score: float,
    siblings_diabetes_count: float,
    aunts_uncles_score: float,
) -> float:
    """Blend parental T2DM, generational positives, weighted tree score, and extended family load."""
    deg1_frac = min(float(first_degree_yes) / 2.0, 1.0)
    deg2_frac = min(float(second_degree_yes) / 4.0, 1.0)
    wf_frac = min(max(float(weighted_family_score), 0.0) / 3.5, 1.0)
    lineage_strength = min(
        1.2,
        0.48 * float(parent_has_t2dm)
        + 0.22 * deg1_frac
        + 0.26 * deg2_frac
        + 0.14 * wf_frac,
    )
    extended = float(siblings_diabetes_count) + float(aunts_uncles_score)
    return round(lineage_strength * (1.0 + 0.42 * extended), 4)


def _resolve_extended_family_for_model(family_history: dict) -> tuple[int, int, float, float]:
    """Normalize sibling and aunt/uncle diabetes counts and scores (survey + legacy fields).

    If total siblings or aunt/uncle headcount is zero, diabetic counts for that group are forced to
    zero so inconsistent form input (e.g. 0 siblings but 3 with diabetes) cannot inflate risk.
    """
    siblings_diabetes_count = _safe_non_negative_int(
        family_history.get("siblingsDiabetesCount", 0),
        0,
    )
    siblings_total_count = _safe_non_negative_int(
        family_history.get("siblingsCount", 0),
        0,
    )
    paternal_aunts_uncles_count = _safe_non_negative_int(
        family_history.get("paternalAuntsUnclesDiabetesCount", 0),
        0,
    )
    paternal_aunts_uncles_total = _safe_non_negative_int(
        family_history.get("paternalAuntsUnclesCount", 0),
        0,
    )
    maternal_aunts_uncles_count = _safe_non_negative_int(
        family_history.get("maternalAuntsUnclesDiabetesCount", 0),
        0,
    )
    maternal_aunts_uncles_total = _safe_non_negative_int(
        family_history.get("maternalAuntsUnclesCount", 0),
        0,
    )

    if siblings_total_count <= 0:
        siblings_diabetes_count = 0
    else:
        siblings_diabetes_count = min(siblings_diabetes_count, siblings_total_count)

    if paternal_aunts_uncles_total <= 0:
        paternal_aunts_uncles_count = 0
    else:
        paternal_aunts_uncles_count = min(paternal_aunts_uncles_count, paternal_aunts_uncles_total)

    if maternal_aunts_uncles_total <= 0:
        maternal_aunts_uncles_count = 0
    else:
        maternal_aunts_uncles_count = min(maternal_aunts_uncles_count, maternal_aunts_uncles_total)

    legacy_aunts_uncles_count = _safe_non_negative_int(
        family_history.get("auntsUnclesDiabetesCount", 0),
        0,
    )
    aunts_uncles_diabetes_count = paternal_aunts_uncles_count + maternal_aunts_uncles_count
    if aunts_uncles_diabetes_count == 0:
        aunts_uncles_diabetes_count = legacy_aunts_uncles_count

    if "siblings" in family_history:
        siblings_score = SIBLING_MAP.get(normalize_family_status(family_history.get("siblings")), 0.35)
        if normalize_family_status(family_history.get("siblings")) != "yes":
            siblings_diabetes_count = 0
    else:
        siblings_score = _status_from_count(siblings_diabetes_count)

    if "auntsUncles" in family_history:
        aunts_uncles_score = STATUS_MAP.get(normalize_family_status(family_history.get("auntsUncles")), 0.35)
        if normalize_family_status(family_history.get("auntsUncles")) != "yes":
            aunts_uncles_diabetes_count = 0
    else:
        aunts_uncles_score = _status_from_count(aunts_uncles_diabetes_count)

    return siblings_diabetes_count, aunts_uncles_diabetes_count, siblings_score, aunts_uncles_score


def build_base_features(payload: dict) -> tuple[dict, dict]:
    personal = payload.get("personalInfo", {})
    family_history = payload.get("familyHistory", {})

    age = float(personal.get("age", 30))
    height_cm = float(personal.get("heightCm", 165))
    weight_kg = float(personal.get("weightKg", 65))
    bmi = compute_bmi(height_cm, weight_kg)

    mother_t2dm_status = STATUS_MAP.get(normalize_family_status(family_history.get("mother")), 0.35)
    father_t2dm_status = STATUS_MAP.get(normalize_family_status(family_history.get("father")), 0.35)
    parent_has_t2dm = max(mother_t2dm_status, father_t2dm_status)
    hypertension_status = _map_hypertension_for_model(personal.get("diagnosedHypertension", "no"))
    father_hypertension = _map_hypertension_for_model(personal.get("fatherHypertension", "no"))
    mother_hypertension = _map_hypertension_for_model(personal.get("motherHypertension", "no"))

    # Blend personal diagnosis with parental hypertension history without adding new model columns.
    hypertension_status = min(1.0, hypertension_status + (0.25 * father_hypertension) + (0.25 * mother_hypertension))

    siblings_diabetes_count, aunts_uncles_diabetes_count, siblings_score, aunts_uncles_score = (
        _resolve_extended_family_for_model(family_history)
    )

    extended_diabetes_count = int(siblings_diabetes_count) + int(aunts_uncles_diabetes_count)
    family_metrics = derive_family_metrics(
        family_history,
        extended_diabetes_count=extended_diabetes_count,
    )

    # Propagation probability from genetic-style propagation model (multiplicative per-relative)
    propagation_probability = float(family_metrics.get("propagationProbability", 0.0))

    mother_gdm_during_index_pregnancy = DIAGNOSIS_MAP.get(
        family_history.get("motherGdmDuringIndexPregnancy", "unsure"),
        0.35,
    )

    # Survey is the source of truth; map raw survey coding to model-compatible scales.
    physical_activity_score = _map_physical_activity_to_model(family_history.get("physicalActivityScore", 2))
    diet_quality_score = _map_diet_quality_to_model(family_history.get("dietQualityScore", 2))

    # Compute interaction features for non-linear risk modeling
    metabolic_risk_index = round(age * (bmi / 24.0), 4)
    hereditary_load_index = _compute_hereditary_load_index(
        parent_has_t2dm,
        int(family_metrics["firstDegreeYesCount"]),
        int(family_metrics["secondDegreeYesCount"]),
        float(family_metrics["weightedFamilyScore"]),
        float(siblings_diabetes_count),
        float(aunts_uncles_score),
    )
    activity_metabolic_index = round(physical_activity_score * (1.0 + hypertension_status), 4)

    base_features = {
        "age": age,
        "bmi": bmi,
        "user_is_male": SEX_MAP.get(personal.get("sex", "female"), 0.0),
        "physical_activity_score": physical_activity_score,
        "smoking_score": 0.0,
        "diet_quality_score": diet_quality_score,
        "alcohol_score": 1.0,
        "sleep_hours": 7.0,
        "stress_score": 1.0,
        "parent_has_t2dm": parent_has_t2dm,
        "hypertension_status": hypertension_status,
        "mother_gdm_during_index_pregnancy": mother_gdm_during_index_pregnancy,
        "siblings_score": siblings_score,
        "aunts_uncles_score": aunts_uncles_score,
        "siblings_diabetes_count": float(siblings_diabetes_count),
        "aunts_uncles_diabetes_count": float(aunts_uncles_diabetes_count),
        "metabolic_risk_index": metabolic_risk_index,
        "hereditary_load_index": hereditary_load_index,
        "propagationProbability": propagation_probability,
        "activity_metabolic_index": activity_metabolic_index,
        **family_metrics,
    }

    return base_features, {"bmi": bmi, **family_metrics}


def build_target_features(base_features: dict, target: TargetSpec) -> dict:
    """
    Add target-specific demographic fields to base features.
    Interaction terms are already computed in build_base_features.
    """
    return {
        **base_features,
        "generation_depth": target.generation_depth,
        "target_is_male": target.target_is_male,
    }


def build_key_factors(derived_metrics: dict, personal: dict) -> list[str]:
    factors: list[str] = []

    bmi = derived_metrics["bmi"]
    if bmi >= 30:
        factors.append("Elevated BMI increases metabolic risk.")
    elif bmi >= 25:
        factors.append("BMI is above the ideal range and may increase susceptibility.")

    if derived_metrics["firstDegreeYesCount"] > 0:
        factors.append("A first-degree family history of Type 2 Diabetes raises hereditary risk.")

    if derived_metrics["secondDegreeYesCount"] >= 2:
        factors.append("Multiple grandparent diabetes cases strengthen lineage-based risk.")

    if not factors:
        factors.append("Current profile indicates lower inherited burden within recorded family history.")

    sex_label = "male" if personal.get("sex") == "male" else "female"
    factors.append(f"Assessment was generated using {sex_label} parent profile inputs and lineage history.")
    return factors[:4]


def _normalize_scale(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    if maximum <= minimum:
        return 0.0
    scaled = ((value - minimum) / (maximum - minimum)) * 100.0
    return round(min(max(scaled, 0.0), 100.0), 1)


def build_risk_breakdown(base_features: dict, derived_metrics: dict) -> list[dict]:
    bmi_score = 0.0
    if derived_metrics["bmi"] >= 30:
        bmi_score = 92.0
    elif derived_metrics["bmi"] >= 25:
        bmi_score = 68.0
    elif derived_metrics["bmi"] >= 18.5:
        bmi_score = 34.0
    else:
        bmi_score = 28.0

    clinical_profile = (
        base_features["parent_has_t2dm"] * 42.0
        + base_features["hypertension_status"] * 22.0
    )

    extended_family_burden = (
        base_features["siblings_diabetes_count"] * 24.0
        + base_features["aunts_uncles_diabetes_count"] * 9.0
    )

    return [
        {
            "key": "family_history",
            "label": "Family History",
            "value": _normalize_scale(derived_metrics["weightedFamilyScore"], 0.0, 2.4),
            "description": "Weighted hereditary influence from parents and grandparents.",
        },
        {
            "key": "bmi_status",
            "label": "BMI Status",
            "value": round(bmi_score, 1),
            "description": "Body mass index contribution to metabolic susceptibility.",
        },
        {
            "key": "clinical_profile",
            "label": "Clinical Profile",
            "value": _normalize_scale(clinical_profile, 0.0, 100.0),
            "description": "Contribution from parent diagnosis and blood pressure history.",
        },
        {
            "key": "lineage_depth",
            "label": "Lineage Depth",
            "value": _normalize_scale(derived_metrics["lineageRiskIndex"], 0.0, 4.5),
            "description": (
                "Generational burden (parents, grandparents) plus extended-family "
                "diabetes counts, combined into a single lineage index."
            ),
        },
        {
            "key": "extended_family_count",
            "label": "Extended Family Count",
            "value": _normalize_scale(extended_family_burden, 0.0, 100.0),
            "description": "Estimated burden from the number of diabetic siblings and aunts/uncles.",
        },
    ]


def _personal_diagnosed_t2dm_raw(personal: dict) -> object:
    """Prefer camelCase survey key; accept snake_case for API compatibility."""
    v = personal.get("diagnosedT2dm")
    if v is not None and str(v).strip() != "":
        return v
    return personal.get("diagnosed_t2dm")


def build_family_lineage_data(family_history: dict, personal: dict | None = None) -> dict:
    """Pedigree nodes for visualization. Respondent status follows surveyed diagnosedT2dm (yes/no/unsure→unknown)."""
    personal = personal or {}
    nodes: list[dict] = []
    for member in [
        "maternalGrandmother",
        "maternalGrandfather",
        "paternalGrandmother",
        "paternalGrandfather",
        "mother",
        "father",
    ]:
        nodes.append(
            {
                "key": member,
                "label": FAMILY_LABELS[member],
                "status": normalize_family_status(family_history.get(member)),
                "generation": 0 if "Grand" in FAMILY_LABELS[member] else 1,
                "isRespondent": False,
            }
        )
    user_node: dict = {
        "key": "user",
        "label": FAMILY_LABELS["user"],
        "status": normalize_family_status(_personal_diagnosed_t2dm_raw(personal)),
        "generation": 2,
        "isRespondent": True,
    }
    sex = str(personal.get("sex") or "").strip().lower()
    if sex in {"male", "m"}:
        user_node["gender"] = "male"
    elif sex in {"female", "f"}:
        user_node["gender"] = "female"
    nodes.append(user_node)
    return {
        "nodes": nodes,
        "edges": [
            {"from": "maternalGrandmother", "to": "mother"},
            {"from": "maternalGrandfather", "to": "mother"},
            {"from": "paternalGrandmother", "to": "father"},
            {"from": "paternalGrandfather", "to": "father"},
            {"from": "mother", "to": "user"},
            {"from": "father", "to": "user"},
        ],
    }


def build_recommendations(derived_metrics: dict, personal: dict, family_history: dict) -> list[dict]:
    recommendations: list[dict] = []

    if derived_metrics["bmi"] >= 25:
        recommendations.append(
            {
                "title": "Weight management support",
                "description": "Aim for a healthy BMI through balanced calorie intake and regular monitoring.",
                "priority": "high",
            }
        )

    if personal.get("diagnosedHypertension") in {"yes", "unsure"}:
        recommendations.append(
            {
                "title": "Monitor blood pressure regularly",
                "description": "Maintain routine blood pressure checks and discuss long-term prevention targets with a clinician.",
                "priority": "high",
            }
        )

    if personal.get("fatherHypertension") in {"yes", "unsure"} or personal.get("motherHypertension") in {"yes", "unsure"}:
        recommendations.append(
            {
                "title": "Track family blood pressure risk",
                "description": "Parental hypertension history can increase cardiometabolic vulnerability, so regular BP checks and preventive follow-up are advised.",
                "priority": "medium",
            }
        )

    if personal.get("diagnosedT2dm") in {"yes", "unsure"}:
        recommendations.append(
            {
                "title": "Prioritize glucose monitoring",
                "description": "Use regular glucose follow-up and professional guidance to support long-term glycemic control.",
                "priority": "medium",
            }
        )

    if personal.get("diagnosedT2dm") == "yes" and personal.get("diagnosedT2dmConfirmationMethod") == "self_check_only":
        recommendations.append(
            {
                "title": "Confirm diabetes status clinically",
                "description": "A laboratory test or physician confirmation helps validate self-check findings and supports appropriate follow-up.",
                "priority": "medium",
            }
        )

    if derived_metrics["firstDegreeYesCount"] > 0 or derived_metrics["secondDegreeYesCount"] > 0:
        recommendations.append(
            {
                "title": "Schedule preventive screening",
                "description": "Because of family history, regular glucose monitoring and early preventive clinical follow-up are advisable.",
                "priority": "high",
            }
        )

    siblings_diabetes_resolved, aunts_uncles_diabetes_resolved, _, _ = _resolve_extended_family_for_model(
        family_history
    )

    if family_history.get("motherGdmDuringIndexPregnancy") == "yes":
        recommendations.append(
            {
                "title": "Monitor maternal-line glucose risk closely",
                "description": "A maternal gestational diabetes history can indicate higher long-term metabolic risk for offspring, so earlier preventive screening is advisable.",
                "priority": "medium",
            }
        )

    if siblings_diabetes_resolved + aunts_uncles_diabetes_resolved >= 2:
        recommendations.append(
            {
                "title": "Use earlier preventive follow-up",
                "description": "Multiple affected relatives among siblings and aunts/uncles suggest earlier and more frequent screening.",
                "priority": "high",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "title": "Maintain healthy routines",
                "description": "Continue balanced nutrition, regular activity, and preventive health checkups to keep risk lower.",
                "priority": "low",
            }
        )

    return recommendations[:4]
