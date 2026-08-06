# Module 2 — Copy-Paste Slide Content
## Hybrid Outbreak Risk Classification

**Owner:** Nethma L.H.K. (214140X)  
**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Deck size:** 7 slides (presentation-safe)

**Production stack (use consistently):** Random Forest Stage 1 → isotonic Stage 2 | Alert τ = **0.14** | High tier ≥ **0.35**

**How to use:** Copy each **ON-SLIDE** block into your slide body. Paste figures from the paths listed. Speaker notes are optional.

---

## SLIDE 1 — Module Introduction

**Title (paste as slide title):**
```
Module 2 — Hybrid Outbreak Risk Classification
Nethma L.H.K. | 214140X
```

**ON-SLIDE:**
```
What is Module 2?
• Hybrid outbreak-risk classifier that estimates outbreak probability,
  calibrates it, and converts it into alerts and low / medium / high tiers

Research gap
• Existing outbreak prediction models estimate outbreak probability
  but do not adjust predictions using climate anomalies or seasonal
  environmental variations [1]
• Baseline probability outputs are often not decision-ready for
  fixed early-warning alert thresholds

Novelty
• Two-stage hybrid pipeline: Stage 1 integrates climate anomalies,
  lagged climate, monsoon and seasonal indicators with epidemiological
  features (Random Forest)
• Stage 2 isotonic calibration compensates systematic probability
  error — residual compensation adapted for outbreak classification
• Produces calibrated alerts and risk tiers within the shared
  residual-compensation framework
```

**INSERT:** None

**SPEAKER NOTES:**
Research gap follows the project's original Module 2 literature framing — lack of climate-anomaly-aware adjustment in existing outbreak models. Our Stage 1 addresses climate integration (lags, anomalies, monsoon/season); Stage 2 is probability calibration for actionable alerts, not a second climate regressor. Keep M1 vs M2 complementarity for the summary slide (Slide 7), not here. Replace [1] with your Chapter 2 citation before presenting.

---

## SLIDE 2 — Two-Stage Design

**Title:**
```
Probability Calibration as Residual Compensation
```

**ON-SLIDE:**
```
Stage 1 — Outbreak discrimination
• Pooled Random Forest classifier
• Outputs predicted outbreak probability per district-week

Stage 2 — Probability calibration
• Isotonic regression on out-of-sample Stage 1 probabilities
• Produces calibrated_probability for decision thresholds

Derived outputs
• alert_flag        (threshold τ = 0.14)
• risk_tier         (low / medium / high; high ≥ 0.35)

Design choices
• Fold-aware harmonic epidemic threshold label (k = 3.0)
• Leakage-safe Stage 2: trains only on out-of-sample Stage 1 scores
• Fixed absolute thresholds (not quantile cutoffs)
```

**INSERT FIGURE:**
- **Figure 6.3** — Module 2 implementation pipeline  
- File: `research_context/report_drafts/diagrams/figure_6_3_module2_implementation.png`  
- Place: right half of slide (or full-width below text)

**FIGURE CAPTION (optional):**
```
Figure 6.3: Module 2 implementation pipeline —
labelling → Random Forest → isotonic calibration → alerts and risk tiers
```

**SPEAKER NOTES:**
The label marks a district-week as an outbreak when cases exceed a fold-aware seasonal epidemic threshold. Stage 2 makes the probability scale trustworthy enough to set fixed alert cutoffs — that is the Module 2 form of residual compensation.

---

## SLIDE 3 — Label, Data & Evaluation Protocol

**Title:**
```
Outbreak Label and Evaluation Protocol
```

**ON-SLIDE:**
```
Outbreak label
• District-week exceeds fold-aware harmonic seasonal epidemic threshold
• Threshold parameter k = 3.0 (Decision 025)

Feature groups
• Lagged case anomalies and short-term case dynamics
• Climate lags, anomalies, and seasonal indicators
• District context (pooled model)

Evaluation protocol
• 13 walk-forward folds (4-year minimum training depth)
• Untouched 2-year holdout block (2,600 district-weeks)
• Stage 1 metric: PR-AUC (rare-event discrimination)
• Stage 2 metric: Brier Skill Score (calibration quality)
```

