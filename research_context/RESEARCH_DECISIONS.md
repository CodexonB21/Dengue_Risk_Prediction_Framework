# Research Decisions

This is a living decision log. Update it whenever the team accepts, rejects, or revises a research decision.

Each decision should include:

- Decision
- Reason
- Status
- Date
- Related module

---

## Decision 001: Keep Stage 1 of Module 1 Climate-Free

**Module:** Module 1 - Time-Series Forecasting  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Stage 1 uses SARIMA with weekly dengue case counts only. Climate variables are not included in Stage 1.

### Reason
The research objective is residual compensation. If climate variables are included in Stage 1, the baseline model may already absorb the climate signal, leaving weaker residuals for Stage 2.

### Implication
Climate variables should mainly enter Stage 2 as lagged climate, anomaly, and interaction features.

---

## Decision 002: Fit SARIMA Separately Per District

**Module:** Module 1 - Time-Series Forecasting  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Fit one SARIMA model per district instead of one pooled national model.

### Reason
Dengue behavior differs across districts. Pooling may hide or fabricate district-specific seasonality and residual behavior.

---

## Decision 003: Use Climate Anomalies for Residual Compensation

**Module:** Module 1 / Module 2  
**Status:** Accepted but may be refined  
**Date:** 2026-07-26

### Decision
Use climate anomaly variables such as rainfall anomaly, temperature anomaly, and humidity anomaly.

### Reason
Raw climate variables contain seasonal patterns that may overlap with seasonality already captured by baseline models. Anomalies are more aligned with residual correction because they represent unusual deviations from expected district-week conditions.

---

## Decision 004: Use Module-Specific Documentation

**Module:** All modules  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Each module should maintain its own `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md`.

### Reason
The three team members work on separate modules. Module-specific documentation prevents one module's temporary changes from polluting another module's context.

---

## Decision 005: Let Cursor Maintain Living Documentation

**Module:** All modules  
**Status:** Accepted  
**Date:** 2026-07-26

### Decision
Cursor should update documentation when major decisions, experiments, or architecture changes occur.

### Reason
The project is evolving. Static rules become outdated. The repository markdown files should act as project memory.

### Guardrail
Cursor should not silently overwrite major decisions. For major architecture changes, it should document the change in `CHANGELOG.md` and update the relevant module context.

---

## Decision 006: Population Normalization as Reporting Layer Only

**Module:** Module 1 (cross-module implication for Module 3)
**Status:** Accepted (2026-07-27 — data placed, method finalized)
**Date:** 2026-07-26 (finalized 2026-07-27)

### Decision
Use interpolated census population (2001, 2012, 2024 data points, `data/raw/population/population_by_district.csv`) to compute cases-per-100,000 as a reporting/evaluation metric alongside raw case counts. Do not change the Stage 1 SARIMA modeling target from raw `Number_of_Cases`.

### Reason
Reviewers will expect incidence normalization for cross-district comparability, but changing the modeling target would cascade into Module 2/3 label definitions and reopen Decisions 001/002. Keeping normalization additive avoids this.

### Implication
- **Method finalized:** linear interpolation between 2001↔2012 and 2012↔2024 per district (`Source_Type = "interpolated"`/`"census"`). For 2025–2026, extrapolate forward using each district's own 2012→2024 linear slope (`Source_Type = "extrapolated"`).
- **Known limitation (2026-07-27):** `Kilinochchi`, `Mullaitivu`, `Mannar` show a non-monotonic 2001→2012→2024 trend (sharp decline then recovery), consistent with civil-war-era displacement in the Vanni region ending 2009. Linear interpolation cannot recover the true wartime population path for 2007–2012, which overlaps the start of the case/climate data. Since population is reporting-layer only, this doesn't affect the modeling target, but `cases_per_100k` for these 3 districts in that period should carry an explicit caveat rather than being treated as precise. See `DATA_DICTIONARY.md` Section 3 for the numbers.
- `Kalmunai` requires no separate population handling: it is administratively part of Ampara District, so its population is already included in Ampara's census figures (consistent with Decision 012's case-count merge).

---

## Decision 007: Merge Epidemiological Week 53 into Week 52

**Module:** Module 1 **only** — explicitly not shared. See Decision 013.
**Status:** Proposed
**Date:** 2026-07-26

