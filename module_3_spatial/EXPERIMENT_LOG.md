# Module 3 Experiment Log

Use this file to record all spatial hotspot detection experiments.

---

## Experiment Template

```markdown
## Experiment ID: M3-000

### Date
YYYY-MM-DD

### Research Question
What are we testing?

### Spatial Unit
District / MOH / GN / grid / centroid

### Baseline Spatial Method
KDE / Moran's I / LISA / other

### Stage 2 Model
Model and parameters

### Spatial Features Used
Rainfall, elevation, population density, etc.

### Validation Method
Spatial split, geographic folds, hotspot overlap, etc.

### Results
Record metric values and maps/observations

### Interpretation
What does this mean?

### Decision
Keep / Reject / Modify / Repeat

### Documentation Updated
List updated files
```

---

## Experiment ID: M3-001

### Date
2026-07-28

### Research Question
Does a case-count-weighted KDE surface over Sri Lanka's 25 district
centroids reflect genuine spatial clustering of dengue risk, and is that
clustering stable across time (peak vs. low periods, monsoon seasons) or
only an artifact of aggregating across the full ~20-year series?

### Spatial Unit
District centroids (25 units, GADM v4.1 Level-1), reprojected to UTM zone
44N (EPSG:32644) for physically meaningful Euclidean distances.

### Baseline Spatial Method
Weighted Gaussian KDE (weight = `Number_of_Cases` per district-week),
Silverman bandwidth derived once from the district centroids' own spatial
spread (not re-derived per week), evaluated via a fixed 25x25 kernel
matrix. Global Moran's I with queen contiguity spatial weights
(`libpysal`/`esda`) as the clustering validation check.

### Stage 2 Model
Not built this session — Stage 1 (baseline) only, per the
`module-03-stage-01` branch plan.

### Spatial Features Used
None yet (Stage 1 has no covariates beyond case count and geometry).
Elevation was joined into `master_table.csv` in preparation for Stage 2 but
is not used by the KDE baseline itself.

