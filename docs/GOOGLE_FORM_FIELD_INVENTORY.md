# DESCEND Google Form Field Inventory

## Source

- Form: **DESCEND - Type 2 Diabetes Risk Awareness Survey**
- Form URL: https://docs.google.com/forms/d/e/1FAIpQLScs6zjIgK_YQ8pqKs3G9neGLIqcPVJFxrpHdSdT1OQwIrqirw/viewform
- Response endpoint: https://docs.google.com/forms/d/e/1FAIpQLScs6zjIgK_YQ8pqKs3G9neGLIqcPVJFxrpHdSdT1OQwIrqirw/formResponse
- Source checked: 2026-08-25
- Form language: Filipino interface with English and Tagalog content
- Total answer-bearing fields identified: 38
- Section/information items: multiple non-answer items and section headings

The entry IDs below are the Google Forms `entry.<id>` parameter IDs. Required status reflects the current form metadata. Some required questions are conditional in meaning, for example diagnosis age is relevant only when the corresponding relative or respondent is diagnosed.

## Summary

| Classification | Count | Fields |
|---|---:|---|
| Required answer fields | 34 | Consent, diagnosis, demographics, hypertension, lifestyle, family-history status, diagnosis ages, and family counts |
| Optional answer fields | 4 | Fasting glucose, HbA1c, maternal earliest diagnosis age, paternal earliest diagnosis age |
| Section/information items | Not counted as fields | Information Sheet, Certificate of Consent, and section headings |

## Required Fields

### Consent and diagnosis

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 1 | `entry.382688273` | Do you agree to participate in this study? | Multiple choice | Yes, I agree and wish to continue; No, I do not agree | Required consent gate |
| 2 | `entry.1347328754` | Has a doctor diagnosed you with Type 2 diabetes? | Multiple choice | Yes; No | Required; answer controls diagnosed/management versus predictive path |
| 3 | `entry.591795896` | At what age were you diagnosed? | Short answer | Number; form range up to 100 | Required in form; applicable to diagnosed respondents |

### Personal details and body measurements

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 4 | `entry.1299897520` | What is your sex? | Multiple choice | Male; Female | Required; encoded as `user_is_male` |
| 5 | `entry.2079451507` | What is your age? | Short answer | Number; 18-90 | Required |
| 6 | `entry.1222415716` | What is your height in centimeters? | Short answer | Number; 120-220 | Required |
| 7 | `entry.611616780` | What is your weight in kilograms? | Short answer | Number; minimum 30 | Required |

### Clinical information

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 8 | `entry.649332042` | Have you been told you have hypertension (high blood pressure)? | Multiple choice | Yes; No | Required |

### Lifestyle

| # | Google entry ID | Question | Type | Choices |
|---:|---|---|---|---|
| 9 | `entry.1432614213` | How would you describe your usual physical activity level? | Multiple choice | Low; Moderate; High |
| 10 | `entry.253265067` | How often do you exercise in a typical week? | Multiple choice | Rarerly/Never; 1-2 times per week; 3-4 times per week; 5 or more times per week |
| 11 | `entry.627081381` | How long is a typical exercise session? | Multiple choice | Less than 15 minutes; 15-30 minutes; 30-60 minutes; More than 60 minutes |
| 12 | `entry.1864121549` | How often do you drink sugary drinks? | Multiple choice | Rarely / never; About once a week; Several times a week; Daily |
| 13 | `entry.1231154742` | How often do you eat fast food? | Multiple choice | Rarely / never; About once a week; Several times a week; Daily |
| 14 | `entry.1013359130` | What is your smoking status? | Multiple choice | Never smoked; Former smoker; Current smoker |
| 15 | `entry.1337140741` | How would you describe your alcohol consumption? | Multiple choice | None; Occasional; Regular |
| 16 | `entry.1831875182` | How many hours do you usually sleep per night? | Multiple choice | Less than 6 hrs; 6-7 hours; 7-8 hours; More than 8 hours |

### Family history: parents and sibling

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 17 | `entry.1314386870` | Does your father have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 18 | `entry.2124806089` | At what age was your father diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 19 | `entry.1414037883` | Does your mother have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 20 | `entry.1462851816` | At what age was your mother diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 21 | `entry.322645668` | Does your sibling have Type 2 diabetes? | Multiple choice | Yes; No; I have no siblings; Not sure |
| 22 | `entry.1305041025` | At what age was your sibling diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |

### Family history: maternal side

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 23 | `entry.1396114499` | Does your maternal grandfather have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 24 | `entry.103046815` | At what age was your maternal grandfather diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 25 | `entry.12129785` | Does your maternal grandmother have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 26 | `entry.1030184872` | At what age was your maternal grandmother diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 27 | `entry.1727381069` | How many maternal uncles have Type 2 diabetes? | Short answer | Number; 0-20 | Required |
| 28 | `entry.973788383` | How many maternal aunts have Type 2 diabetes? | Short answer | Number; 0-20 | Required |

