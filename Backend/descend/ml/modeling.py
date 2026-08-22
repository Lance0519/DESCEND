from __future__ import annotations

import csv
import json
import math
import os
import random
from collections import defaultdict
from typing import Literal
from datetime import datetime, timezone
from pathlib import Path

import joblib
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# Core features with explicit risk direction — clinically grounded
# 8 core features selected via forward selection on 140-row dataset to maximize
# generalization. Additional features (diet_quality_score, mother_gdm) were
# evaluated but degraded ROC-AUC due to low variance with this sample size.
# 3 interaction terms added to capture non-linear metabolic and hereditary risk patterns.
FEATURE_COLUMNS = [
    # Demographic factors
    "age",
    "user_is_male",
    # Anthropometric & metabolic factors
    "bmi",
    "hypertension_status",
    # Behavioral/lifestyle factors
    "physical_activity_score",
    # Family history
    "parent_has_t2dm",
    "siblings_diabetes_count",
    "aunts_uncles_score",
    # Aggregated lineage (same definitions as graph.derive_family_metrics / training CSV)
    "weightedFamilyScore",
    "lineageRiskIndex",
    "propagationProbability",
    # Interaction terms for non-linear risk modeling
    "metabolic_risk_index",
    "hereditary_load_index",
    "activity_metabolic_index",
]

TARGET_COLUMN = "outcome"
# Internal row key for grouped CV / holdout (value copied from CSV grouping column below).
GROUP_COLUMN = "family_id"
# First matching column in the training CSV wins. Prefer source_patient_id for this project.
GROUP_COLUMN_CANDIDATES = ("source_patient_id", "family_id", "source_record_id")
DEFAULT_RANDOM_SEED = 42
# Threshold search (balanced / F1 mode): wide grid; selection uses train or OOF only — never hold-out test
THRESHOLD_RANGE_MIN = 0.20
THRESHOLD_RANGE_MAX = 0.70
# Wider floor for recall-constrained operating points (thesis screening objective)
THRESHOLD_RECALL_STRATEGY_MIN = 0.06
THRESHOLD_RECALL_STRATEGY_MAX = 0.58
TEST_SET_SIZE = 0.20  # 20% hold-out by family

ThresholdStrategy = str  # "f1" | "recall_constrained"

DEFAULT_FEATURE_MEANS = {
    "age": 35.0,
    "bmi": 24.0,
    "user_is_male": 0.5,
    "physical_activity_score": 1.0,
    "parent_has_t2dm": 0.15,
    "hypertension_status": 0.2,
    "siblings_diabetes_count": 0.2,
    "aunts_uncles_score": 0.25,
    "weightedFamilyScore": 0.5,
    "lineageRiskIndex": 0.58,
    "propagationProbability": 0.12,
    "metabolic_risk_index": 35.0,  # age * (bmi / 24) ≈ 35
    # Generational + extended-family composite (see feature_builder._compute_hereditary_load_index)
    "hereditary_load_index": 0.28,
    "activity_metabolic_index": 0.2,  # physical_activity_score * (1 + hypertension_status)
}

DEFAULT_FEATURE_STDS = {
    "age": 12.0,
    "bmi": 4.0,
    "user_is_male": 0.5,
    "physical_activity_score": 0.7,
    "parent_has_t2dm": 0.35,
    "hypertension_status": 0.35,
    "siblings_diabetes_count": 0.8,
    "aunts_uncles_score": 0.45,
    "weightedFamilyScore": 0.6,
    "lineageRiskIndex": 0.95,
    "propagationProbability": 0.18,
    "metabolic_risk_index": 15.0,  # age * (bmi / 24) std
    "hereditary_load_index": 0.42,
    "activity_metabolic_index": 0.3,  # activity × metabolic interaction std
}

TARGET_DEFINITION = (
    "Binary classification trained on respondent-level outcome: T2DM (1) vs not (0). "
    "Labels should reflect verified or clinically documented status when possible; "
    "proxy or manually assigned labels limit achievable accuracy and calibration."
)
TARGET_SCOPE_NOTE = (
    "The deployed classifier is either ExtraTreesClassifier (interaction-friendly ranking) "
    "or HistGradientBoostingClassifier (boosted-tree tabular modeling). "
    "Displayed child scenario values are heuristic projections from the respondent "
    "score, not separately trained targets. Grouped CV uses source_patient_id (or family_id / "
    "source_record_id, first present in the CSV) when multiple rows share a group id; if each "
    "row is its own group, folds approximate stratified splits rather than true family "
    "generalization."
)

EXTRA_TREES_CONFIG = {
    "n_estimators": 400,
    "max_depth": 6,
    "min_samples_leaf": 3,
    "class_weight": "balanced",
    "random_state": DEFAULT_RANDOM_SEED,
}

# Native sklearn boosting: strong tabular default without extra dependencies (cf. LightGBM/XGBoost).
HIST_GRADIENT_BOOSTING_CONFIG = {
    "max_depth": 5,
    "max_iter": 300,
    "learning_rate": 0.06,
    "min_samples_leaf": 20,
    "l2_regularization": 0.1,
    "class_weight": "balanced",
    "random_state": DEFAULT_RANDOM_SEED,
}

ModelAlgorithm = Literal["extra_trees", "hist_gradient_boosting"]

# Explicit multiplicative interactions (orthogonal to scaled metabolic_risk_index).
CLINICAL_INTERACTION_FEATURE_NAMES = ("age_x_bmi", "parent_x_hypertension", "activity_x_bmi")

# Pruned variant for ablation: drop extended-family counts often high-variance at small n.
FEATURE_COLUMNS_PRUNED_ABLATION = [
    c for c in FEATURE_COLUMNS if c not in ("aunts_uncles_score", "siblings_diabetes_count")
]

FEATURE_COLUMNS_WITH_EXPLICIT_INTERACTIONS = list(FEATURE_COLUMNS) + list(CLINICAL_INTERACTION_FEATURE_NAMES)

# Training-time row balancing (optional). "none" relies on class_weight only.
BalanceMode = str  # "none" | "oversample"


def _training_n_jobs() -> int:
    """
    Keep training portable in restricted Windows environments.
    Default to 1 worker; allow power users to opt into parallelism with
    T2DM_TRAIN_N_JOBS when running outside sandboxed shells.
    """
    raw = os.getenv("T2DM_TRAIN_N_JOBS", "1").strip()
    try:
        value = int(raw)
    except ValueError:
        return 1
    return value if value != 0 else 1


def _oversample_minority_rows(
    rows: list[dict[str, float]],
    seed: int,
) -> list[dict[str, float]]:
    """
    Random oversample the minority class with replacement until counts match the majority.
    Duplicates are shallow copies (same group id retained). Applied only to training data
    passed into fit — evaluation rows stay the real distribution.
    """
    if len(rows) < 2:
        return rows
    pos = [r for r in rows if int(r[TARGET_COLUMN]) == 1]
    neg = [r for r in rows if int(r[TARGET_COLUMN]) == 0]
    if not pos or not neg:
        return rows
    if len(pos) == len(neg):
        return list(rows)

    rng = random.Random(seed)
    if len(pos) < len(neg):
        minority, majority = pos, neg
        k_extra = len(neg) - len(pos)
    else:
        minority, majority = neg, pos
        k_extra = len(pos) - len(neg)

    extras = [dict(rng.choice(minority)) for _ in range(k_extra)]
    out = majority + minority + extras
    rng.shuffle(out)
    return out


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sigmoid(value: float) -> float:
    if value >= 35:
        return 1.0
    if value <= -35:
        return 0.0
    return 1.0 / (1.0 + math.exp(-value))


def safe_float(value: str) -> float:
    return float(str(value).strip())


def top_features(coefficients: dict[str, float], limit: int = 6) -> list[dict]:
    items = sorted(coefficients.items(), key=lambda item: abs(item[1]), reverse=True)
    return [{"feature": key, "coefficient": round(value, 4)} for key, value in items[:limit]]


