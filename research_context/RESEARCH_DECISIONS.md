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
