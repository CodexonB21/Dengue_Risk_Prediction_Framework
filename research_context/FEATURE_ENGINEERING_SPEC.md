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

**Fold-aware computation requirement (added 2026-07-26):** given the walk-forward validation scheme (Decision 009), this cannot be computed once globally — the "long-term mean" must be recomputed separately inside each walk-forward fold, using only that fold's training window. Computing it once over the full history would leak future climate norms into early training folds. Contrast with Feature Groups 1 and 2 (case lags, climate lags), which are pure shifts of already-observed values and are safe to compute globally regardless of split. See `research_context/PIPELINE_ARCHITECTURE_PLAN.md` for the Module 1 feature engineering script's handling of this distinction.

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

### 53-Week Year Handling

Sri Lanka MoH epi-week years occasionally contain 53 weeks. Per Decision 007 (`RESEARCH_DECISIONS.md`), week 53 is merged into week 52 (cases summed, climate averaged) before computing the above cyclic features, so `Week` is always in `[1, 52]` and the seasonal period stays fixed for SARIMA.

---

## Feature Group 5: Residual-Specific Features

```text
sarima_prediction
residual_lag_1
residual_lag_2
```

Purpose:
Help the compensation model learn systematic baseline error behavior.

**Leakage-safe construction (implemented 2026-07-27, Decision 015):**
`residual_lag_1/2` are built by reindexing each district's out-of-sample
residual onto the FULL weekly calendar (not just the sparse validation +
holdout rows) before taking `shift(1)/shift(2)`. This matters because of a
genuine ~26-week gap per district between the last walk-forward fold's
validation window and the holdout block's start (discovered during
implementation, not anticipated in the original spec) — see Decision 015 for
the full explanation. `NaN`s at each district's series start and across this
gap are left as-is for XGBoost's native missing-value handling, not
fabricated.

---

## Feature Group 5b: Pooled-Model Support Feature (added 2026-07-27, Stage 2 implementation)

```text
District
```

A categorical feature, one-hot/native-categorical-encoded via XGBoost's
`enable_categorical=True`. This is a deliberate, documented extension beyond
the original Feature Group list above, required by the Stage 2 architecture
decision (Decision 014) to train a single **pooled** model across all 25
districts rather than 25 independent per-district models — without it, the
pooled model would have no way to distinguish district-specific baseline
error behavior at all.

---

## Feature Group 6: Optional / Novelty Features

```text
fogging_indicator
rainfall_temperature_interaction
```

Use only if data quality and availability support them.

---

## Excluded Feature: `weather_code`

Per Decision 008 (`RESEARCH_DECISIONS.md`), the categorical `weather_code` (WMO code) is **excluded** from Module 1 Stage 2 features by default. It is largely redundant with the continuous rainfall/temperature/humidity variables already used, which are more physically precise for dengue transmission drivers. May be revisited as an ablation-study candidate (e.g., a derived `thunderstorm_day_count`) if time permits.

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
| 2026-07-26 | Module 1 | `weather_code` excluded from feature set | Redundant with continuous climate variables | Proposed (Decision 008) |
| 2026-07-26 | Module 1 | `sin_week`/`cos_week` require week-53 merge preprocessing | Keep SARIMA seasonal period fixed at m=52 | Proposed (Decision 007) |
| 2026-07-27 | Module 1 | Rainfall Groups 2-3 source column changed `rain_sum (mm)` -> `precipitation_sum (mm)` | `precipitation_sum` includes convective showers, more complete for Sri Lanka's monsoon pattern | Accepted (Decision 008) |
| 2026-07-27 | Module 1 | `District` added as a categorical feature (new Group 5b) | Required to support the Stage 2 pooled-model architecture | Accepted (Decision 014) |
| 2026-07-27 | Module 1 | `residual_lag_1/2` construction specified as full-calendar reindex + shift, not a naive concatenated-rows shift | A real ~26-week per-district gap between the last walk-forward fold and the holdout block would otherwise leak a stale value | Accepted (Decision 015) |
