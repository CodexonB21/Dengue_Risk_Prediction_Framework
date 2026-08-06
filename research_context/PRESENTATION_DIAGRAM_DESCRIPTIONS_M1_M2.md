# High-Level Architecture Diagram — Brief Narrative Descriptions (Modules 1 & 2)

Use under **Figure 5.3** / **Figure 5.4** on presentation slides.

---

## Module 1 — Figure 5.3

**Caption:** Figure 5.3: High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting

**Description:**

Module 1 forecasts weekly district case counts using a two-stage pipeline. Stage 1 fits a per-district SARIMA model on historical cases only, excluding climate so the baseline captures temporal structure cleanly. Stage 2 trains a pooled XGBoost model on out-of-sample SARIMA residuals, using climate lags, anomalies, seasonal indicators, and case dynamics to predict the correction. The final forecast combines the SARIMA baseline with the predicted residual, producing compensated weekly case estimates for early-warning decision support.

---

## Module 2 — Figure 5.4

**Caption:** Figure 5.4: High-level architecture of Module 2 — Hybrid Outbreak Risk Classification

**Description:**

Module 2 classifies district-week outbreak risk through epidemic-threshold labelling and a two-stage hybrid design. Stage 1 uses a pooled Random Forest classifier, with climate anomalies, lags, and seasonal features, to estimate initial outbreak probability. Stage 2 applies isotonic regression to calibrate those probabilities so they support fixed alert thresholds. The module outputs a calibrated risk score, a binary alert flag, and low, medium, or high risk tiers for early-warning interpretation.

---

**Approx. word count:** Module 1 ~75 words · Module 2 ~70 words
