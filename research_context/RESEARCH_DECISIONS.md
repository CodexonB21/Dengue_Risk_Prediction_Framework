# Research Decisions

This document records the major design decisions behind the residual compensation framework for Module 1.

---

## Decision 1: Why No Climate Variables in SARIMA?

Stage 1 is intentionally climate-free.

If climate variables are added into SARIMA or SARIMAX at Stage 1, the baseline model may already absorb part of the climate signal.

That would weaken the residual and reduce the meaningful signal available for Stage 2.

Therefore, Stage 1 uses only historical weekly dengue case counts.

The goal is to allow residuals to preserve information related to:

- Rainfall anomalies
- Temperature anomalies
- Humidity anomalies
- Monsoon interactions
- Sudden nonlinear outbreaks

---

## Decision 2: Why Not Use SARIMAX?

SARIMAX is a valid forecasting model, but it does not align with the main novelty of this research.

The novelty is not simply adding external climate regressors.

The novelty is:

```text
Baseline Forecast + Residual Error Correction
```

SARIMAX directly models climate covariates inside the first-stage statistical model.

This project instead separates responsibilities:

- SARIMA captures predictable temporal structure.
- XGBoost learns what SARIMA could not explain.

This makes the residual compensation logic clearer and easier to defend.

---

## Decision 3: Why Fit One SARIMA Model Per District?

Dengue dynamics differ across Sri Lankan districts.

For example:

- Colombo has high urban density and large case counts.
- Mullaitivu may have lower baseline case numbers and different seasonal behavior.

A pooled national SARIMA model may:

- Hide district-specific seasonality
- Fabricate patterns that do not exist locally
- Cause misleading residuals

Therefore, SARIMA is fitted separately for each district.

---

## Decision 4: Why Use Climate Anomalies Instead of Only Raw Climate?

Raw rainfall, temperature, and humidity already contain seasonal patterns.

SARIMA captures dengue seasonality through the historical case series.

Therefore, the compensation model should focus on what is unusual, not what is normally seasonal.

Climate anomalies capture:

```text
This week is wetter/hotter/more humid than usual for this district and week of year.
```

This is exactly the kind of signal SARIMA cannot directly observe.

---

## Decision 5: Why Are Seasonal Indicators Used Again in Stage 2?

SARIMA captures average seasonal behavior.

However, XGBoost uses seasonal indicators differently.

Stage 2 needs seasonal indicators to learn conditional interactions such as:

```text
Rainfall anomaly matters more during the southwest monsoon than during inter-monsoon weeks.
```

SARIMA seasonal terms cannot express this type of nonlinear conditional relationship.

XGBoost can.

---

## Decision 6: Why Use XGBoost for Residual Compensation?

XGBoost is suitable because it can model:

- Nonlinear relationships
- Feature interactions
- Threshold effects
- Climate-driven deviations
- Lagged response patterns

It also works well with tabular engineered features and provides feature importance and SHAP-based interpretability.

---

## Decision 7: What Happens If Residuals Are Random?

If residual diagnostics show that residuals are completely random, then Stage 2 will not add much predictive value.

This should be tested using:

- Residual ACF plots
- Ljung-Box test
- Residual variance comparison
- Performance comparison between SARIMA and hybrid model

If residuals are random, the conclusion is:

```text
SARIMA has already captured most learnable temporal structure, and residual compensation is not beneficial for that district/time period.
```

This is still a valid research finding.

---

## Decision 8: Why Use Trend Features in XGBoost?

XGBoost does not understand temporal order by itself.

Therefore, temporal behavior must be represented using tabular features such as:

- Lagged cases
- Rolling mean
- Rolling standard deviation
- Rate of change
- Residual lags

These features convert time-series behavior into machine-learning-readable variables.

---

## Decision 9: Why Keep Module 1 Separate From Spatial Features?

Module 1 focuses on temporal forecasting.

Population density, elevation, urbanization, and fine-scale spatial factors belong mainly to Module 3.

Including them in Module 1 may blur module boundaries and reduce architectural clarity.

---

## Decision 10: What Is the Main Defensible Contribution?

The main contribution is a structured residual compensation design:

```text
Stage 1: Learn normal temporal dengue behavior
Stage 2: Learn systematic errors from climate anomalies and nonlinear effects
Final: Add predicted correction back to baseline forecast
```

This is more interpretable than a black-box single-stage model and more flexible than a purely statistical model.