**INSERT TABLE (paste into slide):**

| Item | Choice |
|---|---|
| Label | Harmonic epidemic threshold, k = 3.0 |
| Stage 1 model | Pooled Random Forest |
| Stage 2 model | Isotonic regression |
| Alert threshold | τ = 0.14 (F2-oriented) |
| High-confidence tier | ≥ 0.35 (F0.5-oriented) |
| Validation | 13 walk-forward folds |
| Final test | 2-year holdout |

**SPEAKER NOTES:**
PR-AUC is the right metric for rare outbreak weeks — it measures ranking quality above the baseline prevalence. Brier Skill Score evaluates whether calibrated probabilities are useful as real risk estimates, not just as a ranking score.

---

## SLIDE 4 — Stage 1: Outbreak Discrimination

**Title:**
```
Stage 1 — Pooled Random Forest Classifier
```

**ON-SLIDE:**
```
Model selection
• Benchmarked Logistic Regression, Random Forest, and XGBoost
• Random Forest selected by median validation PR-AUC

Architecture
• Single pooled model with District as categorical feature
• Outperforms per-district modelling on median PR-AUC comparison
• Class imbalance handled via balanced class weights

Holdout performance (Random Forest)
• PR-AUC  = 0.429
• ROC-AUC = 0.885

Key features
• case_anomaly_lag_1 and case_anomaly_lag_2 (leading drivers)
• Rolling case statistics and short-term case lags
```

**INSERT TABLE — Table 7.3 (paste into slide):**

| Model | Median validation PR-AUC (13 folds) |
|---|---|
| Logistic Regression | 0.358 |
| XGBoost (tuned params) | 0.373 |
| **Random Forest (selected)** | **0.377** |

**INSERT FIGURE (optional):**
- Stage 1 feature-importance bar chart  
- Source: `outputs/metrics/module2/baseline_classifier_feature_importance.csv`

**SPEAKER NOTES:**
Stage 1 successfully ranks rare outbreak weeks well above chance. Case-anomaly lags dominate because the label itself encodes recent seasonal exceedance — this is expected behaviour for an epidemic-threshold label, not accidental leakage of the current week's case count.

---

## SLIDE 5 — Stage 2: Isotonic Calibration

**Title:**
```
Stage 2 — Isotonic Probability Calibration
```

**ON-SLIDE:**
```
Purpose
• Convert Stage 1 scores into decision-ready calibrated probabilities
• Enable fixed absolute alert and risk-tier thresholds

Architecture comparison
• Isotonic regression selected by median validation Brier Skill Score
• Holdout BSS = 0.2315

Outcome
• Calibrated probabilities align more closely with observed outbreak rates
• Supports actionable early-warning thresholds
```

**INSERT TABLE (paste into slide):**

| Architecture | Median validation BSS | Holdout BSS |
|---|---|---|
| Platt scaling | 0.2116 | 0.2344 |
| **Isotonic (selected)** | **0.2146** | **0.2315** |

**INSERT FIGURE:**
- **Figure 7.4** — Reliability / calibration diagram  
- File: `research_context/report_drafts/diagrams/figure_7_4_module2_reliability.png`  
- Place: full-width below table (use isotonic version only)

**FIGURE CAPTION:**
```
Figure 7.4: Reliability diagram — Stage 1 raw vs isotonic Stage 2 probabilities
(validation and holdout)
```

**SPEAKER NOTES:**
Use the Chapter 7 Figure 7.4 PNG — not older reliability diagrams in outputs/figures/module2/ that may still reflect Platt-era runs. Emphasise that Stage 2 moves predicted probabilities toward the diagonal — closer to observed outbreak rates.

---

## SLIDE 6 — Alerts & Risk Tiers

