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

1. **RESOLVED (2026-07-27).** Which SARIMA orders perform best per district?
   Answered empirically: `pmdarima.auto_arima` (constrained stepwise search,
   `max_p=2, max_q=2, max_P=1, max_Q=1`, run once per district per transform
   on the full pre-holdout history) proposed a candidate order for raw counts
   and for `log1p` counts; both were then genuinely walk-forward validated
   (`src/module1_forecasting/baseline_sarima.py`, reusing
   `validation.py` unchanged) and the lower-MASE candidate kept. Full
   per-district `(order, seasonal_order, use_log1p)` is in
   `models/module1/sarima_selected_configs.csv` — see the results table in
   "Stage 1 Implementation Status" below. **Major finding, not a defect**:
   the seasonal-differencing test (OCSB, cross-checked against
   Canova-Hansen — both agree) selected `D=0` for **all 25 districts**, and
   the stepwise search added a seasonal MA term (`Q=1`) for **none** of
   them; only 7/25 got a seasonal AR(1) term (`P=1`). 18/25 districts ended
   up with `seasonal_order=(0,0,0,52)` — a plain, non-seasonal ARIMA despite
   `m=52` being specified. Forcing `D=1` was tested and found computationally
   infeasible at scale (one `D=1, m=52` SARIMAX fit took 7+ minutes vs
   ~0.01s for the fixed-order refits used everywhere else in this pipeline).
   See open question #12 (new) for the implication.
2. **Deferred, not resolved — rationale strengthened (2026-07-27).** Should
   STL + SARIMA be tested as an alternative baseline? Still explicitly out
   of scope this session (building a second baseline architecture in the
   same pass as the first was an explicit non-goal). This is now a
   *higher-priority* future ablation than originally thought: since 18/25
   districts' selected SARIMA has no seasonal component at all (#1 above),
   an STL decomposition that explicitly extracts the annual cycle before
   differencing may recover seasonal structure that AIC-driven `auto_arima`
   is currently missing entirely.
3. **Answered with evidence (2026-07-27).** Are residuals autocorrelated
   enough to justify `residual_lag` features? Ljung-Box tests (lags 26, 52)
   on pooled out-of-sample validation residuals show statistically
   significant residual autocorrelation (p < 0.05 at lag 52) in **23 of 25
   districts** — the two exceptions being `Kilinochchi` (p ≈ 1.0) and
   `Mullaitivu` (p ≈ 0.10, where heavy zero-inflation likely swamps any
   autocorrelation signal). ACF plots for a representative subset
   (`Colombo`, `Kandy`, `Mullaitivu`, `Kilinochchi` —
   `outputs/figures/module1/acf_residuals_*.png`) confirm this visually:
   Colombo's residual ACF decays slowly over ~30 lags, indicating a large
   amount of exploitable structure remains unmodeled. This is genuine
   evidence FOR residual autocorrelation being present and exploitable — it
   supports, but per `PIPELINE_ARCHITECTURE_PLAN.md` does not by itself
   decide, Stage 2's planned `residual_lag_1/2` features. That remains
   Stage 2's own decision.
4. **Not ablated this session.** Which rainfall lag window gives best
   performance? The full `rainfall_lag_2..8` window (as originally specified)
   was used as-is. Stage 2's feature importance (gain-based, final production
   model) shows `rainfall_lag_5`/`rainfall_lag_6` among the top ~10 features
   overall — tentative evidence they carry real signal — but this was not a
   controlled ablation (no lag-window-subset comparison was run). Candidate
   future work.
5. **RESOLVED (2026-07-27).** Should `rain_sum` or `precipitation_sum` be
   preferred? `precipitation_sum (mm)` — see Decision 008
   (`RESEARCH_DECISIONS.md`) for the full reasoning (captures convective
   showers, which `rain_sum` excludes; relevant given Sri Lanka's
   shower-driven monsoon pattern). `feature_engineering.py`'s `RAINFALL_COLUMN`
   was switched and `stage2_feature_table.csv` regenerated before Stage 2 was
   built.
6. **RESOLVED (2026-07-27), answered by the Stage 2 evaluation framework
   itself.** How much improvement is required to claim compensation benefit?
   Rather than an arbitrary threshold, this is answered with a
   Diebold-Mariano test (Decision 016) — the criterion is statistical
   distinguishability from zero improvement, not a fixed percentage. Result:
   24/25 districts improve directionally (validation-aggregate MASE), 12/25
   reach `p < 0.05` at the larger validation+holdout DM scope, 4/25 at the
   stricter holdout-only scope. See "Stage 2 Implementation Status" below.
7. **Resolved (2026-07-27) — evidence gathered, Decision 002 kept
   unchanged.** Zero-inflation risk: rather than special-casing sparse
   districts, all 25 got the same uniform SARIMA treatment and their
   walk-forward results were compared directly. The results do **not**
   show a simple relationship between zero-inflation % and SARIMA
   performance: `Vavuniya` (32.2% zero-weeks — one of the four sparsest
   districts) has the *best* validation MASE of all 25 (0.38), while
   `Mullaitivu` (52.7% zero-weeks, the sparsest) has the *worst* (2.92);
   meanwhile `Colombo` (0.5% zero-weeks, essentially never sparse) also
   underperforms the seasonal-naive benchmark (MASE 1.63). Zero-inflation
   alone is not the dominant driver of relative SARIMA performance here —
   see #12 (outbreak volatility appears more relevant). This is evidence
   *against* the originally hypothesized concern, which supports keeping
   Decision 002 exactly as accepted.
8. **Resolved (2026-07-27), per-district, as recommended.** `log1p` won
   (lower validation MASE) for **17/25** districts; raw counts won for the
   remaining **8** (`Vavuniya, Kegalle, Mannar, Ratnapura, Hambantota,
   Gampaha, Badulla, Jaffna`). No obvious pattern by district size or
   zero-inflation level predicts which transform wins — this was correctly
   a per-district empirical question, not a global one (see
   `models/module1/sarima_selected_configs.csv`). Predictions are always
   inverse-transformed (`expm1`) back to raw case-count scale, and clipped
   to a 0 floor (both candidates, not just raw — see decision 2 below),
   before any metric is computed.

### New Open Questions (discovered 2026-07-27, Stage 1 implementation)

