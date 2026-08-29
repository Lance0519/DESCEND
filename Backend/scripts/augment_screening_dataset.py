"""Build a screening-oriented training export from the DESCEND Google Form CSV.

1. Copy the original 900-row export.
2. Add noise to ~18% of those rows (inconsistent family answers, more blank labs,
   some high-risk profiles with low activity) so uniformly complete synthetic-like
   rows do not dominate.
3. Append 180 labeled boundary cases matching the hold-out false-negative profiles.
4. Write `DESCEND RAW SURVEY augmented.csv` and rebuild `training_dataset.csv`.

The original `DESCEND RAW SURVEY.csv` and `training_dataset_descend_900.csv` are not overwritten.

Usage (from Backend):
    python scripts/augment_screening_dataset.py
"""

from __future__ import annotations

import csv
import json
import random
import sys
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_BACKEND_ROOT = _SCRIPT_DIR.parent
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dataset_paths import AUGMENTED_GFORM_NAME, GFORM_RAW_NAME
from prepare_training_dataset import prepare_training_dataset

FAMILY_STATUS_COLS = [
    "Does your father have Type 2 diabetes?",
    "Does your mother have Type 2 diabetes?",
    "Does your sibling have Type 2 diabetes?",
    "Does your maternal grandfather have Type 2 diabetes?",
    "Does your maternal grandmother have Type 2 diabetes?",
    "Does your paternal grandfather have Type 2 diabetes?",
    "Does your paternal grandmother have Type 2 diabetes?",
]
GLUCOSE_COL = "If you know it, what is your fasting blood glucose (mg/dL)? (optional)"
HBA1C_COL = "If you know it, what is your HbA1c (%)?  (optional)"
ACTIVITY_LEVEL_COL = "How would you describe your usual physical activity level?"
EXERCISE_FREQ_COL = "How often do you exercise in a typical week?"
DIAGNOSIS_COL = "Has a doctor diagnosed you with Type 2 diabetes?"
DIAGNOSIS_AGE_COL = "At what age were you diagnosed?"
HYPERTENSION_COL = "Have you been told you have hypertension (high blood pressure)?"
SEX_COL = "What is your sex?"
AGE_COL = "What is your age?"
HEIGHT_COL = "What is your height in centimeters?"
WEIGHT_COL = "What is your weight in kilograms?"
FATHER_COL = "Does your father have Type 2 diabetes?"
MOTHER_COL = "Does your mother have Type 2 diabetes?"
FATHER_DX_COL = "At what age was your father diagnosed?"
MOTHER_DX_COL = "At what age was your mother diagnosed?"
GP_STATUS = [
    "Does your maternal grandfather have Type 2 diabetes?",
    "Does your maternal grandmother have Type 2 diabetes?",
    "Does your paternal grandfather have Type 2 diabetes?",
    "Does your paternal grandmother have Type 2 diabetes?",
]
GP_AGE = [
    "At what age was your maternal grandfather diagnosed?",
    "At what age was your maternal grandmother diagnosed?",
    "At what age was your paternal grandfather diagnosed?",
    "At what age was your paternal grandmother diagnosed?",
]

NOISE_FRACTION = 0.18
BOUNDARY_PER_PROFILE = 60
RNG_SEED = 42


def _flip_status(value: str, rng: random.Random) -> str:
    text = (value or "").strip()
    if text.startswith("Yes"):
        return rng.choice(["No", "I'm not sure"])
    if text.startswith("No"):
        return rng.choice(["Yes", "I'm not sure"])
    return rng.choice(["Yes", "No"])


def apply_noise(rows: list[dict], rng: random.Random) -> tuple[list[dict], list[int]]:
    """Perturb a fraction of rows in place; return noised copy and 1-based source indices."""
    out = [deepcopy(row) for row in rows]
    n = max(1, int(round(len(out) * NOISE_FRACTION)))
    indices = list(range(len(out)))
    rng.shuffle(indices)
    chosen = sorted(indices[:n])
    for i in chosen:
        row = out[i]
        col = rng.choice(FAMILY_STATUS_COLS)
        row[col] = _flip_status(row.get(col, "No"), rng)
        if rng.random() < 0.55:
            row[GLUCOSE_COL] = ""
            row[HBA1C_COL] = ""
        high_risk = row.get(DIAGNOSIS_COL) == "Yes" or row.get(FATHER_COL) == "Yes" or row.get(MOTHER_COL) == "Yes"
        if high_risk and rng.random() < 0.45:
            row[EXERCISE_FREQ_COL] = "Never"
            row[ACTIVITY_LEVEL_COL] = "Sedentary (little or no exercise)"
    return out, [i + 1 for i in chosen]


def _base_row(template: dict, rng: random.Random, when: datetime) -> dict:
    row = {key: "" for key in template}
    row["Timestamp"] = when.strftime("%m/%d/%Y %H:%M:%S")
    row["Do you agree to participate in this study?"] = "I agree"
    row[DIAGNOSIS_COL] = "Yes"
    row[HYPERTENSION_COL] = "No"
    row[ACTIVITY_LEVEL_COL] = "Lightly active (light exercise 1-3 days/week)"
    row[EXERCISE_FREQ_COL] = "Once a week"
    row["How long is a typical exercise session?"] = "15-30 minutes"
    row["How often do you drink sugary drinks?"] = "Sometimes (a few times a month)"
    row["How often do you eat fast food?"] = "Rarely (once a month or less)"
    row["What is your smoking status?"] = "Never smoked"
    row["How would you describe your alcohol consumption?"] = "I do not drink alcohol"
    row["How many hours do you usually sleep per night?"] = "6-7 hours"
    for col in FAMILY_STATUS_COLS:
        row[col] = "No"
    row["How many maternal uncles have Type 2 diabetes?"] = "0"
    row["How many maternal aunts have Type 2 diabetes?"] = "0"
    row["How many paternal uncles have Type 2 diabetes?"] = "0"
    row["How many paternal aunts have Type 2 diabetes?"] = "0"
    row[GLUCOSE_COL] = ""
    row[HBA1C_COL] = ""
    return row