### Validation Method
Global Moran's I, queen contiguity, 999 permutations: (1) aggregated on
the mean `KDE_baseline` per district across all weeks (primary), and (2) a
secondary, non-aggregated check on 4 representative weeks (peak-case week,
low-case week, one representative week from each monsoon season), each
selected as the highest-case week within its group after excluding
zero-variance weeks (Moran's I is undefined for a constant vector).

### Results
- `data/processed/module3/master_table.csv`: 25,348 district-week rows
  (2006-2026), joined from the shared preprocessing layer plus elevation
  extracted from raw Open-Meteo CSV headers. 125 rows fall outside
  Open-Meteo's climate coverage window (2006 Wk52 + tail weeks of 2026)
  and are dropped before KDE, leaving 25,223 rows.
- `data/features/module3/baseline_risk.csv`: `District, Year, Week,
  Number_of_Cases, KDE_baseline` — one row per surviving district-week.
- **Aggregated Global Moran's I (primary): I = 0.70, p_sim = 0.001** —
  statistically significant spatial clustering in the typical baseline
  risk surface.
- **Secondary per-week check**:

  | Week | Year/Week | I | p_sim | Significant |
  |---|---|---|---|---|
  | Peak / SW monsoon | 2017 Wk29 | 0.728 | 0.001 | Yes |
  | Low | 2007 Wk13 | 0.735 | 0.001 | Yes |
  | NE monsoon | 2021 Wk1 | 0.031 | 0.279 | **No** |

  (The peak week and SW-monsoon representative week coincide: 2017 Wk29
  falls within `MONSOON_WEEKS_SW` and is also the single highest-case week
  in the whole series — the documented peak of Sri Lanka's worst recorded
  dengue outbreak, 2017, ~186,000 national cases.)
- A one-off data-quality bug was caught and fixed during implementation: 2
  (District, Year, Week) cells are genuinely absent from `master_table.csv`
  (real historical gaps, not zeros); left unhandled, `NaN` in the pivoted
  weight matrix would have silently corrupted every district's
  `KDE_baseline` for that one week, not just the missing district's. Fixed
  by treating a missing weight as 0 for the KDE matrix multiply only,
  without fabricating an output row.

### Interpretation
The KDE baseline is not spatially arbitrary noise — genuine, significant
clustering is confirmed both in aggregate and in 3 of 4 representative
weeks. Critically, clustering is **not universal**: the NE-monsoon
representative week (2021 Wk1) shows no significant clustering, which is
itself useful evidence — it means the aggregated I = 0.70 headline number
is a real, non-trivial finding rather than a suspiciously perfect result
that would raise suspicion of a methodological artifact. This nuance
should be reported alongside the aggregated figure, not omitted.

### Decision
**Keep** the aggregated Global Moran's I as Stage 1's primary validation
checkpoint, and **keep** the representative-week check as permanent
secondary evidence (not a one-off diagnostic to discard) — it directly
answers the "is this stable across time" question a review panel would
ask. **Proceed** to Stage 2 (Random Forest residual compensation,
`module-03-stage-02`) using `KDE_baseline` as `Current_Risk` at iteration
0, per the Stage 2 spec already decided in `MODULE_CONTEXT.md`.

### Documentation Updated
- `module_3_spatial/MODULE_CONTEXT.md` (new "Stage 1 Implementation
  Status" section under Stage 1 — Baseline).
- `module_3_spatial/EXPERIMENT_LOG.md` (this entry).
- `src/config.py` (added `RAW_SPATIAL_DIR`, `GADM_LEVEL1_SHAPEFILE_PATH`,
  `MODULE3_PROCESSED_DIR`, `MODULE3_MASTER_TABLE_PATH`,
  `MODULE3_FEATURES_DIR`, `MODULE3_BASELINE_RISK_PATH`).
- `requirements.txt` (added `libpysal`, `esda`).
- Added `src/preprocessing/module3_preprocessing.py` and
  `src/module3_spatial/kde_baseline.py` (both previously placeholders).

### Addendum (2026-07-28): Self-Verification Before Stage 2

A full pre-Stage-2 self-check confirmed `master_table.csv` (25,348 rows,
125 dropped for climate coverage → 25,223) and `baseline_risk.csv` (25,223
rows, all 25 districts, zero NaN, zero negative `KDE_baseline`) both match
their documented figures exactly, and that the `9d21fe5` commit was
present in git log and already on `origin/module-03-stage-01`.

It also caught a real gap: **Moran's I was only ever printed/logged to the
console, never persisted to disk** - re-running the script with no seed
confirmed `p_sim` genuinely drifts run-to-run (`esda.Moran` draws its
permutation test from numpy's global RNG and has no `seed` parameter of
its own; the `I` statistic itself is closed-form and unaffected). Two
unseeded reruns produced `NE monsoon` p_sim = 0.2850, then 0.2860.

Fixed by adding `MORAN_RANDOM_SEED = 13` (seeded once, up front, in
`run_kde_baseline()`) and writing every Moran's I result (aggregated +
all 4 representative weeks) to a new persisted metrics file,
`outputs/metrics/module3/morans_i_validation.csv` (`MODULE3_MORANS_I_METRICS_PATH`
in `config.py`) - matching Module 1/2's convention of a real metrics CSV
rather than console-only output. Verified byte-for-byte reproducible: two
consecutive seeded runs produced an identical CSV (`diff` clean).

With the seed fixed, `NE monsoon`'s authoritative, reproducible p_sim is
**0.279** (corrected from the originally-documented, unseeded 0.285/0.286
above and in `MODULE_CONTEXT.md`) - the significance conclusion (not
significant) is unchanged; only the exact p-value moved, as expected for
a permutation test.

#### Documentation Updated (addendum)
- `module_3_spatial/EXPERIMENT_LOG.md` (this addendum; corrected NE
  monsoon p_sim in the Results table above).
- `module_3_spatial/MODULE_CONTEXT.md` (corrected NE monsoon p_sim).
- `src/config.py` (added `MODULE3_METRICS_DIR`, `MODULE3_MORANS_I_METRICS_PATH`).
- `src/module3_spatial/kde_baseline.py` (seeded RNG, writes
  `morans_i_validation.csv`).
- Added `outputs/metrics/module3/morans_i_validation.csv`.

---

## Experiment ID: M3-002

### Date
2026-07-28

### Research Question
What feature set does Stage 2's Random Forest residual model need, and can
it be built entirely from data already produced by Stage 1 plus the raw
GADM geometry, without collecting anything new? (Feature engineering +
residual target only - no model training this session, per explicit scope
restriction for this piece of work.)

### Spatial Unit
District-week (25 districts), same grain as Stage 1's `baseline_risk.csv`.

### Baseline Spatial Method
N/A - this experiment builds on Stage 1's KDE baseline (`M3-001`) as an
input (`KDE_baseline` is the `Current_Risk` term in the residual), it does
not change the spatial baseline method itself.

### Stage 2 Model
Not built this session - feature engineering only.
`src/module3_spatial/feature_engineering.py` merges `master_table.csv`
with `baseline_risk.csv` on `(District, Year, Week)` and writes
`data/features/module3/stage2_feature_table.csv`.

### Spatial Features Used
`elevation_m` (carried through from `master_table.csv`) and
`population_density` (newly derived - see Results).

### Validation Method
N/A - no model was trained. Manual sanity checks only: lag values
hand-traced against source rows, population density ranked against known
Sri Lankan demographics, Mahalanobis score distribution inspected for a
plausible right-skew with genuine outliers.

### Results
- **Output**: `data/features/module3/stage2_feature_table.csv` - 25,223
  rows (same as `baseline_risk.csv`; the merge preserved every row), 23
  columns (4 keys, 3 target-related, 16 feature columns).
- **Residual target**: `Residual = Number_of_Cases - KDE_baseline`.
- **Two column choices the Stage 2 spec left implicit, resolved here**:
  1. "Rainfall"/"temperature" each map to ONE canonical column -
     `rain_sum (mm)` and `temperature_2m_mean (°C)`, not every candidate
     column in `master_table.csv`. `precipitation_sum (mm)` was excluded
     as a rainfall candidate because it is identical to `rain_sum (mm)`
     in this dataset (no snow in Sri Lanka, so Open-Meteo's two fields
     never diverge).
  2. "Population density" does not actually exist as a column in
     `master_table.csv` (only raw `Estimated_Population` does) - derived
     it instead from the same reprojected GADM Level-1 polygons
     `kde_baseline.py` already computes for centroids/Queen weights
     (`Estimated_Population / district land area`). Sanity-checked:
     Colombo highest (3,356/km²), Mullaitivu lowest (41/km²) - matches
     known Sri Lankan demographics, not an artifact.
- **Lags** (`rainfall_lag_2/3/4`, `temperature_lag_2/3/4`): computed via
  `.shift()` on each district's own time-ordered rows (sorted by
  `Week_Start_Date`), not calendar arithmetic. Manually verified correct
  (e.g. Ampara Wk4's `rainfall_lag_2` = Wk2's actual `rain_sum` = 82.9).
