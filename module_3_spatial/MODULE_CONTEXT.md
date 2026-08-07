# Module 3 Context: Hybrid Spatial Hotspot Detection

## Owner
Karunarathna R.M.D.R.R.

## Purpose
Identify dengue hotspot areas using spatial baseline modeling followed by environmental/demographic residual correction, refined through an iterative feedback loop.

## Scope Rule (for AI assistants — Claude Code, Cursor, etc.)
Only read/edit files under `src/module3_spatial/`, `src/preprocessing/module3_preprocessing.py`, `data/*/module3/`, `models/module3/`, `outputs/*/module3/`, and `module_3_spatial/`. Do not edit anything under `module_1_forecasting/`, `src/module1_forecasting/`, `module_2_classification/`, or `src/module2_classification/` — those belong to other team members. Shared files (`src/config.py`, `src/utils.py`, `src/preprocessing/shared.py`) may be read but not edited without explicit confirmation.

---

## Current Architecture

```text
Stage 1: KDE + Moran's I spatial baseline
Stage 2: Random Forest residual compensation, wrapped in an iterative
         refinement loop with a dual convergence check (risk-value
         change + residual Moran's I significance)
```

Branch plan: `module-03-stage-01` implements Stage 1 only. `module-03-stage-02` implements Stage 2 and the iterative loop.

---

## Data Pipeline Note (2026-07-28)

Module 3 raw data is now fully collected and confirmed:

- **Dengue cases** — weekly, district-level, cleaned (Kalmunai merged into Ampara; Moneragala/Monaragala and Puttlam/Puttalam spelling variants merged) → `data/raw/epidemiological/`
- **Weather** — rainfall, temperature, humidity, daily, all 25 districts, 2007–2026 (Open-Meteo) → `data/raw/weather/`
- **Elevation** — static, per district, included in weather CSV headers
- **Population** — Census 2001 / 2012 / 2024, district-level; linear interpolation between census points (`shared.py::interpolate_population()`), linear extrapolation for 2025-2026, otherwise the 2012 census figure is used as the static covariate → `data/raw/spatial/`
- **District boundaries** — GADM v4.1 **Level-1** (25 districts). Note: Level-2 is DS-division level (323 units) and is NOT used for Module 3 → `data/raw/spatial/`

Module 3 aggregates weather to **weekly** (epi-week aligned), same resolution as Module 1/2, so it does inherit the shared epi-week calendar from `data/processed/shared/`. It does **not** need Module 1's week-53 merge or `weather_code` handling — those remain Module-1-scoped per Decision 013.

Master table output: `data/processed/module3/master_table.csv`.

---

## Stage 1 — Baseline (decided, implemented 2026-07-28)

- **Kernel Density Estimation** — weighted by case count, Gaussian kernel, Silverman bandwidth, over district centroids
- **Global Moran's I** — queen contiguity spatial weights (from GADM Level-1), validates that the KDE surface reflects genuine clustering
- Output: `KDE_baseline` per district-week → `data/features/module3/baseline_risk.csv`
- Local Moran's I / LISA and Getis-Ord Gi* remain optional stretch additions, not required for stage-01

### Stage 1 Implementation Status

- `src/preprocessing/module3_preprocessing.py` joins the shared base tables
  (read-only) with elevation extracted from the raw Open-Meteo CSV
  preambles into `data/processed/module3/master_table.csv` (25,348 rows).
- `src/module3_spatial/kde_baseline.py`: drops the 125 rows outside
  Open-Meteo's climate coverage window, builds a fixed 25x25 Gaussian
  kernel matrix from a Silverman bandwidth derived once from the district
  centroids' own spatial spread (not re-derived per week — keeps the
  smoothing scale a property of the geography, not epidemic intensity),
  and computes `KDE_baseline` per district-week via one matrix multiply
  (case-count matrix @ kernel matrix).
- **Aggregated Global Moran's I** (mean `KDE_baseline` per district, queen
  contiguity, 999 permutations) — the primary Stage 1 validation
  checkpoint: **I = 0.70, p = 0.001**. Genuine, statistically significant
  spatial clustering confirmed.
- **Secondary per-week check**: Moran's I recomputed for a peak-case week,
  a low-case week, and one representative week from each monsoon season
  (see `select_representative_weeks()`), to confirm the aggregated result
  isn't an artifact of averaging across ~1,000 weeks:

  | Representative week | Year/Week | I | p_sim | Significant |
  |---|---|---|---|---|
  | Peak (also SW monsoon) | 2017 Wk29 | 0.728 | 0.001 | Yes |
  | Low | 2007 Wk13 | 0.735 | 0.001 | Yes |
  | NE monsoon | 2021 Wk1 | 0.031 | 0.279 | **No** |

  2017 Wk29 is the documented peak of Sri Lanka's worst recorded dengue
  outbreak (2017, ~186,000 national cases), which is also why it doubles
  as the SW-monsoon representative week. Clustering is strong during the
  peak/SW-monsoon period and even during a low-case week, but **not
  universal** — the NE-monsoon representative week shows no significant
  clustering. Report this nuance alongside the aggregated I = 0.70
  headline figure, not instead of it.
- New dependencies: `libpysal`, `esda` (added to `requirements.txt`).

---

## KDE_baseline: Two Valid Uses, Not a Contradiction

`KDE_baseline` (Stage 1's output) is used in two different forms across
the pipeline. This is deliberate, not an inconsistency - documented here
explicitly so it reads that way to a review panel too:

1. **Stage 1 / Moran's I validation (raw form)**: `KDE_baseline` is a
   properly-normalized 2D Gaussian density surface - it integrates to 1
   over space, so its ABSOLUTE magnitude is tiny (max ~4.48e-7 across the
   whole dataset, since the Silverman bandwidth spans tens/hundreds of km).
   This is fine for Stage 1's purpose: Global Moran's I is scale-invariant
   - it validates the RELATIVE spatial clustering pattern of the surface,
   completely unaffected by the surface's absolute scale. I = 0.70,
   p = 0.001 is a genuine result on these terms and is untouched.

2. **Stage 2 / RF residual model (rescaled form)**: the residual target
   `Actual_case_intensity − Current_Risk` only means something if both
   terms are on a comparable scale - and raw `KDE_baseline` is not (its
   near-zero magnitude made `Residual` numerically indistinguishable from
   `Number_of_Cases` itself: corr = 0.9999999999999991, verified before
   building the RF model). `compensation_model.py::rescale_kde_baseline()`
   mass-conserves `KDE_baseline` per (Year, Week) so it sums to that
   week's actual total case count across districts - this preserves the
   KDE surface's spatial redistribution SHAPE (which district gets more or
   less of the week's total burden, based on proximity to case-heavy
   neighbors) while making its magnitude meaningful as a baseline to
   subtract from. Verified this produces a genuine residual:
   `corr(residual_rescaled, Number_of_Cases)` drops from 0.9999999 to
   0.678.

**Same underlying spatial shape, two different valid uses**: a
scale-invariant clustering test doesn't need (or benefit from) the
rescale; a subtractable baseline can't work without it. The iterative loop
(`src/module3_spatial/iterative_loop.py`, implemented) uses the RESCALED
form as `Risk_0`, per this note.

