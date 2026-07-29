# Chapter 5 Draft — Sections 5.3.1 and 5.3.2

**Source of truth:** `CURRENT_ARCHITECTURE.md`, `PIPELINE_ARCHITECTURE_PLAN.md`, Chapter 4 drafts, Module 1/2 contexts  
**Scope:** High-level design of Modules 1 and 2 only (Module 3 deferred)  
**Status:** Draft for Word paste into Chapter 5  
**Last updated:** 2026-07-29

**Design vs approach vs implementation**

| Chapter | Role of this content |
|---|---|
| Chapter 4 | Conceptual “what/why” of each module |
| **Chapter 5 (this draft)** | Structural design: components, data flow, stage boundaries, leakage guards |
| Chapter 6 | How the design was implemented in code/pipelines |

The interim report left 5.3.1 and 5.3.2 as figure placeholders only. The text below should accompany updated Module 1/2 architecture figures.

---

### 5.3.1 Module 1: Hybrid Time-Series Case Forecasting

The design of Module 1 is organised as a district-level weekly forecasting pipeline with a strict separation between a climate-free temporal baseline and a climate-aware residual compensator. The module estimates expected dengue case magnitude; it does not classify outbreak labels and does not produce spatial hotspot surfaces.

#### Design objectives

1. Capture regular temporal structure in weekly district case series using an interpretable statistical baseline.
2. Preserve climate-driven and nonlinear deviations in the residual by excluding climate from Stage 1.
3. Correct structured residual error with a supervised machine learning compensator.
4. Evaluate forecasts under temporally valid walk-forward and holdout protocols that prevent future leakage.

#### Architectural components

Module 1 is designed as the following sequence of components:

```text
Shared cleaned tables
        ↓
Module 1 preprocessing
  (week-53 merge; seasonal-naive gap fill; is_imputed)
        ↓
Stage 1: per-district SARIMA (cases only)
        ↓
Residual extraction
  residual = actual_cases - sarima_prediction
        ↓
Stage 2 feature construction
  (case lags, climate lags/anomalies, seasonality,
   sarima_prediction, residual lags)
        ↓
Stage 2: pooled XGBoost residual regressor
        ↓
Final forecast
  final_prediction = sarima_prediction + predicted_residual
        ↓
Evaluation outputs / forecast artifacts
```

**Shared input layer.**  
Module 1 consumes shared epidemiological and weekly climate tables after module-agnostic cleaning (including the Kalmunai→Ampara merge to a 25-district set). Shared cleaning does not apply SARIMA-specific calendar constraints; those remain Module 1–scoped.

**Module-specific preprocessing layer.**  
Two design decisions are central:

- week 53 is merged into week 52 so that SARIMA’s seasonal period remains fixed at 52 weeks;
- missing weeks are seasonally-naive imputed and flagged, preserving lag alignment while excluding imputed rows from evaluation targets.

**Stage 1 baseline design.**  
Stage 1 is a per-district SARIMA model on weekly case counts only. Climate covariates are excluded by design so that Stage 1 represents temporal baseline behaviour rather than absorbing the climate signal that Stage 2 is intended to exploit. Optional `log1p` transformation is treated as a per-district modelling choice, with inverse transformation back to the case-count scale before residual construction.

**Residual interface.**  
The residual is the formal interface between stages:

```text
residual = actual_cases - sarima_prediction
```

This residual is the Stage 2 learning target. The design therefore treats residual compensation as additive correction of baseline error, not as a replacement forecasting model.

**Stage 2 compensation design.**  
Stage 2 uses an XGBoost regressor over residual-relevant features: short-term case dynamics, lagged precipitation/temperature/humidity, fold-aware climate anomalies, seasonal/monsoon indicators, the SARIMA prediction, and residual lags. Climate anomalies are designed to be recomputed within each walk-forward training window so that future climate norms cannot leak into earlier folds.

**Output design.**  
The compensated forecast is:

```text
final_prediction = sarima_prediction + predicted_residual
```

