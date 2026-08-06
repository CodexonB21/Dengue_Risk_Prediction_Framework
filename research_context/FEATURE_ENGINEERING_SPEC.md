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

**Untrusted-case masking (Decision 011 + Decision 028):** Groups 1–2 case lags and rolling stats are derived from `Number_of_Cases` after nulling rows where `is_imputed == True` **or** `is_reporting_anomaly == True` (`mask_untrusted_cases()` in `src/preprocessing/reporting_anomalies.py`). Labels and evaluation still use the raw count; only feature derivation is masked. M1 Stage 2 `residual_lag_1/2` apply the same reporting-anomaly mask to residuals before full-calendar reindexing (Decision 015 extension).

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

## Feature Group 6: Reporting-Delay / Nowcasting State (M1-006B)

```text
weeks_since_reporting_anomaly
reporting_rebound_ratio_lag1
suspected_backfill_week
```

Purpose:
Encode suspected reporting-lag / catch-up dynamics (Decision 028 extension) so Stage 2 can adjust residuals when recent case lags are untrusted.

Definitions (week *t*, per district):

```text
suspected_backfill_week = 1 if is_reporting_anomaly at t else 0
weeks_since_reporting_anomaly = weeks since most recent flagged week (0 if t flagged; capped at 4; NaN if none prior)
reporting_rebound_ratio_lag1 = cases[t−1] / max(cases[t−2], 1) when week t−1 was flagged (raw counts)
```

**Nowcast imputation (M1-006B, feature derivation only):** when week *t−1* is `is_reporting_anomaly`, `cases_lag_1` is replaced with `max(cases_lag_2, rolling_mean_cases_4w)` before Stage 2 scoring. Raw `Number_of_Cases` in evaluation tables is never modified.

Implemented in `src/preprocessing/reporting_anomalies.py` (`compute_reporting_delay_features`) and `src/module1_forecasting/feature_engineering.py`.

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

## Label Definition (added 2026-07-28, Decision 019; mean/SD ESTIMATOR superseded 2026-07-28, Decision 025)

```text
outbreak(District, Year, Week) = 1 if Number_of_Cases > threshold(District, Week, Year)
                                = 0 otherwise

threshold(District, Week, Year) = historical_mean + k * historical_SD
```

The threshold **formula** and leakage guard are unchanged since Decision 019. What changed
(Decision 025) is HOW `historical_mean`/`historical_SD` are estimated:

