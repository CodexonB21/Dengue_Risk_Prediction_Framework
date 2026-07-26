# Questions for Defense

This document contains ready-to-use explanations for supervisor, evaluator, and viva-style questions.

---

## 1. Why do you use two stages?

We use two stages to separate two different modeling responsibilities.

Stage 1 uses SARIMA to capture the normal temporal behavior of dengue cases, including trend, seasonality, and autocorrelation.

Stage 2 uses XGBoost to learn the residual errors left by SARIMA using climate and anomaly-based features.

This structure makes the model more interpretable because we can clearly explain what each stage is responsible for.

---

## 2. What happens with the compensation output?

The compensation model predicts the residual error of the SARIMA model.

The final forecast is produced by adding the predicted residual correction to the SARIMA forecast.

```text
Final Forecast = SARIMA Forecast + Predicted Residual
```

This means the second stage does not replace SARIMA. It corrects SARIMA.

---

## 3. Why specifically residual compensation?

Residual compensation is used because baseline forecasting models often leave systematic errors.

In dengue forecasting, those errors may be linked to:

- Rainfall anomalies
- Temperature anomalies
- Humidity changes
- Monsoon-related nonlinear effects
- Sudden outbreak behavior

Instead of ignoring these errors, the second-stage model learns them and adjusts the forecast.

---

## 4. Why not use only XGBoost directly on case counts?

A direct XGBoost model may capture nonlinear patterns, but it does not explicitly model time-series structure in the same way as SARIMA.

SARIMA is strong for trend, seasonality, and autocorrelation.

XGBoost is strong for nonlinear correction.

The hybrid approach combines both strengths.

---

## 5. Why not use SARIMAX?

SARIMAX uses external variables directly inside the statistical forecasting model.

However, this project focuses on residual compensation.

The purpose is to first create a pure temporal baseline and then test whether climate variables explain the remaining errors.

If climate variables are included too early, the residual may no longer contain enough climate signal for the compensation stage.

---

## 6. What if the SARIMA residuals are totally random?

If residuals are completely random, then the compensation model may not improve performance.

This would mean SARIMA has already captured the learnable structure in the data.

In that case, the result is still useful because it shows that residual compensation is not always necessary and may depend on district-specific dengue dynamics.

---

## 7. Why train SARIMA separately per district?

Dengue patterns differ by district.

A high-case district such as Colombo may have different seasonality, outbreak intensity, and climate sensitivity compared with a low-case district.

Training one pooled model risks hiding local patterns.

Therefore, one SARIMA model is fitted per district.

---

## 8. Why are climate variables excluded from Stage 1 but included in Stage 2?

Stage 1 is intended to model only the expected temporal pattern of cases.

Stage 2 is intended to explain why the baseline was wrong.

Climate variables are more useful in Stage 2 because they can explain unusual deviations from the normal temporal pattern.

---

## 9. Why use climate anomalies?

Raw climate values often follow seasonal cycles.

For example, rainfall is naturally higher during monsoon periods.

An anomaly tells us whether a week is unusually wet, hot, or humid compared with what is normal for that district and week of the year.

This makes anomalies more suitable for residual correction.

---

## 10. Why are seasonal indicators used in both stages?

SARIMA captures average seasonal behavior through its seasonal structure.

Stage 2 uses seasonal indicators to learn interactions.

For example, a rainfall anomaly may have a stronger dengue effect during monsoon weeks than during non-monsoon weeks.

This conditional relationship can be learned by XGBoost but not easily by SARIMA.

---

## 11. Why use lagged rainfall from 2 to 8 weeks?

Rainfall does not affect dengue cases immediately.

There is a delay caused by:

- Mosquito breeding
- Larval development
- Adult mosquito survival
- Viral incubation
- Human infection and reporting delay

Therefore, rainfall lags are used to capture delayed effects.

---

## 12. Why use shorter lags for temperature and humidity?

Temperature and humidity can affect mosquito survival and viral incubation more quickly than rainfall-driven breeding cycles.

Therefore, shorter lags such as 1 to 4 weeks are used.

---

## 13. Why use residual_lag_1 and residual_lag_2?

If SARIMA errors are autocorrelated, recent residuals can help predict near-future residuals.

For example, if SARIMA underestimated cases last week, it may also underestimate this week during a sustained outbreak rise.

---

## 14. Why include SARIMA prediction as a Stage 2 feature?

The SARIMA prediction helps XGBoost learn where the baseline tends to fail.

For example, SARIMA may underestimate when its own predicted value is already high or when rapid growth is occurring.

Including the prediction gives the compensation model awareness of the baseline forecast level.

---

## 15. What is the novelty of this module?

The novelty is not simply using SARIMA or XGBoost.

The novelty is the structured residual compensation design:

```text
Pure SARIMA baseline + climate-driven residual correction
```

This makes the forecasting process both interpretable and flexible.

---

## 16. How will you prove that compensation helped?

We compare:

1. SARIMA baseline forecast
2. Hybrid SARIMA + XGBoost compensated forecast

Using metrics such as:

- RMSE
- MAE
- MAPE
- sMAPE
- Residual variance reduction
- Diebold-Mariano test

If the hybrid model performs better on held-out future data, compensation is effective.

---

## 17. Why use temporal train-test split instead of random split?

Random splitting would create data leakage because future weeks may appear in training while earlier weeks appear in testing.

For forecasting, the model must be evaluated on future unseen time periods.

Therefore, a temporal holdout split or rolling-window validation should be used.

---

## 18. What is the final output of Module 1?

The final output is a weekly dengue case forecast for each district.

The forecast is produced as:

```text
Final Forecast = SARIMA Baseline Forecast + XGBoost Residual Correction
```

This output can be passed to the dashboard and also support Module 2 outbreak risk classification.
