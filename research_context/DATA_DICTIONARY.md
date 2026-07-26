# Data Dictionary

## 1. Epidemiological Dataset

### Granularity
Weekly district-level dengue case counts.

### Columns

| Column | Description | Role |
|---|---|---|
| District | Administrative district name | Used for district-wise segmentation |
| Number_of_Cases | Weekly reported dengue case count | Target variable for Stage 1 |
| Week_Start_Date | Start date of epidemiological week | Time ordering and merging |
| Month | Calendar month | Contextual/time reference |
| Year | Calendar year | Temporal split and trend reference |
| Week | Epidemiological week number | Seasonal period and cyclic encoding |
| Week_End_Date | End date of epidemiological week | Time ordering and merging |

### Example Record

```text
District: Ampara
Number_of_Cases: 0
Week_Start_Date: 12/23/2006
Month: 12
Year: 2006
Week: 52
Week_End_Date: 12/29/2006
```

---

## 2. Meteorological Dataset

### Granularity
Daily climate records per district.

### Available Columns

| Column | Description | Suggested Weekly Aggregation |
|---|---|---|
| time | Daily date | Convert to week |
| relative_humidity_2m_mean (%) | Daily mean relative humidity | Weekly mean |
| relative_humidity_2m_max (%) | Daily maximum relative humidity | Weekly mean of daily maxima |
| relative_humidity_2m_min (%) | Daily minimum relative humidity | Weekly mean of daily minima |
| temperature_2m_max (°C) | Daily maximum temperature | Weekly mean of daily maxima |
| temperature_2m_min (°C) | Daily minimum temperature | Weekly mean of daily minima |
| apparent_temperature_mean (°C) | Daily mean apparent temperature | Optional weekly mean |
| apparent_temperature_max (°C) | Daily max apparent temperature | Optional weekly mean |
| apparent_temperature_min (°C) | Daily min apparent temperature | Optional weekly mean |
| temperature_2m_mean (°C) | Daily mean temperature | Weekly mean |
| rain_sum (mm) | Daily rainfall sum | Weekly sum |
| precipitation_sum (mm) | Daily precipitation sum | Weekly sum |
| weather_code (wmo code) | Weather condition code | Optional mode/count encoding |

---

## 3. Data Transformation Pipeline

```text
Daily Climate Data
        ↓
Weekly Aggregation
        ↓
Merge with Weekly Dengue Data
        ↓
Feature Engineering
        ↓
Stage 1: SARIMA Baseline
        ↓
Residual Extraction
        ↓
Stage 2: XGBoost Residual Compensation
        ↓
Final Hybrid Forecast
```

---

## 4. Weekly Aggregation Rules

### Rainfall / Precipitation
Use weekly sum:

```text
weekly_rainfall = sum(daily_rain_sum)
weekly_precipitation = sum(daily_precipitation_sum)
```

### Temperature
Use weekly mean:

```text
weekly_temperature_mean = mean(daily_temperature_2m_mean)
```

Recommended derived weekly temperature columns:

- weekly_temperature_mean
- weekly_temperature_max_mean
- weekly_temperature_min_mean

### Humidity
Use weekly mean:

```text
weekly_humidity_mean = mean(daily_relative_humidity_2m_mean)
```

Recommended derived weekly humidity columns:

- weekly_humidity_mean
- weekly_humidity_max_mean
- weekly_humidity_min_mean

### Dengue Cases
Already weekly, so no aggregation is needed unless duplicate district-week rows exist.

---

## 5. Final Unit of Analysis

One row represents:

```text
One District + One Epidemiological Week
```

Expected final merged table structure:

```text
District
Year
Week
Week_Start_Date
Week_End_Date
Number_of_Cases
weekly_rainfall
weekly_precipitation
weekly_temperature_mean
weekly_humidity_mean
engineered_features...
```