- **Original estimator (Decision 019, superseded but kept in the codebase for
  audit/comparison — `labels.compute_historical_stats`)**: an exact per-`(District, Week)`
  sample mean/SD, using only that exact week number's case counts from strictly-prior years.
  Found (Open Question #8; `scripts/audit_label_stabilization.py`) to be too noisy from small
  per-week sample sizes (3-15 strictly-prior years) — pooled outbreak prevalence was 18-25%
  of weeks, well above WHO/CDC's typical single-digit-percent epidemic-alert norm.
- **Current official estimator (Decision 025 — `labels.compute_historical_stats_harmonic`)**:
  per-district, per-year OLS regression of `Number_of_Cases` on `EPIDEMIC_THRESHOLD_N_HARMONICS`
  (= 1) harmonics of week-of-year (`sin`/`cos(2*pi*Week/52)`), refit expanding each year using
  only that district's REAL, strictly-prior-year rows. `historical_mean` = the fitted seasonal
  curve evaluated at the row's own `Week`; `historical_sd` = the fit's residual standard error
  (one value shared across every week of that district-year, unlike the old per-exact-week SD).
  Pools information across an ENTIRE season instead of one exact week number, directly
  addressing the small-sample-noise root cause. Reduces pooled prevalence to 8.6% while also
  reducing the undefined-label rate (16.0% → 10.7%).
- `k = 3.0` is the current default (was `k = 2.0` under the old estimator — re-audited, not
  carried over unchanged, since the new estimator's SD quantity has a different meaning),
  confirmed via `scripts/audit_label_stabilization.py`'s class-balance audit.
- A `(District, Year)` needs at least 3 strictly-prior years of history before a label is
  defined for any week of that year (mirroring `validation.py`'s `DEFAULT_MIN_TRAIN_YEARS`);
  rows without enough history have an **undefined** label (not defaulted to 0) and are
  excluded from training/scoring.
- **Important documented limitation (Decision 025)**: raising `k` to fix the aggregate
  prevalence problem also raises the threshold in high-variance districts (e.g. Colombo,
  whose harmonic-fit residual SD is much larger than its old per-exact-week SD) — this can
  flip individual high-magnitude-spike weeks from labeled `1` to `0` even as the aggregate
  label quality improves. A district-specific/variance-adaptive `k` is a flagged, not yet
  implemented, future refinement.

**Leakage note:** this is a *label*-leakage risk, not a feature-leakage risk
like Module 1's climate anomalies (Group 3 below) — computing the threshold
once globally would let every fold "see" future outbreak years. This is
implemented in `src/module2_classification/labels.py`.

## Feature Groups (finalized 2026-07-28, kickoff feature-engineering review)

### Group M2-1: Case-Trend Features (fold-agnostic)

```text
cases_lag_1
cases_lag_2
cases_lag_3
cases_lag_4
rolling_mean_cases_4w
rolling_std_cases_4w
rate_of_change              = cases_lag_1 - cases_lag_2
momentum_vs_rolling_mean     = cases_lag_1 - rolling_mean_cases_4w
```

`rate_of_change` alone (a bare first difference) was flagged during review as
noisy under this project's well-documented zero-inflation. Rather than
replace it outright, `momentum_vs_rolling_mean` is added alongside it — a
"recent value vs. short-term baseline" signal that is less sensitive to a
single noisy week-to-week jump. Both are kept (not an either/or).

**`is_imputed` masking (Decision 020, 2026-07-28 preprocessing review):** all
of the above are derived from `Number_of_Cases` with `is_imputed` rows masked
to `NaN` first — the first implementation pass only applied this masking to
Group M2-5's `case_anomaly_lag_*`, letting a fabricated seasonal-naive case
count silently flow into a neighboring real week's `cases_lag_*`/rolling
feature. Fixed for consistency: a fabricated value must not bias any
case-derived feature, the same principle already applied to the label itself.

### Group M2-2: Lagged Climate Features (fold-agnostic, new 2026-07-28)

```text
rainfall_lag_2 .. rainfall_lag_8       (7 features, precipitation_sum source)
temperature_lag_1 .. temperature_lag_4  (4 features)
humidity_lag_1 .. humidity_lag_4        (4 features)
```

Same lag windows and rainfall-column choice as Module 1's Feature Group 2 —
re-affirmed independently for Module 2 (not silently inherited), for the same
underlying reason: dengue's transmission chain (mosquito breeding cycle +
extrinsic incubation period) means the climate conditions that actually drive
a diagnosed outbreak precede it by roughly 2-8 weeks, not the current week
alone. Originally Module 2's feature direction only had *anomalies* (Group
M2-3 below); this lag group was added after review specifically to capture
that delayed causal signal, which anomalies (a single current-week deviation
figure) do not.

### Group M2-3: Current-Week Climate + Climate Anomalies

```text
current_rainfall       = precipitation_sum (mm) at week t
current_temperature    = temperature_2m_mean (°C) at week t
current_humidity       = relative_humidity_2m_mean (%) at week t
rainfall_anomaly, temperature_anomaly, humidity_anomaly   (fold-aware)
```

Unlike Module 1 (where Decision 001 deliberately keeps Stage 1 climate-free
to preserve residual signal for Stage 2), Module 2's Stage 1 has no such
purity constraint — real-time weather is observable before case counts are
confirmed, so current-week raw climate is a legitimate, deliberately-included
feature here (a genuine divergence from Module 1's pattern, decided
explicitly, not inherited by accident).

**Fold-aware anomaly computation, reused unchanged from Module 1**: the
anomaly's "long-term mean" is a single value per `(District, Week)` frozen at
each walk-forward fold's training-window cutoff (`compute_fold_climate_anomalies`,
`src/module1_forecasting/feature_engineering.py` — already module-agnostic,
reused directly rather than duplicated). This MUST be recomputed per fold,
never written to the global feature file.

