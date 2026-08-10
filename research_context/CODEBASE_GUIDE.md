# Codebase Guide — "How Does That Happen?" Reference

## Purpose

This is a **code-navigation reference**, not report content. It exists so that when someone —
a teammate, a supervisor, or an evaluator — asks "how exactly does X happen in the code," you
can point at an exact file and function within seconds, instead of searching live during a
defense.

It covers the **whole repository**: shared preprocessing, all three modules, the dashboard, and
the research/ablation scripts. It does not replace `EVALUATION_STUDY_PLAN_MODULE{1,2,3}.md`
(which cover *why* decisions were made and *what* the results are) — this file covers *where in
the code* each behavior lives.

**Line numbers below are approximate**, taken from a full read of each file at the time this
guide was built. If the code has changed since, use them as a strong starting point (search the
named function) rather than an exact address — a function that has moved 10-20 lines is still
easy to find once you know its name and which file it's in.

**How to use this:**
1. Read `PART 1` first, organized by topic — this is the quick-lookup index. Find your question
   or something close to it, and you get a file + function name to point at.
2. If you need more context on a whole file (not just one function), jump to `PART 2` — a
   file-by-file reference organized the same way the pipeline actually runs (shared →
   Module 1 → Module 2 → Module 3 → dashboard → research scripts).
3. `PART 3` is a flat index of the ~30 one-off research/ablation scripts, mapped to their
   experiment IDs — use it when someone asks "where's the code for M1-007" or similar.

---

# PART 1 — Quick-Lookup Index, by Topic

## A. Configuration & Shared Constants

- **Where is the 25-district list (post-Kalmunai-merge) actually defined?** → `src/config.py`,
  `DISTRICTS` list, ~line 199.
- **How are ablation runs (log-residual mode, feature variants) kept from overwriting production
  CSV/model artifacts?** → `src/config.py`, `module1_stage2_paths()` (~line 114) /
  `module2_stage1_paths()` (~line 295) / `module2_stage2_paths()` (~line 318) — all switch to a
  `_<suffix>`-named path for any non-default mode/variant.
- **What determines the forecast horizon used consistently across Module 1 and Module 2?** →
  `src/config.py`, `FORECAST_HORIZON_WEEKS = 8`, ~line 334.
- **Where is the outbreak-label threshold constant (`k`, harmonics, min prior years) defined, and
  why `k=3.0`?** → `src/config.py`, `EPIDEMIC_THRESHOLD_K` etc., ~lines 213-234 (comment cites
  Decision 025).
- **Why does Module 2's Stage 1 use `min_train_years=4` instead of Module 1's default of 3?** →
  `src/config.py`, `MODULE2_MIN_TRAIN_YEARS = 4`, ~lines 236-247.
- **Is there a shared helper for creating output directories?** → `src/utils.py`, `ensure_dir()`,
  line 6 (note: many other files call `.mkdir(parents=True, exist_ok=True)` directly instead).

## B. Shared Preprocessing (raw data → the four shared base tables, Decision 013)

- **How is the "master" epi-week calendar date pair chosen when districts disagree?** →
  `src/preprocessing/shared.py`, `build_epi_week_calendar()` (~line 127) — per-(Year,Week)
  majority vote across all raw district rows, deterministic earliest-date tie-break.
- **How is Kalmunai's case data folded into Ampara?** → `shared.py`,
  `merge_kalmunai_into_ampara()` (~line 90) — groupby-sum, only sums rows that actually exist,
  nothing fabricated.
- **How are nationwide scrape-gap weeks (e.g. 2020 Wk1) given a calendar date without being
  fabricated arbitrarily?** → `shared.py`, `fill_isolated_calendar_gaps()` (~line 258) — only
  fills unambiguous single-week 8-day gaps; ambiguous/multi-week gaps are left unfilled and
  logged.
- **Is daily weather assigned to an epi-week by its own raw date, or by the master calendar?** →
  `shared.py`, `aggregate_climate_weekly()` (~line 398), via `_build_day_to_week_lookup(calendar)`
  (~line 345) — the master calendar, not each row's own (sometimes wobbly) date.
- **Why is rainfall summed weekly while temperature/humidity are averaged, and how is the
  categorical `weather_code` collapsed?** → `shared.py`, `CLIMATE_SUM_COLUMNS` /
  `CLIMATE_MEAN_COLUMNS` / `CLIMATE_MODE_COLUMN` constants (~lines 59-71), applied inside
  `aggregate_climate_weekly()`.
- **How is population interpolated/extrapolated, and which districts are flagged
  lower-confidence?** → `shared.py`, `interpolate_population()` (~line 453) — linear
  interpolation 2001-2024, linear extrapolation 2025-2026, flags Kilinochchi/Mullaitivu/Mannar.
- **Where does the systematic per-week date-mislabeling check live?** → `shared.py`,
  `find_calendar_chronology_issues()` (~line 209).

## C. Module 1 — Preprocessing & Reporting-Anomaly Detection

- **How exactly is a missing week's case count imputed?** →
  `src/preprocessing/module1_preprocessing.py`, `impute_missing_weeks()` (~line 161) —
  seasonal-naive mean across other years, same (District, Week).
- **How are 53-week years handled so every district-year has exactly 52 rows?** →
  `module1_preprocessing.py`, `merge_week_53_into_52()` / `merge_week_53_cases()` /
  `merge_week_53_climate()` (~lines 81-130), for years `[2009, 2016, 2019, 2021]`.
- **Why aren't the first/last years in the dataset checked for missing weeks?** →
  `module1_preprocessing.py`, `find_missing_weeks()` (~line 137) — excludes `min_year`/`max_year`
  as natural partial-year boundaries.
- **What guarantees are checked before the weekly modeling table is written to disk?** →
  `module1_preprocessing.py`, `validate_weekly_modeling_table()` (~line 262).
- **How is a suspected reporting-delay week distinguished from a genuine outbreak collapse?** →
  `src/preprocessing/reporting_anomalies.py`, `flag_reporting_anomalies()` (~line 33) — drop
  ratio + rebound pattern.
- **Why can't the rebound-confirmed anomaly flag be used in a live forecast, and what's the
  real-time-safe alternative?** → `reporting_anomalies.py`, `flag_reporting_dip_causal()` (~line
  89) — no future rebound needed, usable at prediction time (this is the "causal detector" from
  Decision 043/M1-019).
- **How are case-derived lag/rolling features stopped from consuming an imputed or
  reporting-anomaly value?** → `reporting_anomalies.py`, `mask_untrusted_cases()` (~line 142).
- **How is "weeks since the last suspected reporting anomaly" computed and capped?** →
  `reporting_anomalies.py`, `compute_reporting_delay_features()` (~line 162), cap constant
  `WEEKS_SINCE_REPORTING_ANOMALY_CAP` ~line 153.

## D. Module 1 — Validation Harness & Feature Engineering

- **Where does the walk-forward fold boundary get enforced so a fold can't see future data?** →
  `src/module1_forecasting/validation.py`, `fit_window()` (~line 60) — the only sanctioned way
  to materialize a training slice.
