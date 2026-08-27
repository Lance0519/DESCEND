"""Convert merged raw survey CSV into respondent-level training_dataset.csv.

Usage:
    python scripts/clean_raw_to_training.py

Optional:
    python scripts/clean_raw_to_training.py --raw path/to/raw.csv --out path/to/training.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

from dataset_paths import resolve_raw_survey_csv
from prepare_training_dataset import prepare_training_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Clean and transform raw merged survey data into respondent-level model training format."
    )
    parser.add_argument(
        "--raw",
        type=Path,
        default=None,
        help="Path to raw survey CSV (default: DESCEND Google Form export, else merged internal CSV)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Path to output training CSV (default: backend/ml/datasets/processed/training_dataset.csv)",
    )

    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    datasets_dir = backend_dir / "ml" / "datasets"
    raw_path = args.raw or resolve_raw_survey_csv(datasets_dir)
    out_path = args.out or (datasets_dir / "processed" / "training_dataset.csv")

    print("\n" + "=" * 70)
    print("RAW TO TRAINING DATASET CLEANER")
    print("=" * 70)
    print(f"Raw input:  {raw_path}")
    print(f"Output:     {out_path}")

    prepare_training_dataset(raw_path, out_path)

    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
