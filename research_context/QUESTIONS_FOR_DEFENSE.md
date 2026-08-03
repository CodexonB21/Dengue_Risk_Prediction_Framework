# Questions for Defense

This file contains prepared explanations for supervisor, evaluator, and viva-style questions.

Update this file whenever a new important question is asked or a better explanation is developed.

---

## Why do we use two stages?

We use two stages to separate baseline pattern learning from error correction.

Stage 1 captures the expected structure using a baseline model. Stage 2 learns what the baseline missed by modeling the residual or error.

This makes the framework more interpretable than a black-box single-stage model.

---

## What happens to the compensation output?

The compensation model predicts the baseline model's error.

For Module 1:

```text
Final Forecast = SARIMA Forecast + Predicted Residual
```

The compensation stage does not replace the baseline. It corrects it.

---

## What if the residuals are random?

If residuals are random, compensation may not improve the result.

That is still a valid finding because it means the baseline model has already captured most learnable structure for that district or period.

This should be checked using residual diagnostics such as ACF plots, Ljung-Box tests, and performance comparison.

---

## Why are module-specific documents needed?

The project has three separate modules handled by different team members.

Module-specific documents prevent confusion and allow each module to evolve independently while still following the overall residual compensation framework.

---

## How do we avoid outdated Cursor rules?

The Cursor rule file should not contain detailed static research facts. Instead, it should instruct Cursor to read the latest markdown files and update them when decisions change.

The latest documentation should be treated as the source of truth, not the conversation history.

---

## Why does Stage 1 SARIMA often have no seasonal component (18/25 districts)?

**Short answer:** AIC-driven `auto_arima` order selection, with `m=52`, frequently chose `seasonal_order=(0,0,0,52)` — a plain non-seasonal ARIMA — even though weekly dengue data is strongly seasonal. This is a known limitation of Stage 1 **in isolation**, not a silent bug we ignored.

**What we found:**
- OCSB and Canova-Hansen both selected `D=0` for all 25 districts; only 7/25 got a seasonal AR term.
- **12/25 districts** have Stage-1-only validation MASE > 1 (worse than a seasonal-naive “repeat last year’s same week” benchmark).
- Forcing seasonal differencing (`D=1`) was tested and found computationally infeasible at pipeline scale (7+ minutes per fit vs ~0.01s for the fixed-order refits used everywhere else).

**Why we did not rework Stage 1:**
- The residual-compensation design deliberately keeps climate and explicit seasonality out of Stage 1 (Decision 001) so Stage 2 can learn those signals from residuals.
- We ran the pre-registered diagnostic after Stage 2 was built: the **18 non-seasonal districts improved more** with Stage 2 (median 44.9% validation / 39.1% holdout MASE reduction) than the 7 seasonal districts (31.9% / 26.2%). Stage 2’s `sin_week`/`cos_week`, monsoon indicators, and climate features appear to be compensating for the annual cycle Stage 1 missed.
- Reworking Stage 1 now would risk weakening the residual signal Stage 2 is designed to correct, with no evidence the **combined** pipeline would improve.

**How to present this honestly:**
- Report Stage 1-only metrics separately from Stage 1+Stage 2 — do not oversell Stage 1 as a strong standalone forecaster for all districts.
- Frame the contribution as: *baseline + residual compensation improves forecasts*, not *SARIMA alone is optimal*.
- Flag explicitly to the supervisor: “Stage 1 is a deliberately simple, AIC-selected univariate baseline; its seasonal weakness is a documented limitation that Stage 2 substantially addresses.”

**If challenged:** “Would STL+SARIMA be better?” — Possible ablation for future work, but superseded for this thesis by empirical evidence that Stage 2 already captures the missing seasonal structure. Not required to validate the residual-compensation hypothesis.

**Evidence:** `models/module1/sarima_selected_configs.csv`, M1-001/M1-002 experiment log, Open Question #12 resolution in `module_1_forecasting/MODULE_CONTEXT.md`.

---

## How is forward/dashboard risk different from holdout validation?

**Short answer:** Holdout metrics measure **model skill on past data** the pipeline never used for selection; dashboard forward outputs measure **what the frozen production models say about upcoming weeks** using forecast climate and (for multi-week risk) Module 1 predicted case lags.

