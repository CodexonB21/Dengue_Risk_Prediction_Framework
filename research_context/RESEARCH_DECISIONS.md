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

## Decision 008: Exclude `weather_code` from Module 1 Feature Set; `precipitation_sum` Chosen Over `rain_sum`

**Module:** Module 1 **only** — explicitly not shared. See Decision 013. The shared
climate table (`data/processed/shared/climate_weekly.csv`) retains `weather_code`;
it is dropped only at Module 1's feature-selection step, so Module 2/3 can make an
independent choice.
**Status:** Accepted (rainfall column resolved 2026-07-27)
**Date:** 2026-07-26 (rainfall sub-decision finalized 2026-07-27)

### Decision
Exclude the categorical `weather_code` (WMO code) variable from Stage 2 features by default. Separately: Module 1's `rainfall_lag_*`/`rainfall_anomaly` features (`FEATURE_ENGINEERING_SPEC.md` Groups 2-3) are sourced from `precipitation_sum (mm)`, not `rain_sum (mm)`.

### Reason
`weather_code`: largely redundant with continuous rainfall/temperature/humidity variables that are more physically precise for dengue transmission mechanisms. Adds categorical encoding complexity without a clearly justified benefit.

`precipitation_sum` vs `rain_sum` (Module 1 Open Question #5, resolved 2026-07-27): Open-Meteo's own documentation confirms `precipitation_sum = rain_sum + showers_sum + snowfall_sum` (liquid-equivalent). Sri Lanka's monsoon rainfall is heavily convective-shower-driven, so `rain_sum` alone risks systematically undercounting real water input relevant to mosquito-breeding habitat. `precipitation_sum` is the more complete signal for this project's purpose.

### Implication
`weather_code` may be revisited as an ablation-study candidate (e.g., a derived `thunderstorm_day_count` feature) if time permits, but excluded from the initial feature set. `feature_engineering.py`'s `RAINFALL_COLUMN` constant was changed from `"rain_sum (mm)"` to `"precipitation_sum (mm)"` and `stage2_feature_table.csv` regenerated (2026-07-27) before Stage 2 was built, so no downstream Stage 2 artifact was ever built against the provisional `rain_sum` placeholder.

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

---

## Decision 014: Stage 2 XGBoost Is a Single Pooled Model (District as a Feature), Trained with a Robust (MAE) Loss

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-27

### Decision
Stage 2's residual-compensation model is **one pooled XGBoost model per walk-forward fold** (all 25 districts trained together, `District` as a categorical feature) — not 25 independent per-district models, which would revisit Decision 002 for Stage 2 specifically. The model is trained with `objective="reg:absoluteerror"` (MAE), not the more common `reg:squarederror`.

### Reason
**Pooling:** per-district training data under this walk-forward scheme is too thin for a many-feature GBM in early folds (as few as ~52 rows for one district in fold 2); pooling gives ~1,300+ rows even in fold 2. Per-district MASE is still used for all evaluation (`combine.py`), so pooling doesn't hide district-level failure — see the Implementation Note below for a case where it initially did, and how that was caught and fixed.

**Robust loss (discovered necessary during implementation, not planned upfront):** the first full run used the standard `reg:squarederror` objective and produced a stark, suspicious result — 23/25 districts got *worse* (higher RMSE and MASE) with Stage 2 than without, including a 111-point RMSE increase for Colombo alone. Root-causing this found that Stage 1's SARIMA diverged catastrophically for `Vavuniya` in one walk-forward fold (2010, weeks 42-51): forecasts reached ~30 million against an actual mean of ~6 cases/week, producing a residual of roughly -30,000,000 for those ~10 rows. Because Stage 2 pools every district into one squared-error-loss model, this single extreme value dominated the loss function globally during training and corrupted predicted residuals for every *other* district too (e.g. Colombo's predicted residuals, which should be O(100), were being predicted at O(1,000,000) after training on the contaminated pool). Switching the objective to `reg:absoluteerror` (whose gradient is bounded at ±1 regardless of error magnitude) immediately resolved this: 24/25 districts improved on both the validation-aggregate and the (independently checked) holdout MASE.

### Implication
- This is a general robustness property required by the pooled-model architecture, not a one-off patch for this single Vavuniya fold — any future Stage 1 divergence in any single district/fold would otherwise be able to silently corrupt Stage 2's correction for every other district. Anyone extending this pipeline (e.g. adding new districts, re-running Stage 1 with different orders) should keep the robust loss rather than reverting to squared error, unless Stage 1's output is first hardened against divergent forecasts.
- Stage 1's Vavuniya divergence itself was **not** fixed (out of scope — Stage 1 is a separate, already-accepted stage) but is flagged as a genuine Stage 1 data-quality finding worth a future look; see `module_1_forecasting/MODULE_CONTEXT.md` Open Question #14.
- Fixed, conservative, regularized hyperparameters (`max_depth=3, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, min_child_weight=5`) are used for every fold — not tuned per fold. Early stopping (where enough prior-fold history exists) uses the single most recent prior fold as an internal validation slice, then refits on all available prior folds with the resulting tree count.
- Full per-district results: `module_1_forecasting/MODULE_CONTEXT.md` "Stage 2 Implementation Status".

---

## Decision 015: Leakage-Safe `residual_lag_1/2` via Full-Calendar Reindexing

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-27

### Decision
`residual_lag_1`/`residual_lag_2` (Feature Group 5) are built by reindexing each district's out-of-sample SARIMA residual onto the **full weekly calendar** (every `(Year, Week)` row, not just the sparse validation+holdout rows that actually have a residual), then taking `shift(1)`/`shift(2)` on that full-calendar series, before subsetting back down to the validation+holdout rows.

