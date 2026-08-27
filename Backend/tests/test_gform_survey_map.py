"""Tests for DESCEND Google Form → training-dataset cleaning."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gform_survey_map import (  # noqa: E402
    derive_diet_quality_label,
    encode_consent,
    is_google_form_export,
    maybe_normalize_raw_row,
    sibling_diabetes_count,
)
from prepare_training_dataset import (  # noqa: E402
    map_physical_activity_combined,
    prepare_training_dataset,
)


GFORM_HEADERS = [
    "Timestamp",
    "Do you agree to participate in this study?",
    "Has a doctor diagnosed you with Type 2 diabetes?",
    "At what age were you diagnosed?",
    "What is your sex?",
    "What is your age?",
    "What is your height in centimeters?",
    "What is your weight in kilograms?",
    "Have you been told you have hypertension (high blood pressure)?",
    "If you know it, what is your fasting blood glucose (mg/dL)? (optional)",
    "If you know it, what is your HbA1c (%)?  (optional)",
    "How would you describe your usual physical activity level?",
    "How often do you exercise in a typical week?",
    "How long is a typical exercise session?",
    "How often do you drink sugary drinks?",
    "How often do you eat fast food?",
    "What is your smoking status?",
    "How would you describe your alcohol consumption?",
    "How many hours do you usually sleep per night?",
    "Does your father have Type 2 diabetes?",
    "At what age was your father diagnosed?",
    "Does your mother have Type 2 diabetes?",
    "At what age was your mother diagnosed?",
    "Does your sibling have Type 2 diabetes?",
    "At what age was your sibling diagnosed?",
    "Does your maternal grandfather have Type 2 diabetes?",
    "At what age was your maternal grandfather diagnosed?",
    "Does your maternal grandmother have Type 2 diabetes?",
    "At what age was your maternal grandmother diagnosed?",
    "How many maternal uncles have Type 2 diabetes?",
    "How many maternal aunts have Type 2 diabetes?",
    "What was the earliest age at diagnosis among maternal aunts or uncles? (optional)",
    "Does your paternal grandfather have Type 2 diabetes?",
    "At what age was your paternal grandfather diagnosed?",
    "Does your paternal grandmother have Type 2 diabetes?",
    "At what age was your paternal grandmother diagnosed?",
    "How many paternal uncles have Type 2 diabetes?",
    "How many paternal aunts have Type 2 diabetes?",
    "What was the earliest age at diagnosis among paternal aunts or uncles? (optional)",
]


def _gform_row(**overrides) -> dict[str, str]:
    base = {header: "" for header in GFORM_HEADERS}
    base.update(
        {
            "Timestamp": "1/1/2024 12:00:00",
            "Do you agree to participate in this study?": "I agree",
            "Has a doctor diagnosed you with Type 2 diabetes?": "No",
            "What is your sex?": "Female",
            "What is your age?": "40",
            "What is your height in centimeters?": "160",
            "What is your weight in kilograms?": "60",
            "Have you been told you have hypertension (high blood pressure)?": "No",
            "How would you describe your usual physical activity level?": (
                "Moderately active (moderate exercise 3-5 days/week)"
            ),
            "How often do you exercise in a typical week?": "2-3 times a week",
            "How long is a typical exercise session?": "30-45 minutes",
            "How often do you drink sugary drinks?": "Rarely (once a month or less)",
            "How often do you eat fast food?": "Never",
            "What is your smoking status?": "Never smoked",
            "How would you describe your alcohol consumption?": "I do not drink alcohol",
            "How many hours do you usually sleep per night?": "7-8 hours",
            "Does your father have Type 2 diabetes?": "No",
            "Does your mother have Type 2 diabetes?": "No",
            "Does your sibling have Type 2 diabetes?": "No",
            "Does your maternal grandfather have Type 2 diabetes?": "No",
            "Does your maternal grandmother have Type 2 diabetes?": "No",
            "How many maternal uncles have Type 2 diabetes?": "0",
            "How many maternal aunts have Type 2 diabetes?": "0",
            "Does your paternal grandfather have Type 2 diabetes?": "No",
            "Does your paternal grandmother have Type 2 diabetes?": "No",
            "How many paternal uncles have Type 2 diabetes?": "0",
            "How many paternal aunts have Type 2 diabetes?": "0",
        }
    )
    base.update(overrides)
    return base


def test_detects_google_form_headers():
    assert is_google_form_export(GFORM_HEADERS)
    assert not is_google_form_export(["patient_id", "age", "height_cm"])


def test_consent_and_sibling_encoding():
    assert encode_consent("I agree") == "1"
    assert encode_consent("Yes, I agree and wish to continue") == "1"
    assert encode_consent("No, I do not agree") == "0"
    assert sibling_diabetes_count("Yes") == 1
    assert sibling_diabetes_count("No") == 0
    assert sibling_diabetes_count("I'm not sure") == 0


def test_diet_quality_from_sugary_and_fast_food():
    assert derive_diet_quality_label("Daily", "Never") == "unhealthy"
    assert derive_diet_quality_label("Often (a few times a week)", "Rarely (once a month or less)") == "unhealthy"
    assert derive_diet_quality_label("Sometimes (a few times a month)", "Never") == "mixed"
    assert derive_diet_quality_label("Rarely (once a month or less)", "Never") == "healthy"


def test_activity_mapping_matches_frequency_then_level():
    assert map_physical_activity_combined("Daily", "Sedentary (little or no exercise)") == 2.0
    assert map_physical_activity_combined("4-5 times a week", "") == 2.0
    assert map_physical_activity_combined("2-3 times a week", "") == 1.0
    assert map_physical_activity_combined("Never", "Very active (hard exercise 6-7 days/week)") == 1.0
    assert map_physical_activity_combined("Never", "Sedentary (little or no exercise)") == 0.0
    assert map_physical_activity_combined(4, None) == 2.0
    assert map_physical_activity_combined(1, None) == 0.0


def test_normalize_gform_row_family_counts():
    row = maybe_normalize_raw_row(
        _gform_row(
            **{
                "Does your sibling have Type 2 diabetes?": "Yes",
                "How many maternal uncles have Type 2 diabetes?": "2",
                "How many maternal aunts have Type 2 diabetes?": "1",
                "How many paternal uncles have Type 2 diabetes?": "0",
                "How many paternal aunts have Type 2 diabetes?": "3",
                "Does your father have Type 2 diabetes?": "I'm not sure",
            }
        ),
        patient_id=7,
    )
    assert row["patient_id"] == "7"
    assert row["consent"] == "1"
    assert row["siblings_t2dm_count_raw"] == "1"
    assert row["maternal_aunts_uncles_t2dm_count_raw"] == "3"
    assert row["paternal_aunts_uncles_t2dm_count_raw"] == "3"
    assert row["father_t2dm_count_raw"] == "I'm not sure"
    assert row["diet_quality"] == "healthy"
    assert row["age"] == "40"
    assert row["height_cm"] == "160"


def test_prepare_writes_training_rows(tmp_path: Path):
    raw_path = tmp_path / "raw.csv"
    out_path = tmp_path / "training.csv"
    rows = [
        _gform_row(),
        _gform_row(
            **{
                "Has a doctor diagnosed you with Type 2 diabetes?": "Yes",
                "At what age were you diagnosed?": "48",
                "What is your sex?": "Male",
                "What is your age?": "52",
                "Does your mother have Type 2 diabetes?": "Yes",
            }
        ),
        _gform_row(**{"Do you agree to participate in this study?": "No, I do not agree"}),
    ]
    with raw_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=GFORM_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    prepare_training_dataset(raw_path, out_path)

    with out_path.open("r", encoding="utf-8-sig", newline="") as handle:
        trained = list(csv.DictReader(handle))
    assert len(trained) == 2
    assert {row["outcome"] for row in trained} == {"0", "1"}
    assert trained[0]["user_is_male"] == "0.0"
    assert trained[1]["user_is_male"] == "1.0"
    assert trained[1]["parent_has_t2dm"] == "1.0"
    assert trained[0]["target_label"] == "respondent"