### Decision
In years with 53 MoH epidemiological weeks, merge week 53 into week 52 (sum cases, average climate) so every district-year has exactly 52 rows.

### Reason
SARIMA's seasonal period is fixed at m=52. A variable 52/53-week structure breaks the `sin_week`/`cos_week` cyclic features and the seasonal differencing assumption.

### Implication
Requires a preprocessing step using the master MoH epi-week calendar, applied identically to case data and climate aggregation.

---

## Decision 008: Exclude `weather_code` from Module 1 Feature Set

**Module:** Module 1 **only** — explicitly not shared. See Decision 013. The shared
climate table (`data/processed/shared/climate_weekly.csv`) retains `weather_code`;
it is dropped only at Module 1's feature-selection step, so Module 2/3 can make an
independent choice.
**Status:** Proposed
**Date:** 2026-07-26

### Decision
Exclude the categorical `weather_code` (WMO code) variable from Stage 2 features by default.

### Reason
Largely redundant with continuous rainfall/temperature/humidity variables that are more physically precise for dengue transmission mechanisms. Adds categorical encoding complexity without a clearly justified benefit.

### Implication
May be revisited as an ablation-study candidate (e.g., a derived `thunderstorm_day_count` feature) if time permits, but excluded from the initial feature set.

---

## Decision 009: Walk-Forward Validation with Held-Out Final Test Block

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-26

### Decision
Reserve the final ~2 years (104 weeks) per district as a held-out test set, untouched until final reporting. Use expanding-window walk-forward validation (annual folds) on the remaining history for SARIMA order selection and XGBoost hyperparameter tuning.

### Reason
A single static split is an unreliable performance estimate for a ~19-year series and risks the "unrealistic train/test split" guardrail.

### Implication
Requires per-district fold generation, with SARIMA refit within each fold using only data available up to that fold's cutoff.

### Implementation Note (2026-07-27)
Implemented in `src/module1_forecasting/validation.py` (14 expanding-window
annual folds per district, 3-year minimum initial training window) and
consumed unchanged by `src/module1_forecasting/baseline_sarima.py`. One
accepted, documented compromise: `auto_arima`'s ORDER search (not its
per-fold parameter fitting) runs once per district on the full pre-holdout
history rather than being re-run per fold (already benchmarked as
computationally infeasible per fold - see `module_1_forecasting/
MODULE_CONTEXT.md` "Stage 1 Implementation Status", decision 1). Every
fold's actual fitted parameters and residuals still come from a fresh
`SARIMAX.fit()` on that fold's own training window only - this compromise
touches order *selection*, not the no-leakage rule in Decision 010. The
final holdout block was forecast and scored in the same run (using the
already-finalized per-district config), consistent with "untouched until
final reporting" since nothing about the holdout numbers fed back into
order/transform selection.

---

## Decision 010: No-Leakage Rule for Stage 2 Residual Training

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-26

### Decision
Stage 2 (XGBoost) must always be trained on out-of-sample SARIMA residuals (from a SARIMA model that did not see the target period during fitting), never in-sample fitted residuals.

### Reason
In-sample residuals systematically underestimate real Stage 1 error, which would artificially inflate the apparent benefit of residual compensation — a leakage risk specific to this two-stage architecture.

### Implication
Every walk-forward fold requires its own refit SARIMA model to generate that fold's Stage 2 training residuals.

### Implementation Note (2026-07-27)
Implemented in `src/module1_forecasting/baseline_sarima.py`'s
`validate_candidate()`/`fit_and_forecast()`: every one of the 14 walk-forward
folds x 25 districts x 2 transform candidates refits a fixed-order SARIMAX
on that fold's own training window only (via `validation.py`'s
`fit_window()`, unchanged) and forecasts strictly forward - never in-sample.
Genuine out-of-sample residuals for every validation fold are written to
`data/processed/module1/sarima_stage1_predictions.csv` (`split="validation"`),
ready for Stage 2 to consume once built.

---

## Decision 011: Missing Weeks Imputed and Flagged, Not Silently Zero-Filled