Primary design output is a district-week expected case forecast. Secondary artifacts include residual series and evaluation metrics for comparison of Stage 1 versus Stage 1+Stage 2 performance.

**Validation design.**  
The module is designed around expanding-window walk-forward validation by year, plus a final untouched multi-year holdout block. This design choice prioritises temporal realism over random split convenience.

Figure 5.X presents the high-level architecture of Module 1.

**Suggested Figure:**  
Figure 5.X: High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting  
*(Replace interim “Figure 3” with an updated diagram matching the flow above.)*

**Diagram drawing notes:**
- Show climate entering **only** at Stage 2.
- Label the residual box explicitly with the residual equation.
- Show `is_imputed` / evaluation exclusion as a small side annotation on preprocessing, not as a separate module.
- Do not depict sub-district spatial inputs.

**Notes for Team:**
- Keep this section structural; avoid repeating full feature lists from Chapter 6.
- Do not claim Module 1 production depends on Module 2 outputs.
- If the Word figure still shows SARIMAX or climate in Stage 1, redraw it before pasting this text.

---

### 5.3.2 Module 2: Hybrid Outbreak Risk Classification

The design of Module 2 complements Module 1 by estimating outbreak risk rather than case magnitude. It operates at the same district-week resolution and reuses shared epidemiological/climate base tables, but applies Module 2–specific labelling, preprocessing, and a different interpretation of residual compensation: **probability calibration** rather than additive case-residual correction.

#### Design objectives

1. Define outbreak labels in a district- and season-aware manner without leaking future history into the label.
2. Produce a baseline outbreak probability from epidemiological and climate context.
3. Compensate systematic probability miscalibration so that predicted risk better matches observed outbreak frequency.
4. Convert calibrated probabilities into interpretable early-warning outputs (`alert_flag`, `risk_tier`).

#### Architectural components

Module 2 is designed as the following sequence of components:

```text
Shared cleaned tables
        ↓
Module 2 preprocessing
  (week-53 kept unmerged; seasonal-naive gap fill;
   is_imputed masking for case-derived features)
        ↓
Fold-aware epidemic-threshold labelling
  outbreak = 1 if cases > mean + k × SD
  (strictly prior years only)
        ↓
Stage 1 feature construction
  (case history + climate lags/current climate/anomalies
   + seasonality + district)
        ↓
Stage 1: pooled XGBoost outbreak classifier
        ↓
Stage 1 predicted_probability
        ↓
Stage 2: isotonic probability calibration
        ↓
Decision outputs
  calibrated_probability → alert_flag / risk_tier
        ↓
Evaluation outputs / risk artifacts
```

**Shared input layer.**  
Module 2 reads the same shared cleaned base tables as Module 1. Independence of module-specific design choices is intentional: a transformation required only by SARIMA is not imposed on Module 2’s labelling logic.

**Module-specific preprocessing layer.**  
Two design decisions distinguish Module 2 from Module 1:

- week 53 is retained as its own week, because merging would alter epidemic-threshold labelling and contaminate week-52 historical statistics;
- imputed case values are masked before derivation of case-based features, so fabricated counts cannot enter lag or rolling inputs for neighbouring real weeks.

**Label design.**  
Outbreak status is defined by a fold-aware epidemic threshold using historical mean and dispersion estimated from strictly prior years. The production design uses a harmonic seasonal estimator for historical mean/dispersion and a tuned multiplier `k`, selected to produce a more stable and epidemiologically plausible outbreak prevalence than a fragile exact-week sample estimator. Undefined labels (insufficient history) are excluded from training and scoring rather than forced to zero.

**Stage 1 classifier design.**  
Stage 1 is a pooled binary classifier with district as a categorical feature. The accepted Stage 1 model is XGBoost, selected after comparison with Logistic Regression and Random Forest under walk-forward validation. Unlike Module 1 Stage 1, Module 2 Stage 1 is designed to include climate features because the task is direct risk discrimination, not isolation of a pure temporal residual. Class imbalance is handled by class reweighting rather than synthetic oversampling in the production design.

