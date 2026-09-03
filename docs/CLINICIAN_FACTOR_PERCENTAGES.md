# DESCEND — How Factor Percentages Relate to User Answers

**Audience:** Clinicians reviewing the tool (e.g., endocrinology consult)  
**Purpose:** Explain what each percentage means and which survey answers drive it  
**Scope:** Educational / risk-awareness prototype — **not a diagnosis**

**How to read the numbers below**

| Label style | Meaning |
|---|---|
| **Factor bar %** (e.g. BMI **68%**) | Strength of that factor domain for this person (0–100%). Bars do **not** add up to the overall score. |
| **Overall score change %** (e.g. **+4%**) | How many percentage points are added to / subtracted from the big Results score. Same as “points” in the app (`+4.0 points` = **+4%** on the overall risk). |

---

## 1. Start here: three different “percentages”

| What you see | What it means | What it is *not* |
|---|---|---|
| **Overall risk %** (large number on Results) | Calibrated model probability after family/metabolic blending and small lifestyle/lab adjustments | Not a true lifetime incidence rate; not a lab confirmation |
| **Factor bars** (0–100% each) | How strong *that factor domain* looks for this person | They do **not** add up to the overall % |
| **± % list** (Results “factors”) | Small add-ons after the model (lifestyle, optional labs, early-onset ages) | Not the main ML score |

**Risk bands** used for communication:

| Band | Overall risk % |
|------|----------------|
| Low | **0–33%** |
| Moderate | **34–66%** |
| High | **67–100%** |

---

## 2. Factor bars (0–100%) — driven by answers

These five bars come from the backend `riskBreakdown`. Each bar is scaled to **0–100%** for display. Higher = stronger burden in that domain for this respondent.

### A. Family History — bar %

**Answers used:** Father, mother, maternal/paternal grandparents — Yes / No / Not sure  

| Relative answer | Contribution to the family score |
|-----------------|----------------------------------|
| Mother or father with T2DM (**Yes**) | Full weight (distance 1) |
| Any grandparent with T2DM (**Yes**) | Half weight (distance 2) |
| **Not sure** | Partial weight (0.35 instead of 1.0) |
| **No** | 0 |

**Approximate Family History bar % (examples):**

| User answers | Approx. Family History bar |
|--------------|----------------------------|
| No parents, no grandparents with T2DM | **~0%** |
| One grandparent Yes only | **~21%** |
| One parent Yes only | **~42%** |
| One parent Yes + one grandparent Yes | **~63%** |
| Both parents Yes | **~83%** |
| Both parents Yes + several grandparents Yes | **~90–100%** (capped) |

---

### B. BMI Status — bar %

**Answers used:** Height (cm) and weight (kg) → BMI  

| BMI range | Factor bar % |
|-----------|--------------|
| Underweight (&lt; 18.5) | **28%** |
| Normal (18.5–24.9) | **34%** |
| Overweight (25–29.9) | **68%** |
| Obese (≥ 30) | **92%** |

---

### C. Clinical Profile — bar %

**Answers used:** Any parent with T2DM; respondent hypertension  

| Answer combination | Clinical Profile bar % |
|--------------------|------------------------|
| No parent T2DM, no hypertension | **0%** |
| Hypertension only (Yes) | **~22%** |
| At least one parent with T2DM, no HTN | **42%** |
| Parent T2DM + hypertension Yes | **~64%** |

“I’m not sure” on hypertension is treated as a partial hypertension signal in the model features (not a full Yes).

---

### D. Lineage Depth — bar %

**Answers used:** Parent and grandparent T2DM counts **plus** sibling and aunt/uncle diabetes counts  

This is a **combined lineage index** (parents + grandparents + extended family counts), then scaled to **0–100%**.

| Typical profile | Approx. Lineage Depth bar |
|-----------------|---------------------------|
| No family T2DM | **~0–10%** |
| One parent only | **~25–40%** |
| Parent + grandparents | **~45–70%** |
| Multi-generation + several aunts/uncles/siblings | **~75–100%** |

**Clinical reading:** High Lineage Depth % = deep / multi-generation family burden, not BMI.

---

### E. Extended Family Count — bar %

**Answers used:** Number of siblings with T2DM; number of aunts/uncles with T2DM  

| User answers | Approx. Extended Family bar % |
|--------------|-------------------------------|
| 0 siblings, 0 aunts/uncles with T2DM | **0%** |
| 1 sibling with T2DM | **~24%** |
| 2 siblings with T2DM | **~48%** |
| 1 aunt/uncle with T2DM | **~9%** |
| 1 sibling + 2 aunts/uncles | **~42%** |
| Many siblings and aunts/uncles | Up to **100%** (capped) |