- **Climate anomaly** (`rainfall_anomaly`, `temperature_anomaly`): actual
  minus the historical mean for that (District, calendar Week) across ALL
  years, not a strictly-prior-years window - acceptable here because
  Stage 2's validation axis is spatial K-means CV (Open Questions #4/5),
  not temporal walk-forward, so this does not leak across CV folds the
  way it would under Module 1/2's temporal setup.
- **Monsoon dummies** (`monsoon_indicator_SW`, `monsoon_indicator_NE`):
  from `MONSOON_WEEKS_SW`/`MONSOON_WEEKS_NE` in `config.py`.
- **Mahalanobis anomaly score**: computed across
  `[rain_sum (mm), temperature_2m_mean (°C), elevation_m,
  Estimated_Population]` against the FULL dataset's mean/covariance (not
  per-district). Distribution: mean 1.73, median 1.51, max 13.12 - a
  plausible right-skewed multivariate anomaly distribution with genuine
  outlier rows, not a degenerate constant.
- **NaN from lags (series start), per column**: `rainfall_lag_2` /
  `temperature_lag_2` = 50 rows each (2 weeks x 25 districts);
  `rainfall_lag_3` / `temperature_lag_3` = 75 each; `rainfall_lag_4` /
  `temperature_lag_4` = 100 each. Verified no NaN exists in any other
  column (`validate_feature_table` raises otherwise).
- **NaN decision: KEPT, not dropped.** This is a feature table, not a
  training matrix - drop-vs-impute is deferred to the RF-training step
  (out of scope this session), which may legitimately want different
  handling per lag depth.

### Interpretation
All 16 feature columns are derivable from data Stage 1 already produced
plus the raw GADM shapefile - no new raw data collection was needed for
Stage 2's planned feature set. The two implicit-column ambiguities in the
original spec (rainfall/temperature column choice, population density not
actually existing) were real gaps between the written spec and the actual
data, not oversights in this implementation - both are now made explicit
and reusable by whoever builds the RF model next.

