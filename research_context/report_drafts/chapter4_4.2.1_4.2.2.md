# Chapter 4 Draft — Sections 4.2.1 and 4.2.2

**Source of truth:** `CURRENT_ARCHITECTURE.md`, `module_1_forecasting/MODULE_CONTEXT.md`, `module_2_classification/MODULE_CONTEXT.md`, `FEATURE_ENGINEERING_SPEC.md`, `RESEARCH_DECISIONS.md`  
**Scope:** Module 1 and Module 2 only (Module 3 deferred)  
**Status:** Draft for Word paste into interim/final report Chapter 4  
**Last updated:** 2026-07-29

---

### 4.2.1 Module 1: Hybrid Time-Series Case Forecasting

Module 1 focuses on predicting **weekly dengue case counts at the district level** for all 25 administrative districts of Sri Lanka. The module does not attempt sub-district or fine-scale spatial forecasting. Its role in the overall framework is to estimate the expected magnitude of dengue incidence over short forecasting horizons, so that subsequent risk interpretation and alerting can be grounded in a quantitative case forecast.

The module follows a two-stage residual compensation design. Stage 1 models the regular temporal structure of district-level case series. Stage 2 learns systematic residual patterns that remain after the baseline forecast, particularly patterns associated with lagged climate conditions, seasonal anomalies, and short-term epidemiological dynamics.

**Input**

- Historical weekly dengue case counts by district
- District-level climate variables for Stage 2 only (rainfall/precipitation, temperature, and humidity), aligned to the epidemiological week calendar
- Temporal and seasonal descriptors derived from the epidemiological week structure

**Process**

**Stage 1 — SARIMA baseline.**  
A Seasonal Autoregressive Integrated Moving Average (SARIMA) model is fitted independently for each district using historical weekly case counts only. Climate covariates are deliberately excluded from Stage 1. This design choice keeps the baseline focused on trend, autocorrelation, and seasonal temporal structure, and leaves climate-driven and other nonlinear deviations in the residual for Stage 2 to model. Where appropriate, a `log1p` transform of case counts is selected on a per-district basis, with predictions inverse-transformed back to the raw case-count scale before residual construction and evaluation.

**Residual extraction.**  
For each district-week observation used in residual learning, the residual is defined as:

```text
residual = actual_cases - sarima_prediction
```

**Stage 2 — XGBoost residual compensation.**  
An XGBoost regression model is trained to predict the Stage 1 residual. The Stage 2 feature set includes lagged case counts, rolling case statistics, rate-of-change indicators, lagged rainfall/precipitation features, lagged temperature and humidity features, climate anomaly indicators, seasonal cyclic encodings, monsoon indicators, the SARIMA prediction itself, and lagged residual features. The compensation model is therefore intended to correct structured baseline error rather than replace the SARIMA forecast.

**Output**

The final Module 1 forecast is obtained by adding the predicted residual to the Stage 1 forecast:

```text
final_prediction = sarima_prediction + predicted_residual
```

The primary output is a district-week forecast of expected dengue cases. These forecasts support early-warning interpretation and may also inform complementary outbreak-risk analysis in Module 2. Forecast quality is evaluated using time-series metrics under a walk-forward and holdout protocol, as reported in the evaluation chapter.

**Intended users**

District-level public health analysts and decision-makers who require short-horizon estimates of case burden for planning and situational awareness. The module is positioned as a research decision-support component rather than a clinically certified or fully operational deployment system.

**Suggested Figure:**  
Figure 4.X: Two-stage residual compensation workflow for Module 1 (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast).

**Notes for Team:**
- Replace interim wording that claimed “fine spatial scale” forecasting.
- Do not write SARIMAX for Stage 1; climate enters only in Stage 2.
- Keep numeric MASE/DM results for Chapter 7, not here.
- Confirm figure numbering against the final List of Figures.

---

### 4.2.2 Module 2: Hybrid Outbreak Risk Classification

Module 2 addresses a complementary question to Module 1. Rather than forecasting the exact number of cases, it estimates whether a district-week observation corresponds to an **outbreak-risk state** and produces an interpretable risk score for early warning. The module operates at the same district-week resolution as Module 1 and uses the shared epidemiological and climate base tables, while applying Module 2–specific labelling, preprocessing, and modelling choices.

The module also follows a two-stage design, but the meaning of “compensation” differs from Module 1. Stage 1 produces an initial outbreak probability. Stage 2 corrects systematic probability miscalibration so that the resulting risk score more reliably reflects observed outbreak frequency.