### Reason
A structural gap, not anticipated during planning, was discovered while implementing this: Stage 1's 14 walk-forward folds only cover weeks `[initial 3-year training window .. fold 14's validation end]`; there is a genuine, previously-undocumented **~26-week gap per district** between fold 14's validation end and the holdout block's start (these weeks are used as SARIMA training data for the holdout fit but were never scored out-of-sample, so they have no residual value). A naive `shift(1)` computed only over the concatenated validation+holdout rows (ignoring this gap) would have silently treated fold 14's last residual as "1 week ago" for the holdout block's first row — actually ~26 weeks stale. Reindexing onto the full calendar first makes `shift` correctly produce `NaN` across this gap (and at each district's series start, before the initial training window ends) instead of pulling in a stale value. Verified empirically: exactly 2/district rows have `residual_lag_1 == NaN` (1 from series start + 1 from the fold-14/holdout gap boundary) and exactly 4/district rows have `residual_lag_2 == NaN`, matching this explanation exactly.

### Implication
`NaN`s are left as-is (not fabricated/imputed) and handled natively by XGBoost's missing-value-aware split algorithm. This finding also means the "folds are contiguous, non-overlapping" assumption used elsewhere (e.g. pooling residuals for Ljung-Box/DM tests) is true *within* the validation block and *within* the holdout block, but there is a real temporal discontinuity *between* them that any future feature relying on adjacency across that boundary must account for.

---

## Decision 016: Stage 2 Evaluation Framework — DM Test, Residual Variance Reduction, Final Ljung-Box

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-27

### Decision
Beyond the existing RMSE/MAE/sMAPE/MASE (per-fold + median-aggregate + holdout, unchanged from Stage 1's framework), `combine.py` additionally reports, per district:
1. A **Diebold-Mariano test** (`evaluate.dm_test`, HAC/Newey-West long-run variance with a 12-lag Bartlett kernel and a Harvey-Leybourne-Newbold small-sample correction) comparing Stage-1-only vs Stage-1+Stage-2 squared-error loss, at two scopes: `validation_and_holdout` (pooled, larger sample) and `holdout_only` (stricter, genuinely-never-touched-until-now sample).
2. **Residual variance reduction**: `1 - var(final_residual) / var(stage1_residual)` on pooled non-imputed out-of-sample rows.
3. A **final Ljung-Box check** (`evaluate.ljung_box_diagnostics`, lags 26/52) on `actual - final_prediction`, mirroring Stage 1's own diagnostic, to check whether Stage 2 actually removed autocorrelated structure or merely moved it.

All three are reported **per district, honestly**, including districts where Stage 2 does not help — not only where it does.

### Reason
MASE alone answers "is the point forecast better on average" but not "is that difference statistically distinguishable from noise" (DM test), "did compensation reduce the *spread* of unexplained error, not just a point summary" (variance reduction), or "is there residual structure left to exploit" (Ljung-Box) — these three together give a fuller, more honest picture than a single scale-free accuracy metric.

### Implication
- `dm_test`/`ljung_box_diagnostics` were added to `evaluate.py` (not `combine.py` itself) so they're generic and reusable — no Stage-1/Stage-2-specific assumptions baked in.
- Result (2026-07-27 initial run, **superseded by Decision 017's fix later the same day** — see that entry for corrected numbers): 24/25 districts improve on validation-aggregate MASE (median improvement ≈43%) and on holdout MASE (median ≈29%); only `Kilinochchi` gets worse on both. DM test reaches significance (`p < 0.05`, Stage 2 better) for 12/25 districts at the larger `validation_and_holdout` scope and 4/25 at the stricter `holdout_only` scope (n=104/district) — directionally consistent but not universally significant, an honest and expected outcome at this sample size. 23/25 districts still show significant residual autocorrelation post-Stage-2 (Ljung-Box lag 26, `p < 0.05`) — Stage 2 substantially reduces error magnitude but does **not** fully whiten the residual; real structure likely remains for future work to capture. See `module_1_forecasting/MODULE_CONTEXT.md` "Stage 2 Implementation Status" for full detail.

---

## Decision 017: Stage 1 SARIMA Now Guards Against Explosive/Non-Stationary AR Roots

**Module:** Module 1
**Status:** Accepted (implemented and validated, 2026-07-27)
**Date:** 2026-07-27

### Decision
`baseline_sarima.fit_and_forecast()` now checks every fitted SARIMAX model's combined AR polynomial roots (`fitted.arroots`, which already combines regular and seasonal AR structure). If any root lies on or inside the unit circle — i.e. the fit is non-stationary/explosive despite `enforce_stationarity=False` (Decision 3 in `baseline_sarima.py`'s module docstring) having allowed the optimizer to land there — the fit is treated exactly like any other failure mode already handled by that same decision: logged, and `NaN` is recorded for that fold, rather than an unbounded-growth forecast. This directly revisits (but does not reverse) Decision 002/003's original design; it closes a gap in decision 3's robustness guarantee rather than changing order selection, transform selection, or any other part of Stage 1.

### Reason
While investigating a real-world question (whether Module 1 should be able to forecast the actual, ongoing 2026 Colombo/Gampaha outbreak — see `module_1_forecasting/MODULE_CONTEXT.md` Open Question #14), the `Vavuniya` fold-1 (2010) divergence flagged as an open question during Stage 2 development (Decision 014) was root-caused precisely: the fold's training window fit an AR(1) coefficient of 1.266 (>1, explosive) for the fixed order `(1,0,2)` chosen from the full pre-holdout history, producing a forecast that grew geometrically to ~30 million cases/week against an actual mean of ~6/week. A full 25-district scan for the same pathology found a second, independent occurrence: `Mannar`'s 2022 fold-13 fit a seasonal AR coefficient of 1.162 (`(0,0,0)x(1,0,0,52)`), putting all 52 seasonal roots essentially on the unit circle and producing a forecast that oscillated with a growing envelope. This confirmed the issue is a **general failure mode** of `enforce_stationarity=False`, not a one-off, and was therefore fixed rather than left as a documented-but-unaddressed limitation.

### Implication
- Stage 1 (`sarima_stage1_predictions.csv`, `sarima_selected_configs.csv`, `sarima_walk_forward_metrics.csv`) and, downstream, Stage 2 and `combine.py`'s outputs were all regenerated from scratch with this fix (`main.py --force --stages stage1_sarima stage2_xgboost combine`, ~62 minutes).
- `compensation_model.py` and `combine.py` were hardened to handle the now-possible `NaN` residuals correctly: `_trainable_mask()` excludes `NaN`-target rows from all XGBoost fit/early-stopping-validation/train slices (previously only excluded `is_imputed` rows — not needed before this fix because no fold produced `NaN` residuals that fed into pooled training), and `residual_variance_reduction()` switched from `np.var` to `np.nanvar` for the same reason. `dm_test` and `ljung_box_diagnostics` already dropped `NaN`s internally and needed no change.
- **Result: a clean sweep — 25/25 districts now improve on validation-aggregate MASE with Stage 2** (up from 24/25; `Kilinochchi`'s validation-aggregate MASE flipped from worse to marginally better, 1.448 → 1.372). Median validation MASE improved from 0.967 (Stage 1) to 0.590 (Stage 1+2), a **39.0%** reduction; median holdout MASE improved from 0.622 to 0.375, a **39.7%** reduction (holdout improvement is now much closer to the validation figure than the pre-fix run's 43%/29% split, a more internally consistent result). `Vavuniya` itself went from one of the pipeline's most fragile districts to one of its best (validation MASE 0.375 → 0.286, holdout 0.417 → 0.374); `Mannar` also improved substantially on validation (0.809 → 0.612) though not on holdout (1.119 → 1.152, DM test not significant, `p=0.40`).
- **Holdout win rate is 23/25, not 25/25** — `Kilinochchi` (holdout MASE 2.154 → 2.407) and `Mannar` (1.119 → 1.152) both get marginally worse specifically on the untouched holdout block, though neither difference is statistically significant (DM test `p > 0.3` for both). This is reported honestly rather than only citing the validation-aggregate headline number.
- The seasonal-vs-non-seasonal finding from Open Question #12 holds directionally with the corrected numbers: non-seasonal districts (18/25) show a larger median improvement (44.9% validation / 39.1% holdout) than seasonal districts (7/25: 31.9% validation / 26.2% holdout) — consistent with, though not identical in magnitude to, the original 43.2%/37.2% vs 28.5%/24.3% figures reported before this fix.
- This does **not** fully answer whether Module 1 can predict the real, current 2026 outbreak — that investigation surfaced a separate, larger, and still-open finding: the shared climate data pipeline has not been refreshed past 2026 week 21, while case data extends to week 25, leaving Stage 2 with zero climate signal for the exact weeks (22-25) containing the outbreak's acute spike. See Open Question #14's update for the full analysis and evidence.

---

## Decision 019: Module 2 Outbreak Label — Fold-Aware Epidemic-Threshold Method, Built Independently of Module 1

**Module:** Module 2
**Status:** Accepted (kickoff decision; `k` explicitly flagged as tunable pending the empirical class-balance audit)
**Date:** 2026-07-28

### Decision
Module 2's Stage 1 classification target is defined as a binary **epidemic threshold** label, not the previously-unresolved fixed count in `src/config.py`'s `OUTBREAK_THRESHOLD` placeholder (which this decision retires):

```text
outbreak(District, Year, Week) = 1 if Number_of_Cases > historical_mean + k * historical_SD
                                = 0 otherwise
```

where `historical_mean`/`historical_SD` are computed **per `(District, Week)`**, using only that district-week's case counts from **strictly earlier years** (an expanding window, never the full series) — this is a WHO/CDC-style statistical epidemic threshold, not an arbitrary global cutoff.

`k = 2` is adopted as a literature-standard starting point (a common epidemic-threshold multiplier), but is explicitly **not final** — it is pending confirmation against `scripts/data_audit_module2.py`'s empirical class-balance audit across candidate values (e.g. 1.5, 2, 2.5) before being locked in for Stage 1 training. A minimum history depth of 3 strictly-prior years is required before a `(District, Week)` can receive a defined label (mirroring `validation.py`'s `DEFAULT_MIN_TRAIN_YEARS`); rows without enough prior history have an undefined label and must be excluded from training/scoring, not defaulted to 0.

**`k` finalized as `k = 2` (2026-07-28, audit run against `data/processed/shared/epidemiological_weekly.csv`, 25,348 rows).** No district was degenerate (outside a [2%, 40%] outbreak-rate sanity band) at `k ∈ {1.5, 2.0, 2.5}`. At `k=2`: 84.3% of rows receive a defined label (15.7% undefined for insufficient — under-3-years — history, concentrated in each district's earliest years); pooled outbreak rate among defined labels is 18.4%, ranging from `Anuradhapura` (12.6%) to `Galle` (25.2%) per district. `k=2` is chosen over `1.5` (pooled 22.7%, more weeks flagged) and `2.5` (pooled 15.5%, tighter but not meaningfully different in shape) as a reasonable middle default; the choice among these three is not highly sensitive per the per-district ordering being nearly identical at all three `k` values. Full per-district, per-`k` numbers: `outputs/metrics/module2/label_balance_audit.csv`.

**Methodological caveat, flagged rather than silently accepted:** an 18-25%-of-weeks "outbreak" rate is considerably higher than what WHO/CDC-style epidemic alerting typically intends (often single-digit % of weeks) — this single-week `mean + k*SD` threshold is likely flagging much of each district's normal seasonal peak (monsoon-driven case increases), not only genuinely anomalous spikes above that seasonal pattern. This is an accepted starting point for Module 2's kickoff, not a validated final label definition — see Module 2 Open Question #8 (new) for the follow-up needed (e.g. requiring the threshold to be exceeded for >=2 consecutive weeks before labeling an "outbreak", matching how WHO epidemic alerts are typically operationalized, or detrending/deseasonalizing before computing the anomaly).

Separately: Module 2's Stage 1 will be built **independently of Module 1** for now — it does not consume Module 1's SARIMA/XGBoost forecast output as an input feature. This is a deliberate sequencing choice, not a rejection of the idea (see Module 2 Open Question #6).

### Reason
An arbitrary fixed count threshold (the retired placeholder) is not defensible across 25 districts with wildly different baseline incidence (per `DATA_DICTIONARY.md`'s zero-inflation findings, e.g. `Colombo` at 0.5% zero-weeks vs `Mullaitivu` at 52.8%) — the same count means "business as usual" in one district and "extreme outlier" in another. A per-district-week statistical threshold is naturally district-specific (resolves Module 2 Open Question #2) and has a defensible epidemiological basis (resolves Open Question #3), unlike a single global cutoff.

Building Module 2 independently of Module 1 first avoids compounding two sets of unresolved design choices (Module 2's own label/feature/model decisions, plus however well or poorly Module 1's forecast transfers as a classification feature) into one experiment, and keeps Module 2 usable/evaluable even if Module 1's forecast integration is revisited later.

### Implication — leakage risk distinct from anything Module 1 solved
Module 1's climate-anomaly leakage guard (Decision 003) only had to protect a *feature*. Here, the **label itself** would leak future information if `historical_mean`/`historical_SD` were computed once over each district's entire series — every fold would then "know" about outbreak years that haven't happened yet relative to that fold's training cutoff. `src/module2_classification/label_definition.py` must therefore compute the threshold per walk-forward fold (or at minimum, per row, using only that row's strictly-prior years), the same structurally-hard-to-misuse design principle as `validation.py`'s `fit_window()`. This is a new construct, not a reuse of Module 1's fold-aware anomaly code (which protects a feature, not the target itself).

Because Module 2 is built independently of Module 1 (this decision's second half), its own missing-week, `weather_code`, and week-53 policies must also be decided independently per Decision 013 — tracked in `src/preprocessing/module2_preprocessing.py`'s implementation, not inherited by default.

### Documentation Updated
`module_2_classification/MODULE_CONTEXT.md` (Open Questions #1-3 resolved, #6 annotated deferred, new open question for `k` calibration), `research_context/FEATURE_ENGINEERING_SPEC.md` (Module 2 label formula made concrete), `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section expanded from placeholder), `research_context/CHANGELOG.md`.