| Aspect | Holdout / walk-forward | Operational forward (`future_risk_predictions.csv`) |
|---|---|---|
| Purpose | Honest skill estimate | Decision-support / early warning |
| Models | Same checkpoints, but scored on historical rows | Frozen `final_production_model.*` |
| Case inputs | Real observed lags only | M1 `final_prediction` for lags when real cases unavailable |
| Climate | Observed only (historical) | Observed + Open-Meteo forecast API |
| Evidence tier | Validation | `operational` — never cite as PR-AUC/BSS |

**Thesis framing:** “We validated the framework on held-out history; the dashboard applies the same frozen models operationally with clearly labeled uncertainty and without retraining.”

---

## Why does Module 2 use isotonic calibration instead of climate/residual compensation like Module 1?

**Short answer:** The unified framework is a **two-stage hybrid** (baseline + error correction), not a literal copy of Module 1’s additive residual formula everywhere. Module 2 **does** use climate and case history — in **Stage 1**, where they drive discrimination. Stage 2’s dominant error turned out to be **probability miscalibration** from imbalance handling (`scale_pos_weight` / `class_weight`), not missing weather signal. Isotonic regression fixes that scale distortion; feature-based “residual” models (stacked XGBoost, logit-residual) consistently underperformed in held-out evaluation (M2-002/M2-003/M2-007A).

**Why the architectures differ (by design, not oversight):**

| | Module 1 | Module 2 (production) |
|---|---|---|
| Stage 1 role | Deliberately climate-free SARIMA | Full classifier with case history **and** climate |
| Stage 2 error type | Structured count residuals (`actual − SARIMA`) | Probability scale distortion |
| Stage 2 fix | XGBoost on residuals + climate | Isotonic calibration |
| Literal residual target | Well-posed (continuous) | Ill-posed for binary labels (Decision 022) |

**How to present this honestly:**
- “Climate **does** improve outbreak-risk ranking in Module 2 — via Stage 1 features, not via a failed Stage 2 residual layer.”
- “Stage 2 residual correction in probability space was **tested and rejected** — a documented negative result, not an unexamined gap.”
- “The framework claim is **validated hybrid correction with documented limits**, not state-of-the-art on every metric.”

**Symmetric ablation (M2-008, 2026-07-29):** Stage 1 retrained **without** climate (case history + seasonality only); climate routed **only** to Stage 2 stacked correction. **Result: stacked climate compensation still failed** — holdout PR-AUC 0.424 vs climate-free Stage 1 raw 0.462 (−3.8 pp), BSS −0.22. Platt/isotonic calibration on the weaker Stage 1 probabilities worked (Platt holdout PR-AUC 0.462, isotonic BSS 0.284), but the feature-based residual layer did not behave like Module 1. This strengthens the conclusion that classification’s bottleneck is not merely “climate was already in Stage 1” — even a Module 1–style split does not make stacked probability correction competitive.

**Evidence:** Decision 022, M2-002/M2-003/M2-005, M2-007A (logit-residual rejected), M2-007D (M1-fed stacked improves PR-AUC but hurts BSS/precision), **M2-008** (`outputs/metrics/module2/m2_008_summary.csv`).

---

## Do we use weather/climate anomalies in Module 1 and Module 2?

**Short answer:** **Yes, both modules use fold-aware rainfall, temperature, and humidity anomalies** — same definition, different placement in the pipeline.

**Definition (Decision 003):**

```text
rainfall_anomaly   = current_week_rainfall   − long_term_mean(district, week)
temperature_anomaly = current_week_temperature − long_term_mean(district, week)
humidity_anomaly   = current_week_humidity   − long_term_mean(district, week)
```

The long-term mean is recomputed **per walk-forward fold** from training data only (`compute_fold_climate_anomalies`). Rainfall uses `precipitation_sum (mm)` (Decision 008). `weather_code` is excluded in both modules.

| | Module 1 | Module 2 |
|---|---|---|
| **Stage 1** | **No** climate/anomalies (SARIMA, cases only — Decision 001) | **Yes** — anomalies + lagged/current raw climate in Stage 1 classifier |
| **Stage 2 (production)** | **Yes** — anomalies in XGBoost residual model | **No** in isotonic (feature-free); anomalies appear only in non-production stacked ablations |
| **Also used** | Lagged raw climate (Groups 1–2), seasonality; M1-006B reporting-delay features (not weather) | `case_anomaly_lag_1/2` (case z-scores — **not** weather anomalies) dominate Stage 1 importance |

