# Chapter 1 — Section 1.5.2 Objectives

## 1.5.2 Objectives

In order to achieve the above-mentioned aim, the following objectives have been defined:

1. To develop a residual compensation-based time-series forecasting model that predicts weekly dengue case counts at the district level by combining a climate-free SARIMA baseline with an XGBoost residual compensation stage that uses lagged epidemiological and climate features for error correction.
2. To develop a hybrid outbreak risk classification model that estimates district-week outbreak probability using a baseline classifier and improves the reliability of risk scores through probability calibration, supporting early-warning alert flags and graded risk tiers.
3. To develop a residual compensation-based spatial hotspot detection model that enhances dengue risk mapping by combining spatial statistical baseline techniques, such as Kernel Density Estimation and Moran’s I, with environmental and demographic residual correction.

**Approx. word count:** 130 words (objectives list)

**Notes for Team:**
- Module 2 objective rewritten: Stage 2 is **isotonic probability calibration**, not environmental-anomaly residual correction. Climate/anomaly features belong mainly in Module 2 Stage 1.
- Avoided vague “improves prediction accuracy” for Module 2; used calibration / early-warning reliability language instead.
- Module 1 clarified: SARIMA is climate-free; climate enters Stage 2; compensation model is XGBoost; scope is district-level weekly counts.
- Module 3 kept aligned with KDE + Moran’s I + environmental/demographic correction.
- Numbered list used (acceptable for Aim/Objectives per report style guide).
- Optional fourth objective (if supervisor wants integration explicit):  
  `4. To integrate the forecasting, classification, and spatial outputs into an early-warning decision-support dashboard for joint visualisation and interpretation.`  
  Add only if the Aim also mentions integration; otherwise keep to three module objectives.
- Confirm Aim (1.5.1) wording matches these objectives before finalising.
