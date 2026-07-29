# Chapter 6 Draft — Sections 6.2.1, 6.2.2, 6.3.1, 6.3.2

**Source of truth:** `DATA_DICTIONARY.md`, `PIPELINE_ARCHITECTURE_PLAN.md`, `FEATURE_ENGINEERING_SPEC.md`, `RESEARCH_DECISIONS.md`, Module 1/2 contexts  
**Scope:** Datasets and Module 1/2 implementation only (Module 3 deferred)  
**Status:** Draft for Word paste into Chapter 6  
**Last updated:** 2026-07-29

---

### 6.2.1 Epidemiological Dataset: Weekly Dengue Case Counts

Weekly dengue case counts were obtained from the Weekly Epidemiological Reports (WER) published by the Epidemiology Unit, Ministry of Health, Sri Lanka (`epid.gov.lk`). The dataset provides district-level surveillance counts for Sri Lanka’s administrative districts and forms the primary epidemiological input for Modules 1 and 2.

Each record includes district name, epidemiological year, epidemiological week number, week start and end dates, and the number of reported dengue cases for that district-week. Weeks follow the **Sri Lanka Ministry of Health epidemiological week standard**, rather than a plain ISO calendar week. The audited series covers approximately 19.5 years, from 2006-12-23 to 2026-06-21, and spans multiple outbreak cycles.

The series exhibits Sri Lanka’s well-documented bimodal dengue seasonality, with elevated transmission commonly associated with the southwest monsoon and northeast monsoon periods. Case burden is typically higher in densely populated western and related high-incidence districts such as Colombo, Gampaha, Kalutara, and Kandy. Many district-weeks also report zero cases, creating a zero-inflated structure that influences transform choice, metric selection, and model interpretation.

Before module-specific modelling, shared preprocessing merges the `Kalmunai` reporting series into `Ampara` (case counts summed by epidemiological week), producing a consistent 25-district modelling list aligned with available climate stations. Duplicate `(District, Year, Week)` collisions identified during data auditing were corrected in the cleaned source file prior to modelling.

**Role in the framework**

- **Module 1:** weekly case counts are the sole Stage 1 SARIMA input and supply lagged case features for Stage 2 residual compensation.
- **Module 2:** the same case series is used to construct fold-aware epidemic-threshold outbreak labels and case-history features for classification.

**Suggested Table:**  
Table 6.X: Structure of the weekly epidemiological dataset (column names and roles).

**Notes for Team:**
- Do not claim sub-district case locations; data are district aggregates.
- Avoid citing Module 3 spatial weighting here until Module 3 is finalized.
- Exact cleaned row counts can be confirmed from `data/processed/shared/epidemiological_weekly.csv` before final submission.

---

### 6.2.2 Meteorological Dataset: Open-Meteo District Climate Series

Meteorological covariates were obtained from **Open-Meteo** daily weather series for a representative point in each of the 25 modelling districts. Daily records were temporally aligned to the Ministry of Health epidemiological week calendar and aggregated to weekly resolution for modelling. This climate source replaced the earlier NASA POWER-based interim description and is the current production weather input for Modules 1 and 2.

**Spatial resolution caveat.**  
Open-Meteo values are point samples, not district-wide spatial averages. Larger districts may therefore have reduced spatial representativeness. This is a data-source constraint and is stated explicitly as a modelling limitation.

**Coverage and refresh.**  
Historical daily coverage begins in 2007-01-01 and is maintained through archive and forecast refresh scripts. Observed daily weather is extended with short-range forecast days where required for operational refresh. Weekly aggregation uses the shared master epidemiological-week calendar so that case and climate rows share a common temporal key.

**Variables and weekly aggregation.**  
The daily series includes temperature, relative humidity, rain, and precipitation fields, together with ancillary variables such as apparent temperature and weather code. For modelling, daily values are aggregated to epidemiological weeks as follows:

| Daily variable family | Weekly aggregation used in modelling |
|---|---|
| Temperature (`temperature_2m_*`) | Weekly mean of daily mean / max / min as required by the feature pipeline |
| Relative humidity (`relative_humidity_2m_*`) | Weekly mean of daily mean / max / min as required |
| Precipitation (`precipitation_sum`) | Weekly sum |
| Rain (`rain_sum`) | Available, but not used as the primary rainfall feature |
| Weather code (WMO) | Retained in the shared climate table but excluded from Module 1/2 model features by default |

**Rainfall feature choice.**  
Module 1 and Module 2 rainfall lag and anomaly features are derived from `precipitation_sum`, not `rain_sum`. This choice reflects Open-Meteo’s definition that precipitation includes rain plus showers (and snowfall liquid-equivalent). Because Sri Lanka’s monsoon rainfall is strongly shower-driven, `precipitation_sum` provides a more complete water-input signal for dengue-relevant breeding habitat than rain alone.

**Role in the framework**

