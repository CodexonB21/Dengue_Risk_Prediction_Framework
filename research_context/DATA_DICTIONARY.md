# Data Dictionary

This document describes the currently available datasets and expected transformations.

Update this file whenever new columns, new datasets, or changed preprocessing rules are introduced.

---

# 1. Epidemiological Dataset

## Granularity
Weekly district-level dengue case counts.

## Columns

| Column | Description | Current Role |
|---|---|---|
| District | Administrative district name | Used for district-wise segmentation |
| Number_of_Cases | Weekly reported dengue case count | Target for Module 1 Stage 1 |
| Week_Start_Date | Start date of epidemiological week | Time ordering and merging |
| Month | Calendar month | Context / optional checking |
| Year | Calendar year | Temporal split and trend reference |
| Week | Epidemiological week number | Seasonal encoding and seasonal period |
| Week_End_Date | End date of epidemiological week | Time ordering and merging |

## Example

```text
District,Number_of_Cases,Week_Start_Date,Month,Year,Week,Week_End_Date
Ampara,0,12/23/2006,12,2006,52,12/29/2006
```

---

# 2. Meteorological Dataset

## Granularity
Daily per district.

## Columns

| Column | Description | Planned Weekly Aggregation |
|---|---|---|
| time | Date | Map to epidemiological week |
| relative_humidity_2m_mean (%) | Daily mean relative humidity | Weekly mean |
| relative_humidity_2m_max (%) | Daily maximum relative humidity | Weekly mean of daily max |
| relative_humidity_2m_min (%) | Daily minimum relative humidity | Weekly mean of daily min |
| temperature_2m_max (°C) | Daily maximum temperature | Weekly mean of daily max |
| temperature_2m_min (°C) | Daily minimum temperature | Weekly mean of daily min |
| apparent_temperature_mean (°C) | Daily mean apparent temperature | Optional weekly mean |
| apparent_temperature_max (°C) | Daily max apparent temperature | Optional weekly mean |
| apparent_temperature_min (°C) | Daily min apparent temperature | Optional weekly mean |
| temperature_2m_mean (°C) | Daily mean temperature | Weekly mean |
| rain_sum (mm) | Daily rain sum | Weekly sum |
| precipitation_sum (mm) | Daily precipitation sum | Weekly sum |
| weather_code (wmo code) | Categorical weather code | Optional mode/count encoding |

---

# 3. Transformation Pipeline

```text
Daily climate records
  ↓
Weekly aggregation per district
  ↓
Merge with weekly dengue case data
  ↓
Create temporal features and climate features
  ↓
Run baseline model
  ↓
Extract residual/error
  ↓
Train compensation model
```

---

# 4. Current Weekly Aggregation Rules

## Rainfall / Precipitation

```text
weekly_rainfall = sum(rain_sum)
weekly_precipitation = sum(precipitation_sum)
```

## Temperature

```text
weekly_temperature_mean = mean(temperature_2m_mean)
weekly_temperature_max_mean = mean(temperature_2m_max)
weekly_temperature_min_mean = mean(temperature_2m_min)
```

## Humidity

```text
weekly_humidity_mean = mean(relative_humidity_2m_mean)
weekly_humidity_max_mean = mean(relative_humidity_2m_max)
weekly_humidity_min_mean = mean(relative_humidity_2m_min)
```

---

# 5. Final Modeling Unit

One row should represent:

```text
District + Epidemiological Week + Year
```

---

# 6. Data Quality Notes

Record future data issues here.

| Issue | Status | Resolution |
|---|---|---|
| Date alignment between daily climate and epidemiological weeks | Open | Confirm mapping function |
| Missing dengue weeks | Open | Decide imputation method |
| Choice between rain_sum and precipitation_sum | Open | Compare definitions and consistency |
