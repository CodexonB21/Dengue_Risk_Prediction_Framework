# Feature Engineering Specification

## Overview
This document defines the feature engineering logic for Module 1: Hybrid Time-Series Case Forecasting.

The module follows a two-stage residual compensation structure:

1. Stage 1: SARIMA baseline model
2. Stage 2: XGBoost residual compensation model

---

# Stage 1: SARIMA Baseline

## Purpose
Stage 1 is deliberately kept pure and climate-free.

SARIMA should learn only from the historical dengue case count series so that remaining residuals can preserve climate-driven signals for Stage 2.

---

## Input Features

### Weekly Dengue Case Count Series

```text
Number_of_Cases
```

This is the only modeling input for SARIMA.

SARIMA learns:

- Trend
- Seasonality
- Autocorrelation
- Annual/bimodal dengue behavior

---

## District Identifier

```text
District
```

Used only for segmentation.

SARIMA is fitted separately for each district.

Reason:

- Colombo and Mullaitivu can have structurally different dengue dynamics.
- One pooled national SARIMA may hide or fabricate district-specific residual patterns.

---

## Date / Week Index

```text
Week_Start_Date
Year
Week
```

Used to order the series and define seasonality.

Not used as an external predictor.

---

## Seasonal Period

```text
s = 52
```

Because the data is weekly and dengue has annual seasonal behavior.

---

## Stage 1 Output

```text
y_hat_sarima
```

SARIMA baseline prediction.

---

## Residual Definition

```text
e_t = actual_cases - y_hat_sarima
```

This residual becomes the target for Stage 2.

---

# Stage 2: XGBoost Residual Compensation Model

## Target Variable

```text
e_t = actual_cases - y_hat_sarima
```

Stage 2 predicts the residual, not the raw dengue case count.

---

# Feature Category 1: Epidemiological / Case-Trend Features

## cases_lag_1 to cases_lag_4
Captures short-term case momentum.

```text
cases_lag_1
cases_lag_2
cases_lag_3
cases_lag_4
```

## rolling_mean_cases_4w
Smoothed recent case intensity.

```text
rolling_mean_cases_4w
```

## rolling_std_cases_4w
Recent volatility in case counts.

```text
rolling_std_cases_4w
```

## rate_of_change
Week-over-week percentage change.

```text
rate_of_change = (cases_t - cases_t_minus_1) / cases_t_minus_1
```

Use safe handling when previous week has zero cases.

---

# Feature Category 2: Lagged Raw Climate Features

## Rainfall Lags
Rainfall has delayed dengue effects due to mosquito breeding, viral incubation, and reporting delay.

```text
rainfall_lag_2
rainfall_lag_3
rainfall_lag_4
rainfall_lag_5
rainfall_lag_6
rainfall_lag_7
rainfall_lag_8
```

## Temperature Lags
Temperature effects may appear faster.

```text
temperature_lag_1
temperature_lag_2
temperature_lag_3
temperature_lag_4
```

## Humidity Lags
Humidity affects mosquito survival and breeding suitability.

```text
humidity_lag_1
humidity_lag_2
humidity_lag_3
humidity_lag_4
```

---

# Feature Category 3: Climate Anomaly Features

Climate anomalies measure deviation from the expected district-week normal.

## Anomaly Formula

```text
anomaly = weekly_value - district_week_long_term_mean
```

The long-term mean should be computed separately for each:

```text
District + Week
```

using training-period data only.

---

## rainfall_anomaly
Captures unusually wet or dry weeks relative to the district's normal conditions for that week of the year.

```text
rainfall_anomaly
```

## temperature_anomaly
Captures unusually hot or cool weeks.

```text
temperature_anomaly
```

## humidity_anomaly
Captures unusually humid or dry weeks.

```text
humidity_anomaly
```

---

# Feature Category 4: Seasonal / Contextual Indicators

## Cyclical Week Encoding
Avoids artificial discontinuity between week 52 and week 1.

```text
sin_week = sin(2π × Week / 52)
cos_week = cos(2π × Week / 52)
```

## Southwest Monsoon Indicator

```text
monsoon_indicator_SW = 1 if Week is between 20 and 38 else 0
```

## Northeast Monsoon Indicator

```text
monsoon_indicator_NE = 1 if Week is between 44 and 52 or Week is between 1 and 8 else 0
```

---

# Feature Category 5: Hybrid / Residual-Specific Features

## SARIMA Prediction

```text
sarima_prediction
```

This allows XGBoost to learn where SARIMA tends to be systematically wrong.

## Residual Lags

```text
residual_lag_1
residual_lag_2
```

These features allow the compensation model to learn whether recent correction errors are autocorrelated.

---

# Feature Category 6: Optional Novelty-Strengthening Features

## fogging_indicator
Binary indicator for major fogging/intervention periods if data becomes available.

```text
fogging_indicator
```

This is a novelty-enhancing feature because intervention data is rarely included in reviewed dengue forecasting papers.

## Rainfall × Temperature Interaction

```text
rainfall_temperature_interaction = rainfall_lag_k × temperature_lag_j
```

XGBoost can learn nonlinear interactions automatically, but explicit interaction features may help if the dataset is limited or trees are shallow.

---

# Deliberately Excluded Features

## Raw absolute climate values without lag/anomaly transformation
Reason:
They may reintroduce seasonal climate patterns already captured indirectly by SARIMA.

## Population density / demographic features
Reason:
These are more appropriate for Module 3: Spatial Hotspot Detection.

They are mostly static and may blur the boundaries of Module 1.

---

# Summary Table

| Category | Features | Stage |
|---|---|---|
| Raw case count | Number_of_Cases | Stage 1 |
| Lagged case/trend features | cases_lag_1 to cases_lag_4, rolling mean, rolling std, rate of change | Stage 2 |
| Lagged climate | rainfall lags, temperature lags, humidity lags | Stage 2 |
| Climate anomalies | rainfall_anomaly, temperature_anomaly, humidity_anomaly | Stage 2 |
| Seasonal indicators | sin_week, cos_week, SW monsoon, NE monsoon | Stage 2 |
| Residual-specific | sarima_prediction, residual_lag_1, residual_lag_2 | Stage 2 |
| Optional novelty | fogging_indicator, rainfall-temperature interaction | Stage 2 |