---

## Stage 2 — Residual Compensation (decided; UPDATED 2026-08-08, M3-015)

**UPDATED 2026-08-08 (M3-015, promoted):** the RF's target is now the
RELATIVE residual, not the absolute one - see the dedicated M3-012 through
M3-015 section below for the full motivation (a direct diagnostic found the
absolute residual strongly heteroscedastic) and results (beats both naive
persistence and the previous absolute-residual model on every metric,
bootstrap-confirmed). The formula/feature-set text immediately below is
kept largely as originally written for the M3-008 promotion (historical
context for HOW the own-district lag mechanism was discovered), with the
target/formula changes layered on top via the notes in this update, the
same way M3-008 itself was layered onto the pre-M3-008 text.

**Residual target (UPDATED 2026-08-08, M3-015):**
```
relative_residual = (Actual_case_intensity − Current_Risk) / (Current_Risk + 1)
```
(`Current_Risk` = `KDE_baseline` at iteration 0, then updated each loop pass;
the "+1" denominator guard matches `rescale_kde_baseline`'s own convention.
Was the absolute `Residual = Actual_case_intensity − Current_Risk` before
this date - kept as `residual_rescaled`/`RESIDUAL_LAG_COLUMNS` in
`compensation_model.py`, still computed and still used as additional RF
features, just no longer the TARGET.)

**Features (`STAGE2_FEATURE_COLUMNS_V2`, `compensation_model.py`):**
- **Own-district RELATIVE residual lags (1-4 weeks) — added 2026-08-08, M3-015, now the dominant features (~81% combined importance).** Supersedes the M3-008 absolute-residual lags (still present as additional features, ~5% combined importance) as the RF's primary source of dynamic, per-district memory.
- Rainfall / temperature lags (2–4 weeks)
- Climate anomaly (actual vs. historical weekly average)
- Monsoon season dummy
- Elevation, population density (static covariates)
- Mahalanobis anomaly score across rainfall, temperature, elevation, population (captures multivariate anomalies while accounting for correlation between variables — added as an extra RF feature)

Note: `FEATURE_COLUMNS` (original 16) and `STAGE2_FEATURE_COLUMNS` (those 16 + the M3-008 absolute lags, 20 total) are BOTH kept unchanged in `compensation_model.py` so the frozen exploratory scripts that reproduced pre-M3-015 findings (`alpha_sweep.py`/M3-006, `stage2_experiments.py`, `stacked_persistence_experiment.py`/M3-011) stay byte-for-byte reproducible if rerun - verified directly post-promotion, not assumed. The official model uses `STAGE2_FEATURE_COLUMNS_V2 = STAGE2_FEATURE_COLUMNS + RELATIVE_LAG_COLUMNS` (24 total) instead.

**Model:** Random Forest Regression, `relative_residual` as target (UPDATED 2026-08-08, M3-015; was `residual_rescaled`).

**Iterative loop — UPDATED 2026-08-05 (M3-008): capped at `MAX_ITERATIONS=1` by design, not 4.**
```
Risk_t = Risk_(t-1) + alpha * predicted_relative_residual_t * (Risk_(t-1) + 1)
```
(UPDATED 2026-08-08, M3-015: the multiplicative reconstruction term is new;
was `Risk_t = Risk_(t-1) + alpha * predicted_residual_t` before this date -
the reconstruction from a relative-residual prediction back to an absolute
Risk value is exact, not approximate, by construction.)