### Family history: paternal side

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 29 | `entry.1420700984` | Does your paternal grandfather have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 30 | `entry.820367598` | At what age was your paternal grandfather diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 31 | `entry.927419459` | Does your paternal grandmother have Type 2 diabetes? | Multiple choice | Yes; No; Not sure |
| 32 | `entry.2023219448` | At what age was your paternal grandmother diagnosed? | Short answer | Number; 18-90 | Required in form; conditionally relevant |
| 33 | `entry.1548597372` | How many paternal uncles have Type 2 diabetes? | Short answer | Number; 0-20 | Required |
| 34 | `entry.113761421` | How many paternal aunts have Type 2 diabetes? | Short answer | Number; 0-20 | Required |

## Optional Fields

These four fields are marked optional in the live form metadata or explicitly labeled `(optional)`.

| # | Google entry ID | Question | Type | Choices or validation | Notes |
|---:|---|---|---|---|---|
| 1 | `entry.1716504997` | If you know it, what is your fasting blood glucose (mg/dL)? (optional) | Short answer | Number; 50-400 | Optional laboratory value |
| 2 | `entry.657788061` | If you know it, what is your HbA1c (%)? (optional) | Short answer | Number; 3-15 | Optional laboratory value |
| 3 | `entry.1673982944` | What was the earliest age at diagnosis among maternal aunts or uncles? (optional) | Short answer | Number; 18-90 | Optional early-onset family-history value |
| 4 | `entry.362675749` | What was the earliest age at diagnosis among paternal aunts or uncles? (optional) | Short answer | Number; 18-90 | Optional early-onset family-history value |

## Non-answer Items and Sections

These are displayed form items, but they are not response fields:

| Item | Purpose |
|---|---|
| Information Sheet | Research introduction, purpose, procedures, risks, benefits, confidentiality, privacy, and contact information |
| Certificate of Consent | Consent instructions and declaration |
| Personal Details | Section heading |
| Body Measurements | Section heading |
| Clinical | Section heading |
| Blood Laboratory (optional) | Section heading |
| Lifestyle | Section heading |
| Family Parents and Siblings / family-side headings | Section headings for family-history questions |
| End of form | Closing item |

## Field-to-Project Mapping

| Google Form field | Current project field or feature |
|---|---|
| Consent response | `consent` / participation gate |
| Doctor diagnosis | `patient_has_t2dm_status`, `diagnosedT2dm` |
| Respondent diagnosis age | `ageAtDiagnosis`, `diagnosisAges.self` |
| Sex | `sex_at_birth`, `user_is_male` |
| Age | `age` |
| Height and weight | `height_cm`, `weight_kg`, `bmi` |
| Hypertension | `self_hypertension_status`, `hypertension_status` |
| Physical activity | `physical_activity_score` |
| Parents and grandparents | `parent_has_t2dm`, `weightedFamilyScore`, `lineageRiskIndex` |
| Siblings | `siblings_diabetes_count` |
| Aunts and uncles | `aunts_uncles_diabetes_count`, `aunts_uncles_score` |
| Fasting glucose | `fasting_glucose_mg_dl`, post-model blood adjustment |
| HbA1c | `hba1c_percent`, post-model blood adjustment |
| Diagnosis ages | Early-onset post-model adjustment |
| Smoking, alcohol, sleep, diet | Post-model lifestyle adjustment and recommendations; not tracked ExtraTrees columns in the deployed model |

## Important Reconciliation Notes

1. The live Google Form has more fields than ExtraTrees uses. Lifestyle, diagnosis-age, and optional laboratory fields are mapped from the 900-row export (`DESCEND RAW SURVEY.csv`) into `training_dataset.csv`; only `FEATURE_COLUMNS` are tree inputs. See [DATA_CLEANING.md](DATA_CLEANING.md).
2. The form marks several relative diagnosis-age questions as required even when the corresponding relative may be marked `No`, `Not sure`, or `I have no siblings`. The application should treat these as conditionally applicable and validate them consistently.
3. The exercise choice is displayed as `Rarerly/Never` in the live form. This spelling should be corrected in the form or normalized in the import code. The 900-row export uses `Never`, `Once a week`, `2-3 times a week`, `4-5 times a week`, and `Daily`.
4. The form permits sex choices of Male/Female only. This should be disclosed as a design limitation rather than described as complete sex or gender coverage.
5. Optional fasting glucose and HbA1c values are self-reported research inputs. Abnormal values should produce professional-care guidance and must not be represented as a diagnosis.
6. Response-sheet headers in `DESCEND RAW SURVEY.csv` match the English question text in this inventory (39 columns: Timestamp + 38 answers). Cleaning maps those headers in `Backend/scripts/gform_survey_map.py`.
