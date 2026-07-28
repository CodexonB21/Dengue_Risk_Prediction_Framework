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
  | NE monsoon | 2021 Wk1 | 0.031 | 0.285 | **No** |

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
