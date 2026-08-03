# Current Architecture

## Status
Living document. Update this file whenever the accepted architecture changes.

## Last Updated
2026-08-04 (Module 3 forward operational hotspot forecast — Decision 031)

## Architecture Version
v1.0-initial-living-context

---

# Overall Framework

The project follows a residual compensation design across three modules.

```text
Raw Data
  ↓
Shared Preprocessing (module-agnostic)
  ↓
Module-Specific Preprocessing (temporal/modeling adjustments per module)
  ↓
Baseline Models
  ↓
Module-Specific Feature Engineering
  ↓
Residual / Error Extraction
  ↓
Compensation Models
  ↓
Final Forecasts / Risk Outputs / Hotspot Outputs
  ↓
Dashboard / Decision Support
```

**Guiding principle (added 2026-07-26, Decision 013):** a data transformation only
belongs in the shared layer if every module would make the same choice for the same
reason. Transformations that exist to satisfy one baseline model's assumptions (e.g.
SARIMA's fixed 52-week seasonal period) belong in that module's own preprocessing
step, not upstream, where they would silently bias the other two modules' data.

The full technical build plan (file layout, script responsibilities, exact
transformation order) lives in `research_context/PIPELINE_ARCHITECTURE_PLAN.md`. This file
(`CURRENT_ARCHITECTURE.md`) stays at the research/design level; that file is the
implementation-level companion.

---

# Module 1: Hybrid Time-Series Case Forecasting

## Current Owner
Bandara H.R.B.G.M.

## Current Accepted Design

```text
Stage 1: SARIMA baseline model
Stage 2: XGBoost residual compensation model
```

## Stage 1 Target
Weekly dengue case count.

## Stage 1 Inputs
Only historical weekly dengue case counts.

Climate variables are deliberately excluded from Stage 1.

## Stage 2 Target
SARIMA residual:

```text
residual = actual_cases - sarima_prediction
```

## Stage 2 Features
Currently planned categories:

- Lagged case features
- Rolling case trend features
- Lagged climate features
- Climate anomaly features
- Seasonal/monsoon indicators
- SARIMA prediction
- Residual lag features
- Optional intervention features, if available

---

# Module 2: Hybrid Outbreak Risk Classification

## Current Owner
Nethma L.H.K.

## Current Accepted Design

```text
Stage 1: Baseline outbreak classifier
Stage 2: Probability / classification-error compensation model
```

## Stage 1 Output
Baseline outbreak probability or risk class.

## Stage 2 Purpose
Correct systematic misclassification or probability calibration errors using environmental anomaly and contextual features.

## Notes
The exact classifier and compensation method may change after benchmarking.

---

# Module 3: Hybrid Spatial Hotspot Detection

## Current Owner
Karunarathna R.M.D.R.R.

## Current Accepted Design

```text
Stage 1: KDE + spatial autocorrelation baseline
Stage 2: Spatial residual adjustment using environmental/demographic features
```

## Stage 1 Output
Baseline spatial risk surface / hotspot estimate.

## Stage 2 Purpose
Correct baseline spatial risk using environmental and demographic context such as rainfall, elevation, population density, and other spatial covariates.

---

# Integration Layer

The three modules feed into an **operational early-warning dashboard** (implemented
2026-07-29, Decision 027; Module 3 forward hotspot added 2026-08-04, Decision 031):

```text
scripts/fetch_open_meteo_weather.py     → raw daily weather (observed + forecast)
scripts/refresh_dashboard_data.py     → full refresh orchestrator
src/module1_forecasting/forecast_future.py → future_forecast.csv
src/module2_classification/live_scoring.py   → live_risk_predictions.csv (recent weeks)
src/module2_classification/forecast_future_risk.py → future_risk_predictions.csv (M1-fed)
src/module3_spatial/forecast_future.py  → future_hotspot_forecast.csv (M1-fed case counts,
                                            real observed climate - see Decision 031)
src/dashboard/app.py                    → Streamlit dashboard (read-only CSV consumer)
```

Integrated outputs include:

- Predicted weekly dengue case counts (Module 1 forward forecast)
- Outbreak risk category or probability (Module 2 live + forward operational scoring)
- Spatial hotspot map (Module 3 — historical `hybrid_risk_map.csv` + forward operational
  `future_hotspot_forecast.csv`, Decision 031)
- Alerts and decision-support summaries

**Known gap (2026-08-04):** `module2_classification/live_scoring.py` and
`forecast_future_risk.py` currently have pre-existing, unrelated bugs (a sklearn
calibration reshape error and a reporting-anomaly boolean-mask error) that abort
`scripts/refresh_dashboard_data.py` before it completes. Module 1 and Module 3's own
steps are ordered before these in the orchestrator so they still refresh successfully;
Module 2's live/forward operational outputs remain stale until these are fixed
(Module 2-owned files, not fixed as part of Decision 031 - flagged, not fixed).

**Evidence tiers:** holdout-validated metrics (walk-forward/holdout) vs. operational
forward outputs (`evidence_tier=operational`) — must never be conflated in reporting.

---

# Open Architecture Questions

These should be updated as the project evolves.

1. Should Module 1 remain pure SARIMA, or should STL + SARIMA be tested?
2. Which model gives the best residual compensation: XGBoost, Random Forest, LightGBM, or another method?
3. How should Module 1 outputs feed into Module 2?
4. How should spatial outputs from Module 3 be combined with temporal and classification outputs?
5. How should uncertainty be represented in the dashboard?