12. **Is AIC-driven `auto_arima` order selection actually fit for a
    52-week-ahead walk-forward forecasting task?** Given #1's finding (18/25
    districts get a non-seasonal ARIMA despite `m=52`), and that both
    seasonal-differencing tests independently agree with that choice, the
    underlying issue may be that AIC optimizes one-step-ahead in-sample fit,
    not long-horizon (52-week) forecast skill — a real mismatch for this
    project's use case. 12/25 districts have validation MASE > 1 (worse than
    a naive "repeat last year's same week" forecast). Candidate future work:
    (a) the already-deferred STL+SARIMA ablation (#2), (b) a
    forecast-horizon-aware order-selection criterion (e.g., selecting order
    directly by walk-forward MASE rather than AIC — computationally
    infeasible to do exhaustively within this session's one-time-per-district
    design), or (c) an explicit seasonal-naive/harmonic-regression ensemble
    component.

    **Sequencing decision (2026-07-27): intentionally deferred until after
    Stage 2 exists, not abandoned.** Reworking Stage 1's order selection now
    would be acting on a theoretical concern before knowing whether it's a
    practical problem. Stage 2's own feature set (`sin_week`/`cos_week`,
    monsoon indicators, climate lags, climate anomalies —
    `FEATURE_ENGINEERING_SPEC.md` Feature Groups 2-4) is specifically
    designed to capture the same annual/monsoon cycle that Stage 1 is
    missing for 18/25 districts. If Stage 1 misses that cycle, it doesn't
    disappear - it shows up as a large, systematic, predictable component of
    the residual, which is exactly what Stage 2 is built to learn. It is
    plausible Stage 2 compensates for this gap without any Stage 1 changes,
    in which case reworking Stage 1 first would have solved a problem Stage
    2 already solves.

    The concrete diagnostic that resolves this, once Stage 2 is built: split
    Stage 2's per-district improvement (Stage 1 vs. Stage 1+Stage 2 metrics)
    by whether that district's Stage 1 config has a seasonal component
    (7/25, `seasonal_P=1`) or not (18/25, `seasonal_order=(0,0,0,52)`). If
    the 18 non-seasonal districts show systematically weaker Stage 2
    compensation than the 7 seasonal ones, that is direct evidence Stage 1
    needs rework for (at least) those districts. If not, this open question
    can be closed without touching Stage 1 further. Revisiting Stage 1 later
    is cheap regardless of outcome: the expensive part (`auto_arima` search)
    is a one-time, already-benchmarked ~82-minute cost for all 25 districts,
    and could be re-run for only the specific districts found to need it,
    not all 25 - so deferring this carries no meaningful lock-in cost.

    **RESOLVED WITH EVIDENCE (2026-07-27, Stage 2 built and run; numbers
    refreshed same day after the Open Question #14 fix below).** The
    diagnostic came back in the *opposite* direction from what would justify
    reworking Stage 1: the 18 non-seasonal districts show a **larger** median
    MASE improvement from Stage 2 (44.9% validation-aggregate / 39.1%
    holdout) than the 7 seasonal districts (31.9% validation-aggregate /
    26.2% holdout). This is evidence FOR the original sequencing bet — Stage
    2's `sin_week`/`cos_week`/monsoon-indicator/climate-anomaly features
    appear to be substantially compensating for the annual cycle that Stage
    1's SARIMA missed in those 18 districts, without needing to touch Stage 1
    at all. This open question is now closed: no Stage 1 rework is justified
    by this evidence. (Caveat: `Kilinochchi`, one of only two districts where
    Stage 2 makes the *holdout* MASE worse post-fix, is itself one of the 7
    *seasonal* districts — a small, single-district counter-example within
    the smaller group, noted but not large enough to change the aggregate
    conclusion. See "Stage 2 Implementation Status" below for full numbers.)
14. **RESOLVED AND FIXED (found 2026-07-27 during Stage 2 implementation;
    fixed and re-run 2026-07-27 same day — see Decision 017).** Stage 1's
    SARIMA diverged catastrophically for `Vavuniya` in one walk-forward fold
    (2010, weeks 42-51): forecasts reached ~30 million cases/week against an
    actual mean of ~6/week. This did not surface in Stage 1's own original
    headline metrics because the per-district validation MASE is a
    **median** across 14 folds (robust to one bad fold by design) —
    `Vavuniya`'s originally-reported validation MASE of 0.38 (already the
    best of all 25 districts) was technically correct but hid this one
    catastrophic fold entirely. It was only discovered because Stage 2 pools
    all districts' residuals into one model, and this single extreme
    residual (~-30,000,000) was large enough to corrupt predicted residuals
    for every other district too (see Decision 014's Stage 2 mitigation:
    switching to a robust `reg:absoluteerror` objective, which contained the
    symptom but did not fix Stage 1 itself).

    **Root cause, confirmed precisely**: `enforce_stationarity=False`
    (Stage 1 design decision 3) let the fold-1 refit of the fixed order
    `(1,0,2)` land on an AR(1) coefficient of 1.266 (>1 → explosive/
    non-stationary), which SARIMAX happily accepts without complaint. A full
    25-district scan for the same pathology found a **second, independent
    occurrence**: `Mannar`'s 2022 fold-13 fit a seasonal AR coefficient of
    1.162 (`(0,0,0)x(1,0,0,52)`), putting all 52 seasonal roots on the unit
    circle — confirming this is a general failure mode, not a Vavuniya-only
    quirk. **Fixed** in `baseline_sarima.fit_and_forecast()`: every fit's
    combined AR-polynomial roots are now checked; any root on or inside the
    unit circle is treated as a failed fit (`NaN` for that fold), consistent
    with Stage 1's existing failure-handling convention. Full pipeline
    (Stage 1 → Stage 2 → combine) was regenerated with this fix.

    **Result**: `Vavuniya` went from one of the pipeline's most fragile
    districts to one of its best (validation MASE 0.375 → 0.286, holdout
    0.417 → 0.374). Stage 2's headline result improved from 24/25 to a
    **clean 25/25 districts** improving on validation-aggregate MASE, with
    median validation MASE improvement rising slightly to 39.0% and, more
    notably, median **holdout** MASE improvement rising from ~29% to 39.7% —
    much closer to (and more consistent with) the validation figure than
    before. See Decision 017 and "Stage 2 Implementation Status" below for
    complete before/after numbers, including the (small, non-significant)
    holdout regressions for `Kilinochchi` and `Mannar`.
15. **Holdout vs. validation-fold performance diverges more than expected**:
    18/25 districts have holdout MASE < 1 vs. only 13/25 for the walk-forward
    validation aggregate, and several districts' holdout MASE is noticeably
    better than their validation-fold median (e.g. `Jaffna`: 2.22 validation
    vs. 0.32 holdout; `Puttalam`: 0.89 vs. 0.31). Plausible explanations
    (not yet investigated): the single-block holdout fit benefits from
    using the single longest available training window, or recent years
    (2022-2026) are simply less volatile than the 2007-2021 span most
    validation folds are drawn from. Worth a closer look before Stage 2
    treats holdout numbers as representative of "true" future performance.