- **How many weeks are reserved as the untouched holdout, and how is it guaranteed never to leak
  into a fold?** → `validation.py`, `get_holdout_series()` (~line 73, `DEFAULT_HOLDOUT_YEARS=2`
  = 104 weeks) and `generate_walk_forward_folds()` (~lines 91-135) computing `usable_n = n -
  holdout_size` before generating any fold.
- **What's the minimum training window before the first fold, and why?** → `validation.py`,
  `DEFAULT_MIN_TRAIN_YEARS=3` (~line 39) — one seasonal cycle minimum for SARIMA.
- **Why must climate anomalies be recomputed per walk-forward fold instead of once globally?** →
  `src/module1_forecasting/feature_engineering.py`, `compute_fold_climate_anomalies()` (~line
  175) — uses only that fold's training-window mean as the "normal" baseline.
- **How does the model avoid leaking the current week's own case count into its own rolling
  mean/std feature?** → `feature_engineering.py`, `build_fold_agnostic_features()` (~line 90) —
  `.shift(1)` applied before `.rolling(...)`.
- **How is `cases_lag_1` corrected when the prior week was a suspected reporting anomaly (the
  M1-006B nowcast fix)?** → `feature_engineering.py`, the `apply_nowcast_lag1` block (~lines
  134-145) — substitutes `max(cases_lag_2, rolling_mean_cases_4w)`.
- **Why `precipitation_sum` instead of `rain_sum`?** → `feature_engineering.py`, comment block
  ~lines 63-72 (Decision 008).

## E. Module 1 — Stage 1 (SARIMA Baseline)

- **Why is SARIMA order search run once on full history rather than per fold — doesn't that
  leak future data?** → `src/module1_forecasting/baseline_sarima.py`, module docstring decision
  1 (~lines 13-23) — only the *order* is fixed this way; every fold still refits fresh
  *parameters* on its own training window via `fit_and_forecast()`.
- **How was the explosive/non-stationary SARIMA bug (Vavuniya 2010, Mannar 2022) found and
  fixed?** → `baseline_sarima.py`, `_has_explosive_ar_root()` (~line 207), used inside
  `fit_and_forecast()` (~line 225) — Decision 017.
- **How is raw-count vs. `log1p` transform chosen per district?** → `baseline_sarima.py`,
  `select_winning_candidate()` (~line 406), fed by `validate_candidate()` (~line 317)'s median
  walk-forward MASE.
- **Are SARIMA forecasts ever allowed to go negative?** → No — `fit_and_forecast()` (~line 309)
  unconditionally clips to a 0 floor.
- **Is the holdout block ever used to revise the chosen SARIMA order?** → No —
  `forecast_holdout()` (~lines 423-479) is a one-time report only (Decision 009).
- **Where do the ACF residual diagnostic plots get generated?** → `baseline_sarima.py`,
  `plot_acf_diagnostics()` (~line 527), for the 4 representative districts in
  `ACF_DIAGNOSTIC_DISTRICTS`.

## E2. Module 1 — Alternative Stage 1 Pilot (not in production)

- **Why was STL+ARIMA tried as an alternative to plain SARIMA?** →
  `src/module1_forecasting/stl_arima.py`, module docstring (~lines 1-10) — 18/25 districts had
  `seasonal_order=(0,0,0,52)`.
- **Does this pilot ever run as part of the production pipeline?** → No —
  `stl_arima.py` is explicitly not wired into `main.py` (module docstring ~lines 19-22); the
  actual pilot driver is `scripts/pilot_stl_arima.py` (M1-012).

## F. Module 1 — Stage 2 (XGBoost) & Combination

- **What exactly is the Stage 2 training target?** →
  `src/module1_forecasting/residual_transform.py`, `compute_stage2_target()` (~line 29) —
  additive: `actual - sarima_pred`; log mode (M1-006A, rejected): log1p difference.
- **Why is Stage 2 a single pooled model across all 25 districts instead of 25 separate
  models?** → `src/module1_forecasting/compensation_model.py`, module docstring point 1
  (~lines 7-14) — per-district data too thin in early folds; `District` used as a categorical
  feature.
- **How is the ~26-week gap between fold 14's validation end and the holdout start handled in
  `residual_lag_1/2` so a stale value isn't used?** → `compensation_model.py`,
  `build_residual_lags()` (~line 305) — reindexes onto the full weekly calendar before
  `shift(1)/shift(2)` (Decision 015).
- **Why does Stage 2 use MAE loss instead of squared error?** → `compensation_model.py`,
  `XGB_BASE_PARAMS` comment (~lines 165-189) — one extreme SARIMA-divergence residual (Vavuniya)
  dominated a squared-error pooled fit and corrupted every other district's correction.
- **What happens for fold 1, which has no prior residual history?** → `compensation_model.py`,
  `train_and_predict_fold()` (~line 469) — documented no-op, `predicted_residual=0.0`.
- **How does the M1-021 per-district alternative path work, and what data-sufficiency rule does
  it use?** → `compensation_model.py`, `_fit_one_district()` (~line 546) —
  `MIN_TRAINABLE_ROWS_PER_DISTRICT=104`, `MIN_ROWS_FOR_EARLY_STOPPING_PER_DISTRICT=208`.
- **What is the exact final-forecast formula, and how does per-district shrinkage plug in?** →
  `src/module1_forecasting/combine.py`, `build_final_predictions()` (~line 85), calling
  `residual_transform.combine_stage2_forecast()` (~line 43).
- **How is it verified Stage 2 actually helps and not just by chance?** → `combine.py`,
  `compute_dm_results()` (~line 262), calling `evaluate.dm_test()`.
- **How is Stage 2's benefit quantified beyond point metrics (did it reduce error *spread*)?** →
  `combine.py`, `residual_variance_reduction()` (~line 244).
- **Why is `apply_shrinkage=True` blocked unless a `feature_variant` is also given?** →
  `combine.py`, explicit guard in `run_combine_pipeline()` (~lines 335-339) — prevents silently
  overwriting production `combined_metrics.csv`.
- **How is a per-district shrinkage weight selected without touching the holdout during
  selection?** → `src/module1_forecasting/shrinkage.py`, `select_shrinkage_weights()` (~line 88)
  — validation-folds-only grid search over `w ∈ {0.0, 0.25, 0.5, 0.75, 1.0}`.
- **How does the holdout get used for shrinkage without violating "untouched until final
  reporting"?** → `shrinkage.py`, `evaluate_shrinkage_on_holdout()` (~line 195) — confirms or
  reverts a pre-selected weight, never re-searches on holdout.

## G. Module 1 — Evaluation Metrics & Diagnostics

- **Why is MASE preferred over sMAPE as the primary selection metric given zero-inflation?** →
  `src/module1_forecasting/evaluate.py`, `mase()` docstring (~lines 96-101) — doesn't saturate at
  0/200% when both sides are near zero.