---

## Decision 018: Forward Production Forecasting Uses Recursive Multi-Step Feature Substitution, Kept Separate From the Validated Pipeline

**Module:** Module 1
**Status:** Accepted (implemented, 2026-07-27)
**Date:** 2026-07-27

### Decision
A new, deliberately separate script (`src/module1_forecasting/forecast_future.py`) generates a genuine forward forecast for weeks beyond the last available case-count week — distinct from every existing Stage 1/2 output, all of which score against data already present in the dataset (walk-forward folds, the 104-week holdout block). Method: Stage 1 is refit on each district's entire available history and forecasts `FORECAST_HORIZON_WEEKS` (8) steps ahead in one deterministic multi-step call; Stage 2 uses the existing final production XGBoost model (`xgboost_final_model.json`, unchanged, no retraining) applied **recursively** — for the first 1-2 future weeks, `residual_lag_1/2` and case-count lags use real historical values, and for every subsequent week, the script's own prior-step predictions are fed back in as the lag inputs. A `feature_completeness_pct` diagnostic (share of non-`District` features that are non-`NaN`) is reported per output row rather than presenting every forecasted week as equally reliable. This is **not** wired into `main.py`'s idempotent orchestration and does not touch any validated Stage 1/2 artifact.

### Reason
Directly prompted by the user asking whether Module 1's testing is "done" and whether it can predict genuinely future case counts — a different question from "does the holdout MASE show improvement," which was already answered (M1-002/M1-003). Recursive multi-step substitution is the standard approach when true future values aren't available yet; the alternative (leaving lag features `NaN` from step 1 onward) would discard real, currently-available information (the actual residual/case history for the most recent 1-2 real weeks) for no benefit. Keeping this fully separate from `main.py` and clearly labeled as a different evidence standard prevents it from being mistaken for, or silently blended into, the rigorously validated holdout results.