16. **New (2026-07-27, discovered while checking the framework against the
    real, ongoing 2026 Colombo/Gampaha outbreak).** The dataset already
    extends to 2026 week 25 — the actual outbreak spike (Colombo 1,138
    cases, Gampaha 1,294 cases at week 25) falls inside the untouched
    holdout block, giving a genuine real-world test. Two findings:
    - **Shared climate data pipeline refresh (2026-07-29, Decision 027):**
      `scripts/fetch_open_meteo_weather.py` closes the observed-week gap through
      2026 Wk25. Forward epi-week climate beyond the master calendar and beyond
      the ~16-day Forecast API window remains a documented operational
      limitation.
    - Even during the accuracy-decent weeks 1-21 stretch (climate data
      present, cases already well above the historical Jan-Jun baseline),
      the framework still completely missed the acute week-25 explosion
      itself (~8-10x underestimate for both districts) — expected, not a
      red flag: this is a 104-week-ahead, one-shot holdout forecast from a
      fixed 2-year-old vantage point, not a rolling forecast that would see
      the weeks 20-24 ramp-up happening in real time. A rolling 1-week-ahead
      re-evaluation (closer to how the framework would actually be deployed
      operationally) is a natural, not-yet-built follow-up to properly
      assess real-time outbreak-response accuracy — flagged here, not
      implemented this session per user direction to prioritize the
      Vavuniya/Mannar Stage 1 fix first (Decision 017).
    - A secondary confound worth separating out before drawing conclusions
      from the week-25 numbers specifically: both districts show a
      suspiciously low case count at week 24 (Colombo 20, Gampaha 24)
      immediately preceding the week-25 spike — a plausible signature of
      delayed case reporting catching up in one lump, which would also mean
      `residual_lag_1` fed the model a misleadingly *negative* signal right
      when a strongly positive one was needed. Not yet confirmed against
      the raw source data.

---

## Resolved Data Questions (2026-07-26)

- Data range confirmed: 2007–2026 per district (weekly case + daily climate), sufficient for SARIMA m=52 seasonality.
- Epi-week definition confirmed: Sri Lanka MoH epidemiological week standard (scraped directly from source), not ISO calendar week.
- District names confirmed consistent across case and climate datasets — no merge-key risk.
- Population data available: census years 2001, 2012, 2024 — see Decision 006 for interpolation/reporting-layer policy. **Placed 2026-07-27** at `data/raw/population/population_by_district.csv` (`Moneragala` corrected to `Monaragala` on ingestion). Note: `Kilinochchi`/`Mullaitivu`/`Mannar` show a non-monotonic, war-era population trend across the 3 census points — documented limitation, see `DATA_DICTIONARY.md` Section 3.
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

## Implementation Status (2026-07-27 - Preprocessing Pipeline Built)

The shared preprocessing layer and the full Module 1 preprocessing/feature
pipeline (up to, but not including, the Stage 1/2 models themselves) are now
implemented and have been run end to end against the real data:

- `src/config.py` - real 25-district `DISTRICTS` list, `MONSOON_WEEKS_SW`
  (weeks 20-38), `MONSOON_WEEKS_NE` (weeks 44-52, 1-8), and all pipeline
  paths (raw/shared/module1 processed + feature paths).
- `src/preprocessing/shared.py` - Kalmunai->Ampara merge, master epi-week
  calendar, climate weekly aggregation (all climate columns retained), and
  population interpolation/extrapolation. Outputs written to
  `data/processed/shared/`: `epi_week_calendar.csv` (1,017 rows),
  `climate_weekly.csv` (25,300 rows x 15 cols — up from 24,950 prior to the
  2026-07-27 raw date corrections below), `population_annual.csv`
  (525 rows), `epidemiological_weekly.csv` (25,348 rows).
- `src/preprocessing/module1_preprocessing.py` - week-53 merge (2009, 2016,
  2019, 2021), seasonal-naive imputation of the 4 confirmed nationwide gap
  weeks (100 rows flagged `is_imputed`), climate + population merge,
  `cases_per_100k`. Output: `data/processed/module1/weekly_modeling_table.csv`
  (25,350 rows; every interior year 2007-2025 has exactly 52 weeks/district;
  zero duplicate `(District, Year, Week)` keys).
- `src/module1_forecasting/validation.py` (new) - `generate_walk_forward_folds`,
  `fit_window`, `get_holdout_series`, `iter_walk_forward_windows`,
  `generate_walk_forward_folds_by_district`. Tested against Colombo's real
  series: 14 expanding-window annual folds, 104-week holdout, zero overlap
  between any fold and the holdout block.
- `src/module1_forecasting/feature_engineering.py` (new) - fold-agnostic
  features (case lags/rolling stats/rate of change, climate lags, cyclic
  week + monsoon indicators) written to
  `data/features/module1/stage2_feature_table.csv` (25,350 rows x 47 cols,
  `weather_code` excluded). Fold-aware climate anomalies are exposed as
  `compute_fold_climate_anomalies(df, train_mask)` - deliberately NOT written
  to a global file, since a global computation would leak future climate
  norms into early walk-forward folds. Verified against a manual
  hand-calculation for one district/fold.

Out of scope this session (per plan): `baseline_sarima.py`,
`compensation_model.py`, `combine.py`, `evaluate.py`, `main.py`.

### Deviations From the Plan / Implementation Choices Made

1. **Weekly aggregation rule for `weather_code`** (both in
   `shared.py`'s daily->weekly step and `module1_preprocessing.py`'s
   week-53 merge): the plan says "keep all columns" / "average climate
   columns" but never specifies a rule for a *categorical* code. Implemented
   as the weekly/pair **mode** (most frequent value, ties broken by the
   smaller code). This is an implementation choice, not a research decision -
   flag for review if `weather_code` is ever promoted out of "excluded"
   status (Decision 008).
2. **`rainfall_lag_*` feature source**: Open Question #5 below ("`rain_sum`
   vs `precipitation_sum`") is still unresolved. `feature_engineering.py`
   defaults to `rain_sum (mm)` as a **provisional placeholder**, clearly
   flagged in code (`RAINFALL_COLUMN`) - not a resolution of the open
   question.
3. **`rate_of_change` formula**: not specified in
   `FEATURE_ENGINEERING_SPEC.md`. Implemented as the absolute difference
   `cases_lag_1 - cases_lag_2` rather than a percent change, specifically to
   avoid divide-by-zero blowups given this module's well-documented
   zero-inflation. Worth an ablation later.
4. **Rolling case stats use `shift(1)` before `rolling(4)`**: i.e.
   `rolling_mean_cases_4w`/`rolling_std_cases_4w` for week *t* summarize
   weeks *t-1..t-4*, never week *t* itself. Not explicit in the spec, but
   required to avoid the feature leaking its own target.
5. **Interior-year completeness check excludes the two boundary years**
   (2006, 2026): "exactly 52 weeks/district/year" is enforced for 2007-2025
   only. 2006 (starts 12/23) and 2026 (data ends mid-year) are naturally
   partial by construction, not genuine gaps - forcing them to 52 rows would
   have meant fabricating dozens of weeks that were never scraped because
   they hadn't happened yet / the series hadn't started.
6. **Calendar gap-filling added to `shared.py`** (`fill_isolated_calendar_gaps`,
   not in the original plan text): see open question #10 below - this was
   necessary to give the 4 confirmed nationwide-gap weeks a usable date at
   all downstream.

