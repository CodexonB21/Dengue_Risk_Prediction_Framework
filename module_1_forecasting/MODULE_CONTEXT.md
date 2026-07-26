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
7. **Zero-inflation risk (new, 2026-07-26):** Most weeks report zero cases across many districts. Need to compute per-district zero-week % and assess whether SARIMA remains an appropriate Stage 1 baseline for very sparse districts, or whether a simpler baseline (e.g., week-of-year historical mean, monthly aggregation) is more defensible there. This is a potential refinement to Decision 002 ("one SARIMA per district"), not yet resolved.
8. Log transform for SARIMA should use `log1p`, not plain `log`, given zero-valued weeks — both transformed and untransformed SARIMA should be compared empirically.

---

## Resolved Data Questions (2026-07-26)

- Data range confirmed: 2007–2026 per district (weekly case + daily climate), sufficient for SARIMA m=52 seasonality.
- Epi-week definition confirmed: Sri Lanka MoH epidemiological week standard (scraped directly from source), not ISO calendar week.
- District names confirmed consistent across case and climate datasets — no merge-key risk.
- Population data available: census years 2001, 2012, 2024 — see Decision 006 for interpolation/reporting-layer policy. **Not yet placed in the repo** (`data/raw/` has no population file as of this writing).
- Climate data confirmed single-point-per-district (Open-Meteo constraint) — documented as a limitation in `DATA_DICTIONARY.md`.
- See `RESEARCH_DECISIONS.md` Decisions 006–012 for the resulting policy decisions (population normalization, week-53 merge, `weather_code` exclusion, walk-forward validation, no-leakage rule, missing-week imputation, Kalmunai merge).

## Raw Data Audit Findings (2026-07-26, post-cleanup)

A full audit (`scripts/data_audit_module1.py`) was run against the actual placed raw files and, after a joint iterative cleanup with the team, confirmed:

- **26 → 25 modeling districts**: `Kalmunai` (real 19-year series, no weather station) merged into `Ampara` per Decision 012. Two district-name typos (`Moneragala`, `Puttlam`) were also found and corrected to `Monaragala`/`Puttalam`.
- **Zero duplicate `(District, Year, Week)` rows** after resolving 5 week-boundary collisions (2010, 2012/2013, 2014, 2022/2023) — see `RESEARCH_DECISIONS.md` and `CHANGELOG.md` for details.
- **Remaining real (non-error) missing weeks**: `Ampara`, `Kilinochchi`, `Mullaitivu` (1 week each), plus 3 weeks from the merged `Kalmunai` series. These go through the Decision 011 imputation policy.
- **Confirmed 53-week years**: 2009, 2016, 2019, 2021.
- **Climate source**: use `data/raw/weather/*.csv` (25 per-district files, flat, no subfolders). Each file has all 13 columns including humidity. The formerly separate `Humidity/` subfolder was confirmed fully redundant and has been deleted; `Weather (Except Humidity)/` was flattened into `data/raw/weather/` directly.
- **Corrected zero-inflation understanding**: pooled 13.7%, but concentrated in `Mullaitivu` (52.8%), `Kilinochchi` (47.7%), `Mannar` (40.4%), `Ampara` (32.9%), `Vavuniya` (32.3%). High-incidence districts (`Colombo`, `Kandy`, `Gampaha`, `Kegalle`, `Kurunegala`) have near-zero zero-weeks. The SARIMA-appropriateness question below applies mainly to the five sparse districts, not universally.

---

## Evaluation Metrics

- RMSE
- MAE
- sMAPE (preferred over MAPE due to frequent zero-case weeks)
- MASE (scale-free, more robust than sMAPE under zero-inflation)
- Residual variance reduction
- Diebold-Mariano test, if applicable

---

## Implementation Plan (2026-07-26)

Full technical detail lives in `research_context/PIPELINE_ARCHITECTURE_PLAN.md`. Summary:

1. **Prerequisite:** fix `src/config.py` placeholders (real 25-district list, correct monsoon weeks: SW = weeks 20-38, NE = weeks 44-52/1-8).
2. **Shared layer** (`src/preprocessing/shared.py`, module-agnostic, feeds Module 2/3 too): Kalmunai→Ampara merge, master epi-week calendar, climate aggregation (all 13 columns retained), population interpolation. Writes to `data/processed/shared/`.
3. **Module 1 preprocessing** (`src/preprocessing/module1_preprocessing.py`): week-53 merge (Decision 007), missing-week imputation with `is_imputed` flag (Decision 011), merge in climate + population, compute `cases_per_100k`. Writes to `data/processed/module1/weekly_modeling_table.csv`.
4. **Validation harness** (`src/module1_forecasting/validation.py`, new file): walk-forward fold generator enforcing the no-leakage rule (Decision 010).
5. **Feature engineering** (`src/module1_forecasting/feature_engineering.py`, new file): builds Stage 2 features per `FEATURE_ENGINEERING_SPEC.md`, distinguishing fold-agnostic features (lags, rolling stats — safe to compute globally) from fold-aware features (climate anomalies — must be recomputed per walk-forward fold to avoid leakage). Excludes `weather_code` here (Decision 008). Writes to `data/features/module1/`.
6. **Stage 1/2 modeling**: `baseline_sarima.py` → `compensation_model.py` → `combine.py` → `evaluate.py` (excludes `is_imputed == True` rows from scoring), orchestrated by `main.py`.

## Validation Strategy (Proposed, Decision 009/010)

- Final ~2 years (104 weeks) per district held out untouched until final reporting.
- Expanding-window walk-forward validation (annual folds) on remaining history for SARIMA order selection and XGBoost hyperparameter tuning.
- Stage 2 must always train on out-of-sample SARIMA residuals (refit per fold) — never in-sample fitted residuals, to avoid inflating apparent compensation benefit.
- Report per-district metrics plus a median-across-districts aggregate (avoids high-incidence districts like Colombo/Gampaha dominating the aggregate).

---

## Documentation Rule

Update this file when Module 1 architecture, features, decisions, or evaluation method changes.
