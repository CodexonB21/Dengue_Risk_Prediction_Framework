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

## Why does Stage 2 use one pooled model across all 25 districts instead of one model per district?

**Short answer:** We tested this directly rather than relying on the original design reasoning. A per-district Stage 2 — 25 separate XGBoost models instead of one pooled model, everything else (hyperparameters, features minus the now-redundant `District` column, fold structure, evaluation) held fixed — was **decisively worse**: validation-aggregate median MASE 0.7473 vs. the pooled baseline's 0.5821 (+28.4%), with only 1 of 13 folds and 4 of 25 districts improving. The pre-registered overfitting safeguard (must beat baseline on the aggregate **and** a majority of folds **and** a majority of districts) was not cleared, so no holdout check was even performed.

**Why pooling wins for most districts:** Per-district training data is roughly 25× thinner than pooled at the same fold — the first fold with any residual history at all gives a single district only 52 rows, versus ~1,300 pooled. An explicit three-tier data-sufficiency rule (no-op below 104 trainable rows, fixed tree count 104–207 rows, early stopping only at 208+ rows) protected against fitting models to token amounts of data, but most districts (21/25) still depend on the cross-district information-sharing that pooling provides.

**What the 4 exceptions tell us:** The districts that *did* improve without pooling — `Monaragala`, `Mannar`, `Vavuniya`, `Matale` — are not random; they are exactly the districts already flagged in earlier diagnostics (Decisions 017/034/037) as ones where the pooled correction underperforms. This sharpens the earlier shrinkage work: it suggests a **narrow, targeted** per-district remedy for those specific districts, not a wholesale architecture change, is the more promising follow-up (not built — deliberately scoped as future work).

**Defense one-liner:** "We didn't just assume pooling was right — we ablated it. Pooling wins for 21/25 districts by a wide margin, and the 4 exceptions are the same districts already flagged as structurally different, which is itself useful diagnostic information, not noise."

**Evidence:** Decision 045, M1-021 (`module_1_forecasting/EXPERIMENT_LOG.md`), `scripts/evaluate_per_district_stage2.py`, `outputs/metrics/module1/stage2_per_district_vs_pooled.csv`.

---

## Was there a data leakage risk in the reporting-anomaly features? How did you catch and handle it?

**Short answer:** Yes — a subtle one, found by us during unrelated scoping work, and then **empirically verified not to have inflated any previously published result** before deciding no retraction was needed.

**The leakage pathway:** `flag_reporting_anomalies()` (Decision 026/028) needs `cases[i+1]` — the *following* week's case count — to decide whether week *i* looks like a reporting dip. Every downstream consumer of that flag (the nowcast correction and Feature Group 6 in `feature_engineering.py`, and the residual-lag masking in `compensation_model.build_residual_lags()`) used week *T−1*'s flag as an input feature for predicting row *T*. Because week *T−1*'s flag is itself computed from `cases[T]`, the feature was — subtly, and unintentionally — informed by the very value being predicted.

**How we checked whether it mattered (rather than assuming):** We built a causal-only replacement (`flag_reporting_dip_causal()` — drop-only, no rebound confirmation, uses only `cases[i-1]` and `cases[i]`) and re-ran the full Stage 2 + combine pipeline with it substituted everywhere the leaky flag had been used. **Result: median holdout MASE 0.3655 (causal-safe) vs. 0.3741 (production) — the leakage-closed variant is not worse, and if anything ~2.3% better.** This means the leakage existed in the code but did not meaningfully inflate Decision 030's reported improvement.

**Why we didn't then build a real-time correction on top of the causal detector:** We also measured the causal detector's real-time precision against the retrospective flag as ground truth — 100% recall but only 42.9% precision overall, and worse in exactly the two highest-volume districts (`Colombo` 46.2%, `Gampaha` 30.0%). More than half of real-time alerts in those districts would be false alarms, so a point-forecast adjustment built on it was rejected before being built, rather than shipped and found wanting later.

**Defense one-liner:** "We found and disclosed our own leakage pathway, quantified its actual impact instead of assuming the worst, and confirmed the published result stands — that's the level of scrutiny we applied to our own pipeline, not just to baselines."

**Evidence:** Decision 043, M1-019 (`module_1_forecasting/EXPERIMENT_LOG.md`), `scripts/evaluate_reporting_leakage_fix.py`, `scripts/evaluate_causal_dip_detector.py`, `src/preprocessing/reporting_anomalies.py`.