### Implication
- New output: `data/processed/module1/future_forecast.csv` (200 rows = 25 districts x 8 weeks) plus illustrative plots for `Colombo`/`Gampaha` (`outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`).
- `feature_completeness_pct` declines from 56.2% (horizon step 1) to 43.8% (steps 5-8) across all districts — an honest, quantified confidence signal rather than an implicit one.
- For the two real-outbreak districts: `Colombo`'s forecast rises from its pre-spike ~300-500/week baseline to a ~460-470/week plateau; `Gampaha`'s rises from ~200-500/week to a ~1,360-1,370/week plateau — both substantially elevated relative to baseline but not simply repeating the single week-25 spike value, consistent with (not proof of) the model correctly discounting what may be a partly reporting-lag-driven outlier (Open Question #16).
- Does **not** close Open Question #16's climate-data-currency gap, and does **not** substitute for the still-not-built rolling 1-week-ahead re-evaluation — both remain open, higher-rigor follow-ups. This script's numbers must never be cited alongside holdout MASE/DM-test results as if equivalently validated.

---

## Decision 020: Module 2 Preprocessing Review — Week 53 Kept Unmerged; is_imputed Masking Made Consistent Across All Case-Derived Features

**Module:** Module 2
**Status:** Accepted (implemented, 2026-07-28)
**Date:** 2026-07-28

### Decision
A dedicated review of `src/preprocessing/module2_preprocessing.py`'s three Decision-013-independent choices (week 53, missing-week imputation, `weather_code`), requested before proceeding to Stage 1 modeling, produced two changes and one confirmation:

1. **Week 53 is no longer merged into week 52.** Reverses the kickoff-default implementation (Decision 019's mention of a "week-53 policy... tracked in module2_preprocessing.py"). Week 53 (2009, 2016, 2019, 2021) now passes through as its own `(District, Year, Week=53)` row.
2. **`is_imputed` rows are now masked to `NaN` before deriving `cases_lag_1-4`, `rolling_mean_cases_4w`, `rolling_std_cases_4w`, `rate_of_change`, and `momentum_vs_rolling_mean`** (`src/module2_classification/feature_engineering.py`), not just `case_anomaly_lag_1/2` as originally implemented.
3. **`weather_code` exclusion is reconfirmed** as-is (same reasoning as Module 1's Decision 008) — no change.

### Reason
1. **Week 53 merge risked contaminating the label itself, not just a feature.** Summing two real weeks' case counts into one "week 52" bucket (a) could spuriously push that bucket's case count over the epidemic threshold purely from merge arithmetic, and (b) contaminates `historical_mean`/`historical_SD` for week 52 **across every year**, not just the four merged ones, since `label_definition.py`'s expanding-window statistic is computed cross-year per `(District, Week)`. Module 1 never had this exposure because SARIMA only depends on total magnitude, not a per-week threshold-crossing semantic. Kept unmerged, week 53 will almost always have an undefined label (only 4 total occurrences, short of the 3-strictly-prior-years rule) — an honest "insufficient history" outcome, not a code defect. `sin_week`/`cos_week` require no special-casing (`sin(2*pi*53/52) = sin(2*pi*1/52)` by periodicity, i.e. week 53 naturally lands adjacent to week 1's value, matching its real calendar position); a Module-2-local `MODULE2_MONSOON_WEEKS_NE` (`= MONSOON_WEEKS_NE + [53]`) was added since week 53 falls in late December (NE monsoon) and the shared `MONSOON_WEEKS_NE` constant assumes Module 1's already-merged 52-week structure.
   - Note that a gap-free weekly series is still required for `.shift()`-based lag features to stay correctly aligned (this part of the original imputation rationale does generalize to Module 2, just via a different mechanism than SARIMA's).
2. **The `is_imputed` masking gap was a genuine inconsistency, found during this review.** `case_anomaly_lag_1/2` and the label already excluded fabricated seasonal-naive case counts from contributing to any statistic computed from them — but the plain case-trend features (`cases_lag_*`, rolling stats) did not, meaning a fabricated value could silently flow into a neighboring real week's feature. Fixed for consistency; verified post-fix that `cases_lag_1` for the week immediately following an imputed week is now `NaN` rather than the fabricated value (previously it silently absorbed it).
3. `weather_code`'s redundancy with the continuous climate variables (Module 1's original reasoning) applies equally to a classification target; no Module-2-specific reason to reconsider was found.

### Implication
- `data/processed/module2/weekly_modeling_table.csv` regenerated: 25,450 rows (up from a merged-week-53 count), 102 rows flagged `is_imputed` (was ~100), week counts are 52/year except 53 for `{2009, 2016, 2019, 2021}` (`validate_weekly_modeling_table` updated accordingly).
- `data/features/module2/stage1_feature_table.csv` regenerated with the masking fix; downstream Stage 1/2 code must be trained/evaluated against this regenerated table.
- The `k=2` label-balance audit (Decision 019) required **no rerun**: `scripts/data_audit_module2.py` already read the unmerged shared table directly and grouped by `(District, Week)`, so it was never exposed to the now-reversed week-53 merge in the first place.
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md`'s Module 2 Layer section, `module_2_classification/MODULE_CONTEXT.md`, and `research_context/FEATURE_ENGINEERING_SPEC.md` updated to describe the current (not the original kickoff-default) preprocessing behavior.

### Documentation Updated
`src/preprocessing/module2_preprocessing.py` and `src/module2_classification/feature_engineering.py` docstrings, `research_context/PIPELINE_ARCHITECTURE_PLAN.md`, `module_2_classification/MODULE_CONTEXT.md`, `research_context/CHANGELOG.md`.

---

## Decision 022: Module 2 Stage 2 Design — Three Well-Posed Calibration/Correction Architectures Benchmarked by Brier Skill Score, Not a Literal Residual Regression

**Module:** Module 2
**Status:** Accepted (implemented and run 2026-07-28 as `EXPERIMENT_LOG.md` M2-002 — Platt scaling originally selected; superseded numerically, architecture unchanged in kind, by Decision 023's Stage 1 retuning, which flipped the winner to isotonic regression — see M2-003)
**Date:** 2026-07-28

### Decision
Following a dedicated planning session (prompted by the user, no code written yet at
decision time), Module 2's Stage 2 (`compensation_model.py`) is designed as follows:

1. **Architecture — three candidates benchmarked, none a literal residual regression.**
   Module 1 Stage 2's `residual = actual - sarima_prediction` metaphor does not transfer
   cleanly to a binary target: `label - predicted_probability` for a single Bernoulli
   observation is a high-variance, low-information regression target (variance ≈
   `p(1-p)`, dominated by sampling noise), and there is no clean way to define it such
   that `predicted_probability + predicted_residual` stays inside `[0, 1]` without ad
   hoc clipping. Three numerically well-posed candidates are benchmarked instead:
   - **Isotonic regression** (pooled, feature-free) on `predicted_probability` → `label`.
   - **Platt scaling** (pooled, feature-free): logistic regression on
     `logit(predicted_probability)` — one feature, the log-odds, not raw `p` (this is
     what makes it standard Platt scaling rather than an ad hoc single-feature LR).
   - **Stacked XGBoost**: a classifier on `[predicted_probability, contextual features,
     District, probability_residual_lag_1/2]` → `label` directly. This subsumes the
     "residual/probability correction model" idea from `MODULE_CONTEXT.md`'s "Possible
     Stage 2 Models" list without the ill-posed target, and — unlike a fixed-margin
     approach — can down-weight Stage 1's raw signal if `scale_pos_weight`-based
     imbalance correction really has distorted its scale (which the calibration
     diagnostic already found evidence of).
   - Considered and explicitly deferred: an XGBoost variant with `base_margin =
     logit(predicted_probability)` (trees learn only an additive correction in logit
     space) — the most literal translation of Module 1's residual-compensation metaphor
     that stays numerically well-posed. Not built this round because the stacked model
     already covers its expected benefit and is strictly more flexible; flagged as a
     future ablation candidate, not rejected outright.
   - Selection metric: **median Brier Skill Score** (see point 4) across trainable
     folds, gated by a check (not an assumption) that PR-AUC/ROC-AUC do not regress
     relative to Stage 1's raw probability — monotonic recalibration (isotonic, Platt)
     provably cannot hurt ranking, but the stacked model in principle could.

2. **No-leakage rule, adapted from Decision 010.** Stage 2 fold *k* (for `k = 2..13`)
   trains only on the official Stage 1 model's out-of-sample `predicted_probability` +
   `label` from folds `1..k-1` — never fold *k* itself. Fold 1 has no prior
   out-of-sample data and is a documented no-op passthrough (`calibrated_probability =
   predicted_probability`, `stage2_trained=False`), mirroring Module 1 Stage 2's fold-1
   no-op exactly. This yields **12 trainable folds** (2-13), one fewer than Stage 1's 13.

3. **Pooled vs. per-district**: re-validated empirically (not assumed to inherit
   Decision 021's Stage-1 finding), using the stacked-XGBoost architecture alone as the
   arbiter — mirrors `baseline_classifier.run_pooled_vs_per_district_comparison` exactly.

4. **Evaluation**: `brier_skill_score` (`1 - brier_score / (prevalence * (1 -
   prevalence))`, skill relative to a climatology/base-rate forecast) is promoted from
   the one-off `scripts/stage1_calibration_diagnostic.py` into a first-class pure
   function in `evaluate.py` — Stage 2's primary selection metric, the same role PR-AUC
   played for Stage 1 (Decision 021). Reliability diagrams (binned predicted-probability
   vs. observed frequency, Stage-1-raw vs. Stage-2-calibrated) are added — the one
   `MODULE_CONTEXT.md` Evaluation Metrics item never implemented.

5. **Output format**: calibrated `predicted_probability` is the primary Stage 2 output
   (resolves part of the long-standing "Target Direction" ambiguity in
   `MODULE_CONTEXT.md`). A risk-level tier (low/medium/high) is a secondary, derived
   output using **fixed absolute probability thresholds**, not quantile cutoffs —
   quantile cutoffs would force a constant fraction of "high risk" weeks regardless of
   true epidemic conditions, which stops making sense once probabilities are genuinely
   calibrated (a benefit only available *after* Stage 2 fixes calibration). Exact
   threshold values are deferred to a short follow-up once Stage 2's real
   calibrated-probability distribution can be inspected, not chosen blind.

6. **Module 1 integration (Open Question #6) deferred again**, for a sharper reason than
   the original kickoff sequencing choice: Module 1 (14 folds, `MIN_TRAIN_YEARS=3`) and
   Module 2 Stage 1 (13 folds, `MIN_TRAIN_YEARS=4`) have misaligned fold boundaries, so
   merging Module 1's `final_prediction` in as a feature requires a dedicated
   fold-alignment leakage audit, not a two-line merge, and would create a live
   cross-module dependency (any future Module 1 change would silently change Module 2
   Stage 2's inputs). Planned as an **optional ablation** after Stage 2's own-feature-set
   version is built and evaluated, not abandoned.

7. **Open Question #8** (single-week vs. consecutive-week outbreak trigger) stays
   deferred, untouched by this design or its implementation.

### Reason
A literal port of Module 1's residual-compensation architecture would have produced an
ill-posed regression target for a binary label without the team noticing until
implementation — this was caught during planning, before any code was written, by
examining what "residual" actually means for a Bernoulli outcome. Benchmarking three
architectures (rather than picking one a priori) follows the same evidentiary standard
already used for Stage 1's model selection (Decision 021) and the pooled-vs-per-district
question. Deferring Module 1 integration and exact risk-tier cutoffs are both deliberate,
reasoned decisions (fold misalignment; distribution not yet known) rather than silent
omissions — both are recorded as concrete follow-ups, not closed questions.

### Implication
- New file `src/module2_classification/compensation_model.py`; new functions
  `brier_skill_score`/`reliability_curve` in `evaluate.py`; new path constants in
  `src/config.py`; new pipeline stage in `main.py`.
- New outputs (once run): `data/processed/module2/stage2_compensated_predictions.csv`,
  `outputs/metrics/module2/{stage2_compensation_metrics,
  stage2_pooled_vs_per_district_comparison}.csv`,
  `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
  `models/module2/stage2_compensation/`.
- This decision's numeric results (which architecture wins, actual BSS/PR-AUC values)
  are recorded in `EXPERIMENT_LOG.md` M2-002 (Platt scaling, pre-Stage-1-retuning) and
  superseded by M2-003 (isotonic regression, post-Decision-023 retuning).

### Documentation Updated
`module_2_classification/MODULE_CONTEXT.md` (Open Questions #5/#6 updated, Target
Direction updated, "Possible Stage 2 Models" resolved),
`research_context/FEATURE_ENGINEERING_SPEC.md` (new Stage 2 feature group),
`research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer's
`compensation_model.py` entry expanded), `research_context/CHANGELOG.md`.

---

## Decision 021: Module 2 Stage 1 Baseline Classifier — MIN_TRAIN_YEARS=4 Fix, Pooled Architecture Confirmed Empirically, XGBoost Selected

**Module:** Module 2
**Status:** Accepted (implemented and validated, 2026-07-28)
**Date:** 2026-07-28

### Decision
Implemented `src/module2_classification/baseline_classifier.py` (Stage 1), with four decisions made and confirmed before/during implementation:

1. **New `MODULE2_MIN_TRAIN_YEARS = 4`** (`src/config.py`), a Module-2-specific override of `src/module1_forecasting/validation.py`'s SARIMA-tuned `DEFAULT_MIN_TRAIN_YEARS = 3`. Verified empirically (against the real feature table, for every district) that at the SARIMA-tuned default, walk-forward fold 1's ENTIRE training window has **zero** rows with a defined label — Decision 019's label requires 3 strictly-prior years of history, which overlaps exactly with the 3-year minimum training window itself, for every district simultaneously (a calendar-driven effect, not a per-district data-thinness issue that pooling could rescue, unlike Module 1 Stage 2's analogous but differently-caused fold-1 thinness). Using `min_train_years=4` yields **13 walk-forward folds** (down from Module 1's 14), each with genuinely trainable rows (fold 1: 1,275 pooled trainable rows across 25 districts).
2. **Pooled model (District as a categorical feature) confirmed empirically, not assumed** — validated via a dedicated `run_pooled_vs_per_district_comparison()` using XGBoost alone as the arbiter (no imputation/encoding confound). Result: pooled median PR-AUC across 13 folds = **0.500**, vs. per-district median PR-AUC = **0.287** (mean 0.433) — pooled clearly and consistently outperforms per-district, most starkly in early folds where per-district training data is thinnest (e.g. fold 1: pooled 0.272 vs. per-district median 0.165). Full per-fold comparison: `outputs/metrics/module2/pooled_vs_per_district_comparison.csv`.
3. **Correction to the original NaN-handling premise**: `sklearn.ensemble.RandomForestClassifier` does **not** accept NaN natively (unlike XGBoost) — only XGBoost among the three benchmarked models has true native missing-value handling. Random Forest and Logistic Regression both use an identical `ColumnTransformer` (median-impute numeric features, one-hot encode `District` against the fixed `DISTRICTS` list; Logistic Regression additionally standard-scales), fit on each fold's training rows only.
4. **Model selection**: Logistic Regression, Random Forest, and XGBoost were benchmarked across all 13 folds with `class_weight="balanced"` (LR/RF) / per-fold `scale_pos_weight` (XGBoost) for imbalance (not SMOTE). **XGBoost selected as the official Stage 1 model** by median validation PR-AUC (0.500, vs. Random Forest 0.462 and Logistic Regression 0.437) — used consistently across all folds (not a per-fold winner). Held-out final block (last 2 years, never touched during fold-based selection): XGBoost PR-AUC 0.538, roughly consistent with the validation-aggregate figure. Top feature by gain: `case_anomaly_lag_1` (as expected — conceptually near-identical to the label one week prior, per `FEATURE_ENGINEERING_SPEC.md`'s Group M2-5 leakage note), followed by `case_anomaly_lag_2` and `rolling_mean_cases_4w`.

### Reason
1. A structural fold-1 problem was caught by direct empirical verification (not assumed to work by analogy with Module 1) before committing to a fold design — training a classifier on a window with zero informative labels would have silently produced meaningless fold-1 output.
2. Per-district models are much thinner during exactly the early folds where reliable classification matters most for demonstrating walk-forward robustness; confirming pooling empirically (rather than only citing Module 1 Stage 2's precedent) avoids assuming a Module-1-specific finding transfers unchanged to a different target type (classification, not regression) and a different, calendar-driven data-thinness cause.
3. Assuming "tree-based models handle NaN" without verifying per-library behavior would have caused a runtime failure (or silently wrong behavior) for Random Forest specifically once real is_imputed-masked NaN features reached it.
4. PR-AUC (not accuracy/F1) is the correct primary metric given the ~14-22% prevalence observed within trainable folds (lower than the unconditional 18.4% pooled rate reported in Decision 019's audit, since `MIN_TRAIN_YEARS=4` reshapes which years are ever scored) — accuracy alone would reward a majority-class classifier.

### Implication
- New config constants: `MODULE2_MIN_TRAIN_YEARS`, `MODULE2_BASELINE_PREDICTIONS_PATH`, `MODULE2_BASELINE_METRICS_PATH`, `MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH`, `MODULE2_POOLED_VS_DISTRICT_PATH`, `MODULE2_BASELINE_MODELS_DIR`, `MODULE2_BASELINE_FINAL_MODEL_PATH` (`src/config.py`).
- New files: `src/module2_classification/evaluate.py` (classification metrics: `accuracy`, `precision`, `recall`, `specificity`, `f1`, `roc_auc`, `pr_auc`, `brier_score`, `prevalence`, `confusion_counts`, all mirroring Module 1 `evaluate.py`'s masked-pure-function style), `src/module2_classification/baseline_classifier.py` (full Stage 1 pipeline), `src/module2_classification/main.py` (idempotent orchestration, mirroring `module1_forecasting/main.py`).
- Threshold-dependent secondary metrics (F1, confusion matrix) use a **fixed, explicitly-untuned 0.5 cutoff** — real threshold/calibration tuning remains deferred to Stage 2 (`compensation_model.py`), per Module 2 Open Question #5.
- Per-fold model artifacts are saved only for the official model (XGBoost) — `models/module2/baseline_classifier/fold_{1..13}.json`, `holdout.json`, `final_production_model.json`. All 3 models' per-fold and aggregate metrics remain in `outputs/metrics/module2/baseline_classifier_metrics.csv` for the permanent benchmark record.
- This does **not** resolve Module 2 Open Question #8 (single-week vs. consecutive-week outbreak trigger) — Stage 1 was built against the existing `k=2` single-week label as-is; that refinement remains a candidate follow-up.

### Documentation Updated
`module_2_classification/MODULE_CONTEXT.md` (Open Question #4 resolved; new "Stage 1 Implementation Status" section), `module_2_classification/EXPERIMENT_LOG.md` (new entry M2-001), `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section updated), `research_context/FEATURE_ENGINEERING_SPEC.md` (baseline-probability feature now available), `research_context/CHANGELOG.md`.

---

## Decision 023: Module 2 Stage 1 XGBoost Hyperparameter Tuning — Optuna Search, Holdout-Gated Adoption, Tuned Params Adopted

**Module:** Module 2
**Status:** Accepted (implemented, run, and adopted 2026-07-28)
**Date:** 2026-07-28

### Decision
After M2-002 confirmed Stage 2 fixes calibration but cannot itself improve discrimination
(a monotonic recalibration provably cannot change ranking), the team asked whether Stage 1's
own discrimination could be improved before considering a full Module 2 redesign. Rather than
touch features, label definition, or architecture, the cheapest lever — Stage 1's XGBoost
hyperparameters, fixed by hand since Decision 021 (`max_depth=4, learning_rate=0.05,
n_estimators=300, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, min_child_weight=5`) —
was tuned via Optuna:

1. **New standalone script `scripts/tune_stage1_xgboost.py`** (not wired into `main.py` — a
   one-off research script, mirroring `stage1_calibration_diagnostic.py`'s pattern), reusing
   `baseline_classifier.assemble_labeled_feature_table()`/`compute_fold_boundaries()`/
   `attach_fold_anomalies()` to rebuild the exact same 13 walk-forward folds.
2. **Search objective**: median PR-AUC across the 13 validation folds (TPE sampler, seed=42,
   60 trials), searching `max_depth [3,8]`, `learning_rate [0.01,0.3]` (log), `n_estimators
   [100,600]`, `subsample [0.5,1.0]`, `colsample_bytree [0.5,1.0]`, `reg_lambda [0.1,10]`
   (log), `min_child_weight [1,15]`, `reg_alpha [0,5]`, `gamma [0,5]`. `scale_pos_weight` is
   never searched — it stays a per-fold, leakage-safety-derived quantity (Decision 021),
   recomputed fresh from each fold's own training labels regardless of what hyperparameter
   dict is passed in (enforced in `baseline_classifier.fit_and_predict`'s new optional
   `xgb_params` override parameter).
3. **Holdout-gated adopt/reject decision, deliberately NOT gated on the search's own
   objective.** Stage 1's official model was already chosen by comparing 3 model types on
   the same 13-fold median PR-AUC it is reported against (Decision 021 — a mild, accepted
   selection bias tolerated only because the search space was 3 candidates). Running ~60
   hyperparameter trials against that *same* metric would make the resulting fold-median
   PR-AUC value optimistic almost by construction. The untouched holdout block (never seen
   during the Optuna search, exactly as it is never seen during Stage 1's own model-type
   selection) is therefore the ONLY evidence treated as an honest verdict on whether tuning
   actually helped — the search's own median-PR-AUC value is used purely to *propose* the
   candidate, never to *report* the win.
4. **Result: ADOPTED.** Holdout PR-AUC improved **0.5380 → 0.5577** (+0.0198, +3.7%
   relative) and holdout ROC-AUC improved **0.8978 → 0.9109**, under a genuinely untouched
   evaluation block. `XGB_BASE_PARAMS` in `baseline_classifier.py` updated to: `max_depth=3,
   learning_rate=0.01237, n_estimators=217, subsample=0.6565, colsample_bytree=0.5962,
   reg_lambda=1.0758, min_child_weight=10, reg_alpha=4.1197, gamma=2.4930`. Holdout Brier
   score/BSS got *worse* under the tuned params (0.0725→0.0902 Brier, -0.080→-0.345 BSS) —
   explicitly not a blocker: Stage 1 was never selected or tuned for calibration (Decision
   021), and Stage 2 recalibrates whatever raw scale Stage 1 produces (Decision 022), so a
   PR-AUC-only tuning objective correctly ignores Stage 1's own calibration.
5. **Full Stage 1 + Stage 2 rerun with `--force`** after adoption, as the plan required
   (Stage 2 trains on Stage 1's out-of-sample probabilities, so it cannot be left stale).
   XGBoost remained the selected Stage 1 model (median PR-AUC 0.532 vs. Random Forest 0.462,
   Logistic Regression 0.437); pooled architecture still confirmed over per-district (Stage 1
   aggregate pooled PR-AUC 0.532 vs. per-district median 0.355, pooled wins 12/13 folds).
   **Stage 2's official architecture changed from Platt scaling to isotonic regression** as a
   direct, unplanned consequence — see Decision 022's status note and M2-003 for the full
   before/after.

### Reason
Threshold and per-fold hyperparameter tuning were both on the table as lower-cost, more
targeted alternatives to a full Module 2 redesign after the team asked "shouldn't the final
goal be predicting outbreaks more accurately?". Hand-picked "reasonable" defaults (Decision
021) were never claimed to be optimal, only conservative and non-overfit; a holdout-gated
search is the correct way to test whether that conservatism left real PR-AUC on the table,
without repeating Decision 021's own mild selection-bias risk on a much larger search space.

### Implication
- `baseline_classifier.fit_and_predict` gained an optional `xgb_params: dict | None`
  parameter (XGBoost only; `scale_pos_weight` still always computed per-fold, never
  overridable).
- `XGB_BASE_PARAMS` permanently updated (with an inline comment citing this decision and the
  before/after holdout numbers) — this is now the production Stage 1 hyperparameter set.
- New artifacts: `scripts/tune_stage1_xgboost.py`,
  `outputs/metrics/module2/xgboost_tuning_trials.csv` (all 60 trials, audit trail),
  `outputs/metrics/module2/xgboost_tuning_holdout_comparison.csv` (the adopt/reject
  evidence).
- Every Stage 1/Stage 2 artifact that depends on `XGB_BASE_PARAMS` was regenerated:
  `data/processed/module2/{baseline_classifier_predictions,stage2_compensated_predictions}.csv`,
  `outputs/metrics/module2/{baseline_classifier_metrics,pooled_vs_per_district_comparison,
  baseline_classifier_feature_importance,stage2_compensation_metrics,
  stage2_pooled_vs_per_district_comparison}.csv`,
  `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
  `models/module2/{baseline_classifier,stage2_compensation}/*`.
- **Requires updating M2-002's superseded numeric claims** (Platt scaling, old PR-AUC/BSS
  figures) — done via a new `EXPERIMENT_LOG.md` entry M2-003, not an edit to M2-002 itself
  (the old run is a real, valid, historical result — just no longer the current production
  state).

### Documentation Updated
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-003), `research_context/
RESEARCH_DECISIONS.md` Decision 022's Status/Implication corrected to point at M2-003,
`module_2_classification/MODULE_CONTEXT.md` (Stage 1/Stage 2 Implementation Status sections
updated), `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (tuned-params note),
`research_context/CHANGELOG.md`.

---

## Decision 024: Module 2 Stage 2 Risk Thresholds — F2-Optimal Alert Threshold, F0.5-Optimal High-Confidence Tier

**Module:** Module 2
**Status:** Accepted (implemented and run 2026-07-28)
**Date:** 2026-07-28

### Decision
Completes Decision 022's deferred risk-tier item, now that Stage 2 (post-Decision-023
retuning: isotonic regression) produces a real calibrated-probability distribution to set
thresholds against:

1. **Alert threshold** (binary "should this trigger an outbreak alert?"): the cutoff that
   maximizes **F2** (recall weighted 2x over precision) — the correct choice for a public-
   health early-warning system, where a missed outbreak is costlier than an extra false
   alarm. Replaces the fixed, explicitly-untuned 0.5 cutoff used only as a Stage 1/2
   benchmarking diagnostic.
2. **High-confidence tier boundary**: the cutoff that maximizes **F0.5** (precision weighted
   2x over recall) — the correct choice for a "high confidence" label, where a false positive
   at the top tier is more costly to the system's credibility than at the alert tier. One
   consistent F-beta framework at two operating points, not two unrelated ad hoc rules.
   Constrained to be `>= alert_threshold` (clipped up if the two independently-scanned
   objectives ever disagree) so tiers stay coherently nested.
3. **Fixed absolute thresholds, not quantiles** — reaffirms Decision 022's own reasoning:
   quantile cutoffs would force a constant fraction of "high risk" weeks regardless of true
   epidemic conditions, meaningless once probabilities are genuinely calibrated.
4. **Selected on validation folds 2-13 only, holdout untouched.** The official architecture's
   rows on the validation split are the selection population — fold 1's uncalibrated
   passthrough (`architecture="none"`) is automatically excluded (it never carries the
   official architecture's rows), and the holdout split is excluded so it remains the one
   honest, never-touched check of whether the new threshold actually helps (mirrors every
   other holdout-gated decision in this project: Decisions 009, 021, 023).
5. **Result**: `alert_threshold = 0.170`, `high_confidence_threshold = 0.570`. On the
   untouched holdout block, switching from the naive 0.5 cutoff to 0.170 nearly doubles
   recall (**39.9% → 68.6%**) at the expected precision cost (70.8% → 34.7%), and the F2
   score itself improves (0.437 → 0.574) — the correct trade-off for an early-warning
   framing. Empirical tier separation is strong and monotonic: observed outbreak rate is
   **2.6% (low) → 22.0% (medium) → 76.7% (high)** on holdout (3.2% / 27.3% / 83.2% on
   validation folds 2-13) — the tiers genuinely track risk, not just an assumption from the
   threshold values chosen.

### Reason
F-beta at two asymmetric operating points is the standard, principled way to encode "which
kind of error matters more" without inventing an arbitrary rule per tier, and stays
consistent with Decision 022's earlier rejection of quantile-based cutoffs. Selecting purely
on validation folds and reserving the holdout for the final check follows the same
no-look-ahead discipline used for every other threshold/architecture choice in this project.

### Implication
- New module `src/module2_classification/risk_thresholds.py` — a permanent pipeline stage
  (`stage2_risk_thresholds` in `main.py`'s `PIPELINE_STAGES`, unlike Decision 023's one-off
  tuning script), not a research script.
- New functions in `evaluate.py`: `fbeta_score(y_true, y_pred_label, beta, mask=None)`
  (generalizes `f1`), `threshold_scan(y_true, y_prob, thresholds=..., mask=None)`.
- New config path constants: `MODULE2_RISK_TIER_PREDICTIONS_PATH`,
  `MODULE2_RISK_THRESHOLD_SCAN_PATH`, `MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH`.
- New outputs: `data/processed/module2/stage2_risk_tier_predictions.csv` (adds `alert_flag`,
  `risk_tier` columns to every row of `stage2_compensated_predictions.csv`, all
  architectures/splits, for audit), `outputs/metrics/module2/{risk_threshold_scan,
  risk_threshold_holdout_comparison}.csv`.
- A binary outbreak/non-outbreak alert flag and a 3-level risk tier are now first-class,
  reproducible Stage 2 outputs — resolves Module 2's "Target Direction" ambiguity down to a
  concrete artifact, not just a stated intention.

### Documentation Updated
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-004), `module_2_classification/
MODULE_CONTEXT.md` ("Target Direction" and Stage 2 Implementation Status sections updated,
deferred risk-tier item resolved), `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (new
`risk_thresholds.py` entry), `research_context/CHANGELOG.md`.

---

## Decision 025: Module 2 Label Mean/SD Estimator Replaced With Per-District Harmonic
Regression (Open Question #8); k Re-Audited to 3.0

**Module:** Module 2
**Status:** Accepted (implemented, audited, and run 2026-07-28 as `EXPERIMENT_LOG.md` M2-005)
**Date:** 2026-07-28

### Decision
Decision 019's outbreak-threshold **formula** (`outbreak = 1 if Number_of_Cases >
historical_mean + k * historical_sd`, strictly-prior-years-only) is unchanged. What changes
is the **estimator** used to compute `historical_mean`/`historical_sd`, addressing Module 2
Open Question #8 (flagged since Decision 019, never yet acted on):

1. **New official estimator**: `compute_historical_stats_harmonic`
   (`src/module2_classification/labels.py`) replaces `compute_historical_stats` (Decision
   019's exact-per-(District, Week) sample mean/SD) as the function
   `compute_epidemic_threshold_labels` calls by default. For each `(District, Year)`, an OLS
   regression of `Number_of_Cases` on 1 harmonic of week-of-year
   (`sin(2*pi*Week/52)`/`cos(2*pi*Week/52)`) is fit using only that district's REAL,
   strictly-prior-year rows (expanding, refit each year — the same strictly-prior-years
   leakage guard as before, just applied at an annual grain instead of per-row).
   `historical_mean` = the fitted seasonal curve evaluated at the row's own `Week`;
   `historical_sd` = the fit's residual standard error, shared across every week of that
   district-year (unlike the old estimator's per-exact-week SD). Decision 019's original
   estimator is **kept in the codebase, not deleted**, explicitly marked superseded, for
   audit/comparison (`scripts/audit_label_stabilization.py`'s `exact_week` control).
2. **`k` re-audited, not carried over unchanged**: `EPIDEMIC_THRESHOLD_K` changes from `2.0`
   to `3.0`. Because the new estimator's `historical_sd` is a fundamentally different
   quantity (a regression residual SE, not a per-week sample SD), reusing `k=2.0` would not
   obviously mean "the same 2 SDs" as before — `k` was re-scanned specifically for the new
   estimator.
3. **New config constant**: `EPIDEMIC_THRESHOLD_N_HARMONICS = 1` (`src/config.py`). A
   2-harmonic variant was audited alongside (to capture Sri Lanka's bimodal SW/NE monsoon
   pattern) but performed almost identically to 1 harmonic (pooled prevalence 15.72% vs.
   15.73% at k=1.5, 10.14% vs. 10.03% at k=2.5) — the simpler 1-harmonic model is preferred
   on parsimony grounds, not because 2 harmonics failed.
4. **Audit-first methodology** (new script `scripts/audit_label_stabilization.py`, mirrors
   `scripts/data_audit_module2.py`'s original k-audit pattern): 6 candidate estimators
   (`exact_week` control; `windowed` at week-window sizes 1/2/3, pooling nearby weeks'
   case counts across strictly-prior years; `harmonic` at 1/2 harmonics) x 3 k values each,
   compared on pooled/per-district prevalence, undefined-label rate, and an explicit
   spot-check of Colombo District/2025/Week 15 (see Reason below for why this spot-check
   mattered). Full results: `outputs/metrics/module2/{label_stabilization_audit,
   label_stabilization_spot_check}.csv`.

### Reason
**The motivating evidence needed correction before any fix could be honestly evaluated.**
The task that prompted this decision cited Colombo's 2025 Week 15 (277 actual cases) as a
label defect — "labeled/predicted low risk" because Colombo's high baseline supposedly
dampens the relative-deviation threshold. Direct verification against the running
production pipeline **disproved this specific claim**: under Decision 019's ORIGINAL
estimator, Colombo 2025 Wk15's `historical_mean=80.9`, `historical_sd=87.7`,
`threshold=256.4` — so `277 > 256.4` and the row's true LABEL was already `1` (outbreak),
correctly, before any of this work began. Cross-referencing
`stage2_risk_tier_predictions.csv` for that exact row showed what actually happened: Stage
1's raw probability was 0.455, but the official isotonic-calibrated probability was 0.155 —
just under the (pre-Decision-025) F2-optimal alert threshold of 0.170 — so it was tiered
"low" and never alerted, while the (non-selected) stacked-XGBoost architecture would have
called it "medium." **This was a Stage 2 calibration/threshold near-miss, not a label
defect** — a materially different diagnosis that changes what "fixing Colombo" would even
mean (nothing in `labels.py` needed fixing for this specific case). This correction was
surfaced to the user before any candidate was chosen, per this project's "critique
assumptions, don't just agree" rule.

**The other motivating finding was real and is what this decision actually addresses**:
Decision 019's own audit found an 18-25%-of-weeks pooled "outbreak" rate, well above
WHO/CDC's typical single-digit-percent epidemic-alert norm — evidence the exact-per-week
estimator's small sample size (as few as 3-15 strictly-prior years for one week number) was
noisy enough to flag much of each district's normal seasonal peak, not only genuine
anomalies.

**Window-pooling was tested and rejected as the fix**, a genuinely important negative
result: pooling nearby weeks' case counts INCREASES the SD estimate in high-variance urban
districts (more weeks captured = more spread), which raises the threshold rather than
stabilizing it — it only modestly reduced pooled prevalence (18.4% → 15.5% at window=3,
k=2.0) and, when checked against the Colombo spot-check at the finally-chosen k, would have
made that specific case's threshold even harder to cross (Colombo's `historical_sd` rises to
~145 at window=3 vs. 87.7 for the exact-week estimator). Harmonic regression won instead:
by fitting one smooth curve per district-year using ALL of that district's strictly-prior
weeks (not just one exact week number), it materially reduces the pooled prevalence (18.4%
→ 12.3% at the SAME k=2.0; → 8.6% at the chosen k=3.0) while ALSO reducing the
undefined-label rate (16.0% → 10.7%, since a smooth curve needs less exact-week history to
fit reliably) — a genuine improvement on both axes, not a trade-off, and the closest of all
6 candidates to Open Question #8's WHO/CDC-style single-digit aspiration.

**Important honest limitation, not hidden**: adopting `k=3.0` with the harmonic estimator
raises `historical_sd` for Colombo specifically (208.97, nearly 2.4x the old estimator's
87.7 — Colombo's true week-to-week case dynamics are not well captured by a single smooth
harmonic curve, leaving a large residual spread), pushing its threshold to 792.8. **This
FLIPS Colombo 2025 Wk15's label from `1` (outbreak, old estimator) to `0` (not outbreak, new
estimator)** — the opposite of a "fix" for this one case, even though the aggregate
prevalence problem is genuinely improved. This is an expected, structural consequence of
using one global `k` to fix an aggregate-prevalence problem: it necessarily also raises the
bar in the highest-variance individual districts. Reported here explicitly rather than
presented as a clean win on all fronts — a district-specific or variance-adaptive `k` is
noted below as a candidate future refinement, not implemented this round.

### Results (full pipeline rerun, `--force`, `feature_engineering` through
`stage2_risk_thresholds`; `shared`/`module2_preprocessing` unaffected, not rerun)
- **Label**: pooled outbreak rate 18.41% → **8.57%** (defined labels), undefined-label rate
  16.02% → **10.72%**. No district degenerate (outside [2%, 40%]) at any audited k.
- **Stage 1 model selection FLIPPED**: median validation PR-AUC now favors
  **Random Forest** (0.3766) over XGBoost (0.3726) and Logistic Regression (0.3580) — a
  direct consequence of the much lower, differently-shaped label prevalence, not a code
  change to any model. Holdout (now only ~40 positive rows out of 2,600, since undefined
  labels concentrate in early years and the holdout block has 0% undefined): Random Forest
  PR-AUC 0.429, ROC-AUC 0.885, vs. XGBoost 0.424/0.896, Logistic Regression 0.235/0.835.
- **Stage 2 architecture unchanged (isotonic)**, but now a much closer contest: median
  validation BSS isotonic 0.2146 vs. Platt 0.2116 (was 0.166 vs. 0.145) — both markedly
  improved vs. Stage 1 raw's -0.584. Holdout BSS: Platt (0.2344) edges isotonic (0.2315)
  very slightly, but isotonic remains selected per the pre-registered validation-fold
  selection rule.
- **Risk thresholds recomputed**: alert threshold 0.170 → **0.140**, high-confidence
  boundary 0.570 → **0.350** (both lower, tracking the lower overall prevalence). Holdout:
  naive 0.5 cutoff now gives recall 45%/F2 0.459 (accuracy 98.5%, reflecting the much lower
  prevalence); the F2-optimal 0.140 threshold gives recall 60%/F2 0.519. **Not directly
  comparable to Decision 024's 68.6%-recall/0.574-F2 figures** — the label itself changed,
  so these numbers measure a different, less noisy target, not a regression.
- **Pooled-vs-per-district reconfirmed** for both stages (Stage 1: pooled median PR-AUC
  0.373 vs. per-district median 0.343; Stage 2: pooled BSS -0.108 vs. per-district median
  -0.463) — architecture choice unaffected by the label change.
- **Feature importance dominance unchanged**: `case_anomaly_lag_1`/`_2` remain the top two
  features by a wide margin under the new official model (Random Forest), consistent with
  Decision 019's leakage note (these are conceptually near-identical to the label one week
  prior) — no new leakage concern introduced by the estimator change.

### Implication
- **This is a genuine break in numeric comparability with M2-001 through M2-004**, an
  explicit, justified, and documented break (not silent) — the label ITSELF changed, unlike
  Decisions 023/024 which only changed hyperparameters/thresholds around a fixed label. Any
  future comparison against pre-Decision-025 numbers must state which label version was used.
- `src/module2_classification/labels.py`: new `compute_historical_stats_harmonic` and
  `_harmonic_design` functions; `compute_historical_stats` (Decision 019's estimator) kept,
  not deleted, explicitly marked superseded; `compute_epidemic_threshold_labels` switched to
  the new default.
- `src/module2_classification/feature_engineering.py`: `compute_case_anomaly_lags` switched
  to call `compute_historical_stats_harmonic` (Group M2-5's `case_anomaly_lag_1/2` reuse the
  SAME estimator as the label, per its existing documented design — this consistency
  requirement is why this file needed a matching change, not just `labels.py`).
- `src/config.py`: `EPIDEMIC_THRESHOLD_K` changed `2.0` → `3.0`; new
  `EPIDEMIC_THRESHOLD_N_HARMONICS = 1`.
- New script `scripts/audit_label_stabilization.py` (read-only, not wired into `main.py`,
  mirrors `scripts/data_audit_module2.py`/`scripts/tune_stage1_xgboost.py`'s standalone
  precedent).
- Regenerated: `data/features/module2/stage1_feature_table.csv`,
  `data/processed/module2/{baseline_classifier_predictions, stage2_compensated_predictions,
  stage2_risk_tier_predictions}.csv`, all `outputs/metrics/module2/*` files depending on
  Stage 1/2/thresholds, `outputs/figures/module2/reliability_diagram_*.png`,
  `models/module2/{baseline_classifier, stage2_compensation}/*`.
- **Open follow-up, not implemented this round**: a district-specific or variance-adaptive
  `k` (or an interaction term letting the harmonic fit's residual spread scale with a
  district's own case volume) could recover sensitivity to genuine high-magnitude spikes in
  high-variance districts like Colombo without reopening the aggregate-prevalence problem
  this decision fixes — flagged as a candidate future refinement, not the same as Open
  Question #8's original consecutive-week idea (still separately available if wanted later).

### Documentation Updated
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-005), `module_2_classification/
MODULE_CONTEXT.md` (Open Question #8 resolved; Stage 1/Stage 2 Implementation Status
updated), `research_context/FEATURE_ENGINEERING_SPEC.md` (Label Definition and Group M2-5
updated), `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (`labels.py` entry and banner
updated), `research_context/CHANGELOG.md` (new entry).

---

## Decision 026: SMOTENC Oversampling Audited and Rejected — Decision 021's Class-Weight-Only Imbalance Handling Reconfirmed

**Module:** Module 2
**Status:** Rejected (audited 2026-07-28, `EXPERIMENT_LOG.md` M2-006; no production code changed)
**Date:** 2026-07-28

### Decision
**Reconfirm** Decision 021: Stage 1 keeps `class_weight="balanced"` (Random Forest/Logistic
Regression) / per-fold `scale_pos_weight` (XGBoost) as its only imbalance-handling mechanism.
**Do not adopt** SMOTENC (or any of the audited variants) as a production preprocessing step.
No change to `src/module2_classification/baseline_classifier.py`.

### Reason This Was Re-Audited At All
Prompted by a user request to research ways to increase real-world classification accuracy.
Literature review (dengue-specific and general imbalanced-classification sources) repeatedly
cited SMOTE-family oversampling as the single most effective lever for raising sensitivity in
imbalanced outbreak/disease classifiers. Decision 021 had already rejected SMOTE, but on a
reasoning worth re-examining rather than taking at face value: "synthetic oversampling across
a temporal walk-forward split would blur the fold boundary." On inspection, that specific
framing is not quite right — SMOTENC fit strictly on a fold's own TRAINING rows (never seeing
that fold's validation/holdout rows) does not leak future information across the walk-forward
boundary; the real, distinct risk is that SMOTE/SMOTENC linearly interpolates feature vectors
between two random minority-class TRAINING rows, which can synthesize physically-implausible
lag/rolling-stat combinations given `case_anomaly_lag_1/2` alone drive >60% of this model's
feature importance. Given the reasoning needed correcting, the conclusion itself was
re-audited empirically rather than assumed to still hold, per this project's "critique
assumptions, don't just agree" rule and its established audit-before-deciding precedent
(Decision 025).

### Audit Method (`scripts/audit_smote_imbalance.py`, read-only, not wired into `main.py`)
Reused `baseline_classifier.py`'s own `assemble_labeled_feature_table`,
`compute_fold_boundaries`, and `attach_fold_anomalies` verbatim, so every variant below is
scored on IDENTICAL 13 walk-forward folds + holdout rows to the current production benchmark
— only the training-time resampling/weighting differs. Leakage guard: SMOTENC is
`fit_resample`'d on each fold's own training rows only, after that fold's own
median-imputation (imputer fit on train, applied to train+val); `District` is passed as a
`categorical_features` column so synthetic rows always get a real, existing district (nearest-
neighbor majority vote), never an invented category. Four variants compared for both Random
Forest (current official model) and XGBoost (runner-up):

- `baseline_class_weight` — CONTROL, exactly today's production approach.
- `smotenc_full_no_weight` — SMOTENC to 1:1 balance, class weighting disabled.
- `smotenc_half_no_weight` — SMOTENC to minority=50% of majority, class weighting disabled.
- `smotenc_half_plus_weight` — SMOTENC to 50% balance PLUS class weighting still applied.

Caveat: XGBoost's production path leaves NaNs untouched (native handling); this audit's
XGBoost rows are median-imputed first (SMOTENC requires no missing values), so XGBoost's
numbers here are an indicative, not apples-to-apples, comparison. Random Forest's comparison
IS apples-to-apples, since RF is already median-imputed in production.

### Results (`outputs/metrics/module2/smote_imbalance_audit.csv`)
**Random Forest (official model), median validation PR-AUC across 13 folds — the
pre-registered primary selection metric (Decision 021):**

| Variant | Median val PR-AUC | Holdout PR-AUC | Holdout recall | Holdout Brier |
|---|---|---|---|---|
| `baseline_class_weight` (current) | **0.3766** | **0.4292** | 0.550 | 0.0273 |
| `smotenc_full_no_weight` | 0.3564 | 0.4024 | 0.550 | 0.0282 |
| `smotenc_half_no_weight` | 0.3862 | 0.4290 | 0.500 | 0.0187 |
| `smotenc_half_plus_weight` | 0.3465 | 0.4207 | 0.600 | 0.0274 |

- The best-looking variant (`smotenc_half_no_weight`) shows a small validation-median PR-AUC
  gain (+0.0096) that **evaporates on holdout** (-0.0002, statistically a wash) — the
  pre-registered selection rule (Decision 021) treats holdout as a check, not a tiebreaker,
  and this variant fails that check. It also costs holdout recall (0.550 → 0.500), the wrong
  direction for an early-warning system that deliberately favors recall (Decision 024).
- The other two variants (`smotenc_full_no_weight`, `smotenc_half_plus_weight`) are worse than
  baseline on PR-AUC in BOTH validation and holdout — clean losses, not close calls.
- **XGBoost showed a genuinely informative red flag, not just a null result**: every SMOTENC
  variant improved XGBoost's median validation PR-AUC (0.383 → 0.397-0.401) but WORSENED its
  holdout PR-AUC (0.422 → 0.411-0.416) in all three cases — validation-fold gains that
  systematically fail to generalize to the untouched holdout block are exactly the pattern a
  pre-registered holdout check exists to catch, and reinforce (rather than merely fail to
  contradict) the decision not to adopt SMOTE.
- **One consistent, real secondary finding**: nearly every SMOTENC variant meaningfully
  improves raw Brier score (e.g. Random Forest holdout 0.0273 → 0.0187 for
  `smotenc_half_no_weight`) — SMOTENC's rebalancing does produce better-calibrated raw
  probabilities. This is very unlikely to be a decision-relevant win in this specific
  pipeline, though: Stage 2 already recalibrates whatever raw probability distribution Stage 1
  produces via isotonic regression (Decision 022/025), so a Stage-1-only calibration
  improvement is largely redundant with a correction that already happens downstream
  regardless of Stage 1's raw calibration quality — flagged as a possible ablation for a
  future full Stage 1+2 rerun, not evidence for adopting SMOTENC on its own.

### Implication
- Decision 021 stands, now on stronger empirical footing than its original reasoning alone
  (which was imprecise about why the temporal split mattered). The interpolation-of-lagged-
  features risk raised as the more precise concern in this decision's own reasoning section is
  consistent with the observed pattern: SMOTENC's apparent within-fold gains do not survive
  the holdout check.
- `imbalanced-learn` was added to `requirements.txt` for this audit; left in place (harmless,
  documents the audit was run with a real, installable dependency) even though production code
  does not import it.
- **Not** implemented or explored further this round: SMOTE combined with a Stage 2 rerun (to
  test whether the Brier-score improvement survives downstream), or non-SMOTE resampling
  (e.g. simple random undersampling, as used successfully in some literature). Both flagged as
  candidate future ablations, not rejected outright.

### Documentation Updated
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-006), `module_2_classification/
MODULE_CONTEXT.md` (Open Question #4 addendum reconfirming Decision 021),
`research_context/CHANGELOG.md` (new entry). New artifacts: `scripts/audit_smote_imbalance.py`,
`outputs/metrics/module2/smote_imbalance_audit.csv`. No production pipeline artifact
regenerated — `baseline_classifier.py` and all its outputs are unchanged.

---

## Decision 027: Module 2 Forward Operational Risk Uses Module 1 Case Forecasts + Forecast Climate (Operational Tier)

**Module:** Module 2 (cross-module with Module 1, Integration layer)
**Status:** Accepted (implemented 2026-07-29)
**Date:** 2026-07-29

### Decision
For **operational** multi-week-ahead outbreak risk (dashboard consumption), Module 2's
forward scoring script (`forecast_future_risk.py`) may use:
1. **Module 1 `final_prediction`** from `future_forecast.csv` to populate case-derived lag
   features when real case counts are unavailable (weeks t+2 onward in the forward horizon).
2. **Open-Meteo forecast daily weather** (tagged `climate_data_source=forecast`) aggregated
   through the shared climate pipeline for weeks not yet observed.

This is **explicitly separate** from the holdout-validated walk-forward evaluation pipeline.
No Module 1 or Module 2 models are retrained. All forward outputs carry
`evidence_tier=operational`.

### Reason
Module 2's Stage 1 features are lags of prior-week cases/climate — never the current week's
case count (leakage guard). For true forward weeks, case lags must come from somewhere;
Module 1's recursive case forecast is the user-approved source. Climate for future weeks
requires the Forecast API extension, not just Archive gap-fill.

### Implication
- Does **not** supersede Decision 019/022's deferral of M1 integration in **training/evaluation**.
- Forward risk CSV must never be cited alongside holdout PR-AUC/BSS/recall figures.
- Error compounding (M1 recursive cases + forecast climate uncertainty) is flagged per-row
  via `uses_module1_cases`, `cases_source`, `climate_source`, `feature_completeness_pct`.

### Documentation Updated
`research_context/CHANGELOG.md`, `research_context/PIPELINE_ARCHITECTURE_PLAN.md`,
`research_context/CURRENT_ARCHITECTURE.md`, `module_2_classification/MODULE_CONTEXT.md`,
`module_1_forecasting/MODULE_CONTEXT.md`, `research_context/DATA_DICTIONARY.md`,
`research_context/QUESTIONS_FOR_DEFENSE.md`.
