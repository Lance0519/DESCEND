# DESCEND Risk Scoring Documentation

Educational awareness scoring for the DESCEND rebuild. This is **not a medical diagnosis**.

Clinician one-pager (factor % ↔ survey answers): [CLINICIAN_FACTOR_PERCENTAGES.md](CLINICIAN_FACTOR_PERCENTAGES.md).

## Pipeline

1. Survey answers → feature builder (legacy ExtraTrees features)
2. ExtraTrees (or logistic fallback) → model probability `p_model`
3. Structural lineage / metabolic blend → `p_struct`
4. Soft adjustment (lifestyle + optional blood + early-onset ages) → `p_final`
5. Risk band assignment from `p_final`

```text
features → ExtraTrees → structural blend → soft_adjust → bands
```

## Risk bands

| Band | Probability | Display % |
|------|-------------|-----------|
| Low | `p < 0.34` | 0–33% |
| Moderate | `0.34 ≤ p < 0.67` | 34–66% |
| High | `p ≥ 0.67` | 67–100% |

Pedigree upgrade (legacy): if Low but `0.24 ≤ p < 0.34` with strong lineage burden, displayed band may become Moderate while the numeric probability stays unchanged.

## Trained model feature importances (ExtraTrees)

From `t2dm_risk_model.json` after the retrain on the 1080-row `(Responses)` export (2026-08-29). Importances shift when the training CSV or labels change; they are not the family-formula weights.

| Feature | Importance |
|---------|------------|
| propagationProbability | ~28.3% |
| lineageRiskIndex | ~20.5% |
| weightedFamilyScore | ~16.1% |
| hereditary_load_index | ~12.6% |
| bmi | ~5.8% |
| parent_has_t2dm | ~5.6% |
| aunts_uncles_score | ~4.0% |
| siblings_diabetes_count | ~3.2% |
| metabolic_risk_index | ~1.3% |
| age | ~1.2% |
| hypertension_status | ~0.7% |
| user_is_male | ~0.4% |
| activity_metabolic_index | ~0.1% |
| physical_activity_score | ~0.1% |

The four lineage-derived features now carry ~77.5% of the importance, up from ~55% on the previous artifact — the added responses pushed the model further onto family-history signal.

### Binary operating threshold (evaluation only)

Default strategy is **recall-constrained**, not F1. Target: recall ≥ 0.82 with precision ≥ 0.70, search 0.45–0.58 first. Current artifact cutoff: **0.58**. Risk bands (Low / Moderate / High) still use 0.34 / 0.67 and are not this cutoff.

## Core formulas (legacy)

### BMI

```
BMI = weightKg / (heightCm / 100)²
```

### Weighted family score (WFS)

For each of six relatives (parents distance 1, grandparents distance 2):

```
contribution = status / distance
WFS = Σ contribution
```

Status encoding: yes=1.0, no=0.0, unknown=0.35.

### Lineage risk index (LRI)

```
LRI = 0.36·WFS + 0.30·F1 + 0.20·F2 + 0.07·min(ext, 6)
```

- `F1` = count of parents with T2DM yes  
- `F2` = count of grandparents with T2DM yes  
- `ext` = sibling + aunt/uncle diabetes counts  

### Propagation probability

```
P = 1 − (1−0.18)^F1 · (1−0.08)^F2 · (1−0.04)^F3
```

### Hereditary load index (HLI)

```
lineage_strength = min(1.2, 0.48·parent + 0.22·F1/2 + 0.26·F2/4 + 0.14·WFS/3.5)
HLI = lineage_strength · (1 + 0.42·(sib_count + aunts_score))
```

### Hypertension blend

```
hyp = min(1, self + 0.25·father + 0.25·mother)
```

### Interaction features

```
metabolic_risk_index = age × (bmi / 24)
activity_metabolic_index = activity × (1 + hypertension)
```

### Structural blend (post-ML)

Lineage severity ≈ 32% LRI + 26% WFS + 24% HLI + 18% first-degree  
Metabolic severity ≈ 45% MRI + 40% BMI excess + 15% hypertension  
Combined = `0.58·lin + 0.42·met`  

Logit-mix with model `p` using blend weight that grows with burden (see `predictor.py` constants `_STRUCT_*`, `_BLEND_*`).

## Soft adjustment (DESCEND additions)

Applied after structural blend:

```
p_final = clamp(p + delta_lifestyle + delta_blood + delta_early_onset, 0.02, 0.98)
```

### Lifestyle deltas

| Factor | Condition | Delta |
|--------|-----------|-------|
| Activity / exercise | Rarely + short duration / low activity | +0.04 |
| Activity / exercise | 5+/week + 30–60+ min | −0.03 |
| Sugary drinks | Daily | +0.035 |
| Sugary drinks | Several×/week | +0.02 |
| Fast food | Daily | +0.03 |
| Fast food | Several×/week | +0.015 |
| Smoking | Current | +0.04 |
| Smoking | Former | +0.015 |
| Alcohol | Regular | +0.025 |
| Sleep | &lt;6 hours | +0.03 |
| Sleep | 7–8 hours | −0.01 |

Clamp: `|delta_lifestyle| ≤ 0.12`.

### Optional blood deltas (0 if skipped / unknown)

| Marker | Band | Delta |
|--------|------|-------|
| Fasting glucose | &lt;100 mg/dL | −0.01 |
| Fasting glucose | 100–125 | +0.04 |
| Fasting glucose | ≥126 | +0.07 |
| HbA1c | &lt;5.7% | −0.01 |
| HbA1c | 5.7–6.4 | +0.045 |
| HbA1c | ≥6.5 | +0.08 |

Clamp: `|delta_blood| ≤ 0.10`.

### Early-onset hereditary severity

First-degree relatives with known age at diagnosis (max 2 counted):

| Age at diagnosis | Delta each |
|------------------|------------|
| &lt;40 | +0.025 |
| 40–50 | +0.015 |
| &gt;50 | +0.005 |

Grandparent early onset (&lt;50): +0.01 each (max 2).  
Clamp: `delta_early_onset ≤ 0.06`.

## UI question → scoring path

| UI factor | Model / soft path |
|-----------|-------------------|
| Sex, age, height, weight | ExtraTrees features (BMI derived) |
| Hypertension | hypertension_status (+ blend) |
| Parent / grandparent T2DM | WFS, LRI, HLI, parent_has_t2dm |
| Sibling / aunt / uncle counts | siblings_diabetes_count, aunts_uncles_score |
| Exercise level / frequency / duration | physical_activity_score (derived) + lifestyle soft delta |
| Sugary / fast food | dietQualityScore proxy + lifestyle soft delta |
| Smoking / alcohol / sleep | lifestyle soft delta |
| Diagnosis ages | early-onset soft delta |
| Fasting glucose / HbA1c | blood soft delta (optional) |
| Own physician-diagnosed T2DM | recommendations / target context (not ExtraTrees column) |

## Scenario projections (heuristic)

Child percentages are **not** separately trained. They are communicative projections from the blended respondent score (small male/female spread, lineage multiplier). Do not read them as validated offspring probabilities.

## Implementation files

- Frontend mock (offline): `Frontend/src/utils/mockScore.ts`
- Backend soft layer: `Backend/app/ml/soft_adjust.py`
- Predict hook: `Backend/app/ml/predictor.py` → `predict_assessment`
- Payload mapper: `Frontend/src/api/mapPayload.ts`
