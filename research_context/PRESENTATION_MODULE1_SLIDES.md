# Module 1 Presentation Slides — Hybrid Time-Series Case Forecasting

**Owner:** Bandara H.R.B.G.M. (214029P)  
**Audience:** FYP presentation (sample-style module pack)  
**Status:** Presentation-safe outline (2026-07-31, revised)  
**Evidence base:** `MODULE_CONTEXT.md`, Chapter 7.3, `REPORT_DIAGRAM_PLAN.md`

**Presentation policy:** This pack includes **supporting results and design strengths only**. Negative outcomes, partial failures, and methodological caveats stay in the report and viva prep — see **Excluded from slides** at the end.

Use **6–7 core slides** in the main deck.

---

## Slide M1-1 — Module Introduction

**Title:** Module 1 — Hybrid Time-Series Case Forecasting (214029P)

**Content structure:** What is Module 1 → Research gap → Novelty (three short blocks)

**Content:**
- **What is Module 1?** Hybrid time-series pipeline forecasting weekly district case counts via SARIMA + XGBoost residual compensation
- **Research gap:** Classical models leave structured error from climate/seasonality; single-stage ML obscures baseline vs correction; climate handling is often all-or-nothing
- **Novelty:** Climate-free SARIMA Stage 1 + climate-aware XGBoost Stage 2 on out-of-sample residuals; task-specific case-count compensation; pooled leakage-safe evaluation

**Suggested figure:** none required.

---

## Slide M1-2 — Two-Stage Design

**Title:** Residual Compensation Design

**Content:**
```text
Stage 1: SARIMA (weekly cases only)
residual = actual_cases − sarima_prediction
Stage 2: XGBoost predicts residual
final_prediction = sarima_prediction + predicted_residual
```
- Stage 1 models temporal structure; Stage 2 adds climate-aware and epidemiological correction
- Pooled XGBoost with district as a categorical feature
- Leakage-safe training: Stage 2 uses only **out-of-sample** SARIMA residuals

**Suggested figure:**
- **Figure 6.2** — `research_context/report_drafts/diagrams/figure_6_2_module1_implementation.png`  
  Caption: *Module 1 pipeline: preprocessing → SARIMA → residual extraction → XGBoost → final forecast*

---

## Slide M1-3 — Data & Preprocessing

**Title:** Data Inputs and Evaluation Protocol

**Content:**
- Inputs: weekly MoH WER dengue cases (25 districts); Open-Meteo climate aggregated to epi-week
- Shared district–week calendar with Modules 2 and 3
- Module 1 preprocessing: SARIMA-ready weekly series; imputed weeks flagged and excluded from scoring
- Evaluation: **14 walk-forward folds** + untouched **104-week holdout** per district

**Suggested table:**

| Component | Description |
|---|---|
| Cases | 25 districts, weekly epi-weeks |
| Climate | Rainfall, temperature, humidity (Stage 2) |
| Validation | Expanding-window walk-forward |
| Final test | 2-year holdout block |

**Suggested figure (optional):** Figure 6.1 shared pipeline — only if not already on the overview slide.

---

## Slide M1-4 — Stage 1 & Stage 2 Implementation

**Title:** Stage 1 SARIMA and Stage 2 XGBoost

**Content:**

**Stage 1 — Per-district SARIMA**
- Automatic order selection per district with walk-forward validation
- Univariate weekly case counts establish a strong temporal baseline

**Stage 2 — Residual compensation**
- Feature groups: case lags and rolling trends; rainfall lags (2–8 weeks); temperature/humidity lags; climate anomalies; monsoon and cyclic week features; SARIMA prediction; residual lags
- Top learned drivers: recent SARIMA error (`residual_lag_1`, `residual_lag_2`) plus local case intensity and climate-seasonal context

**Suggested table — feature importance (top 5):**

| Rank | Feature | Role |
|---|---|---|
| 1 | residual_lag_1 | Recent baseline error |
| 2 | residual_lag_2 | Error persistence |
| 3 | rolling_mean_cases_4w | Local intensity |
| 4 | cases_lag_3 | Short-term memory |
| 5 | rainfall_lag_5 / cos_week | Climate / season |

**Suggested figure (recommended):** feature-importance bar chart from production model gains.

**Do not put on slide:** non-seasonal SARIMA counts, per-district failure cases, ACF residual diagnostics.

---

## Slide M1-5 — Evaluation Results