**Module:** Module 1 **only** — explicitly not shared. See Decision 013. The shared
layer (`data/processed/shared/epidemiological_weekly.csv`) leaves genuine gaps as
absent rows; imputation happens only inside Module 1's own preprocessing step.
Module 2/3 must decide their own missing-week policy independently.
**Status:** Proposed
**Date:** 2026-07-26

### Decision
For weeks missing from the source case data (scrape gaps), impute the case count using a seasonal-naive method (same district, same epi-week average across other years), and add an `is_imputed` flag column. Imputed weeks are excluded from evaluation metrics (RMSE/MAE/sMAPE/MASE) and from serving as Stage 2 prediction targets.

### Reason
SARIMA requires a complete, regularly-spaced series, but silently treating missing weeks as zero cases would bias the model toward under-reporting and corrupt zero-inflation diagnostics.

### Implication
Requires an `is_imputed` indicator column in the merged dataset; downstream evaluation code must filter on it.

### Confirmed Scope (2026-07-26, corrected)
An earlier row-count-based estimate undercounted this. The verified method (checking which `(District, Year, Week)` labels are actually absent, excluding the partial boundary years 2006 and 2026) found:
- **4 weeks missing for all 25 districts simultaneously**: `2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43` (likely a nationwide source-website gap, not a per-district issue).
- `Kalmunai` has 3 additional gaps of its own (`2013 Wk52`, `2016 Wk3`, `2019 Wk23`), now folded into the Ampara merge (Decision 012).
- `Ampara` has 1 additional gap (`2014 Wk39`).
- `Kilinochchi` and `Mullaitivu` are each missing `2009 Week 53` specifically, which becomes moot once the week-53 merge (Decision 007) is applied.
- Total: 104 district-week rows requiring imputation, under 0.5% of the full dataset.

---

## Decision 012: Merge Kalmunai into Ampara

**Module:** Module 1
**Status:** Accepted
**Date:** 2026-07-26

### Decision
`Kalmunai` (a real, ~19-year case-reporting series with no matching Open-Meteo weather station) is merged into `Ampara`: case counts are summed per epi-week, and Ampara's climate series is used for the combined series.

### Reason
Kalmunai is not one of the 25 official districts with its own weather station; it sits within/near Ampara administratively. Keeping it as a 26th independent series would leave it with no climate covariates, breaking the Stage 2 feature set. Excluding it entirely would discard a real, substantial 19-year case history (~17,500 total cases, comparable in volume to Badulla).

### Implication
Module 1 models exactly the 25 official districts. The merge must happen before SARIMA fitting and before Stage 2 feature engineering. `DATA_DICTIONARY.md` and `module_1_forecasting/MODULE_CONTEXT.md` updated accordingly.

---

## Decision 013: Layered Shared vs. Module-Specific Preprocessing Architecture

**Module:** All modules
**Status:** Accepted
**Date:** 2026-07-26

### Decision
The preprocessing pipeline is split into a shared, module-agnostic layer and separate module-specific layers:

```text
data/raw/ → shared preprocessing → data/processed/shared/
          → module-specific preprocessing → data/processed/moduleN/
          → module-specific feature engineering → data/features/moduleN/
```

A transformation belongs in the shared layer only if every module would make the same choice for the same reason (e.g. fixing genuine data-entry errors, merging Kalmunai into Ampara, selecting the canonical climate source, interpolating population). A transformation that exists to satisfy one baseline model's specific assumptions belongs only in that module's own preprocessing step.

### Reason
During planning it was found that week-53 merging (Decision 007), `weather_code` exclusion (Decision 008), and missing-week imputation (Decision 011) had been implicitly treated as general-purpose fixes, when they actually exist to satisfy SARIMA-specific requirements (Module 1). Applying them at a shared layer would have silently discarded real data (a full week's worth of cases) and imposed unproven feature-selection choices on Module 2 and Module 3 before those modules' own designs were even finalized.

### Implication
- Decisions 007, 008, and 011 are re-scoped to Module 1 only (see their updated entries above).
- `src/preprocessing/shared.py` handles only: raw data corrections already applied, Kalmunai→Ampara merge, master epi-week calendar construction, canonical climate source aggregation (all 13 columns retained), and population interpolation.
- Each module's own preprocessing script owns its modeling-specific temporal/feature adjustments.
- Full technical detail lives in `research_context/PIPELINE_ARCHITECTURE_PLAN.md`.