### Group M2-4: Seasonal / Contextual Indicators (fold-agnostic)

```text
sin_week
cos_week
monsoon_indicator_SW
monsoon_indicator_NE
```

Identical definitions to Module 1 Feature Group 4, with one deliberate
divergence (Decision 020, 2026-07-28): Module 2 keeps epi-week 53 unmerged
(see this document's Module 2 preprocessing note / Decision 020), so `Week`
can be 53 here, unlike Module 1 where it is always in `[1, 52]`. `sin_week`/
`cos_week` need no special-casing — `sin(2*pi*53/52) = sin(2*pi*1/52)` by
periodicity, so week 53 naturally lands adjacent to week 1's value, matching
its real calendar position. `monsoon_indicator_NE` uses a Module-2-local
override, `MODULE2_MONSOON_WEEKS_NE = MONSOON_WEEKS_NE + [53]` (week 53 falls
in late December, squarely inside the NE monsoon window) — the shared
`MONSOON_WEEKS_NE` constant assumes Module 1's already-merged 52-week
structure and must not be mutated for Module 2's sake.

### Group M2-5: Case-Level Seasonal Anomaly Lags (new 2026-07-28; estimator updated 2026-07-28, Decision 025)

```text
case_anomaly_lag_1
case_anomaly_lag_2
```

```text
case_zscore(District, Year, Week) = (Number_of_Cases - historical_mean) / historical_sd
case_anomaly_lag_N = case_zscore shifted N weeks within the district's chronological series
```

`historical_mean`/`historical_sd` are the SAME strictly-prior-years quantities
`src/module2_classification/labels.py` computes for the label itself — as of Decision 025,
this means `labels.compute_historical_stats_harmonic` (the per-district harmonic-regression
estimator), not the original per-exact-`(District, Week)` estimator
(`labels.compute_historical_stats`, superseded but kept for audit/comparison). This
consistency requirement — Group M2-5 must always use whichever estimator the label currently
uses — is why `feature_engineering.py`'s import was switched alongside `labels.py`'s change,
not left pointing at the old function. `case_zscore` for the CURRENT row must never be used
as a feature (at `k=EPIDEMIC_THRESHOLD_K` it is almost exactly the label itself,
`zscore > k`) — only its **lagged** versions are safe and exposed. Rows where the lagged week
was itself `is_imputed` get `NaN` (a fabricated case count is not a real observation to
compute an anomaly from).

**Important leakage-guard distinction from Group M2-3's climate anomaly**:
because `historical_mean`/`historical_sd` are computed using only
years strictly before that row's own calendar year (not per-fold using a
frozen training-window average), this construction is safe to compute ONCE,
globally — every possible walk-forward fold's validation year `V` only ever
needs years `< V`, which is exactly what the per-row expanding construction
already provides for any row whose year equals `V`. This is a deliberately
different (and, for this specific quantity, provably equivalent) leakage-guard
architecture than Group M2-3's fold-frozen anomaly — do not conflate the two
or assume both need identical per-fold recomputation.

### Group M2-6: Pooled-Model Support Feature

```text
District
```

Categorical, handled by Stage 1 modeling code (mirrors Module 1 Feature
Group 5b) — not listed as a plain numeric feature.

### Explicitly Excluded From The Model Feature Matrix (leakage/metadata guard, added 2026-07-28)

```text
Number_of_Cases   - IS the quantity the label is thresholded on; using it (or
                     any rescaling of it) as an input feature would let the
                     classifier trivially "predict" its own target.
cases_per_100k    - a population-rescaled copy of Number_of_Cases for the
                     SAME week; equally a direct label leak.
Year (raw)        - monotonically increasing with the walk-forward split
                     itself; a raw numeric Year feature risks the model
                     partially exploiting the split structure rather than
                     genuine seasonal/climate signal.
is_imputed, Estimated_Population, Source_Type, Week_Start_Date,
Week_End_Date     - metadata/reporting columns, not epidemiological signal.
```

`src/module2_classification/feature_engineering.py` defines an explicit,
enumerated `FOLD_AGNOSTIC_FEATURE_COLUMNS` list for exactly this reason —
Stage 1/2 modeling code must build its feature matrix from that list, never
from "all columns minus a manually-remembered exclude list," which is the
more error-prone pattern that let this leakage risk go unnoticed during the
first implementation pass.

