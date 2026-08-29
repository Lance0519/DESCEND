# DESCEND Survey Cleaning for Model Training

This document records how the DESCEND Google Form export is checked, mapped, and transformed into the respondent-level CSV used by `train.py`. It is intended for the thesis methodology chapter and for reproducing the processed file.

DESCEND is educational and non-diagnostic. Survey answers and the processed `outcome` column are self-reported research labels, not physician-confirmed diagnoses.

Related docs: [Google Form field inventory](GOOGLE_FORM_FIELD_INVENTORY.md), [ML validation plan](ML_VALIDATION_AND_DOCUMENTATION_PLAN.md), [Risk scoring](RISK_SCORING.md).

## 1. Files and how to reproduce

| Role | Path |
|---|---|
| Raw Google Form export (unchanged original) | `Backend/ml/datasets/raw/DESCEND RAW SURVEY.csv` |
| Augmented raw (noise + 180 boundary cases) | `Backend/ml/datasets/raw/DESCEND RAW SURVEY augmented.csv` |
| Canonical training CSV | `Backend/ml/datasets/processed/training_dataset.csv` |
| Named 900-row snapshot (pre-augmentation) | `Backend/ml/datasets/processed/training_dataset_descend_900.csv` |
| Named 1080-row snapshot (current train file) | `Backend/ml/datasets/processed/training_dataset_descend_1080.csv` |
| Augmentation manifest | `Backend/ml/datasets/processed/screening_augmentation_manifest.json` |
| Prior 488-row artifact | `Backend/ml/datasets/processed/training_dataset_filipino_488.csv` |

**Scripts**

| Script | Role |
|---|---|
| `Backend/scripts/clean_raw_to_training.py` | Clean original or resolved raw CSV |
| `Backend/scripts/augment_screening_dataset.py` | Noise 18% of the 900-row export; append 180 FN-profile rows; rebuild training CSV |
| `Backend/scripts/gform_survey_map.py` | Detect Google Form headers; map questions to internal names |
| `Backend/scripts/prepare_training_dataset.py` | Validate rows; encode features; write training CSV |
| `Backend/scripts/dataset_paths.py` | Prefer the augmented Google Form export when present |
| `Backend/train.py` | Train ExtraTrees; default threshold is recall-constrained |
| `Backend/tests/test_gform_survey_map.py` | Mapping, activity/diet encoding, and end-to-end prepare tests |
| `Backend/tests/test_threshold_selection.py` | Screening threshold selection |

From `Backend/`:

```bash
python scripts/clean_raw_to_training.py
python scripts/augment_screening_dataset.py
python train.py
```

Optional paths:

```bash
python scripts/clean_raw_to_training.py --raw ml/datasets/raw/DESCEND RAW SURVEY.csv --out ml/datasets/processed/training_dataset.csv
```

The cleaner detects question-text headers automatically. Rows that fail validation are **skipped entirely** (not imputed).

## 2. Raw export profile

Checked 2026-08-27 on `DESCEND RAW SURVEY.csv`.

| Item | Result |
|---|---|
| Format | Google Sheets / Forms CSV, UTF-8 |
| Rows | 900 |
| Columns | 39 (timestamp + 38 answer fields) |
| Collection timestamps | 2024-01-05 through 2025-08-20 (565 in 2024, 335 in 2025) |
| Consent | 900 `I agree`; 0 refusals |
| Exact duplicate responses (excluding timestamp) | 0 |
| Duplicate timestamps | 0 |
| Required demographics (sex, age, height, weight) | 0 missing |
| Family status and aunt/uncle counts | 0 missing |
| Optional fasting glucose filled | 363 / 900 (40.3%) |
| Optional HbA1c filled | 325 / 900 (36.1%) |
| Respondent diagnosis age filled | 220 / 900 (only the diagnosed group) |

### 2.1 Raw label and demographics

| Item | Count |
|---|---:|
| Doctor-diagnosed T2DM = Yes | 220 |
| Doctor-diagnosed T2DM = No | 680 |
| Female | 479 |
| Male | 421 |
| Age | 18–77 years (mean 48.88) |
| Height | 143–177 cm |
| Weight | 37–109 kg |
| Computed BMI | 17.31–37.72 (mean 23.25) |
| Diagnosed age among Yes respondents | 22–75; none missing; none greater than current age |