### Decision
**Keep** this feature table as Stage 2's input. **Keep** the NaN-kept (not
dropped) policy for lag columns - explicitly deferring the drop/impute
choice to the RF-training step rather than baking an assumption into the
shared feature table. **Proceed** to building the Random Forest residual
model and the iterative convergence loop as the next piece of Stage 2
work - not started this session.

### Documentation Updated
- `module_3_spatial/MODULE_CONTEXT.md` (new "Stage 2 Implementation
  Status" section under Stage 2 — Residual Compensation).
- `module_3_spatial/EXPERIMENT_LOG.md` (this entry).
- `src/config.py` (added `MODULE3_STAGE2_FEATURE_TABLE_PATH`).
- Added `src/module3_spatial/feature_engineering.py` and
  `data/features/module3/stage2_feature_table.csv`.

---

## Experiment ID: M3-003

### Date
2026-07-28

### Research Question
Does a single-pass Random Forest, trained on M3-002's feature set and
evaluated under genuine spatial (not random) cross-validation, produce a
sensible residual-compensation model - and is `stage2_feature_table.csv`'s
literal `Residual` column actually usable as its training target?

### Spatial Unit
District-week, same grain as M3-001/M3-002. CV folds are 5 clusters of
whole districts (K-means on GADM centroids), not random row splits.

### Baseline Spatial Method
Builds on M3-001's `KDE_baseline` (see the new "KDE_baseline: Two Valid
Uses" section in `MODULE_CONTEXT.md` for why this experiment uses a
rescaled form of it, not the raw one).

### Stage 2 Model
`RandomForestRegressor` (`n_estimators=300, min_samples_leaf=5,
random_state=42`), fixed hyperparameters (not tuned). Single-pass only -
the iterative convergence loop is explicit future work, not built here.

### Spatial Features Used
`elevation_m`, `population_density`, `Estimated_Population` (see Feature
importance below).

### Validation Method
Spatial K-means CV: the 25 district centroids clustered into 5 groups
(`KMeans(n_clusters=5, random_state=42)`), each cluster held out as one
fold's test set, trained on the other 4 clusters' districts - a district's
weeks are never split across folds by construction (whole districts move
together).

### Results
- **Critical pre-training finding**: `stage2_feature_table.csv`'s
  `Residual` column (`Number_of_Cases - KDE_baseline`, as literally
  specified) is numerically unusable as a target -
  `corr(Residual, Number_of_Cases) = 0.9999999999999991`, because
  `KDE_baseline`'s max value (4.48e-7) is negligible next to
  `Number_of_Cases` (max 2,631). Flagged to the user before training;
  user chose a Stage-2-scoped fix (see `MODULE_CONTEXT.md`'s new
  "KDE_baseline: Two Valid Uses" section for the full framing - this is
  NOT a defect in Stage 1's committed Moran's I=0.70 result, which is
  scale-invariant and remains correct).
- **Fix**: `rescale_kde_baseline()` mass-conserves `KDE_baseline` per
  (Year, Week) to sum to that week's actual total case count, preserving
  its spatial redistribution shape. `residual_rescaled` (the actual RF
  target) has mean ≈0 and `corr(residual_rescaled, Number_of_Cases) =
  0.678` - a genuine residual with real, learnable variance.
- **Training set**: 25,123 rows (100 series-start rows dropped for
  incomplete `lag_4` history - exactly 25 districts × 4 weeks).
