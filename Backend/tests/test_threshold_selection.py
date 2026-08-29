"""Threshold selection for screening (recall-constrained)."""

from descend.ml.modeling import (
    DEFAULT_MIN_PRECISION_FLOOR,
    DEFAULT_MIN_RECALL_FLOOR,
    DEFAULT_THRESHOLD_STRATEGY,
    _select_threshold_recall_constrained,
    select_operating_threshold,
)


def test_defaults_are_screening_oriented():
    assert DEFAULT_THRESHOLD_STRATEGY == "recall_constrained"
    assert DEFAULT_MIN_RECALL_FLOOR == 0.82
    assert DEFAULT_MIN_PRECISION_FLOOR == 0.70


def test_recall_constrained_picks_highest_cutoff_that_hits_recall():
    labels = [1] * 10 + [0] * 10
    scores = [0.90] * 8 + [0.50, 0.50] + [0.20] * 8 + [0.52, 0.52]
    threshold, metrics = _select_threshold_recall_constrained(
        labels, scores, min_recall=0.82, min_precision=0.70
    )
    assert 0.45 <= threshold <= 0.58
    assert threshold <= 0.50 + 1e-9
    assert metrics["recall"] + 1e-6 >= 0.82
    assert metrics["precision"] + 1e-6 >= 0.70
    assert metrics["falseNegatives"] <= 2


def test_select_operating_threshold_default_is_recall_constrained():
    labels = [1] * 12 + [0] * 12
    scores = [0.88] * 10 + [0.47, 0.47] + [0.15] * 10 + [0.40, 0.41]
    threshold, metrics = select_operating_threshold(labels, scores)
    assert metrics["recall"] + 1e-6 >= 0.82
    assert 0.20 <= threshold <= 0.58