Hypertension: 549 No, 246 Yes, 105 I'm not sure.

The form does not include a mother-GDM question. That training column is filled as unknown (`0.35`) for every row and is **not** an ExtraTrees feature.

## 3. Raw quality checks

Plausibility ranges are those in `prepare_training_dataset.py`.

| Check | Threshold | Failures |
|---|---|---:|
| Consent refused | `I agree` / Yes required | 0 |
| Age | 12–110 years | 0 |
| Height | 100–230 cm | 0 |
| Weight | 28–280 kg | 0 |
| BMI | 12–65 | 0 |
| Sex | Male or Female | 0 |
| Blank required answer fields | sex, age, height, weight, hypertension, lifestyle, family status, aunt/uncle counts | 0 |
| Diagnosis age vs current age | diagnosis age ≤ age when diagnosed = Yes | 0 |
| Diagnosis age present when diagnosed = No | must be empty | 0 |

Optional blanks (glucose, HbA1c, relative diagnosis ages, earliest aunt/uncle ages) are expected and are not used as ExtraTrees columns.

## 4. Cleaning flowchart

```mermaid
flowchart TD
    A[900 Google Form rows] --> B[Detect question-text headers]
    B --> C[Map to internal column names]
    C --> D[Assign sequential patient_id]
    D --> E[Consent screen]
    E --> F[Age / sex / height / weight / BMI validation]
    F --> G[Encode lifestyle, family, outcome]
    G --> H[Compute lineage and interaction features]
    H --> I[900-row training_dataset.csv]
```

| Stage | Rows remaining | Removed |
|---|---:|---:|
| Raw export | 900 | — |
| Consent | 900 | 0 |
| Demographic and BMI validation | 900 | 0 |
| Duplicate responses | 900 | 0 |
| Final training CSV | 900 | 0 |

## 5. Google Form → internal schema

`gform_survey_map.py` matches headers after lowercasing and collapsing whitespace. Detection uses any of: consent question, doctor-diagnosis question, height-in-centimeters question.