**Input**

- Historical weekly dengue case counts by district
- Climate variables (rainfall/precipitation, temperature, and humidity), including lagged values, current-week climate features, and fold-aware climate anomalies
- Seasonal encodings and monsoon indicators
- District identity, used to support a pooled classifier across districts

**Label definition**

Outbreak labels are constructed using a district- and week-specific epidemic threshold based on historical case behaviour:

```text
outbreak = 1 if cases > historical_mean(District, Week) + k × historical_SD(District, Week)
```

The historical mean and standard deviation are computed from strictly prior years within each training window, so that label construction does not leak future information into model fitting. This adaptive definition accounts for cross-district differences in baseline incidence: a case count that is routine in a high-burden district may represent an unusual surge in a low-burden district.

**Process**

**Stage 1 — Baseline outbreak classifier.**  
Stage 1 uses an XGBoost classifier selected after benchmarking against Logistic Regression and Random Forest under a walk-forward validation scheme. The Stage 1 feature set combines epidemiological history features (case lags, rolling statistics, rate-of-change and related trend descriptors, and case-anomaly lags) with climate and seasonal features. Unlike Module 1 Stage 1, Module 2 Stage 1 intentionally includes climate information because its task is direct outbreak-risk discrimination rather than isolation of a pure temporal residual. Class imbalance is handled through class reweighting (`scale_pos_weight` for XGBoost), rather than synthetic oversampling as the production strategy.

**Stage 2 — Probability compensation (calibration).**  
Stage 2 takes the Stage 1 predicted probability and applies a compensation step designed for binary probability outputs. After benchmarking isotonic regression, Platt scaling, and a stacked contextual XGBoost correction model, **isotonic regression** was selected as the official Stage 2 method based on Brier Skill Score. In the accepted design, Stage 2 is therefore primarily a probability-calibration compensator: it adjusts the baseline probability so that predicted risk better matches observed outbreak frequency. A literal residual-regression formulation of the form `label − predicted_probability` was considered and rejected as ill-posed for a binary outcome.

**Output**

The primary Stage 2 output is a calibrated outbreak probability. From this probability, two decision-support outputs are derived using fixed absolute thresholds selected for early-warning utility:

- a binary `alert_flag` for outbreak-oriented alerting
- a three-level `risk_tier` (`low` / `medium` / `high`) for graded interpretation

These outputs are intended to support early-warning communication. They should be interpreted as model-based risk indicators under the defined label and evaluation protocol, not as clinical diagnoses or guaranteed outbreak forecasts.

**Intended users**

District-level health authorities and analysts who need probabilistic outbreak-risk alerts to complement quantitative case forecasts from Module 1.

**Suggested Figure:**  
Figure 4.X: Two-stage Module 2 workflow (epidemic-threshold labelling → XGBoost baseline probability → isotonic calibration → alert flag and risk tier).

**Suggested Table:**  
Table 4.X: Comparison of Module 1 and Module 2 residual-compensation interpretations (case residual vs probability calibration).

**Notes for Team:**
- Interim draft incorrectly implied Stage 1 was climate-free and Stage 2 was mainly climate residual ML; update both.
- Do not present SMOTE as the production imbalance method.
- Threshold values (e.g. 0.170 / 0.570) and metric tables belong mainly in Chapter 7; Chapter 4 may say “fixed absolute thresholds selected for early-warning utility.”
- Optional one-sentence cross-reference: Module 2 does not require Module 1 forecasts as a production input; cross-module alert comparison is an evaluation question (M2-009), not a design dependency for this subsection.
- `CURRENT_ARCHITECTURE.md` still describes Module 2 Stage 2 in broader “environmental anomaly compensation” language; Module 2 living context + Decision 022/023 are the accurate source for this section.

---

## Optional short bridge paragraph (after 4.2.2, before 4.2.3)

Modules 1 and 2 therefore provide complementary district-week views of dengue risk: Module 1 estimates expected case magnitude through residual-corrected forecasting, while Module 2 estimates outbreak likelihood through calibrated probability scoring. Together, they support a multidimensional early-warning interpretation even before spatial hotspot detection is incorporated.

---

## Paste checklist for Word

- [ ] Replace interim 4.2.1 and 4.2.2 text with the sections above (remove internal Notes for Team before final submission)
- [ ] Update any Module 1/2 diagrams in Chapter 4/5 to match SARIMA→XGBoost and XGBoost→isotonic
- [ ] Leave 4.2.3 as existing text or a short placeholder until Module 3 is complete
