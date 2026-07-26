# Feature Engineering Specification

This is a living feature specification. Update it when features are added, removed, renamed, or moved between modules.

---

# Module 1: Hybrid Time-Series Case Forecasting

## Stage 1: SARIMA Baseline

### Target

```text
Number_of_Cases
```

### Inputs

Only the historical weekly dengue case count series per district.

### Excluded from Stage 1

- Rainfall
- Temperature
- Humidity
- Climate anomalies
- Population density
- Spatial variables

### Reason
Stage 1 must remain pure so that residuals can preserve unexplained climate-driven and nonlinear signals for Stage 2.

---

# Module 1 Stage 2: XGBoost Residual Compensation

## Target

```text
residual = actual_cases - sarima_prediction
```

Stage 2 predicts the residual, not the raw case count.

---

## Feature Group 1: Case-Trend Features

```text
cases_lag_1
cases_lag_2
cases_lag_3
cases_lag_4
rolling_mean_cases_4w
rolling_std_cases_4w
rate_of_change
```

Purpose:
Capture short-term momentum, volatility, and acceleration that SARIMA may underrepresent during nonlinear outbreak growth.

---

## Feature Group 2: Lagged Climate Features

### Rainfall Lags

```text
rainfall_lag_2
rainfall_lag_3
rainfall_lag_4
rainfall_lag_5
rainfall_lag_6
rainfall_lag_7
rainfall_lag_8
```

### Temperature Lags

```text
temperature_lag_1
temperature_lag_2
temperature_lag_3
temperature_lag_4
```

### Humidity Lags

```text
humidity_lag_1
humidity_lag_2
humidity_lag_3
humidity_lag_4
```

---

## Feature Group 3: Climate Anomaly Features

```text
rainfall_anomaly
temperature_anomaly
humidity_anomaly
```

Formula:

```text
anomaly = current_week_value - long_term_mean_for_same_district_and_week
```

Important:
Calculate long-term means using training data only to avoid leakage.

---

## Feature Group 4: Seasonal / Contextual Indicators

```text
sin_week
cos_week
monsoon_indicator_SW
monsoon_indicator_NE
```

Definitions:

```text
sin_week = sin(2π × Week / 52)
cos_week = cos(2π × Week / 52)
monsoon_indicator_SW = 1 for weeks 20-38, else 0
monsoon_indicator_NE = 1 for weeks 44-52 or 1-8, else 0
```

---

## Feature Group 5: Residual-Specific Features

```text
sarima_prediction
residual_lag_1
residual_lag_2
```

Purpose:
Help the compensation model learn systematic baseline error behavior.

---

## Feature Group 6: Optional / Novelty Features

```text
fogging_indicator
rainfall_temperature_interaction
```

Use only if data quality and availability support them.

---

# Module 2: Outbreak Risk Classification Feature Direction

Detailed specification should be maintained inside:

```text
module_2_classification/MODULE_CONTEXT.md
```

Current expected feature categories:

- Lagged case counts
- Rolling case trends
- Outbreak labels
- Baseline outbreak probability
- Climate anomalies
- Residual/probability-error lags
- Seasonal indicators

---

# Module 3: Spatial Hotspot Feature Direction

Detailed specification should be maintained inside:

```text
module_3_spatial/MODULE_CONTEXT.md
```

Current expected feature categories:

- District-level case intensity
- KDE baseline risk estimate
- Moran's I / spatial autocorrelation outputs
- Rainfall raster-derived features
- Elevation
- Population density
- Spatial residuals
- Environmental correction features

---

# Feature Change Log

Record major feature changes here or in `CHANGELOG.md`.

| Date | Module | Feature Change | Reason | Status |
|---|---|---|---|---|
| 2026-07-26 | Module 1 | Initial Stage 2 feature groups defined | Based on residual compensation logic | Accepted |
