# Module 1 — Copy-Paste Slide Content
## Hybrid Time-Series Case Forecasting

**Owner:** Bandara H.R.B.G.M. (214029P)  
**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Deck size:** 7 slides (presentation-safe)

**How to use:** Copy each **ON-SLIDE** block into your slide body. Paste figures from the paths listed. Speaker notes are optional — paste into PowerPoint *Notes* if wanted.

---

## SLIDE 1 — Module Introduction

**Title (paste as slide title):**
```
Module 1 — Hybrid Time-Series Case Forecasting
Bandara H.R.B.G.M. | 214029P
```

**ON-SLIDE:**
```
What is Module 1?
• Hybrid time-series pipeline that forecasts weekly dengue case counts
  per district using SARIMA + XGBoost residual compensation

Research gap
• Classical models capture temporal trends but leave structured error
  from climate lags, monsoon effects, and recent case dynamics
• Single-stage ML often mixes baseline and correction into one opaque model
• Climate is either forced into the baseline or excluded entirely —
  neither separates temporal structure from contextual correction

Novelty
• Two-stage residual compensation: climate-free SARIMA Stage 1,
  climate-aware XGBoost Stage 2 on out-of-sample residuals
• Task-specific compensation on the case-count scale — not a generic
  end-to-end black-box forecaster
• Pooled district model with leakage-safe walk-forward + holdout evaluation
```

**INSERT:** None

**SPEAKER NOTES:**
This slide frames Module 1 in three parts: what it is, why it is needed, and what is different. Module 1 is the magnitude layer — it answers "how many cases?" Complement Modules 2 and 3 in the closing summary slide. Do not claim guaranteed outbreak prediction.

---

## SLIDE 2 — Two-Stage Design

**Title:**
```
Residual Compensation Design
```

**ON-SLIDE:**
```
Stage 1 — SARIMA baseline
• Per-district weekly case counts only
• Captures linear temporal structure

Stage 2 — XGBoost residual compensation
• Predicts out-of-sample SARIMA residuals
• Adds climate, epidemiological, and seasonal features

Final forecast
  final_prediction = sarima_prediction + predicted_residual

Design choices
• Pooled XGBoost model (District as categorical feature)
• Leakage-safe: Stage 2 trained only on out-of-sample residuals
```

**INSERT FIGURE:**
- **Figure 6.2** — Module 1 implementation pipeline  
- File: `research_context/report_drafts/diagrams/figure_6_2_module1_implementation.png`  
- Place: right half of slide (or full-width below text if layout is tight)

**FIGURE CAPTION (optional, below image):**
```
Figure 6.2: Module 1 implementation pipeline —
preprocessing → SARIMA → residual extraction → XGBoost → final forecast
```

**SPEAKER NOTES:**
Climate is deliberately excluded from Stage 1 so the baseline models temporal structure cleanly. Climate-driven deviations are left in the residual for Stage 2 to learn — this is the core residual-compensation idea for Module 1.

---

## SLIDE 3 — Data & Evaluation Protocol

**Title:**
```
Data Inputs and Evaluation Protocol
```

**ON-SLIDE:**
```
Data sources
• Weekly dengue cases — Ministry of Health epidemiological reports
• Daily climate — Open-Meteo (rainfall, temperature, humidity)
• 25 Sri Lankan districts, epi-week aligned calendar

Preprocessing
• Shared district–week table with Modules 2 and 3
• Module 1–specific SARIMA-ready weekly series
• Imputed weeks flagged and excluded from scoring

Evaluation protocol
• 14 expanding-window walk-forward folds
• Untouched 2-year holdout block (104 weeks per district)
• Primary metric: MASE (seasonal-naive scale, m = 52)
```

**INSERT TABLE (paste into slide):**

| Component | Description |
|---|---|
| Spatial unit | 25 districts |
| Temporal unit | Weekly epi-weeks |
| Stage 1 input | Historical case counts |
| Stage 2 input | Cases + climate + seasonality |
| Validation | 14 walk-forward folds |
| Final test | 2-year holdout |

**SPEAKER NOTES:**
Walk-forward validation mimics real forecasting — each fold only uses past data to predict future weeks. The holdout block was never used for model selection, so it gives an honest final check.

---

## SLIDE 4 — Stage 1 & Stage 2 Implementation

**Title:**
```
Stage 1 SARIMA and Stage 2 XGBoost
```

**ON-SLIDE:**
```
Stage 1 — Per-district SARIMA
• Automatic order selection per district
• Walk-forward validated univariate baseline
• One SARIMA model per district

Stage 2 — Residual compensation features
• Case lags and 4-week rolling statistics
• Rainfall lags (2–8 weeks), temperature & humidity lags
• Climate anomalies, monsoon indicators, cyclic week encoding
• SARIMA prediction and residual lags (1–2 weeks)

Top learned drivers (Stage 2)
• Recent SARIMA error (residual_lag_1, residual_lag_2)
• Local case intensity and climate–seasonal context
```

**INSERT TABLE (paste into slide):**