- **Module 1:** climate enters Stage 2 residual compensation only; Stage 1 SARIMA remains case-only.
- **Module 2:** lagged climate, current-week climate, and fold-aware climate anomalies are included in Stage 1 outbreak classification features.

**Suggested Table:**  
Table 6.X: Open-Meteo daily variables and weekly aggregation rules used by Modules 1 and 2.

**Notes for Team:**
- Delete all NASA POWER / MERRA-2 / PRECTOTCORR wording from the interim draft.
- Do not describe CHIRPS as the Module 1/2 climate source.
- Point-sample limitation should also appear in Challenges/Limitations later.

---

### 6.3.1 Module 1: Hybrid Time-Series Forecasting Implementation

Module 1 was implemented as a layered pipeline: shared cleaning, Module 1–specific temporal adjustments, Stage 1 SARIMA baseline forecasting, Stage 2 feature construction, and XGBoost residual compensation. The implementation follows the accepted residual-compensation principle:

```text
residual = actual_cases - sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

#### Shared base preparation

Shared preprocessing produces cleaned base tables used by Modules 1 and 2, including:

- Kalmunai→Ampara merge to a 25-district modelling set
- a master epidemiological-week calendar
- weekly climate aggregation from Open-Meteo daily records
- interpolated annual population fields for reporting-layer indicators where required

Transformations that exist only to satisfy SARIMA’s modelling assumptions are applied in the Module 1 layer rather than forced onto every module.

#### Module 1–specific preprocessing

**Week-53 handling.**  
For years containing 53 epidemiological weeks (2009, 2016, 2019, 2021), week 53 is merged into week 52 (cases summed; climate averaged). This keeps the seasonal period fixed at 52 weeks for SARIMA and ensures cyclic week encodings remain well defined on a `[1, 52]` week index.

**Missing-week imputation.**  
Genuine gaps in the case series are filled using seasonal-naive imputation (same district, same epidemiological week across other years), with an `is_imputed` flag. Imputed rows are retained for lag alignment but are excluded from evaluation targets and from serving as Stage 2 prediction targets. Where reporting-anomaly logic is applied, untrusted case values are masked during feature derivation so that fabricated or suspect values do not silently contaminate lag and rolling features.

**Climate join.**  
Module 1 joins the shared weekly climate table to the Module 1 modelling table on district and epidemiological week. The categorical weather code is excluded from Stage 2 features by default.

#### Stage 1: SARIMA baseline

Stage 1 fits a district-specific SARIMA model on weekly case counts only. Climate covariates are excluded. Candidate orders and optional `log1p` transforms were selected using constrained auto-ARIMA search on pre-holdout history and then validated under walk-forward evaluation. Predictions are inverse-transformed to the raw case-count scale before residual construction. Non-negativity is enforced by clipping forecasts at zero where required.

#### Stage 2: feature engineering and residual compensation

Stage 2 predicts the SARIMA residual using an XGBoost regressor. Fold-agnostic features include:

- case lags (1–4 weeks), 4-week rolling mean/standard deviation, and rate of change
- rainfall/precipitation lags (2–8 weeks)
- temperature and humidity lags (1–4 weeks)
- seasonal encodings (`sin_week`, `cos_week`) and southwest/northeast monsoon indicators
- SARIMA prediction and residual lags

Fold-aware climate anomalies (rainfall, temperature, humidity) are recomputed inside each walk-forward fold using only that fold’s training window, preventing leakage of future climate norms into earlier folds.

#### Validation and holdout design

Module 1 uses expanding-window walk-forward validation by year, with a final untouched holdout block of the most recent two years (104 weeks per district under the Module 1 calendar). Metrics are computed after excluding imputed evaluation rows. Stage 1 and Stage 1+Stage 2 forecasts are compared using error metrics such as MAE, RMSE, sMAPE, and MASE, with additional residual-compensation diagnostics reported in the evaluation chapter.

**Suggested Figure:**  
Figure 6.X: Module 1 implementation pipeline (shared tables → Module 1 preprocessing → SARIMA → residual features → XGBoost → final forecast).

**Suggested Table:**  
Table 6.X: Module 1 Stage 2 feature groups and leakage-safe computation rules.

**Notes for Team:**
- Interim text claimed linear/forward-fill imputation and a simple 2007–2023 / 2024–2025 split; replace with seasonal-naive + `is_imputed` and walk-forward + 2-year holdout.
- Do not say rolling case features were inputs to SARIMA; they belong to Stage 2.
- Numeric performance belongs in Chapter 7.

---

### 6.3.2 Module 2: Outbreak Risk Classification Implementation

Module 2 was implemented on the same shared epidemiological and climate base tables as Module 1, but with Module 2–specific preprocessing, labelling, feature construction, and two-stage modelling. The module predicts outbreak risk rather than exact case counts.

#### Module 2–specific preprocessing

**Missing weeks.**  
As in Module 1, missing weeks are seasonally-naive imputed and flagged with `is_imputed` to preserve lag alignment. Imputed rows are excluded as label targets and masked to `NaN` before derivation of case-based features (lags, rolling statistics, and case-anomaly lags), so fabricated values cannot leak into neighbouring real weeks.

**Week-53 handling (deliberate divergence from Module 1).**  
Module 2 keeps week 53 as its own week and does **not** merge it into week 52. Merging would sum two real weeks before epidemic-threshold labelling and could distort week-52 historical statistics used for labelling. Unmerged week-53 rows typically remain unlabeled because they lack sufficient repeated-year history.

**Climate and exclusions.**  
Weekly climate is joined from the shared table. Weather code is excluded from model features by default. Population-derived reporting fields may be retained for interpretation, but leakage-prone columns such as contemporaneous `Number_of_Cases` and `cases_per_100k` are excluded from the model feature matrix.

#### Outbreak label construction

Binary outbreak labels use a fold-aware epidemic threshold:

```text
outbreak = 1 if Number_of_Cases > historical_mean(District, Week) + k × historical_SD(District, Week)
```

Historical mean and dispersion are estimated from **strictly prior years only**. The production estimator uses a per-district harmonic seasonal fit rather than a fragile exact-week sample mean/SD, with `k = 3.0` selected after label-balance auditing under the revised estimator. Rows without sufficient prior history receive an undefined label and are excluded from training and scoring rather than defaulted to zero.

This design yields district- and season-aware labels that respect cross-district incidence heterogeneity. Graded risk communication is handled later through calibrated probability thresholds (`alert_flag` and `risk_tier`), rather than by treating a separate multi-class label as the primary modelling target.

#### Stage 1: baseline classifier

Stage 1 constructs a pooled Random Forest classifier with district as a categorical feature. Candidate baselines (Logistic Regression, Random Forest, and XGBoost) were benchmarked under walk-forward validation; **Random Forest** was selected by median validation PR-AUC under the current epidemic-threshold label (Decision 025 / M2-005). Earlier interim selection of XGBoost applied to a superseded label definition and is not the current production Stage 1 model.

Stage 1 features include:

- case-trend features (lags, rolling statistics, rate of change, momentum versus rolling mean)
- lagged climate features (precipitation 2–8 weeks; temperature and humidity 1–4 weeks)
- current-week climate and fold-aware climate anomalies
- seasonal encodings and monsoon indicators
- case-anomaly lags

Unlike Module 1 Stage 1, Module 2 Stage 1 intentionally includes climate features because the task is direct outbreak-risk discrimination. Class imbalance is handled through class reweighting. Synthetic oversampling (SMOTE-family methods) was audited and not adopted as the production strategy.

Module 2 uses a Module-specific minimum training-history setting for walk-forward folds so that early folds contain enough defined labels to train. A final untouched holdout block is reserved for reporting.

#### Stage 2: probability compensation and alert outputs

Stage 2 takes Stage 1’s out-of-sample predicted probability and applies probability compensation. Three well-posed architectures were benchmarked—isotonic regression, Platt scaling, and stacked contextual XGBoost—using Brier Skill Score as the primary selection metric. **Isotonic regression** was selected as the official Stage 2 method.

From the calibrated probability, fixed absolute thresholds produce:

- a binary `alert_flag` for early-warning use
- a three-level `risk_tier` (`low` / `medium` / `high`)

These thresholds were selected for early-warning utility and are reported with empirical risk separation in the evaluation chapter. A literal residual target of the form `label − predicted_probability` was rejected as ill-posed for binary outcomes.

**Suggested Figure:**  
Figure 6.X: Module 2 implementation pipeline (shared tables → Module 2 preprocessing → epidemic-threshold labels → Random Forest → isotonic calibration → alert/risk tier).

**Suggested Table:**  
Table 6.X: Key Module 1 vs Module 2 preprocessing divergences (week-53 policy, Stage 1 climate use, Stage 2 compensation type).

**Notes for Team:**
- Interim draft’s climate-free Stage 1 + climate Stage 2 story is obsolete for production Module 2.
- Interim multi-class label as a parallel primary target should not be presented as the current production design.
- Do not present SMOTE as production.
- Exact threshold values (0.170 / 0.570) and metric tables belong mainly in Chapter 7; Chapter 6 may say they were selected by F-beta / early-warning criteria.
- Mention Decision 013 explicitly if examiners ask why Module 1 and Module 2 differ on week 53.

---

## Paste checklist for Word

- [ ] Replace interim 6.2.1, 6.2.2, 6.3.1, and 6.3.2 with the sections above
- [ ] Remove NASA POWER tables/captions; insert Open-Meteo variable table
- [ ] Leave 6.2.3 / 6.3.3 as placeholders until Module 3 is ready
- [ ] Update 6.1 introduction later so it no longer summarizes NASA POWER / CHIRPS as current M1/M2 sources
- [ ] Strip “Notes for Team” before final submission