**Stage 2 compensation design.**  
Stage 2 receives the Stage 1 predicted probability and applies a probability-compensation layer. The accepted design uses isotonic regression after benchmarking against Platt scaling and a stacked contextual correction model. In architectural terms, Module 2’s second stage corrects calibration error in the probability space:

```text
calibrated_probability = g(predicted_probability)
```

where `g(·)` denotes the fitted isotonic mapping. This is conceptually aligned with residual compensation (baseline output + correction), but is not an additive case-count residual model.

**Output design.**  
Primary output is the calibrated outbreak probability. Secondary decision-support outputs are derived using fixed absolute probability thresholds:

- `alert_flag` for binary early-warning use
- `risk_tier` (`low` / `medium` / `high`) for graded interpretation

These outputs are designed as research decision-support indicators under the defined label protocol, not as clinical diagnoses.

**Validation design.**  
Module 2 uses walk-forward validation with a Module-specific minimum training-history setting that ensures early folds contain enough defined labels, followed by an untouched holdout block for final reporting. Discrimination and calibration are both first-class design concerns: Stage 1 emphasises ranking quality (e.g. PR-AUC under class imbalance), while Stage 2 emphasises probability reliability (e.g. Brier Skill Score).

Figure 5.X presents the high-level architecture of Module 2.

**Suggested Figure:**  
Figure 5.X: High-level architecture of Module 2 — Hybrid Outbreak Risk Classification  
*(Replace interim “Figure 4” with an updated diagram matching the flow above.)*

**Suggested Table:**  
Table 5.X: Design contrast between Module 1 and Module 2 residual-compensation architectures.

| Design aspect | Module 1 | Module 2 |
|---|---|---|
| Prediction target | Weekly case count | Outbreak risk (binary label → probability) |
| Stage 1 model | Per-district SARIMA | Pooled XGBoost classifier |
| Climate in Stage 1 | Excluded | Included |
| Week-53 policy | Merge into week 52 | Keep unmerged |
| Stage 2 target | Case residual | Probability calibration |
| Stage 2 model | XGBoost regressor | Isotonic regression |
| Final decision output | `final_prediction` (cases) | `calibrated_probability`, `alert_flag`, `risk_tier` |

**Diagram drawing notes:**
- Show labelling as an explicit box before Stage 1.
- Show Stage 2 as calibration (`predicted_probability` → `calibrated_probability`), not as climate residual regression.
- Show `alert_flag` / `risk_tier` as downstream thresholding, not as a separate third model stage.
- Optionally annotate that Module 1 forecasts are not a required production input to Module 2 Stage 1.

**Notes for Team:**
- Interim Figure 4 likely still reflects the older “climate-free Stage 1 + environmental residual Stage 2” story; redraw before viva/final submission.
- Do not present multi-class labelling as the primary architecture; graded risk comes from calibrated probability thresholds.
- Cross-module comparison (e.g. thresholding Module 1 forecasts vs Module 2 alerts) is an evaluation design topic for Chapter 7, not a hard architectural dependency in 5.3.2.

---

## Optional short bridge (end of 5.3.2, before 5.3.3)

Modules 1 and 2 therefore share a common residual-compensation philosophy while differing in stage semantics, climate placement, and calendar handling. This deliberate divergence is part of the framework design: each module’s second stage corrects the error type that remains after its own baseline, rather than forcing a single identical pipeline onto both forecasting and classification.

---

## Paste checklist for Word

- [ ] Replace empty 5.3.1 / 5.3.2 placeholders with the sections above
- [ ] Redraw Module 1 and Module 2 architecture figures to match the ASCII flows
- [ ] Insert Table 5.X (Module 1 vs Module 2 design contrast) if space allows
- [ ] Leave 5.3.3 as placeholder until Module 3 design is stable
- [ ] Later align 5.1 / 5.2 wording with shared vs module-specific preprocessing (Decision 013)
- [ ] Strip “Notes for Team” before final submission
