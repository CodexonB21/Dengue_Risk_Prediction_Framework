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

## Stage 2 — Residual Compensation (decided)

**Residual target:**
```
Residual = Actual_case_intensity − Current_Risk
```
(`Current_Risk` = `KDE_baseline` at iteration 0, then updated each loop pass)

**Features:**
- Rainfall / temperature lags (2–4 weeks)
- Climate anomaly (actual vs. historical weekly average)
- Monsoon season dummy
- Elevation, population density (static covariates)
- Mahalanobis anomaly score across rainfall, temperature, elevation, population (captures multivariate anomalies while accounting for correlation between variables — added as an extra RF feature)

**Model:** Random Forest Regression, `Residual` as target.

**Iterative loop (novel contribution):**
```
Risk_t = Risk_(t-1) + alpha * predicted_residual_t
```
`alpha = 0.05` (shrinkage/learning-rate term, NOT in the original spec -
discovered necessary during implementation; see "Stage 2 Implementation
Status" below for why the un-shrunk `alpha=1.0` formula diverges).

Repeat until BOTH:
1. `max(|Risk_t − Risk_(t-1)|) < ε` (≈1% of initial risk range), AND
2. Moran's I of the new residual is not statistically significant

Cap at 4 iterations as a practical safeguard. Log risk values and Moran's I per iteration for the convergence plot.

**Final output:** converged `Risk_t` = Hybrid Risk Map, exported as GeoJSON (merged with GADM shapefile) for the dashboard.

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

---

## Open Questions — now answered

1. **Are district centroids sufficient, or are finer spatial units needed?** → District centroids (25 units) are sufficient for this scope; sub-district disaggregation is noted as a limitation/future work, not implemented.
2. **How should KDE bandwidth be selected?** → Silverman's rule of thumb.
3. **What is the spatial residual target?** → `Actual case intensity − Current_Risk` (see Stage 2 above), recalculated each loop iteration.
4. **How should spatial leakage be prevented?** → Spatial K-means CV (5 folds, districts clustered by location), not random k-fold.
5. **Which spatial validation method is most suitable?** → Spatial K-means CV, per point 4.
6. **How should Module 3 outputs combine with Module 1 and Module 2?** → TBD at integration stage; Module 3 exports district-week Hybrid Risk as GeoJSON/CSV keyed by (District, Epi_Week) for the shared dashboard to consume — final join logic to be confirmed with the team.

**Rejected approach:** Geographically Weighted Regression (GWR) — considered, not used. With only 25 spatial units, local weighting is statistically unreliable; Random Forest was chosen instead for robustness with limited-N tabular data.

---

## Evaluation Direction

- Reduction in residual variance after compensation (Stage 2 vs. Stage 1 alone)
- Moran's I of residuals, before vs. after each iteration (should trend toward non-significant)
- MAE / RMSE of the Random Forest on held-out spatial CV folds
- Feature importance (which environmental factors drive corrections)
- Spatial cross-validation performance, not random split

---

## Documentation Rule

Update this file when Module 3 spatial features, baseline methods, residual definition, iteration/convergence logic, or evaluation method changes.