- **How exactly is statistical significance of Stage 2's improvement computed?** →
  `evaluate.py`, `dm_test()` (~line 172) — Diebold-Mariano with Newey-West/Bartlett HAC variance
  + Harvey-Leybourne-Newbold small-sample correction.
- **Why does MASE's scale denominator come from the training window, not the evaluation
  window?** → `evaluate.py`, `mase()` docstring (~lines 104-107).
- **How are NaN predictions (e.g. a failed SARIMA fit) stopped from silently counting as a
  zero-error observation?** → `evaluate.py`, `_apply_mask()` (~line 28).

## H. Module 1 — Forward Forecast, Nowcast, Rolling Evaluation (operational, not backtest)

- **How does the 8-week forward forecast avoid needing real future case counts for its Stage 2
  features?** → `src/module1_forecasting/forecast_future.py`, `forecast_district()`'s recursive
  self-feeding loop (~lines 353-424) — own prior predictions fed back in as if real after the
  first 1-2 weeks.
- **What exactly is the vintage-ensembled nowcast, and how many independent SARIMA fits does it
  average?** → `forecast_future.py`, `_collect_vintage_forecasts()` (~line 179) /
  `_ensembled_next_week_sarima()` (~line 259); `MODULE1_NOWCAST_ENSEMBLE_WINDOW=4`
  (`src/config.py`).
- **How is a forecast row's declining confidence at longer horizons actually surfaced?** →
  `forecast_future.py`, `feature_completeness_pct` and `residual_lag_{1,2}_is_recursive` columns
  (~lines 405, 421-422).
- **Is `run_nowcast()` a true single-step forecast or an approximation?** → Genuine, zero
  recursion at `horizon_step==1` — `forecast_future.py`, module docstring ~lines 52-61.
- **What SARIMA refit strategies were tried in the rolling evaluator, and how do they differ?**
  → `src/module1_forecasting/rolling_one_step.py`: `_low_freq_refit_step()` (~line 106, M1-014,
  refits only every N weeks) vs. `_vintage_ensemble_step()` (~line 181, M1-015, averages several
  independently-fitted vintages) vs. inline `warm_start` (M1-013, ~lines 369-381) — mutually
  exclusive.
- **Why does `combine.py`'s DM test only reach significance for 5/25 districts, and how was that
  investigated?** → `rolling_one_step.py`, module docstring (~lines 18-23) and
  `compute_dm_results_rolling()` (~line 499) — a much larger out-of-sample sample from rolling
  scoring than the 104-week holdout.
- **Since the nowcast predicts genuinely future weeks with no ground truth yet, how is its
  accuracy ever validated?** → `src/module1_forecasting/nowcast_tracking.py`,
  `reconcile_nowcast_log()` (~line 90) — waits for real data to arrive, then joins; never
  fabricates a result for an unresolved week.
- **What's the exact end-to-end Module 1 pipeline order, and how does it avoid re-running the
  ~82-minute SARIMA stage unnecessarily?** → `src/module1_forecasting/main.py`,
  `PIPELINE_STAGES` (~line 80) + `run_pipeline()`'s skip-if-exists logic (~lines 92-118).

## I. Module 2 — Preprocessing & Labels

- **Why does Module 2 keep epi-week 53 as its own week instead of merging it like Module 1?** →
  `src/preprocessing/module2_preprocessing.py`, module docstring point 1; `WEEK_53_YEARS`.
- **How exactly is the outbreak label's historical mean/SD computed without leaking future
  years?** → `src/module2_classification/labels.py`, `compute_historical_stats_harmonic()`
  (~line 127) — per-district, per-year expanding harmonic regression fit on strictly-prior real
  years (the OFFICIAL estimator, Decision 025).
- **What's the exact threshold formula, and what does `k` control?** → `labels.py`,
  `compute_epidemic_threshold_labels()` (~line 205) — `threshold = historical_mean + k *
  historical_sd`.
- **Under what condition is a row's label left undefined (NaN) rather than 0?** → `labels.py`,
  ~lines 229-233 — insufficient prior years, or `is_imputed=True`.
- **What was the superseded label estimator, and why was it replaced?** → `labels.py`,
  `compute_historical_stats()` (~line 75, SUPERSEDED, kept for audit) — see module docstring for
  the Decision 025 rationale (noisy exact-per-week estimates).

## J. Module 2 — Feature Engineering

- **Why are climate anomaly features computed per fold while case-anomaly lags are computed
  once globally — aren't both "anomalies"?** → `src/module2_classification/feature_engineering.py`,
  module docstring "Leakage-guard architecture note" (~lines 40-57).
- **How is `is_imputed`/reporting-anomaly masking applied before deriving case features?** →
  `feature_engineering.py`, `build_fold_agnostic_features()` (~lines 201-219), using
  `mask_untrusted_cases()` from `reporting_anomalies.py`.
- **Why is `Number_of_Cases` kept in the feature table if it must never be a model input?** →
  `feature_engineering.py`, module docstring "Leakage/metadata exclusion" section (~lines 64-76).
- **How does week 53 get handled in the cyclic seasonal features?** → `feature_engineering.py`,
  ~lines 121-128, 241-253, `MODULE2_MONSOON_WEEKS_NE`.

## K. Module 2 — Stage 1 (Baseline Classifier)

- **Why is Module 2 Stage 1 a single pooled model rather than 25 per-district models?** →
  `src/module2_classification/baseline_classifier.py`, `run_pooled_vs_per_district_comparison()`
  (~line 505).
- **How exactly is class imbalance handled per model type?** → `baseline_classifier.py`,
  `fit_and_predict()` (~lines 297-380) — `class_weight="balanced"` for LR/RF, per-fold
  `scale_pos_weight` for XGBoost.
- **How is the "official" Stage 1 model selected?** → `baseline_classifier.py`,
  `select_official_model()` (~line 565) — highest median PR-AUC across folds.
- **Why does `RandomForestClassifier` need a different preprocessing pipeline than XGBoost?** →
  `baseline_classifier.py`, `build_sklearn_preprocessor()` docstring (~line 268) — RF needs
  median-impute + one-hot, XGBoost handles `NaN`/categoricals natively.

## L. Module 2 — Stage 2 (Probability Calibration)

- **Why isn't Stage 2 a literal `residual = actual - predicted` regression like Module 1's?** →
  `src/module2_classification/compensation_model.py`, module docstring point 1 (~lines 8-29) —
  ill-posed for a binary target.
- **How is Platt scaling implemented exactly — on raw probability or log-odds?** →
  `compensation_model.py`, `fit_and_calibrate()`'s "platt" branch (~lines 381-387), using
  `_logit()` (~line 193).
- **What data does each Stage 2 fold train on, and why is fold 1 a no-op?** →
  `compensation_model.py`, module docstring point 2; `run_stage2_benchmark()` (~lines 489-497).
- **On what metric/population is the official Stage 2 architecture selected?** →
  `compensation_model.py`, `select_official_architecture()` (~line 619) — median Brier Skill
  Score among `PRODUCTION_ARCHITECTURE_NAMES`.

