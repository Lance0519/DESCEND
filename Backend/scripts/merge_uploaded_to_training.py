"""Merge an uploaded raw survey (Excel) into the processed training dataset.

Behavior:
- Locate an uploaded raw Excel in `backend/ml/datasets/raw/` (prefer Responses or merged file).
- Convert to a temporary CSV, normalize column names using the mapping CSV,
- Auto-generate `patient_id` values when missing (continuing after existing max),
- Run the existing `prepare_training_dataset` transform to produce processed rows,
- Append processed rows to `backend/ml/datasets/processed/training_dataset.csv`,
  ensuring `source_patient_id` and `source_record_id` remain unique and
  preserving any existing `source_patient_id` values 1..92.

Run this from the repo root: `python backend/scripts/merge_uploaded_to_training.py`
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
import csv
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ML_DATASETS = ROOT / "ml" / "datasets"
RAW_DIR = ML_DATASETS / "raw"
PROCESSED_DIR = ML_DATASETS / "processed"
TRAINING_CSV = PROCESSED_DIR / "training_dataset.csv"
MAPPING_CSV = RAW_DIR / "survey_to_excel_column_map.csv"


def find_raw_candidate() -> Path:
    # Prefer the 'Responses' workbook, else prefer merged, else pick any xlsx
    candidates = list(RAW_DIR.glob("*.xlsx")) + list(RAW_DIR.glob("*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No raw uploads found in {RAW_DIR}")
    for p in candidates:
        if "responses" in p.name.lower():
            return p
    for p in candidates:
        if "merged" in p.name.lower():
            return p
    return candidates[0]


def load_mapping() -> list[str]:
    if not MAPPING_CSV.exists():
        raise FileNotFoundError(f"Mapping CSV not found: {MAPPING_CSV}")
    rows = []
    with MAPPING_CSV.open('r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((r.get('survey_item','').strip(), r.get('column_name','').strip()))
    return rows


def normalize_columns(df: pd.DataFrame, mapping_rows: list[tuple[str,str]]) -> pd.DataFrame:
    # Try to rename columns: match survey_item or column_name to existing df columns (case-insensitive)
    rename = {}
    lc_cols = {c.lower().strip(): c for c in df.columns}
    for survey_item, column_name in mapping_rows:
        if not column_name:
            continue
        target = column_name
        # exact match by column_name
        key = target.lower()
        if key in lc_cols:
            rename[lc_cols[key]] = target
            continue
        # match by survey_item text if present in any column
        s = survey_item.lower()
        matched = None
        for col_lc, orig in lc_cols.items():
            if s and s == col_lc:
                matched = orig
                break
        if matched:
            rename[matched] = target
            continue
        # substring fallback
        for col_lc, orig in lc_cols.items():
            if s and s in col_lc:
                rename[orig] = target
                break
        # numeric question fallback: if survey_item contains a number like 'Q2' or '2',
        # try to match header containing '2.' or ' 2.' which is common in form exports
        import re
        num_match = re.search(r"(\d+)", survey_item)
        if num_match:
            q = num_match.group(1)
            for col_lc, orig in lc_cols.items():
                if f"{q}." in col_lc or f" {q}." in col_lc or f"q{q}" in col_lc:
                    rename[orig] = target
                    break

    if rename:
        df = df.rename(columns=rename)
    return df


def main():
    print("Merging uploaded raw into training dataset...")
    candidate = find_raw_candidate()
    print(f"Using raw file: {candidate}")

    mapping_rows = load_mapping()

    # Read candidate (Excel or CSV)
    if candidate.suffix.lower() in {'.xlsx', '.xls'}:
        df = pd.read_excel(candidate)
    else:
        df = pd.read_csv(candidate)

    print(f"Loaded {len(df)} rows from raw upload")

    df = normalize_columns(df, mapping_rows)

    # Ensure patient_id exists — if missing or invalid, generate new ones starting after existing max
    if TRAINING_CSV.exists():
        existing = pd.read_csv(TRAINING_CSV)
        max_pid = int(existing['source_patient_id'].max()) if 'source_patient_id' in existing.columns else 0
    else:
        max_pid = 0

    if 'patient_id' not in df.columns:
        start = max_pid + 1
        df['patient_id'] = list(range(start, start + len(df)))
        print(f"Assigned synthetic patient_id starting at {start}")
    else:
        # coerce non-numeric to NaN then fill
        df['patient_id'] = pd.to_numeric(df['patient_id'], errors='coerce')
        missing = df['patient_id'].isna()
        if missing.any():
            start = max_pid + 1
            nmissing = missing.sum()
            df.loc[missing, 'patient_id'] = range(start, start + nmissing)
            print(f"Filled {nmissing} missing patient_id values starting at {start}")

    # Write temp CSV for prepare script
    temp_input = RAW_DIR / "tmp_upload_for_prepare.csv"
    df.to_csv(temp_input, index=False)
    print(f"Wrote temp CSV for prepare: {temp_input}")

    # Load prepare_training_dataset module dynamically
    prepare_path = Path(__file__).resolve().parents[0] / "prepare_training_dataset.py"
    spec = importlib.util.spec_from_file_location("prepare_module", str(prepare_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    temp_processed = PROCESSED_DIR / "tmp_processed_fragment.csv"
    # Call the prepare function
    mod.prepare_training_dataset(temp_input, temp_processed)

    # Read processed fragment
    frag = pd.read_csv(temp_processed)
    print(f"Prepared fragment rows: {len(frag)}")

    # Append to training CSV with careful id assignment
    if TRAINING_CSV.exists():
        train = pd.read_csv(TRAINING_CSV)
    else:
        train = pd.DataFrame()

    # Determine current maxima
    existing_pids = set(train['source_patient_id'].astype(int).tolist()) if 'source_patient_id' in train.columns else set()
    max_pid = max(existing_pids) if existing_pids else 0
    max_rec = int(train['source_record_id'].max()) if 'source_record_id' in train.columns and not train.empty else 0

    assigned_new_pids = []
    new_rows = []
    for _, row in frag.iterrows():
        pid = int(row.get('source_patient_id', 0)) if 'source_patient_id' in row and not pd.isna(row.get('source_patient_id')) else int(row.get('source_patient_id', 0))
        # The prepare script sets 'source_patient_id' from patient_id; if that collides, assign new
        if pid in existing_pids or pid == 0:
            max_pid += 1
            pid = max_pid
        existing_pids.add(pid)
        max_rec += 1
        row['source_patient_id'] = int(pid)
        row['source_record_id'] = int(max_rec)
        new_rows.append(row)

    if new_rows:
        append_df = pd.DataFrame(new_rows)
        combined = pd.concat([train, append_df], ignore_index=True, sort=False)
    else:
        combined = train

    # Backup existing training CSV
    if TRAINING_CSV.exists():
        bak = TRAINING_CSV.with_name(TRAINING_CSV.stem + '_bak_for_merge.csv')
        TRAINING_CSV.rename(bak)
        print(f"Backed up training CSV to {bak}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(TRAINING_CSV, index=False)
    print(f"Merged {len(new_rows)} rows. Training dataset now has {len(combined)} rows.")


if __name__ == '__main__':
    main()