| Rank | Feature | Role |
|:---:|---|---|
| 1 | residual_lag_1 | Recent baseline error |
| 2 | residual_lag_2 | Error persistence |
| 3 | rolling_mean_cases_4w | Local case intensity |
| 4 | cases_lag_3 | Short-term epidemiological memory |
| 5 | rainfall_lag_5 / cos_week | Climate and seasonality |

**INSERT FIGURE (optional):**
- Feature-importance bar chart from production model (create from model artefacts if available)
- Place: right side or second row below table

**SPEAKER NOTES:**
The dominance of residual_lag features shows Stage 2 is correcting structured error left by SARIMA — especially error that persists from one week to the next. Climate and seasonal features add the epidemiological context SARIMA alone cannot capture.

---

## SLIDE 5 — Results: Headline Metrics

**Title:**
```
Results — Stage 1 vs Stage 1+2
```

**ON-SLIDE:**
```
Residual compensation improved forecast accuracy across all 25 districts
on validation-aggregate MASE.

Headline improvements
• Validation: median MASE improvement 43.5%  (25/25 districts)
• Holdout:   median MASE improvement 32.7%  (majority of districts)
• Median holdout MASE: ~0.62 → ~0.37  (Stage 1 → Stage 1+2)

Selected holdout examples
• Colombo:     MASE 0.65 → 0.32
• Gampaha:     MASE 0.74 → 0.35
• Batticaloa:  MASE 0.59 → 0.25
```

**INSERT TABLE (paste into slide):**

| Scope | Median MASE improvement | Districts improved |
|---|---|---|
| Validation aggregate | 43.5% | 25 / 25 |
| Holdout | 32.7% | Majority of districts |

**INSERT FIGURE:**
- **Figure 7.2** — Actual vs Stage 1 vs Stage 1+2 holdout forecasts  
- File: `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png`  
- Place: full-width below table (Colombo and Gampaha trajectories)

**FIGURE CAPTION:**
```
Figure 7.2: Holdout weekly case forecasts — actual vs Stage 1 vs Stage 1+2
(Colombo and Gampaha)
```

**SPEAKER NOTES:**
MASE compares forecast error to a seasonal-naive benchmark — values below 1.0 mean the model beats naive seasonality. The hybrid pipeline clearly tracks observed case trajectories more closely than SARIMA alone in high-burden districts like Colombo and Gampaha.

---

## SLIDE 6 — Results: District-Level Comparison

**Title:**
```
Holdout MASE — All 25 Districts
```

**ON-SLIDE:**
```
District-level holdout comparison confirms broad improvement from
residual compensation.

• Stage 1+2 reduces MASE relative to Stage 1 alone across the majority
  of districts on the untouched holdout block
• Improvement is consistent across high-burden and moderate-burden districts
• Residual compensation recovers error left by the climate-free SARIMA baseline
```

**INSERT FIGURE:**
- **Figure 7.3** — District-level holdout MASE comparison  
- File: `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png`  
- Place: full slide (large, readable)

**FIGURE CAPTION:**
```
Figure 7.3: Holdout MASE comparison — Stage 1 vs Stage 1+2 (25 districts)
```

**SPEAKER NOTES:**
This figure shows the breadth of improvement — not just one or two districts. The median holdout MASE drop from about 0.62 to 0.37 means the typical district forecast moves closer to — and often below — the seasonal-naive benchmark after compensation.

---

## SLIDE 7 — Summary & Contribution

**Title:**
```
Module 1 — Key Outcomes
```

**ON-SLIDE:**
```
Delivered
• End-to-end two-stage hybrid forecasting pipeline for weekly district cases
• Leakage-safe residual compensation architecture (SARIMA → XGBoost)

Demonstrated
• Material MASE reduction relative to SARIMA alone
• Climate-aware and residual-lag features drive Stage 2 correction

Integrated
• Forecast outputs feed the Streamlit early-warning dashboard
• Supports Module 2 forward-risk workflows

Framework role
• Module 1 = magnitude layer
• Works with Module 2 (outbreak alerts) and Module 3 (spatial hotspots)
```

**INSERT (optional):**
- Small thumbnail of Figure 6.2, OR
- Three-box diagram:

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Module 1   │   │  Module 2   │   │  Module 3   │
│  How many   │   │  Outbreak   │   │   Where     │
│   cases?    │   │    risk?    │   │  hotspots?  │
└─────────────┘   └─────────────┘   └─────────────┘
```

**SPEAKER NOTES:**
Module 1 answers the quantitative forecasting question. It does not replace outbreak classification or spatial mapping — those are separate modules with separate evaluation protocols. Together they form a multidimensional early-warning framework.

---

# Quick reference — files to insert

| Slide | Asset | Path |
|:---:|---|---|
| 2 | Figure 6.2 | `research_context/report_drafts/diagrams/figure_6_2_module1_implementation.png` |
| 5 | Figure 7.2 | `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png` |
| 6 | Figure 7.3 | `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png` |

---

# Slide footer (optional, all slides)

Paste into slide master footer if your template uses it:
```
Team Codexon | A Residual Compensation Modeling Framework for Dengue Risk Prediction
Module 1 — Hybrid Time-Series Case Forecasting | 214029P
```

---

**Approx. on-slide word count:** ~650 words across 7 slides  
**Status:** Copy-paste ready (presentation-safe, 2026-07-31)
