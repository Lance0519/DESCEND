#!/usr/bin/env python3
"""
Automated end-to-end ML pipeline for T2DM risk prediction.

Steps:
  1. Prepare training dataset from raw survey CSV
  2. Profile dataset (class balance, missing values, feature stats)
  3. Train model with 5-fold grouped stratified cross-validation
  4. Validate on 20% group-based hold-out test set
  5. Run leakage diagnostics (label shuffle, cross-group duplicates)
  6. Export final model artifact + comprehensive evaluation report

Usage:
    cd backend
    .\\venv\\Scripts\\Activate.ps1
    python scripts/run_pipeline.py
    python scripts/run_pipeline.py --raw-csv ml/datasets/raw/survey_to_excel_raw_merged.csv
    python scripts/run_pipeline.py --training-csv ml/datasets/processed/training_dataset.csv --skip-prepare
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))
sys.path.insert(0, str(_backend_dir / "scripts"))

from dataset_paths import resolve_raw_survey_csv  # noqa: E402


def _hr(char: str = "=", width: int = 78) -> str:
    return char * width


def _section(title: str) -> None:
    print(f"\n{_hr()}")
    print(f"  {title}")
    print(_hr())


def _subsection(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


# Full classification metrics (Brier is on 0–1 scale, not a fraction accuracy)
FULL_METRIC_KEYS = [
    "accuracy",
    "precision",
    "recall",
    "f1Score",
    "specificity",
    "rocAuc",
    "prAuc",
    "brierScore",
]


def _metric_table(metrics: dict, std: dict | None = None, keys: list[str] | None = None) -> None:
    if keys is None:
        keys = FULL_METRIC_KEYS
    for key in keys:
        val = metrics.get(key, 0)
        if key == "brierScore":
            if std and key in std:
                print(f"  {key:<14} {val:.4f} +/- {std[key]:.4f}  (lower is better)")
            else:
                print(f"  {key:<14} {val:.4f}  (lower is better)")
            continue
        if std and key in std:
            print(f"  {key:<14} {val:.4f} +/- {std[key]:.4f}")
        else:
            print(f"  {key:<14} {val:.4f}")


def _confusion_matrix(matrix: list[list[int]]) -> None:
    print("                    Predicted Neg  Predicted Pos")
    print(f"  Actual Negative:  {matrix[0][0]:>12}  {matrix[0][1]:>13}")
    print(f"  Actual Positive:  {matrix[1][0]:>12}  {matrix[1][1]:>13}")


# ---------------------------------------------------------------------------
#  STEP 1: Prepare training dataset
# ---------------------------------------------------------------------------
def step_prepare(raw_csv: Path, training_csv: Path) -> int:
    _section("STEP 1: PREPARE TRAINING DATASET")
    print(f"  Raw CSV:      {raw_csv}")
    print(f"  Training CSV: {training_csv}")

    if not raw_csv.exists():
        print(f"  ERROR: Raw CSV not found at {raw_csv}")
        return 0

    from prepare_training_dataset import prepare_training_dataset
    prepare_training_dataset(raw_csv, training_csv)

    row_count = 0
    with training_csv.open("r", encoding="utf-8-sig") as f:
        row_count = sum(1 for _ in f) - 1
    print(f"  Result: {row_count} rows written")
    return row_count


# ---------------------------------------------------------------------------
#  STEP 2: Profile dataset
# ---------------------------------------------------------------------------
def step_profile(training_csv: Path) -> dict:
    _section("STEP 2: DATASET PROFILE")

    from descend.ml.modeling import (
        FEATURE_COLUMNS,
        GROUP_COLUMN,
        TARGET_COLUMN,
        read_dataset_rows,
    )

    rows, group_col = read_dataset_rows(training_csv)
    total = len(rows)
    pos = sum(1 for r in rows if int(r[TARGET_COLUMN]) == 1)
    neg = total - pos
    ratio = min(pos, neg) / max(pos, neg, 1)
    unique_groups = len({int(r[GROUP_COLUMN]) for r in rows})

    print(f"  Total rows:        {total}")
    print(f"  Positive (T2DM=1): {pos} ({pos / total:.1%})")
    print(f"  Negative (T2DM=0): {neg} ({neg / total:.1%})")
    print(f"  Balance ratio:     {ratio:.2f} {'(good)' if ratio >= 0.3 else '(imbalanced)'}")
    print(f"  Unique groups:     {unique_groups}")
    print(f"  Group column:      {group_col}")

    _subsection("Feature statistics:")
    print(f"  {'Feature':<30} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8}")
    print(f"  {'-' * 66}")
    for feat in FEATURE_COLUMNS:
        vals = [float(r[feat]) for r in rows]
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        std = var ** 0.5
        print(f"  {feat:<30} {mean:>8.3f} {std:>8.3f} {min(vals):>8.2f} {max(vals):>8.2f}")

    profile = {
        "total": total,
        "positive": pos,
        "negative": neg,
        "ratio": ratio,
        "groups": unique_groups,
        "rows": rows,
        "group_col": group_col,
    }
    return profile


# ---------------------------------------------------------------------------
#  STEP 3: Train with cross-validation
# ---------------------------------------------------------------------------
def step_train_cv(rows: list, seed: int) -> dict:
    _section("STEP 3: 5-FOLD GROUPED STRATIFIED CROSS-VALIDATION")

    from descend.ml.modeling import compute_crossvalidation_metrics

    cv = compute_crossvalidation_metrics(rows, k=5, seed=seed)

    print(f"  Effective folds: {cv['foldCount']}")
    _subsection("Mean metrics (+/- std):")
    _metric_table(cv["meanMetrics"], cv["stdMetrics"])

    _subsection("Optimal threshold:")
    scoring = cv["scoringConfig"]
    print(f"  Aggregated: {scoring['optimalThreshold']:.4f}")
    print(f"  Per-fold:   {scoring['perFoldThresholds']}")
    print(f"  Strategy:   {scoring['thresholdStrategy']}")

    _subsection("Per-fold breakdown:")
    print(
        f"  {'Fold':<6} {'Trn':<6} {'Ev':<6} {'Acc':>6} {'Pre':>6} {'Rec':>6} "
        f"{'F1':>6} {'Spe':>6} {'AUC':>6} {'PR':>6} {'Br':>6} {'Thr':>7}"
    )
    print(f"  {'-' * 86}")
    for fd in cv["foldDetails"]:
        m = fd["metrics"]
        print(
            f"  {fd['fold']:<6} {fd['trainSize']:<6} {fd['evalSize']:<6} "
            f"{m['accuracy']:>6.3f} {m['precision']:>6.3f} {m['recall']:>6.3f} "
            f"{m['f1Score']:>6.3f} {m.get('specificity', 0):>6.3f} {m['rocAuc']:>6.3f} "
            f"{m.get('prAuc', 0):>6.3f} {m.get('brierScore', 0):>6.3f} {fd['optimizedThreshold']:>7.3f}"
        )

    _subsection("Overfitting check (train - eval mean gap):")
    for key in FULL_METRIC_KEYS:
        if key == "brierScore":
            continue
        gap = cv["meanOverfitGap"][key]
        status = "OK" if abs(gap) <= 0.08 else "WARN"
        print(f"  {key:<14} gap={gap:>+.4f}  [{status}]")

    _subsection("Aggregated confusion matrix:")
    _confusion_matrix(cv["aggregateConfusionMatrix"]["matrix"])

    return cv


# ---------------------------------------------------------------------------
#  STEP 4: Hold-out test
# ---------------------------------------------------------------------------
def step_holdout(rows: list, seed: int) -> dict:
    _section("STEP 4: 20% HOLD-OUT TEST SET VALIDATION")

    from descend.ml.modeling import (
        compute_holdout_metrics,
        stratified_group_holdout_split,
        TEST_SET_SIZE,
    )

    train_rows, test_rows = stratified_group_holdout_split(rows, test_size=TEST_SET_SIZE, seed=seed)
    holdout = compute_holdout_metrics(train_rows, test_rows, seed=seed)

    print(f"  Train set: {holdout['trainSize']} rows")
    print(f"  Test set:  {holdout['testSize']} rows")
    print(f"  Threshold: {holdout['optimizedThreshold']:.4f}")

    _subsection("Test set metrics (F1-tuned threshold, calibrated pipeline):")
    _metric_table(holdout["testMetrics"])

    if holdout.get("testMetricsAtThreshold05"):
        _subsection("Test set metrics (threshold 0.5, reference):")
        _metric_table(holdout["testMetricsAtThreshold05"])

    _subsection("Test confusion matrix:")
    _confusion_matrix(holdout["testConfusionMatrix"]["matrix"])

    _subsection("Overfitting check (train - test gap):")
    for key in FULL_METRIC_KEYS:
        if key == "brierScore":
            continue
        gap = holdout["overfitGap"][key]
        status = "OK" if abs(gap) <= 0.08 else "WARN"
        print(f"  {key:<14} gap={gap:>+.4f}  [{status}]")

    return holdout


# ---------------------------------------------------------------------------
#  STEP 5: Leakage diagnostics
# ---------------------------------------------------------------------------
def step_leakage(rows: list, cv: dict, seed: int) -> dict:
    _section("STEP 5: LEAKAGE DIAGNOSTICS")

    from descend.ml.modeling import _detect_cross_group_duplicates, _run_label_shuffle_check

    dup = _detect_cross_group_duplicates(rows)
    print(f"  Cross-group duplicate signatures: {dup['duplicateSignaturesAcrossGroups']}")
    print(f"  Rows in duplicates:               {dup['rowsInCrossGroupDuplicateSignatures']}")

    shuffle = _run_label_shuffle_check(rows, k=cv["foldCount"], seed=seed)
    print(f"\n  Label shuffle test:")
    print(f"    Status:      {shuffle['status']}")
    print(f"    Mean ROC-AUC: {shuffle['meanRocAuc']:.4f} (expect < 0.65 for no leakage)")
    print(f"    Std ROC-AUC:  {shuffle['stdRocAuc']:.4f}")

    if shuffle["status"] == "ok":
        print("    PASSED: Model does not overfit to label patterns")
    else:
        print("    WARNING: Investigate potential label leakage")

    return {"duplicates": dup, "shuffle": shuffle}


# ---------------------------------------------------------------------------
#  STEP 6: Export final model
# ---------------------------------------------------------------------------
def step_export(rows: list, model_path: Path, seed: int) -> dict:
    _section("STEP 6: TRAIN FINAL MODEL & EXPORT")

    from descend.ml.modeling import build_trained_artifact, _build_training_pipeline, _build_xyg, FEATURE_COLUMNS
    import joblib

    artifact = build_trained_artifact(rows, seed=seed)

    features, labels, _ = _build_xyg(rows)
    pipeline = _build_training_pipeline(seed=seed)
    pipeline.fit(features, labels)

    pipeline_path = model_path.with_suffix(".joblib")
    joblib.dump(pipeline, pipeline_path)
    artifact.setdefault("metadata", {})["pipelinePath"] = str(pipeline_path)

    json_artifact = {k: v for k, v in artifact.items() if k != "_pipeline"}
    model_path.parent.mkdir(parents=True, exist_ok=True)
    model_path.write_text(json.dumps(json_artifact, indent=2), encoding="utf-8")

    meta = artifact["metadata"]
    print(f"  Model JSON:    {model_path}")
    print(f"  Pipeline:      {pipeline_path}")
    print(f"  Type:          {meta.get('modelType')}")
    print(f"  Dataset rows:  {meta.get('datasetRows')}")
    print(f"  Eval method:   {meta.get('evaluationMethod')}")
    print(f"  Eval status:   {meta.get('evaluationStatus')}")

    _subsection("Feature importances:")
    importances = meta.get("featureImportances", {})
    ranked = sorted(importances.items(), key=lambda x: abs(x[1]), reverse=True)
    for rank, (feat, imp) in enumerate(ranked, 1):
        bar = "#" * int(imp * 200)
        print(f"  {rank}. {feat:<30} {imp:.6f}  {bar}")

    return artifact


# ---------------------------------------------------------------------------
#  STEP 7: Summary report
# ---------------------------------------------------------------------------
def step_summary(cv: dict, holdout: dict, leakage: dict, profile: dict) -> None:
    _section("EVALUATION SUMMARY")

    checks = []
    cv_mean = cv["meanMetrics"]
    cv_std = cv["stdMetrics"]

    # Recall
    if cv_mean["recall"] >= 0.70:
        checks.append(("PASS", f"CV Recall {cv_mean['recall']:.2%} >= 70% target"))
    else:
        checks.append(("FAIL", f"CV Recall {cv_mean['recall']:.2%} < 70% target"))

    # ROC-AUC
    if cv_mean["rocAuc"] >= 0.70:
        checks.append(("PASS", f"CV ROC-AUC {cv_mean['rocAuc']:.2%} >= 70% target"))
    else:
        checks.append(("FAIL", f"CV ROC-AUC {cv_mean['rocAuc']:.2%} < 70% target"))

    # Stability
    if cv_std["f1Score"] <= 0.15:
        checks.append(("PASS", f"CV F1 std {cv_std['f1Score']:.2%} <= 15% (stable)"))
    else:
        checks.append(("WARN", f"CV F1 std {cv_std['f1Score']:.2%} > 15% (high variance)"))

    # Holdout generalization
    holdout_gap = abs(holdout["overfitGap"]["rocAuc"])
    if holdout_gap <= 0.08:
        checks.append(("PASS", f"Holdout ROC gap {holdout_gap:.2%} <= 8% (generalizes well)"))
    else:
        checks.append(("WARN", f"Holdout ROC gap {holdout_gap:.2%} > 8% (potential overfit)"))

    # Leakage
    if leakage["shuffle"]["status"] == "ok":
        checks.append(("PASS", "Label shuffle test passed (no leakage)"))
    else:
        checks.append(("FAIL", "Label shuffle test flagged potential leakage"))

    # Class balance
    if profile["ratio"] >= 0.3:
        checks.append(("PASS", f"Class balance ratio {profile['ratio']:.2f} (adequate)"))
    else:
        checks.append(("WARN", f"Class balance ratio {profile['ratio']:.2f} (imbalanced)"))

    for status, msg in checks:
        icon = {"PASS": "[OK]  ", "FAIL": "[FAIL]", "WARN": "[WARN]"}[status]
        print(f"  {icon} {msg}")

    passed = sum(1 for s, _ in checks if s == "PASS")
    total = len(checks)
    print(f"\n  Result: {passed}/{total} checks passed")

    if passed == total:
        print("  Verdict: MODEL IS THESIS-DEFENSIBLE")
    elif passed >= total - 1:
        print("  Verdict: MODEL IS ACCEPTABLE WITH NOTED LIMITATIONS")
    else:
        print("  Verdict: REVIEW FLAGGED ISSUES BEFORE DEFENSE")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description="Automated T2DM ML Pipeline")
    parser.add_argument("--raw-csv", type=Path, default=None,
                        help="Path to raw survey CSV (default: auto-detect)")
    parser.add_argument("--training-csv", type=Path, default=None,
                        help="Path to training dataset CSV (default: ml/datasets/processed/training_dataset.csv)")
    parser.add_argument("--model-path", type=Path, default=None,
                        help="Output model JSON path")
    parser.add_argument("--skip-prepare", action="store_true",
                        help="Skip step 1 (use existing training CSV)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    args = parser.parse_args()

    datasets_dir = _backend_dir / "ml" / "datasets"
    models_dir = _backend_dir / "ml" / "models"

    training_csv = args.training_csv or datasets_dir / "processed" / "training_dataset.csv"
    model_path = args.model_path or models_dir / "t2dm_risk_model.json"
    skip_prepare = args.skip_prepare

    if skip_prepare:
        raw_csv = args.raw_csv.resolve() if args.raw_csv else None
    elif args.raw_csv is None:
        try:
            raw_csv = resolve_raw_survey_csv(datasets_dir)
        except FileNotFoundError:
            if training_csv.exists():
                print(
                    "  Raw survey CSV not found. Using existing processed file:\n"
                    f"  {training_csv}"
                )
                skip_prepare = True
                raw_csv = None
            else:
                raise
    else:
        raw_csv = args.raw_csv.resolve()

    print(_hr("="))
    print("  T2DM RISK PREDICTION - AUTOMATED ML PIPELINE")
    print(f"  Seed: {args.seed}")
    print(_hr("="))

    start = time.time()

    # Step 1
    if not skip_prepare:
        if raw_csv is None:
            print("\n  ERROR: Raw CSV path is missing and --skip-prepare was not set.")
            return 1
        step_prepare(raw_csv, training_csv)
    else:
        print(f"\n  [SKIPPED] Step 1: Using existing training CSV: {training_csv}")

    if not training_csv.exists():
        print(f"\n  ERROR: Training CSV not found at {training_csv}")
        return 1

    # Step 2
    profile = step_profile(training_csv)
    rows = profile["rows"]

    # Step 3
    cv = step_train_cv(rows, args.seed)

    # Step 4
    holdout = step_holdout(rows, args.seed)

    # Step 5
    leakage = step_leakage(rows, cv, args.seed)

    # Step 6
    artifact = step_export(rows, model_path, args.seed)

    # Step 7
    step_summary(cv, holdout, leakage, profile)

    elapsed = time.time() - start
    _section("PIPELINE COMPLETE")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Model:      {model_path}")
    print(f"  Pipeline:   {model_path.with_suffix('.joblib')}")
    print(f"  Dataset:    {training_csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
