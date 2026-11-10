# DESCEND Thesis Defense Quick-Reference: Metrics & Model Architecture

> **Purpose**: A concise, panel-ready cheat sheet for the oral defense of the **DESCEND** system (Filipino Type 2 Diabetes Mellitus Risk Screening). Use this to quickly answer questions regarding model choice, hyperparameter tuning, and clinical evaluation metrics.

---

## 1. Executive Summary (30-Second Defense Pitch)

* **Architecture**: Extremely Randomized Trees (`ExtraTreesClassifier`) with Platt Sigmoid Probability Calibration (`CalibratedClassifierCV`).
* **Hyperparameters**: $400$ estimators (trees), maximum depth of $6$, minimum leaf samples of $3$, `class_weight='balanced'`.
* **Validation**: 5-Fold Stratified Cross-Validation on $N = 1,080$ survey responses ($400$ positive, $680$ negative).
* **Operational Cutoff**: $\tau^* = 0.580$ (recall-constrained to prioritize catching at-risk individuals).
* **Key Performance**: 
  * Accuracy: **88.61%** | Sensitivity (Recall): **86.00%** | Specificity: **90.15%**
  * Precision (PPV): **83.70%** | Negative Predictive Value (NPV): **91.63%**
  * ROC-AUC: **0.9545** | PR-AUC: **0.9289** | Brier Calibration Score: **0.0949**
* **Core Philosophy**: DESCEND is an **educational risk-screening and triage tool**, not a confirmatory clinical diagnostic device.

---

## 2. Why 400 Estimators? (Model Architecture)

### What is an "Estimator"?
In tree ensembles, an **estimator is an individual decision tree**. Setting `n_estimators = 400` means the system constructs a committee of **400 distinct decision trees**. The patient's survey data is passed through all 400 trees, and the final output is their collective average probability vote:
$$P(\text{T2DM}) = \frac{1}{400} \sum_{k=1}^{400} P_k(\text{T2DM})$$

### Why are 400 Trees Needed? (Oral Defense Points)

