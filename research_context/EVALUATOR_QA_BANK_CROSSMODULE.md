---
name: evaluator-qa-bank-crossmodule
description: Mechanism/is-it-good/contradiction/deliberate-vs-incidental Q&A bank for cross-module questions spanning Modules 1-3, companion to QUESTIONS_FOR_DEFENSE.md
metadata:
  type: report_support
---

# Evaluator Q&A Bank — Cross-Module

Companion to `research_context/QUESTIONS_FOR_DEFENSE.md` and to the per-module files
(`EVALUATOR_QA_BANK_MODULE1/2/3.md`). This is the flagship "same technique — deliberate or
coincidence?" question shape, since almost all of it only makes sense compared across
modules.

Answers are terse defense ammunition — cite exact file/line or Decision number.

---

### X-1. Is `is_reporting_anomaly` shared infrastructure or module-specific?

**Shape:** Deliberate-vs-incidental

Neither — a third, undocumented category. `flag_reporting_anomalies()`
(`src/preprocessing/reporting_anomalies.py:33-86`) is **not** called from
`src/preprocessing/shared.py` (the true shared layer per Decision 013 — zero matches on a
direct grep) and is **not** in Decision 013's own enumerated list of what the shared layer
covers (raw corrections, Kalmunai merge, calendar, climate aggregation, population
interpolation). It's a standalone helper called independently by exactly two of the three
modules: Module 1 (`module1_preprocessing.py:311`, after week-53 merge and imputation) and
Module 2 (`module2_preprocessing.py:286`, after imputation, no week-53 merge — Decision
020 keeps week 53 unmerged for M2). **Zero references anywhere in `src/module3_spatial/`.**
It genuinely cannot live in `shared.py`: Module 1 calls it on a week-53-merged series,
Module 2 calls it on an unmerged one — the flagging *logic* is identical/reusable, but the
*timing* structurally cannot be shared because the two modules' weekly series have already
diverged by the time it runs. Decision 028's own header
("Module 1 + Module 2 (shared preprocessing column)") is misleading if read against
Decision 013's strict definition — it's shared between two modules via a helper file,
not part of the actual shared layer.

---

### X-2. Is your climate-anomaly formula (Decision 003) identical across modules?

**Shape:** Deliberate-vs-incidental

Module 1 and Module 2: **yes, literally the same function object**, not just the same
formula independently coded. Module 1 defines `compute_fold_climate_anomalies()`
(`module1_forecasting/feature_engineering.py:175-213`), computed **per walk-forward fold,
training rows only**. Module 2 imports and calls that exact function
(`module2_classification/feature_engineering.py:98-99`) rather than reimplementing it.
Module 3 **deliberately diverges**: `compute_climate_anomaly()`
(`module3_spatial/feature_engineering.py:134-145`) uses
`df.groupby(["District","Week"])[source_col].transform("mean")` — a full-sample,
all-years mean, not a strictly-prior/fold-scoped one. The function's own docstring
justifies this explicitly: Module 3's validation axis is spatial K-means clustering, not
temporal walk-forward, so a full-sample per-week mean does not leak across folds the way it
would under M1/M2's temporal CV (see X-8). This is a clean answer: identical code reuse
for M1/M2, an explicitly-justified divergence for M3 — not an oversight. Don't confuse
this with Module 3's separate `mahalanobis_anomaly_score` (a different, multivariate
concept sharing only the word "anomaly").

---

### X-3. Do all three modules compute feature importance the same way?

**Shape:** Deliberate-vs-incidental

No. Module 1: XGBoost gain (`get_score(importance_type="gain")`,
`module1_forecasting/compensation_model.py:827`). Module 2 (currently): Random Forest
Gini/MDI (`clf.feature_importances_`, `module2_classification/baseline_classifier.py:682`)
— though it used XGBoost gain when XGBoost was still Module 2's official model, pre-
Decision-025. Module 3: Random Forest Gini/MDI (`final_model.feature_importances_`,
`module3_spatial/compensation_model.py:386`) — matching Module 2's *current* mechanism,
not Module 1's. The M2/M3 convergence on MDI is incidental — both independently picked a
scikit-learn Random Forest and used its default attribute; no document anywhere in the
repo (`FEATURE_ENGINEERING_SPEC.md`, `PIPELINE_ARCHITECTURE_PLAN.md`, any `MODULE_CONTEXT.md`)
discusses reconciling or even acknowledging that the three modules use different importance
statistics. This is the honest answer to "is it the same technique across all three
modules, and if not, is that a decision or a coincidence?" — no, and coincidence, entirely
downstream of which model each module's benchmark happened to select.

---

### X-4. One data point broke both Module 1 and Module 2 the same week — same bug, or same weakness?

**Shape:** Mechanism

