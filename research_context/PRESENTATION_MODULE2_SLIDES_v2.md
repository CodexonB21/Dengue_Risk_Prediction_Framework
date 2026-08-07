# Module 2 Presentation Slides — Hybrid Outbreak Risk Classification (v2)

**Owner:** Nethma L.H.K. (214140X)
**Audience:** FYP presentation (sample-style module pack)
**Status:** Presentation-safe outline (2026-08-06, v2 — updated after Decision 047/M2-013)
**Supersedes:** `PRESENTATION_MODULE2_SLIDES.md` (v1 retained unchanged — describes the pre-tuning, isotonic-era production stack; do not mix numbers from the two files)
**Evidence base:** `MODULE_CONTEXT.md` (Decisions 025, 047), Chapter 7.4 v2, `REPORT_DIAGRAM_PLAN.md`

**Presentation policy:** This pack includes **supporting results and design strengths only**. Calibration failures, rejected ablations, low precision, and sparse-holdout caveats stay in the report and viva prep — see **Excluded from slides** at the end.

**Current production (use consistently):** tuned Random Forest Stage 1 → Platt-scaling Stage 2; alert τ = **0.10**; high tier ≥ **0.50**.

Use **6–7 core slides** in the main deck.

---

## Slide M2-1 — Module Introduction

**Title:** Module 2 — Hybrid Outbreak Risk Classification (214140X)

**Content structure:** What is Module 2 → Research gap → Novelty (three short blocks)

**Content:**
- **What is Module 2?** Hybrid outbreak-risk classifier: estimate outbreak probability → calibrate → alerts and risk tiers
- **Research gap:** Existing outbreak models estimate probability but do not adjust predictions using climate anomalies or seasonal environmental variations [1]; baseline scores often unsuitable for fixed alert cutoffs
- **Novelty:** Stage 1 RF integrates climate anomalies, lagged climate, monsoon/season with epi features; Stage 2 probability calibration (Platt scaling) as task-appropriate residual compensation; calibrated alert/tier outputs

**Suggested figure:** none required.

**Note:** M1 complementarity (thresholding forecasts ≠ outbreak alerts) belongs on summary slide M2-7, not the research gap slide.

---

## Slide M2-2 — Two-Stage Design

**Title:** Probability Calibration as Residual Compensation

**Content:**
```text
Stage 1: Pooled, tuned Random Forest → predicted outbreak probability
Stage 2: Platt scaling → calibrated_probability
Outputs: alert_flag (τ = 0.10) + risk_tier (low / medium / high)
```
- Fold-aware harmonic epidemic threshold label (`k = 3.0`)
- Leakage-safe Stage 2: trains only on out-of-sample Stage 1 probabilities
- Fixed absolute thresholds for alerts and tiers (not quantile cutoffs)

**Suggested figure:**
- **Figure 6.3** — `research_context/report_drafts/diagrams/figure_6_3_module2_implementation.png` (needs re-export — v1 asset still labels Stage 2 "isotonic")
  Caption: *Module 2 pipeline: labelling → tuned Random Forest → Platt-scaling calibration → alerts and risk tiers*

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
| Stage 1 model | Pooled Random Forest (tuned) |
| Stage 2 model | Platt scaling |
| Alert threshold | τ = 0.10 (F2-oriented) |
| High tier | ≥ 0.50 (F0.5-oriented) |

---

## Slide M2-4 — Stage 1: Baseline Classifier

**Title:** Stage 1 — Outbreak Discrimination

**Content:**
- Benchmarked Logistic Regression, Random Forest, and XGBoost; **Random Forest selected** by median validation PR-AUC
- Random Forest subsequently tuned via a 50-trial hyperparameter search, confirmed on the untouched holdout block
- Pooled architecture outperforms per-district modelling
- Strong rare-event ranking on holdout: PR-AUC **0.423**, ROC-AUC **0.905**
- Key features: lagged case anomalies and short-term case dynamics (top two features alone account for over half of total importance)

**Suggested table — Table 7.3:**

| Model | Median validation PR-AUC |
|---|---|
| Logistic Regression | 0.355 |
| XGBoost | 0.382 |
| Random Forest (selected model type) | 0.390 |
| **Random Forest, tuned (production)** | **0.395** |

**Suggested figure (optional):** Stage 1 feature-importance chart (`case_anomaly_lag_1`, `case_anomaly_lag_2` leading).

**Do not put on slide:** "raw calibration poor", negative BSS, model-selection history under older labels, the specific rejected tuning variants (balanced_subsample, Gradient Boosting).

---

## Slide M2-5 — Stage 2: Calibration & Reliability

**Title:** Stage 2 — Platt-Scaling Probability Calibration