### Not Yet Included (deferred, tracked as open questions)

- **Now available (2026-07-28, Decision 021)**: baseline outbreak probability
  — Stage 1's `predicted_probability` column
  (`data/processed/module2/baseline_classifier_predictions.csv`, official
  model = XGBoost), ready to be consumed as a Stage 2 input feature.
- A "weeks currently above threshold" streak/momentum feature — deliberately
  deferred until Module 2 Open Question #8 (single-week vs. consecutive-week
  outbreak trigger) is resolved, to avoid coupling two undecided design
  questions.

## Explicitly Independent of Module 1 (Decision 019, reaffirmed Decision 022)

Module 2's Stage 1 does **not** consume Module 1's SARIMA/XGBoost forecast
output as an input feature. Stage 2 deferred M1 integration in Decision 022;
**M2-007D (2026-07-29)** adds an evaluation-safe join for tree-based Stage 2
only — see Feature Group M2-S2-3 below. Official production architecture
remains isotonic (feature-free).

---

# Module 2 Stage 2: Probability/Classification-Error Compensation

## Target

Three candidate architectures are benchmarked (Decision 022) rather than a
single predetermined target, because a literal port of Module 1 Stage 2's
`residual = actual - sarima_prediction` formula is statistically ill-posed
for a binary label (`label - predicted_probability` for one Bernoulli
observation is a high-variance, low-information regression target, and
there is no clean way to keep `predicted_probability + predicted_residual`
inside `[0, 1]` without ad hoc clipping):

```text
isotonic:        IsotonicRegression(predicted_probability) -> calibrated_probability
platt:           sigmoid(LogisticRegression(logit(predicted_probability))) -> calibrated_probability
stacked_xgboost: XGBClassifier([predicted_probability, contextual features,
                                 District, probability_residual_lag_1/2,
                                 m1_final_prediction_lag_1, m1_forecast_momentum]) -> calibrated_probability
                                 ^ M2-007D optional; tree architectures only
```

Selected by median Brier Skill Score across the 12 trainable walk-forward
folds (2-13; fold 1 is a no-op passthrough — no prior out-of-sample Stage 1
probabilities exist yet), gated by a check that PR-AUC/ROC-AUC don't regress
relative to Stage 1's raw probability.

## Feature Group M2-S2-1: Reused Stage 1 Contextual Features

All of `FOLD_AGNOSTIC_FEATURE_COLUMNS` (Groups M2-1 through M2-5) plus the
fold-aware climate anomalies (Group M2-3's `rainfall_anomaly`/
`temperature_anomaly`/`humidity_anomaly`) plus `District` — used only by the
`stacked_xgboost` architecture, not by isotonic/Platt (which are feature-free
by design). The anomaly value attached to each historical training row is
the one computed from **that row's own originating Stage 1 fold's training
window** (reusing a genuinely-already-known, correctly-scoped value as a
Stage 2 input is not leakage — the same reasoning Module 1's
`compensation_model.build_fold_scoped_anomalies` already established).

## Feature Group M2-S2-2: Stage 1 Probability Signal

```text
predicted_probability   - Stage 1's own out-of-sample outbreak probability
                           (official model = XGBoost), the primary input
                           every Stage 2 architecture corrects
probability_residual_lag_1
probability_residual_lag_2
```

```text
probability_residual(District, Year, Week) = label - predicted_probability
                                              (out-of-sample rows only)
probability_residual_lag_N = probability_residual shifted N weeks within
                              the district's chronological series
```

Built via the same **full-calendar-reindex-then-shift** construction as
Module 1's `residual_lag_1/2` (Decision 015) — reindexing onto every
`(Year, Week)` row (not just the sparse out-of-sample rows) before taking
`shift(1)/shift(2)`, so `NaN`s correctly appear at each district's series
start and across any structural gap, rather than silently pulling in a
stale value. Used only by `stacked_xgboost` (isotonic/Platt take no
features beyond `predicted_probability` itself).

## Feature Group M2-S2-3: M1 OOS Forecast Lags (M2-007D, experimental)

