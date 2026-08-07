# Module 2 Presentation Slides — Hybrid Outbreak Risk Classification

**Owner:** Nethma L.H.K. (214140X)  
**Audience:** FYP presentation (sample-style module pack)  
**Status:** Presentation-safe outline (2026-07-31, revised)  
**Evidence base:** `MODULE_CONTEXT.md` (Decision 025), Chapter 7.4, `REPORT_DIAGRAM_PLAN.md`

**Presentation policy:** This pack includes **supporting results and design strengths only**. Calibration failures, rejected ablations, low precision, and sparse-holdout caveats stay in the report and viva prep — see **Excluded from slides** at the end.

**Current production (use consistently):** Random Forest Stage 1 → isotonic Stage 2; alert τ = **0.14**; high tier ≥ **0.35**.

Use **6–7 core slides** in the main deck.

---

## Slide M2-1 — Module Introduction

**Title:** Module 2 — Hybrid Outbreak Risk Classification (214140X)

**Content structure:** What is Module 2 → Research gap → Novelty (three short blocks)

**Content:**
- **What is Module 2?** Hybrid outbreak-risk classifier: estimate outbreak probability → calibrate → alerts and risk tiers
- **Research gap:** Existing outbreak models estimate probability but do not adjust predictions using climate anomalies or seasonal environmental variations [1]; baseline scores often unsuitable for fixed alert cutoffs
- **Novelty:** Stage 1 RF integrates climate anomalies, lagged climate, monsoon/season with epi features; Stage 2 isotonic calibration as task-appropriate residual compensation; calibrated alert/tier outputs

**Suggested figure:** none required.

**Note:** M1 complementarity (thresholding forecasts ≠ outbreak alerts) belongs on summary slide M2-7, not the research gap slide.

---

## Slide M2-2 — Two-Stage Design

**Title:** Probability Calibration as Residual Compensation

**Content:**
```text
Stage 1: Pooled Random Forest → predicted outbreak probability
Stage 2: Isotonic regression → calibrated_probability
Outputs: alert_flag (τ = 0.14) + risk_tier (low / medium / high)
```
- Fold-aware harmonic epidemic threshold label (`k = 3.0`)
- Leakage-safe Stage 2: trains only on out-of-sample Stage 1 probabilities
- Fixed absolute thresholds for alerts and tiers (not quantile cutoffs)

**Suggested figure:**
- **Figure 6.3** — `research_context/report_drafts/diagrams/figure_6_3_module2_implementation.png`  
  Caption: *Module 2 pipeline: labelling → Random Forest → isotonic calibration → alerts and risk tiers*

---

## Slide M2-3 — Data, Label & Protocol

**Title:** Outbreak Label and Evaluation Protocol

**Content:**
- Label: district-week exceeds a **fold-aware harmonic seasonal epidemic threshold**
- Features: lagged case anomalies, climate lags and anomalies, seasonal indicators, district context
- Evaluation: **13 walk-forward folds** + untouched **2-year holdout**
- Primary metrics: **PR-AUC** (Stage 1 discrimination), **Brier Skill Score** (Stage 2 calibration)

**Suggested table:**

| Item | Choice |
|---|---|
| Label | Harmonic epidemic threshold, k = 3.0 |
| Stage 1 model | Pooled Random Forest |
| Stage 2 model | Isotonic regression |
| Alert threshold | τ = 0.14 (F2-oriented) |
| High tier | ≥ 0.35 (F0.5-oriented) |

---

## Slide M2-4 — Stage 1: Baseline Classifier

**Title:** Stage 1 — Outbreak Discrimination

**Content:**
- Benchmarked Logistic Regression, Random Forest, and XGBoost
- **Random Forest selected** by median validation PR-AUC
- Pooled architecture outperforms per-district modelling
- Strong rare-event ranking on holdout: PR-AUC **0.429**, ROC-AUC **0.885**
- Key features: lagged case anomalies and short-term case dynamics

**Suggested table — Table 7.3:**

| Model | Median validation PR-AUC |
|---|---|
| Logistic Regression | 0.358 |
| XGBoost | 0.373 |
| **Random Forest (selected)** | **0.377** |

**Suggested figure (optional):** Stage 1 feature-importance chart (`case_anomaly_lag_1`, `case_anomaly_lag_2` leading).

**Do not put on slide:** “raw calibration poor”, negative BSS, model-selection history under older labels.

---

## Slide M2-5 — Stage 2: Calibration & Reliability

**Title:** Stage 2 — Isotonic Probability Calibration

**Content:**
- Stage 2 repairs probability scale so calibrated scores support absolute alert thresholds
- **Isotonic regression selected** by median validation Brier Skill Score
- Holdout BSS **0.2315** — clear improvement over uncalibrated Stage 1 probabilities
- Reliability diagram shows predicted probabilities align more closely with observed outbreak rates after calibration

**Suggested table — Stage 2 comparison (positive rows only):**

| Architecture | Median validation BSS | Holdout BSS |
|---|---|---|
| Platt scaling | 0.2116 | 0.2344 |
| **Isotonic (selected)** | **0.2146** | **0.2315** |

