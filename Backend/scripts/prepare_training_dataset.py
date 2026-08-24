"""
Feature engineering script to transform raw survey CSV into training dataset.
Converts the survey_to_excel_raw_template.csv into training_dataset.csv
with all computed features ready for model training.

Rows are skipped (not silently imputed) when required fields are missing or
out of plausible range; see validate_and_parse_demographics.
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from descend.ml.feature_builder import _compute_hereditary_load_index
from descend.ml.graph import derive_family_metrics


TARGET_LABEL = "respondent"
NEUTRAL_GENERATION_DEPTH = 1.5
NEUTRAL_TARGET_IS_MALE = 0.5

# Plausible screening ranges — tighten/loosen in one place for thesis documentation
AGE_MIN, AGE_MAX = 12.0, 110.0
HEIGHT_CM_MIN, HEIGHT_CM_MAX = 100.0, 230.0
WEIGHT_KG_MIN, WEIGHT_KG_MAX = 28.0, 280.0
BMI_MIN, BMI_MAX = 12.0, 65.0


def _text(value) -> str:
    return str(value).strip().lower() if value is not None else ""


def _extract_first_number(value):
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def compute_bmi(height_cm: float, weight_kg: float) -> float:
    """Calculate BMI from height (cm) and weight (kg)."""
    height_m = max(height_cm / 100.0, 0.1)
    return round(weight_kg / (height_m**2), 2)


def map_physical_activity(value) -> float:
    """Map survey activity frequency to model scale 0-2."""
    txt = _text(value)
    if "rare" in txt or "never" in txt:
        return 0.0
    if "1-2" in txt:
        return 1.0
    if "3-4" in txt:
        return 1.0
    if "5+" in txt or "5x" in txt:
        return 2.0

    numeric = _extract_first_number(value)
    if numeric is None:
        return 1.0
    raw = int(numeric)
    
    if raw <= 0:
        return 0.0
    if raw == 1:  # rarely/never
        return 0.0
    if raw in {2, 3}:  # 1-2x/week or 3-4x/week
        return 1.0
    if raw >= 4:  # 5+/week
        return 2.0
    return 1.0


def map_diet_quality(value) -> float:
    """Map survey diet quality to model scale 0-2."""
    txt = _text(value)
    if "unhealthy" in txt or "poor" in txt:
        return 0.0
    if "mixed" in txt or "average" in txt:
        return 1.0
    if "healthy" in txt or "balanced" in txt:
        return 2.0

    numeric = _extract_first_number(value)
    if numeric is None:
        return 1.0
    raw = int(numeric)
    
    if raw <= 1:  # poor
        return 0.0
    if raw == 2:  # average
        return 1.0
    if raw >= 3:  # balanced
        return 2.0
    return 1.0


def map_yes_no_unsure(value) -> float:
    """Map yes/no/unsure coding: 1->1.0, 0->0.0, 99/0.35->0.35."""
    txt = _text(value)
    if "not sure" in txt or "unsure" in txt or "unknown" in txt:
        return 0.35
    if txt.startswith("yes"):
        return 1.0
    if txt.startswith("no"):
        return 0.0

    numeric = _extract_first_number(value)
    if numeric is None:
        return 0.35
    if abs(numeric - 0.35) < 1e-6:
        return 0.35
    raw = int(numeric)
    
    if raw == 1:
        return 1.0
    if raw == 0:
        return 0.0
    return 0.35  # for 99 (unsure) or other values


def map_hypertension(value) -> float:
    """Map self-reported hypertension: yes=1, no=0, unsure/99=0.35 (uncertain)."""
    txt = _text(value)
    if "not sure" in txt or "unsure" in txt or "unknown" in txt:
        return 0.35
    if txt.startswith("yes"):
        return 1.0
    if txt.startswith("no"):
        return 0.0

    numeric = _extract_first_number(value)
    if numeric is None:
        return 0.35
    if abs(numeric - 0.35) < 1e-6:
        return 0.35
    raw = int(numeric)
    if raw == 1:
        return 1.0
    if raw == 0:
        return 0.0
    if raw == 99:
        return 0.35
    return 0.35


def map_count_to_status(value) -> float:
    """Map count-style family value to status score.

    0 -> 0.0, any positive count -> 1.0, 99/0.35 -> 0.35 (unknown).
    """
    txt = _text(value)
    if "not sure" in txt or "unsure" in txt or "unknown" in txt:
        return 0.35
    if txt.startswith("yes"):
        return 1.0
    if txt.startswith("no"):
        return 0.0

    numeric = _extract_first_number(value)
    if numeric is None:
        return 0.35
    if abs(numeric - 0.35) < 1e-6:
        return 0.35
    raw = int(numeric)

    if raw == 99:
        return 0.35
    if raw <= 0:
        return 0.0
    return 1.0


def safe_int(value, fallback=0) -> int:
    """Safely parse value to int."""
    txt = _text(value)
    if txt.startswith("yes"):
        return 1
    if txt.startswith("no"):
        return 0
    if "not sure" in txt or "unsure" in txt or "unknown" in txt:
        return 99

    numeric = _extract_first_number(value)
    if numeric is None:
        return fallback
    if abs(numeric - 0.35) < 1e-6:
        return 99
    try:
        return max(int(numeric), 0)
    except (TypeError, ValueError):
        return fallback


def safe_count(value, fallback=0) -> int:
    """Parse count fields while treating 99 as unknown (0 for numeric counts)."""
    parsed = safe_int(value, fallback=fallback)
    return 0 if parsed == 99 else parsed


def normalize_sex_is_male(value) -> float | None:
    """Map sex_at_birth to user_is_male in {0.0, 1.0}.

    Supports 0/1 encoding (0=female, 1=male) and 1/2 encoding (1=male, 2=female).
    """
    if value is None or (isinstance(value, str) and not str(value).strip()):
        return None
    txt = _text(value)
    if "female" in txt or txt == "f":
        return 0.0
    if "male" in txt and "female" not in txt:
        return 1.0
    n = _extract_first_number(value)
    if n is None:
        return None
    i = int(round(float(n)))
    if i == 0:
        return 0.0
    if i == 1:
        return 1.0
    if i == 2:
        return 0.0
    return None


def validate_and_parse_demographics(raw_row: dict) -> tuple[dict | None, str | None]:
    """Return parsed age/BMI/sex or (None, reason_code) if row should be skipped."""
    pid = safe_int(raw_row.get("patient_id", ""), fallback=0)
    if pid <= 0:
        return None, "invalid_or_missing_patient_id"

    if "consent" in raw_row and raw_row.get("consent") not in ("", None):
        c = safe_int(raw_row.get("consent"), fallback=1)
        if c == 0:
            return None, "no_consent"

    age_n = _extract_first_number(raw_row.get("age"))
    if age_n is None:
        return None, "missing_age"
    age = float(age_n)
    if not (AGE_MIN <= age <= AGE_MAX):
        return None, "age_out_of_range"

    h_n = _extract_first_number(raw_row.get("height_cm"))
    w_n = _extract_first_number(raw_row.get("weight_kg"))
    if h_n is None or w_n is None:
        return None, "missing_height_or_weight"
    height_cm = float(h_n)
    weight_kg = float(w_n)
    if not (HEIGHT_CM_MIN <= height_cm <= HEIGHT_CM_MAX):
        return None, "height_out_of_range"
    if not (WEIGHT_KG_MIN <= weight_kg <= WEIGHT_KG_MAX):
        return None, "weight_out_of_range"

    bmi = compute_bmi(height_cm, weight_kg)
    if not (BMI_MIN <= bmi <= BMI_MAX):
        return None, "bmi_implausible"

    is_m = normalize_sex_is_male(raw_row.get("sex_at_birth"))
    if is_m is None:
        return None, "invalid_or_missing_sex"

    return {
        "age": age,
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "bmi": bmi,
        "user_is_male": is_m,
    }, None


def transform_row(raw_row: dict, source_record_id: int, demo: dict) -> dict:
    """Transform a raw survey row into training features.

    ``demo`` must come from validate_and_parse_demographics (age, bmi, user_is_male).
    """
    age = demo["age"]
    bmi = demo["bmi"]
    user_is_male = demo["user_is_male"]
    
    # Lifestyle scores
    physical_activity_score = map_physical_activity(raw_row.get('physical_activity_frequency', 1))
    diet_quality_score = map_diet_quality(raw_row.get('diet_quality', 1))
    
    # Health indicators (with defaults)
    hypertension_status = map_hypertension(raw_row.get('self_hypertension_status', 0))
    mother_gdm_during_index_pregnancy = map_yes_no_unsure(raw_row.get('mother_gdm_during_index_pregnancy', 0))
    
    # Note: Smoking, alcohol, sleep, stress not in survey - removed to avoid constant features
    
    # Family history - sibling and aunt/uncle data
    siblings_t2dm_count = safe_count(raw_row.get('siblings_t2dm_count_raw', 0))
    # Binary: any sibling with T2DM vs none (counts still in siblings_diabetes_count)
    siblings_score = 1.0 if siblings_t2dm_count > 0 else 0.0
    
    paternal_aunts_uncles_t2dm = safe_count(raw_row.get('paternal_aunts_uncles_t2dm_count_raw', 0))
    maternal_aunts_uncles_t2dm = safe_count(raw_row.get('maternal_aunts_uncles_t2dm_count_raw', 0))
    aunts_uncles_diabetes_count = paternal_aunts_uncles_t2dm + maternal_aunts_uncles_t2dm
    aunts_uncles_score = 1.0 if aunts_uncles_diabetes_count > 0 else 0.0
    
    # Grandparent family history
    paternal_grandfather_t2dm = map_count_to_status(raw_row.get('paternal_grandfather_t2dm_count_raw', 0))
    paternal_grandmother_t2dm = map_count_to_status(raw_row.get('paternal_grandmother_t2dm_count_raw', 0))
    maternal_grandfather_t2dm = map_count_to_status(raw_row.get('maternal_grandfather_t2dm_count_raw', 0))
    maternal_grandmother_t2dm = map_count_to_status(raw_row.get('maternal_grandmother_t2dm_count_raw', 0))
    
    # Parent family history
    father_t2dm = map_count_to_status(raw_row.get('father_t2dm_count_raw', 0))
    mother_t2dm = map_count_to_status(raw_row.get('mother_t2dm_count_raw', 0))
    
    # Parent history must come from family lineage (not respondent diagnosis).
    parent_has_t2dm = max(father_t2dm, mother_t2dm)

    def _score_to_family_status(v: float) -> str:
        if v >= 1.0 - 1e-9:
            return "yes"
        if v <= 0.0 + 1e-9:
            return "no"
        return "unknown"

    family_history_graph = {
        "maternalGrandmother": _score_to_family_status(maternal_grandmother_t2dm),
        "maternalGrandfather": _score_to_family_status(maternal_grandfather_t2dm),
        "paternalGrandmother": _score_to_family_status(paternal_grandmother_t2dm),
        "paternalGrandfather": _score_to_family_status(paternal_grandfather_t2dm),
        "mother": _score_to_family_status(mother_t2dm),
        "father": _score_to_family_status(father_t2dm),
    }
    extended_lineage_diabetes = int(siblings_t2dm_count) + int(aunts_uncles_diabetes_count)
    lineage_metrics = derive_family_metrics(
        family_history_graph,
        extended_diabetes_count=extended_lineage_diabetes,
    )
    weighted_family_score = lineage_metrics["weightedFamilyScore"]
    maternal_score = lineage_metrics["maternalScore"]
    paternal_score = lineage_metrics["paternalScore"]
    first_degree_yes_count = float(lineage_metrics["firstDegreeYesCount"])
    second_degree_yes_count = float(lineage_metrics["secondDegreeYesCount"])
    lineage_risk_index = lineage_metrics["lineageRiskIndex"]
    propagation_probability = float(lineage_metrics.get("propagationProbability", 0.0))

    # Diabetic relatives: tree positives (strict yes) plus sibling/aunt counts
    diabetic_relatives_count = (
        float(lineage_metrics["diabeticRelativesCount"])
        + float(siblings_t2dm_count)
        + float(aunts_uncles_diabetes_count)
    )

    # Interaction terms — same definitions as app/ml/feature_builder.py (training / inference parity)
    metabolic_risk_index = round(age * (bmi / 24.0), 4)
    hereditary_load_index = _compute_hereditary_load_index(
        float(parent_has_t2dm),
        int(lineage_metrics["firstDegreeYesCount"]),
        int(lineage_metrics["secondDegreeYesCount"]),
        float(lineage_metrics["weightedFamilyScore"]),
        float(siblings_t2dm_count),
        float(aunts_uncles_score),
    )
    activity_metabolic_index = round(
        float(physical_activity_score) * (1.0 + float(hypertension_status)),
        4,
    )
    
    inferred_outcome = 1 if map_yes_no_unsure(raw_row.get('patient_has_t2dm_status', 0)) >= 1.0 else 0
    raw_outcome = safe_int(raw_row.get("outcome", ""), fallback=-1)
    # outcome column (when present): 1 = T2DM, 0 = not, 99 = not sure (survey coding).
    # - Missing/empty outcome → infer from patient_has_t2dm_status (legacy / partial exports).
    # - 99 → label 0 for training (do not upgrade to positive from patient_has_t2dm; that caused
    #   outcome=99 + patient_has_t2dm=1 to count as positive against explicit "not sure" outcome).
    # - Never treat 99 as positive via ">= 1" (older bug).
    if raw_outcome < 0:
        final_outcome = inferred_outcome
    elif raw_outcome == 99:
        final_outcome = 0
    else:
        final_outcome = 1 if raw_outcome >= 1 else 0

    raw_spid = raw_row.get("source_patient_id")
    if raw_spid is not None and str(raw_spid).strip():
        source_patient_id = str(raw_spid).strip()
    else:
        source_patient_id = str(safe_int(raw_row.get("patient_id", 0), fallback=0))

    base_row = {
        'age': round(age, 2),
        'bmi': bmi,
        'user_is_male': user_is_male,
        'physical_activity_score': physical_activity_score,
        'diet_quality_score': diet_quality_score,
        'parent_has_t2dm': parent_has_t2dm,
        'hypertension_status': hypertension_status,
        'mother_gdm_during_index_pregnancy': mother_gdm_during_index_pregnancy,
        'siblings_score': siblings_score,
        'aunts_uncles_score': aunts_uncles_score,
        'siblings_diabetes_count': siblings_t2dm_count,
        'aunts_uncles_diabetes_count': aunts_uncles_diabetes_count,
        'weightedFamilyScore': weighted_family_score,
        'maternalScore': maternal_score,
        'paternalScore': paternal_score,
        'firstDegreeYesCount': int(first_degree_yes_count),
        'secondDegreeYesCount': int(second_degree_yes_count),
        'diabeticRelativesCount': diabetic_relatives_count,
        'lineageRiskIndex': lineage_risk_index,
        'propagationProbability': propagation_probability,
        'metabolic_risk_index': metabolic_risk_index,
        'hereditary_load_index': hereditary_load_index,
        'activity_metabolic_index': activity_metabolic_index,
        'outcome': final_outcome,
        'source_record_id': source_record_id,
        'source_patient_id': source_patient_id,
    }

    return base_row


def prepare_training_dataset(input_path: Path, output_path: Path):
    """Transform raw CSV to training dataset."""
    
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Read input CSV
    rows = []
    skip_reasons: Counter[str] = Counter()
    source_record_id = 0
    with input_path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            demo, reason = validate_and_parse_demographics(row)
            if demo is None:
                skip_reasons[reason or "unknown"] += 1
                continue
            source_record_id += 1
            transformed = transform_row(row, source_record_id=source_record_id, demo=demo)
            transformed['generation_depth'] = NEUTRAL_GENERATION_DEPTH
            transformed['target_is_male'] = NEUTRAL_TARGET_IS_MALE
            transformed['target_label'] = TARGET_LABEL
            rows.append(transformed)
    
    if not rows:
        raise ValueError(
            "No valid rows after cleaning. Check raw data and skip reasons: "
            + ", ".join(f"{k}={v}" for k, v in skip_reasons.most_common())
        )
    
    # Write output CSV — only columns actually computed (no ghost placeholders)
    fieldnames = [
        'age', 'bmi', 'user_is_male', 'physical_activity_score',
        'diet_quality_score', 'parent_has_t2dm',
        'hypertension_status', 'mother_gdm_during_index_pregnancy',
        'siblings_score', 'aunts_uncles_score', 'siblings_diabetes_count',
        'aunts_uncles_diabetes_count', 'weightedFamilyScore',
        'maternalScore', 'paternalScore', 'firstDegreeYesCount',
        'secondDegreeYesCount',
        'diabeticRelativesCount', 'lineageRiskIndex',
        'propagationProbability',
        'metabolic_risk_index', 'hereditary_load_index', 'activity_metabolic_index',
        'generation_depth', 'target_is_male', 'outcome',
        'source_record_id', 'source_patient_id', 'target_label'
    ]
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Prepared {len(rows)} respondent-level rows")
    if skip_reasons:
        total_skipped = sum(skip_reasons.values())
        print(f"Skipped {total_skipped} row(s) (validation); reasons:")
        for code, count in skip_reasons.most_common():
            print(f"  {code}: {count}")
    print(f"Training dataset saved to: {output_path}")
    print(f"Ready for training!")


if __name__ == "__main__":
    from dataset_paths import resolve_raw_survey_csv

    _datasets = Path(__file__).resolve().parents[1] / "ml" / "datasets"
    training_dataset = (
        Path(__file__).resolve().parents[1] / "ml" / "datasets" / "processed" / "training_dataset.csv"
    )
    try:
        raw_dataset = resolve_raw_survey_csv(_datasets)
    except FileNotFoundError as exc:
        print(str(exc))
        print(
            "\nTo train the existing processed CSV instead, from Backend run:\n"
            "  python train.py\n"
            "or:\n"
            "  python train.py --dataset ml/datasets/processed/training_dataset_filipino_488.csv"
        )
        raise SystemExit(1) from exc

    prepare_training_dataset(raw_dataset, training_dataset)
