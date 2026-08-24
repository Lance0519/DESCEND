"""
Single canonical training entry point for T2DM risk prediction model.

Works standalone (no Flask context required). Calls the modeling module
directly via importlib to avoid Flask app factory side-effects.

Usage:
    python train.py
    python train.py --dataset ml/datasets/processed/training_dataset.csv
    python train.py --dataset ml/datasets/processed/training_dataset_filipino_488.csv
    python train.py --dataset path/to/dataset.csv --model path/to/model.json --seed 42
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))


def _load_modeling_module():
    module_path = backend_dir / "descend" / "ml" / "modeling.py"
    spec = importlib.util.spec_from_file_location("t2dm_modeling", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load modeling module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Full metric keys for hold-out and algorithm comparison tables
CV_KEYS_PCT = [
    "accuracy",
    "precision",
    "recall",
    "f1Score",
    "specificity",
    "rocAuc",
    "prAuc",
]

# Console table: emphasis on discrimination + calibration; accuracy last (prevalence-sensitive)
CV_KEYS_PRINT = [
    "rocAuc",
    "prAuc",
    "brierScore",
    "recall",
    "f1Score",
    "precision",
    "specificity",
    "accuracy",
]


def _run_training(modeling, dataset_path: Path, model_path: Path, seed: int, balance_mode: str, args) -> dict:
    artifact = modeling.train_model_from_dataset_path(
        dataset_path,
        model_path,
        seed=seed,
        balance_mode=balance_mode,
        threshold_strategy=args.threshold_strategy,
        min_recall_floor=args.min_recall,
        min_precision_floor=args.min_precision,
        cv_repeats=args.cv_repeats,
        tune_hyperparams=args.tune_hyperparams,
        model_algorithm="extra_trees",
        compare_algorithms=False,
    )

    metadata = artifact.get("metadata", {})
    metrics = metadata.get("cvMetrics") or metadata.get("metrics") or {}
    metrics_std = metadata.get("cvMetricsStd") or metadata.get("metricsStd") or {}
    warnings = metadata.get("datasetWarnings", [])

    print("\n" + "=" * 60)
    print("MODEL TRAINED SUCCESSFULLY")
    print("=" * 60)

    dataset_profile = metadata.get("datasetProfile", {})
    print(f"\nDataset Statistics:")
    print(f"  Total rows: {metadata.get('datasetRows', 'N/A')}")
    print(f"  Training balance mode: {metadata.get('trainingBalanceMode', balance_mode)}")
    if dataset_profile:
        class_counts = dataset_profile.get("classCounts", {})
        print(f"  Positive (T2DM): {class_counts.get('positive', 'N/A')}")
        print(f"  Negative (no T2DM): {class_counts.get('negative', 'N/A')}")
        print(f"  Positive rate: {dataset_profile.get('positiveRate', 0):.1%}")
        print(f"  Balance: {dataset_profile.get('balance', 'N/A')}")
    print(f"  Evaluation: {metadata.get('evaluationMethod', 'N/A')}  |  CV repeats: {metadata.get('cvRepeats', 1)}")
    if metadata.get("hyperparameterTuning", {}).get("enabled"):
        print(f"  Hyperparameter tuning: inner 3-fold PR-AUC — {metadata['hyperparameterTuning'].get('selectedOverrides')}")
    algo = metadata.get("modelAlgorithm") or artifact.get("modelAlgorithm")
    if algo:
        print(f"  Model algorithm: {algo}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"  - {warning}")

    if metrics:
        print(f"\nCross-validation (mean ± std; see model JSON for fold CIs & full metrics):")
        for key in CV_KEYS_PRINT:
            if key not in metrics:
                continue
            mean_val = metrics.get(key, 0)
            std_val = metrics_std.get(key, 0)
            if key == "brierScore":
                print(
                    f"  {key:<14} {mean_val:.4f} ± {std_val:.4f}  (lower is better)"
                )
            else:
                print(f"  {key:<14} {mean_val:.2%} ± {std_val:.2%}")

    holdout = metadata.get("holdoutMetrics", {})
    test_metrics = holdout.get("testMetrics", {})
    if test_metrics:
        print(f"\nHold-out (locked test set, train-optimized threshold):")
        for key in CV_KEYS_PRINT:
            if key not in test_metrics:
                continue
            val = test_metrics.get(key, 0)
            if key == "brierScore":
                print(f"  {key:<14} {val:.4f}  (lower is better)")
            else:
                print(f"  {key:<14} {val:.2%}")
        cm = (holdout.get("testConfusionMatrix") or {}).get("matrix")
        if cm and len(cm) == 2:
            print(f"  Confusion [[TN, FP], [FN, TP]]: {cm}")

    scoring = metadata.get("cvScoringConfig") or metadata.get("scoringConfig") or {}
    if scoring:
        print(f"\nThreshold (from training / OOF only; see metadata.thresholdStrategy):")
        thr = scoring.get("optimalThreshold", scoring.get("threshold", 0.5))
        print(f"  Operating cutoff: {float(thr):.4f}")
    cal = metadata.get("probabilityCalibration")
    if isinstance(cal, dict) and cal.get("deploymentPipeline"):
        print(f"\nCalibration: {cal['deploymentPipeline']}")

    comp = metadata.get("algorithmComparison")
    if isinstance(comp, dict) and comp.get("alternateCvMeanMetrics"):
        print("\nAlgorithm comparison (CV means; details in metadata):")
        print(f"  {comp.get('primaryAlgorithm')} vs {comp.get('alternateAlgorithm')}")
        pm, am = comp.get("primaryCvMeanMetrics") or {}, comp.get("alternateCvMeanMetrics") or {}
        for key in ("rocAuc", "prAuc", "brierScore", "f1Score", "recall"):
            if key in pm and key in am:
                print(f"    {key:<12} {pm[key]:.4f}  |  {am[key]:.4f}")

    top_feats = metadata.get("topFeaturesRanked") or metadata.get("topFeatures", [])
    if top_feats:
        print(f"\nTop Features (by importance):")
        for i, feature in enumerate(top_feats, 1):
            if isinstance(feature, (list, tuple)):
                print(f"  {i}. {feature[0]}: {feature[1]:.6f}")
            elif isinstance(feature, dict):
                print(f"  {i}. {feature['feature']}: {feature.get('coefficient', feature.get('importance', 0)):.6f}")

    leakage = metadata.get("leakageChecks", {})
    if leakage:
        shuffle = leakage.get("labelShuffleCheck", {})
        print(
            f"\nSanity: label-shuffle {shuffle.get('status', 'n/a')} "
            f"(mean ROC-AUC ~{shuffle.get('meanRocAuc', 'n/a')})"
        )

    print(f"\nModel saved to: {model_path}")
    print("=" * 60)
    return artifact


def _print_balance_comparison(results_by_mode: dict[str, dict]) -> None:
    print("\n" + "=" * 60)
    print("BALANCE MODE COMPARISON")
    print("=" * 60)

    metric_specs = [
        ("cvMetrics", "Cross-validation", "rocAuc", "ROC-AUC"),
        ("cvMetrics", "Cross-validation", "prAuc", "PR-AUC"),
        ("cvMetrics", "Cross-validation", "f1Score", "F1"),
        ("cvMetrics", "Cross-validation", "recall", "Recall"),
        ("cvMetrics", "Cross-validation", "specificity", "Specificity"),
        ("holdoutMetrics.testMetrics", "Hold-out", "rocAuc", "ROC-AUC"),
        ("holdoutMetrics.testMetrics", "Hold-out", "prAuc", "PR-AUC"),
        ("holdoutMetrics.testMetrics", "Hold-out", "f1Score", "F1"),
        ("holdoutMetrics.testMetrics", "Hold-out", "recall", "Recall"),
        ("holdoutMetrics.testMetrics", "Hold-out", "brierScore", "Brier"),
    ]

    def read_path(metadata: dict, dotted_path: str):
        value = metadata
        for part in dotted_path.split("."):
            value = value.get(part, {}) if isinstance(value, dict) else {}
        return value

    for dotted_path, section_label, metric_key, metric_label in metric_specs:
        none_meta = results_by_mode["none"].get("metadata", {})
        over_meta = results_by_mode["oversample"].get("metadata", {})
        none_metrics = read_path(none_meta, dotted_path)
        over_metrics = read_path(over_meta, dotted_path)
        none_val = float(none_metrics.get(metric_key, 0.0))
        over_val = float(over_metrics.get(metric_key, 0.0))
        delta = over_val - none_val
        suffix = "" if metric_key == "brierScore" else "%"
        if suffix:
            print(
                f"  {section_label:<17} {metric_label:<12} "
                f"none={none_val:.2%}  oversample={over_val:.2%}  delta={delta:+.2%}"
            )
        else:
            print(
                f"  {section_label:<17} {metric_label:<12} "
                f"none={none_val:.4f}  oversample={over_val:.4f}  delta={delta:+.4f}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train T2DM risk prediction model from dataset"
    )
    parser.add_argument(
        "--dataset", type=Path, default=None,
        help="Path to training dataset CSV (default: ml/datasets/processed/training_dataset.csv)",
    )
    parser.add_argument(
        "--model", type=Path, default=None,
        help="Output model JSON path (default: ml/models/t2dm_risk_model.json)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--balance",
        choices=("none", "oversample"),
        default="none",
        help=(
            "Class balancing for training fits: 'none' uses sklearn class_weight=balanced only; "
            "'oversample' randomly duplicates minority-class rows until 50/50 inside each train fit "
            "(CV, holdout training split, final model). Test/eval rows stay unmodified."
        ),
    )
    parser.add_argument(
        "--compare-balance",
        action="store_true",
        help=(
            "Train both balance modes ('none' and 'oversample') and print a side-by-side "
            "metric comparison so you can choose the better option for this dataset."
        ),
    )
    parser.add_argument(
        "--threshold-strategy",
        choices=("f1", "recall_constrained"),
        default="f1",
        help=(
            "f1: maximize F1 on train fold within a bounded threshold range. "
            "recall_constrained: require recall >= --min-recall (relaxing --min-precision if needed), "
            "then maximize F1; uses a wider probability search band for screening-oriented points."
        ),
    )
    parser.add_argument(
        "--min-recall",
        type=float,
        default=0.65,
        help="Minimum recall floor when --threshold-strategy recall_constrained (default: 0.65).",
    )
    parser.add_argument(
        "--min-precision",
        type=float,
        default=0.25,
        help="Initial minimum precision when recall_constrained; relaxed in steps if infeasible (default: 0.25).",
    )
    parser.add_argument(
        "--cv-repeats",
        type=int,
        default=1,
        help="Repeat grouped stratified CV this many times (different shuffle seeds) to stabilize mean/std reporting.",
    )
    parser.add_argument(
        "--tune-hyperparams",
        action="store_true",
        help="Run inner 3-fold CV grid on max_depth and min_samples_leaf (PR-AUC) before final training.",
    )
    args = parser.parse_args()

    dataset_path = (args.dataset or backend_dir / "ml" / "datasets" / "processed" / "training_dataset.csv").absolute()
    model_path = (args.model or backend_dir / "ml" / "models" / "t2dm_risk_model.json").absolute()

    if not dataset_path.exists():
        print(f"ERROR: Dataset not found: {dataset_path}")
        return 1

    model_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Training model from: {dataset_path}")
    print(f"Model will be saved to: {model_path}")

    try:
        modeling = _load_modeling_module()
        if args.compare_balance:
            results_by_mode: dict[str, dict] = {}
            for balance_mode in ("none", "oversample"):
                compare_model_path = model_path.with_name(
                    f"{model_path.stem}_{balance_mode}{model_path.suffix}"
                )
                print(f"\n{'#' * 60}")
                print(f"Training run for balance mode: {balance_mode}")
                print(f"{'#' * 60}")
                results_by_mode[balance_mode] = _run_training(
                    modeling, dataset_path, compare_model_path, args.seed, balance_mode, args
                )
            _print_balance_comparison(results_by_mode)
        else:
            _run_training(modeling, dataset_path, model_path, args.seed, args.balance, args)
        return 0

    except Exception as e:
        print(f"ERROR: Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
