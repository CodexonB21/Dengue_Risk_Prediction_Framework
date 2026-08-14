---
name: evaluator-qa-bank-module1
description: Mechanism/is-it-good/contradiction/deliberate-vs-incidental Q&A bank for Module 1 (Hybrid Time-Series Case Forecasting), companion to QUESTIONS_FOR_DEFENSE.md
metadata:
  type: report_support
---

# Evaluator Q&A Bank — Module 1 (Hybrid Time-Series Case Forecasting)

Companion to `research_context/QUESTIONS_FOR_DEFENSE.md`, which already covers Module 1
in this same adversarial style (seasonal-order gap, leakage pathway, holdout-discipline
proof, pooled-vs-per-district ablation, two-evidence-tier MASE). This file adds entries
that were genuinely missing, not duplicates. Cross-reference both files together.

Answers are terse defense ammunition, not report prose — cite exact file/line or
Decision/M1-0xx number for every claim.

---

### M1-1. Your docs call the XGBoost importance number "total gain" — is that accurate?

**Shape:** Mechanism

No. The code calls `final_model.get_booster().get_score(importance_type="gain")`
(`src/module1_forecasting/compensation_model.py:827`), which is XGBoost's **average**
gain per split using that feature, not total gain. `plot_feature_importance.py:97`
labels its axis "Gain (total loss reduction attributed to this feature)" and
`MODULE_CONTEXT.md`'s prose calls the numbers "total gain" — both are an imprecise
restatement of what `importance_type='gain'` actually returns. The correct one-line
answer if pressed: "average per-split gain, via XGBoost's own `get_score` API — not
literally summed."

---

### M1-2. Is the model that produced your feature-importance ranking the same one that produced your headline holdout MASE?

**Shape:** Contradiction-check

No — two different fitted objects. The published holdout MASE (~0.374–0.375) comes from
`train_and_predict_holdout`, trained on folds 1–14 only, never exposed to the holdout
block. The feature-importance CSV (`outputs/metrics/module1/xgboost_feature_importance.csv`)
comes from `train_final_production_model`, trained on folds 1–14 **plus** the holdout
block combined, run once as a separate step. Both use the same pooled-XGBoost recipe, but
they are trained on different data windows. The honest answer to "does that top-feature
ranking apply to the model that produced the holdout number" is no.

---

### M1-3. Your DM-test significance count changed from 14/25 to 5/25 across two write-ups — which is real?

**Shape:** Is-that-actually-good

5/25 (at the stricter `holdout_only` scope, n=104/district) is the corrected, current
number. An earlier draft cited "14/25 with a named district list that matches no saved
CSV" — a real citation-gap bug, caught and fixed, documented in `MODULE_CONTEXT.md`'s
"Statistical significance" section. At the larger, pooled `validation_and_holdout` scope,
12/25 districts reach significance — report both scopes, and lead with the stricter one
if asked for "the" number.

---

### M1-4. Mullaitivu has negative residual-variance-reduction but still "improves" on MASE — how?

**Shape:** Is-that-actually-good

MASE (a point-accuracy metric) and residual-variance-reduction (`1 - var(final_residual) /
var(stage1_residual)`, a spread metric) answer different questions and can disagree.
Mullaitivu's variance reduction is -0.14 (Stage 2 makes the *spread* of unexplained error
slightly worse) while its MASE still improves 17.1% (validation) / 16.2% (holdout) — Stage
2 shifted the typical error down even while occasionally producing larger outliers. 3 of
the 4 districts with negative variance reduction still improve on MASE — this is reported
as-is (Decision 016), not smoothed into one number.

---

### M1-5. Why do `residual_lag_1/2` dominate Stage 2 feature importance?

**Shape:** Mechanism (why)

Because SARIMA's own out-of-sample residuals are not white noise. Decision 016/017's own
Ljung-Box diagnostic (lags 26/52) finds **23/25 districts still show significant residual
autocorrelation even after Stage 2 correction** — meaning the raw Stage 1 residual carries
real, exploitable short-lag structure Stage 1 leaves behind. `residual_lag_1/2` giving
Stage 2 a genuine, evidence-backed predictive signal is a direct consequence of that
autocorrelation, not an artifact of how XGBoost happens to split features. This is the
mechanistic "why," distinct from just naming the feature.

---

### M1-6. How exactly was the feature-importance test run — one model, cross-validated, on which data?

**Shape:** How (procedure)

A single run on one frozen model — `train_final_production_model`
(`compensation_model.py`), fit once on folds 1–14 + holdout combined — via
`get_booster().get_score(importance_type="gain")` (line 827). It is **not**
cross-validated or averaged across the 14 walk-forward folds, and it is **not** computed
on the same model that produced the reported holdout MASE (see M1-2). Be upfront about
this scope if asked "how robust is this ranking" — it's one fit, not a distribution.

---

### M1-7. Why did switching to `reg:absoluteerror` fix the Vavuniya-driven corruption, mechanically?

**Shape:** Mechanism (why)