### New Open Questions / Data Quality Findings (discovered 2026-07-27 while implementing)

9. **Confirmed via re-run**: the 4 documented nationwide case-data gaps
   (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) have **zero raw rows
   for any district** - they don't even exist in the master epi-week
   calendar (which is built from raw rows), not just the case data. Handled
   by (a) a new `fill_isolated_calendar_gaps` step in `shared.py` that
   sequentially infers a clean date range when exactly one week's worth of
   days (8-day gap) fits unambiguously between two known neighbours, and
   (b) `module1_preprocessing.py`'s existing seasonal-naive imputation for
   the case counts. 3 of the 4 (`2015 Wk30`, `2021 Wk42`, `2022 Wk43`) got
   an inferred date this way. **`2020 Wk1` could not be dated**: 2019 is a
   confirmed 53-week year whose Wk53 already runs through 2020-01-03, and
   2020's own Wk2 starts 2020-01-04 - there is no day-range gap left to
   place a "Week 1" in at all. `Number_of_Cases` for these 25 rows is still
   seasonal-naive imputed and flagged `is_imputed`, but their
   `Week_Start_Date`/`Week_End_Date` are left as `NaN` rather than
   fabricated. **Needs team discussion**: does a real "epi-week 1 of 2020"
   exist in the true MoH calendar at all, or is this a structural artifact
   of 2019 running long?