**Title:**
```
Actionable Early-Warning Outputs
```

**ON-SLIDE:**
```
Alert threshold
• τ = 0.14 (F2-optimal, recall-oriented)
• Holdout recall improves from 45.0% (naive 0.5 cutoff) to 60.0%
• Holdout F2 score improves from 0.459 to 0.519

Risk tiers (monotonic separation)
• Low    → lowest observed outbreak rate
• Medium → intermediate outbreak rate
• High   → highest observed outbreak rate
• Ordering preserved on both validation and holdout splits

Framework role
• Module 2 = outbreak-alert layer (distinct from Module 1 magnitude forecasts)
```

**INSERT TABLE 1 — Alert utility (holdout):**

| Alert rule | Recall | F2 |
|---|---|---|
| Naive cutoff 0.5 | 45.0% | 0.459 |
| **Calibrated τ = 0.14** | **60.0%** | **0.519** |

**INSERT TABLE 2 — Risk-tier separation:**

| Risk tier | Validation outbreak rate | Holdout outbreak rate |
|---|---|---|
| Low | 1.3% | 0.6% |
| Medium | 26.2% | 13.3% |
| High | 71.1% | 48.8% |

**INSERT (optional):** Simple 3-tier diagram — Low → Medium → High with rates as labels

**SPEAKER NOTES:**
Emphasise recall improvement and tier ordering. Do not lead with accuracy — high accuracy at 0.5 cutoff mostly reflects low outbreak prevalence, not detection skill. Do not quote precision unless asked.

---

## SLIDE 7 — Summary & Complementarity with Module 1

**Title:**
```
Module 2 — Key Outcomes
```

**ON-SLIDE:**
```
Delivered
• Two-stage outbreak-risk pipeline: Random Forest + isotonic calibration
• Alert flag and three-level risk tier outputs

Demonstrated
• Strong rare-event discrimination (Stage 1 PR-AUC)
• Improved calibration skill (Stage 2 BSS)
• Usable recall-oriented alerts at τ = 0.14

Complementarity
• Module 2 alerts are not replaceable by thresholding Module 1 forecasts
• Magnitude forecasting and outbreak-risk classification are separate tasks

Integrated
• Calibrated risk trajectories and alert indicators in Streamlit dashboard
```

**INSERT TABLE — Table 7.7 (trimmed, paste into slide):**

| Method | Holdout PR-AUC |
|---|---|
| **Module 2 production alerts** | **0.412** |
| Thresholding Module 1 forecasts | 0.063 – 0.280 |

**INSERT (optional):** Callout box:
```
Module 2 captured outbreak weeks missed by magnitude-only rules (M2-009)
```

**INSERT (optional):** Three-module framework box:
```
Module 1 — How many cases?     (magnitude)
Module 2 — Outbreak risk?      (alert layer)  ← this module
Module 3 — Where concentrated? (spatial)
```

**SPEAKER NOTES:**
The M2-009 comparison shows that good case forecasts do not automatically produce good outbreak alerts when the target is seasonal exceedance. Module 2 remains essential as the calibrated alert layer even when Module 1 forecasting is available.

---

# Quick reference — files to insert

| Slide | Asset | Path |
|:---:|---|---|
| 2 | Figure 6.3 | `research_context/report_drafts/diagrams/figure_6_3_module2_implementation.png` |
| 5 | Figure 7.4 | `research_context/report_drafts/diagrams/figure_7_4_module2_reliability.png` |
| 4 | Feature importance (optional) | `outputs/metrics/module2/baseline_classifier_feature_importance.csv` |

---

# Slide footer (optional, all slides)

```
Team Codexon | A Residual Compensation Modeling Framework for Dengue Risk Prediction
Module 2 — Hybrid Outbreak Risk Classification | 214140X
```

---

**Approx. on-slide word count:** ~680 words across 7 slides  
**Status:** Copy-paste ready (presentation-safe, 2026-07-31)
