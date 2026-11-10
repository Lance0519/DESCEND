# DESCEND Risk Indicator Calculation

## Purpose

DESCEND presents **survey-derived risk indicators** based on information
provided by the participant.

The indicators are **heuristic values**. They were created for this research
prototype to summarize patterns in the participant's reported health,
lifestyle, and family-history information.

They are not validated clinical risk scores, diagnostic results, or confirmed
medical probabilities.

## Appropriate terminology

The information comes from the participant's answers. The appropriate
professional terms are:

- **Participant-reported data**
- **Self-reported health information**
- **Self-reported risk-factor data**
- **Survey-derived heuristic risk indicators**

The system should not describe the results as clinically validated scores.

## Information used

The calculation considers the following survey information:

- age and sex;
- height and weight;
- hypertension;
- physical activity;
- diet-related responses;
- smoking, alcohol, and sleep responses, when available;
- diabetes history of parents and grandparents; and
- diabetes history or counts among siblings, aunts, and uncles.

The system converts the answers into a consistent format so that responses can
be summarized and compared.

## What is calculated

The system creates summaries for the following areas:

### BMI status

Height and weight are used to determine the participant's body-mass category.

### Family-history indicator

The system summarizes reported diabetes history among parents and
grandparents. Parent history is given greater emphasis than grandparent
history because it is closer in family relationship.

### Extended-family indicator

Reported diabetes history among siblings, aunts, and uncles is included as
additional family-history information.

### Lineage-depth indicator

The system combines family-history information across generations to describe
the overall strength of the reported family pattern.

### Metabolic and lifestyle indicators

Age, BMI, hypertension, physical activity, diet, and other available lifestyle
answers are considered together to describe the participant's reported
metabolic and lifestyle profile.

## Formulas used in the prototype

The following formulas are the actual researcher-defined heuristic formulas
used to summarize the survey responses. They are shown for transparency and
clinical review. Their inclusion does not mean that the formulas are
clinically validated.

### 1. Body mass index

Height is converted from centimeters to meters:

```text
heightMeters = heightCm / 100
BMI = weightKg / (heightMeters × heightMeters)
```

### 2. Family-history status values

Family-history answers are converted into heuristic values:

| Answer | Value |
|---|---:|
| Yes | 1.00 |
| No | 0.00 |
| Unknown / Not sure | 0.35 |

The value `0.35` represents partial information in the prototype. It is not
a 35% medical risk.

### 3. Weighted Family Score

Parents are assigned a family distance of 1, and grandparents a distance of
2:

```text
relativeContribution = statusValue / familyDistance
weightedFamilyScore = sum of all relative contributions
```

This gives parent history greater emphasis than grandparent history because
parents are one generation closer to the participant.

### 4. Lineage Risk Index

```text
lineageRiskIndex =
    0.36 × weightedFamilyScore
  + 0.30 × firstDegreePositiveCount
  + 0.20 × secondDegreePositiveCount
  + 0.07 × min(extendedFamilyCount, 6)
```

Where:

- `firstDegreePositiveCount` = number of parents reported with T2DM;
- `secondDegreePositiveCount` = number of grandparents reported with T2DM;
- `extendedFamilyCount` = reported diabetic siblings, aunts, and uncles.

### 5. Family propagation indicator

```text
propagationIndicator =
    1 − (1 − 0.18)^F1
      × (1 − 0.08)^F2
      × (1 − 0.04)^F3
```

`F1`, `F2`, and `F3` represent project-defined first-degree,
second-degree, and extended-family counts. This is a heuristic family
aggregation indicator. Despite the original internal name
`propagationProbability`, it is not a validated genetic transmission
probability.

### 6. Hereditary Load Index

```text
lineageStrength = min(
    1.2,
    0.48 × parentStatus
  + 0.22 × (firstDegreePositiveCount / 2)
  + 0.26 × (secondDegreePositiveCount / 4)
  + 0.14 × (weightedFamilyScore / 3.5)
)

hereditaryLoadIndex =
    lineageStrength ×
    (1 + 0.42 × (siblingScore + auntUncleScore))
```

### 7. Hypertension indicator

```text
hypertensionStatus =
    min(
        1,
        selfHypertension
      + 0.25 × fatherHypertension
      + 0.25 × motherHypertension
    )
```

For these terms, `Yes = 1.00`, `No = 0.00`, and unknown information is treated
as `0.35`.

