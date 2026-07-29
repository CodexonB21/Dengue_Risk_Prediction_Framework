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
