# Project Context

## Project Title
A Residual Compensation Modeling Framework for Dengue Risk Prediction

## Research Goal
Develop a two-stage residual compensation framework that improves dengue prediction by explicitly modeling and correcting systematic prediction errors left by baseline models.

The framework contains three modules:

1. Hybrid Time-Series Forecasting
2. Hybrid Outbreak Risk Classification
3. Hybrid Spatial Hotspot Detection

The current research focus is **Module 1: Hybrid Time-Series Case Forecasting**.

---

## Core Research Hypothesis
Most dengue forecasting studies stop after generating predictions. However, forecast residuals often contain systematic information related to:

- Climate anomalies
- Monsoon effects
- Environmental changes
- Contextual factors

If these residual patterns can be learned and corrected, prediction accuracy can improve.

---

## Module 1 Architecture

### Stage 1: SARIMA Baseline Forecasting Model
SARIMA is used as the baseline model to capture:

- Trend
- Seasonality
- Autocorrelation

### Stage 2: XGBoost Residual Compensation Model
XGBoost is used to learn the residual error left by SARIMA using lagged climate, anomaly, seasonal, and residual-specific features.

### Final Prediction Formula

```text
Final Prediction = SARIMA Prediction + Predicted Residual Correction
```

or:

```text
y_hat_final = y_hat_sarima + e_hat_xgboost
```

---

## Why Two Stages?
SARIMA specializes in temporal structure:

- Trend
- Seasonality
- Autocorrelation

XGBoost specializes in nonlinear correction:

- Climate interactions
- Monsoon-related nonlinear effects
- Residual patterns
- Anomaly-driven deviations

The framework deliberately separates these responsibilities.

---

## Key Research Question
Can climate-driven residual compensation improve dengue forecasting performance compared with a standalone SARIMA model?

---

## Expected Evaluation Metrics

- RMSE
- MAE
- MAPE
- sMAPE
- Residual Variance Reduction
- Diebold-Mariano Test

---

## Geographic Scope

Sri Lanka

25 administrative districts

Forecasting is performed separately per district.

A pooled national model is deliberately avoided because dengue dynamics differ structurally across districts.

---

## Current Available Data

### Weekly Dengue Case Data

- District
- Number_of_Cases
- Week_Start_Date
- Month
- Year
- Week
- Week_End_Date

### Daily Meteorological Data Per District

- time
- relative_humidity_2m_mean (%)
- relative_humidity_2m_max (%)
- relative_humidity_2m_min (%)
- temperature_2m_max (°C)
- temperature_2m_min (°C)
- apparent_temperature_mean (°C)
- apparent_temperature_max (°C)
- apparent_temperature_min (°C)
- temperature_2m_mean (°C)
- rain_sum (mm)
- precipitation_sum (mm)
- weather_code (wmo code)