---

## If a hyperparameter search found a better validation score, why wasn't the new configuration adopted?

**Short answer:** Because it failed the one check that actually matters — the untouched holdout block — after passing every validation-fold check we threw at it. This is presented as a demonstration of *why* the holdout discipline exists, not as a wasted exercise.

**What happened:** A 40-candidate randomized search over Stage 2's XGBoost hyperparameters (max depth, learning rate, subsample, column subsample, L2 regularization, min child weight) was scored on walk-forward folds 2–14 using the exact metric function production already publishes. 5 of 39 candidates cleared a pre-registered safeguard — beating baseline's aggregate **and** a majority of the 13 folds **and** a majority of the 25 districts, not just a lower single number. The best candidate reached a validation-aggregate median MASE of 0.5659, a 2.8% improvement over the published 0.5821.

**Then the one-time holdout check:** median holdout MASE **0.3874 vs. production's 0.3741 — a 3.6% regression.** Per the pre-registered rule ("holdout touched once, only after a candidate already wins on validation, never for further selection"), no other qualifying candidate was checked afterward.

**Why this matters for the thesis, not just as a null result:** A hyperparameter set that broadly beat production across all 13 validation folds — clearing a safeguard specifically designed to filter out fold-count noise — still did not generalize to genuinely unseen data. That is direct, first-hand evidence for why the project's holdout-integrity rule (Decision 009/010) is not a bureaucratic formality: a naive "pick whatever wins on validation" process would have shipped a regression here.

**Defense one-liner:** "Our holdout protocol isn't just a rule we cite — this experiment is the proof it catches real overfitting-to-validation that a 13-fold majority vote alone did not."

**Evidence:** Decision 044, M1-020 (`module_1_forecasting/EXPERIMENT_LOG.md`), `scripts/search_stage2_hyperparameters.py`.

---

## After all this investigation, is Module 1's forecasting accuracy actually better than before?

**Short answer:** For the validated, historical-holdout accuracy number examiners will look at first (median holdout MASE), **no — it is unchanged at 0.374.** The one genuine, evidence-backed improvement found across this entire investigation arc (M1-007 through M1-021) applies to a different capability — the forward-looking, real-time "predict next week" nowcast — not to the headline backtest metric.

**What was tried and rejected (six ablations):** warm-started SARIMA refitting (M1-013), a lower-frequency refit cadence (M1-014), robust ensemble aggregation via median/trimmed-mean (M1-018/Decision 042), a real-time reporting-dip point adjustment (M1-019/Decision 043, Option A), a 40-candidate XGBoost hyperparameter search (M1-020/Decision 044), and per-district Stage 2 models (M1-021/Decision 045). Each held everything else fixed and tested one structural or tuning change against the same walk-forward folds and the same untouched holdout block; each was reported and documented as a negative result rather than discarded quietly.

**What was accepted:** vintage-ensembled SARIMA — averaging, in transformed space, the current week's fresh SARIMA fit with the last 3 weeks' own independently-fitted models' forecasts for the same target week. In the rolling one-step-ahead evaluator, this raised the number of districts where Stage 2 helps from 10/25 to 24/25 and improved rolling sMAPE for 22/25 districts (median 58.8% → 56.8%) at effectively zero extra cost (Decision 039/M1-015). It is now the production nowcast's default (Decision 040/M1-016), with a permanent prospective-accuracy log (Decision 041/M1-017) seeded to check its real-world performance as future weeks resolve.

**Why the two evidence tiers must not be conflated:** the rolling-evaluator improvement is measured on a deployment-faithful, one-step-ahead re-simulation of history, not on the 104-week flat holdout forecast that produces the headline MASE — they answer different questions ("does this help predict the very next week, repeatedly, as data accumulates" vs. "how accurate is a single long-horizon forecast fit once"). Reporting the nowcast win as if it moved the holdout MASE would overstate the result.

**Defense one-liner:** "The core two-stage architecture's backtest accuracy is stable, not broken — we spent this arc stress-testing it from six different angles and it held up. The one real improvement we found applies specifically to the operational next-week nowcast, and we built the infrastructure to keep measuring it honestly rather than declaring victory on a single retroactive check."

**Evidence:** Decisions 039–045, M1-013 through M1-021 (`module_1_forecasting/EXPERIMENT_LOG.md`), "Investigation Summary: Module 1 Remediation Arc" section of `module_1_forecasting/MODULE_CONTEXT.md`.
