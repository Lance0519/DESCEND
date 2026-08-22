#!/usr/bin/env python3
"""
Full ML improvement experiment: train-only repeated CV, hold-out isolation, model comparison,
nested tuning on training split, threshold modes, subgroup/error summaries.

Reproduce:
    cd backend
    python scripts/run_ml_improvement_experiment.py
    python scripts/run_ml_improvement_experiment.py --seed 42 --training-csv ml/datasets/processed/training_dataset.csv
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from sklearn.model_selection import StratifiedKFold  # noqa: E402

from app.ml.modeling import (  # noqa: E402
    DEFAULT_RANDOM_SEED,
    FEATURE_COLUMNS_PRUNED_ABLATION,
    FEATURE_COLUMNS_WITH_EXPLICIT_INTERACTIONS,
    TEST_SET_SIZE,
    audit_split_grouping,
    calculate_metrics,
    compute_crossvalidation_metrics,
    compute_holdout_metrics,
    evaluate_stratified_subgroups,
    inner_cv_select_extra_trees_config,
    inner_cv_select_hgb_config,
    read_dataset_rows,
    select_operating_threshold,
    select_screening_threshold,
    stratified_group_holdout_split,
    summarize_uncertainty_codings,
    threshold_sweep_table,
    _build_base_classifier_pipeline,
    _build_calibrated_pipeline,
    _build_xyg,
    _resolved_et_config,
)


def _oof_scores_for_train(
    train_rows: list,
    *,
    k: int,
    seed: int,
    model_algorithm: str,
    et_config: dict | None,
    lr_config: dict | None,
    hgb_config: dict | None,
    feature_columns: list[str] | None,
) -> list[float]:
    features, labels, _ = _build_xyg(train_rows, feature_columns)
    oof = [0.0] * len(labels)
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed + 501)
    for tr_idx, ev_idx in skf.split(features, labels):
        tr_rows = [train_rows[i] for i in tr_idx]
        tr_x, tr_y, _ = _build_xyg(tr_rows, feature_columns)
        ev_x = [features[i] for i in ev_idx]
        pipe = _build_base_classifier_pipeline(
            seed, model_algorithm, et_config, lr_config, hgb_config
        )
        pipe.fit(tr_x, tr_y)
        preds = pipe.predict_proba(ev_x)[:, 1]
        for j, score in zip(ev_idx, preds):
            oof[j] = float(score)
    return oof


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--training-csv",
        type=Path,
        default=Path("ml/datasets/processed/training_dataset.csv"),
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_SEED)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=Path("ml/reports/ml_improvement_experiment.json"),
    )
    args = parser.parse_args()

    dataset_path = args.training_csv if args.training_csv.is_absolute() else _backend / args.training_csv
    rows, group_src = read_dataset_rows(dataset_path.resolve())
    seed = args.seed
    k = args.k
    repeats = args.repeats

    train_rows, test_rows = stratified_group_holdout_split(
        rows, test_size=TEST_SET_SIZE, seed=seed
    )

    grouping_full = audit_split_grouping(rows)
    grouping_train = audit_split_grouping(train_rows)
    uncertainty = summarize_uncertainty_codings(rows)

    # --- Nested tuning (train split only, no test) ---
    et_tuned = inner_cv_select_extra_trees_config(train_rows, seed=seed, inner_cv=3, feature_columns=None)
    merged_et_tuned = {
        **_resolved_et_config(None),
        **{k: v for k, v in et_tuned.items() if k != "innerMeanPrAuc"},
    }

    hgb_tuned_raw = inner_cv_select_hgb_config(train_rows, seed=seed, inner_cv=3, feature_columns=None)
    hgb_tuned = {k: v for k, v in hgb_tuned_raw.items() if k != "innerMeanPrAuc"}

    candidates: list[dict] = [
        {
            "id": "et_baseline",
            "label": "ExtraTrees baseline features",
            "model_algorithm": "extra_trees",
            "feature_columns": None,
            "et_config": None,
            "lr_config": None,
            "hgb_config": None,
        },
        {
            "id": "hgb_baseline",
            "label": "HistGradientBoosting default-ish",
            "model_algorithm": "hist_gradient_boosting",
            "feature_columns": None,
            "et_config": None,
            "lr_config": None,
            "hgb_config": None,
        },
        {
            "id": "et_explicit_interactions",
            "label": "ExtraTrees + age×BMI, parent×HTN, activity×BMI",
            "model_algorithm": "extra_trees",
            "feature_columns": list(FEATURE_COLUMNS_WITH_EXPLICIT_INTERACTIONS),
            "et_config": None,
            "lr_config": None,
            "hgb_config": None,
        },
        {
            "id": "et_pruned_ablation",
            "label": "ExtraTrees pruned (drop siblings_diabetes_count, aunts_uncles_score)",
            "model_algorithm": "extra_trees",
            "feature_columns": list(FEATURE_COLUMNS_PRUNED_ABLATION),
            "et_config": None,
            "lr_config": None,
            "hgb_config": None,
        },
        {
            "id": "et_nested_tuned",
            "label": "ExtraTrees + train-only inner-CV tuned hyperparameters",
            "model_algorithm": "extra_trees",
            "feature_columns": None,
            "et_config": merged_et_tuned,
            "lr_config": None,
            "hgb_config": None,
        },
        {
            "id": "hgb_nested_tuned",
            "label": "HistGradientBoosting + train-only inner-CV tuned",
            "model_algorithm": "hist_gradient_boosting",
            "feature_columns": None,
            "et_config": None,
            "lr_config": None,
            "hgb_config": hgb_tuned,
        },
    ]

    cv_block: list[dict] = []
    baseline_key_metrics: dict | None = None

    for spec in candidates:
        cv = compute_crossvalidation_metrics(
            train_rows,
            k=k,
            seed=seed,
            cv_repeats=repeats,
            model_algorithm=spec["model_algorithm"],
            et_config=spec["et_config"],
            lr_config=spec["lr_config"],
            hgb_config=spec["hgb_config"],
            feature_columns=spec["feature_columns"],
        )
        entry = {
            "id": spec["id"],
            "label": spec["label"],
            "meanMetrics": cv["meanMetrics"],
            "stdMetrics": cv["stdMetrics"],
            "metricConfidenceIntervals95": cv.get("metricConfidenceIntervals95"),
            "repeatSummaries": cv.get("repeatSummaries"),
            "evaluationMethod": cv["evaluationMethod"],
            "cvSplitProtocol": cv.get("cvSplitProtocol"),
        }
        cv_block.append(entry)
        if spec["id"] == "et_baseline":
            baseline_key_metrics = {
                "rocAucMean": cv["meanMetrics"]["rocAuc"],
                "rocAucStd": cv["stdMetrics"]["rocAuc"],
                "prAucMean": cv["meanMetrics"]["prAuc"],
                "prAucStd": cv["stdMetrics"]["prAuc"],
                "f1Std": cv["stdMetrics"]["f1Score"],
            }

    def passes_primary(entry: dict) -> bool:
        m = entry["meanMetrics"]
        s = entry["stdMetrics"]
        b = baseline_key_metrics
        assert b is not None
        lift_roc = m["rocAuc"] >= b["rocAucMean"] + 0.01
        lift_pr = m["prAuc"] >= b["prAucMean"] + 0.02
        stable = (s["rocAuc"] <= b["rocAucStd"] + 1e-9) and (s["f1Score"] <= b["f1Std"] + 1e-9)
        return (lift_roc or lift_pr) and stable

    def passes_secondary(entry: dict) -> bool:
        m = entry["meanMetrics"]
        s = entry["stdMetrics"]
        b = baseline_key_metrics
        assert b is not None
        if not (
            abs(m["rocAuc"] - b["rocAucMean"]) < 0.005
            and abs(m["prAuc"] - b["prAucMean"]) < 0.01
        ):
            return False
        rel_roc = (b["rocAucStd"] - s["rocAuc"]) / max(b["rocAucStd"], 1e-9)
        rel_f1 = (b["f1Std"] - s["f1Score"]) / max(b["f1Std"], 1e-9)
        return rel_roc >= 0.10 and rel_f1 >= 0.10

    def selection_rank(entry: dict) -> tuple:
        """Prefer acceptance gates, then mean ranking quality, then stability."""
        m = entry["meanMetrics"]
        s = entry["stdMetrics"]
        score = float(m["rocAuc"]) + float(m["prAuc"])
        pen = float(s["rocAuc"]) + float(s["prAuc"]) + float(s["f1Score"])
        return (passes_primary(entry), passes_secondary(entry), score, -pen)

    best_cv_entry = max(cv_block, key=selection_rank)
    best_spec = next(c for c in candidates if c["id"] == best_cv_entry["id"])

    # OOF scores on train for best model: threshold table + modes (no test leakage)
    oof_scores = _oof_scores_for_train(
        train_rows,
        k=k,
        seed=seed,
        model_algorithm=best_spec["model_algorithm"],
        et_config=best_spec["et_config"],
        lr_config=best_spec["lr_config"],
        hgb_config=best_spec["hgb_config"],
        feature_columns=best_spec["feature_columns"],
    )
    train_labels = [int(r["outcome"]) for r in train_rows]
    balanced_thr, balanced_metrics = select_operating_threshold(
        train_labels, oof_scores, strategy="f1"
    )
    screening_thr, screening_metrics = select_screening_threshold(
        train_labels, oof_scores, min_precision_floor=0.25
    )
    thr_table = threshold_sweep_table(train_labels, oof_scores, 0.20, 0.70, 0.01)

    subgroup_train = evaluate_stratified_subgroups(
        train_rows, train_labels, oof_scores, balanced_thr
    )

    holdout_balanced = compute_holdout_metrics(
        train_rows,
        test_rows,
        seed=seed,
        model_algorithm=best_spec["model_algorithm"],
        et_config=best_spec["et_config"],
        lr_config=best_spec["lr_config"],
        hgb_config=best_spec["hgb_config"],
        feature_columns=best_spec["feature_columns"],
        calibration_method="sigmoid",
    )
    holdout_isotonic = compute_holdout_metrics(
        train_rows,
        test_rows,
        seed=seed,
        model_algorithm=best_spec["model_algorithm"],
        et_config=best_spec["et_config"],
        lr_config=best_spec["lr_config"],
        hgb_config=best_spec["hgb_config"],
        feature_columns=best_spec["feature_columns"],
        calibration_method="isotonic",
    )

    train_fit_x, train_fit_y, _ = _build_xyg(train_rows, best_spec["feature_columns"])
    test_x, test_y, _ = _build_xyg(test_rows, best_spec["feature_columns"])

    cal_pipe = _build_calibrated_pipeline(
        seed=seed,
        et_config=best_spec["et_config"],
        lr_config=best_spec["lr_config"],
        hgb_config=best_spec["hgb_config"],
        model_algorithm=best_spec["model_algorithm"],
        calibration_method="sigmoid",
    )
    cal_pipe.fit(train_fit_x, train_fit_y)
    tr_cal_scores = [float(s) for s in cal_pipe.predict_proba(train_fit_x)[:, 1]]
    te_cal_scores = [float(s) for s in cal_pipe.predict_proba(test_x)[:, 1]]
    scr_thr_cal, _ = select_screening_threshold(train_fit_y, tr_cal_scores, min_precision_floor=0.25)

    holdout_screening_test_metrics = calculate_metrics(test_y, te_cal_scores, threshold=scr_thr_cal)

    test_subgroup_balanced = evaluate_stratified_subgroups(
        test_rows, test_y, te_cal_scores, holdout_balanced["optimizedThreshold"]
    )

    assert baseline_key_metrics is not None
    best_mean = best_cv_entry["meanMetrics"]
    best_std = best_cv_entry["stdMetrics"]
    accept_primary = passes_primary(best_cv_entry)
    rel_roc_std = (
        baseline_key_metrics["rocAucStd"] - best_std["rocAuc"]
    ) / max(baseline_key_metrics["rocAucStd"], 1e-9)
    rel_f1_std = (baseline_key_metrics["f1Std"] - best_std["f1Score"]) / max(
        baseline_key_metrics["f1Std"], 1e-9
    )
    accept_secondary = passes_secondary(best_cv_entry)

    report = {
        "datasetPath": str(dataset_path),
        "groupSourceColumn": group_src,
        "nRows": len(rows),
        "holdoutLocked": {
            "trainRows": len(train_rows),
            "testRows": len(test_rows),
            "testSizeFraction": TEST_SET_SIZE,
            "seed": seed,
        },
        "groupingAuditFull": grouping_full,
        "groupingAuditTrainCvScope": grouping_train,
        "uncertaintyCodingSummary": uncertainty,
        "cvScope": "train_rows_only_after_holdout_lock",
        "cvFolds": k,
        "cvRepeats": repeats,
        "nestedTuning": {
            "extraTreesSelected": et_tuned,
            "histGradientBoostingSelected": hgb_tuned_raw,
        },
        "candidateCv": cv_block,
        "selectedCandidateId": best_spec["id"],
        "thresholdPolicy": {
            "balancedMode": {
                "thresholdTrainOofUncalibrated": balanced_thr,
                "metricsTrainOof": balanced_metrics,
            },
            "screeningMode": {
                "thresholdTrainOofUncalibrated": screening_thr,
                "metricsTrainOof": screening_metrics,
            },
            "thresholdTable012To070": thr_table,
        },
        "holdoutSigmoidCalibrated": {
            "balancedTrainSelectedThreshold": holdout_balanced["optimizedThreshold"],
            "metricsAtBalancedThreshold": holdout_balanced["testMetrics"],
            "screeningTrainSelectedThresholdCalibrated": scr_thr_cal,
            "metricsAtScreeningThreshold": holdout_screening_test_metrics,
        },
        "holdoutIsotonicCalibrated": {
            "balancedTrainSelectedThreshold": holdout_isotonic["optimizedThreshold"],
            "metricsAtBalancedThreshold": holdout_isotonic["testMetrics"],
        },
        "subgroupAnalysis": {
            "trainOofAtBalancedThreshold": subgroup_train,
            "testAtHoldoutBalancedThreshold": test_subgroup_balanced,
        },
        "acceptance": {
            "primaryPass": accept_primary,
            "secondaryPass": accept_secondary,
            "baselineReference": baseline_key_metrics,
        },
        "decisionLog": [
            "CV and nested tuning used only train_rows; test_rows used once at end for holdout metrics.",
            "When each row is its own group id, StratifiedKFold is used for CV (see cvSplitProtocol per candidate).",
            f"Selected {best_spec['id']} by maximizing mean(ROC-AUC)+mean(PR-AUC) with tie-break toward lower std sum.",
        ],
    }

    out_path = args.out_json if args.out_json.is_absolute() else _backend / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("selectedCandidateId", "acceptance", "holdoutSigmoidCalibrated")}, indent=2))
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