Used only by `stacked_xgboost` and `logit_residual` when
`include_m1_forecast_features=True`:

```text
m1_final_prediction_lag_1   - Module 1 final_prediction (SARIMA + Stage 2 residual),
                               lagged 1 week within district (full-calendar reindex)
m1_forecast_momentum        - m1_final_prediction_lag_1 − cases_lag_2
```

Source: `data/processed/module1/final_combined_predictions.csv` (walk-forward OOS
rows only). Join keys `(District, Year, Week)`. Implementation: `m1_forecast_join.py`.

Holdout ablation (M2-007D): stacked_xgboost PR-AUC +0.054 vs isotonic but BSS
regresses; precision @ τ=0.14 collapses. Not promoted to official Stage 2.

## Not Yet Included (deferred, tracked as an open question)

- An XGBoost variant with `base_margin = logit(predicted_probability)`
  (trees learn only an additive correction in logit space) — the most
  literal translation of Module 1's residual-compensation metaphor that
  stays numerically well-posed. Considered during Decision 022's design but
  deferred as a future ablation, not built in the initial benchmark.
- ~~Module 1's `final_prediction` as a Stage 2 feature~~ — implemented M2-007D
  (Group M2-S2-3); experimental only, not official Stage 2.

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
| 2026-07-28 | Module 2 | Outbreak label made concrete: fold-aware epidemic-threshold method (`mean + k*SD` per District+Week, strictly-prior-years only) | Defensible, district-specific statistical threshold; retires the arbitrary `OUTBREAK_THRESHOLD` placeholder | Accepted (Decision 019); `k` value pending empirical audit |
| 2026-07-29 | Module 1 | `is_reporting_anomaly` masking for all case-derived features + residual lags (Decision 028) | 2026 Wk24 reporting dips poisoned Wk25 lags | Accepted |
| 2026-07-29 | Module 2 | M1 OOS forecast lags in tree Stage 2 (M2-007D) | Leakage-safe join improves stacked PR-AUC but hurts BSS/precision @ fixed τ | Experimental |
| 2026-07-29 | Module 1 | Feature Group 6 reporting-delay + nowcast lag1 (M1-006B) | Catch-up/backfill weeks need explicit state beyond masking | Accepted (Decision 030) |
| 2026-07-28 | Module 2 | Preprocessing review: week 53 kept unmerged (reverses kickoff default); `is_imputed` masking made consistent across all case-derived features (Groups M2-1, M2-5) | Merging week 53 risked spuriously tripping/contaminating the week-52 threshold across all years; masking gap let a fabricated case count silently flow into neighboring weeks' features | Accepted (Decision 020) |
| 2026-07-28 | Module 2 | Stage 2 feature groups defined: reused Stage 1 contextual features + `predicted_probability` + `probability_residual_lag_1/2` (full-calendar-reindex-then-shift construction, Decision-015-style) | A literal residual-regression target (`label - predicted_probability`) is ill-posed for a binary label; three well-posed architectures benchmarked instead, only one of which (`stacked_xgboost`) uses contextual features | Accepted (Decision 022); implementation pending |
| 2026-07-28 | Module 2 | Label/Group-M2-5 `historical_mean`/`historical_sd` estimator replaced: per-exact-`(District, Week)` sample mean/SD -> per-district harmonic-regression seasonal curve (`n_harmonics=1`); `k` re-audited `2.0` -> `3.0` | Exact-per-week estimator was too noisy from small samples (18-25% pooled outbreak prevalence, well above WHO/CDC single-digit norm); harmonic regression pools a whole season's data, reducing prevalence to 8.6% while also lowering the undefined-label rate | Accepted (Decision 025); old estimator kept, not deleted, for audit/comparison |
| 2026-08-04 | Module 1 | Residual-lag extension: `residual_lag_3/4` + causal `residual_ewma_4` (`RESIDUAL_LAG_EXTENSION_COLUMNS`), gated behind `feature_variant="m1_007_residual_ext"` | Targeted the 23/25-districts-fail-Ljung-Box gap; validation MASE improved but holdout MASE regressed (0.374 -> 0.395) | Rejected (Decision 033); code kept as an ablation switch, not deleted |