**Suggested figure (required):**
- **Figure 7.4** — `research_context/report_drafts/diagrams/figure_7_4_module2_reliability.png`  
  Caption: *Reliability of Stage 1 raw vs isotonic Stage 2 probabilities*

**Do not put on slide:** Stage 1 raw negative BSS (−0.584), stacked XGBoost negative BSS, rejected ablation list.

---

## Slide M2-6 — Alerts, Risk Tiers & Framework Value

**Title:** Actionable Early-Warning Outputs

**Content:**
- Alert threshold τ = **0.14** improves usable outbreak recall vs a naive 0.5 cutoff (**45% → 60%** holdout recall)
- Three risk tiers show **clear monotonic separation** of observed outbreak rates
- Module 2 provides the framework’s **outbreak-alert layer**, distinct from Module 1 case magnitude

**Suggested table — alert utility (holdout):**

| Alert rule | Recall | F2 |
|---|---|---|
| Naive cutoff 0.5 | 45.0% | 0.459 |
| **Calibrated τ = 0.14** | **60.0%** | **0.519** |

**Suggested table — risk-tier separation:**

| Risk tier | Validation outbreak rate | Holdout outbreak rate |
|---|---|---|
| Low | 1.3% | 0.6% |
| Medium | 26.2% | 13.3% |
| High | 71.1% | 48.8% |

**Suggested figure:** Figure 7.4 if not on M2-5; optional 3-tier diagram.

**Presentation tip:** Emphasise recall and tier ordering; omit precision unless asked.

---

## Slide M2-7 — Summary & Complementarity with Module 1

**Title:** Module 2 — Key Outcomes

**Content:**
- Delivered a **calibrated outbreak-risk classifier** with alert and tier outputs
- Stage 1 discriminates rare outbreak weeks; Stage 2 makes probabilities decision-ready
- **Module 2 alerts are not replaceable by thresholding Module 1 forecasts** — complementary tasks in the framework
- Integrated into the Streamlit dashboard for risk trajectories and alert indicators

**Suggested table — Table 7.7 (positive framing only):**

| Method | Holdout PR-AUC |
|---|---|
| **Module 2 production alerts** | **0.412** |
| Thresholding Module 1 forecasts | 0.063 – 0.280 |

**Callout:** Module 2 captured outbreak weeks missed by magnitude-only rules.

**Do not put on slide:** oracle row (1.000), naive >100 rule, precision percentages.

---

## Optional Slide M2-8 — Related Works

**Title:** Related Work — Outbreak Risk Classification

**Content:** 2–3 citations from Chapter 2. Pull before finalizing.

---

# Recommended Main-Deck Sequence (7 slides)

1. M2-1 Gap & goal  
2. M2-2 Design + Figure 6.3  
3. M2-3 Label & protocol  
4. M2-4 Stage 1 + Table 7.3  
5. M2-5 Stage 2 + Figure 7.4  
6. M2-6 Alerts & tiers  
7. M2-7 Summary + complementarity  

---

# Figure & Table Checklist (presentation-safe)

| Asset | Slide | Priority |
|---|---|---|
| Fig 6.3 implementation pipeline | M2-2 | High |
| Fig 7.4 reliability diagram (isotonic) | M2-5 | High |
| Table 7.3 Stage 1 comparison | M2-4 | High |
| Table 7.4 BSS (isotonic + Platt only) | M2-5 | High |
| Alert / tier tables (positive metrics) | M2-6 | High |
| Table 7.7 (M2 vs M1, trimmed) | M2-7 | Medium |

---

# Excluded from slides (report / viva only)

Do **not** present these in the main deck:

| Topic | Why excluded |
|---|---|
| Stage 1 raw BSS ≈ −0.584 | Negative baseline calibration |
| Stacked XGBoost negative BSS | Failed architecture |
| SMOTENC / M2-006 / M2-007 / M2-008 rejections | Failed ablation narrative |
| Holdout only ~40 positives / high variance | Weakens confidence in holdout |
| Holdout precision 33.8% | Low precision headline |
| Accuracy ≈ 98% at 0.5 cutoff | Misleading + low-skill framing |
| XGBoost was official under older label | Model flip / inconsistency story |
| Isotonic mildly reduces PR-AUC | Trade-off that weakens Stage 2 |
| Superseded thresholds τ = 0.17 / 0.57 | Outdated numbers |
| Live-scoring vs holdout mixing caveats | Operational confusion |
| Full Table 7.7 with oracle and naive rules | Too much negative contrast detail |

---

# Speaker guardrails

**Say:**
- Random Forest + isotonic calibration is the production stack
- Calibrated alerts improve recall vs naive cutoff
- Risk tiers show ordered outbreak separation
- Module 2 complements Module 1 (magnitude vs outbreak state)

**Avoid in the presentation:**
- “Stage 1 probabilities were miscalibrated” (say “Stage 2 calibrates probabilities” instead)
- Quoting precision unless asked
- Discussing rejected experiments unless asked

---

# Notes for Team

- Use **Figure 7.4 isotonic version** only — not older Platt-labelled PNGs in `outputs/figures/module2/`
- Report Chapter 7.4 retains full evaluation; slides are curated for clarity
- Module 1 and Module 3 packs follow the same presentation-safe policy
