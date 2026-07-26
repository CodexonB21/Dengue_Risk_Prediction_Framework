# Module 3 Context: Hybrid Spatial Hotspot Detection

## Owner
Karunarathna R.M.D.R.R.

## Purpose
Identify dengue hotspot areas using spatial baseline modeling followed by environmental/demographic residual correction.

---

## Current Architecture

```text
Stage 1: KDE + Moran's I / spatial autocorrelation baseline
Stage 2: Spatial residual adjustment model
```

---

## Data Pipeline Note (2026-07-26)

Module 3 will consume `data/processed/shared/` (Kalmunai merged into Ampara — important here since Kalmunai has no independent spatial boundary, master epi-week calendar, full climate aggregation, interpolated population). Module 3 does **not** automatically inherit Module 1's week-53 merge, missing-week imputation, or `weather_code` exclusion (all Module-1-scoped per Decision 013) — Module 3 likely aggregates to a coarser temporal resolution than weekly (TBD), where a handful of missing weeks may simply wash out rather than needing explicit imputation. Spatial boundary/polygon data is not yet placed in `data/raw/spatial/` (currently empty). See `research_context/PIPELINE_ARCHITECTURE_PLAN.md` for the full layered pipeline design.

---

## Stage 1 Direction

Possible baseline techniques:

- Kernel Density Estimation
- Global Moran's I
- Local Moran's I / LISA
- Getis-Ord Gi*, if added later

---

## Stage 2 Direction

Use environmental and demographic covariates to correct spatial baseline residuals.

Possible features:

- Rainfall raster-derived values
- Temperature, if spatially available
- Elevation
- Population density
- District centroid features
- Land-use/environmental variables, if available

---

## Current Open Questions

1. Are district centroids sufficient, or are finer spatial units needed?
2. How should KDE bandwidth be selected?
3. What is the spatial residual target?
4. How should spatial leakage be prevented?
5. Which spatial validation method is most suitable?
6. How should Module 3 outputs combine with Module 1 and Module 2 outputs?

---

## Evaluation Direction

Possible evaluation methods:

- Spatial overlap with observed hotspots
- Moran's I significance
- LISA cluster agreement
- Spatial cross-validation
- Hotspot classification accuracy, if labels are created

---

## Documentation Rule

Update this file when Module 3 spatial features, baseline methods, residual definition, or evaluation method changes.