**Title:** Results — Stage 1 vs Stage 1+2

**Content (headline only — positive framing):**
- Residual compensation improved forecast accuracy **across all 25 districts** on validation-aggregate MASE
- **Median improvement ≈ 43.5%** (validation) and **≈ 32.7%** (holdout)
- Median holdout MASE moved from **~0.62 → ~0.37** (Stage 1 → Stage 1+2)
- Strong district examples: Colombo, Gampaha, Batticaloa show clear holdout gains

**Suggested table — Table 7.1 (presentation version):**

| Scope | Median MASE improvement | Districts improved |
|---|---|---|
| Validation aggregate | 43.5% | 25/25 |
| Holdout | 32.7% | Majority of districts |

**Suggested figures (use both if possible):**
1. **Figure 7.2** — actual vs Stage 1 vs Stage 1+2 (Colombo / Gampaha holdout)  
   `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png`
2. **Figure 7.3** — district-level holdout MASE comparison  
   `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png`

**Presentation tip:** Lead with Figure 7.2 (visual proof), then Figure 7.3 (breadth). Use Colombo/Gampaha callouts verbally.

---

## Slide M1-6 — Summary & Contribution

**Title:** Module 1 — Key Outcomes

**Content:**
- Delivered a **two-stage hybrid forecasting pipeline** for weekly district case counts
- Demonstrated that **residual compensation** materially reduces error relative to SARIMA alone
- Integrated outputs feed the framework dashboard and support Module 2 forward-risk workflows
- Complements Module 2 (outbreak state) and Module 3 (spatial concentration) as the **magnitude** layer

**Suggested figure:** reuse Figure 6.2 thumbnail or a single before/after metric callout box.

**Optional positive add-on (one line only):** production stack refined with reporting-delay features (M1-006B) for near-term operational scoring — cite as enhancement, not the primary claim.

---

## Optional Slide M1-7 — Related Works

**Title:** Related Work — Dengue Forecasting

**Content:** 2–3 citations from Chapter 2 on hybrid / ML-augmented dengue forecasting. Pull from literature chapter before finalizing.

---

# Recommended Main-Deck Sequence (6 slides)

1. M1-1 Gap & goal  
2. M1-2 Design + Figure 6.2  
3. M1-3 Data & protocol  
4. M1-4 Stage 1 + Stage 2 + features  
5. M1-5 Results — Table 7.1 + Figures 7.2 & 7.3  
6. M1-6 Summary & contribution  

---

# Figure & Table Checklist (presentation-safe)

| Asset | Slide | Priority |
|---|---|---|
| Fig 6.2 implementation pipeline | M1-2 | High |
| Fig 7.2 holdout forecast trajectories | M1-5 | High |
| Fig 7.3 holdout MASE comparison | M1-5 | High |
| Table 7.1 (positive headline rows only) | M1-5 | High |
| Feature-importance chart | M1-4 | Medium |

---

# Excluded from slides (report / viva only)

Do **not** present these in the main deck:

| Topic | Why excluded |
|---|---|
| 18/25 districts with non-seasonal SARIMA (`D=0`) | Reads as baseline weakness |
| Kilinochchi / Mannar holdout worsening | Negative holdout exceptions |
| Diebold–Mariano partial significance (14/25, 5/25) | Undermines “universal” improvement claim |
| Ljung–Box still significant after Stage 2 (23/25) | Residual structure not fully removed |
| Vavuniya/Mannar explosive AR root fix narrative | Implementation failure story |
| Reporting-delay spike unpredictability (2026 Wk25) | Operational negative |
| Forward forecasts without ground truth | Unvalidated |
| M1-006B only 22/25 districts improved vs prior stack | Mixed refinement result |
| ACF residual plots | Shows remaining error structure |
| Full 25-district MASE table with negative rows | Too much detail; exposes exceptions |

---

# Speaker guardrails

**Say:**
- Residual compensation improved MASE for all districts on validation and for the majority on holdout
- Median holdout MASE improvement ≈ 32.7%
- Climate and residual-lag features drive Stage 2 correction

**Avoid in the presentation:**
- Naming underperforming districts
- Claiming universal statistical significance
- Claiming deployment-ready outbreak prediction

---

# Notes for Team

- Report Chapter 7.3 retains full honest evaluation; slides are a **curated subset**
- If asked in viva about exceptions, answer from report — do not volunteer on slides
- Module 2 and Module 3 packs use the same presentation-safe policy
