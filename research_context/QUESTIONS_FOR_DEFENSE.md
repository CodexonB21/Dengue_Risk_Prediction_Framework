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

## Why does Module 2 use calibration (Platt scaling, currently) instead of climate/residual compensation like Module 1?

**Correction (2026-08-13):** this entry previously named **isotonic regression, τ=0.14** as production. That was the state before Decision 047/M2-013 (2026-08-06). As of Decision 047, **Platt scaling is production**, alert threshold **τ=0.100** (high-confidence boundary 0.500, up from 0.350), holdout PR-AUC **0.4228** (up from 0.412), holdout recall **62.5%** (up from 60.0%), precision **34.2%** (up from 33.8%), F2 **0.536** (up from 0.519). Decision 047’s own “Documentation Updated” list did not include this file, so the drift went uncaught until this pass — see `research_context/EVALUATOR_QA_BANK_MODULE2.md` (M2-2, M2-3) for the full four-round isotonic-vs-Platt flip-flop history and why it is not itself a red flag (it tracks upstream Stage-1/label changes, not a Stage-2 code change each time).

**Short answer (architecture-family point, unaffected by the isotonic/Platt flip):** The unified framework is a **two-stage hybrid** (baseline + error correction), not a literal copy of Module 1’s additive residual formula everywhere. Module 2 **does** use climate and case history — in **Stage 1**, where they drive discrimination. Stage 2’s dominant error turned out to be **probability miscalibration** from imbalance handling (`scale_pos_weight` / `class_weight`), not missing weather signal. Pooled, feature-free recalibration (isotonic or Platt — whichever wins the current benchmark round) fixes that scale distortion; feature-based “residual” models (stacked XGBoost, logit-residual) consistently underperformed in held-out evaluation (M2-002/M2-003/M2-007A) and still do post-047.

**Why the architectures differ (by design, not oversight):**

| | Module 1 | Module 2 (production, post-Decision-047) |
|---|---|---|
| Stage 1 role | Deliberately climate-free SARIMA | Full classifier with case history **and** climate |
| Stage 2 error type | Structured count residuals (`actual − SARIMA`) | Probability scale distortion |
| Stage 2 fix | XGBoost on residuals + climate | Platt scaling (was isotonic pre-047; see correction above) |
| Literal residual target | Well-posed (continuous) | Ill-posed for binary labels (Decision 022) |

**How to present this honestly:**
- “Climate **does** improve outbreak-risk ranking in Module 2 — via Stage 1 features, not via a failed Stage 2 residual layer.”
- “Stage 2 residual correction in probability space was **tested and rejected** — a documented negative result, not an unexamined gap.”
- “Which pooled recalibration method wins (isotonic vs. Platt) is a close, upstream-driven race, not a fixed property of the problem — it has flipped four times, always tracking a Stage 1 or label change, never a Stage 2 change.”
- “The framework claim is **validated hybrid correction with documented limits**, not state-of-the-art on every metric.”

**Symmetric ablation (M2-008, 2026-07-29):** Stage 1 retrained **without** climate (case history + seasonality only); climate routed **only** to Stage 2 stacked correction. **Result: stacked climate compensation still failed** — holdout PR-AUC 0.424 vs climate-free Stage 1 raw 0.462 (−3.8 pp), BSS −0.22. Platt/isotonic calibration on the weaker Stage 1 probabilities worked (Platt holdout PR-AUC 0.462, isotonic BSS 0.284), but the feature-based residual layer did not behave like Module 1. This strengthens the conclusion that classification’s bottleneck is not merely “climate was already in Stage 1” — even a Module 1–style split does not make stacked probability correction competitive. (Predates Decision 047; unaffected by the isotonic/Platt flip since it’s about the stacked-vs-recalibration architecture question, not which recalibration method wins.)

**Evidence:** Decision 022, Decision 047/M2-013, M2-002/M2-003/M2-005, M2-007A (logit-residual rejected), M2-007D (M1-fed stacked improves PR-AUC but hurts BSS/precision), **M2-008** (`outputs/metrics/module2/m2_008_summary.csv`), `research_context/EVALUATOR_QA_BANK_MODULE2.md`.

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

**Empirical comparison (M2-009, holdout — 2,600 district-weeks, 40 true outbreaks). Caveat added 2026-08-13: this table predates Decision 047/M2-013 (2026-08-06), which flipped production from isotonic/τ=0.14 to Platt/τ=0.10 (see the isotonic-calibration entry above). No record found confirming `m2_009_m1_alert_baseline.py` was rerun under Platt — cite the row below as the pre-047 configuration, and note current production PR-AUC/recall/precision are 0.4228/62.5%/34.2% (M2-013), somewhat better than the row shown, until this comparison is regenerated:**