## M. Module 2 — Risk Thresholds & Alerts

- **Where exactly does the alert threshold get selected, and on what population?** →
  `src/module2_classification/risk_thresholds.py`, `select_thresholds()` /
  `selection_population()` (~lines 69-104) — F2-optimal, validation folds only, excludes fold 1
  and holdout.
- **Why F0.5 for the high-confidence tier instead of F2 or a fixed quantile?** →
  `risk_thresholds.py`, module docstring points 2-3 (~lines 15-24).
- **How is it confirmed "high" tier really does have a higher observed outbreak rate?** →
  `risk_thresholds.py`, `summarize_tier_rates()` (~line 148).
- **How does the "ramp" alert rule (accelerating case counts) work, and how is it combined with
  the base threshold?** → `src/module2_classification/alert_rules.py`,
  `apply_ramp_alert_rule()` (~line 47) — `base_alert OR (prob >= tau_ramp AND ratio >= rho)`.

## N. Module 2 — Live/Forward Scoring & Prospective Tracking

- **How does live/forward scoring know which model type is "official" without hardcoding it?**
  → `src/module2_classification/scoring_utils.py`, `official_stage1_model()` /
  `official_stage2_architecture()` (~lines 36-49) — reads the `selected` column from the metrics
  CSV.
- **Why doesn't Module 2's live scoring need Module 1's recursive multi-step forecast
  machinery?** → `src/module2_classification/live_scoring.py`, module docstring (~lines 13-25) —
  every Stage 1 feature is a lag or already-reported climate, never same-week case count.
- **How exactly does Module 1's forecast get substituted into Module 2's case-lag features for
  multi-week-ahead rows?** → `src/module2_classification/forecast_future_risk.py`,
  `_cases_for_lags()` (~line 206) — from horizon step 2 onward.
- **Why is Module 3's `Risk` score lagged by ≥1 week before being used as a Module 2 feature?** →
  `src/module2_classification/m3_risk_join.py`, module docstring (~lines 5-14) — same-week use
  would leak the same case counts the label is derived from.
- **How does Module 2's own forward-prediction log avoid ever fabricating a resolved outcome?**
  → `src/module2_classification/risk_tracking.py`, `reconcile_risk_log()` (~lines 121-127) —
  unresolved rows are dropped from output entirely, not guessed.
- **How are Venn-Abers uncertainty bands computed around Stage 1's probability?** →
  `src/module2_classification/uncertainty_bands.py`, `_ivap_point()` (~line 63) — two augmented
  isotonic fits (label forced to 0, then to 1).

## O. Module 3 — Preprocessing & Stage 1 (KDE + Moran's I)

- **How is district elevation obtained when it isn't in any weekly table?** →
  `src/preprocessing/module3_preprocessing.py`, `extract_elevation()` (~line 82) — parsed from
  each raw Open-Meteo CSV's metadata preamble.
- **How is the KDE baseline's bandwidth chosen, and why isn't it refit per week?** →
  `src/module3_spatial/kde_baseline.py`, `silverman_covariance()` (~line 145) — Silverman rule,
  computed once from the district centroids' own spatial spread.
- **How is one week's spatial KDE surface computed efficiently for ~1,000 weeks?** →
  `kde_baseline.py`, `compute_kde_baseline()` (~line 165) — one matrix multiply (case-count
  matrix @ kernel matrix).
- **How does the pipeline check that spatial clustering is a real, stable pattern and not an
  averaging artifact?** → `kde_baseline.py`, `select_representative_weeks()` (~line 237) +
  per-week Moran's I via `compute_moransI_for_week()` (~line 266).

## P. Module 3 — Feature Engineering & Stage 2 (Random Forest)

- **Why is the raw `Residual` column not used as the RF's training target?** →
  `src/module3_spatial/compensation_model.py`, module docstring (~lines 4-17) — `KDE_baseline`'s
  raw magnitude (~1e-7) is numerically incompatible with case counts.
- **How does the mass-conserving KDE rescale work?** → `compensation_model.py`,
  `rescale_kde_baseline()` (~line 177).
- **How does the relative-residual reconstruction back to an absolute Risk value work (the
  official M3-015 mechanism)?** → `compensation_model.py`, module docstring (~lines 76-78):
  `Risk_t = Risk_(t-1) + predicted_relative_residual * (Risk_(t-1) + 1)`.
- **How are the spatial cross-validation folds constructed so districts are never split across
  folds?** → `compensation_model.py`, `build_spatial_folds()` (~line 268) — K-means (5 clusters)
  on district centroids.
- **How is the Mahalanobis multivariate anomaly score computed?** →
  `src/module3_spatial/feature_engineering.py`, `fit_mahalanobis_stats()` /
  `apply_mahalanobis_scores()` (~lines 176-204).
- **Why does every iteration of the iterative loop retrain the RF instead of reusing one frozen
  model?** → `src/module3_spatial/iterative_loop.py`, module docstring (~lines 9-24) — a frozen
  model with unchanging climate inputs can't respond to the evolving Risk state.
- **Why is the iterative loop capped at 1 iteration rather than run to convergence?** →
  `iterative_loop.py`, `MAX_ITERATIONS` comment (~lines 107-126) — oscillating `max_delta` when
  tried at 4 iterations, pre-M3-008 feature fix.
- **What evidence motivated switching Stage 2's target from absolute to relative residual
  (M3-015)?** → `src/module3_spatial/relative_residual_compensation.py`, module docstring
  (~lines 1-14) — `corr(Risk_0, |error|) = 0.78` (heteroscedasticity).