MAE's gradient is bounded at ±1 regardless of error magnitude; squared error's gradient
scales with the error itself. When Vavuniya's 2010 fold-1 SARIMA diverged to a ~30,000,000
forecast against an actual mean of ~6 cases/week, the resulting -30,000,000 residual, under
squared-error loss in a pooled model, dominated the global loss surface and corrupted every
other district's predicted residual (e.g. Colombo's predicted residuals jumped from O(100)
to O(1,000,000)). Under MAE, that same outlier contributes the same bounded gradient as any
other row — structurally incapable of dominating the pooled fit the way squared error did.
Discovered mid-implementation (Decision 014), not planned upfront.

---

### M1-8. Why is Stage 2 one pooled model instead of one per district — and does per-district ever actually win?

**Shape:** Deliberate-vs-incidental

Pooling (Decision 014) was chosen because per-district data is too thin in early folds
(~52 rows for one district vs. ~1,300+ pooled). This was independently re-tested, not
assumed: a full per-district ablation (Decision 045/M1-021) was **decisively worse**
overall (validation-aggregate median MASE 0.7473 vs. pooled 0.5821, +28.4%; only 1/13 folds
and 4/25 districts improved). Those 4 exceptions — Monaragala, Mannar, Vavuniya, Matale —
are not carved out in production; pooling still applies uniformly to all 25 despite a
locally better answer existing for those 4 (see M1-13). Flagged explicitly as a possible
narrow follow-up, not built.

---

### M1-9. Stage 1 is per-district (Decision 002); Stage 2 is pooled (Decision 014) — which one did you actually test both ways?

**Shape:** Contradiction-check