| Alert / scoring rule | PR-AUC | Recall | Precision | F2 | Alerts |
|---|---:|---:|---:|---:|---:|
| **M2 production (isotonic, τ=0.14 — pre-Decision-047, not yet rerun)** | **0.412** | **0.600** | 0.338 | **0.519** | 71 |
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

---

## Why is the actual-vs-predicted gap for Colombo/Gampaha 2026 Wk25 so large, when the surrounding weeks look fine?

**Short answer:** it is a specific, documented reporting-delay artifact in the case data one week earlier, not a general model failure and not primarily a missing-feature (e.g. mobility) problem.

**The mechanism:** Colombo went 507 → **20** → 1,138 cases (Wk23/24/25); Gampaha went 502 → **24** → 1,294. A real epidemic does not crash to near-zero for a single week and then explode — that shape is the signature of delayed reporting: Wk24's real cases were most likely under-reported and folded into Wk25's count on top of genuine continued growth. Both weeks are already flagged `is_reporting_anomaly=True`/the week after in the pipeline (Decision 026/028), independently of this specific question.

**Why it broke the forecast specifically:** both modules' single most important input is "what happened in the last 1-2 weeks" (Module 1's `residual_lag_1` is its top feature by a wide margin; Module 2's `case_anomaly_lag_1/2` account for >60% of its feature importance). Wk24's artificially low count told both models "cases just fell" immediately before the week they needed to predict a multi-fold jump — the models were not wrong to trust that signal in general, they were fed a corrupted version of it once.

**Why the previous weeks looked fine:** Wk18-23 was a genuine, smooth ramp-up, so "trust last week's number" was good advice there, and both modules tracked it reasonably well (~13% sMAPE under the deployment-realistic rolling evaluation). The model did not get worse — its most-trusted input broke for one week.

**Is it a missing-data issue (e.g. human mobility)?** Not the direct cause here — we can point to the exact corrupted data point and mechanism, not just infer a gap. But it is fair to separately volunteer a genuine, broader limitation: the framework has no independent leading indicator (mobility, healthcare-seeking behaviour, vector surveillance) that could signal an accelerating outbreak *before* it shows up in reported case counts. Even with a perfectly clean Wk24, a 2-8x single-week jump is inherently hard for a trend-following model to anticipate a week ahead, since by construction it reacts to what already happened rather than what is about to.

**What was tried and ruled out, so this isn't presented as unexplored:** a real-time detector that would adjust the forecast whenever a dip looks like a reporting delay was tested and rejected (Decision 043/M1-019) — only 42.9% precision overall, worse for Colombo/Gampaha specifically (46.2%/30.0%) — more than half of live flags would be false alarms on a genuine decline, so "fixing" this in real time would do more harm than good.

**Defense one-liner:** "This isn't a case we can't explain — we can point to the exact corrupted data point, the exact mechanism, and the specific dominant feature it poisoned. We also tested the obvious real-time fix and can show why it was rejected, rather than leaving the question unexplored."