`alpha = 1.0` (no shrinkage — UPDATED 2026-08-05, was 0.05; see "Stage 2
Implementation Status" for the full M3-008 reasoning; unchanged by M3-015).
The own-district residual lag features give the RF a genuine dynamic anchor
even for a held-out district under spatial CV, which resolves the
extrapolation instability that originally forced alpha down to 0.05
(M3-004) — alpha=1.0 remains the best-performing choice. The relative-
residual reformulation (M3-015) achieves a ~61% MAE reduction over Stage 1
alone, AND (unlike the M3-008 absolute-residual version) a genuine,
bootstrap-confirmed win over the naive-persistence baseline too - see the
M3-012 through M3-015 section below.

Critically, **the loop is capped at 1 iteration, not run to convergence**:
the residual lag features are computed ONCE, fixed relative to `Risk_0`
(a historical fact, not a moving target), so retraining on iteration t's
evolving residual while those features still describe "relative to
Risk_0" is theoretically incoherent past iteration 1 — verified empirically
before capping (not assumed): running iterations 2-4 anyway produced an
OSCILLATING, non-converging `max_delta` (578→240→167→190) that
progressively degraded an already-excellent iteration-1 result. The strict
numeric convergence check (`max(|Risk_t − Risk_(t-1)|) < ε`) and the
Moran's I check are still computed and logged every run (diagnostic value
— Moran's I stays non-significant, confirming Stage 1 alone still captures
the spatial autocorrelation, per the original "Why the loop converges in 1
iteration" finding below), they just no longer gate a second iteration.

**Final output:** `Risk_t` (iteration 1) = Hybrid Risk Map, **clipped at 0**
(case counts cannot be negative — UPDATED 2026-08-05, was not clipped;
see "Stage 2 Implementation Status" for why the decision changed),
exported as CSV for the dashboard.

### Stage 2 Implementation Status

**Feature engineering + residual target (implemented 2026-07-28)** —
`src/module3_spatial/feature_engineering.py` merges `master_table.csv` with
`baseline_risk.csv` on `(District, Year, Week)` and writes
`data/features/module3/stage2_feature_table.csv` (25,223 rows, 23
columns).

Two column choices the spec above leaves implicit were pinned down:
- **"Rainfall" / "temperature"** each map to ONE canonical column:
  `rain_sum (mm)` and `temperature_2m_mean (°C)` - not every rainfall/temp
  column in `master_table.csv`. `precipitation_sum (mm)` was excluded as a
  rainfall candidate because it is identical to `rain_sum (mm)` in this
  dataset (Sri Lanka has no snow, so Open-Meteo's rain/precipitation
  totals never diverge).
- **"Population density" is not actually a column in `master_table.csv`**
  (only raw `Estimated_Population` is) - it is derived in
  `compute_population_density()` from the same reprojected GADM Level-1
  polygons `kde_baseline.py` already uses for centroids/Queen weights
  (`Estimated_Population / district land area`), rather than mislabeling
  the raw headcount as a density. Sanity-checked against real Sri Lankan
  demographics: Colombo highest (3,356/km²), Mullaitivu lowest (41/km²).

Feature set (16 columns beyond the 4 keys + 3 target-related columns):
`rain_sum (mm)`, `temperature_2m_mean (°C)` (current-week raw values),
`rainfall_lag_2/3/4`, `temperature_lag_2/3/4`, `rainfall_anomaly`,
`temperature_anomaly`, `monsoon_indicator_SW`, `monsoon_indicator_NE`,
`elevation_m`, `Estimated_Population`, `population_density`,
`mahalanobis_anomaly_score`.

Design notes:
- Climate anomaly uses the historical mean for that (District, calendar
  Week) across **all years**, not a strictly-prior-years expanding
  window - defensible here because Module 3's validation axis is spatial
  K-means CV (Open Questions #4/5), not a temporal walk-forward split, so
  a full-sample per-week mean does not leak across folds the way it would
  under Module 1/2's temporal CV.
- Lags use `.shift()` on each district's own time-ordered rows, not
  calendar-week arithmetic - the ~2 known genuinely-absent (District,
  Year, Week) cells (see Stage 1's KDE fix) mean a shifted value could, in
  that rare case, be the previous AVAILABLE week rather than strictly N
  calendar weeks prior. Module 3 does not impute (no such decision is
  recorded), so this is an accepted, documented limitation.
- Mahalanobis score is computed against the FULL dataset's mean/covariance
  (not per-district) - it measures how unusual a district-week's
  combination of the 4 variables is relative to the whole series.
- **NaN from lags (series start) are KEPT, not dropped**: 50/75/100 rows
  per lag depth (2/3/4 weeks × 25 districts) - this is a feature table,
  not a training matrix; drop-vs-impute is deferred to the RF-training
  step, which may want different handling per lag depth.

**Random Forest compensation model, single-pass (implemented 2026-07-28)**
— `src/module3_spatial/compensation_model.py`. Trains on 25,123 rows
(after dropping 100 series-start rows lacking full `lag_4` history),
evaluated under 5-fold spatial K-means CV (whole districts clustered by
GADM centroid, never split across folds). **Aggregate MAE = 33.12 ± 23.57,
RMSE = 54.79 ± 29.63** across folds - the spread tracks each fold's case
volume (folds containing Colombo/Gampaha/Galle/Kalutara have higher
absolute error). Feature importance dominated by `population_density`
(0.407) and `Estimated_Population` (0.178) - together 58.5%, sensible
since the rescaled KDE baseline already captures pure spatial-proximity
redistribution. Models are `.gitignore`d (not committed - regenerate via
`python -m src.module3_spatial.compensation_model`); metrics CSVs are
committed (`outputs/metrics/module3/rf_stage2_metrics.csv`,
`rf_feature_importance.csv`, `spatial_cv_folds.csv`).

**Iterative refinement loop (implemented 2026-07-28)** —
`src/module3_spatial/iterative_loop.py`. Retrains every iteration via the
SAME 5 spatial CV folds, producing out-of-fold `predicted_residual_t` (a
district's prediction always comes from a model that never saw it) -
chosen over reusing a frozen model (mathematically cannot converge, since
its output doesn't depend on the evolving `Risk_(t-1)` state) or in-sample
retraining (would overfit its own target, "converging" via memorization
rather than genuine correction).

**Critical finding**: the literal spec's formula
(`Risk_t = Risk_(t-1) + predicted_residual_t`, no damping) DIVERGES under
honest out-of-fold evaluation - `max_delta` grew every iteration (192.6 →
1094.1) and `Risk` reached physically nonsensical negative values (down to
-1414). Root cause: several features (`population_density`,
`Estimated_Population`, `elevation_m`) are static per-district, so
out-of-fold prediction for a held-out district is genuine extrapolation
with real error - adding that error back at full magnitude compounds
iteration over iteration (the instability gradient boosting avoids via a
learning rate). Fixed by adding `alpha = 0.05` shrinkage
(`Risk_t = Risk_(t-1) + alpha * predicted_residual_t`) - empirically
tested `alpha ∈ {1.0, 0.3, 0.15, 0.05}`; across every value, aggregated
Moran's I of the residual was NEVER significant even from iteration 1
(p_sim ≥ 0.14 throughout), meaning the spatial-clustering convergence
criterion is essentially always trivially satisfied here - the real
bottleneck is purely the numeric `max_delta < epsilon` bound, which scales
almost linearly with alpha. `alpha = 0.05` converges cleanly at
**iteration 1**: `max_delta = 9.63 < epsilon = 12.98`, Moran's I not
significant (I = -0.158, p_sim = 0.147). Full alpha comparison and
rationale: `EXPERIMENT_LOG.md` M3-004.

**Alpha tradeoff - corrected framing**: an earlier draft described
alpha=0.3 and alpha=0.15's behavior as "decelerating." Checked against the
actual per-iteration numbers and found imprecise: alpha=0.3's `max_delta`
growth rate is itself ACCELERATING (+13%, +22%, +24% per step), just far
less severely than alpha=1.0's catastrophic blowup - reduced-severity
divergence, not deceleration. Alpha=0.15 nearly plateaus for two
iterations before ticking back up. Neither converges within the
4-iteration budget. Accurate framing: smaller alpha dramatically slows the
RATE of divergence relative to the unshrunk formula - a genuine
stability-vs-speed-of-convergence tradeoff (tunable hyperparameter, not
evidence the architecture is broken), not a clean "smaller alpha
decelerates toward convergence" story. Only alpha=0.05 (chosen) actually
satisfies the convergence criterion within budget - alpha=0.15/0.3 are
documented as a rejected tradeoff, never reported as an alternative
"final" result (a follow-up request to test alpha=0.15's fit quality
separately was dropped for this reason - see `EXPERIMENT_LOG.md` M3-005).

**Why the loop converges in 1 iteration - verified, not assumed**: the
spatial-clustering half of the convergence check is satisfied immediately,
but by **Stage 1's KDE baseline alone, not the RF correction**. Verified
by computing Moran's I on `Number_of_Cases - Risk_0` directly (zero RF
involvement): **I = -0.166, p_sim = 0.133 (not significant)** - essentially
identical to the post-RF-correction result (I = -0.158, p_sim = 0.147).
The RF's single pass did not remove residual spatial autocorrelation;
there was no significant autocorrelation left for it to remove - Stage 1's
KDE baseline already did that job (consistent with its own Moran's
I = 0.70 finding: the baseline genuinely captures the spatial clustering
structure). The RF's actual contribution in this loop is therefore
district-level burden correction (population/climate-driven, per the
58.5% combined feature importance of `population_density` +
`Estimated_Population` above), NOT further spatial declustering. This
distinction was checked empirically (not assumed) after an initial,
looser causal claim was proposed and found to need correction - see
`EXPERIMENT_LOG.md` M3-004's "Self-Correction" note. The dual-criterion
framework remains general: a noisier dataset or a coarser spatial baseline
that left genuine residual clustering behind would engage the
spatial-convergence criterion and drive additional iterations.

Output: `data/features/module3/hybrid_risk_map.csv` (25,123 rows,
`District, Year, Week, Number_of_Cases, Risk, Residual_final,
n_iterations, converged`) and
`outputs/metrics/module3/iterative_convergence_log.csv` (per-iteration
risk range, max_delta, Moran's I, p_sim, significance - one row here,
since it converged at iteration 1). `corr(Risk, Number_of_Cases) = 0.82`.
216 rows (0.86%) have a small negative `Risk` (min -2.32) - a minor
overshoot on near-zero-case district-weeks, not clipped (not requested,
and small enough not to be a stability concern) - flagged here rather than
silently left unmentioned.

**Evaluation (implemented 2026-07-29)** —
`src/module3_spatial/evaluate.py`. Compares Stage 1 alone (`Risk_0`, the
rescaled KDE_baseline) against Stage 2 final (`Risk`, post iterative loop)
on fit to actual case counts:

| Metric | Stage 1 alone | Stage 2 final | Change |
|---|---|---|---|
| corr | 0.8243 | 0.8205 | -0.0037 |
| MAE | 20.19 | 20.54 | +1.74% (worse) |
| RMSE | 47.30 | 47.72 | +0.87% (worse) |

**Verified, honest null/negative result - Stage 2's correction does NOT
improve aggregate fit.** Checked directly before writing this into any
report language (not assumed): `alpha = 0.05` was chosen for STRICT
convergence (see the Iterative refinement loop note above), not for
accuracy - the correction it applies is deliberately small, and a small,
genuinely out-of-fold (imperfect) correction is essentially a coin-flip on
net direction. Here it landed marginally negative. Full reasoning:
`EXPERIMENT_LOG.md` M3-005.

**A null aggregate-fit result does not mean Stage 2 has no value.** Three
points, checked against the evidence:
1. **Feature importance is a genuinely Stage-2-only capability** - Stage
   1's KDE baseline has zero covariates, so ranking `population_density`,
   `Estimated_Population`, and climate timing as burden drivers is
   diagnostic/explanatory value Stage 1 could never provide, independent
   of alpha or convergence outcome.
2. **Alpha=0.05 was a stability/convergence design choice, not a modeling
   failure** - see the "Alpha tradeoff - corrected framing" note above.
3. **The null result is itself evidence of methodological rigor**:
   verified directly (catching an index-alignment bug in the process, not
   assumed) and reported transparently rather than reframed around a more
   flattering metric.

Also generates `outputs/figures/module3/convergence_plot.png` (max_delta
vs. epsilon, Risk range per iteration - a single point, honestly, since
the loop converged at iteration 1) and `feature_importance.png` (all 16
features, sorted), plus a consolidated
`outputs/metrics/module3/results_summary.txt` for the report's Results
chapter.

---

## Stage 2 Promotion: Own-District Residual Lags (2026-08-05, M3-008)

**Supersedes the null/negative result above.** The above section (M3-005,
2026-07-29) is kept as historical record, not deleted - it was a correct,
honestly-verified finding at the time, using the original 16-feature set.
This section documents what changed and why.

**Finding**: none of the original 16 features gave the RF any information
about a district's own recent case trajectory - every feature was either
static per-district (population/elevation) or current-week climate. Added
`residual_rescaled_lag_1/2/3/4` (own-district lags of the rescaled
residual, same `.shift()` pattern already used for climate lags) and
tested via a standalone ablation (`src/module3_spatial/
stage2_experiments.py`) before promoting - checked, not assumed, per this
module's own established discipline:

| Config | Out-of-fold residual MAE | Best final MAE (Stage 1 alone: 20.54) | Best alpha |
|---|---|---|---|
| Original 16 features | 34.71 | 20.91 | 0.05 |
| + winsorized target only | 32.87 | 20.89 | 0.05 |
| + leave-one-district-out CV only | 34.86 | 20.83 | 0.05 |
| **+ residual lags** | **10.08** | **10.08** | **1.0** |
| + residual lags + winsorized + LOO | 9.96 | 9.96 | 1.0 |

Winsorizing and leave-one-out CV alone changed almost nothing - the entire
improvement is the residual lag features. Verified not a leakage artifact:
`kde_baseline_rescaled[t]` only ever uses week *t*'s own case counts, never
*t-1*'s, so the lag-1 correlation (raw `corr(residual_rescaled,
residual_rescaled_lag_1) = 0.84`) reflects genuine week-to-week epidemic
persistence, not shared computational lineage.

**Promoted to the official pipeline**: `compensation_model.py` (feature
set, `STAGE2_FEATURE_COLUMNS`), `iterative_loop.py` (`SHRINKAGE_ALPHA=1.0`,
`MAX_ITERATIONS=1` - see the updated Stage 2 spec above for why the loop no
longer runs to convergence), `evaluate.py`, `forecast_future.py` (needs the
forecast week's own real historical residual lags too - computed from
`baseline_risk.csv` + real reported `Number_of_Cases`, not a forecast
value, since even the forecast week's lag_1..4 always look strictly
backward into already-reported weeks).

**Official result after promotion**: corr 0.8241 → 0.9554, MAE 20.54 →
9.96 (~51% reduction), RMSE 48.20 → 25.06. Feature importance now
dominated by `residual_rescaled_lag_1` (63.9%) + `lag_2` (25.9%) = 89.8%
combined; `population_density`/`Estimated_Population` (previously 58.5%
combined) drop out of the top 10 entirely.

**Clipping decision changed**: alpha=1.0's unshrunk correction widens the
negative-Risk tail from the old "minor overshoot" (216 rows, max magnitude
2.32, not clipped) to 1,211 rows (4.82%, median still small at -0.94, but
a genuine tail down to -112.87) - large enough to be a physically
nonsensical "negative case count," not a rounding-scale artifact. Verified
before clipping (not assumed): clipping at 0 is a strict improvement on
every metric (not a trade-off), so `iterative_loop.py` and
`forecast_future.py` now both clip `Risk`/`Risk_forecast` at 0.

**What this changes about Stage 2's framing**: the module's Stage 2 was
originally scoped as an "environmental/demographic residual correction"
(see this file's Purpose section). This result means Stage 2's real power
is short-term epidemic persistence, with climate/demographics now playing
a secondary role - a genuine, deliberate reframing, not a silent scope
creep. Report language should reflect this rather than keep describing
Stage 2 as primarily an environmental correction step.

### Documentation Updated
`RESEARCH_DECISIONS.md` (Decision 032), `EXPERIMENT_LOG.md` (M3-008),
`QUESTIONS_FOR_DEFENSE.md`, `CHANGELOG.md`.

---

## Stage 2 vs. Naive Persistence Baseline (2026-08-04, M3-010/M3-011)

**Important caveat on the "51% MAE reduction" headline above.** With
`residual_rescaled_lag_1` + `lag_2` at 89.8% combined feature importance,
the obvious next check is whether the RF actually beats the trivial
arithmetic of carrying last week's own residual forward with no model at
all (`predicted_residual_t = residual_rescaled_lag_1`, combined with
`Risk_0` via the same alpha/clipping formula the official model uses -
`src/module3_spatial/persistence_baseline.py`, M3-010). It does not, on
every metric:

| Model | corr | MAE | RMSE | rows clipped at 0 |
|---|---|---|---|---|
| Stage 1 alone (Risk_0) | 0.8241 | 20.5363 | 48.1989 | - |
| Naive persistence (no model) | 0.9493 | **9.4386** | 26.6343 | 2,296 (9.1%) |
| Stage 2 RF, official | **0.9554** | 9.9621 | **25.0601** | 1,211 (4.8%) |

Naive persistence alone recovers about 93% of the total MAE reduction over
Stage 1 (20.54 -> 9.44 vs. the RF's 20.54 -> 9.96) - **the RF is
marginally WORSE than a zero-modeling baseline on MAE.** It remains better
on correlation and RMSE, and clips roughly half as many rows to zero
(4.8% vs. 9.1%), which is direct evidence it dampens the naive predictor's
more frequent and more severe overshoots by using climate/demographic/
monsoon context persistence cannot see.

**Corrected framing**: Stage 2's genuine, defensible contribution is
controlling the severity of large errors/overshoots (RMSE, clipping rate),
NOT beating a naive baseline on typical-case accuracy - report language
should present the naive-persistence comparison alongside the MAE
reduction, not let the 51% figure stand alone as if the RF were the sole
source of it.

**A stacked fix was tried and rejected (M3-011), not just accepted as a
limitation.** Hypothesis: have the RF predict only the correction beyond
persistence (`target = residual_rescaled - residual_rescaled_lag_1`) so it
spends its split budget on the remaining signal instead of implicitly
reconstructing persistence through splits on lag_1 - motivated by RFs not
being linear (unlike a linear model, pre-subtracting a dominant feature's
effect is not mathematically equivalent to including it as a plain input).
Tested directly: the stacked version is worse than BOTH naive persistence
AND the official RF on every metric (corr 0.9487, MAE 11.0088, RMSE
26.9565) - rejected cleanly, not pursued further without a new, specific
reason to expect a different variant to behave differently.

**Decision: keep the official Stage 2 RF (predicts the raw residual
directly) as Module 3's sole reported model** - neither naive persistence
nor the stacked correction is a strict improvement over it once RMSE and
outlier control are weighed alongside MAE, and for an outbreak-hotspot use
case, damping severe over/undershoot is arguably more operationally
relevant than shaving typical-case error.

### Documentation Updated
`EXPERIMENT_LOG.md` (M3-010, M3-011), `QUESTIONS_FOR_DEFENSE.md`,
`CHANGELOG.md`. `results_summary.txt` now includes the persistence-baseline
comparison table (`evaluate.py`).

---

## Stage 2: Four Follow-Up Compensation Mechanisms Tested (2026-08-08, M3-012 through M3-015)

Following directly from M3-010/M3-011's finding that the official RF loses
to naive persistence, four genuinely different mechanisms were tested in
sequence - each one either ruled out honestly or advanced only after
surviving a stress test, per this module's established discipline.

**M3-012 - re-evaluate with a hotspot-ranking metric instead of MAE/RMSE.**
Module 3's actual purpose is spatial hotspot detection, not case-count
regression - Spearman rank correlation and precision@k (does the model
correctly flag the top-k highest-risk districts each week) were added as a
companion evaluation lens. Result: naive persistence wins on this lens too
(Spearman 0.849 vs. the RF's 0.813; precision@5 0.784 vs. 0.759) - this did
not rescue the RF, it confirmed the gap under a second, independent metric.
Kept permanently in `results_summary.txt` alongside MAE/RMSE, not as a
replacement (`hotspot_ranking_evaluation.py`).

**M3-013 - blend the RF's and persistence's final predictions** (not
stacking, which M3-011 already rejected - this leaves both models
unchanged and mixes their outputs, `Risk_blend = w*Risk_RF +
(1-w)*Risk_persistence`, weight chosen out-of-fold per spatial fold).
Stress-tested with a week-level paired bootstrap before trusting the
aggregate table (which initially looked like a clean win): the blend is a
real, statistically robust improvement over the RF alone (all bootstrap CIs
favorable), but a statistical TIE with persistence on MAE/precision@5 and a
real, significant LOSS on Spearman rho. **Not adopted** - narrower value
only (`blended_persistence_rf.py`).

**M3-014 - isotonic calibration, Module 2's own compensation mechanism**
(recalibrate a raw score against actual outcomes, zero covariates - adapted
from Module 2's Platt/isotonic Stage 2). Motivated by a real, committed
diagnostic: every model under-predicts systematically in its lowest-risk
decile (actual cases 57-139% higher than predicted there). **Failed
cleanly, and the failure was root-caused, not left unexplained**: degradation
concentrated almost entirely in the fold containing Colombo/Gampaha (the
highest case-magnitude fold by a wide margin) - the calibration curve, fit
on the other 4 (lower-magnitude) folds, has no data to extrapolate from and
clips Colombo's real range to a severe underprediction. This is a structural
mismatch between calibration's implicit same-range assumption and Module 3's
geographically-clustered CV folds (unlike Module 2's random folds, where
every fold shares a similar distribution) - **rejected**
(`isotonic_calibration.py`).

**M3-015 - model the RELATIVE residual, not the absolute one - the strongest
result in this arc.** A direct diagnostic (not assumed) found Stage 1's raw
error strongly heteroscedastic (corr(Risk_0, |residual|) = 0.78) - every
prior mechanism modeled the absolute residual, letting the largest outbreak
weeks dominate the learning signal. Modeling
`(Number_of_Cases - Risk_0)/(Risk_0+1)` instead, with an exact
reconstruction back to absolute Risk, produces an RF that beats BOTH naive
persistence and the official RF on every metric, confirmed via a week-level
bootstrap (CIs entirely favorable, not a raw-aggregate artifact) and broad
across 4 of 5 spatial folds. Two honest caveats: RMSE's win concentrates in
the highest-volume fold (the official RF still wins RMSE in 3 of the other
4), and the model does notably worse at the NE-monsoon representative week
(2021 Wk1 - already flagged in M3-001 as the one structurally non-clustered
week). **Promoted to official Stage 2 (2026-08-08), user-confirmed** - see
`EXPERIMENT_LOG.md` M3-015 for the full numbers and the promotion's
post-hoc verification (regenerated `results_summary.txt`/
`hotspot_ranking_evaluation.csv` reproduce M3-015's own validated figures;
frozen scripts M3-006/M3-011 re-verified unaffected).

A companion diagnostic ruled out spatial spillover before M3-015 was built:
a Queen-contiguous neighbor's residual lagged one week correlates -0.30 with
a district's own current residual, but that drops to a negligible 0.03
partial correlation once the district's own lag_1 is accounted for -
neighboring districts' errors carry no information a district's own recent
history doesn't already provide.

### Documentation Updated
`EXPERIMENT_LOG.md` (M3-012 through M3-015), `research_context/
QUESTIONS_FOR_DEFENSE.md`, `research_context/CHANGELOG.md`.

---

## Visualization: Continuous Risk Surface (implemented 2026-07-29)

**Rendering-layer technique only — not a new modeling stage.** Neither the
choropleth (one flat color per district polygon) nor the original Folium
heat-cloud tab (25 district centroids run through Leaflet's generic
`HeatMap` plugin, `radius=45, blur=35`) visually showed the spatial
blending that Stage 1's KDE baseline already computes numerically — a
point between two high-risk neighbouring districts (e.g. the
Colombo/Gampaha border) should read hotter than a point between a
high-risk and a low-risk district (e.g. Colombo/Kalutara), driven by the
same kernel math already validated via Moran's I, not by an arbitrary
Leaflet blur radius.

`src/module3_spatial/risk_surface.py` interpolates the 25 already-computed
`Risk` scores (`hybrid_risk_map.csv`) onto a fine spatial grid. The grid is
clipped to Sri Lanka's landmass (`shapely.contains_xy` against the union of
GADM district polygons) so the surface never colors the ocean/India.

**Interpolation method - three attempts, two rejected, verified
numerically at each step (not assumed):**
1. **Nadaraya-Watson kernel average, Stage 1's own
   `silverman_covariance` bandwidth** (tuned for a country-wide Moran's I
   clustering TEST). Rejected: on 2017 Wk29 (Colombo 1285 / Gampaha 1296 /
   Kalutara 1141, a genuine 12% Gampaha-vs-Kalutara gap), the
   Colombo-Gampaha vs. Colombo-Kalutara midpoints came out only **1.3%**
   apart - the wide, country-scale bandwidth let half the country's
   districts dilute the local signal.
2. **Nadaraya-Watson, per-district bandwidth** (each district's own mean
   distance to its Queen-contiguous neighbours, reasoning that Sri Lanka's
   districts vary too much in spacing for one shared bandwidth). Rejected,
   worse than attempt 1: different districts now had differently-shaped
   kernels, breaking the symmetry a midpoint calculation depends on - on
   the same 2017 Wk29 check this **reversed** the expected order
   (Colombo-Gampaha 860.7 < Colombo-Kalutara 863.0).
3. **k-nearest-neighbour Inverse Distance Weighting (IDW / Shepard's
   method), k=4** (chosen): `surface(x) = Σ_{i∈kNN(x)} Risk_i / d(x,i)^power
   / Σ_{i∈kNN(x)} 1/d(x,i)^power` - only the 4 physically closest districts
   contribute at all; every other district gets exactly zero weight rather
   than a diluting tail. `power=2` (the IDW default) already fixed the
   direction: **1269.8 vs. 1210.7** (4.9% gap, correctly higher for
   Colombo-Gampaha) - the first result matching the intended "risk points
   toward whichever neighbour has more cases" behaviour.

**Further narrowed on request (2026-07-30).** Swept `k ∈ {2..5} x power ∈
{2,3,4,6}` against the same check: the gap grows toward a ~6.4% ceiling
(the plain 2-district average - the limit as only the nearest district
matters) as `power` increases, with diminishing returns past ~4.
`power=4` (adopted; `k` stays 4, avoiding `k∈{2,3}`'s more blocky,
sharply-faceted look) sits close to that ceiling - **1287.9 vs. 1213.3**
(6.1% gap) - and, more importantly for "narrowing," steepens the falloff
away from each district's own centroid, visibly shrinking the hot zone's
footprint (less bleed into Kegalle/Ratnapura beyond the immediate
Colombo/Gampaha/Kalutara cluster - compare
`risk_surface_peak_week.png` before/after in git history).

This stays in `Risk`'s own units - a grid point at a district's own
centroid comes out ≈ that district's own Risk score - and blends only
toward the district's nearest few neighbours, not the whole country.

**Is the map "test set"-safe / not overfit-in-sample?** (question raised
2026-07-30) Yes, by construction, for EVERY week - not just one. Module 3
has NO temporal train/test split anywhere (unlike Module 1/2's fixed
104-week / 2-year holdout blocks); its only validation axis is 5-fold
SPATIAL K-means CV (districts held out, never weeks - see
`compensation_model.py::build_spatial_folds`/`run_spatial_cv`, reused
identically inside `iterative_loop.py::out_of_fold_predict`). Every row of
`hybrid_risk_map.csv` - the file this surface interpolates - already comes
from a model that never saw that district during training, regardless of
which (Year, Week) is selected. There is consequently no separate
"held-out test week" to switch this visualization to: the whole file is
uniformly out-of-fold in the one sense Module 3 validates. A genuine
temporal holdout (weeks never touched during training, mirroring Module
1/2) does not currently exist for Module 3 and would be new methodology,
not a visualization change, if ever wanted.

Explicitly **not** a revisit of the already-rejected GWR-as-a-model
decision (see "Rejected approach" below): the kernel here interpolates a
fixed set of already-computed Stage 2 scores for display; it does not
re-fit anything, does not feed back into the RF or iterative loop, and
does not change any committed Stage 1/Stage 2 output.

Two consumers:
- **Static report figure** — `run_risk_surface()` (CLI:
  `python -m src.module3_spatial.risk_surface [--year YYYY --week N]`), a
  1000m-resolution grid rendered via matplotlib `pcolormesh`. Defaults to
  Stage 1's already-identified peak week (2017 Wk29), saving to
  `outputs/figures/module3/risk_surface_peak_week.png`; an explicit
  `--year`/`--week` instead saves to `risk_surface_{year}_wk{week}.png`
  (never overwrites the canonical figure) - added to let other weeks be
  spot-checked. Also logs a direct sanity check comparing the
  Colombo-Gampaha midpoint against the Colombo-Kalutara midpoint (verified
  under the final kNN-IDW, `k=4, power=4` method: 1287.9 vs. 1213.3 at 2017
  Wk29 — see the "Interpolation method" numbered list above for the two
  earlier, rejected Gaussian attempts and the `power` sweep on this same
  check). Spot-checked on three very different weeks (2026-07-30) and
  confirmed sensible in each: a near-zero "low" week (2007 Wk13, values
  auto-scale to a tiny range, no degenerate output); the NE-monsoon
  representative week (2021 Wk1) - the ONE week Stage 1's own Moran's I
  check found NOT significantly clustered (I=0.031, p=0.279) - correctly
  shows the hot zone shift away from the west entirely (to Jaffna/Mannar
  and the Ampara/Batticaloa coast instead), rather than forcing the same
  western-cluster story every time; and the latest real week (2026 Wk21),
  correctly rescaled to its much lower case counts, with Kalutara edging
  out Gampaha - exactly what that week's real numbers say, not a bug.
  **Superseded (2026-08-04, Decision 031)**: a genuine FUTURE-week map was
  previously deliberately out of scope, since Module 3 had no forecasting
  capability of its own - both Stage 1's KDE weighting and Stage 2's
  residual target require a known `Number_of_Cases`, and `hybrid_risk_map.csv`
  stops at the latest week with real reported data. This has now been
  built (`src/module3_spatial/forecast_future.py`) by feeding Module 1's
  forecasted case counts in as the required cross-module input - see the
  new "Forward Operational Hotspot Forecast" section below and
  `RESEARCH_DECISIONS.md` Decision 031 for the full reasoning.
- **Dashboard — four switchable views** (`render_operational_page()`,
  `pages.py`), all real data (`hybrid_risk_map.csv` + the same GADM
  centroids), no synthetic values in any of the four:
  1. **District boundaries (choropleth)** — `_hybrid_risk_choropleth()`,
     precise polygons colored by Hybrid Risk (`px.choropleth`,
     `color_continuous_scale="YlOrRd"`), thick black outline on the
     selected district. The original view, restored 2026-07-30 (see the
     root-cause note below for why it was removed and then brought back).
  2. **Heat cloud (Folium)** — `_hybrid_risk_folium_heatmap()` renders a
     1500m-resolution grid as a geographically-anchored raster image
     (`risk_surface.py::risk_surface_rgba` + `grid_lonlat_bounds`, added
     via `folium.raster_layers.ImageOverlay`) — **not** Leaflet's
     point-based `HeatMap` plugin (see the root-cause note below for why
     that was replaced). District boundaries drawn on top as a no-fill
     `folium.GeoJson` outline (thick black for the selected district, thin
     white otherwise) SOLELY so a viewer can see the raster color visibly
     crossing them — the raster itself deliberately ignores district shape.
  3. **Hotspot markers (precise)** — `_hybrid_risk_circle_map()`, added
     2026-07-30: one `folium.CircleMarker` per district centroid, radius
     AND fill color both driven by that district's real Hybrid Risk value
     (8-25px, `branca.colormap.linear.YlOrRd_09` - same color family as
     the choropleth, with its legend added via `colormap.add_to(fmap)`).
     Selection is marked via the marker's OWN BORDER (thick black vs. thin
     white), not its fill, so the fill stays purely risk-driven (no
     conflict with the size/color double-encoding). A precise, exact-value
     complement to the heat-cloud's smoothed, border-blended interpolation
     - this view makes no spatial claim beyond each district's own number.
  4. **Heat glow (Uber-style)** — `_hybrid_risk_uber_heatmap()`, added
     2026-07-30 at the user's explicit spec, then revised twice more on
     direct visual feedback the same day. A purely stylistic view -
     deliberately kept separate from `_hybrid_risk_folium_heatmap()`
     rather than modifying it.

     **v1 (as originally specced)**: dark CartoDB basemap
     (`tiles='https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'`)
     + Leaflet's POINT-BASED `HeatMap` plugin (`radius=30, blur=25,
     max_zoom=13`) over the 25 district centroids.

     **v2, feedback "not dark blue, glow should follow each district's
     shape, not always a circle"**: replaced the point-based `HeatMap`
     (which can only ever render CIRCULAR gradients - no concept of a
     district's real shape) with a `folium.GeoJson` fill of each
     district's ACTUAL polygon, colored by its Risk value, with a CSS
     `blur()` on the SVG paths to soften the hard edges into a glow -
     genuinely spreads from within each district's own footprint now, not
     a generic circle. (Reintroducing the point-based `HeatMap` at all was
     already a known-risky choice - it's exactly what `ImageOverlay`
     replaced in the 2026-07-29 "equal bubbles" fix below; ONLY safe here
     because this view is now built without it.)

     **v3, dark-blue fix (took two real, verified bugs, not one)**:
     - CSS wasn't reaching the page AT ALL, regardless of content -
       verified by inspecting the live rendered iframe DOM directly (not
       assumed from a screenshot). Traced into `branca.element` source:
       `folium.Element(css).add_to(m)` and `m.get_root().html.add_child(...)`
       both silently do nothing when rendered as a descendant of a `Map` -
       only `MacroElement.render()` (what `TileLayer`/`GeoJson` actually
       are, hence why THEY already worked) has the side effect of
       registering a child's `html`/`script` macro onto the current root
       Figure. Fixed with `_InlineCss`, a two-line `MacroElement`
       subclass, `.add_to(m)`'d like every other layer.
     - Once injection was fixed, a `mix-blend-mode: screen` colored
       overlay `<div>` (tried first, assuming the basemap was pure black)
       still showed no visible tint - likely a z-index/stacking-context
       mismatch against Leaflet's transform-positioned panes. Sampled
       actual rendered pixels directly (not assumed): CartoDB `dark_all`'s
       ocean tiles are dark GREY (~RGB 30-38), not pure black. Replaced
       with a direct `filter: sepia(1) hue-rotate(190deg) saturate(3)
       brightness(0.6)` on `.leaflet-tile-pane` instead - simpler, no
       separate element's stacking position to get right - confirmed via
       screenshot to produce a genuine navy-blue basemap.

**Root-caused and fixed (2026-07-29): map rendered totally blank.** The
Folium map used to sit inside the second panel of `st.tabs(["District
boundaries (choropleth)", "Heat cloud (Folium)"])`. Streamlit tabs hide
inactive panels with CSS (`display:none`), they don't skip rendering them
— so Leaflet initialized inside a zero-width/zero-height hidden container
on first page load and never recovered its size even after the tab was
clicked (no `invalidateSize()` call wired up on tab-switch). Fixed by
dropping the tabs entirely: the choropleth (which was pure duplication of
what the heat-cloud now shows better, with the added drawback of solid
flat per-district fill — the opposite of this section's goal) was removed,
and the Folium map is now the single, always-visible view under "Module 3
— spatial hotspot map", mounted while visible from the first render.
`_hybrid_risk_choropleth` was deleted from `pages.py` (was otherwise
unused after this).

**Choropleth restored + a third view added, without reintroducing the
tabs bug (2026-07-30).** Asked to add a third "Hotspot markers (precise)"
view alongside a restored choropleth tab - i.e. exactly the 3-panel
layout whose panel-hiding behaviour caused the blank-map bug above.
`_hybrid_risk_choropleth` was recovered verbatim from git history (commit
`5c9d5fd`, pre-dating its removal) rather than rewritten from memory.
Instead of `st.tabs()` again, switched to `st.radio(..., horizontal=True,
key="module3_map_view")`: Python only constructs the ONE currently-selected
map each script rerun (a plain `if/elif/else` branch), so the other two
views are never mounted hidden at all - structurally the same bug class
cannot recur, regardless of how many views get added later. Verified live
(2026-07-30): switching between all three renders correctly with no blank
panels and no console errors; the circle-marker view specifically
confirmed via `page.frame_locator("iframe")` - found all 25
`path.leaflet-interactive` elements, clicked one, and got the expected
popup text (`"Anuradhapura\nHybrid Risk Score: 20.4\nActual Cases: 13"`).

**Root-caused and fixed (2026-07-29): heat-cloud showed separate uniform
circles ("equal bubbles") instead of a continuous surface, once zoomed in
close.** The first fix above used Leaflet's `HeatMap` plugin fed with
~7,000 grid points (one per interpolated grid cell). `HeatMap`'s
`radius`/`blur` are FIXED SCREEN PIXELS - the real-world distance between
adjacent grid points covers a different pixel span at every zoom level, so
there is only one zoom level at which a given radius happens to make
neighbouring points overlap into a smooth blend. Zoom in further (as a
user naturally would to inspect a specific area) and the same points stop
overlapping - the "continuous surface" visibly decomposes into separate
uniform-looking circles, one per grid cell, which defeats the entire
point of this feature. Fixed by replacing the point-based `HeatMap` with a
geographically-anchored raster image
(`risk_surface.py::risk_surface_rgba` - a transparent-outside-Sri-Lanka
RGBA array built directly from the interpolated grid via a `YlOrRd`
colormap, plus `grid_lonlat_bounds` reprojecting the grid's UTM corners to
lon/lat - added to the map via `folium.raster_layers.ImageOverlay`). An
image overlay scales with the map like any tile layer, so it stays one
continuous gradient at every zoom level, not just the one radius/blur
happened to be tuned for.

---

## Forward Operational Hotspot Forecast (implemented 2026-08-04, Decision 031)

**Cross-module, operational tier - see `RESEARCH_DECISIONS.md` Decision
031.** Supersedes this file's earlier (2026-07-30) "deliberately out of
scope" note for a future-week map - that note correctly identified the
exact dependency this now resolves: a future-week map needs Module 1's
forecasted case counts fed in as a hypothetical input, since Stage 1's KDE
weighting and Stage 2's residual target both require a known
`Number_of_Cases`.

`src/module3_spatial/forecast_future.py` produces a next-week hotspot
forecast (default horizon: 1 week beyond the last reported case week -
currently 2026 Wk25 → forecasts Wk26) without retraining or reconverging
anything:

1. **Case-count proxy**: reads `data/processed/module1/future_forecast.csv`
   (`horizon_step=1`'s `final_prediction` per district) - only READS this
   file, never edits anything under `module_1_forecasting/`/
   `src/module1_forecasting/`, per this module's own scope rule.
2. **Climate is real observed data, not a forecast**: verified directly -
   because Module 3's case-count reporting lags real calendar time by
   several weeks, the forecast week's actual calendar dates have typically
   already passed by the time this script runs, so every raw daily
   Open-Meteo row for that date range is tagged `climate_data_source=
   "observed"`. Only the case count is a genuine forecast; every output
   row records both `cases_source` and `climate_source` so this is never
   conflated.
3. **Stage 1**: the SAME fixed 25x25 Silverman kernel (not refit) applied
   to Module 1's forecasted case counts as weights, then mass-conserved to
   the forecast week's total forecasted cases (the forecast-week analogue
   of `compensation_model.py::rescale_kde_baseline`).
4. **Stage 2**: the already-trained frozen final RF model
   (`rf_final_model.joblib`, now trained on `STAGE2_FEATURE_COLUMNS` -
   M3-008) scores the forecast row(s); the Mahalanobis anomaly score
   reuses the PERSISTED training-time mean/covariance
   (`MODULE3_MAHALANOBIS_STATS_PATH`, written by
   `feature_engineering.py`) rather than refitting on a
   historical-plus-one-new-row sample. **Own-district residual lags
   (UPDATED 2026-08-05, M3-008)**: computed from REAL historical
   `Number_of_Cases` and Stage 1's already-committed `KDE_baseline`
   (`baseline_risk.csv`), never from a forecast value - lag_1..4 always
   look strictly backward into already-reported weeks, even at
   `horizon_step=1`.
5. **Combine once**: `Risk_forecast = Risk_0_forecast + 1.0 *
   predicted_residual` (UPDATED 2026-08-05, was 0.05 - see the Stage 2
   Promotion section above), then **clipped at 0** (case counts cannot be
   negative) - a single application of the already-decided formula, not a
   multi-iteration convergence claim (the official pipeline itself now
   caps at `MAX_ITERATIONS=1` by design, not just "happens to converge
   there" - see the updated Stage 2 spec above).

Any remaining NaN in a required feature raises an explicit error rather
than guessing - unlike Module 1's XGBoost, Module 3's Stage 2 model is a
bare `sklearn.RandomForestRegressor` with no native NaN tolerance.

Output: `data/processed/module3/future_hotspot_forecast.csv`, every row
tagged `evidence_tier="operational"` - never to be cited alongside Stage
1's Moran's I / Stage 2's spatial-CV figures in `results_summary.txt`.
Also produces a static figure
(`outputs/figures/module3/risk_surface_forecast_{year}_wk{week}.png`,
reusing `risk_surface.py`'s grid/IDW functions unchanged) and a dashboard
panel (`pages.py`, "Module 3 — next-week hotspot forecast").

Wired into `scripts/refresh_dashboard_data.py` (module3_preprocessing +
module3_forecast_future, ordered right after module1_forecast_future -
its only dependency - and before the Module 2 steps, since two pre-existing,
unrelated bugs in Module 2's own forward-scoring scripts currently abort
that orchestrator before reaching later steps).

**Note on `DEFAULT_HORIZON_WEEKS`**: only horizon=1 has been exercised and
verified. Raising it would need each later forecast week to chain in
earlier forecast weeks as pseudo-history for its own lag features (as
Module 1's `forecast_future.py` does recursively) - not yet implemented,
flagged directly in the code rather than silently assumed to work.

---

## Open Questions — now answered

1. **Are district centroids sufficient, or are finer spatial units needed?** → District centroids (25 units) are sufficient for this scope; sub-district disaggregation is noted as a limitation/future work, not implemented.
2. **How should KDE bandwidth be selected?** → Silverman's rule of thumb.
3. **What is the spatial residual target?** → `Actual case intensity − Current_Risk` (see Stage 2 above), recalculated each loop iteration.
4. **How should spatial leakage be prevented?** → Spatial K-means CV (5 folds, districts clustered by location), not random k-fold.
5. **Which spatial validation method is most suitable?** → Spatial K-means CV, per point 4.
6. **How should Module 3 outputs combine with Module 1 and Module 2?** → Historical: Module 3 exports district-week Hybrid Risk as CSV keyed by (District, Epi_Week) for the shared dashboard to consume. Forward/operational: resolved by Decision 031 - Module 3's forecast_future.py reads Module 1's `future_forecast.csv` for the forecast week's case-count proxy (read-only, one direction); Module 2's own forward risk score is independent and does not feed into or consume Module 3's output.

**Rejected approach:** Geographically Weighted Regression (GWR) — considered, not used. With only 25 spatial units, local weighting is statistically unreliable; Random Forest was chosen instead for robustness with limited-N tabular data.

---

## Evaluation Direction

- Reduction in residual variance after compensation (Stage 2 vs. Stage 1 alone)
- Moran's I of residuals, before vs. after each iteration (should trend toward non-significant)
- MAE / RMSE of the Random Forest on held-out spatial CV folds
- Feature importance (which environmental factors drive corrections)
- Spatial cross-validation performance, not random split
- **Hotspot-ranking companion metrics (added 2026-08-08, M3-012)**: Spearman
  rank correlation and precision@k (k=3, 5) between predicted and actual
  risk ordering across districts each week - matches Module 3's actual
  hotspot-detection purpose more directly than MAE/RMSE alone; reported
  alongside, not instead of, the fit metrics above.
- A naive persistence baseline (M3-010) and, where relevant, a week-level
  paired bootstrap CI (M3-013/M3-015) are the standard before any new
  compensation mechanism's aggregate metric is trusted as a genuine
  improvement - an aggregate table alone has already been shown (M3-013) to
  overstate a result that doesn't survive fold- and week-level scrutiny.

---

## Documentation Rule

Update this file when Module 3 spatial features, baseline methods, residual definition, iteration/convergence logic, or evaluation method changes.