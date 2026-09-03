# DESCEND — How Factor Percentages Relate to User Answers

**Audience:** Clinicians reviewing the tool (e.g., endocrinology consult)  
**Purpose:** Explain what each percentage means and which survey answers drive it  
**Scope:** Educational / risk-awareness prototype — **not a diagnosis**

---

## 1. Start here: three different “percentages”

| What you see | What it means | What it is *not* |
|---|---|---|
| **Overall risk %** (large number on Results) | Calibrated model probability after family/metabolic blending and small lifestyle/lab adjustments | Not a true lifetime incidence rate; not a lab confirmation |
| **Factor bars** (0–100 each) | How strong *that factor domain* looks for this person | They do **not** add up to the overall % |
| **± points list** (Results “factors”) | Small add-ons after the model (lifestyle, optional labs, early-onset ages) | Not the main ML score |

**Risk bands** used for communication:

| Band | Overall % |
|------|-----------|
| Low | 0–33% |
| Moderate | 34–66% |
| High | 67–100% |

---

## 2. Factor bars (0–100%) — driven by answers

These five bars come from the backend `riskBreakdown`. Each bar is scaled to **0–100 for display**. Higher = stronger burden in that domain for this respondent.

### A. Family History

**Answers used:** Father, mother, maternal/paternal grandparents — Yes / No / Not sure  

**How it is scored:**

| Relative | Weight in the family score |
|----------|----------------------------|
| Mother or father with T2DM (Yes) | Full weight (distance 1) |
| Any grandparent with T2DM (Yes) | Half weight (distance 2) |
| “Not sure” | Partial weight (0.35 instead of 1.0) |
| No | 0 |

**Display:** Family score is mapped so that a high multi-relative burden approaches **100%**.  
**Example:** Mother Yes + one grandparent Yes → mid–high Family History bar. No relatives → near **0%**.

---

### B. BMI Status

**Answers used:** Height (cm) and weight (kg) → BMI  

| BMI range | Bar shown |
|-----------|-----------|
| Underweight (&lt; 18.5) | **28%** |
| Normal (18.5–24.9) | **34%** |
| Overweight (25–29.9) | **68%** |
| Obese (≥ 30) | **92%** |

---

### C. Clinical Profile

**Answers used:** Any parent with T2DM; respondent hypertension  

| Answer combination | Approx. bar |
|--------------------|-------------|
| No parent T2DM, no hypertension | **0%** |
| Hypertension only (scaled) | Up to ~**22%** |
| At least one parent with T2DM, no HTN | **42%** |
| Parent T2DM + hypertension | Up to **~64%** (parent 42 + HTN contribution) |

“I’m not sure” on hypertension is treated as a partial hypertension signal in the model features (not a full Yes).

---

### D. Lineage Depth

**Answers used:** Parent and grandparent T2DM counts **plus** sibling and aunt/uncle diabetes counts  

This is a **combined lineage index** (parents + grandparents + extended family counts).  
More generations and more affected relatives → higher bar (scaled toward **100%** when the index is high).

**Clinical reading:** High Lineage Depth = deep / multi-generation family burden, not BMI.

---

### E. Extended Family Count

**Answers used:** Number of siblings with T2DM; number of aunts/uncles with T2DM  

| Rough effect | Direction |
|--------------|-----------|
| Each diabetic sibling | Stronger lift (~24 points toward the raw scale) |
| Each diabetic aunt/uncle | Smaller lift (~9 points toward the raw scale) |
| None reported | **0%** |

Bar is capped at **100%** after scaling.

---

## 3. ± points on the Results page (soft adjustments)

These are **small percentage-point shifts** added *after* the machine-learning score.  
They explain lifestyle and optional lab answers the tree model does not fully absorb.

**Positive (+)** = raises the displayed overall % · **Negative (−)** = lowers it  

### Lifestyle

| User answer | Effect on overall score |
|-------------|-------------------------|
| Exercise rare / low / session &lt; 15 min | **+4.0 points** |
| Exercise 5+ days/week and 30–60+ min | **−3.0 points** |
| Sugary drinks daily | **+3.5 points** |
| Sugary drinks several×/week | **+2.0 points** |
| Fast food daily | **+3.0 points** |
| Fast food several×/week | **+1.5 points** |
| Current smoker | **+4.0 points** |
| Former smoker | **+1.5 points** |
| Regular alcohol | **+2.5 points** |
| Sleep &lt; 6 hours | **+3.0 points** |
| Sleep 7–8 hours | **−1.0 points** |

Lifestyle total is capped at about **±12 points**.

### Optional blood tests (skipped = no change)

| Answer | Effect |
|--------|--------|
| Fasting glucose &lt; 100 mg/dL | **−1.0** |
| Fasting glucose 100–125 mg/dL | **+4.0** |
| Fasting glucose ≥ 126 mg/dL | **+7.0** |
| HbA1c &lt; 5.7% | **−1.0** |
| HbA1c 5.7–6.4% | **+4.5** |
| HbA1c ≥ 6.5% | **+8.0** |

Blood total is capped at about **±10 points**.

### Early age at diagnosis (family)

| Answer | Effect (per relative, limited count) |
|--------|--------------------------------------|
| Parent or sibling diagnosed &lt; 40 years | **+2.5** each (max 2 relatives) |
| Parent or sibling diagnosed 40–50 | **+1.5** each |
| Parent or sibling diagnosed &gt; 50 | **+0.5** each |
| Grandparent diagnosed &lt; 50 | **+1.0** each (max 2) |

Early-onset total is capped at **+6 points**.

---

## 4. Quick walkthrough for a review session

1. Look at the **overall %** and **band** (Low / Moderate / High).  
2. Check **BMI Status** and **Clinical Profile** (metabolic + parent/HTN).  
3. Check **Family History**, **Lineage Depth**, and **Extended Family Count** (heredity).  
4. Read the **± points** list for modifiable lifestyle and any labs the user entered.  
5. Treat child/descendant figures as **illustrative scenarios**, not validated offspring probabilities.

---

## 5. What to say to patients (aligned with the system)

> “This score is an **awareness estimate** based on your answers and family history. It is **not** a medical diagnosis. High scores mean we should discuss prevention and clinical screening with your doctor; they do not confirm diabetes.”

---

## 6. Technical note for reviewers

- The **ExtraTrees model** learns patterns from the survey dataset (age, sex, BMI, hypertension, activity, parent T2DM, siblings, aunts/uncles, and lineage composite features).  
- The **factor bars** are transparent, rule-based summaries of those answers for interpretability.  
- The **± points** are fixed clinical heuristics (lifestyle / labs / early onset), not learned weights.  
- Full formulas: [RISK_SCORING.md](RISK_SCORING.md) · Cleaning / labels: [DATA_CLEANING.md](DATA_CLEANING.md)

*Document version: 2026-09-03 — matches current deployed scoring rules.*