Only Stage 2's pooling choice was empirically ablated (M1-021, see M1-8). Stage 1's
per-district SARIMA (Decision 002) was an a priori design decision from kickoff, never
independently tested against a pooled-SARIMA alternative. Both decisions are correctly
described as "per-district vs. pooled," but for different pipeline stages, and only one
carries direct ablation evidence — `RESEARCH_DECISIONS.md` itself cross-references this
("Decision 014... would revisit Decision 002 for Stage 2 specifically"). Do not conflate a
question about SARIMA with a question about the XGBoost residual model — this exact
confusion is a named calibration example ("this pooled model is regarding XGBoost right,
not SARIMA?").

---

### M1-10. Your hyperparameter search cleared every validation safeguard and still regressed on holdout — so what's a validation safeguard actually worth?

**Shape:** Is-that-actually-good

A 40-candidate randomized search over Stage 2's XGBoost hyperparameters found a candidate
that beat production's aggregate **and** a majority of 13 validation folds **and** a
majority of 25 districts (validation-aggregate median MASE 0.5659 vs. 0.5821, -2.8%) — a
safeguard specifically designed to filter fold-count noise. It still regressed on the
one-time holdout check (0.3874 vs. 0.3741, +3.6%) and was rejected (Decision 044/M1-020).
This is direct, first-hand evidence that a 13-fold majority vote does not guarantee
holdout generalization — presented as proof the holdout-integrity rule (Decisions 009/010)
catches real overfitting, not a bureaucratic formality.

---

### M1-11. Why does SARIMA give a flat line for some districts?

**Shape:** Mechanism (why)

Two compounding mechanisms, both code-verified. First: 18/25 districts' AIC-selected
config is `seasonal_order=(0,0,0,52)` — confirmed independently by two seasonal-differencing
tests (OCSB and Canova-Hansen `nsdiffs()`) both returning `D=0` for all 25 districts across
{raw, log1p} candidates, zero disagreements (`seasonal_diff_diagnostics.py`,
`seasonal_differencing_tests.csv`). Second: with no seasonal component and low-order
non-seasonal terms, a single-shot multi-step SARIMAX forecast has no long-memory dynamics
to draw on and mathematically reverts to the model's unconditional mean over the forecast
horizon — e.g. Colombo's `sarima_prediction` ranges only 335.1–367.8 across all 8 steps of
`forecast_future.py`'s horizon (Decision 053/M1-022). Root cause: `auto_arima`'s AIC
selection optimizes one-step-ahead in-sample fit, not 52-week-ahead forecast skill — tested
directly via an STL+ARIMA pilot on 3 non-seasonal districts and rejected 0/3 (Decision
036/M1-012). Not fixed; documented as a known Stage-1-alone limitation that Stage 2
substantially compensates for (see `QUESTIONS_FOR_DEFENSE.md`'s existing seasonal-order
entry for the compensation evidence).

---

### M1-12. How exactly did you determine 18/25 districts have no seasonal component — what test, on what data?

**Shape:** How (procedure)

Two independent statistical tests, not one team judgment call: OCSB and Canova-Hansen
`nsdiffs()` seasonal-differencing tests, run on 50 rows (25 districts × {raw, log1p}
transform candidates) — `seasonal_diff_diagnostics.py`, results in
`outputs/metrics/module1/seasonal_differencing_tests.csv`. Both tests independently
returned `D=0` for the same 18 districts with zero disagreements between the two methods —
that agreement is itself worth citing as corroboration, not just one test's opinion, if
asked how confident this finding is.

---

### M1-13. Why do exactly those 4 districts (Monaragala, Mannar, Vavuniya, Matale) benefit from per-district modeling instead of pooling?

**Shape:** Mechanism (why)

Not a random split of the ablation — these are the same districts already independently
flagged in earlier diagnostics (Decisions 017, 034, 037) as ones where the pooled
correction underperforms. M1-021's per-district ablation didn't discover a new pattern; it
confirmed one that was already visible in prior, unrelated diagnostics. This sharpens the
earlier shrinkage work into a suggestion for a narrow, targeted per-district remedy for
these 4 specifically, rather than a wholesale architecture change — flagged as future work,
not built.

---

### M1-14. How exactly does the vintage-ensemble nowcast combine multiple SARIMA fits into one number?

**Shape:** How (procedure)

`forecast_future._collect_vintage_forecasts()` (lines 189–233) fits `ensemble_window`
(default 4, `MODULE1_NOWCAST_ENSEMBLE_WINDOW`) **independent** SARIMA models, each trimmed
back 0–3 additional weeks from the latest data, each extended forward via its own multi-step
call to the **same target week**. These are collected **in transformed space** (log1p if
`use_log1p`, else raw) — not in raw case-count space — before
`_aggregate_vintage_forecasts()` (lines 236–266) averages them (`"mean"` is the adopted
default; `"median"`/`"trimmed_mean"` were tested and not promoted, see M1-15), then
inverse-transforms and clips at 0. This is mechanically distinct from
`rolling_one_step._vintage_ensemble_step()`, which reuses persisted fitted-model state
across a sequential loop rather than refitting fresh each time — both were validated to
give equivalent behavior (Decision 040).

---

### M1-15. Why is the vintage-ensemble window exactly 4, and is "mean" the right aggregator?

**Shape:** Deliberate-vs-incidental

The mechanism (averaging independent vintage fits) is deliberate and validated at full
scale — it raised the number of districts where Stage 2 helps from 10/25 to 24/25 and
improved rolling sMAPE for 22/25 districts (Decision 039/M1-015). The specific window
size of 4 was never itself ablated against 3, 5, or 6 — a real deliberate/incidental split
within one decision. "Mean" vs. "median"/"trimmed-mean" **was** tested: differences were
≤1%, and at window=4, median and trimmed-mean are mathematically identical, so mean was
kept as the simplest adopted default (Decision 042/M1-018) — not because it was proven
strictly best.

---

### M1-16. How exactly do you test whether Stage 2's improvement over Stage 1 is statistically real, not noise?

**Shape:** How (procedure)

A Diebold-Mariano test (`evaluate.dm_test`) with HAC/Newey-West long-run variance using a
12-lag Bartlett kernel, plus a Harvey-Leybourne-Newbold small-sample correction — comparing
Stage-1-only vs. Stage-1+Stage-2 squared-error loss. Run at **two separate scopes**
deliberately: `validation_and_holdout` (pooled, larger sample) and `holdout_only` (stricter,
genuinely never-touched-until-scoring sample, n=104/district) — see M1-3 for why the two
scopes give different significance counts. Added alongside residual-variance-reduction and a
final Ljung-Box check (Decision 016) specifically because MASE alone doesn't answer whether
an improvement is statistically distinguishable from noise.

---

### M1-17. Why does the recursive multi-step forecast drift downward, mechanistically?

**Shape:** Mechanism (why)

From horizon step 2 onward, the lag inputs feeding Stage 2 (`residual_lag_1/2`,
case-count lags) are the model's own prior **predicted** residuals, not real observed
ones. Predicted residuals are systematically shrunk toward the mean relative to real
residuals, so the genuine autocorrelation signal that normally justifies leaning on
`residual_lag_1` (see M1-5) weakens with every recursive step, compounding into a
downward drift (M1-022/M1-023: 24/25 districts declined 8-weeks-out vs. week 1, 4
collapsed to exactly 0). Shortening the horizon 8→4 weeks (Decision 053) reduces exposure
to this drift but does not fix the underlying mechanism — direct per-horizon models were
tested and found to only narrow, not reverse, the advantage over recursive as horizon
grows (M1-023/M1-024), and were not promoted to production.

---

### M1-18. Your recursive-forecast bias hypothesis — did the data actually confirm it?

**Shape:** Deliberate-vs-incidental (honest negative result)

No — it was falsified, not confirmed. The working hypothesis going into M1-023/M1-024 was
"direct forecasting's advantage over recursive grows with horizon." The result: the
advantage on MASE **narrows** from +0.037 (h=2) to -0.006 (h=4, recursive marginally
ahead), even though sMAPE and per-district win-rate still favor direct. This is reported
as a genuinely surprising empirical result, not dressed up after the fact as an expected
finding — direct forecasting was not promoted to production on the strength of this
narrowing margin.