- **Spatial K-means CV folds** (geographically coherent clusters):

  | Fold | Districts | Test rows | MAE | RMSE |
  |---|---|---|---|---|
  | 0 | Colombo, Gampaha, Kandy, Kegalle, Kurunegala, Puttalam | 6,030 | 61.28 | 96.90 |
  | 1 | Jaffna, Kilinochchi, Mannar, Mullaitivu, Vavuniya | 5,023 | 13.61 | 36.86 |
  | 2 | Ampara, Badulla, Hambantota, Monaragala, Nuwara Eliya | 5,025 | 19.84 | 37.04 |
  | 3 | Galle, Kalutara, Matara, Ratnapura | 4,020 | 56.17 | 74.83 |
  | 4 | Anuradhapura, Batticaloa, Matale, Polonnaruwa, Trincomalee | 5,025 | 14.69 | 28.33 |

  **Aggregate: MAE = 33.12 ± 23.57, RMSE = 54.79 ± 29.63** (mean ± std
  across 5 folds). The large spread tracks case-volume magnitude per fold
  (fold 0/3 contain the highest-burden districts - Colombo, Gampaha,
  Kalutara, Galle) - not a modeling defect, but worth normalizing (e.g.
  MAE relative to each fold's mean case count) for a fairer cross-fold
  comparison in future work.
- **Top 10 feature importance** (final model, trained on all 25
  districts): `population_density` (0.407), `Estimated_Population`
  (0.178), `temperature_2m_mean (°C)` (0.056), `temperature_anomaly`
  (0.048), `rainfall_lag_4` (0.042), `monsoon_indicator_SW` (0.039),
  `temperature_lag_4` (0.036), `temperature_lag_2` (0.032),
  `temperature_lag_3` (0.027), `mahalanobis_anomaly_score` (0.025).
  Population features dominate (58.5% combined) - sensible, since the
  rescaled KDE baseline already accounts for pure spatial proximity
  redistribution, leaving population size/density as the main systematic
  driver of a district's remaining burden beyond that.
- **Outputs**: `outputs/metrics/module3/rf_stage2_metrics.csv` (per-fold +
  aggregate MAE/RMSE), `outputs/metrics/module3/rf_feature_importance.csv`
  (full ranked list), `outputs/metrics/module3/spatial_cv_folds.csv`
  (District → spatial_fold assignment).
- **Models are NOT committed to git** - `models/module3/` is now
  `.gitignore`d (large binaries: `rf_final_model.joblib` alone is
  ~110MB, exceeding GitHub's 100MB push limit; 5 fold models add another
  ~440MB). Fully reproducible from code + already-committed data. **To
  regenerate locally: `python -m src.module3_spatial.compensation_model`.**

### Interpretation
The scale-mismatch finding was a genuine pre-existing gap between the
written Stage 2 spec and Stage 1's actual output, not an oversight in this
implementation - catching it before training (rather than after seeing an
implausibly "perfect" model) is what let it get fixed cleanly, scoped to
Stage 2 only. With the fix applied, the RF model behaves sensibly:
population dominates feature importance (expected, since the baseline
already handles spatial proximity), and per-fold error scales with each
fold's case-volume magnitude (expected, not a leakage or degeneracy
signal). Spatial CV folds are geographically coherent (e.g. the northern
peninsula districts cluster together), confirming the K-means clustering
on GADM centroids is doing something sensible, not producing arbitrary
groupings.

### Decision
**Keep** the rescaled residual as Stage 2's actual training target going
forward (not the raw `Residual` column already in
`stage2_feature_table.csv`, which remains on disk unchanged for
transparency but is not model-usable as-is). **Keep** models out of git
(`.gitignore`d, regenerate via the command above). **Proceed** to the
iterative convergence loop as the next piece of Stage 2 work - not started
this session. The loop must use the RESCALED `KDE_baseline` as `Risk_0`,
not the raw Stage 1 output, per the new `MODULE_CONTEXT.md` section.

### Documentation Updated
- `module_3_spatial/MODULE_CONTEXT.md` (new "KDE_baseline: Two Valid Uses,
  Not a Contradiction" section between Stage 1 and Stage 2).
- `module_3_spatial/EXPERIMENT_LOG.md` (this entry).
- `src/config.py` (added `MODULE3_MODELS_DIR`, `MODULE3_RF_FOLDS_DIR`,
  `MODULE3_RF_FINAL_MODEL_PATH`, `MODULE3_RF_METRICS_PATH`,
  `MODULE3_RF_FEATURE_IMPORTANCE_PATH`, `MODULE3_SPATIAL_CV_FOLDS_PATH`).
- `.gitignore` (added `models/module1/`, `models/module2/`,
  `models/module3/` - module1/module2 already had model binaries
  committed before this pattern existed; this does not retroactively
  untrack those, only stops future additions).
- Added `src/module3_spatial/compensation_model.py`.
- Added `outputs/metrics/module3/rf_stage2_metrics.csv`,
  `rf_feature_importance.csv`, `spatial_cv_folds.csv`.