---

## 3. Overall score change % (soft adjustments on Results)

These are **percentage-point changes** added *after* the machine-learning score.  
In the app they appear as “points”; for clinicians they are the same as **% on the overall risk**.

Example: if the model score is **48%** and lifestyle adds **+4%**, the adjusted score becomes about **52%** (before other clamps).

**Positive (+%)** = raises the displayed overall risk · **Negative (−%)** = lowers it  

### Lifestyle → overall risk %

| User answer | Change in overall risk % |
|-------------|--------------------------|
| Exercise rare / low / session &lt; 15 min | **+4%** |
| Exercise 5+ days/week and 30–60+ min | **−3%** |
| Sugary drinks daily | **+3.5%** |
| Sugary drinks several×/week | **+2%** |
| Fast food daily | **+3%** |
| Fast food several×/week | **+1.5%** |
| Current smoker | **+4%** |
| Former smoker | **+1.5%** |
| Regular alcohol | **+2.5%** |
| Sleep &lt; 6 hours | **+3%** |
| Sleep 7–8 hours | **−1%** |

Lifestyle total is capped at about **±12%**.

### Optional blood tests → overall risk % (skipped = 0%)

| Answer | Change in overall risk % |
|--------|--------------------------|
| Fasting glucose &lt; 100 mg/dL | **−1%** |
| Fasting glucose 100–125 mg/dL | **+4%** |
| Fasting glucose ≥ 126 mg/dL | **+7%** |
| HbA1c &lt; 5.7% | **−1%** |
| HbA1c 5.7–6.4% | **+4.5%** |
| HbA1c ≥ 6.5% | **+8%** |

Blood total is capped at about **±10%**.

### Early age at diagnosis (family) → overall risk %

| Answer | Change in overall risk % |
|--------|--------------------------|
| Parent or sibling diagnosed &lt; 40 years | **+2.5%** each (max 2 relatives) |
| Parent or sibling diagnosed 40–50 | **+1.5%** each |
| Parent or sibling diagnosed &gt; 50 | **+0.5%** each |
| Grandparent diagnosed &lt; 50 | **+1%** each (max 2) |

Early-onset total is capped at **+6%**.

---

## 4. One worked example (for the consult)

| Item | Value |
|------|------:|
| Model + blend score (before soft adjust) | **48%** |
| BMI Status bar (BMI 27 → overweight) | **68%** |
| Family History bar (mother Yes) | **~42%** |
| Clinical Profile bar (mother Yes, no HTN) | **42%** |
| Soft adjust: low activity | **+4%** |
| Soft adjust: sugary drinks several×/week | **+2%** |
| **Displayed overall risk (approx.)** | **~54%** → **Moderate** |

Factor bars stay as shown; only the soft-adjust **%** moves the big number.

---

## 5. Quick walkthrough for a review session

1. Look at the **overall risk %** and **band** (Low / Moderate / High).  
2. Check **BMI Status %** and **Clinical Profile %** (metabolic + parent/HTN).  
3. Check **Family History %**, **Lineage Depth %**, and **Extended Family %** (heredity).  
4. Add up the soft-adjust **±%** for lifestyle, labs, and early-onset ages.  
5. Treat child/descendant figures as **illustrative scenarios**, not validated offspring probabilities.

---

## 6. What to say to patients (aligned with the system)

> “This score is an **awareness estimate** based on your answers and family history. It is **not** a medical diagnosis. High scores mean we should discuss prevention and clinical screening with your doctor; they do not confirm diabetes.”

---

## 7. Technical note for reviewers

- The **ExtraTrees model** learns patterns from the survey dataset (age, sex, BMI, hypertension, activity, parent T2DM, siblings, aunts/uncles, and lineage composite features).  
- The **factor bars (%)** are transparent, rule-based summaries of those answers for interpretability.  
- The **±% soft adjustments** are fixed clinical heuristics (lifestyle / labs / early onset), not learned weights. In the UI they may be labeled “points”; **1 point = 1 percentage point on overall risk**.  
- Full formulas: [RISK_SCORING.md](RISK_SCORING.md) · Cleaning / labels: [DATA_CLEANING.md](DATA_CLEANING.md)

*Document version: 2026-09-03 — percentages added for clinician readability; matches current deployed scoring rules.*