1. **Counteracts the Extreme Randomness of ExtraTrees**:
   * Unlike standard Random Forests (which calculate optimal split cut-points), ExtraTrees selects split thresholds *completely at random* ([Geurts et al., 2006](https://doi.org/10.1007/s10994-006-6226-1)).
   * Because individual trees are weaker and more randomized, a larger forest ($400$ trees) is required so that random noise cancels out and the true metabolic signal emerges.
2. **Guarantees Cross-Validation Stability (Low Variance)**:
   * Across all 5 folds, sensitivity varied by only $\pm 0.50\%$ and accuracy by only $\pm 0.81\%$. The large tree ensemble ensures the model does not fluctuate when evaluated on different patient subgroups.
3. **Fine-Grained Probability Resolution for Risk Scoring**:
   * A 10-tree model can only output probabilities in coarse $10\%$ jumps ($0.10, 0.20, \dots$).
   * A 400-tree model outputs probabilities in smooth increments of $\frac{1}{400} = 0.25\%$, providing high-resolution data for Platt calibration and resulting in an exceptional **Brier score of 0.0949**.
4. **Asymptotic Convergence Without Overfitting**:
   * [Breiman (2001)](https://doi.org/10.1023/A:1010933404324) proved that adding trees to an ensemble does **not** cause overfitting; generalization error reaches a finite upper bound.
   * Performance plateaus around $300\text{–}500$ trees. At $400$, the system captures maximum predictive accuracy while maintaining sub-50ms web inference times.

---

## 3. Defense Table: Why Each Metric Is Essential

| Metric | Score | Clinical Question It Answers | Why the Panel Demands It |
| :--- | :---: | :--- | :--- |
| **Accuracy** | **88.61%** | *What fraction of all instances were right?* | Standard baseline benchmark, but insufficient alone in medical screening. |
| **Recall (Sensitivity)** | **86.00%** | *Out of 100 diabetic individuals, how many are caught?* | **Patient Safety.** Minimizes False Negatives (only 56 missed out of 400). Unscreened diabetics risk preventable complications. |
| **Specificity** | **90.15%** | *Out of 100 healthy individuals, how many are cleared?* | **Healthcare Efficiency.** Minimizes False Positives (67 false alarms). Prevents unnecessary patient panic and costly confirmatory tests. |
| **Precision (PPV)** | **83.70%** | *If the system flags elevated risk, is it real?* | **Alert Trustworthiness.** Prevents "alert fatigue" among users and clinicians. |
| **NPV** | **91.63%** | *If the system says low risk, is the user truly safe?* | **Safe Triage.** Clinicians need high confidence (91.6%) before advising routine follow-up instead of immediate intervention. |
| **F1-Score** | **84.84%** | *What is the balanced score between precision and recall?* | Proves the model didn't inflate accuracy by favoring the majority class. |
| **ROC-AUC** | **0.9545** | *How well does the model separate classes overall?* | **Threshold Independence.** Evaluates true discriminative power across all cutoffs ($0.0 \to 1.0$), proving the underlying ranking is sound. |
| **PR-AUC** | **0.9289** | *Does detection hold up under class skew?* | Directly monitors the minority (disease) class without being artificially boosted by a large pool of true negatives. |
| **Brier Score** | **0.0949** | *Can we trust the actual risk percentage output?* | **Probability Calibration.** Scores below $0.10$ prove that if the model predicts an $80\%$ risk, the real-world probability is genuinely near $80\%$. |

---

## 4. Anticipated Panel Questions & Spoken Answers

### Q1: "Why use ExtraTrees instead of XGBoost or Logistic Regression?"
> **Spoken Answer:**  
> *"Logistic Regression assumes strict linearity, which fails to capture nonlinear interactions between lifestyle, BMI, and generational pedigree. While XGBoost is powerful, ExtraTrees draws cut-points at random, which introduces extreme variance reduction and prevents overfitting on correlated survey answers. Furthermore, ExtraTrees trains and executes rapidly in a serverless web deployment without heavy GPU dependencies."*

### Q2: "Why is your operational threshold 0.58 instead of the standard 0.50?"
> **Spoken Answer:**  
> *"In clinical screening, default 0.50 thresholds are arbitrary. We implemented a recall-constrained threshold search optimizing for precision while enforcing a minimum sensitivity of 82%. At $\tau^* = 0.580$, the system achieved an optimal trade-off: 86.00% sensitivity and 90.15% specificity, successfully weeding out false positives without compromising patient safety."*

### Q3: "Doesn't 400 trees cause the model to overfit?"
> **Spoken Answer:**  
> *"No, sir/ma'am. In ensemble decision trees, Leo Breiman proved that adding estimators does not cause overfitting; it simply allows the ensemble variance to converge. Our empirical results confirm this: the generalization gap between training accuracy (90.52%) and cross-validation accuracy (88.61%) was under 2%, proving high generalizability."*

### Q4: "ROC-AUC is 0.9545. Why did you still need to report PR-AUC and Brier score?"
> **Spoken Answer:**  
> *"ROC-AUC only measures relative ranking—it tells us sick patients score higher than healthy ones, but it doesn't verify if an 80% risk score actually means an 80% probability. The Brier score measures that exact calibration; our score of 0.0949 proves our probabilities are accurate. Additionally, PR-AUC of 0.9289 ensures that class imbalance did not artificially inflate our ROC curve."*

---

## 5. Formal Guidelines to Mention in Defense

1. **TRIPOD Statement (2015)**: Mandates reporting both **Discrimination** (ROC-AUC) and **Calibration** (Brier Score) for all clinical prediction models.
2. **STARD 2015**: Requires reporting the full confusion contingency matrix alongside **Sensitivity, Specificity, PPV, and NPV**.
3. **Geurts et al. (2006)**: Foundational paper for Extremely Randomized Trees (`ExtraTrees`).