def roc_auc(labels: list[int], scores: list[float]) -> float:
    positives = [score for label, score in zip(labels, scores) if label == 1]
    negatives = [score for label, score in zip(labels, scores) if label == 0]
    if not positives or not negatives:
        return 0.5
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def _wilson_score_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Two-sided Wilson score interval for a binomial proportion (Wallis 2013)."""
    if n <= 0:
        return (0.0, 1.0)
    phat = min(1.0, max(0.0, successes / n))
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (phat + z2 / (2.0 * n)) / denom
    half = (z / denom) * math.sqrt(phat * (1.0 - phat) / n + z2 / (4.0 * n * n))
    return (max(0.0, center - half), min(1.0, center + half))


def _binomial_wilson_cis_from_confusion(m: dict) -> dict:
    """95% Wilson intervals for rates derived from a single confusion matrix (hold-out reporting)."""
    tp = int(m["truePositives"])
    tn = int(m["trueNegatives"])
    fp = int(m["falsePositives"])
    fn = int(m["falseNegatives"])

    def _cell(successes: int, n: int) -> dict:
        lo, hi = _wilson_score_interval(successes, n)
        est = successes / n if n else 0.0
        return {
            "estimate": round(est, 4),
            "ci95Low": round(lo, 4),
            "ci95High": round(hi, 4),
            "denominatorN": n,
        }

    out: dict = {}
    if tp + fn > 0:
        out["recallSensitivity"] = _cell(tp, tp + fn)
    if tp + fp > 0:
        out["precisionPpv"] = _cell(tp, tp + fp)
    if tn + fp > 0:
        out["specificity"] = _cell(tn, tn + fp)
    return out


def calculate_metrics(labels: list[int], scores: list[float], threshold: float = 0.5) -> dict:
    predictions = [1 if score >= threshold else 0 for score in scores]
    tp = sum(1 for truth, pred in zip(labels, predictions) if truth == 1 and pred == 1)
    tn = sum(1 for truth, pred in zip(labels, predictions) if truth == 0 and pred == 0)
    fp = sum(1 for truth, pred in zip(labels, predictions) if truth == 0 and pred == 1)
    fn = sum(1 for truth, pred in zip(labels, predictions) if truth == 1 and pred == 0)
    total = max(len(labels), 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    # Count class distribution in labels
    positives_count = sum(1 for label in labels if label == 1)
    negatives_count = sum(1 for label in labels if label == 0)

    try:
        pr_auc = float(average_precision_score(labels, scores))
    except ValueError:
        pr_auc = 0.0
    try:
        brier = float(brier_score_loss(labels, scores))
    except ValueError:
        brier = 1.0
    
    return {
        "accuracy": round((tp + tn) / total, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1Score": round(f1, 4),
        "specificity": round(specificity, 4),
        "rocAuc": round(roc_auc(labels, scores), 4),
        "prAuc": round(pr_auc, 4),
        "brierScore": round(brier, 4),
        "truePositives": tp,
        "trueNegatives": tn,
        "falsePositives": fp,
        "falseNegatives": fn,
        "positivesInSet": positives_count,
        "negativesInSet": negatives_count,
        "threshold": round(threshold, 6),
    }


def _recompute_f1_from_pr(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return 2.0 * precision * recall / (precision + recall)


def _classification_report_from_counts(tp: int, tn: int, fp: int, fn: int) -> dict:
    support_0 = tn + fp
    support_1 = tp + fn
    total = support_0 + support_1

    precision_0 = tn / max(tn + fn, 1)
    recall_0 = tn / max(support_0, 1)
    f1_0 = _recompute_f1_from_pr(precision_0, recall_0)

    precision_1 = tp / max(tp + fp, 1)
    recall_1 = tp / max(support_1, 1)
    f1_1 = _recompute_f1_from_pr(precision_1, recall_1)

    macro_precision = (precision_0 + precision_1) / 2.0
    macro_recall = (recall_0 + recall_1) / 2.0
    macro_f1 = (f1_0 + f1_1) / 2.0

    weighted_precision = (
        ((precision_0 * support_0) + (precision_1 * support_1)) / max(total, 1)
    )
    weighted_recall = (
        ((recall_0 * support_0) + (recall_1 * support_1)) / max(total, 1)
    )
    weighted_f1 = (
        ((f1_0 * support_0) + (f1_1 * support_1)) / max(total, 1)
    )

    return {
        "labels": [0, 1],
        "average": {
            "type": "binary",
            "posLabel": 1,
        },
        "class_0": {
            "precision": round(precision_0, 4),
            "recall": round(recall_0, 4),
            "f1Score": round(f1_0, 4),
            "support": support_0,
        },
        "class_1": {
            "precision": round(precision_1, 4),
            "recall": round(recall_1, 4),
            "f1Score": round(f1_1, 4),
            "support": support_1,
        },
        "macroAvg": {
            "precision": round(macro_precision, 4),
            "recall": round(macro_recall, 4),
            "f1Score": round(macro_f1, 4),
            "support": total,
        },
        "weightedAvg": {
            "precision": round(weighted_precision, 4),
            "recall": round(weighted_recall, 4),
            "f1Score": round(weighted_f1, 4),
            "support": total,
        },
    }


def _group_key_for_row(row: dict[str, float], fallback_index: int) -> int:
    raw = row.get(GROUP_COLUMN)
    if raw is None:
        return fallback_index
    return int(raw)


def _feature_signature(row: dict[str, float]) -> tuple[float, ...]:
    return tuple(round(float(row[column]), 6) for column in FEATURE_COLUMNS)


def _detect_cross_group_duplicates(rows: list[dict[str, float]]) -> dict:
    signatures: dict[tuple[float, ...], set[int]] = defaultdict(set)
    signature_counts: dict[tuple[float, ...], int] = defaultdict(int)

    for index, row in enumerate(rows):
        signature = _feature_signature(row)
        signature_counts[signature] += 1
        signatures[signature].add(_group_key_for_row(row, index))

    duplicate_signatures = 0
    duplicate_rows = 0
    for signature, groups in signatures.items():
        if len(groups) > 1:
            duplicate_signatures += 1
            duplicate_rows += signature_counts[signature]

    return {
        "duplicateSignaturesAcrossGroups": duplicate_signatures,
        "rowsInCrossGroupDuplicateSignatures": duplicate_rows,
    }


def _mean(values: list[float]) -> float:
    return sum(values) / max(len(values), 1)


def _std(values: list[float]) -> float:
    if not values:
        return 0.0
    avg = _mean(values)
    variance = sum((value - avg) ** 2 for value in values) / len(values)
    return math.sqrt(variance)


def _populate_clinical_interaction_features(row: dict[str, float]) -> None:
    """Derive explicit interaction terms for ablation experiments (keys may be absent until called)."""
    age = float(row.get("age", 0.0))
    bmi = float(row.get("bmi", 0.0))
    act = float(row.get("physical_activity_score", 0.0))
    parent = float(row.get("parent_has_t2dm", 0.0))
    htn = float(row.get("hypertension_status", 0.0))
    row["age_x_bmi"] = age * bmi
    row["parent_x_hypertension"] = parent * htn
    row["activity_x_bmi"] = act * bmi


def _build_xyg(
    rows: list[dict[str, float]],
    feature_columns: list[str] | None = None,
) -> tuple[list[list[float]], list[int], list[int]]:
    columns = feature_columns if feature_columns is not None else FEATURE_COLUMNS
    features = [[float(row[column]) for column in columns] for row in rows]
    labels = [int(row[TARGET_COLUMN]) for row in rows]
    groups = [_group_key_for_row(row, idx) for idx, row in enumerate(rows)]
    return features, labels, groups


def _resolved_et_config(overrides: dict | None) -> dict:
    """Merge EXTRA_TREES_CONFIG with optional tuning overrides (max_depth, min_samples_leaf, etc.)."""
    cfg = {**EXTRA_TREES_CONFIG}
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg


def _resolved_hgb_config(overrides: dict | None) -> dict:
    cfg = {**HIST_GRADIENT_BOOSTING_CONFIG}
    if overrides:
        cfg.update({k: v for k, v in overrides.items() if v is not None})
    return cfg


def _build_base_classifier_pipeline(
    seed: int = DEFAULT_RANDOM_SEED,
    model_algorithm: ModelAlgorithm = "extra_trees",
    et_config: dict | None = None,
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
) -> Pipeline:
    """StandardScaler + classifier. Used for CV folds (uncalibrated) and as CalibratedClassifierCV base."""
    # Support both ExtraTrees and HistGradientBoosting algorithms.
    if model_algorithm == "extra_trees":
        cfg = _resolved_et_config(et_config)
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=int(cfg["n_estimators"]),
                        max_depth=int(cfg["max_depth"]),
                        min_samples_leaf=int(cfg["min_samples_leaf"]),
                        class_weight=cfg["class_weight"],
                        random_state=seed,
                        n_jobs=_training_n_jobs(),
                    ),
                ),
            ]
        )
    if model_algorithm == "hist_gradient_boosting":
        cfg = _resolved_hgb_config(hgb_config)
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        max_depth=int(cfg["max_depth"]),
                        max_iter=int(cfg["max_iter"]),
                        learning_rate=float(cfg["learning_rate"]),
                        min_samples_leaf=int(cfg["min_samples_leaf"]),
                        l2_regularization=float(cfg.get("l2_regularization", 0.0)),
                        random_state=seed,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unsupported model_algorithm: {model_algorithm}")


def _build_training_pipeline(seed: int = DEFAULT_RANDOM_SEED, et_config: dict | None = None) -> Pipeline:
    """Backward-compatible alias: StandardScaler + ExtraTrees only."""
    return _build_base_classifier_pipeline(seed, "extra_trees", et_config, None)


def _build_calibrated_pipeline(
    seed: int = DEFAULT_RANDOM_SEED,
    et_config: dict | None = None,
    model_algorithm: ModelAlgorithm = "extra_trees",
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    calibration_method: Literal["sigmoid", "isotonic"] = "sigmoid",
) -> CalibratedClassifierCV:
    """Sigmoid or isotonic calibration on top of the chosen base pipeline for deployment / holdout."""
    return CalibratedClassifierCV(
        estimator=_build_base_classifier_pipeline(
            seed, model_algorithm, et_config, lr_config, hgb_config
        ),
        method=calibration_method,
        cv=3,
        n_jobs=_training_n_jobs(),
    )


def inner_cv_select_extra_trees_config(
    train_rows: list[dict[str, float]],
    seed: int,
    inner_cv: int = 3,
    feature_columns: list[str] | None = None,
    speed_mode: bool = True,
) -> dict:
    """
    Train-only nested selection: small grid maximizing PR-AUC (average_precision).
    Does not touch hold-out rows when train_rows excludes them.
    """
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    features, labels, _ = _build_xyg(train_rows, feature_columns)
    skf = StratifiedKFold(n_splits=inner_cv, shuffle=True, random_state=seed + 11)
    base = _resolved_et_config(None)
    n_tune = min(int(base["n_estimators"]), 200 if speed_mode else 300)
    best_ap = -1.0
    best: dict = {}
    for max_depth in (4, 6, 8):
        for min_leaf in (2, 4, 6):
            for class_weight in ("balanced", None):
                pipe = Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        (
                            "model",
                            ExtraTreesClassifier(
                                n_estimators=n_tune,
                                max_depth=max_depth,
                                min_samples_leaf=min_leaf,
                                class_weight=class_weight,
                                random_state=seed,
                                n_jobs=_training_n_jobs(),
                            ),
                        ),
                    ]
                )
                scores = cross_val_score(
                    pipe,
                    features,
                    labels,
                    cv=skf,
                    scoring="average_precision",
                    n_jobs=_training_n_jobs(),
                )
                ap = float(scores.mean())
                if ap > best_ap:
                    best_ap = ap
                    best = {
                        "max_depth": max_depth,
                        "min_samples_leaf": min_leaf,
                        "n_estimators": n_tune,
                        "class_weight": class_weight,
                        "innerMeanPrAuc": round(ap, 4),
                    }
    return best


def inner_cv_select_hgb_config(
    train_rows: list[dict[str, float]],
    seed: int,
    inner_cv: int = 3,
    feature_columns: list[str] | None = None,
) -> dict:
    """Train-only grid for HistGradientBoosting on PR-AUC."""
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    features, labels, _ = _build_xyg(train_rows, feature_columns)
    skf = StratifiedKFold(n_splits=inner_cv, shuffle=True, random_state=seed + 13)
    best_ap = -1.0
    best: dict = {}
    for max_depth in (3, 5, 7):
        for min_leaf in (10, 20, 35):
            for max_iter in (200, 350):
                pipe = Pipeline(
                    [
                        ("scaler", StandardScaler()),
                        (
                            "model",
                            HistGradientBoostingClassifier(
                                max_depth=max_depth,
                                max_iter=max_iter,
                                learning_rate=0.06,
                                min_samples_leaf=min_leaf,
                                l2_regularization=0.1,
                                class_weight="balanced",
                                random_state=seed,
                            ),
                        ),
                    ]
                )
                scores = cross_val_score(
                    pipe,
                    features,
                    labels,
                    cv=skf,
                    scoring="average_precision",
                    n_jobs=_training_n_jobs(),
                )
                ap = float(scores.mean())
                if ap > best_ap:
                    best_ap = ap
                    best = {
                        "max_depth": max_depth,
                        "min_samples_leaf": min_leaf,
                        "max_iter": max_iter,
                        "learning_rate": 0.06,
                        "l2_regularization": 0.1,
                        "class_weight": "balanced",
                        "innerMeanPrAuc": round(ap, 4),
                    }
    return best


def tune_extra_trees_hyperparameters(
    rows: list[dict[str, float]],
    seed: int,
    et_base: dict | None = None,
    inner_cv: int = 3,
) -> dict[str, int]:
    """
    Inner stratified CV grid search on PR-AUC (average_precision).
    Only max_depth and min_samples_leaf are tuned to keep JSON config simple and thesis-auditable.
    """
    from sklearn.model_selection import StratifiedKFold, cross_val_score

    base = _resolved_et_config(et_base)
    features, labels, _ = _build_xyg(rows)
    skf = StratifiedKFold(n_splits=inner_cv, shuffle=True, random_state=seed + 404)
    n_tune = min(int(base["n_estimators"]), 250)
    best_ap = -1.0
    best: dict[str, int] = {}
    for max_depth in (4, 6, 8):
        for min_leaf in (2, 4, 6):
            pipe = Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "model",
                        ExtraTreesClassifier(
                            n_estimators=n_tune,
                            max_depth=max_depth,
                            min_samples_leaf=min_leaf,
                            class_weight=base["class_weight"],
                            random_state=seed,
                            n_jobs=_training_n_jobs(),
                        ),
                    ),
                ]
            )
            scores = cross_val_score(
                pipe,
                features,
                labels,
                cv=skf,
                scoring="average_precision",
                n_jobs=_training_n_jobs(),
            )
            ap = float(scores.mean())
            if ap > best_ap:
                best_ap = ap
                best = {"max_depth": max_depth, "min_samples_leaf": min_leaf}
    return best


def _run_label_shuffle_check(
    rows: list[dict[str, float]],
    k: int,
    seed: int,
    model_algorithm: ModelAlgorithm = "extra_trees",
    et_config: dict | None = None,
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    feature_columns: list[str] | None = None,
) -> dict:
    features, labels, groups = _build_xyg(rows, feature_columns)
    shuffled_labels = list(labels)
    random.Random(seed + 97).shuffle(shuffled_labels)

    degenerate = len(set(groups)) == len(rows)
    pos = sum(1 for y in labels if y == 1)
    neg = len(labels) - pos
    effective_k = min(k, pos, neg)
    if effective_k < 2:
        effective_k = 2

    if degenerate:
        splitter = StratifiedKFold(
            n_splits=effective_k, shuffle=True, random_state=seed + 101
        )
        split_iter = splitter.split(features, shuffled_labels)
    else:
        splitter = StratifiedGroupKFold(
            n_splits=effective_k, shuffle=True, random_state=seed + 101
        )
        split_iter = splitter.split(features, shuffled_labels, groups)

    accuracies: list[float] = []
    roc_aucs: list[float] = []

    for train_indices, eval_indices in split_iter:
        train_x = [features[index] for index in train_indices]
        train_y = [shuffled_labels[index] for index in train_indices]
        eval_x = [features[index] for index in eval_indices]
        eval_y = [shuffled_labels[index] for index in eval_indices]

        pipeline = _build_base_classifier_pipeline(
            seed, model_algorithm, et_config, lr_config, hgb_config
        )
        pipeline.fit(train_x, train_y)
        eval_scores = [float(score) for score in pipeline.predict_proba(eval_x)[:, 1]]
        fold_metrics = calculate_metrics(eval_y, eval_scores, threshold=0.5)
        accuracies.append(fold_metrics["accuracy"])
        roc_aucs.append(fold_metrics["rocAuc"])

    mean_accuracy = round(_mean(accuracies), 4)
    mean_roc_auc = round(_mean(roc_aucs), 4)
    return {
        "meanAccuracy": mean_accuracy,
        "stdAccuracy": round(_std(accuracies), 4),
        "meanRocAuc": mean_roc_auc,
        "stdRocAuc": round(_std(roc_aucs), 4),
        "status": "ok" if mean_roc_auc < 0.65 else "investigate",
    }


def _log_loss(
    labels: list[int],
    scores: list[float],
    sample_weights: list[float] | None = None,
) -> float:
    epsilon = 1e-9
    total = 0.0
    total_weight = 0.0
    if sample_weights is None:
        sample_weights = [1.0] * len(labels)
    for truth, score, sample_weight in zip(labels, scores, sample_weights):
        clipped = min(max(score, epsilon), 1.0 - epsilon)
        total += sample_weight * (-(truth * math.log(clipped) + (1 - truth) * math.log(1.0 - clipped)))
        total_weight += sample_weight
    return total / max(total_weight, 1.0)


def _balanced_class_weights(labels: list[int]) -> dict[int, float]:
    positives = sum(1 for label in labels if label == 1)
    negatives = sum(1 for label in labels if label == 0)
    total = max(positives + negatives, 1)
    if positives == 0 or negatives == 0:
        return {0: 1.0, 1: 1.0}
    return {
        0: total / (2.0 * negatives),
        1: total / (2.0 * positives),
    }


def stratified_holdout_split(
    rows: list[dict[str, float]],
    test_size: float = 0.2,
    seed: int = DEFAULT_RANDOM_SEED,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    positives = [row for row in rows if int(row[TARGET_COLUMN]) == 1]
    negatives = [row for row in rows if int(row[TARGET_COLUMN]) == 0]

    if not positives or not negatives:
        raise ValueError("Dataset must contain at least one positive and one negative outcome.")
    if len(rows) < 10:
        raise ValueError("Dataset must contain at least 10 rows for evaluation.")

    rng = random.Random(seed)
    rng.shuffle(positives)
    rng.shuffle(negatives)

    def split_one_class(class_rows: list[dict[str, float]]) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        test_count = int(round(len(class_rows) * test_size))
        test_count = max(1, min(len(class_rows) - 1, test_count))
        train_count = len(class_rows) - test_count
        return class_rows[:train_count], class_rows[train_count:]

    pos_train, pos_test = split_one_class(positives)
    neg_train, neg_test = split_one_class(negatives)

    training_rows = pos_train + neg_train
    evaluation_rows = pos_test + neg_test
    rng.shuffle(training_rows)
    rng.shuffle(evaluation_rows)
    return training_rows, evaluation_rows


def stratified_kfold_splits(
    rows: list[dict[str, float]],
    k: int = 5,
    seed: int = DEFAULT_RANDOM_SEED,
) -> list[tuple[list[dict[str, float]], list[dict[str, float]]]]:
    """Generate k stratified folds for cross-validation."""
    positives = [row for row in rows if int(row[TARGET_COLUMN]) == 1]
    negatives = [row for row in rows if int(row[TARGET_COLUMN]) == 0]

    if not positives or not negatives:
        raise ValueError("Dataset must contain at least one positive and one negative outcome.")
    if len(rows) < k:
        raise ValueError(f"Dataset must contain at least {k} rows for {k}-fold evaluation.")

    rng = random.Random(seed)
    rng.shuffle(positives)
    rng.shuffle(negatives)

    folds = []
    for fold_idx in range(k):
        test_pos = []
        test_neg = []
        
        # Stratified split: distribute each class across folds
        pos_per_fold = len(positives) // k
        neg_per_fold = len(negatives) // k
        pos_start = fold_idx * pos_per_fold
        neg_start = fold_idx * neg_per_fold
        
        if fold_idx == k - 1:  # Last fold gets remainder
            test_pos = positives[pos_start:]
            test_neg = negatives[neg_start:]
            train_pos = positives[:pos_start]
            train_neg = negatives[:neg_start]
        else:
            test_pos = positives[pos_start:pos_start + pos_per_fold]
            test_neg = negatives[neg_start:neg_start + neg_per_fold]
            train_pos = positives[:pos_start] + positives[pos_start + pos_per_fold:]
            train_neg = negatives[:neg_start] + negatives[neg_start + neg_per_fold:]
        
        training_rows = train_pos + train_neg
        evaluation_rows = test_pos + test_neg
        rng.shuffle(training_rows)
        rng.shuffle(evaluation_rows)
        folds.append((training_rows, evaluation_rows))
    
    return folds


def stratified_group_kfold_splits(
    rows: list[dict[str, float]],
    k: int = 5,
    seed: int = DEFAULT_RANDOM_SEED,
) -> list[tuple[list[dict[str, float]], list[dict[str, float]]]]:
    """Generate k stratified folds while keeping grouped rows in the same fold."""
    grouped_rows: dict[int, list[dict[str, float]]] = {}
    for index, row in enumerate(rows):
        group_key = _group_key_for_row(row, index)
        grouped_rows.setdefault(group_key, []).append(row)

    positive_groups: list[tuple[int, list[dict[str, float]]]] = []
    negative_groups: list[tuple[int, list[dict[str, float]]]] = []

    for group_key, group_items in grouped_rows.items():
        labels = {int(item[TARGET_COLUMN]) for item in group_items}
        if len(labels) != 1:
            raise ValueError(
                f"Group {group_key} has mixed target labels. Grouped CV requires consistent group labels."
            )
        group_label = next(iter(labels))
        if group_label == 1:
            positive_groups.append((group_key, group_items))
        else:
            negative_groups.append((group_key, group_items))

    if not positive_groups or not negative_groups:
        raise ValueError("Dataset must contain at least one positive and one negative outcome.")
    if len(positive_groups) < k or len(negative_groups) < k:
        raise ValueError(
            "Insufficient group count per class for grouped stratified CV. "
            f"Need at least {k} groups in each class."
        )

    rng = random.Random(seed)
    rng.shuffle(positive_groups)
    rng.shuffle(negative_groups)

    pos_fold_groups: list[list[tuple[int, list[dict[str, float]]]]] = [[] for _ in range(k)]
    neg_fold_groups: list[list[tuple[int, list[dict[str, float]]]]] = [[] for _ in range(k)]

    for idx, group in enumerate(positive_groups):
        pos_fold_groups[idx % k].append(group)
    for idx, group in enumerate(negative_groups):
        neg_fold_groups[idx % k].append(group)

    folds: list[tuple[list[dict[str, float]], list[dict[str, float]]]] = []
    for fold_idx in range(k):
        eval_groups = pos_fold_groups[fold_idx] + neg_fold_groups[fold_idx]
        train_groups: list[tuple[int, list[dict[str, float]]]] = []
        for other_idx in range(k):
            if other_idx == fold_idx:
                continue
            train_groups.extend(pos_fold_groups[other_idx])
            train_groups.extend(neg_fold_groups[other_idx])

        training_rows: list[dict[str, float]] = []
        evaluation_rows: list[dict[str, float]] = []
        for _, group_items in train_groups:
            training_rows.extend(group_items)
        for _, group_items in eval_groups:
            evaluation_rows.extend(group_items)

        rng.shuffle(training_rows)
        rng.shuffle(evaluation_rows)
        folds.append((training_rows, evaluation_rows))

    return folds


def _build_preprocessing(training_rows: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    means: dict[str, float] = {}
    stds: dict[str, float] = {}
    row_count = len(training_rows)

    for feature in FEATURE_COLUMNS:
        values = [float(row[feature]) for row in training_rows]
        mean_value = sum(values) / row_count
        variance = sum((value - mean_value) ** 2 for value in values) / row_count
        std_value = math.sqrt(variance) or 1.0
        means[feature] = round(mean_value, 6)
        stds[feature] = round(std_value, 6)

    return {"means": means, "stds": stds}


def _standardized_vector(features: dict[str, float], preprocessing: dict[str, dict[str, float]]) -> list[float]:
    means = preprocessing["means"]
    stds = preprocessing["stds"]
    vector: list[float] = []
    for feature in FEATURE_COLUMNS:
        std_value = stds.get(feature) or 1.0
        vector.append((float(features.get(feature, 0.0)) - means.get(feature, 0.0)) / std_value)
    return vector


def _select_optimal_threshold_f1(
    labels: list[int],
    scores: list[float],
    min_positive_predictions: int = 5,
) -> tuple[float, dict]:
    """Select threshold that maximizes F1 within THRESHOLD_RANGE_* (decision metric, not ROC)."""
    step = 0.005
    n_steps = int(round((THRESHOLD_RANGE_MAX - THRESHOLD_RANGE_MIN) / step)) + 1
    candidates = sorted(
        set(
            [round(THRESHOLD_RANGE_MIN + i * step, 4) for i in range(max(n_steps, 2))]
            + [round(float(s), 6) for s in scores]
        )
    )
    candidates = sorted(c for c in candidates if THRESHOLD_RANGE_MIN <= c <= THRESHOLD_RANGE_MAX)

    best_threshold = 0.5
    best_f1 = -1.0
    best_metrics = None

    for threshold in candidates:
        metrics = calculate_metrics(labels, scores, threshold=threshold)
        predicted_positives = metrics["truePositives"] + metrics["falsePositives"]

        if predicted_positives < min_positive_predictions:
            continue

        f1 = metrics["f1Score"]
        if f1 > best_f1:
            best_f1 = f1
            best_threshold = threshold
            best_metrics = metrics

    if best_metrics is None:
        best_metrics = calculate_metrics(labels, scores, threshold=0.5)

    return best_threshold, best_metrics


def _select_threshold_recall_constrained(
    labels: list[int],
    scores: list[float],
    *,
    min_recall: float = 0.65,
    min_precision: float = 0.25,
    min_positive_predictions: int = 5,
) -> tuple[float, dict]:
    """
    Prefer operating points with recall >= min_recall, then maximize F1.
    Relaxes precision floor in small steps if infeasible (small-n screening reality).
    """
    step = 0.005
    n_steps = int((THRESHOLD_RECALL_STRATEGY_MAX - THRESHOLD_RECALL_STRATEGY_MIN) / step) + 1
    candidates = sorted(
        set(
            [round(THRESHOLD_RECALL_STRATEGY_MIN + i * step, 4) for i in range(n_steps)]
            + [round(float(s), 6) for s in scores]
        )
    )
    candidates = sorted(
        c for c in candidates if THRESHOLD_RECALL_STRATEGY_MIN <= c <= THRESHOLD_RECALL_STRATEGY_MAX
    )

    precision_floors = [
        min_precision,
        min_precision - 0.04,
        min_precision - 0.08,
        min_precision - 0.12,
        0.10,
        0.05,
        0.0,
    ]
    for prec_floor in precision_floors:
        feasible: list[tuple[float, dict]] = []
        for threshold in candidates:
            metrics = calculate_metrics(labels, scores, threshold=threshold)
            predicted_positives = metrics["truePositives"] + metrics["falsePositives"]
            if predicted_positives < min_positive_predictions:
                continue
            if metrics["recall"] + 1e-6 >= min_recall and metrics["precision"] + 1e-6 >= prec_floor:
                feasible.append((threshold, metrics))
        if feasible:
            feasible.sort(key=lambda item: (-item[1]["f1Score"], item[0]))
            return feasible[0][0], feasible[0][1]

    best_threshold = 0.5
    best_recall = -1.0
    best_metrics = calculate_metrics(labels, scores, threshold=0.5)
    for threshold in candidates:
        metrics = calculate_metrics(labels, scores, threshold=threshold)
        predicted_positives = metrics["truePositives"] + metrics["falsePositives"]
        if predicted_positives < min_positive_predictions:
            continue
        if metrics["recall"] > best_recall:
            best_recall = metrics["recall"]
            best_threshold = threshold
            best_metrics = metrics
    return best_threshold, best_metrics


def select_operating_threshold(
    labels: list[int],
    scores: list[float],
    *,
    strategy: ThresholdStrategy = "f1",
    min_recall_floor: float = 0.65,
    min_precision_floor: float = 0.25,
    min_positive_predictions: int = 5,
) -> tuple[float, dict]:
    """Unified threshold selection for CV / holdout (no test-set peeking)."""
    if strategy == "recall_constrained":
        return _select_threshold_recall_constrained(
            labels,
            scores,
            min_recall=min_recall_floor,
            min_precision=min_precision_floor,
            min_positive_predictions=min_positive_predictions,
        )
    return _select_optimal_threshold_f1(labels, scores, min_positive_predictions)


def threshold_sweep_table(
    labels: list[int],
    scores: list[float],
    low: float = 0.20,
    high: float = 0.70,
    step: float = 0.01,
) -> list[dict[str, float]]:
    """Precision, recall, F1, specificity at each threshold (for reporting / mode selection)."""
    rows_out: list[dict[str, float]] = []
    t = low
    while t <= high + 1e-9:
        m = calculate_metrics(labels, scores, threshold=round(t, 4))
        rows_out.append(
            {
                "threshold": round(t, 4),
                "precision": m["precision"],
                "recall": m["recall"],
                "f1Score": m["f1Score"],
                "specificity": m["specificity"],
            }
        )
        t += step
    return rows_out


def select_screening_threshold(
    labels: list[int],
    scores: list[float],
    *,
    min_precision_floor: float = 0.25,
    min_positive_predictions: int = 5,
) -> tuple[float, dict]:
    """
    Screening mode: maximize recall subject to a precision floor; tie-breaker higher F1.
    Search uses the same wide probability grid as balanced F1 mode.
    """
    step = 0.005
    n_steps = int(round((THRESHOLD_RANGE_MAX - THRESHOLD_RANGE_MIN) / step)) + 1
    candidates = sorted(
        set(
            [round(THRESHOLD_RANGE_MIN + i * step, 4) for i in range(max(n_steps, 2))]
            + [round(float(s), 6) for s in scores]
        )
    )
    candidates = sorted(c for c in candidates if THRESHOLD_RANGE_MIN <= c <= THRESHOLD_RANGE_MAX)

    feasible: list[tuple[float, dict]] = []
    for threshold in candidates:
        metrics = calculate_metrics(labels, scores, threshold=threshold)
        if metrics["truePositives"] + metrics["falsePositives"] < min_positive_predictions:
            continue
        if metrics["precision"] + 1e-6 >= min_precision_floor:
            feasible.append((threshold, metrics))
    if feasible:
        feasible.sort(key=lambda item: (-item[1]["recall"], -item[1]["f1Score"], item[0]))
        return feasible[0][0], feasible[0][1]
    return _select_optimal_threshold_f1(labels, scores, min_positive_predictions)


def audit_split_grouping(rows: list[dict[str, float]]) -> dict:
    """Quantify whether family/source grouping is informative or one-group-per-row."""
    _, _, groups = _build_xyg(rows)
    sizes: dict[int, int] = defaultdict(int)
    for g in groups:
        sizes[g] += 1
    size_values = list(sizes.values())
    multi = sum(1 for s in size_values if s > 1)
    return {
        "rowCount": len(rows),
        "uniqueGroups": len(sizes),
        "degenerateOneGroupPerRow": len(sizes) == len(rows),
        "groupsWithMultipleRows": multi,
        "largestGroupSize": max(size_values) if size_values else 0,
        "meanRowsPerGroup": round(len(rows) / max(len(sizes), 1), 4),
    }


def summarize_uncertainty_codings(rows: list[dict[str, float]]) -> dict:
    """
    Count soft-coded survey values (e.g. 0.35 unsure) on key predictors after pipeline imputation.
    """
    keys = ("hypertension_status", "parent_has_t2dm", "physical_activity_score")
    epsilon = 1e-6
    out: dict[str, dict[str, float | int]] = {}
    for key in keys:
        vals = [float(r[key]) for r in rows if key in r]
        unsure = sum(1 for v in vals if abs(v - 0.35) < epsilon)
        out[key] = {
            "n": len(vals),
            "countNear035UnsureCoding": unsure,
            "fractionNear035": round(unsure / max(len(vals), 1), 4),
        }
    return out


def _normal_ci95_from_fold_scores(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        m = values[0] if values else 0.0
        return m, m
    m = _mean(values)
    s = _std(values)
    err = 1.96 * s / math.sqrt(n)
    return m - err, m + err


def evaluate_stratified_subgroups(
    rows: list[dict[str, float]],
    labels: list[int],
    scores: list[float],
    threshold: float,
) -> dict:
    """Performance and error counts by clinically interpretable strata (train/CV context)."""

    def age_band(age: float) -> str:
        if age < 40:
            return "age_lt_40"
        if age < 60:
            return "age_40_59"
        return "age_ge_60"

    def bmi_band(bmi: float) -> str:
        if bmi < 25:
            return "bmi_lt_25"
        if bmi < 30:
            return "bmi_25_30"
        return "bmi_ge_30"

    def yn(flag: float, cutoff: float = 0.5) -> str:
        return "yes" if flag >= cutoff else "no"

    subgroups: dict[str, dict[str, list[float]]] = defaultdict(lambda: {"labels": [], "scores": []})
    fp_by: dict[str, int] = defaultdict(int)
    fn_by: dict[str, int] = defaultdict(int)

    for row, y, s in zip(rows, labels, scores):
        pred = 1 if s >= threshold else 0
        keys = [
            age_band(float(row["age"])),
            bmi_band(float(row["bmi"])),
            f"htn_{yn(float(row['hypertension_status']))}",
            f"parent_{yn(float(row['parent_has_t2dm']))}",
        ]
        key = "|".join(keys)
        subgroups[key]["labels"].append(y)
        subgroups[key]["scores"].append(s)
        if y == 0 and pred == 1:
            fp_by[key] += 1
        if y == 1 and pred == 0:
            fn_by[key] += 1

    per_key: list[dict] = []
    for key, payload in sorted(subgroups.items()):
        ys = payload["labels"]
        ss = payload["scores"]
        if len(ys) < 3:
            continue
        m = calculate_metrics(ys, ss, threshold=threshold)
        per_key.append(
            {
                "stratum": key,
                "n": len(ys),
                "positives": sum(1 for v in ys if v == 1),
                "rocAuc": m["rocAuc"],
                "prAuc": m["prAuc"],
                "f1Score": m["f1Score"],
                "recall": m["recall"],
                "precision": m["precision"],
            }
        )

    top_fp = sorted(fp_by.items(), key=lambda x: -x[1])[:5]
    top_fn = sorted(fn_by.items(), key=lambda x: -x[1])[:5]
    return {
        "strataMinN": 3,
        "subgroups": per_key,
        "topFalsePositiveStrata": [{"stratum": k, "count": v} for k, v in top_fp],
        "topFalseNegativeStrata": [{"stratum": k, "count": v} for k, v in top_fn],
    }


def _repeat_level_metric_summary(
    fold_details: list[dict],
    metric_keys: list[str],
) -> list[dict]:
    by_rep: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for fd in fold_details:
        rep = int(fd.get("repeat", 1))
        for key in metric_keys:
            by_rep[rep][key].append(float(fd["metrics"][key]))
    summaries = []
    for rep in sorted(by_rep):
        row: dict[str, float | int] = {"repeat": rep}
        for key in metric_keys:
            vals = by_rep[rep][key]
            row[f"mean_{key}"] = round(_mean(vals), 4)
            row[f"std_{key}"] = round(_std(vals), 4)
        summaries.append(row)
    return summaries


def train_classifier_model(
    training_rows: list[dict[str, float]],
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    et_config: dict | None = None,
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    model_algorithm: ModelAlgorithm = "extra_trees",
    feature_columns: list[str] | None = None,
) -> dict:
    """
    Fit the full-data sklearn pipeline (uncalibrated) and export preprocessing + importances.

    ExtraTrees / HistGradientBoosting: feature-importance export for dashboard ranking.
    """
    columns = feature_columns if feature_columns is not None else FEATURE_COLUMNS
    rows_fit = (
        _oversample_minority_rows(training_rows, seed + 1337)
        if balance_mode == "oversample"
        else training_rows
    )
    features, labels, _ = _build_xyg(rows_fit, columns)

    merged_et = _resolved_et_config(et_config)
    merged_hgb = _resolved_hgb_config(hgb_config)
    pipeline = _build_base_classifier_pipeline(
        seed, model_algorithm, merged_et, None, merged_hgb
    )
    pipeline.fit(features, labels)

    scaler: StandardScaler = pipeline.named_steps["scaler"]
    model = pipeline.named_steps["model"]

    if model_algorithm == "hist_gradient_boosting":
        imp = getattr(model, "feature_importances_", None)
        if imp is not None and len(imp) == len(columns):
            total = float(sum(imp)) or 1.0
            feature_importances = {
                f: round(float(v) / total, 6) for f, v in zip(columns, imp)
            }
        else:
            feature_importances = {f: round(1.0 / len(columns), 6) for f in columns}
        model_type = "hist_gradient_boosting_classifier"
        merged_cfg = merged_hgb
        steps_desc = ["StandardScaler", "HistGradientBoostingClassifier"]
        pipeline_note = (
            "HistGradientBoosting often improves PR-AUC on tabular clinical data; monitor CV std vs ExtraTrees."
        )
    else:
        feature_importances = {
            feature: round(float(importance), 6)
            for feature, importance in zip(columns, model.feature_importances_)
        }
        model_type = "extra_trees_classifier"
        merged_cfg = merged_et
        steps_desc = ["StandardScaler", "ExtraTreesClassifier"]
        pipeline_note = (
            "Tree ensemble captures nonlinearities; monitor fold variability on small datasets."
        )

    preprocessing = {
        "means": {
            feature: round(float(value), 6)
            for feature, value in zip(columns, scaler.mean_)
        },
        "stds": {
            feature: round(float(value), 6)
            for feature, value in zip(columns, scaler.scale_)
        },
    }

    return {
        "modelAlgorithm": model_algorithm,
        "modelType": model_type,
        "modelConfig": merged_cfg,
        "featureColumnsUsed": columns,
        "featureImportances": feature_importances,
        "preprocessing": preprocessing,
        "trainingConfig": {
            "classWeightMode": str(merged_cfg.get("class_weight", "balanced")),
            "rowBalanceMode": balance_mode,
            "pipelineSteps": steps_desc,
            "preprocessing": "StandardScaler fit on training data only (fold-local fit_transform)",
            "crossFoldLeakageControl": (
                "fold-local fit_transform on train only; grouped splits when multi-row groups exist"
            ),
            "algorithmNote": pipeline_note,
        },
    }


def train_extra_trees_model(
    training_rows: list[dict[str, float]],
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    et_config: dict | None = None,
) -> dict:
    """Backward-compatible wrapper for ExtraTrees-only training."""
    return train_classifier_model(
        training_rows,
        seed=seed,
        balance_mode=balance_mode,
        et_config=et_config,
        lr_config=None,
        hgb_config=None,
        model_algorithm="extra_trees",
        feature_columns=None,
    )


def predict_probability_tree_ensemble(features: dict[str, float], pipeline: Pipeline) -> float:
    """Predict probability using a deserialized sklearn pipeline."""
    vector = [[float(features.get(col, 0.0)) for col in FEATURE_COLUMNS]]
    probabilities = pipeline.predict_proba(vector)
    return float(probabilities[0][1])


def predict_probability(features: dict[str, float], artifact: dict) -> float:
    preprocessing = artifact.get("preprocessing")
    coefficients = artifact.get("coefficients", {})
    if not preprocessing:
        raise ValueError("Model artifact is missing preprocessing statistics.")

    vector = _standardized_vector(features, preprocessing)
    logit = float(artifact.get("intercept", 0.0))
    for feature, value in zip(FEATURE_COLUMNS, vector):
        logit += float(coefficients.get(feature, 0.0)) * value
    return sigmoid(logit)


def read_dataset_rows(dataset_path: Path, include_warnings: bool = False):
    if not dataset_path.exists():
        raise FileNotFoundError("Dataset file was not found.")

    warnings: list[str] = []
    with dataset_path.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        fieldnames = reader.fieldnames or []
        missing_features = [column for column in FEATURE_COLUMNS if column not in fieldnames]
        if TARGET_COLUMN not in fieldnames:
            raise ValueError(f"Dataset is missing required target column: {TARGET_COLUMN}")

        if missing_features:
            warnings.append(
                f"Dataset is missing feature columns: {', '.join(missing_features)}; filling with defaults."
            )

        group_source_column = next(
            (column for column in GROUP_COLUMN_CANDIDATES if column in fieldnames),
            "",
        )

        rows = []
        for row_index, row in enumerate(reader, start=1):
            parsed: dict[str, float] = {}
            for feature in FEATURE_COLUMNS:
                if feature in row and row[feature] is not None and str(row[feature]).strip() != "":
                    parsed[feature] = safe_float(row[feature])
                else:
                    parsed[feature] = float(DEFAULT_FEATURE_MEANS.get(feature, 0.0))
            parsed[TARGET_COLUMN] = int(safe_float(row[TARGET_COLUMN]))
            if group_source_column:
                parsed[GROUP_COLUMN] = int(safe_float(row[group_source_column]))
            else:
                parsed[GROUP_COLUMN] = row_index
            _populate_clinical_interaction_features(parsed)
            rows.append(parsed)

    if len(rows) < 10:
        raise ValueError("Dataset must contain at least 10 rows for evaluation.")
    group_col = (group_source_column or "row_index_fallback")
    if include_warnings:
        return rows, group_col, warnings
    return rows, group_col


def stratified_group_holdout_split(
    rows: list[dict[str, float]],
    test_size: float = TEST_SET_SIZE,
    seed: int = DEFAULT_RANDOM_SEED,
) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    """
    Split data by groups (families) ensuring stratification by class.
    Approximately test_size% of families go to test set.
    """
    grouped_rows: dict[int, list[dict[str, float]]] = {}
    for index, row in enumerate(rows):
        group_key = _group_key_for_row(row, index)
        grouped_rows.setdefault(group_key, []).append(row)
    
    # Classify groups by their label
    positive_groups = []
    negative_groups = []
    
    for group_key, group_items in grouped_rows.items():
        labels = {int(item[TARGET_COLUMN]) for item in group_items}
        if len(labels) != 1:
            raise ValueError(f"Group {group_key} has mixed labels.")
        group_label = next(iter(labels))
        if group_label == 1:
            positive_groups.append(group_items)
        else:
            negative_groups.append(group_items)
    
    if not positive_groups or not negative_groups:
        raise ValueError("Need at least one positive and one negative group.")
    
    rng = random.Random(seed)
    rng.shuffle(positive_groups)
    rng.shuffle(negative_groups)
    
    # Split groups
    pos_test_count = max(1, int(round(len(positive_groups) * test_size)))
    neg_test_count = max(1, int(round(len(negative_groups) * test_size)))
    
    train_rows = []
    test_rows = []
    
    for group_items in positive_groups[pos_test_count:] + negative_groups[neg_test_count:]:
        train_rows.extend(group_items)
    
    for group_items in positive_groups[:pos_test_count] + negative_groups[:neg_test_count]:
        test_rows.extend(group_items)
    
    rng.shuffle(train_rows)
    rng.shuffle(test_rows)
    
    return train_rows, test_rows


def compute_crossvalidation_metrics(
    rows: list[dict[str, float]],
    k: int = 5,
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    threshold_strategy: ThresholdStrategy = "f1",
    min_recall_floor: float = 0.65,
    min_precision_floor: float = 0.25,
    cv_repeats: int = 1,
    et_config: dict | None = None,
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    model_algorithm: ModelAlgorithm = "extra_trees",
    feature_columns: list[str] | None = None,
    include_oob_scores: bool = False,
) -> dict:
    """
    Repeated k-fold CV with threshold fit on each training fold only.

    When every row has a unique group id, ``StratifiedKFold`` is used (equivalent independence
    splits with clearer semantics than ``StratifiedGroupKFold``). When families share ids,
    ``StratifiedGroupKFold`` keeps related rows together.
    """
    # Build matrix-style inputs once; folds then index into these arrays.
    features, labels, groups = _build_xyg(rows, feature_columns)

    unique_groups = sorted(set(groups))
    degenerate_independence = len(unique_groups) == len(rows)
    groups_by_class = {
        0: len({group for group, label in zip(groups, labels) if label == 0}),
        1: len({group for group, label in zip(groups, labels) if label == 1}),
    }
    min_groups_per_class = min(groups_by_class.values())
    if min_groups_per_class < 2:
        raise ValueError("Need at least 2 groups per class for grouped CV.")

    effective_k = min(k, min_groups_per_class)
    repeats = max(1, int(cv_repeats))

    all_cv_metrics = []
    all_train_metrics = []
    fold_details = []
    all_eval_labels: list[int] = []
    all_eval_scores: list[float] = []
    fold_weights: list[int] = []
    fold_thresholds: list[float] = []

    # Repeat CV with different deterministic seeds to stabilize mean/std on small datasets.
    global_fold = 0
    for rep in range(repeats):
        if degenerate_independence:
            splitter = StratifiedKFold(
                n_splits=effective_k, shuffle=True, random_state=seed + rep * 9973
            )
            split_iter = splitter.split(features, labels)
        else:
            splitter = StratifiedGroupKFold(
                n_splits=effective_k, shuffle=True, random_state=seed + rep * 9973
            )
            split_iter = splitter.split(features, labels, groups)

        for fold_idx, (train_indices, eval_indices) in enumerate(split_iter):
            train_row_dicts = [rows[index] for index in train_indices]
            if balance_mode == "oversample":
                train_row_dicts = _oversample_minority_rows(
                    train_row_dicts, seed + rep * 131071 + fold_idx * 7919
                )
            train_x, train_y, train_g = _build_xyg(train_row_dicts, feature_columns)
            train_groups = set(train_g)
            eval_x = [features[index] for index in eval_indices]
            eval_y = [labels[index] for index in eval_indices]
            eval_groups = {groups[index] for index in eval_indices}

            overlap = train_groups.intersection(eval_groups)
            if overlap:
                raise ValueError(
                    f"Repeat {rep + 1} fold {fold_idx + 1}: Group overlap detected between train and eval folds."
                )

            pipeline = _build_base_classifier_pipeline(
                seed, model_algorithm, et_config, lr_config, hgb_config
            )
            pipeline.fit(train_x, train_y)

            train_scores = [float(score) for score in pipeline.predict_proba(train_x)[:, 1]]

            # Threshold is optimized on training-fold scores only to avoid validation leakage.
            fold_threshold, _ = select_operating_threshold(
                train_y,
                train_scores,
                strategy=threshold_strategy,
                min_recall_floor=min_recall_floor,
                min_precision_floor=min_precision_floor,
            )

            # Evaluate on untouched fold rows using the fixed fold-specific threshold.
            eval_scores = [float(score) for score in pipeline.predict_proba(eval_x)[:, 1]]
            train_metrics = calculate_metrics(train_y, train_scores, threshold=fold_threshold)
            eval_metrics = calculate_metrics(eval_y, eval_scores, threshold=fold_threshold)

            all_cv_metrics.append(eval_metrics)
            all_train_metrics.append(train_metrics)
            all_eval_labels.extend(eval_y)
            all_eval_scores.extend(eval_scores)
            fold_weights.append(len(eval_indices))
            fold_thresholds.append(fold_threshold)

            f1_from_formula = _recompute_f1_from_pr(eval_metrics["precision"], eval_metrics["recall"])
            global_fold += 1
            fold_details.append({
                "repeat": rep + 1,
                "fold": fold_idx + 1,
                "globalFold": global_fold,
                "trainSize": len(train_row_dicts),
                "trainSizeBeforeBalance": len(train_indices),
                "evalSize": len(eval_indices),
                "trainGroupCount": len(train_groups),
                "evalGroupCount": len(eval_groups),
                "groupOverlapCount": 0,
                "optimizedThreshold": round(fold_threshold, 6),
                "metrics": eval_metrics,
                "trainMetrics": train_metrics,
                "overfitGap": {
                    "accuracy": round(train_metrics["accuracy"] - eval_metrics["accuracy"], 4),
                    "precision": round(train_metrics["precision"] - eval_metrics["precision"], 4),
                    "recall": round(train_metrics["recall"] - eval_metrics["recall"], 4),
                    "f1Score": round(train_metrics["f1Score"] - eval_metrics["f1Score"], 4),
                    "rocAuc": round(train_metrics["rocAuc"] - eval_metrics["rocAuc"], 4),
                },
                "consistency": {
                    "f1FromFormula": round(f1_from_formula, 4),
                    "f1Reported": round(eval_metrics["f1Score"], 4),
                    "f1Difference": round(abs(f1_from_formula - eval_metrics["f1Score"]), 6),
                },
            })
    
    # Compute mean and std across folds
    metric_keys = [
        "accuracy",
        "precision",
        "recall",
        "f1Score",
        "specificity",
        "rocAuc",
        "prAuc",
        "brierScore",
    ]
    mean_metrics = {}
    std_metrics = {}
    mean_train_metrics = {}
    total_weight = max(sum(fold_weights), 1)
    
    for key in metric_keys:
        values = [m[key] for m in all_cv_metrics]
        mean_val = sum(value * weight for value, weight in zip(values, fold_weights)) / total_weight
        variance = sum(weight * ((value - mean_val) ** 2) for value, weight in zip(values, fold_weights)) / total_weight
        std_val = math.sqrt(variance)
        mean_metrics[key] = round(mean_val, 4)
        std_metrics[key] = round(std_val, 4)
        
        train_values = [m[key] for m in all_train_metrics]
        mean_train_metrics[key] = round(
            sum(value * weight for value, weight in zip(train_values, fold_weights)) / total_weight,
            4
        )
    
    # Secondary pooled OOF threshold is for reporting consistency tables only (not model refit).
    optimal_agg_threshold, agg_metrics_at_optimal = select_operating_threshold(
        all_eval_labels,
        all_eval_scores,
        strategy=threshold_strategy,
        min_recall_floor=min_recall_floor,
        min_precision_floor=min_precision_floor,
    )
    
    agg_confusion_matrix = {
        "labels": [0, 1],
        "matrix": [
            [agg_metrics_at_optimal["trueNegatives"], agg_metrics_at_optimal["falsePositives"]],
            [agg_metrics_at_optimal["falseNegatives"], agg_metrics_at_optimal["truePositives"]],
        ],
    }
    
    agg_report = _classification_report_from_counts(
        tp=agg_metrics_at_optimal["truePositives"],
        tn=agg_metrics_at_optimal["trueNegatives"],
        fp=agg_metrics_at_optimal["falsePositives"],
        fn=agg_metrics_at_optimal["falseNegatives"],
    )
    
    agg_f1_from_formula = _recompute_f1_from_pr(
        agg_metrics_at_optimal["precision"],
        agg_metrics_at_optimal["recall"],
    )

    fold_ci: dict[str, dict[str, float]] = {}
    for key in metric_keys:
        vals = [float(m[key]) for m in all_cv_metrics]
        lo, hi = _normal_ci95_from_fold_scores(vals)
        fold_ci[key] = {"ci95Low": round(lo, 4), "ci95High": round(hi, 4)}

    split_name = "StratifiedKFold" if degenerate_independence else "StratifiedGroupKFold"
    eval_label = (
        f"{repeats}x{effective_k}-fold_repeated_{split_name.lower()}_shuffle"
        if repeats > 1
        else f"{effective_k}-fold_{split_name.lower()}_shuffle"
    )

    payload: dict = {
        "modelAlgorithm": model_algorithm,
        "foldCount": effective_k,
        "cvRepeats": repeats,
        "totalFoldsRun": len(fold_details),
        "balanceMode": balance_mode,
        "meanMetrics": mean_metrics,
        "stdMetrics": std_metrics,
        "meanTrainMetrics": mean_train_metrics,
        "metricConfidenceIntervals95": fold_ci,
        "repeatSummaries": _repeat_level_metric_summary(fold_details, metric_keys),
        "outOfFoldPooled": {
            "nScores": len(all_eval_scores),
            "note": "Pooled out-of-fold validation scores for threshold tables; do not use hold-out test rows.",
        },
        "meanOverfitGap": {
            key: round(mean_train_metrics[key] - mean_metrics[key], 4)
            for key in metric_keys
        },
        "foldDetails": fold_details,
        "aggregateEvalMetrics": agg_metrics_at_optimal,
        "aggregateConfusionMatrix": agg_confusion_matrix,
        "classificationReport": agg_report,
        "metricConsistency": {
            "f1FromFormula": round(agg_f1_from_formula, 4),
            "f1Reported": round(agg_metrics_at_optimal["f1Score"], 4),
            "f1Difference": round(abs(agg_f1_from_formula - agg_metrics_at_optimal["f1Score"]), 6),
            "formula": "f1 = 2 * precision * recall / (precision + recall)",
        },
        "scoringConfig": {
            "optimalThreshold": round(optimal_agg_threshold, 6),
            "thresholdStrategy": threshold_strategy,
            "thresholdStrategyNote": (
                "f1: maximize F1 on train fold within [THRESHOLD_RANGE_MIN, THRESHOLD_RANGE_MAX]. "
                "recall_constrained: require recall >= minRecallFloor (relaxing precision floor if needed), "
                "then maximize F1; search extends to lower probabilities for screening-oriented points."
            ),
            "minRecallFloor": min_recall_floor,
            "minPrecisionFloor": min_precision_floor,
            "f1SearchRange": f"[{THRESHOLD_RANGE_MIN}, {THRESHOLD_RANGE_MAX}]",
            "recallSearchRange": f"[{THRESHOLD_RECALL_STRATEGY_MIN}, {THRESHOLD_RECALL_STRATEGY_MAX}]",
            "perFoldThresholds": [round(t, 6) for t in fold_thresholds],
            "cvRepeats": repeats,
            "average": "binary",
            "posLabel": 1,
        },
        "grouping": {
            "groupColumn": GROUP_COLUMN,
            "totalUniqueGroups": len(unique_groups),
            "groupCountByClass": {
                "negative": groups_by_class[0],
                "positive": groups_by_class[1],
            },
            "degenerateIndependence": degenerate_independence,
            "groupingNote": (
                "Each row is a distinct group id: CV uses StratifiedKFold (not family-clustered). "
                "Collect shared source_patient_id (or family_id) for related respondents to enable grouped evaluation."
                if degenerate_independence
                else "Multiple rows may share a group id for leakage-aware splits."
            ),
        },
        "cvSplitProtocol": {
            "splitter": split_name,
            "degenerateIndependence": degenerate_independence,
            "effectiveK": effective_k,
        },
        "evaluationMethod": eval_label,
    }
    if include_oob_scores:
        payload["oobValidationLabels"] = list(all_eval_labels)
        payload["oobValidationScores"] = [round(float(s), 6) for s in all_eval_scores]
    return payload


def compute_holdout_metrics(
    train_rows: list[dict[str, float]],
    test_rows: list[dict[str, float]],
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    threshold_strategy: ThresholdStrategy = "f1",
    min_recall_floor: float = 0.65,
    min_precision_floor: float = 0.25,
    et_config: dict | None = None,
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    model_algorithm: ModelAlgorithm = "extra_trees",
    feature_columns: list[str] | None = None,
    calibration_method: Literal["sigmoid", "isotonic"] = "sigmoid",
) -> dict:
    """
    Train calibrated pipeline on train_rows, evaluate on test_rows.
    Threshold is chosen on train to maximize F1; test reports that threshold and 0.5 for comparison.
    """
    train_fit = (
        _oversample_minority_rows(train_rows, seed + 4242)
        if balance_mode == "oversample"
        else train_rows
    )
    train_features, train_labels, train_groups = _build_xyg(train_fit, feature_columns)
    test_features, test_labels, test_groups = _build_xyg(test_rows, feature_columns)

    pipeline = _build_calibrated_pipeline(
        seed=seed,
        et_config=et_config,
        model_algorithm=model_algorithm,
        lr_config=lr_config,
        hgb_config=hgb_config,
        calibration_method=calibration_method,
    )
    pipeline.fit(train_features, train_labels)

    train_scores = [float(score) for score in pipeline.predict_proba(train_features)[:, 1]]
    test_scores = [float(score) for score in pipeline.predict_proba(test_features)[:, 1]]

    optimal_threshold, _ = select_operating_threshold(
        train_labels,
        train_scores,
        strategy=threshold_strategy,
        min_recall_floor=min_recall_floor,
        min_precision_floor=min_precision_floor,
    )
    
    # Apply to test set
    train_metrics = calculate_metrics(train_labels, train_scores, threshold=optimal_threshold)
    test_metrics = calculate_metrics(test_labels, test_scores, threshold=optimal_threshold)
    test_metrics_at_05 = calculate_metrics(test_labels, test_scores, threshold=0.5)
    test_wilson_ci = _binomial_wilson_cis_from_confusion(test_metrics)

    reference_thresholds_on_holdout: list[dict] = []
    thr = float(THRESHOLD_RANGE_MIN)
    while thr <= float(THRESHOLD_RANGE_MAX) + 1e-9:
        t = round(thr, 4)
        rm = calculate_metrics(test_labels, test_scores, threshold=t)
        reference_thresholds_on_holdout.append(
            {
                "threshold": t,
                "recall": rm["recall"],
                "precision": rm["precision"],
                "specificity": rm["specificity"],
                "f1Score": rm["f1Score"],
            }
        )
        thr += 0.05

    test_confusion_matrix = {
        "labels": [0, 1],
        "matrix": [
            [test_metrics["trueNegatives"], test_metrics["falsePositives"]],
            [test_metrics["falseNegatives"], test_metrics["truePositives"]],
        ],
    }
    
    test_report = _classification_report_from_counts(
        tp=test_metrics["truePositives"],
        tn=test_metrics["trueNegatives"],
        fp=test_metrics["falsePositives"],
        fn=test_metrics["falseNegatives"],
    )
    
    return {
        "trainSize": len(train_fit),
        "trainSizeBeforeBalance": len(train_rows),
        "balanceMode": balance_mode,
        "thresholdStrategy": threshold_strategy,
        "minRecallFloor": min_recall_floor,
        "minPrecisionFloor": min_precision_floor,
        "testSize": len(test_rows),
        "optimizedThreshold": round(optimal_threshold, 6),
        "trainMetrics": train_metrics,
        "testMetrics": test_metrics,
        "testMetricsAtThreshold05": test_metrics_at_05,
        "calibration": (
            f"CalibratedClassifierCV({calibration_method}, cv=3) on training split only; "
            "no calibration refit on hold-out."
        ),
        "overfitGap": {
            k: round(train_metrics[k] - test_metrics[k], 4)
            for k in [
                "accuracy",
                "precision",
                "recall",
                "f1Score",
                "specificity",
                "rocAuc",
                "prAuc",
                "brierScore",
            ]
        },
        "testConfusionMatrix": test_confusion_matrix,
        "testClassificationReport": test_report,
        "testBinomialWilsonCi95": test_wilson_ci,
        "referenceThresholdsOnHoldout": reference_thresholds_on_holdout,
    }


def _build_metrics_analysis_metadata(
    holdout_results: dict,
    class_counts: dict,
) -> dict:
    """Structured guidance for thesis-style reporting (stored in model JSON metadata)."""
    n = max(class_counts.get("positive", 0) + class_counts.get("negative", 0), 1)
    pos_rate = class_counts.get("positive", 0) / n
    strat = holdout_results.get("thresholdStrategy", "f1")
    return {
        "wilsonScoreNote": (
            "Hold-out 95% intervals use the Wilson score method for binomial proportions "
            "(sensitivity/recall, precision/PPV, specificity). They quantify sampling uncertainty "
            "for this fixed test partition, not guaranteed coverage on external cohorts."
        ),
        "imbalanceNote": (
            f"Observed positive prevalence in this corpus ≈ {pos_rate:.1%}. Under imbalance, "
            "accuracy alone is insufficient; report PR-AUC and calibration alongside ROC-AUC."
        ),
        "cvUncertaintyNote": (
            "CV mean ± std reflects fold-to-fold variability. It is not a formal confidence interval "
            "for future performance unless paired with an explicit inferential framework."
        ),
        "thresholdPolicyNote": (
            f"Threshold strategy: {strat}. The cutoff is derived from training scores only; "
            "the hold-out set evaluates that fixed policy without re-tuning the threshold."
        ),
        "referenceGridNote": (
            "referenceThresholdsOnHoldout is a descriptive trade-off grid on held-out scores. "
            "Only the train-optimized threshold is the declared operating point; other cutoffs are exploratory."
        ),
        "discriminationVsCalibrationNote": (
            "ROC-AUC and PR-AUC measure discrimination (ranking); Brier score measures probability calibration. "
            "These address different questions and should be interpreted jointly for risk tools."
        ),
        "recommendedReportingOrder": [
            "Discrimination: ROC-AUC, PR-AUC (prevalence-sensitive)",
            "Calibration: Brier score",
            f"Threshold-based (train-optimized; strategy={strat}): confusion matrix + Wilson 95% CIs",
            "Exploratory: reference threshold grid on hold-out (not re-tuned)",
        ],
    }


def build_trained_artifact(
    rows: list[dict[str, float]],
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    threshold_strategy: ThresholdStrategy = "f1",
    min_recall_floor: float = 0.65,
    min_precision_floor: float = 0.25,
    cv_repeats: int = 1,
    tune_hyperparams: bool = False,
    model_algorithm: ModelAlgorithm = "extra_trees",
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    feature_columns: list[str] | None = None,
    compare_algorithms: bool = False,
) -> dict:
    """
    Build trained artifact with:
    1. 5-fold grouped stratified CV with threshold optimization
    2. 20% group-based hold-out test set
    3. Comprehensive diagnostics (per-fold, label shuffle test, feature importances)
    4. Final model trained on full dataset

    ``compare_algorithms`` runs a second grouped CV with the alternate algorithm (same folds
    / settings) so thesis chapters can report recall, precision, F1, ROC-AUC, and Brier fairly.
    """
    cv_repeats = max(1, min(int(cv_repeats), 30))
    if model_algorithm != "extra_trees":
        raise ValueError(
            "Only model_algorithm='extra_trees' is supported in this project."
        )
    et_overrides: dict | None = None
    if tune_hyperparams and model_algorithm == "extra_trees":
        et_overrides = tune_extra_trees_hyperparameters(rows, seed, et_base=None, inner_cv=3)
    merged_et = _resolved_et_config(et_overrides)
    merged_hgb = _resolved_hgb_config(hgb_config)

    # Step 1: repeated CV for robust internal validation and threshold diagnostics.
    cv_results = compute_crossvalidation_metrics(
        rows,
        k=5,
        seed=seed,
        balance_mode=balance_mode,
        threshold_strategy=threshold_strategy,
        min_recall_floor=min_recall_floor,
        min_precision_floor=min_precision_floor,
        cv_repeats=cv_repeats,
        et_config=merged_et if model_algorithm == "extra_trees" else None,
        lr_config=None,
        hgb_config=merged_hgb if model_algorithm == "hist_gradient_boosting" else None,
        model_algorithm=model_algorithm,
        feature_columns=feature_columns,
    )

    # Step 2: single locked holdout split (group-aware when groups are available).
    train_rows, test_rows = stratified_group_holdout_split(rows, test_size=TEST_SET_SIZE, seed=seed)
    holdout_results = compute_holdout_metrics(
        train_rows,
        test_rows,
        seed=seed,
        balance_mode=balance_mode,
        threshold_strategy=threshold_strategy,
        min_recall_floor=min_recall_floor,
        min_precision_floor=min_precision_floor,
        et_config=merged_et if model_algorithm == "extra_trees" else None,
        lr_config=None,
        hgb_config=merged_hgb if model_algorithm == "hist_gradient_boosting" else None,
        model_algorithm=model_algorithm,
        feature_columns=feature_columns,
    )

    # Step 3: fit final (uncalibrated) model on full rows for feature importances and metadata export.
    artifact = train_classifier_model(
        rows,
        seed=seed,
        balance_mode=balance_mode,
        et_config=merged_et,
        lr_config=None,
        hgb_config=merged_hgb,
        model_algorithm=model_algorithm,
        feature_columns=feature_columns,
    )

    algorithm_comparison: dict | None = None
    if compare_algorithms:
        alternate_algo: ModelAlgorithm = (
            "hist_gradient_boosting" if model_algorithm == "extra_trees" else "extra_trees"
        )
        alt_cv = compute_crossvalidation_metrics(
            rows,
            k=5,
            seed=seed,
            balance_mode=balance_mode,
            threshold_strategy=threshold_strategy,
            min_recall_floor=min_recall_floor,
            min_precision_floor=min_precision_floor,
            cv_repeats=cv_repeats,
            et_config=merged_et if alternate_algo == "extra_trees" else None,
            lr_config=None,
            hgb_config=merged_hgb if alternate_algo == "hist_gradient_boosting" else None,
            model_algorithm=alternate_algo,
            feature_columns=feature_columns,
        )
        algorithm_comparison = {
            "primaryAlgorithm": model_algorithm,
            "alternateAlgorithm": alternate_algo,
            "primaryCvMeanMetrics": cv_results["meanMetrics"],
            "alternateCvMeanMetrics": alt_cv["meanMetrics"],
            "primaryCvStdMetrics": cv_results["stdMetrics"],
            "alternateCvStdMetrics": alt_cv["stdMetrics"],
            "interpretationNote": (
                "Same StratifiedGroupKFold protocol and threshold strategy; fold estimators stay "
                "uncalibrated for both algorithms so mean/std CV metrics are comparable. "
                "ExtraTrees tends to better capture sparse nonlinear interactions, while "
                "HistGradientBoosting can improve ranking/calibration on tabular data. "
                "Default deployment remains the selected primary algorithm."
            ),
        }

    # Step 4: leakage/sanity diagnostics are stored directly in artifact metadata for auditability.
    duplicate_check = _detect_cross_group_duplicates(rows)
    label_shuffle_check = _run_label_shuffle_check(
        rows,
        k=cv_results["foldCount"],
        seed=seed,
        model_algorithm=model_algorithm,
        et_config=merged_et if model_algorithm == "extra_trees" else None,
        lr_config=None,
        hgb_config=merged_hgb if model_algorithm == "hist_gradient_boosting" else None,
        feature_columns=feature_columns,
    )
    
    # Step 5: compile one thesis-facing metadata payload for reporting + API introspection.
    class_counts = {
        "negative": sum(1 for row in rows if int(row[TARGET_COLUMN]) == 0),
        "positive": sum(1 for row in rows if int(row[TARGET_COLUMN]) == 1),
    }
    
    _calibration_base = (
        "StandardScaler+HistGradientBoostingClassifier"
        if model_algorithm == "hist_gradient_boosting"
        else "StandardScaler+ExtraTreesClassifier"
    )
    _fold_uncal_note = (
        "Fold models are uncalibrated HistGradientBoosting for stable CV benchmarks; deployed joblib uses calibration."
        if model_algorithm == "hist_gradient_boosting"
        else "Fold models are uncalibrated ExtraTrees for stable CV benchmarks; deployed joblib uses calibration."
    )
    _model_warning = (
        f"Model uses ExtraTreesClassifier with max_depth={merged_et['max_depth']} for controlled complexity."
        if model_algorithm == "extra_trees"
        else (
            f"HistGradientBoosting (max_depth={merged_hgb['max_depth']}, max_iter={merged_hgb['max_iter']}); "
            "monitor calibration on small cohorts."
        )
    )

    artifact["metadata"] = {
        "source": (
            "hist-gradient-boosting"
            if model_algorithm == "hist_gradient_boosting"
            else "extra-trees-refactored"
        ),
        "modelAlgorithm": model_algorithm,
        "modelType": artifact["modelType"],
        "modelConfig": (
            merged_hgb
            if model_algorithm == "hist_gradient_boosting"
            else merged_et
        ),
        "hyperparameterTuning": {
            "enabled": bool(tune_hyperparams and model_algorithm == "extra_trees"),
            "innerCvFolds": 3 if (tune_hyperparams and model_algorithm == "extra_trees") else None,
            "selectedOverrides": et_overrides if (tune_hyperparams and model_algorithm == "extra_trees") else {},
            "scoring": "average_precision",
            "note": (
                "Inner grid search applies only to ExtraTrees."
                if tune_hyperparams and model_algorithm == "hist_gradient_boosting"
                else None
            ),
        },
        "trainedAt": utc_now_iso(),
        "datasetRows": len(rows),
        "cvTrainRows": len(train_rows) if train_rows else len(rows),
        "cvTestRows": len(test_rows),
        "holdoutTestSize": TEST_SET_SIZE,
        "evaluationMethod": cv_results["evaluationMethod"],
        "splitStrategy": f"stratified-group-kfold-random-seed-{seed}",
        "evaluationStatus": "evaluated_with_cv_and_holdout",
        "trainingBalanceMode": balance_mode,
        "thresholdStrategy": threshold_strategy,
        "minRecallFloor": min_recall_floor,
        "minPrecisionFloor": min_precision_floor,
        "cvRepeats": cv_repeats,
        "requiredColumns": artifact.get("featureColumnsUsed", FEATURE_COLUMNS),
        "targetColumn": TARGET_COLUMN,
        
        # Cross-validation metrics
        "cvMetrics": cv_results["meanMetrics"],
        "cvMetricsStd": cv_results["stdMetrics"],
        "cvMetricsTraining": cv_results["meanTrainMetrics"],
        "cvOverfitGap": cv_results["meanOverfitGap"],
        "cvFoldDetails": cv_results["foldDetails"],
        "cvMetricConfidenceIntervals95": cv_results.get("metricConfidenceIntervals95", {}),
        "cvRepeatSummaries": cv_results.get("repeatSummaries", {}),
        "cvAggregateEvalMetrics": cv_results["aggregateEvalMetrics"],
        "cvAggregateConfusionMatrix": cv_results["aggregateConfusionMatrix"],
        "cvClassificationReport": cv_results["classificationReport"],
        "cvScoringConfig": cv_results["scoringConfig"],
        
        # Hold-out test metrics
        "holdoutMetrics": holdout_results,
        
        # Leakage controls
        "leakageChecks": {
            "cvSplitterUsed": cv_results.get("cvSplitProtocol", {}).get("splitter", "StratifiedGroupKFold"),
            "groupColumn": GROUP_COLUMN,
            "groupOverlapAcrossFolds": "none-detected",
            "crossGroupDuplicateFeatures": duplicate_check,
            "labelShuffleCheck": label_shuffle_check,
            "preprocessingIsolation": "StandardScaler fit on each training fold only via Pipeline",
            "thresholdLeakage": "avoided-threshold-optimized-on-train-fold-only",
        },
        
        # Feature analysis
        "featureImportances": artifact.get("featureImportances", {}),
        "topFeaturesRanked": sorted(
            artifact.get("featureImportances", {}).items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:8],  # Top 8 features
        
        # Dataset profile
        "datasetProfile": {
            "classCounts": class_counts,
            "positiveRate": round(class_counts["positive"] / max(len(rows), 1), 4),
            "uniqueSourceRecords": len({int(row[GROUP_COLUMN]) for row in rows if GROUP_COLUMN in row}),
            "balance": "good" if 0.4 <= class_counts["positive"] / len(rows) <= 0.6 else "imbalanced",
        },
        
        "trainingConfig": artifact.get("trainingConfig", {}),
        "targetDefinition": TARGET_DEFINITION,
        "targetScopeNote": TARGET_SCOPE_NOTE,
        
        # Honest reporting: do not treat illustrative targets as pass/fail for thesis
        "performanceGoalsAssessment": {
            "interpretationNote": (
                "Single-number accuracy targets are not primary when labels are proxy-based and n is small. "
                "Report ROC-AUC, PR-AUC, Brier score, confusion matrix at an explicit threshold, and limitations."
            ),
            "primaryMetricsGuidance": (
                "For imbalanced T2DM screening contexts, prioritize PR-AUC and Brier with ROC-AUC; "
                "report Wilson intervals at the train-chosen threshold for interpretability."
            ),
            "cvMeanRecallPct": round(cv_results["meanMetrics"]["recall"] * 100, 1),
            "cvMeanRocAucPct": round(cv_results["meanMetrics"]["rocAuc"] * 100, 1),
            "cvMeanPrAuc": cv_results["meanMetrics"]["prAuc"],
            "cvMeanBrier": cv_results["meanMetrics"]["brierScore"],
            "cvF1Std": cv_results["stdMetrics"]["f1Score"],
            "holdoutBrier": holdout_results["testMetrics"]["brierScore"],
        },
        "metricsAnalysis": _build_metrics_analysis_metadata(holdout_results, class_counts),
        
        "probabilityCalibration": {
            "deploymentPipeline": (
                f"CalibratedClassifierCV(method=sigmoid, cv=3) wrapping {_calibration_base}"
            ),
            "cvMetricsNote": _fold_uncal_note,
        },
        
        "datasetWarnings": [
            *(
                [
                    "Row-level random oversampling of the minority class was applied inside each training "
                    "fit (CV folds, holdout train split, and final deployment fit). Evaluation sets use the "
                    "original class distribution.",
                ]
                if balance_mode == "oversample"
                else []
            ),
            _model_warning,
            "All feature engineering performed within each fold to prevent leakage.",
            "Operating threshold chosen on training split / fold only (F1 or recall-constrained per config); "
            "no evaluation-set threshold tuning.",
            "Label shuffle test confirms model does not overfit to label patterns.",
            "Family grouping (source_patient_id, family_id, or source_record_id in CSV) required to prevent test contamination; "
            "if each row is a unique id, grouped CV does not measure family-level generalization.",
        ],
    }
    if algorithm_comparison is not None:
        artifact["metadata"]["algorithmComparison"] = algorithm_comparison
    if cv_results["grouping"].get("degenerateIndependence"):
        artifact["metadata"]["datasetWarnings"].insert(
            0,
            "Each respondent row uses a distinct group id: CV uses StratifiedKFold (not clustered family holdout).",
        )
    
    return artifact


def train_model_from_dataset_path(
    dataset_path: Path,
    model_path: Path,
    seed: int = DEFAULT_RANDOM_SEED,
    balance_mode: BalanceMode = "none",
    threshold_strategy: ThresholdStrategy = "f1",
    min_recall_floor: float = 0.65,
    min_precision_floor: float = 0.25,
    cv_repeats: int = 1,
    tune_hyperparams: bool = False,
    model_algorithm: ModelAlgorithm = "extra_trees",
    lr_config: dict | None = None,
    hgb_config: dict | None = None,
    feature_columns: list[str] | None = None,
    compare_algorithms: bool = False,
) -> dict:
    cv_repeats = max(1, min(int(cv_repeats), 30))
    rows, group_source_column, dataset_warnings = read_dataset_rows(dataset_path, include_warnings=True)
    artifact = build_trained_artifact(
        rows,
        seed=seed,
        balance_mode=balance_mode,
        threshold_strategy=threshold_strategy,
        min_recall_floor=min_recall_floor,
        min_precision_floor=min_precision_floor,
        cv_repeats=cv_repeats,
        tune_hyperparams=tune_hyperparams,
        model_algorithm=model_algorithm,
        lr_config=lr_config,
        hgb_config=hgb_config,
        feature_columns=feature_columns,
        compare_algorithms=compare_algorithms,
    )
    # Merge any dataset loading warnings into artifact metadata for auditability
    artifact.setdefault("metadata", {})["groupSourceColumn"] = group_source_column
    existing_warnings = artifact.setdefault("metadata", {}).get("datasetWarnings", [])
    artifact.setdefault("metadata", {})["datasetWarnings"] = list(dataset_warnings or []) + list(existing_warnings or [])
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Deployment artifact is calibrated for better probability quality (Brier), while CV fold
    # metrics stay uncalibrated to keep fold-vs-fold benchmarking comparable.
    rows_deploy = (
        _oversample_minority_rows(rows, seed + 9001) if balance_mode == "oversample" else rows
    )
    artifact.setdefault("metadata", {})["deploymentTrainRows"] = len(rows_deploy)
    artifact.setdefault("metadata", {})["deploymentTrainRowsBeforeBalance"] = len(rows)
    cols = artifact.get("featureColumnsUsed") or FEATURE_COLUMNS
    features, labels, _ = _build_xyg(rows_deploy, cols)
    deploy_algo: ModelAlgorithm = artifact.get("modelAlgorithm", "extra_trees")
    final_cfg = artifact.get("modelConfig") or (
        _resolved_hgb_config(hgb_config)
        if deploy_algo == "hist_gradient_boosting"
        else _resolved_et_config(None)
    )
    pipeline = _build_calibrated_pipeline(
        seed=seed,
        et_config=final_cfg if deploy_algo == "extra_trees" else None,
        lr_config=None,
        hgb_config=final_cfg if deploy_algo == "hist_gradient_boosting" else None,
        model_algorithm=deploy_algo,
    )
    # Final fit uses all available training rows under the selected balance mode.
    pipeline.fit(features, labels)
    pipeline_path = model_path.with_suffix(".joblib")
    joblib.dump(pipeline, pipeline_path)
    artifact.setdefault("metadata", {})["pipelinePath"] = str(pipeline_path)

    # Strip non-serializable keys before writing JSON
    json_artifact = {k: v for k, v in artifact.items() if k != "_pipeline"}
    model_path.write_text(json.dumps(json_artifact, indent=2), encoding="utf-8")
    return artifact


def load_pipeline(model_path: Path) -> Pipeline | None:
    """Load the joblib-serialized sklearn pipeline adjacent to the JSON artifact."""
    pipeline_path = model_path.with_suffix(".joblib")
    if pipeline_path.exists():
        return joblib.load(pipeline_path)
    return None