**Evidence:** Decisions 026/028/043, M1-019 (`module_1_forecasting/MODULE_CONTEXT.md` Open Question #16, `EXPERIMENT_LOG.md`); `data/processed/module1/weekly_modeling_table.csv` (`is_reporting_anomaly` column); Figure 7.2 (now annotated with this event directly on the chart).

---

## In simple terms, why did BOTH the forecast (Module 1) and the outbreak classification (Module 2) go badly wrong for Wk25 2026, when the models had been doing fine before?

**Short answer:** one bad data point one week earlier confused both models at once, because they both rely most heavily on the exact same kind of clue — "how many cases were there last week."

**The simple story:** Colombo's reported cases went 507 → **20** → 1,138 across three weeks (Gampaha: 502 → 24 → 1,294). A real outbreak doesn't crash to almost nothing for one week and then jump to record levels — that pattern looks like a **reporting delay**: the health system likely didn't finish counting Wk24's real cases on time, and those uncounted cases got added into Wk25's number instead, on top of real continued growth. We can point to this exact data point — it's automatically flagged in our data as unusual (`is_reporting_anomaly`), independently of this specific week.

**Why it fooled both models the same way:** think of each model as asking "what just happened, and how is it changing?" before it guesses what happens next. For Module 1 (the forecast), the single most trusted clue is last week's error trend. For Module 2 (the classifier), the single most trusted clue is how unusual last week's case count was compared to normal. Both of those clues pointed the same wrong direction right before Wk25 — one said "the trend just dropped," the other said "this looks like a big data gap, best guess is nothing unusual." Both models did what they were designed to do; the input they trusted most was itself wrong that one time.

**Why the weeks before and after looked fine:** during the real, gradual build-up (roughly Wk18-23), "trust last week's number" was genuinely good advice, and both models tracked the rising case counts reasonably well. The models did not get worse at their job — the one signal they lean on hardest broke for a single week, right when accuracy mattered most.

**Is this a sign the models are broken, or missing something big like mobility data?** No — we can name the exact cause (one corrupted data point) rather than shrug and say "the model just isn't good enough." It's fair to also mention, separately, that the framework has no independent early-warning signal (like mobility or healthcare-seeking behaviour) that could hint at a surge before it shows up in case counts — but that's a general, honest limitation of the whole approach, not the specific reason this one week failed.

**We didn't just find the cause and stop there — we tried to fix it, honestly:**
- For Module 1, a real-time "catch this kind of dip and correct the forecast" detector was built and tested. It was **rejected**: it would have been wrong more than half the time for these exact two districts (Decision 043).
- For Module 2, we specifically tested replacing the missing "how unusual was last week" signal with the next best available reading, mirroring a fix that DID work for Module 1 elsewhere. It was also **rejected** — it made the model's overall accuracy slightly worse, not better, on the validation data used to decide such things (Decision 049/M2-016). We deliberately did not peek at the exact week in question to see if it "would have worked," because that would break the same evaluation rule that makes every other number in this project trustworthy.

**Defense one-liner:** "One bad data point, one week before, fooled both modules the same way — because both lean hardest on 'what just happened.' We can name the exact cause, we tried the obvious fixes for both modules, and we can show honestly why each fix was rejected rather than quietly assumed to work."

---

## Does Module 3's hybrid (spatial baseline + Random Forest) approach actually beat a simple, no-model baseline?

**Short answer:** For a long time, no — and we can show the full, honest arc of why, and what finally changed that.

**The original null result (M3-010/M3-011):** the official Stage 2 RF's headline "~51% MAE reduction over Stage 1" is mostly achievable with zero modeling — a naive "carry last week's own leftover error forward" baseline recovers about 93% of that reduction on its own, and actually beats the RF on MAE (9.44 vs. 9.96) and on rank-based hotspot metrics (M3-012: Spearman 0.849 vs. 0.813). A stacked correction-beyond-persistence formulation (M3-011) and an output-level blend of the two models (M3-013) were both tested; the blend genuinely improved on the RF alone but still only tied or lost to persistence.

**A calibration-based mechanism, borrowed directly from Module 2's own Stage 2 (isotonic recalibration of a raw score, no covariates), was also tried (M3-014) and failed cleanly** — root-caused to a real structural mismatch: Module 3's spatially-clustered CV folds put the highest-case-magnitude district cluster (Colombo/Gampaha) entirely outside the range any training fold's calibration curve had seen, so it clipped and badly underpredicted exactly the biggest outbreak weeks. This is not a defect in the calibration idea in general — it is specific to Module 3's geographic fold structure, unlike Module 2's random folds where every fold shares a similar distribution.

**What finally worked (M3-015):** a direct diagnostic of Stage 1's raw error (not assumed) found it strongly heteroscedastic — error magnitude scales with predicted magnitude, so every prior model, which targeted the *absolute* residual, let the largest outbreak weeks dominate the learning signal. Modeling the *relative* residual instead (`(actual − Risk_0)/(Risk_0+1)`, reconstructed back to an absolute prediction exactly, not approximately) produces a Random Forest that beats both naive persistence and the official RF on every reported metric — confirmed via a week-level bootstrap (not just a raw aggregate table, which M3-013 already showed can be misleading) and broad across 4 of 5 spatial folds, not concentrated in one.

**Two honest caveats kept alongside this result, not hidden:** the RMSE improvement is concentrated in the highest-case-volume fold (the official RF still has better RMSE in 3 of the other 4 folds), and the model performs notably worse at the one week already flagged (M3-001) as having no significant spatial clustering — the NE-monsoon representative week.

**Defense one-liner:** "We didn't stop at the first null result — we tested four mechanically different compensation ideas, including one borrowed directly from Module 2, rejected two honestly with a root cause each, and found a genuine, bootstrap-confirmed improvement by diagnosing WHY the residual was hard to learn (heteroscedasticity) rather than trying yet another feature set on the same wrong target scale."

**Evidence:** `module_3_spatial/EXPERIMENT_LOG.md` M3-010 through M3-015; `outputs/metrics/module3/relative_residual_comparison.csv`, `relative_residual_bootstrap_ci.csv`.

**Evidence:** Decisions 026/028/043/049, M1-019, M2-016 (`module_1_forecasting/MODULE_CONTEXT.md` Open Question #16; `module_2_classification/MODULE_CONTEXT.md` Open Question #11; both modules' `EXPERIMENT_LOG.md`); the previous question above for the Module 1-specific technical detail.
