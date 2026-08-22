"""Print side-by-side CV and holdout metrics for ExtraTrees vs HistGradientBoosting."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from descend.ml.modeling import (
    TEST_SET_SIZE,
    compute_crossvalidation_metrics,
    compute_holdout_metrics,
    read_dataset_rows,
    stratified_group_holdout_split,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("ml/datasets/processed/training_dataset.csv"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()

    dataset_path = (
        args.dataset if args.dataset.is_absolute() else _backend / args.dataset
    )
    rows, group_src = read_dataset_rows(dataset_path.resolve())
    train_rows, test_rows = stratified_group_holdout_split(
        rows, test_size=TEST_SET_SIZE, seed=args.seed
    )

    keys = [
        "accuracy",
        "precision",
        "recall",
        "f1Score",
        "specificity",
        "rocAuc",
        "prAuc",
        "brierScore",
    ]

    out: dict[str, dict] = {}
    for algo in ("extra_trees", "hist_gradient_boosting"):
        cv = compute_crossvalidation_metrics(
            rows, k=args.k, seed=args.seed, model_algorithm=algo
        )
        ho = compute_holdout_metrics(
            train_rows, test_rows, seed=args.seed, model_algorithm=algo
        )
        out[algo] = {
            "cv_mean": cv["meanMetrics"],
            "cv_std": cv["stdMetrics"],
            "cv_thr": cv["scoringConfig"]["optimalThreshold"],
            "holdout": ho["testMetrics"],
            "holdout_thr": ho["optimizedThreshold"],
        }

    print(f"Dataset: {len(rows)} rows | grouping: {group_src}")
    print(
        f"Same StratifiedGroupKFold (k={args.k}, seed={args.seed}) + "
        f"same family holdout ({int(TEST_SET_SIZE * 100)}% test)\n"
    )

    w = 14
    line = (
        f"{'Metric':<{w}}"
        f"{'ET CV mean':>{w}}"
        f"{'HGB CV mean':>{w}}"
        f"{'ET holdout':>{w}}"
        f"{'HGB holdout':>{w}}"
    )
    print(line)
    print("-" * len(line))
    for key in keys:
        print(
            f"{key:<{w}}"
            f"{out['extra_trees']['cv_mean'][key]:>{w}.4f}"
            f"{out['hist_gradient_boosting']['cv_mean'][key]:>{w}.4f}"
            f"{out['extra_trees']['holdout'][key]:>{w}.4f}"
            f"{out['hist_gradient_boosting']['holdout'][key]:>{w}.4f}"
        )

    print("\nCV std (ExtraTrees / HistGradientBoosting):")
    for key in keys:
        s0 = out["extra_trees"]["cv_std"][key]
        s1 = out["hist_gradient_boosting"]["cv_std"][key]
        print(f"  {key:<14} {s0:.4f} / {s1:.4f}")

    print("\nOOF aggregated CV threshold (F1 strategy on train folds):")
    print(f"  ExtraTrees:           {out['extra_trees']['cv_thr']}")
    print(f"  HistGradientBoosting: {out['hist_gradient_boosting']['cv_thr']}")

    print("\nHoldout threshold (from train split, calibrated):")
    print(f"  ExtraTrees:           {out['extra_trees']['holdout_thr']}")
    print(f"  HistGradientBoosting: {out['hist_gradient_boosting']['holdout_thr']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
