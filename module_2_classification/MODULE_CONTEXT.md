# Module 2 Context: Hybrid Outbreak Risk Classification

## Owner
Nethma L.H.K.

## Purpose
Classify dengue outbreak risk using a two-stage residual/error compensation approach.

---

## Current Architecture

```text
Stage 1: Baseline outbreak classifier
Stage 2: Probability / classification error compensation model
```

Exact models may change after benchmarking.

---

## Data Pipeline Note (2026-07-26)

Module 2 will consume `data/processed/shared/` (Kalmunai merged into Ampara, master epi-week calendar, full 13-column climate aggregation, interpolated population) — the same base tables Module 1 uses. Module 2 does **not** automatically inherit Module 1's downstream choices: the week-53 merge (Decision 007), missing-week imputation policy (Decision 011), and `weather_code` exclusion (Decision 008) are all Module-1-scoped per Decision 013. Module 2 must decide its own missing-week policy (e.g. drop vs. impute) once its label definition is settled, and independently decide on `weather_code`. See `research_context/PIPELINE_ARCHITECTURE_PLAN.md` for the full layered pipeline design.

---

## Possible Stage 1 Models

- Random Forest
- XGBoost
- Logistic Regression baseline
- Gradient Boosting

---

## Possible Stage 2 Models

- XGBoost
- Random Forest
- Calibration model
- Residual/probability correction model

---

## Target Direction

The module predicts outbreak risk, not exact case count.

Possible outputs:

- Binary outbreak/non-outbreak label
- Multi-class risk level: low / medium / high
- Outbreak probability

---

## Current Feature Direction

- Lagged dengue case counts
- Rolling mean of cases
- Rate of change
- Seasonal week encoding
- Monsoon indicators
- Baseline classifier probability
- Climate anomalies
- Probability residual lags, if valid

---

## Current Open Questions

1. How should outbreak labels be defined?
2. Should labels be district-specific and week-specific?
3. Which threshold definition is most defensible?
4. How should class imbalance be handled?
5. Should probability calibration be included?
6. How will Module 1 forecasts feed into Module 2?

---

## Evaluation Metrics

- Accuracy
- Precision
- Recall / Sensitivity
- Specificity
- F1-score
- ROC-AUC
- PR-AUC
- Confusion matrix
- Calibration plots

---

## Documentation Rule

Update this file when Module 2 labels, models, features, or evaluation method changes.