**Content:**
- Stage 2 repairs probability scale so calibrated scores support absolute alert thresholds
- **Platt scaling selected** by median validation Brier Skill Score (this flipped from isotonic once Stage 1 was tuned — Stage 1's changed output distribution drove the flip, not a Stage 2 change)
- Holdout BSS **0.267** — clear improvement over uncalibrated Stage 1 probabilities
- Reliability diagram shows predicted probabilities align more closely with observed outbreak rates after calibration

**Suggested table — Stage 2 comparison (positive rows only):**

| Architecture | Median validation BSS | Holdout BSS |
|---|---|---|
| **Platt (selected)** | **0.227** | **0.267** |
| Isotonic | 0.220 | 0.259 |

**Suggested figure (required):**
- **Figure 7.4** — `outputs/figures/module2/reliability_diagram_{validation,holdout}.png` (needs recomposing into a single figure asset — the v1 composite PNG predates this update and still shows isotonic)
  Caption: *Reliability of Stage 1 raw vs Platt-scaled Stage 2 probabilities*

**Do not put on slide:** Stage 1 raw negative BSS (−0.33 validation / −0.19 holdout), stacked XGBoost negative BSS, rejected ablation list (M2-010/011/014).

---

## Slide M2-6 — Alerts, Risk Tiers & Framework Value

**Title:** Actionable Early-Warning Outputs

**Content:**
- Alert threshold τ = **0.10** improves usable outbreak recall vs a naive 0.5 cutoff (**37.5% → 62.5%** holdout recall)
- Three risk tiers show **clear monotonic separation** of observed outbreak rates, and separate more cleanly than the prior production stack
- Module 2 provides the framework's **outbreak-alert layer**, distinct from Module 1 case magnitude

**Suggested table — alert utility (holdout):**

| Alert rule | Recall | F2 |
|---|---|---|
| Naive cutoff 0.5 | 37.5% | 0.408 |
| **Calibrated τ = 0.10** | **62.5%** | **0.536** |

**Suggested table — risk-tier separation:**

| Risk tier | Validation outbreak rate | Holdout outbreak rate |
|---|---|---|
| Low | 1.2% | 0.6% |
| Medium | 34.8% | 20.4% |
| High | 78.7% | 62.5% |

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
| **Module 2 production alerts** | **0.423** |
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
| Fig 6.3 implementation pipeline | M2-2 | High — **re-export needed**, v1 PNG labels Stage 2 "isotonic" |
| Fig 7.4 reliability diagram (Platt) | M2-5 | High — **recompose needed** from fresh `reliability_diagram_{validation,holdout}.png` |
| Table 7.3 Stage 1 comparison | M2-4 | High |
| Table 7.4 BSS (Platt + isotonic only) | M2-5 | High |
| Alert / tier tables (positive metrics) | M2-6 | High |
| Table 7.7 (M2 vs M1, trimmed) | M2-7 | Medium |

---

# Excluded from slides (report / viva only)

Do **not** present these in the main deck:

| Topic | Why excluded |
|---|---|
| Stage 1 raw BSS ≈ −0.33 / −0.19 | Negative baseline calibration |
| Stacked XGBoost negative BSS | Failed architecture |
| SMOTENC / M2-006 / M2-007 / M2-008 rejections | Failed ablation narrative |
| M2-010 (ensembling), M2-011 (adaptive k), M2-014 (M3 feature) | Failed/mixed ablation narrative |
| Holdout only ~40 positives / high variance | Weakens confidence in holdout |
| Holdout precision 34.2% | Low precision headline |
| XGBoost was official under older label | Model flip / inconsistency story |
| Stage 2 architecture flipped isotonic → Platt after tuning | Model-flip inconsistency story (true, but confusing without full context) |
| Superseded thresholds τ = 0.14 / 0.35, τ = 0.17 / 0.57 | Outdated numbers |
| Live-scoring vs holdout mixing caveats | Operational confusion |
| Full Table 7.7 with oracle and naive rules | Too much negative contrast detail |

---

# Speaker guardrails

**Say:**
- Random Forest (tuned) + Platt-scaling calibration is the production stack
- Calibrated alerts improve recall vs naive cutoff
- Risk tiers show ordered outbreak separation
- Module 2 complements Module 1 (magnitude vs outbreak state)

**Avoid in the presentation:**
- "Stage 1 probabilities were miscalibrated" (say "Stage 2 calibrates probabilities" instead)
- Quoting precision unless asked
- Discussing rejected experiments unless asked
- Explaining *why* the architecture flipped from isotonic to Platt unless directly asked (the honest answer — Stage 1 tuning changed the probability distribution — is fine to give if asked, just not something to volunteer)

---

# Notes for Team

- Use **Figure 7.4 Platt version** only, once recomposed — not the v1 isotonic-labelled composite PNG, and not the raw pipeline output without a proper figure caption/layout
- Report Chapter 7.4 (v2) retains full evaluation; slides are curated for clarity
- Module 1 and Module 3 packs follow the same presentation-safe policy
- v1 of this file (`PRESENTATION_MODULE2_SLIDES.md`) is retained for reference only — do not present from it, its numbers predate Decision 047
