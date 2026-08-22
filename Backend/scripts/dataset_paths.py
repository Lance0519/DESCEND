"""Canonical locations for survey CSVs and sync from legacy duplicate paths."""

from __future__ import annotations

import shutil
from pathlib import Path

# Prefer merged export; template name kept as fallback for older workflows
RAW_MERGED_NAME = "survey_to_excel_raw_merged.csv"
TEMPLATE_GLOB_HINT = "survey_to_excel_raw_template - survey_to_excel_raw_template.csv"


def sync_legacy_merged_into_raw(datasets_dir: Path) -> None:
    """If ml/datasets/survey_to_excel_raw_merged.csv is newer than raw/, copy it into raw/.

    Many editors save the merged export next to older docs; the pipeline only reads
    ml/datasets/raw/. This keeps a single up-to-date file for prepare_training_dataset.
    """
    legacy = datasets_dir / RAW_MERGED_NAME
    raw_merged = datasets_dir / "raw" / RAW_MERGED_NAME
    if not legacy.exists():
        return
    if not raw_merged.exists() or legacy.stat().st_mtime > raw_merged.stat().st_mtime:
        raw_merged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy, raw_merged)
        print(
            f"  [dataset_paths] Synced newer '{RAW_MERGED_NAME}' to {raw_merged} "
            "(canonical raw path for the pipeline)."
        )


def resolve_raw_survey_csv(datasets_dir: Path) -> Path:
    """Return the raw survey CSV to use for training prep (merged preferred, then template)."""
    sync_legacy_merged_into_raw(datasets_dir)
    raw_merged = datasets_dir / "raw" / RAW_MERGED_NAME
    template = datasets_dir / "raw" / TEMPLATE_GLOB_HINT
    if raw_merged.exists():
        return raw_merged
    if template.exists():
        return template
    raise FileNotFoundError(
        f"No raw survey CSV found. Expected one of:\n  {raw_merged}\n  {template}"
    )