### 8. Metabolic and activity indicators

```text
metabolicRiskIndex = age × (BMI / 24)
activityMetabolicIndex =
    activityScore × (1 + hypertensionStatus)
```

The activity score used by the prototype is:

| Reported activity | Activity score |
|---|---:|
| Rarely / never | 0 |
| 1–2 times per week | 1 |
| 3–4 times per week | 1 |
| 5 or more times per week | 2 |

### 9. Structural heuristic blend

The system summarizes the family-history and metabolic indicators into two
heuristic components:

```text
lineageSeverity =
    0.32 × normalizedLineageRiskIndex
  + 0.26 × normalizedWeightedFamilyScore
  + 0.24 × normalizedHereditaryLoadIndex
  + 0.18 × normalizedFirstDegreeHistory

metabolicSeverity =
    0.45 × normalizedMetabolicRiskIndex
  + 0.40 × normalizedBMIExcess
  + 0.15 × normalizedHypertension

combinedSeverity =
    0.58 × lineageSeverity
  + 0.42 × metabolicSeverity
```

The normalization scales each indicator into a comparable range before the
components are combined. The constants are researcher-defined heuristic
weights, not published clinical risk ratios.

### 10. Final displayed value

The prototype begins with the model output based on the participant's
features, then applies the structural heuristic blend and small optional
adjustments:

```text
finalValue =
    clamp(
        structuralBlendedValue
      + lifestyleAdjustment
      + bloodMarkerAdjustment
      + earlyOnsetAdjustment,
        0.02,
        0.98
    )
```

The optional adjustments use the following project rules:

- low physical activity, frequent sugary drinks, frequent fast food, current
  smoking, regular alcohol use, or short sleep may increase the value;
- frequent physical activity, adequate sleep, or favorable optional blood
  results may slightly decrease the value; and
- early diabetes diagnosis among close relatives may increase the value.

These adjustments are heuristic additions. They are not clinical effect sizes.

### 11. Display band

```text
if finalValue < 0.34:
    Low
elif finalValue < 0.67:
    Moderate
else:
    High
```

The displayed percentage is `finalValue × 100`.

## Meaning of the displayed percentages

The percentages are **indicator levels**, not separate medical probabilities.

For example:

> A Family History indicator of 63% means that the participant's reported
> family-history answers reached that level under the system's heuristic
> calculation. It does not mean that the participant has a 63% clinical
> chance of developing Type 2 Diabetes Mellitus.

The factor indicators should not be added together. Each one describes a
different area of the participant's reported information.

## Overall result

The system combines the survey-derived indicators to produce an overall
prototype result. The result is then shown using three communication bands:

| Band | Display range |
|---|---:|
| Low | 0–33% |
| Moderate | 34–66% |
| High | 67–100% |

These ranges are operational categories created for this prototype. They are
not official clinical thresholds.

## Dataset and research use

The current prototype was developed using a processed dataset containing
1,080 respondent-level records. The dataset includes survey responses,
family-history information, calculated indicators, and an outcome label used
for research modeling.

The dataset and calculations support the system's exploratory research
purpose. They do not establish that the indicators are clinically accurate or
appropriate for diagnosis.

## Important limitation

The values are based mainly on participant-reported information. They may be
affected by incomplete knowledge, recall errors, or inaccurate responses.

The formulas, weights, categories, and display ranges were defined for this
project. They were not directly adopted from a validated clinical risk
calculator such as FINDRISC, the ADA Diabetes Risk Test, or QDiabetes.

The results must not be used as:

- a diagnosis;
- a laboratory result;
- a confirmed probability of developing diabetes;
- a replacement for professional medical assessment; or
- a replacement for blood-glucose or HbA1c testing.

## Recommended explanation to a clinician

> “The system produces survey-derived hereditary-lineage risk estimates from
> participant-reported demographic, clinical, lifestyle, and family-history
> data. The indicators summarize reported patterns and are combined to create
> an exploratory prototype result. They are not based on a validated clinical
> risk-scoring instrument, and they should not be interpreted as diagnostic
> probabilities.”

## Recommended thesis description

> “The study used researcher-defined heuristic calculations to generate
> survey-derived risk indicators from participant-reported data. These
> indicators were designed for exploratory risk awareness and have not been
> externally validated as clinical risk scores.”