| Google Form question | Internal field |
|---|---|
| Do you agree to participate in this study? | `consent` (`1` / `0`) |
| Has a doctor diagnosed you with Type 2 diabetes? | `patient_has_t2dm_status` |
| At what age were you diagnosed? | `age_at_diagnosis` |
| What is your sex? | `sex_at_birth` |
| What is your age? | `age` |
| What is your height in centimeters? | `height_cm` |
| What is your weight in kilograms? | `weight_kg` |
| Have you been told you have hypertension…? | `self_hypertension_status` |
| Fasting blood glucose (optional) | `fasting_glucose_mg_dl` |
| HbA1c (optional) | `hba1c_percent` |
| Usual physical activity level | `physical_activity_level` |
| Exercise frequency in a typical week | `physical_activity_frequency` |
| Typical exercise session length | `exercise_duration` |
| Sugary drinks | `sugary_drink_frequency` |
| Fast food | `fast_food_frequency` |
| Smoking / alcohol / sleep | kept on the mapped row; not ExtraTrees features |
| Father / mother / four grandparents T2DM | `*_t2dm_count_raw` (Yes / No / I'm not sure) |
| Sibling T2DM | `sibling_t2dm_status` → `siblings_t2dm_count_raw` |
| Maternal uncles + maternal aunts counts | summed → `maternal_aunts_uncles_t2dm_count_raw` |
| Paternal uncles + paternal aunts counts | summed → `paternal_aunts_uncles_t2dm_count_raw` |

`patient_id` is not on the Google Form. Each kept row receives a sequential id `1`…`900`, copied to `source_patient_id` and `source_record_id`.

## 6. Feature encoding

### 6.1 Outcome (`outcome`)

| Raw doctor diagnosis | Training label |
|---|---|
| Yes | 1 |
| No | 0 |

This export has no `I'm not sure` diagnosis answers, so no unknown-outcome rows were dropped. Labels remain self-reported.

### 6.2 Demographics

- `user_is_male`: Male → `1.0`, Female → `0.0`
- `bmi`: `weight_kg / (height_cm / 100)^2`, rounded to 2 decimals

### 6.3 Hypertension and unknown family status

Yes / No / I'm not sure map to `1.0` / `0.0` / `0.35`. The same coding is used for parents and grandparents. `parent_has_t2dm` is the maximum of father and mother scores.

### 6.4 Physical activity (`physical_activity_score`, model scale 0–2)

Encoding prefers **exercise frequency**, then falls back to **usual activity level**, matching the DESCEND app payload mapper.

| Exercise frequency | Score |
|---|---:|
| Daily, or 4–5 times a week | 2.0 |
| Once a week, or 2–3 times a week | 1.0 |
| Never, and level is sedentary / low | 0.0 |
| Never, and level is light / moderate / very or extremely active | 1.0 |

Processed counts: 18 low (`0.0`), 590 moderate (`1.0`), 292 high (`2.0`).

### 6.5 Diet (`diet_quality_score`, model scale 0–2)

The Google Form has no single diet-quality item. The cleaner derives it from sugary-drink and fast-food frequency:

| Rule | Label | Score |
|---|---|---:|
| Either item is Daily or Often (a few times a week) | unhealthy | 0.0 |
| Otherwise either item is Sometimes (a few times a month) | mixed | 1.0 |
| Otherwise (Rarely / Never) | healthy | 2.0 |

Processed counts: 392 unhealthy, 353 mixed, 155 healthy.

`diet_quality_score` is written to the training CSV for completeness. It is **not** in the ExtraTrees `FEATURE_COLUMNS` list. At inference, sugary-drink and fast-food answers still enter the post-model lifestyle adjustment ([Risk scoring](RISK_SCORING.md)).

### 6.6 Siblings and aunts/uncles

| Raw | Training |
|---|---|
| Sibling = Yes | `siblings_diabetes_count` = 1, `siblings_score` = 1 |
| Sibling = No or I'm not sure | count 0, score 0 |
| Aunt/uncle counts | integer sum of maternal uncles + aunts + paternal uncles + aunts |
| Any aunt/uncle count > 0 | `aunts_uncles_score` = 1 |

I'm not sure on sibling status does not invent a diabetic sibling. That matches the live app (`siblingsDiabetesCount` is 1 only when the answer is yes).

### 6.7 Lineage and interaction features

Family Yes/No/unknown values are passed to `derive_family_metrics` (same functions used at prediction time):

- `weightedFamilyScore`, `maternalScore`, `paternalScore`
- `firstDegreeYesCount`, `secondDegreeYesCount`, `diabeticRelativesCount`
- `lineageRiskIndex`, `propagationProbability`

Interaction terms:

- `metabolic_risk_index` = `age * (bmi / 24)`
- `hereditary_load_index` = blend of parental T2DM, first/second-degree counts, weighted family score, sibling count, and aunt/uncle score
- `activity_metabolic_index` = `physical_activity_score * (1 + hypertension_status)`

Respondent-level training rows use placeholder target fields `generation_depth = 1.5` and `target_is_male = 0.5`, with `target_label = respondent`. Child-scenario scoring is applied only at inference.

## 7. Processed training file

### 7.1 Class distribution

| Outcome | Definition | Count | Percentage |
|---|---|---:|---:|
| 0 | No self-reported doctor diagnosis | 680 | 75.56% |
| 1 | Self-reported doctor diagnosis of T2DM | 220 | 24.44% |

Compared with the prior 488-row file (290 positive / 198 negative), this set is larger and more negative-class dominant. Retraining on it will change class balance and should be re-evaluated with grouped cross-validation before replacing the deployed model.

### 7.2 Columns written

```
age, bmi, user_is_male, physical_activity_score, diet_quality_score,
parent_has_t2dm, hypertension_status, mother_gdm_during_index_pregnancy,
siblings_score, aunts_uncles_score, siblings_diabetes_count,
aunts_uncles_diabetes_count, weightedFamilyScore, maternalScore, paternalScore,
firstDegreeYesCount, secondDegreeYesCount, diabeticRelativesCount,
lineageRiskIndex, propagationProbability, metabolic_risk_index,
hereditary_load_index, activity_metabolic_index, generation_depth,
target_is_male, outcome, source_record_id, source_patient_id, target_label
```

ExtraTrees training uses only `FEATURE_COLUMNS` in `Backend/descend/ml/modeling.py`. Grouped splits use `source_patient_id`.

### 7.3 Fields kept on the raw file but not ExtraTrees inputs

Smoking, alcohol, sleep, exercise duration, optional glucose/HbA1c, and relative diagnosis ages are available on the raw export and in the live assessment payload. They affect the **soft-adjustment** layer after the tree model, not the ExtraTrees feature vector.

## 8. Limitations

1. Outcome is self-reported doctor diagnosis, not a lab-confirmed or chart-verified label.
2. Each row is one respondent; `source_patient_id` is a sequential survey id, not a multi-member family id. Grouped CV therefore does not test family-level generalization.
3. Sex is Male/Female only, as on the form.
4. Sibling history is a yes/no item, not a count of diabetic siblings.
5. Mother GDM was not asked; the column is a constant unknown value.
6. Optional labs are missing for most respondents and must not be described as complete clinical workups.
7. ExtraTrees does not include mother GDM (not asked on the form). Young-female boundary rows teach mother T2DM in young women, not a GDM coefficient.
8. The 180 boundary-case rows are synthetic labeled positives. Hold-out metrics after augmentation are not comparable one-to-one with the previous 13-FN / 180-row hold-out.

## 9. Relationship to the 488-row Filipino artifact

| | Google Form 900 | Prior Filipino 488 |
|---|---|---|
| Raw file | `DESCEND RAW SURVEY.csv` | `training_dataset_filipino_488.csv` (processed); original workbook documented in the ML plan |
| Processed rows | 900 | 488 |
| Rows dropped | 0 | 12 unknown `outcome = 99` |
| T2DM / not T2DM | 220 / 680 | 290 / 198 |
| Header style | Google Form question text | Internal column names |
| Current `training_dataset.csv` | This file | Replaced as the canonical train path |

Keep `training_dataset_filipino_488.csv` so that artifact can still be reproduced. Do not mix the two CSVs in one training run without documenting the merge.

## 10. Screening augmentation and operating threshold

This repository does **not** contain a documented 520-row real + 900-row generated mix. The 900-row Google Form export is uniformly complete. To reduce that uniformity and to target missed-positive profiles, `augment_screening_dataset.py` (seed 42):

| Step | What happened |
|---|---|
| Noise | 162 / 900 original rows (18%): one family-history field flipped; often blank glucose/HbA1c; some high-risk rows set to Never / sedentary activity |
| Boundary A | 60 labeled T2DM: age 40–55, exactly one parent with T2DM, no hypertension, normal BMI |
| Boundary B | 60 labeled T2DM: age 55–65, no parent T2DM, 3–4 grandparents affected |
| Boundary C | 60 labeled T2DM: female age 22–35, mother T2DM, no hypertension |
| Combined | 1080 rows, 400 T2DM / 680 not T2DM |

`python train.py` now defaults to **recall-constrained** threshold selection (not F1):

- Require **recall ≥ 0.82**
- Prefer **precision ≥ 0.70** inside **0.45–0.58**
- If that band cannot hit the recall floor, search down to 0.20
- Among feasible cutoffs, pick the **highest** threshold (as few extra false positives as possible)

Rationale for the thesis: this is a screening-style awareness tool, so missed positives are costlier than extra false positives. The displayed percentage is still the calibrated probability; the cutoff is the binary operating point used in CV/hold-out confusion matrices.

Retrain (2026-08-29): ExtraTrees, 1080 rows, operating cutoff **0.58**. CV recall 83.5%, precision 92.1%. Hold-out recall 85.0%, precision 88.3%, confusion `[[127, 9], [12, 68]]` (12 FN / 9 FP on 216 test rows). Do not claim those 12 FN are the same 13 cases from the unaugmented 180-row hold-out.
