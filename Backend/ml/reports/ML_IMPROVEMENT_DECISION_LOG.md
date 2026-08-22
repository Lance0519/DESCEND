# ML improvement cycle — decision log

## Context

- Dataset: 426 rows, 31.2% positive (`training_dataset.csv`).
- Group column resolved to `source_patient_id`; audit shows **426 unique groups** → one row per group (degenerate for grouped CV).
- **Evaluation change:** cross-validation now uses **StratifiedKFold** when degenerate, instead of StratifiedGroupKFold, so reported CV reflects stratified row sampling with explicit semantics. Hold-out remains **group-based row assignment** (here equivalent to stratified row hold-out because groups are singletons).
- **Leakage guard:** all nested tuning and repeated CV metrics use **training split only** (340 rows) after locking the same 20% hold-out (86 rows) used for final reporting. Thresholds for operating modes are derived from **train / OOF** scores only.

## Candidate outcomes (train-only 5-fold × 3 repeats)

| Candidate | ROC-AUC mean | ROC-AUC std | PR-AUC mean | F1 std |
|-----------|--------------|-------------|-------------|--------|
| ExtraTrees baseline | 0.7369 | 0.0543 | 0.6358 | 0.0797 |
| LogisticRegression L2 balanced | **0.7478** | **0.0500** | 0.6194 | **0.0535** |
| HistGradientBoosting baseline | 0.6765 | 0.0535 | 0.5610 | 0.0753 |
| ExtraTrees + explicit interactions | 0.7364 | 0.0540 | 0.6342 | 0.0789 |
| ExtraTrees pruned | 0.7442 | 0.0557 | 0.6363 | 0.0705 |
| ExtraTrees nested tuned | 0.7410 | 0.0580 | 0.6373 | 0.0667 |
| HGB nested tuned | 0.6971 | 0.0604 | 0.5920 | 0.0591 |

## Selection

**Chosen configuration: `lr_baseline` (L2 logistic, standardized inputs, `class_weight=balanced`).**

Reasons:

1. **Primary acceptance met:** ROC-AUC mean **+0.0109** vs ExtraTrees baseline on the same train-only protocol, while ROC-AUC std **does not increase** (0.0500 ≤ 0.0543) and F1 std **decreases** (0.0535 ≤ 0.0797). PR-AUC mean is slightly lower than baseline; the gate is disjunctive (ROC **or** PR lift), so the run still passes the stated primary condition.
2. **Stability:** Logistic regression exhibits the lowest combined variance on precision/F1-relevant axes among strong ROC contenders.
3. **Rejected alternatives:** HistGradientBoosting (default and tuned) underperformed ExtraTrees on this sample under the same pipeline. ExtraTrees variants (interactions, pruning, nested tuning) did not simultaneously meet the primary lift + std constraints vs the ET baseline. Pruned ET improved F1 std but failed the +0.01 ROC mean lift.

## Calibration

- Deployment-style metrics use **CalibratedClassifierCV** fit **only on train**, with **sigmoid** as default; **isotonic** evaluated in the JSON report. Hold-out thresholds are **never** used during calibration fit.

## Risks

- Train-only CV means metrics are **not comparable** to a historical run that included hold-out rows inside CV folds.
- Logistic model may underrepresent strong nonlinear lineage effects that trees capture; monitor domain expert review.
- Isotonic calibration can overfit when calibration folds are tiny; sigmoid remained the default recommendation.

## Next data collection (from error strata)

See `ml_improvement_experiment.json` → `subgroupAnalysis` for counts. Prioritize:

1. Strata with highest **false negative** counts at the balanced threshold (missed T2DM cases)—enrich positives in those age/BMI/hypertension/parent-history bands.
2. Strata with high **false positives** under screening mode—collect cleaner labels and blood-work confirmation for uncertain hypertension / parent history coding (0.35 “unsure” fields are non-trivial).