10. **RESOLVED (2026-07-27).** Systematic per-week date mislabeling,
    distinct from the 5 collisions fixed 2026-07-26. Building the master
    calendar and sorting it chronologically originally surfaced **30
    `(Year, Week)` labels** (2008-2024) whose date stamp was self-consistent
    across (almost) all districts — invisible to the per-row disagreement
    check — but chronologically wrong relative to neighbouring weeks (a
    page-level MoH scrape error per affected week). The user manually
    corrected 28 of the 30 against the original MoH source pages. Verifying
    that pass surfaced two further layers of issues, all now fixed directly
    in `dengue_cases_corected.csv`:
    - **2 of the 30 were missed** — `2009 Wk24` and `2023 Wk40` both had the
      same "month field one behind" error as the other 28 (e.g. `2009 Wk24`
      showed `5/6/2009–5/12/2009`, day-of-month exactly right, but should
      have been `6/6/2009–6/12/2009`), just not caught during manual review.
    - **A full-calendar day-count scan** (checking every week for exactly 7
      days and a 1-day gap to its neighbour, not just the overlap-only check
      that found the original 30) found 3 more previously-undetected
      date-entry errors that don't manifest as overlaps: `2010 Wk9` (end
      date was literally before its start date — `3/27/2010–3/5/2010`; fixed
      to `2/27/2010–3/5/2010`), `2011 Wk48` (start date 3 days late, leaving
      a 4-day week; fixed `11/29/2011→11/26/2011`), and `2013 Wk39`/`Wk40`
      (a 1-day boundary misplacement mirroring the `2009 Wk21/22` pattern;
      fixed `9/28/2013→9/27/2013` and `9/29/2013→9/28/2013` respectively).
    - The 2 outstanding per-row disagreements (`Ampara 2013 Wk51`, `Ampara
      2023 Wk14`) were also corrected — Ampara's own row now matches the
      national mode for both weeks.
    - **Two weeks are accepted as irregular by design, not left broken by
      oversight**: `2009 Wk17` (8 days) and `2009 Wk22` (6 days) each sit in
      a stretch of the raw data with a genuine 1-day surplus/deficit that
      cannot be fixed by editing one date without opening a *new* gap with
      an already-correct neighbour (verified concretely for `Wk17`: shortening
      it creates a fresh 2-day gap with `Wk18`, which was untouched and
      correct). Case counts for both weeks are unaffected.
    - **One low-priority item remains open**: a genuine 3-day gap between
      `2025 Wk52` (ends `12/26/2025`) and `2026 Wk1` (starts `12/29/2025`),
      confirmed present in the raw source. This sits at the live-scrape edge
      of the dataset (raw data currently extends to `2026 Wk25`) and needs a
      source-page check rather than an assumed fix.
    - After re-running the full pipeline, `epi_week_calendar_chronology_issues.csv`
      and `epi_week_calendar_disagreements.csv` are both empty, and all 375
      climate rows previously blocked by this issue in
      `weekly_modeling_table.csv` are now populated (confirmed: the only
      remaining 150 "no matching climate" rows are the expected boundary
      cases — 2006 Wk52 before climate coverage begins, 2020 Wk1's dateless
      rows per #9, and 2026 Wk22-25 after current climate coverage ends).
    - **Bonus fix**: also found `shared.py` only wrote the two diagnostic
      CSVs above when non-empty, so a clean re-run left a stale issues file
      from a prior run on disk. `run_shared_preprocessing()` now always
      (re)writes both files.
11. **Weather CSV dates are inconsistently formatted**: 24 of 25 per-district
    files use ISO `YYYY-MM-DD`; the Colombo file alone uses `M/D/Y`. Parsed
    with `pd.to_datetime(..., format="mixed")` in `shared.py` - works, but
    is a fragile pattern worth normalizing at the source if the raw files
    are ever regenerated.

## Stage 1 Implementation Status (2026-07-27 - SARIMA Baseline Built)

`src/module1_forecasting/baseline_sarima.py` and `src/module1_forecasting/
evaluate.py` are implemented and have been run end to end against all 25
districts (`python -m src.module1_forecasting.baseline_sarima`, ~82 minutes
wall time, dominated by the 50 one-time `auto_arima` calls). Outputs:

- `data/processed/module1/sarima_stage1_predictions.csv` (20,800 rows =
  25 districts x (14 folds x 52 validation weeks + 104 holdout weeks)):
  `District, Year, Week, split (validation/holdout), fold_id, Number_of_Cases,
  is_imputed, sarima_prediction, residual`.
- `models/module1/sarima_selected_configs.csv` (25 rows): per-district
  winning `(order, seasonal_order, use_log1p)` plus both candidates'
  aggregate MASE for transparency.
- `outputs/metrics/module1/sarima_walk_forward_metrics.csv` (400 rows =
  25 districts x (14 validation folds + 1 `validation_aggregate` + 1
  `holdout`)): RMSE/MAE/sMAPE/MASE + Ljung-Box stat/p-value (lags 26, 52)
  on the aggregate row.
- `outputs/figures/module1/acf_residuals_{Colombo,Kandy,Mullaitivu,
  Kilinochchi}.png`: representative-subset ACF diagnostic plots.

Zero fallback orders were needed - `auto_arima` completed successfully for
all 25 districts x 2 transforms.

**Update (2026-07-27, later same day, Decision 017):** the claim below in
decision 3 that "none occurred in the full run" (referring to failed
fits/`NaN` folds) was **only true before the explosive-AR-root guard was
added**. Two folds now legitimately produce `NaN` under the corrected
definition of "failed fit" - `Vavuniya` fold 1 (2010) and `Mannar` fold 13
(2022), both non-stationary/explosive SARIMAX fits that the original
`enforce_stationarity=False` design let through silently. See Decision 017
and Open Question #14 for full detail; all Stage 1 numbers throughout this
document reflect the post-fix, regenerated run.

### Five design decisions approved before implementation

1. **Order search uses full pre-holdout history, not per-fold.** One
   `auto_arima` call per district per transform (constrained stepwise
   search: `max_p=2, max_q=2, max_P=1, max_Q=1`), not per walk-forward
   fold (infeasible - already benchmarked at ~25-59s/call). Accepted,
   documented compromise: the order chosen for an early fold is technically
   informed by later data, but every fold's *fitted parameters and
   residuals* still come from a fresh `SARIMAX.fit()` on that fold's own
   training window only (Decision 010 unaffected - see `fit_and_forecast()`).
2. **Forecasts clipped to a 0 floor after inverse-transforming**, for BOTH
   candidates (not just raw) - case counts cannot be negative, and a
   `log1p`-space forecast can technically dip below `log1p(0) == 0`, which
   `expm1` would turn negative.
3. **`SARIMAX(..., enforce_stationarity=False, enforce_invertibility=False)`**
   on every fit, to avoid convergence failures across 25 districts x 14
   folds x 2 candidates. Any fold whose fit still fails is caught, logged,
   and recorded as `NaN`. **Updated 2026-07-27 (Decision 017)**: "failed fit"
   now also includes a fit whose AR polynomial has a non-stationary/explosive
   root (`enforce_stationarity=False` otherwise lets these through silently)
   - two folds (`Vavuniya` fold 1, `Mannar` fold 13) are caught by this and
   recorded as `NaN`, where they previously produced wildly divergent
   finite forecasts instead.
4. **MASE is the single deciding metric** for both (a) raw-vs-`log1p` per
   district and (b) the reported "winning" config, computed with a
   seasonal-naive (m=52) scale from the *training* window, with
   `is_imputed` rows excluded from both the scale and the scored error
   (Decision 011). RMSE/MAE/sMAPE are still stored for every fold.
5. **Holdout (104 weeks) is forecast AND scored now**, fit once on all
   pre-holdout data with the winning config, explicitly labeled
   `split="holdout"` - a one-time report, never used to revise the
   selected order/transform (Decision 009's "untouched until final
   reporting" is intact: nothing here fed back into order/transform
   selection).

### Per-district results (validation = median across 14 walk-forward folds; holdout = single final 104-week block)

| District | Transform | Order | Seasonal Order | Validation MASE | Holdout MASE |
|---|---|---|---|---|---|
| Ampara | log1p | (0,1,1) | (0,0,0,52) | 0.97 | 0.43 |
| Anuradhapura | log1p | (0,1,2) | (1,0,0,52) | 0.79 | 0.53 |
| Badulla | raw | (1,1,1) | (1,0,0,52) | 1.36 | 0.55 |
| Batticaloa | log1p | (0,1,1) | (0,0,0,52) | 1.92 | 0.59 |
| Colombo | log1p | (1,1,1) | (0,0,0,52) | 1.63 | 0.65 |
| Galle | log1p | (0,1,1) | (0,0,0,52) | 1.21 | 1.17 |
| Gampaha | raw | (2,1,0) | (0,0,0,52) | 1.05 | 0.74 |
| Hambantota | raw | (0,1,1) | (0,0,0,52) | 0.96 | 0.95 |
| Jaffna | raw | (2,1,2) | (1,0,0,52) | 2.22 | 0.32 |
| Kalutara | log1p | (2,1,1) | (0,0,0,52) | 1.42 | 0.66 |
| Kandy | log1p | (0,1,1) | (0,0,0,52) | 1.27 | 0.43 |
| Kegalle | raw | (0,1,2) | (0,0,0,52) | 0.59 | 0.33 |
| Kilinochchi | log1p | (0,1,1) | (1,0,0,52) | 1.45 | 2.15 |
| Kurunegala | log1p | (1,1,1) | (0,0,0,52) | 0.86 | 0.38 |
| Mannar | raw | (0,0,0) | (1,0,0,52) | 0.81 | 1.12 |
| Matale | log1p | (1,1,2) | (0,0,0,52) | 0.84 | 1.28 |
| Matara | log1p | (2,1,2) | (0,0,0,52) | 0.94 | 1.45 |
| Monaragala | log1p | (1,1,2) | (1,0,0,52) | 0.63 | 0.62 |
| Mullaitivu | log1p | (0,1,1) | (0,0,0,52) | 2.92 | 0.53 |
| Nuwara Eliya | log1p | (0,1,2) | (0,0,0,52) | 0.93 | 1.37 |
| Polonnaruwa | log1p | (1,1,2) | (1,0,0,52) | 1.04 | 0.78 |
| Puttalam | log1p | (0,1,1) | (0,0,0,52) | 0.89 | 0.31 |
| Ratnapura | raw | (2,1,0) | (0,0,0,52) | 0.90 | 1.11 |
| Trincomalee | log1p | (0,1,2) | (0,0,0,52) | 1.04 | 0.41 |
| Vavuniya | raw | (1,0,2) | (0,0,0,52) | 0.37 | 0.42 |

*(`Mannar`'s and `Vavuniya`'s validation MASE above reflect the Decision 017
explosive-AR-root fix - both improved slightly once their one pathological
fold each was correctly excluded as a failed fit rather than scored on a
wildly divergent finite forecast. Every other district's numbers are
unaffected by that fix.)*

Full detail (RMSE/MAE/sMAPE, both candidates' MASE, Ljung-Box results) in
`models/module1/sarima_selected_configs.csv` and `outputs/metrics/module1/
sarima_walk_forward_metrics.csv`. Summary: **17/25 districts use `log1p`**,
8 use raw counts; **13/25 beat the seasonal-naive benchmark** on validation
(MASE < 1), 18/25 do on the holdout block; **18/25 selected configs have NO
seasonal AR/I/MA component at all** (`seasonal_order=(0,0,0,52)`) despite
`m=52` - see Open Question #12 (new) for why, and its implications.

### Implementation choices made (not explicit in the plan/spec)

1. **Aggregation across folds uses the median**, not the mean, of each
   metric (RMSE/MAE/sMAPE/MASE) - consistent with how `aggregate_mase`
   already had to be defined for candidate selection, and more robust to
   the occasional very-bad fold than a mean would be.
2. **Pooled Ljung-Box/ACF residuals** are the winning candidate's
   validation-fold residuals concatenated in chronological fold order
   (folds are non-overlapping and already generated in ascending order, so
   simple list concatenation is chronologically correct without extra
   sorting), with `is_imputed` rows and any failed-fit `NaN`s excluded.
3. **Metrics CSV mixes per-fold, aggregate, and holdout rows** in one file
   (`fold_id` is an int for validation folds, the string `"aggregate"` for
   the per-district aggregate row, and `"holdout"` for the holdout row) -
   simpler than three separate files, distinguished by the `split` column.

---

## Stage 2 Implementation Status (2026-07-27 - XGBoost Compensation Model Built; numbers below refreshed same day after the Decision 017 Stage 1 fix)

`src/module1_forecasting/compensation_model.py`, `combine.py`, and the
`dm_test()`/`ljung_box_diagnostics()` additions to `evaluate.py` are
implemented and have been run end to end against all 25 districts
(`python -m src.module1_forecasting.main`, ~1 minute combined wall time for
Stage 2 + combine - CPU-only, no GPU needed at this data scale; see Stage 1's
~82-minute `auto_arima` cost for contrast). Outputs:

- `data/processed/module1/xgboost_stage2_predictions.csv` (20,800 rows):
  `District, Year, Week, split, fold_id, Number_of_Cases, is_imputed,
  sarima_prediction, residual, predicted_residual, stage2_trained`.
- `models/module1/xgboost_folds/` (14 per-fold + 1 holdout model artifact)
  and `models/module1/xgboost_final_model.json` (trained on all available
  out-of-sample residuals - folds 1-14 + holdout - for potential future live
  use; not used for any reported metric).
- `outputs/metrics/module1/xgboost_feature_importance.csv` (gain-based, from
  the final production model).
- `outputs/metrics/module1/xgboost_stage2_metrics.csv`: RMSE/MAE/sMAPE of
  `predicted_residual` vs actual `residual` (a residual-prediction-quality
  diagnostic; MASE intentionally omitted here - its seasonal-naive scale
  doesn't have a clean meaning for a pooled residual-of-a-residual task; see
  the module docstring).
- `data/processed/module1/final_combined_predictions.csv` (20,800 rows):
  adds `final_prediction = sarima_prediction + predicted_residual` (clipped
  to a 0 floor) and `final_residual = Number_of_Cases - final_prediction`.
- `outputs/metrics/module1/combined_vs_baseline_metrics.csv` (800 rows =
  25 districts x 2 models x (14 folds + `validation_aggregate` + `holdout`)):
  RMSE/MAE/sMAPE/MASE for both `stage1_only` and `stage1_plus_stage2`, plus
  `residual_variance_reduction`/`ljung_box_*` columns on each district's
  `stage1_plus_stage2` `validation_aggregate` row.
- `outputs/metrics/module1/diebold_mariano_results.csv` (50 rows = 25
  districts x 2 scopes): `dm_stat, p_value, mean_loss_diff, n_obs`.
- `outputs/figures/module1/acf_residuals_final_{Colombo,Kandy,Mullaitivu,
  Kilinochchi}.png`: same representative-subset ACF diagnostic, now on the
  final combined residual.

### Design decisions approved before implementation (see Decisions 014-016 for full detail)

1. **Pooled XGBoost** (all 25 districts, `District` as a categorical
   feature) per walk-forward fold, not per-district - too little per-fold
   data for 25 independent models in early folds.
2. **`residual_lag_1/2`** built via full-calendar reindex + shift, not a
   naive shift on the sparse validation+holdout rows - required to correctly
   handle a real ~26-week per-district gap between fold 14 and the holdout
   block (Decision 015).
3. **Stage 2 reuses Stage 1's exact 14 folds** (via `fold_id`/`split` already
   in `sarima_stage1_predictions.csv`). Fold *k* trains on pooled,
   non-imputed folds `1..k-1`; fold 1 is a documented no-op
   (`predicted_residual = 0`).
4. **Rainfall column switched to `precipitation_sum (mm)`** before Stage 2
   was built (Decision 008, resolved).
5. **Evaluation framework**: RMSE/MAE/sMAPE/MASE (per fold + median
   aggregate + holdout) plus DM test, residual variance reduction, and a
   final Ljung-Box check (Decision 016) - all reported per district.
6. **`main.py` orchestrates idempotently**: each stage skipped if its output
   file already exists, `--force` reruns, `--stages` runs a subset.

### Mid-implementation finding and fix: pooled squared-error loss is not robust to a single district's SARIMA divergence

The first full run used the standard `objective="reg:squarederror"` and
produced a deeply suspicious result: **23/25 districts got worse** (higher
RMSE and MASE) with Stage 2 than without - e.g. Colombo's RMSE rose from
162.8 to 274.0. Root cause: `Vavuniya`'s Stage 1 SARIMA diverged in one
walk-forward fold (2010, weeks 42-51), forecasting up to ~30 million
cases/week against an actual mean of ~6/week - a residual of roughly
-30,000,000. Because Stage 2 pools every district's residuals into one
squared-error-loss model, this single extreme value dominated training
globally, corrupting predicted residuals for every other district too (e.g.
Colombo's, which should be O(100), were being predicted at O(1,000,000)).
Switching to `objective="reg:absoluteerror"` (MAE - bounded gradient,
immune to any single outlier's magnitude) fixed this immediately: 24/25
districts improved. See Decision 014 for full detail.

### Follow-up fix: the Vavuniya/Mannar divergence itself (Decision 017)

The MAE-loss fix above only *contained* the symptom (stopped one district's
divergence from corrupting every other district's Stage 2 correction) - it
did not fix Stage 1 itself, and `Vavuniya`'s own numbers still carried the
scar of that one catastrophic fold. Root-caused and fixed same day (Decision
017): `enforce_stationarity=False` let the fold-1 refit land on a
non-stationary/explosive AR root; a full 25-district scan found a second,
independent case (`Mannar`, 2022 fold-13, explosive seasonal AR root).
`baseline_sarima.fit_and_forecast()` now detects and rejects any fit whose
AR polynomial has a root on or inside the unit circle, and the full Stage 1
→ Stage 2 → combine pipeline was regenerated. **All results below reflect
the post-fix numbers.**

### Per-district results (validation = median across 14 walk-forward folds; holdout = single final 104-week block)

| District | Stage 1 MASE (val) | Stage 1+2 MASE (val) | % improvement (val) | Stage 1 MASE (holdout) | Stage 1+2 MASE (holdout) | % improvement (holdout) |
|---|---|---|---|---|---|---|
| Ampara | 0.97 | 0.62 | 35.7% | 0.43 | 0.27 | 36.3% |
| Anuradhapura | 0.79 | 0.46 | 42.0% | 0.53 | 0.38 | 28.7% |
| Badulla | 1.36 | 0.72 | 46.6% | 0.55 | 0.33 | 39.5% |
| Batticaloa | 1.92 | 0.66 | 65.5% | 0.59 | 0.25 | 56.9% |
| Colombo | 1.63 | 0.84 | 48.2% | 0.65 | 0.32 | 50.6% |
| Galle | 1.21 | 0.64 | 46.6% | 1.17 | 0.51 | 56.1% |
| Gampaha | 1.05 | 0.63 | 40.6% | 0.74 | 0.35 | 52.1% |
| Hambantota | 0.96 | 0.50 | 48.1% | 0.95 | 0.50 | 47.5% |
| Jaffna | 2.22 | 0.79 | 64.3% | 0.32 | 0.16 | 48.9% |
| Kalutara | 1.42 | 0.78 | 44.9% | 0.66 | 0.45 | 32.7% |
| Kandy | 1.27 | 0.58 | 54.3% | 0.43 | 0.29 | 31.2% |
| Kegalle | 0.59 | 0.39 | 34.0% | 0.33 | 0.26 | 22.1% |
| Kilinochchi | 1.45 | 1.37 | 5.3% | 2.15 | 2.41 | **-11.7%** |
| Kurunegala | 0.86 | 0.35 | 59.0% | 0.38 | 0.27 | 28.5% |
| Mannar | 0.81 | 0.61 | 24.4% | 1.12 | 1.15 | **-3.0%** |
| Matale | 0.84 | 0.42 | 50.3% | 1.28 | 1.02 | 20.5% |
| Matara | 0.94 | 0.39 | 59.1% | 1.45 | 0.62 | 57.0% |
| Monaragala | 0.63 | 0.54 | 14.6% | 0.62 | 0.51 | 17.5% |
| Mullaitivu | 2.92 | 2.42 | 17.1% | 0.53 | 0.45 | 16.2% |
| Nuwara Eliya | 0.93 | 0.59 | 36.9% | 1.37 | 1.02 | 25.4% |
| Polonnaruwa | 1.04 | 0.71 | 31.9% | 0.78 | 0.58 | 26.2% |
| Puttalam | 0.89 | 0.52 | 40.9% | 0.31 | 0.18 | 41.9% |
| Ratnapura | 0.90 | 0.51 | 43.5% | 1.11 | 0.48 | 57.0% |
| Trincomalee | 1.04 | 0.57 | 44.9% | 0.41 | 0.19 | 53.6% |
| Vavuniya | 0.37 | 0.29 | 23.7% | 0.42 | 0.37 | 10.3% |

**25/25 districts improve on validation-aggregate MASE** (up from 24/25
pre-fix - `Kilinochchi` flipped from -9.4% to +5.3%). **23/25 districts
improve on holdout MASE** - `Kilinochchi` (-11.7%, worse than pre-fix's
-4.5%) and `Mannar` (-3.0%, newly negative - it wasn't a holdout exception
before this fix) are the two exceptions, though neither's DM test reaches
significance (see below). Median % improvement across all 25 districts:
**43.5% validation-aggregate, 32.7% holdout**. Median among districts that
improved on that split: 43.5% validation-aggregate (all 25), 36.3% holdout
(23/25).

Full detail (RMSE/MAE/sMAPE, DM test, residual variance reduction,
Ljung-Box): `outputs/metrics/module1/combined_vs_baseline_metrics.csv`,
`outputs/metrics/module1/diebold_mariano_results.csv`.

### Statistical significance (Diebold-Mariano test)

At the `validation_and_holdout` scope (larger pooled sample per district),
**14/25 districts** reach `p < 0.05` (Stage 2 significantly better):
`Badulla, Batticaloa, Colombo, Galle, Gampaha, Hambantota, Jaffna, Kalutara,
Kandy, Kurunegala, Matara, Nuwara Eliya, Polonnaruwa, Puttalam`. At the
stricter `holdout_only` scope (n=104/district, the genuinely-never-touched-
until-now test block), **5/25** reach significance: `Badulla, Batticaloa,
Gampaha, Kandy, Puttalam`. **No district shows a statistically significant
worsening at either scope** (including `Kilinochchi` and `Mannar`, whose
directional holdout worsening does not reach significance - `p ≈ 0.33`-`0.40`
for both). This is an honest, expected outcome given per-district sample
sizes (728 validation + 104 holdout observations) - directionally
consistent, positive, but not universally significant.

*(Note: while re-verifying these numbers, a sign-convention bug was found
and fixed in `evaluate.dm_test`'s docstring - it previously described
`mean_loss_diff < 0` as "Stage 2 helped", which is backwards relative to the
actual `d = g1 - g2` computation; `mean_loss_diff > 0` is what indicates
Stage 2 helped. The numbers reported here and in Decision 016 were already
computed with the correct sign in code, only the prose explanation was
wrong - now corrected in `evaluate.py`.)*

### Residual variance reduction and final Ljung-Box check

22/25 districts show positive residual variance reduction (Stage 2 reduces
the spread of unexplained error, up to 81% for `Trincomalee`). 3 districts
show negative reduction: `Kilinochchi` (-0.27), `Mannar` (-0.18), `Mullaitivu`
(-0.14) - notably, `Mullaitivu` *still* improved substantially on MASE
(17.1% validation / 16.2% holdout), illustrating that variance reduction (a
squared-error-scale diagnostic) and MASE (an absolute-error-scale accuracy
metric) can disagree - a few large corrections can improve typical-case
accuracy while occasionally overshooting on specific weeks. `Vavuniya`'s
variance reduction is no longer a special case post-fix (its own explosive
fold no longer contaminates its residual series at all, unlike before when
the MAE-robust Stage 2 model deliberately declined to chase Stage 1's
~-30,000,000 outlier residual, leaving `Vavuniya`'s reported variance
reduction near zero).

The final Ljung-Box check (lags 26/52, pooled non-imputed validation
residuals) shows **23/25 districts still have statistically significant
residual autocorrelation** (`p < 0.05` at lag 26) even after Stage 2 - only
`Ampara` and `Vavuniya` pass (note: `Vavuniya` newly joins the passing set
post-fix, replacing `Anuradhapura` from the pre-fix run). This is an
important, honest limitation: Stage 2 substantially reduces error
*magnitude* (MASE, RMSE) for most districts but does **not** fully whiten
the residual - real, exploitable structure likely still remains (candidate
future work: additional residual lags beyond `residual_lag_1/2`, or a
fundamentally different Stage 2 architecture/feature set).

### Top Stage 2 features (gain-based importance, final production model)

`residual_lag_1` and `residual_lag_2` dominate (486 and 297 total gain
respectively - by far the two most important features), followed by
`rolling_mean_cases_4w` (79), `cases_lag_3` (78), `cases_lag_1` (72),
`rolling_std_cases_4w` (52), `cases_lag_4` (50), then climate-lag and
seasonal features (`rainfall_lag_5`, `cos_week`, `sarima_prediction`
itself). This is intuitive: the previous 1-2 weeks' own out-of-sample SARIMA
error is the single strongest predictor of the current week's error - i.e.
Stage 1's error is itself autocorrelated (consistent with the Ljung-Box
finding above), and Stage 2's residual-lag features are what's actually
being exploited to capture that.

### Real-world check against the ongoing 2026 Colombo/Gampaha outbreak (2026-07-27)

See Open Question #16 for the full analysis. Headline: the dataset already
extends to 2026 week 25, which includes the actual outbreak spike (Colombo
1,138 cases, Gampaha 1,294 cases) inside the untouched holdout block.
Stage 1+2 achieves a genuinely useful sMAPE of 14-24% across every period
checked where climate data is complete, but the **shared climate pipeline
has not been refreshed past week 21** while case data reaches week 25,
leaving Stage 2 blind (all climate features `NaN`) for exactly the weeks
containing the spike - sMAPE for those 4 weeks alone is ~97% for both
districts. This is flagged as an actionable data-currency gap, not a
Stage 1/2 modeling deficiency - re-running the climate ETL is a prerequisite
before drawing further conclusions about real-time outbreak-tracking
accuracy.

### Implementation choices made (not explicit in the plan/spec)

1. **`objective="reg:absoluteerror"` (MAE), not squared error** - a
   robustness requirement discovered during implementation, not an original
   design choice. See "Mid-implementation finding and fix" above and
   Decision 014.
2. **Stage-2-own metrics deliberately omit MASE** (`xgboost_stage2_metrics.csv`
   reports only RMSE/MAE/sMAPE of `predicted_residual` vs `residual`) - MASE's
   seasonal-naive scale doesn't have a clean meaning for a pooled
   residual-of-a-residual prediction task. The primary, decision-relevant
   evaluation (accuracy against actual case counts, including MASE) lives in
   `combined_vs_baseline_metrics.csv` instead.
3. **Early stopping uses a two-pass fit**: probe-fit with the single most
   recent prior fold held out as an internal validation slice to find a
   sensible tree count via early stopping, then refit on all available prior
   folds (including that slice) with the resulting fixed tree count - uses
   all available training data for the model actually used to predict, while
   still adaptively choosing model complexity.
4. **`final_prediction` clipped to a 0 floor** (`combine.py`), mirroring
   Stage 1's own design decision 2 - adding a negative `predicted_residual`
   can push an already-small SARIMA forecast below zero, which is not a
   valid case count.

---

## Forward Production Forecast (2026-07-27)

`src/module1_forecasting/forecast_future.py` (new) answers a question none
of the above sections do: "what does the trained pipeline predict for weeks
that don't exist in the dataset at all yet?" - as opposed to walk-forward
validation and the holdout block, which only ever score against data that IS
in the dataset, just held back from training/selection. There is **no
ground truth** for these numbers, so they are evidence of a different
(lower) kind than the holdout MASE/DM-test results above and must never be
cited as if they were.

### Method
1. **Stage 1**: each district's already-selected `(order, seasonal_order,
   use_log1p)` is refit on its ENTIRE available history (not a pre-holdout
   window), then forecast 8 weeks beyond the last available case-count week
   in one deterministic multi-step call - unchanged `fit_and_forecast()`.
2. **Stage 2**: the existing final production XGBoost model
   (`xgboost_final_model.json`) is applied **recursively**, one future week
   at a time. For the first 1-2 future weeks, `residual_lag_1/2` and
   case-count lags use real historical values; every week after that, the
   script's own prior-step `final_prediction`/`predicted_residual` are fed
   back in as if they were the real outcome (standard recursive multi-step
   forecasting - errors can compound with horizon).
3. **Climate features are `NaN` for every future week** - climate data
   doesn't extend past the last case-count week either (Open Question #16),
   so every climate-derived feature (raw anomalies, and any lag reaching
   into the missing range) is missing by construction. XGBoost's native
   missing-value handling copes numerically; this is a real information
   loss, not a bug.
4. **Honesty mechanism**: `feature_completeness_pct` (share of non-`District`
   features that are non-`NaN`) is reported per output row, declining with
   horizon, rather than presenting every forecasted week as equally reliable.

### Results (8-week horizon, 2026 weeks 26-33)
`feature_completeness_pct` declines from 56.2% (week 1 of the horizon) to
43.8% (weeks 5-8, where it flattens once both residual lags are fully
recursive). For the two districts in the real, ongoing outbreak:
- `Colombo`: rises from the pre-spike ~300-500/week baseline to 442.7 (wk26),
  peaks at 524.8 (wk27), settles to a ~460-470/week plateau (wk28-33) - well
  above baseline but well below the week-25 spike (1,138) itself.
- `Gampaha`: rises from ~200-500/week to 1,087.7 (wk26), peaks at 1,465.9
  (wk27), settles to a ~1,360-1,370/week plateau (wk28-33) - also well above
  baseline, closer to (but not simply repeating) the week-25 spike (1,294).

Both districts show a suspicious week-24 dip (`Colombo` 20, `Gampaha` 24
cases) immediately before the week-25 spike, consistent with Open Question
#16's flagged reporting-lag-catchup hypothesis - the forecast's
plateau-rather-than-repeat-the-spike shape is consistent with (but does not
prove) the model correctly discounting a possibly-artifactual single-week
outlier.

Full output: `data/processed/module1/future_forecast.csv` (200 rows = 25
districts x 8 weeks: `sarima_prediction`, `predicted_residual`,
`final_prediction`, `feature_completeness_pct`,
`residual_lag_{1,2}_is_recursive`). Illustrative plots:
`outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`.

### Status
Kept as a separate, clearly-labeled deliverable (see Decision 018) - not
merged into `main.py`'s validated walk-forward/holdout orchestration, since
it answers a fundamentally different question at a fundamentally different
evidence standard. **Module 1 outputs now also feed Module 2 forward operational
risk** (`forecast_future_risk.py`, Decision 027) — not training/evaluation.
Climate refresh via `scripts/fetch_open_meteo_weather.py` (Decision 027).
Rolling 1-week-ahead re-evaluation remains an open higher-rigor follow-up.

---

## Supervisor Flag: Non-Seasonal SARIMA (2026-07-29)

**Status:** Documented limitation — no Stage 1 rework planned.

**Finding:** 18/25 districts selected `seasonal_order=(0,0,0,52)` despite `m=52`. Stage 1 alone underperforms seasonal naive for 12/25 districts (validation MASE > 1).

**Why not fixed:** Stage 2 diagnostic (Open Question #12, M1-002) showed non-seasonal districts benefit *more* from compensation, not less. Combined pipeline: 25/25 validation MASE improvement, 23/25 holdout improvement.

**Thesis framing:** Present Stage 1 as an intentionally simple univariate baseline; the research contribution is residual compensation, not optimal SARIMA order selection. Do not claim Stage 1 alone is a strong forecaster for all districts.

**Deferred follow-ups (accepted, not blocking Module 1 completion):** climate data currency refresh, rolling 1-week-ahead evaluation, STL+SARIMA ablation, extra residual lags, rainfall lag-window ablation, holdout-vs-validation divergence investigation. See team discussion 2026-07-29 — thesis scope is validated backtest of the compensation framework, not operational deployment certification.

---

## Documentation Rule

Update this file when Module 1 architecture, features, decisions, or evaluation method changes.
