"""Map DESCEND Google Form survey exports onto the internal training schema.

The live Google Form uses question-text headers (and English choice labels).
The feature-engineering script expects the older internal column names
(patient_id, age, height_cm, father_t2dm_count_raw, ...).
"""

from __future__ import annotations

import re
from typing import Iterable

# Normalized question text (lowercase, collapsed whitespace) -> internal column.
GFORM_COLUMN_MAP: dict[str, str] = {
    "do you agree to participate in this study?": "consent",
    "has a doctor diagnosed you with type 2 diabetes?": "patient_has_t2dm_status",
    "at what age were you diagnosed?": "age_at_diagnosis",
    "what is your sex?": "sex_at_birth",
    "what is your age?": "age",
    "what is your height in centimeters?": "height_cm",
    "what is your weight in kilograms?": "weight_kg",
    "have you been told you have hypertension (high blood pressure)?": "self_hypertension_status",
    "if you know it, what is your fasting blood glucose (mg/dl)? (optional)": "fasting_glucose_mg_dl",
    "if you know it, what is your hba1c (%)? (optional)": "hba1c_percent",
    "how would you describe your usual physical activity level?": "physical_activity_level",
    "how often do you exercise in a typical week?": "physical_activity_frequency",
    "how long is a typical exercise session?": "exercise_duration",
    "how often do you drink sugary drinks?": "sugary_drink_frequency",
    "how often do you eat fast food?": "fast_food_frequency",
    "what is your smoking status?": "smoking_status",
    "how would you describe your alcohol consumption?": "alcohol_consumption",
    "how many hours do you usually sleep per night?": "sleep_duration",
    "does your father have type 2 diabetes?": "father_t2dm_count_raw",
    "at what age was your father diagnosed?": "father_age_at_diagnosis",
    "does your mother have type 2 diabetes?": "mother_t2dm_count_raw",
    "at what age was your mother diagnosed?": "mother_age_at_diagnosis",
    "does your sibling have type 2 diabetes?": "sibling_t2dm_status",
    "at what age was your sibling diagnosed?": "sibling_age_at_diagnosis",
    "does your maternal grandfather have type 2 diabetes?": "maternal_grandfather_t2dm_count_raw",
    "at what age was your maternal grandfather diagnosed?": "maternal_grandfather_age_at_diagnosis",
    "does your maternal grandmother have type 2 diabetes?": "maternal_grandmother_t2dm_count_raw",
    "at what age was your maternal grandmother diagnosed?": "maternal_grandmother_age_at_diagnosis",
    "how many maternal uncles have type 2 diabetes?": "maternal_uncles_t2dm_count",
    "how many maternal aunts have type 2 diabetes?": "maternal_aunts_t2dm_count",
    "what was the earliest age at diagnosis among maternal aunts or uncles? (optional)": (
        "maternal_aunts_uncles_earliest_age"
    ),
    "does your paternal grandfather have type 2 diabetes?": "paternal_grandfather_t2dm_count_raw",
    "at what age was your paternal grandfather diagnosed?": "paternal_grandfather_age_at_diagnosis",
    "does your paternal grandmother have type 2 diabetes?": "paternal_grandmother_t2dm_count_raw",
    "at what age was your paternal grandmother diagnosed?": "paternal_grandmother_age_at_diagnosis",
    "how many paternal uncles have type 2 diabetes?": "paternal_uncles_t2dm_count",
    "how many paternal aunts have type 2 diabetes?": "paternal_aunts_t2dm_count",
    "what was the earliest age at diagnosis among paternal aunts or uncles? (optional)": (
        "paternal_aunts_uncles_earliest_age"
    ),
}

_GFORM_DETECT_HEADERS = {
    "do you agree to participate in this study?",
    "has a doctor diagnosed you with type 2 diabetes?",
    "what is your height in centimeters?",
}


def normalize_header(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def is_google_form_export(fieldnames: Iterable[str] | None) -> bool:
    if not fieldnames:
        return False
    headers = {normalize_header(name) for name in fieldnames}
    return bool(headers & _GFORM_DETECT_HEADERS)


def _text(value) -> str:
    return str(value).strip().lower() if value is not None else ""


def encode_consent(value) -> str:
    txt = _text(value)
    if not txt:
        return "1"
    if "not agree" in txt or txt in {"no", "0"}:
        return "0"
    if "agree" in txt or txt in {"yes", "1"}:
        return "1"
    return "1"


def _parse_non_negative_int(value, fallback: int = 0) -> int:
    match = re.search(r"-?\d+", str(value or "").strip())
    if not match:
        return fallback
    try:
        return max(int(match.group(0)), 0)
    except ValueError:
        return fallback


def sibling_diabetes_count(value) -> int:
    txt = _text(value)
    if txt.startswith("yes"):
        return 1
    return 0


def derive_diet_quality_label(sugary, fast_food) -> str | None:
    """Map sugary-drink + fast-food frequency to the old diet_quality labels."""
    texts = [_text(sugary), _text(fast_food)]
    if not any(texts):
        return None
    if any(
        any(token in text for token in ("daily", "often", "several", "few times a week"))
        for text in texts
    ):
        return "unhealthy"
    if any(
        any(token in text for token in ("sometimes", "few times a month", "weekly", "once a week"))
        for text in texts
    ):
        return "mixed"
    return "healthy"


def remap_gform_headers(row: dict) -> dict:
    remapped: dict[str, str] = {}
    for raw_key, raw_value in row.items():
        internal = GFORM_COLUMN_MAP.get(normalize_header(raw_key))
        if internal:
            remapped[internal] = "" if raw_value is None else str(raw_value).strip()
        elif normalize_header(raw_key) == "timestamp":
            remapped["timestamp"] = "" if raw_value is None else str(raw_value).strip()
    return remapped


def normalize_gform_row(row: dict, patient_id: int) -> dict:
    """Convert one Google Form response into the internal raw-survey schema."""
    mapped = remap_gform_headers(row)
    mapped["patient_id"] = str(patient_id)
    mapped["consent"] = encode_consent(mapped.get("consent"))
    mapped["siblings_t2dm_count_raw"] = str(sibling_diabetes_count(mapped.get("sibling_t2dm_status")))
    mapped["maternal_aunts_uncles_t2dm_count_raw"] = str(
        _parse_non_negative_int(mapped.get("maternal_uncles_t2dm_count"))
        + _parse_non_negative_int(mapped.get("maternal_aunts_t2dm_count"))
    )
    mapped["paternal_aunts_uncles_t2dm_count_raw"] = str(
        _parse_non_negative_int(mapped.get("paternal_uncles_t2dm_count"))
        + _parse_non_negative_int(mapped.get("paternal_aunts_t2dm_count"))
    )
    diet_label = derive_diet_quality_label(
        mapped.get("sugary_drink_frequency"),
        mapped.get("fast_food_frequency"),
    )
    if diet_label:
        mapped["diet_quality"] = diet_label
    # Field was not asked on the DESCEND Google Form.
    mapped.setdefault("mother_gdm_during_index_pregnancy", "")
    return mapped


def maybe_normalize_raw_row(row: dict, patient_id: int) -> dict:
    """Normalize Google Form rows; pass through internal-schema rows with an id."""
    if is_google_form_export(row.keys()):
        return normalize_gform_row(row, patient_id)

    out = {key: ("" if value is None else str(value).strip()) for key, value in row.items()}
    if not str(out.get("patient_id") or "").strip():
        out["patient_id"] = str(patient_id)
    return out