- **How was spatial spillover (a neighbor's own residual) ruled out as a feature?** →
  `relative_residual_compensation.py`, module docstring (~lines 27-33) — partial correlation of
  0.03 once own lag_1 is controlled for.

## Q. Module 3 — Evaluation, Visualization & Forward Forecast

- **What is the headline Stage 1 vs. Stage 2 accuracy comparison, and how is it computed?** →
  `src/module3_spatial/evaluate.py`, `compare_stage1_vs_stage2()` (~line 92).
- **How is it verified `population_density`'s dominant feature importance isn't just a proxy for
  `Estimated_Population`?** → `evaluate.py`, `plot_population_density_pdp()` (~line 160) —
  sklearn partial-dependence plot.
- **How is "correctly identifying the hottest districts" measured separately from absolute
  error?** → `src/module3_spatial/hotspot_ranking_evaluation.py`,
  `compute_weekly_rank_metrics()` (~line 92) — Spearman rho + Precision@k.
- **How is a paired week-level bootstrap CI computed (reused across several Module 3
  ablations)?** → `src/module3_spatial/blended_persistence_rf.py`, `bootstrap_ci_diff()`
  (~line 203).
- **Why does the risk surface use Inverse Distance Weighting instead of a Gaussian kernel like
  Stage 1's KDE?** → `src/module3_spatial/risk_surface.py`, module docstring (~lines 12-57) —
  two Gaussian-kernel attempts numerically failed a Colombo/Gampaha/Kalutara sanity check.
- **Does the risk-surface interpolation feed back into the RF or iterative loop?** → No —
  `risk_surface.py`, module docstring (~lines 50-57) — display-only.
- **Why is the forward hotspot forecast's climate treated as real observed data, not a genuine
  forecast?** → `src/module3_spatial/forecast_future.py`, module docstring (~lines 16-30) —
  verified `climate_data_source="observed"` for the relevant dates (case reporting lags real
  time more than climate forecasting range).
- **How does Stage 1's KDE step work for a forecast week with no real case count yet?** →
  `forecast_future.py`, `forecast_week_kde()` / `rescale_forecast_kde()` (~lines 360-388) —
  Module 1's forecasted cases substitute as KDE weights.
- **Is there a single entry point that runs Module 3's whole pipeline end to end?** → No —
  `src/module3_spatial/main.py` is an unimplemented placeholder; each stage
  (`kde_baseline.py`, `feature_engineering.py`, `compensation_model.py`, `iterative_loop.py`,
  `evaluate.py`) is run independently via its own `if __name__ == "__main__"` block.

## R. Dashboard

- **How does the dashboard know which page to render and in what order?** →
  `src/dashboard/app.py`, `main()` (~line 51) — `st.navigation([...])` over the four
  `views/*.py` files.
- **How does the "Refresh operational data" button trigger the pipeline?** → `app.py`,
  `_run_refresh()` (~line 37) — runs `scripts/refresh_dashboard_data.py` as a subprocess.
- **How does the dashboard guarantee the alert threshold shown never goes stale after a
  Stage 1/2 retune?** → `src/dashboard/components.py`, `get_thresholds()` (~line 107, cached) —
  the only sanctioned entry point, wraps `scoring_utils.load_production_thresholds()`.
- **How does a viewer distinguish "validated" from "operational, no ground truth yet" at a
  glance?** → `components.py`, `evidence_badge()` (~line 27) / `module_badge()` (~line 47).
- **Why does the dashboard sometimes show different Module 2 holdout numbers than a static CSV
  snapshot would suggest?** → `src/dashboard/data_loaders.py`, `m2_holdout_summary()`
  (~line 119) — reads Module 2 metrics **live**, bypassing a frozen, pre-Decision-047 snapshot
  CSV.
- **How is cache invalidation done so a manual refresh reflects immediately but page navigation
  stays fast?** → `data_loaders.py`, `_cached_csv()` (~line 56) — mtime-keyed `@st.cache_data`.
- **Which specific districts did Module 1's residual correction regress on holdout, and how is
  that shown to a viewer?** → `src/dashboard/views/research_evidence.py`,
  `M1_REGRESSED_DISTRICTS` (~line 35) — Kilinochchi/Mannar/Vavuniya, called out explicitly on
  the per-district bar chart.
- **How is a reporting-delay catch-up week surfaced visually?** →
  `src/dashboard/views/operational_monitoring.py`, `tab_recent` block inside
  `render_operational_page()` (~line 83) — merges in `is_reporting_anomaly` flags.
- **Why does Module 3's spatial map use an `ImageOverlay` instead of Leaflet's point-based
  `HeatMap` plugin?** → `operational_monitoring.py`, `_hybrid_risk_folium_heatmap()`
  (~line 552) — `HeatMap`'s fixed-pixel radius breaks across zoom levels.
- **Why did raw CSS fail to inject into a folium map, and what fixed it?** →
  `operational_monitoring.py`, `_InlineCss` class (~line 722) — a `MacroElement` subclass (plain
  `folium.Element` silently fails to register).
- **Why is it legitimate for the Prospective Tracking page to show 0 resolved predictions
  early on?** → `src/dashboard/views/prospective_tracking.py`,
  `render_prospective_page()` (~line 21) + `components.prospective_tracker_panel()` (~line 120)
  — explicit framing, not a bug.

## S. Pipeline Orchestration (cross-cutting)

- **What is the exact, ordered sequence of pipeline stages a dashboard "Refresh" click
  triggers?** → `scripts/refresh_dashboard_data.py`, `run_refresh()` (~line 79) — weather fetch
  → shared/module1/module2/module3 preprocessing → M1 forecast/nowcast → M1 tracking → M2 live →
  M2 forward → M2 tracking.
- **How does the pipeline distinguish "observed" from "forecast" climate rows downstream?** →
  `scripts/fetch_open_meteo_weather.py`, `climate_data_source` column, set in
  `fetch_archive()`/`fetch_forecast()` (~lines 151, 167).
- **How far into the future does the weather fetch reach?** → `fetch_open_meteo_weather.py`,
  `compute_forecast_horizon_end()` (~line 185) — at least `FORECAST_HORIZON_WEEKS` beyond the
  last known case week, capped at the API's 16-day limit.
- **What's the exact Module 2 end-to-end pipeline order?** →
  `src/module2_classification/main.py`, `PIPELINE_STAGES` (~line 79).

---

# PART 2 — File-by-File Reference

*(Organized in the order the pipeline actually runs. Each entry is deliberately concise — see
Part 1 for the "how does X happen" framing, and open the file directly for full detail.)*

## Configuration

### `src/config.py`
Central configuration: all filesystem paths, shared constants (`DISTRICTS`, monsoon weeks,
epidemic-threshold parameters), and ablation-safe path-builder functions
(`module1_stage2_paths()`, `module2_stage1_paths()`, `module2_stage2_paths()`) that route
non-default runs to suffixed paths so they never overwrite production artifacts.

### `src/utils.py`
Ten lines. `ensure_dir(path)` — idempotent directory creation.

## Shared Preprocessing

### `src/preprocessing/shared.py`
Module-agnostic layer (Decision 013). Reads raw epi/weather/population files, writes the four
shared base tables: `epi_week_calendar.csv`, `climate_weekly.csv`, `population_annual.csv`,
`epidemiological_weekly.csv`. Key functions: `merge_kalmunai_into_ampara()`,
`build_epi_week_calendar()`, `fill_isolated_calendar_gaps()`, `aggregate_climate_weekly()`,
`interpolate_population()`. Deliberately excludes any module-specific transformation.

## Module 1 — Forecasting

### `src/preprocessing/module1_preprocessing.py`
Module-1-specific layer: week-53→52 merge, seasonal-naive gap imputation, climate/population
merge, `cases_per_100k`. Writes `weekly_modeling_table.csv`. Key functions:
`impute_missing_weeks()`, `merge_week_53_into_52()`, `validate_weekly_modeling_table()`.

### `src/preprocessing/reporting_anomalies.py`
Shared by Modules 1 and 2. `flag_reporting_anomalies()` (retrospective, rebound-confirmed),
`flag_reporting_dip_causal()` (real-time-safe), `mask_untrusted_cases()`,
`compute_reporting_delay_features()` (the M1-006B feature group).

### `src/module1_forecasting/validation.py`
The walk-forward harness (Decisions 009/010). `get_district_series()`, `fit_window()` (the sole
sanctioned training-slice accessor), `get_holdout_series()`, `generate_walk_forward_folds()`
(14 expanding-window annual folds, `min_train_years=3` default).

### `src/module1_forecasting/feature_engineering.py`
Stage 2 feature builder. `build_fold_agnostic_features()` (case/climate lags, rolling stats,
cyclic seasonal, reporting-delay features — all safe to compute once globally) vs.
`compute_fold_climate_anomalies()` (must be recomputed per fold — the single most
leakage-sensitive function in Module 1).

### `src/module1_forecasting/baseline_sarima.py`
Stage 1. One SARIMA per district (Decision 002). `select_order()` (once per district/transform,
full pre-holdout history), `_has_explosive_ar_root()` (Decision 017's stability guard),
`fit_and_forecast()` (never raises, 0-floor clip), `validate_candidate()` (walk-forward MASE),
`select_winning_candidate()` (raw vs. log1p), `forecast_holdout()` (one-time holdout report).

### `src/module1_forecasting/stl_arima.py`
STL+ARIMA pilot alternative to SARIMA (M1-012). Mirrors `baseline_sarima.py`'s interface to
reuse the same walk-forward harness. **Not wired into `main.py`** — rejected after piloting.

### `src/module1_forecasting/residual_transform.py`
`compute_stage2_target()` and `combine_stage2_forecast()` — the additive (production) vs. log
(M1-006A, rejected) transform, implemented as a mode switch, not separate code paths.

### `src/module1_forecasting/compensation_model.py`
Stage 2. Pooled XGBoost per fold, MAE loss. `compute_fold_boundaries()`,
`build_fold_scoped_anomalies()`, `build_residual_lags()` (full-calendar reindex, Decision 015),
`train_and_predict_fold()`, `train_final_production_model()`. Also contains the M1-021
per-district alternative path (`_fit_one_district()`, rejected after testing).

### `src/module1_forecasting/shrinkage.py`
Phase-3 per-district shrinkage weight (Decision 034/M1-009). `select_shrinkage_weights()`
(validation-only grid search), `evaluate_shrinkage_on_holdout()` (confirm/revert only, never
re-search), `load_final_weights()`.

### `src/module1_forecasting/combine.py`
Combines Stage 1 + Stage 2 into `final_prediction`, runs the full evaluation framework.
`build_final_predictions()`, `compute_district_fold_metrics()`, `residual_variance_reduction()`,
`compute_dm_results()`, `plot_final_acf_diagnostics()`.

### `src/module1_forecasting/evaluate.py`
Pure metric functions: `rmse()`, `mae()`, `smape()`, `mase()` (all mask-aware), `dm_test()`
(Diebold-Mariano, HAC/Newey-West), `ljung_box_diagnostics()`.

### `src/module1_forecasting/main.py`
End-to-end orchestrator. `PIPELINE_STAGES`, `run_pipeline(force, stages, residual_mode)` —
idempotent, skips any stage whose output already exists unless `--force`.

### `src/module1_forecasting/forecast_future.py`
Operational forward forecasting (Decision 018/031/040). `forecast_district()` (8-week recursive
forecast, self-feeding after 1-2 real weeks), `run_future_forecast()`, `_collect_vintage_forecasts()`
/ `_ensembled_next_week_sarima()` (vintage-ensembled SARIMA), `run_nowcast()` (genuine
`horizon=1`, zero recursion, Decision 031/040).

### `src/module1_forecasting/rolling_one_step.py`
Deployment-faithful weekly-refit evaluator (Decision 029). `rolling_one_step_district()`, three
mutually-exclusive refit strategies (`_low_freq_refit_step()` M1-014,
`_vintage_ensemble_step()` M1-015, inline `warm_start` M1-013), `compute_dm_results_rolling()`.

### `src/module1_forecasting/nowcast_tracking.py`
Permanent prospective-accuracy log (Decision 041/M1-017). `append_to_nowcast_log()`
(append-only), `reconcile_nowcast_log()` (joins against real data once available, never
fabricates a result for an unresolved week).

## Module 2 — Classification

### `src/preprocessing/module2_preprocessing.py`
Module-2-specific layer: week 53 kept unmerged, seasonal-naive imputation, climate/population
merge. `impute_missing_weeks()`, `merge_climate()`, `merge_population()`,
`validate_weekly_modeling_table()`.

### `src/module2_classification/labels.py`
The epidemic-threshold outbreak label (Decisions 019/025). `compute_historical_stats_harmonic()`
(OFFICIAL: per-district, per-year expanding harmonic regression), `compute_historical_stats()`
(SUPERSEDED exact-per-week estimator, kept for audit), `compute_epidemic_threshold_labels()`.

### `src/module2_classification/feature_engineering.py`
Stage 1 feature builder. `build_fold_agnostic_features()`, `compute_case_anomaly_lags()`
(computed once globally, unlike Module 1's climate anomalies — see the module's own "leakage
guard architecture note" explaining why that's still safe here).

### `src/module2_classification/baseline_classifier.py`
Stage 1. Pooled walk-forward benchmark of Logistic Regression/Random Forest/XGBoost.
`compute_fold_boundaries()` (`MODULE2_MIN_TRAIN_YEARS=4`, 13 folds), `fit_and_predict()`,
`run_pooled_vs_per_district_comparison()`, `select_official_model()` (median PR-AUC),
`train_final_production_model()`.

### `src/module2_classification/compensation_model.py`
Stage 2. Isotonic / Platt / stacked-XGBoost / experimental logit_residual, selected by median
Brier Skill Score. `assemble_stage2_table()`, `fit_and_calibrate()`, `run_stage2_benchmark()`
(fold 1 no-op), `select_official_architecture()`, `plot_reliability_diagrams()`.

### `src/module2_classification/risk_thresholds.py`
Alert threshold (F2-optimal) and high-confidence boundary (F0.5-optimal), validation-folds-only.
`scan_alert_thresholds()`, `select_thresholds()`, `assign_risk_tier()`,
`run_holdout_threshold_evaluation()`.

### `src/module2_classification/alert_rules.py`
M2-007C "ramp" alert rule extension — an additional trigger for sharply accelerating case
counts. `compute_ramp_ratio()`, `apply_ramp_alert_rule()`, `grid_search_ramp_rule()`.

### `src/module2_classification/evaluate.py`
Pure metric functions: `fbeta_score()`, `threshold_scan()`, `pr_auc()` (Stage 1's primary
metric), `brier_skill_score()` (Stage 2's primary metric), `reliability_curve()`.

### `src/module2_classification/scoring_utils.py`
Shared helpers for live/forward scoring. `official_stage1_model()` / `official_stage2_architecture()`
(read the "selected" flag, never hardcoded), `load_stage1_model()` / `load_stage2_model()`,
`score_feature_rows()`, `apply_risk_tiers()`.

### `src/module2_classification/main.py`
End-to-end orchestrator, same idempotent pattern as Module 1's `main.py`. `PIPELINE_STAGES`,
`run_pipeline()`.

### `src/module2_classification/live_scoring.py`
Scores the most recent N weeks per district using frozen production models — for dashboard
consumption, distinct from walk-forward evaluation. `run_live_scoring()`, flags
`already_scored_in_pipeline` so live numbers are never cited as extra validation evidence.

### `src/module2_classification/forecast_future_risk.py`
Forward operational scoring beyond the last case-count week (Decision 027). Substitutes Module
1's `final_prediction` into case-derived lag features from horizon step 2 onward.
`_extend_with_forward_weeks()`, `_cases_for_lags()`, `run_forward_risk()`.

### `src/module2_classification/m1_forecast_join.py`
Builds leakage-safe lagged Module 1 forecast features (`m1_final_prediction_lag_1`) for the
optional M2-007D feature variant — only from Module 1's walk-forward out-of-sample predictions.

### `src/module2_classification/m3_risk_join.py`
Builds leakage-safe lagged Module 3 hybrid-risk features (`m3_risk_lag_1/2`) for the optional
M2-014 feature variant — lagged by ≥1 week to avoid leaking same-week case information.

### `src/module2_classification/risk_tracking.py`
Permanent prospective-accuracy log for Module 2's forward risk predictions, mirroring Module
1's `nowcast_tracking.py`. `append_to_risk_log()`, `reconcile_risk_log()`.

### `src/module2_classification/uncertainty_bands.py`
Venn-Abers (IVAP) uncertainty intervals around Stage 1's raw probability — a companion
diagnostic, does not alter the official Stage 2 calibrator. `_ivap_point()`, `ivap_batch()`,
`compute_fold_aware_uncertainty_bands()`.

## Module 3 — Spatial

### `src/preprocessing/module3_preprocessing.py`
Builds `master_table.csv` — shared tables + elevation (parsed from raw weather CSV preambles).
`extract_elevation()`, `merge_climate()`, `merge_population()`, `merge_elevation()`.

### `src/module3_spatial/kde_baseline.py`
Stage 1. Case-weighted Gaussian KDE over district centroids + Global Moran's I validation.
`load_district_boundaries()`, `silverman_covariance()`, `build_kernel_matrix()`,
`compute_kde_baseline()`, `build_queen_weights()`, `compute_global_moransI()`,
`select_representative_weeks()`.

### `src/module3_spatial/feature_engineering.py`
Stage 2 feature builder (no training). `compute_residual()` (the raw target, later shown
unusable at this scale), `compute_lag_features()`, `compute_climate_anomaly()` (full-sample, not
fold-aware — justified since Module 3 uses spatial not temporal CV), `compute_population_density()`,
`fit_mahalanobis_stats()` / `apply_mahalanobis_scores()`.

### `src/module3_spatial/compensation_model.py`
Stage 2, the official model. `rescale_kde_baseline()` (mass-conserving), `add_residual_lag_features()`
(own-district lags, dominant features per M3-008/M3-015), `build_spatial_folds()` (K-means, 5
clusters), `run_spatial_cv()`. `TARGET_COL = "relative_residual"` (M3-015, current official).

### `src/module3_spatial/iterative_loop.py`
The core "iterative" risk-compensation mechanism, capped at `MAX_ITERATIONS=1` by design.
`out_of_fold_predict()` (retrains per spatial fold), `aggregated_moransI()`,
`run_iterative_loop()` (dual convergence check: numeric delta + Moran's I non-significance).

### `src/module3_spatial/evaluate.py`
`compare_stage1_vs_stage2()`, `plot_population_density_pdp()`, `plot_convergence()`,
`build_summary_text()` → writes `results_summary.txt`.

### `src/module3_spatial/persistence_baseline.py`
The naive "carry last week's own residual forward" baseline (M3-010) that the official RF must
beat to claim genuine value. `run_persistence_baseline()`.

### `src/module3_spatial/relative_residual_compensation.py`
M3-015 — the promoted relative-residual reformulation. `add_relative_residual_features()`,
`out_of_fold_relative_rf()`, paired week-level bootstrap stress test.

### `src/module3_spatial/blended_persistence_rf.py`
M3-013 — tests a convex blend of RF and persistence outputs (not stacking). `best_weight_by_mae()`,
`out_of_fold_blend()`, `bootstrap_ci_diff()` (reused by several other Module 3 files),
`per_week_metric_table()`.

### `src/module3_spatial/isotonic_calibration.py`
M3-014 — calibration-based Stage 2 alternative (rejected: fails on the highest-magnitude spatial
fold). `decile_bias_table()`, `out_of_fold_isotonic_calibrate()`.

### `src/module3_spatial/stacked_persistence_experiment.py` and `stage2_experiments.py`
Frozen exploratory ablations (M3-011, M3-008 respectively) — kept unchanged for reproducibility,
not part of the official pipeline. `stage2_experiments.py`'s residual-lag finding is what got
promoted into `compensation_model.py`.

### `src/module3_spatial/alpha_sweep.py`
M3-006 — frozen ablation asking whether running the full 4-iteration loop at different alpha
values improves fit (answer: no, the real fix was a missing feature, resolved by M3-008).

### `src/module3_spatial/hotspot_ranking_evaluation.py`
Companion evaluation lens (M3-012): Spearman rank correlation + Precision@k, since Module 3's
actual purpose is hotspot *detection*, not case-count regression. `build_model_predictions()`
(widely reused), `compute_weekly_rank_metrics()`.

### `src/module3_spatial/risk_surface.py`
Visualization-only continuous risk-surface interpolation via k-NN Inverse Distance Weighting.
`build_evaluation_grid()`, `evaluate_risk_surface()`, `risk_surface_rgba()` (for the Folium
`ImageOverlay`).

### `src/module3_spatial/raster_alignment.py`
Empty placeholder — docstring only, no code.

### `src/module3_spatial/actual_vs_predicted_surface.py`
Ad-hoc, non-official side-by-side visualization of actual-case vs. predicted-Risk surfaces on a
shared color scale.

### `src/module3_spatial/forecast_future.py`
Cross-module operational forward hotspot forecast (Decision 052). Reads Module 1's
`future_forecast.csv` (read-only) as the case-count proxy for Stage 1 KDE weighting.
`forecast_week_calendar()`, `aggregate_forecast_week_climate()`, `build_forecast_feature_table()`,
`run_forecast_future()`. Every output row tagged `evidence_tier="operational"`. Also logs every
forecast to the prospective tracker (`hotspot_tracking.py`, Decision 052/M3-016).

### `src/module3_spatial/hotspot_tracking.py`
Prospective (not backtested) accuracy tracking for the forward hotspot forecast above
(Decision 052/M3-016), mirroring `module1_forecasting/nowcast_tracking.py` and
`module2_classification/risk_tracking.py`. `append_to_hotspot_log()`,
`reconcile_hotspot_log()`.

### `src/module3_spatial/main.py`
Unimplemented placeholder — Module 3 has no single end-to-end entry point; each stage script
runs independently.

## Dashboard

### `src/dashboard/app.py`
Streamlit entry point; four-page `st.navigation`, sidebar controls, refresh trigger.

### `src/dashboard/components.py`
Shared UI atoms: `evidence_badge()`, `module_badge()`, `GLOSSARY`, `get_thresholds()` (the
sanctioned, always-live threshold accessor), `prospective_tracker_panel()`.

### `src/dashboard/data_loaders.py`
The single read layer for every CSV/shapefile. `_cached_csv()` (mtime-keyed cache),
`load_district_geometry()`, `m1_holdout_summary()`, `m2_holdout_summary()` (reads live, not a
stale snapshot), `m3_morans_i_summary()`.

### `src/dashboard/theme.py`
Pure color constants: `MODULE_COLORS` (matches Figure 5.1), `RISK_COLORSCALE`,
`EVIDENCE_TIER_COLORS` — two deliberately separate color languages, never mixed.

### `src/dashboard/views/overview.py`
Page 1 — cold-open summary of all three modules' headline holdout metrics + evidence-tier
legend.

### `src/dashboard/views/research_evidence.py`
Page 2 — every number here is holdout-validated. Per-district Module 1 chart with regressed
districts called out; Module 2 vs. M1-threshold comparison (M2-009); Module 3's evaluation
evolution (M3-005 → M3-008 → M3-015).

### `src/dashboard/views/operational_monitoring.py`
Page 3 — live/forward decision-support prototype. National triage, per-district drill-down, and
four alternative Module 3 map renderings (choropleth, folium heat-cloud/`ImageOverlay`, circle
map, "Uber-style" glow map via `_InlineCss`).

### `src/dashboard/views/prospective_tracking.py`
Page 4 — the two self-checking, non-backtested accuracy trackers (Module 1 nowcast, Module 2
forward risk).

## Cross-Cutting Scripts

### `scripts/refresh_dashboard_data.py`
Orchestrates the full refresh: weather fetch → shared/module preprocessing → M1 forecast/nowcast
→ M1 tracking → M2 live/forward → M2 tracking. `run_refresh()`, `_summarize_outputs()` (writes
the freshness manifest).

### `scripts/fetch_open_meteo_weather.py`
Appends observed (Archive API, gap-fill) and forecast (Forecast API) rows to all 25 per-district
weather CSVs, preserving each file's original preamble/date format.
`compute_forecast_horizon_end()`, `refresh_district_file()`.

---

# PART 3 — Research/Ablation Script Index (`scripts/`)

For the ~30 one-off scripts behind each numbered experiment — use this table when someone asks
"where's the code for M1-007" or similar. Full result numbers live in each module's
`EXPERIMENT_LOG.md`, not repeated here.

| Script | Purpose | Experiment ID | Module |
|---|---|---|---|
| `audit_label_stabilization.py` | Compares exact-week vs. windowed/harmonic label estimators | Decision 025 | 2 |
| `audit_smote_imbalance.py` | Tests SMOTENC oversampling vs. class-weighting for Stage 1 | Decision 021 | 2 |
| `backtest_nowcast_ensemble.py` | Retroactive check: single-fit vs. vintage-ensembled nowcast | M1-018 | 1 |
| `data_audit_module1.py` | Read-only factual audit of raw epi/weather data | pre-experiment audit | 1 |
| `data_audit_module2.py` | Epidemic-threshold label class balance across candidate `k` | pre-k-selection audit | 2 |
| `diagnose_rolling_dm_gap.py` | Root-causes the rolling-vs-holdout DM significance gap | M1-011 | 1 |
| `evaluate_causal_dip_detector.py` | Precision/recall of the real-time reporting-dip detector | M1-019 (step 2) | 1 |
| `evaluate_per_district_stage2.py` | Per-district Stage 2 vs. pooled | M1-021 | 1 |
| `evaluate_production_stack.py` | Evaluates the promoted production stack vs. pre-promotion | M1-005/M1-006B | 1 & 2 |
| `evaluate_reporting_leakage_fix.py` | Checks Decision 030's gain survives with leakage closed | M1-019 (step 1) | 1 |
| `m1_006_compare.py` | M1-006A log-residual vs. M1-005 additive | M1-006 (M1-006A) | 1 |
| `m1_006b_compare.py` | M1-006B reporting-delay features vs. M1-005 | M1-006B | 1 |
| `m1_007_residual_lag_extension.py` | Extra residual lags/EWMA vs. Ljung-Box failures | M1-007 | 1 |
| `m2_007a_evaluate.py` | Logit-residual Stage 2 vs. isotonic baseline | M2-007A | 2 |
| `m2_007c_evaluate.py` | Ramp alert rule vs. single-threshold baseline | M2-007C | 2 |
| `m2_007d_evaluate.py` | M1-fed Stage 2 features vs. isotonic baseline | M2-007D | 2 |
| `m2_008_symmetric_ablation.py` | Module-1-style climate-in-Stage-2 ablation for Module 2 | M2-008 | 2 |
| `m2_009_m1_alert_baseline.py` | Is Module 2 redundant with thresholding Module 1's forecast? | M2-009 | 2 (vs. M1) |
| `m2_010_stage1_ensemble.py` | Ensembling RF+XGBoost+LR vs. picking one official model | M2-010 | 2 |
| `m2_011_adaptive_k_label.py` | District-adaptive `k` vs. one global k=3.0 | M2-011 | 2 |
| `m2_012_uncertainty_bands_eval.py` | Evaluates the Venn-Abers uncertainty bands | M2-012 | 2 |
| `m2_013_stage1_rf_refresh.py` | `balanced_subsample`, RF tuning, gradient boosting | M2-013 | 2 |
| `m2_014_m3_risk_feature.py` | Lagged Module 3 spatial-risk feature added to Stage 1 | M2-014 | 2 (uses M3) |
| `m2_016_case_anomaly_lag1_carryforward.py` | Carry-forward substitution for masked `case_anomaly_lag_1` | M2-016 | 2 |
| `pilot_stl_arima.py` | 3-district STL+ARIMA pilot vs. existing SARIMA | M1-012 | 1 |
| `run_rolling_one_step_ensemble_parallel.py` | Full 25-district rolling eval with vintage ensemble | M1-015 | 1 |
| `run_rolling_one_step_parallel.py` | Parallel driver for the full rolling one-step backtest | M1 remediation phase 1 | 1 |
| `search_stage2_hyperparameters.py` | Randomized XGBoost hyperparameter search, holdout-gated | M1-020 | 1 |
| `stage1_calibration_diagnostic.py` | Discrimination-vs-calibration diagnostic on Stage 1 | Decision 021 follow-up | 2 |
| `summarize_predictions.py` | One-off summary of final M1/M2 predictions | — | 1 & 2 |
| `tune_stage1_xgboost.py` | Optuna hyperparameter tuning for Module 2 Stage 1 | Decision 023 | 2 |

**Note:** several scripts above reference their motivating decision but don't name a formal
experiment ID in their own docstring — cross-check against the relevant module's
`EXPERIMENT_LOG.md` if the exact ID matters.