**Defense one-liner:** “Weather anomalies are used in both modules. Module 1 applies them in Stage 2 to explain SARIMA residuals; Module 2 applies them in Stage 1 to rank outbreak risk, because classification has no climate-free baseline requirement.”

**Evidence:** `research_context/FEATURE_ENGINEERING_SPEC.md` (Groups 3 / M2-3), `src/module1_forecasting/feature_engineering.py`, `src/module2_classification/feature_engineering.py`.

---

## Why is Module 2 needed if Module 1 already forecasts case counts?

**Short answer:** Module 1 answers **how many cases**; Module 2 answers **whether this district-week is epidemiologically abnormal** (relative to its own seasonal baseline). Those are different tasks. On holdout, deriving outbreak alerts from Module 1 forecasts **does not** match Module 2's discrimination or early-warning recall.

**Conceptual distinction:**

| | Module 1 | Module 2 |
|---|---|---|
| Target | Weekly case count (continuous) | Outbreak exceedance (binary, ~1.5% holdout prevalence) |
| Optimized for | MASE / sMAPE | PR-AUC, alert recall (F2-optimal τ=0.14) |
| “High value” meaning | Large expected count | **Unexpected** count for this district-week |

Outbreak label (Decision 025):

```text
outbreak = 1 if cases > harmonic_seasonal_expectation(district, week) + 3 × SD
```

Colombo at 200 cases may be normal; a low-incidence district at 30 may be an outbreak. High predicted counts in high-baseline districts (Colombo, Gampaha) are often **not** outbreaks — on holdout, **240 of 260** top-decile M1 prediction weeks are non-outbreaks.

**Empirical comparison (M2-009, holdout — 2,600 district-weeks, 40 true outbreaks):**

| Alert / scoring rule | PR-AUC | Recall | Precision | F2 | Alerts |
|---|---:|---:|---:|---:|---:|
| **M2 production (isotonic, τ=0.14)** | **0.412** | **0.600** | 0.338 | **0.519** | 71 |
| M1 forecast > **same epidemic threshold** | 0.063 | 0.225 | 0.563 | 0.256 | 16 |
| M1 excess (pred − threshold) score | 0.280 | — | — | — | — |
| M1 forecast > **fixed 100 cases** (naive) | 0.063 | 0.500 | 0.073 | 0.231 | 273 |
| Oracle: actual > epidemic threshold | 0.302 | 1.000 | 1.000 | 1.000 | 40 |

**Key findings:**

- M2 ranks outbreak weeks **~6.5× better** on PR-AUC than M1-threshold (0.412 vs 0.063).
- M2 recall **60%** vs M1-threshold **22.5%** — M2 catches **15 outbreaks M1 misses**; M1-threshold catches **zero** M2 misses.
- Naive fixed cutoff (>100 cases) fires **273 alerts** at **7.3% precision** — not viable for surveillance.
- M1-threshold has higher precision (56%) but misses most outbreaks — F2-optimal early warning favors M2 (Decision 024).

**Defense one-liner:** “Module 1 quantifies expected cases; Module 2 detects relative epidemic exceedance. Thresholding M1 forecasts on holdout achieved 0.063 PR-AUC and 22.5% recall versus Module 2's 0.412 and 60% — Module 2 is not redundant.”

**Evidence:** `scripts/m2_009_m1_alert_baseline.py`, `outputs/metrics/module2/m2_009_{m1_alert_baseline,summary,discordant_counts}.csv`, `module_2_classification/EXPERIMENT_LOG.md` M2-009.

---

## Why doesn't Module 3 use a temporal holdout like Module 1/2?

**Short answer:** Module 3's residual target and validation question are spatial, not sequential — a temporal split would not test the thing Module 3 actually claims.

Module 1/2 forecast or classify a specific FUTURE week from past weeks — a temporal holdout (weeks the model never saw during training) is the correct test of that claim. Module 3's claim is different: does a spatial baseline (KDE) capture genuine geographic clustering, and does a residual model correct district-level burden using spatially-held-out districts? Its only validation axis is 5-fold spatial K-means CV (whole districts held out, never split — `compensation_model.py::build_spatial_folds`) — every row of `hybrid_risk_map.csv`, for every (Year, Week), already comes from a model that never saw that district during training, which is Module 3's own form of held-out evaluation, applied uniformly to every week rather than one held-out block.

