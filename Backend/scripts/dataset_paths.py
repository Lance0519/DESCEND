"""Canonical locations for survey CSVs and sync from legacy duplicate paths."""

from __future__ import annotations

import shutil
from pathlib import Path

# Prefer merged export; template name kept as fallback for older workflows
RAW_MERGED_NAME = "survey_to_excel_raw_merged.csv"
TEMPLATE_GLOB_HINT = "survey_to_excel_raw_template - survey_to_excel_raw_template.csv"
GFORM_RAW_NAME = "DESCEND RAW SURVEY.csv"
# Current live Google Form export ("...(Responses)"). It already contains the
# earlier 900 responses plus the added missed-positive profiles.
RESPONSES_GFORM_NAME = "DESCEND RAW SURVEY (Responses).csv"


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


def _find_gform_raw(raw_dir: Path) -> Path | None:
    exact = raw_dir / GFORM_RAW_NAME
    if exact.exists():
        return exact
    for path in sorted(raw_dir.glob("*.csv")):
        name = path.name.lower()
        if "descend" in name and "raw" in name and "survey" in name:
            return path
    return None


def resolve_raw_survey_csv(datasets_dir: Path) -> Path:
    """Return the raw survey CSV to use for training prep.

    Preference: live Google Form "(Responses)" export, then the earlier DESCEND
    Google Form export, then merged internal CSV, then template.
    """
    sync_legacy_merged_into_raw(datasets_dir)
    raw_dir = datasets_dir / "raw"
    responses = raw_dir / RESPONSES_GFORM_NAME
    gform = _find_gform_raw(raw_dir)
    raw_merged = raw_dir / RAW_MERGED_NAME
    template = raw_dir / TEMPLATE_GLOB_HINT
    if responses.exists():
        return responses
    if gform is not None:
        return gform
    if raw_merged.exists():
        return raw_merged
    if template.exists():
        return template
    raise FileNotFoundError(
        "No raw survey CSV found. Expected one of:\n"
        f"  {responses}\n"
        f"  {raw_dir / GFORM_RAW_NAME}\n"
        f"  {raw_merged}\n"
        f"  {template}"
    )
