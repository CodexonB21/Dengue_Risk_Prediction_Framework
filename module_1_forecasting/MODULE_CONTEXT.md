# Module 1 Context: Hybrid Time-Series Case Forecasting

## Owner
Bandara H.R.B.G.M.

## Purpose
Predict weekly dengue case counts using a two-stage residual compensation model.

---

## Current Architecture

```text
Stage 1: SARIMA baseline forecasting model
Stage 2: XGBoost residual compensation model
```

---

## Stage 1

### Model
SARIMA

### Input
Weekly dengue case count series per district.

### Excluded
Climate variables are excluded from Stage 1.

### Reason
Stage 1 should model normal temporal structure only. Climate-driven deviations should remain in residuals for Stage 2.

---

## Stage 2

### Model
XGBoost regressor, subject to benchmarking.

### Target

```text
residual = actual_cases - sarima_prediction
```

### Feature Groups

- Case lags: `cases_lag_1` to `cases_lag_4`
- Rolling case features: 4-week rolling mean and standard deviation
- Rate of change
- Rainfall lags: 2 to 8 weeks
- Temperature lags: 1 to 4 weeks
- Humidity lags: 1 to 4 weeks
- Climate anomalies
- Seasonal cyclic features
- Monsoon indicators
- SARIMA prediction
- Residual lags

---

## Current Open Questions

1. Which SARIMA orders perform best per district?
2. Should STL + SARIMA be tested as an alternative baseline?
3. Are residuals autocorrelated enough to justify residual_lag features?
4. Which rainfall lag window gives best performance?
5. Should `rain_sum` or `precipitation_sum` be preferred?
6. How much improvement is required to claim compensation benefit?

---

## Evaluation Metrics

- RMSE
- MAE
- MAPE
- sMAPE
- Residual variance reduction
- Diebold-Mariano test, if applicable

---

## Documentation Rule

Update this file when Module 1 architecture, features, decisions, or evaluation method changes.