A temporal holdout is not currently implemented for Module 3 and would test a different question (does the model generalize to unseen TIME, not unseen SPACE) — a legitimate future extension, not a gap being hidden.

**Evidence:** `module_3_spatial/MODULE_CONTEXT.md`'s "Is the map test-set-safe" note, `EXPERIMENT_LOG.md` M3-003/M3-004.

---

## Did Module 3's Stage 2 ever show a null result, and what changed?

**Short answer:** Yes, initially (M3-005, 2026-07-29) — with the original 16 features, `alpha=0.05` (chosen for strict loop convergence, not accuracy) produced a marginally WORSE fit than Stage 1 alone on every metric. This was later resolved (M3-008, 2026-08-05) by adding own-district residual lag features — Stage 2 now IMPROVES substantially (MAE 20.54 → 9.96, ~51% reduction), not marginally worsens.

**Original finding (M3-005), correct at the time:** Stage 2 final (`Risk`) was marginally worse than Stage 1 alone (`Risk_0`) on every metric against actual case counts — corr −0.0037, MAE +1.74%, RMSE +0.87%. Reported honestly rather than reframed around a friendlier metric. A follow-up exploratory sweep (M3-006) then confirmed no alpha in {1.0, 0.3, 0.15, 0.05} improved on Stage 1 alone with that feature set — the problem was not alpha tuning.

**What actually fixed it (M3-008):** every one of the original 16 features was either static per-district (population/elevation) or current-week climate — none gave the RF any memory of a district's own recent case trajectory, despite dengue outbreaks having real week-to-week persistence. Adding `residual_rescaled_lag_1/2/3/4` (own-district lags of the rescaled residual) dropped out-of-fold residual MAE from ~34.7 to ~10.1 and let `alpha=1.0` (full correction, no shrinkage) become optimal — verified NOT a leakage artifact, since `kde_baseline_rescaled[t]` only ever uses week *t*'s own case counts, never *t-1*'s (raw `corr(residual_rescaled, its own lag-1) = 0.84` reflects genuine epidemic persistence). Promoting this into the existing multi-iteration loop unchanged was checked, not assumed to work: the loop no longer converges past iteration 1 with the new features (a real, verified instability — fixed by capping `MAX_ITERATIONS=1` by design, since iteration 1 alone already reproduces the validated result).

This progression is itself worth stating plainly in a defense: the null result was real and honestly reported, the fix was a genuine feature-engineering gap (not a mistuned hyperparameter), and every step — the original null finding, the alpha sweep, the leakage check, the loop-instability discovery, the clipping decision — was verified directly before being written into the permanent record, not assumed.

**Evidence:** `outputs/metrics/module3/results_summary.txt`, `outputs/metrics/module3/stage2_experiments.csv`, `EXPERIMENT_LOG.md` M3-004/M3-005/M3-006/M3-008.

---

## Does Module 3 predict a genuine future hotspot map?

**Short answer:** Yes, as of Decision 031 (2026-08-04) — but only the CASE COUNT is a forecast; the CLIMATE is real observed data, and the output is explicitly `evidence_tier=operational`, not a holdout-validated result.

Module 3's Stage 1 KDE weighting and Stage 2 residual target both require a known `Number_of_Cases`, which does not exist for a week that has not been reported yet. `src/module3_spatial/forecast_future.py` resolves this the same way Decision 027 already resolved it for Module 2: it reads Module 1's `future_forecast.csv` for the forecast week's per-district case-count proxy. A non-obvious, verified finding: because Module 3's case-count reporting lags real calendar time by several weeks, the forecast week's actual calendar DATES have typically already passed by the time this script runs — so its weather is real `observed` data, not a meteorological forecast (checked directly against the raw Open-Meteo `climate_data_source` column). Only the case count is genuinely uncertain.

No model is retrained; the already-trained frozen final Stage 2 RF model and the already-decided `alpha=1.0` formula (M3-008; was 0.05 before the residual-lag promotion) are applied once, then clipped at 0 (case counts cannot be negative). Every output row is tagged `evidence_tier=operational` and must never be cited alongside Stage 1's Moran's I=0.70 or Stage 2's spatial-CV MAE/RMSE as if it were additional validation evidence.

**Evidence:** `RESEARCH_DECISIONS.md` Decision 031, `module_3_spatial/MODULE_CONTEXT.md`'s "Forward Operational Hotspot Forecast" section, `EXPERIMENT_LOG.md` M3-007.