def _set_bmi(row: dict, rng: random.Random, *, female: bool, bmi_lo: float, bmi_hi: float) -> None:
    height = rng.randint(150, 168) if female else rng.randint(160, 176)
    bmi = rng.uniform(bmi_lo, bmi_hi)
    weight = round(bmi * (height / 100.0) ** 2, 1)
    row[HEIGHT_COL] = str(height)
    row[WEIGHT_COL] = str(weight)


def build_boundary_rows(template: dict, start: datetime, rng: random.Random) -> list[dict]:
    rows: list[dict] = []
    clock = start

    for i in range(BOUNDARY_PER_PROFILE):
        clock += timedelta(minutes=3)
        row = _base_row(template, rng, clock)
        female = i % 2 == 0
        row[SEX_COL] = "Female" if female else "Male"
        age = rng.randint(40, 55)
        row[AGE_COL] = str(age)
        row[DIAGNOSIS_AGE_COL] = str(max(28, age - rng.randint(2, 8)))
        _set_bmi(row, rng, female=female, bmi_lo=19.0, bmi_hi=24.4)
        if i % 2 == 0:
            row[FATHER_COL] = "Yes"
            row[FATHER_DX_COL] = str(rng.randint(45, 62))
        else:
            row[MOTHER_COL] = "Yes"
            row[MOTHER_DX_COL] = str(rng.randint(42, 60))
        rows.append(row)

    for i in range(BOUNDARY_PER_PROFILE):
        clock += timedelta(minutes=3)
        row = _base_row(template, rng, clock)
        female = i % 2 == 1
        row[SEX_COL] = "Female" if female else "Male"
        age = rng.randint(55, 65)
        row[AGE_COL] = str(age)
        row[DIAGNOSIS_AGE_COL] = str(max(40, age - rng.randint(1, 6)))
        _set_bmi(row, rng, female=female, bmi_lo=20.0, bmi_hi=26.5)
        n_gp = 4 if i % 3 == 0 else 3
        chosen = list(range(4))
        rng.shuffle(chosen)
        for gp_i in chosen[:n_gp]:
            row[GP_STATUS[gp_i]] = "Yes"
            row[GP_AGE[gp_i]] = str(rng.randint(48, 72))
        rows.append(row)

    for i in range(BOUNDARY_PER_PROFILE):
        clock += timedelta(minutes=3)
        row = _base_row(template, rng, clock)
        row[SEX_COL] = "Female"
        age = rng.randint(22, 35)
        row[AGE_COL] = str(age)
        row[DIAGNOSIS_AGE_COL] = str(max(20, age - rng.randint(1, 4)))
        _set_bmi(row, rng, female=True, bmi_lo=19.5, bmi_hi=24.8)
        row[MOTHER_COL] = "Yes"
        row[MOTHER_DX_COL] = str(rng.randint(28, 40))
        rows.append(row)

    return rows


def main() -> int:
    rng = random.Random(RNG_SEED)
    datasets = _BACKEND_ROOT / "ml" / "datasets"
    raw_dir = datasets / "raw"
    source = raw_dir / GFORM_RAW_NAME
    out_raw = raw_dir / AUGMENTED_GFORM_NAME
    out_train = datasets / "processed" / "training_dataset.csv"
    manifest_path = datasets / "processed" / "screening_augmentation_manifest.json"

    if not source.exists():
        print(f"ERROR: missing {source}")
        return 1

    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        original = list(reader)

    noisy, noised_ids = apply_noise(original, rng)
    last_ts = datetime.strptime(original[-1]["Timestamp"].strip(), "%m/%d/%Y %H:%M:%S")
    boundary = build_boundary_rows(original[0], last_ts + timedelta(days=1), rng)
    combined = noisy + boundary

    out_raw.parent.mkdir(parents=True, exist_ok=True)
    with out_raw.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(combined)

    prepare_training_dataset(out_raw, out_train)

    manifest = {
        "seed": RNG_SEED,
        "originalRows": len(original),
        "noiseFraction": NOISE_FRACTION,
        "noisedOriginalRowNumbers": noised_ids,
        "noisedCount": len(noised_ids),
        "boundaryRows": {
            "midAgeSingleParentNormalBmi": BOUNDARY_PER_PROFILE,
            "olderGrandparentHeavyNoParent": BOUNDARY_PER_PROFILE,
            "youngFemaleMotherT2dm": BOUNDARY_PER_PROFILE,
            "total": len(boundary),
            "allLabeledOutcome": 1,
        },
        "combinedRawRows": len(combined),
        "rawOutput": str(out_raw.as_posix()),
        "trainingOutput": str(out_train.as_posix()),
        "notes": [
            "Original DESCEND RAW SURVEY.csv is unchanged.",
            "This repository does not contain a documented 520-row real + 900-row generated split; noise is applied to the 900-row Google Form export.",
            "Young-female boundary rows include mother T2DM. Mother GDM is not an ExtraTrees feature (constant/unknown on the form), so those rows teach first-degree maternal risk in young women rather than a GDM coefficient.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {len(combined)} raw rows -> {out_raw}")
    print(f"Noised {len(noised_ids)} of {len(original)} original rows ({NOISE_FRACTION:.0%})")
    print(f"Appended {len(boundary)} labeled boundary cases")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
