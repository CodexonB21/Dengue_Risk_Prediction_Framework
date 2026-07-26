# Current Architecture

## Status
Living document. Update this file whenever the accepted architecture changes.

## Last Updated
2026-07-26

## Architecture Version
v1.0-initial-living-context

---

# Overall Framework

The project follows a residual compensation design across three modules.

```text
Raw Data
  ↓
Preprocessing + Feature Engineering
  ↓
Baseline Models
  ↓
Residual / Error Extraction
  ↓
Compensation Models
  ↓
Final Forecasts / Risk Outputs / Hotspot Outputs
  ↓
Dashboard / Decision Support
```

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

The three modules are expected to feed into an early warning dashboard.

Integrated outputs may include:

- Predicted weekly dengue case counts
- Outbreak risk category or probability
- Spatial hotspot map
- Alerts and decision-support summaries

---

# Open Architecture Questions

These should be updated as the project evolves.

1. Should Module 1 remain pure SARIMA, or should STL + SARIMA be tested?
2. Which model gives the best residual compensation: XGBoost, Random Forest, LightGBM, or another method?
3. How should Module 1 outputs feed into Module 2?
4. How should spatial outputs from Module 3 be combined with temporal and classification outputs?
5. How should uncertainty be represented in the dashboard?