Same underlying weakness, two mechanistically distinct failure paths. Colombo's reported
cases went 507 → **20** → 1,138 across three weeks (Gampaha: 502 → 24 → 1,294) — a
reporting-delay artifact already flagged `is_reporting_anomaly=True` in the pipeline
independently of this question (Decision 026/028). Both modules' single most-trusted
input is "what happened last week or two": Module 1's `residual_lag_1` (see Module 1 file,
M1-5) got fed an artificially collapsed value, corrupting its trend signal for the one week
it needed to predict a multi-fold jump. Module 2's `case_anomaly_lag_1` (~35% of Random
Forest feature importance, see Module 2 file, M2-13) got masked to `NaN` by the same
reporting-anomaly flag (Decision 028's `mask_untrusted_cases`) and was then silently
back-filled by `RandomForestClassifier`'s median imputer inside the sklearn pipeline —
told, in effect, "nothing unusual here" right when something very unusual was about to
happen. Both models did what they were designed to do; the specific input each leans on
hardest broke for the same single week, via two different code paths.

---

### X-5. You caught and fixed two mis-citations to the wrong Decision number in your own logs — does that happen often, and is it actually fixed?

**Shape:** Deliberate-vs-incidental (meta, self-correction discipline)

Mostly fixed, one instance still open. Decision 050 corrects an earlier erroneous
"Decision 032" citation (Module 3), and Decision 052/M3-016 corrects an earlier erroneous
"Decision 031" citation (also Module 3, mistakenly pointing at an unrelated Module 1
entry about the production nowcast) — both corrections propagated to `MODULE_CONTEXT.md`
and `RESEARCH_DECISIONS.md`. But `module_3_spatial/EXPERIMENT_LOG.md:1169` (M3-008's own
"Documentation Updated" list) still reads the stale "Decision 032," never actually
updated. Good, citable evidence of the project catching and correcting its own citation
drift — with the honest caveat that one specific instance of that same drift is itself
still uncorrected as of this writing.

---

### X-6. What's the actual cross-module integration status — has anything been tried between modules, or is it all deferred?

**Shape:** Deliberate-vs-incidental

Mixed, and it's important not to overstate either direction. Module 1 feeding Module 2
(Decision 022, item 6) is **deferred, never built** — the two modules' walk-forward fold
boundaries are misaligned (M1: 14 folds, 3-year minimum training window; M2: 13 folds,
4-year minimum), so merging M1's forecast into M2 as a feature requires a dedicated
fold-alignment leakage audit, not a two-line merge; explicitly planned as an optional
future ablation, not abandoned. Module 3 feeding Module 2 **was** actually tried
(M2-014, see Module 2 file M2-11) and **rejected** — M3's `Risk` output turned out
redundant with `case_anomaly_lag_1/2`. So: one real, executed, negative cross-module
fusion result exists; the other remains an unbuilt, deferred idea. Don't cite the M1→M2
deferral as if it carries the same evidentiary weight as the M3→M2 rejection — one was
tested and failed, the other was never attempted.

---

### X-7. Why does "what just happened last week" dominate feature importance in both Module 1 and Module 2 — coincidence, or structural?

**Shape:** Mechanism (why)

Structural, not coincidental. Module 1's target (a SARIMA residual) and Module 2's target
(an outbreak flag) are both, by construction, **deviations from an expected baseline** —
SARIMA's own forecast in one case, a harmonic seasonal expectation in the other. Short-lag
deviations from a baseline are autocorrelated in epidemiological count data generally
(confirmed directly for Module 1 via Decision 016/017's Ljung-Box diagnostic — 23/25
districts still show significant lag-26 autocorrelation even post-correction), so a model
predicting either kind of deviation will naturally find the most recent deviation
informative about the next one. This is a genuinely unifying "why" for the whole
three-module framework's shared reliance on recency, not a property either module invented
independently — strong closing material for tying the framework's overall design
philosophy together.

---

### X-8. Why does Module 3 use a completely different validation structure (spatial clustering) instead of the temporal walk-forward Modules 1 and 2 use?

**Shape:** Mechanism (why)

Because the three modules face different leakage risks along different axes. Module 1/2
predict forward in time (Decision 009: expanding-window walk-forward, held-out final
block) — their leakage risk is future information leaking into training. Module 3
detects hotspots across space in a given week — its leakage risk is spatial contiguity
between training and test districts (a model trained partly on Colombo's neighbors could
trivially "predict" Colombo). The two CV structures apply the same underlying discipline —
don't let training see what the test split needs to be blind to — along the axis that's
actually relevant to each task. This directly explains X-2's climate-anomaly divergence:
Module 3's full-sample per-week climate mean is safe precisely because temporal leakage
isn't the risk its CV structure is guarding against.

---

### X-9. How do the three modules' fold/holdout boundaries relate to each other — can I compare a Module 1 metric to a Module 2 metric on "the same period" directly?

**Shape:** How (procedure) / contradiction-check

No, not directly. Per Decision 022 (item 6): Module 1 uses 14 walk-forward folds with a
3-year minimum training window (`DEFAULT_MIN_TRAIN_YEARS`); Module 2 Stage 1 uses 13 folds
with a 4-year minimum. The fold boundaries are misaligned by construction — this is
exactly why merging Module 1's `final_prediction` into Module 2 as a feature was deferred
rather than done as a quick merge (see X-6): it would require a dedicated fold-alignment
leakage audit first, not just matching column names. Module 3's fold structure isn't
temporal at all (spatial K-means clusters, see X-8), so it isn't even expressed on the
same axis as M1/M2's folds. Bottom line for defense: don't present M1's holdout MASE and
M2's holdout PR-AUC as scored over "the same 104 weeks" without checking — they aren't
guaranteed to be, and for M3 the question doesn't even apply the same way.
