# Chapter 4 — Section 4.4 Module 1: Hybrid Time-Series Case Forecasting

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 4.3 Residual Compensation Strategy  
**Next topic:** 4.5 Module 2: Hybrid Outbreak Risk Classification

---

## 4.4 Module 1: Hybrid Time-Series Case Forecasting

### 4.4.1 Purpose and scope

Module 1 estimates short-horizon weekly dengue case counts for each of Sri Lanka’s 25 administrative districts. Its purpose is to quantify expected case magnitude so that early-warning interpretation is grounded in a concrete forecast of burden rather than only in qualitative risk language. Within the overall residual compensation framework, Module 1 answers the magnitude question identified in Section 4.2: how many cases are expected in the coming weeks at the district-week scale used by official surveillance.

The modelling unit is the district-week observation, consistent with Weekly Epidemiological Report reporting. The module does not attempt sub-district or fine-scale spatial forecasting, does not classify outbreak labels, and does not produce hotspot surfaces; those responsibilities belong to Modules 2 and 3. Historical weekly dengue case counts form the primary Stage 1 input, while district-level meteorological covariates such as rainfall, temperature, and humidity are reserved mainly for Stage 2 residual learning.

### 4.4.2 Stage 1 baseline (SARIMA)

Stage 1 fits a Seasonal Autoregressive Integrated Moving Average (SARIMA) model independently for each district using historical weekly case counts only. Climate covariates are deliberately excluded from Stage 1. This design choice keeps the baseline focused on trend, autocorrelation, and seasonal temporal structure, and leaves climate-driven and other nonlinear deviations in the residual for Stage 2 to model. In other words, Stage 1 is intentionally a climate-free temporal baseline rather than a climate-aware SARIMAX specification.

Where appropriate, a `log1p` transform of case counts may be selected on a per-district basis to stabilise variance, with predictions inverse-transformed back to the raw case-count scale before residual construction and evaluation. Fitting separate district models recognises that dengue dynamics differ across districts and that a single pooled national baseline would obscure district-specific temporal behaviour that later residual learning needs to correct.

### 4.4.3 Stage 2 residual compensation (XGBoost)

After Stage 1 produces forecasts that can be compared with observed cases, residuals are extracted as:

```text
residual = actual_cases - sarima_prediction
```

Stage 2 then trains an XGBoost regression model to predict these residuals. The compensation feature set includes lagged case counts, rolling case statistics, rate-of-change indicators, lagged rainfall/precipitation features, lagged temperature and humidity features, climate anomaly indicators, seasonal cyclic encodings, monsoon indicators, the SARIMA prediction itself, and lagged residual features. Reporting-delay and related nowcasting indicators may also be used where they improve residual learning without violating temporal leakage constraints.

The Stage 2 model is intended to correct structured baseline error, not to replace the SARIMA forecast. Climate information therefore enters the Module 1 pipeline primarily as an explanation of residual behaviour rather than as a direct Stage 1 covariate. The final Module 1 forecast is obtained by adding the predicted residual to the baseline prediction:

```text
final_prediction = sarima_prediction + predicted_residual
```

Figure 4.2 summarises this two-stage workflow from the SARIMA baseline through residual extraction and XGBoost compensation to the final compensated case forecast.

**[Insert Figure 4.2 here]**

**Figure 4.2:** Two-stage residual compensation workflow for Module 1 (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast).

### 4.4.4 Expected outputs and users

The primary output of Module 1 is a district-week forecast of expected dengue cases. These forecasts support early-warning interpretation and situational awareness for district-level public health analysts and planners who need quantitative estimates of case burden. The module is positioned as a research decision-support component rather than as a clinically certified or fully operational deployment system. Forecast quality is assessed under walk-forward and holdout protocols in the evaluation chapter; those numeric results are not repeated here. Compensated case forecasts may also inform complementary outbreak-risk interpretation in Module 2, especially in operational forward settings where true future case counts are not yet available.

**Figure 4.2 content to draw (required):**

```text
Historical weekly dengue cases (per district)
        ↓
Stage 1: SARIMA baseline forecast
   (cases only; no climate covariates)
        ↓
Residual extraction
   residual = actual_cases - sarima_prediction
        ↓
Stage 2: XGBoost residual prediction
   (lagged cases, climate lags/anomalies,
    seasonal indicators, residual lags, etc.)
        ↓
Final compensated forecast
   final_prediction = sarima_prediction + predicted_residual
```

Do **not** label Stage 1 as SARIMAX or place climate variables inside the SARIMA box. Climate belongs on the Stage 2 feature branch only.

**Approx. word count:** 560 words

**Notes for Team:**
- Cite Figure 4.2 in the body (done in 4.4.3) and place it immediately after that paragraph in Word.
- Exact MASE/DM-test numbers belong in Chapter 7.
- Align any existing draw.io Module 1 diagram with SARIMA → XGBoost (not RF-or-XGBoost undecided).
- Tracked in `research_context/REPORT_DIAGRAM_PLAN.md` (Figure 4.2).
