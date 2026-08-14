---
name: evaluator-qa-bank-module2
description: Mechanism/is-it-good/contradiction/deliberate-vs-incidental Q&A bank for Module 2 (Hybrid Outbreak Risk Classification), companion to QUESTIONS_FOR_DEFENSE.md
metadata:
  type: report_support
---

# Evaluator Q&A Bank — Module 2 (Hybrid Outbreak Risk Classification)

Companion to `research_context/QUESTIONS_FOR_DEFENSE.md`. **Important:** that file's
existing Module 2 entry ("Why does Module 2 use isotonic calibration...") is currently
stale — it describes the pre-Decision-047 state. This file uses the current, verified
state (Decision 047 / M2-013, 2026-08-06) throughout. See M2-2 below and the standalone
correction applied to `QUESTIONS_FOR_DEFENSE.md` in the same batch as this file.

Answers are terse defense ammunition — cite exact file/line or Decision/M2-0xx number.

---

### M2-1. What exactly computes feature importance in Module 2, and is it the same technique as Module 1's?

**Shape:** Mechanism

`compute_feature_importance()` (`src/module2_classification/baseline_classifier.py:667-690`)
branches by model type: for the currently-official Random Forest, it's
`clf.feature_importances_` (line 682) — sklearn's default **mean decrease in impurity
(Gini importance)**, computed only for the single official model
(`final_model = train_final_production_model(...)`, called once — same
single-frozen-model pattern as Module 1, see M1-6). This is a **different statistic**
from Module 1's XGBoost gain-based importance
(`get_booster().get_score(importance_type="gain")`,
`src/module1_forecasting/compensation_model.py:827`). The divergence is incidental: it
tracks whichever model architecture each module's benchmark happened to select, not a
coordinated methodological choice — nowhere in `MODULE_CONTEXT.md` or
`FEATURE_ENGINEERING_SPEC.md` is this reconciled or even flagged. Worth noting: when
XGBoost was still Module 2's official model (pre-Decision-025), its importance stat
**did** match Module 1's (`get_score(importance_type="gain")`,
`baseline_classifier.py:672`) — the current mismatch is a side effect of the later
label-driven model flip, not a standing design difference.

---

### M2-2. Your own defense doc says isotonic is production — is that still true?

**Shape:** Contradiction-check

No. `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md` M2-013 (Decision 047, 2026-08-06, after
Random Forest Stage-1 retuning) are unambiguous: **Platt scaling is now official**, not
isotonic. Current numbers: alert threshold **0.100** (not 0.14), high-confidence boundary
**0.500** (not 0.35), holdout PR-AUC **0.4228** (not 0.412), holdout recall **62.5%**
(not 60%), precision **34.2%** (not 33.8%). `QUESTIONS_FOR_DEFENSE.md`'s existing entry
states the pre-047 numbers and was never updated — Decision 047's own "Documentation
Updated" list does not include that file. If asked "why isotonic over Platt," the current
honest answer is the reverse of what that file says: Platt now beats isotonic (median
validation BSS 0.2271 vs. 0.2195) — see M2-3 for why this flipped.

---

### M2-3. Isotonic beat Platt, then lost, then won, then lost again across four re-runs — what's actually going on?

**Shape:** Contradiction-check

Four re-runs, four different winners, and every flip was caused by an **upstream** change
(Stage 1 hyperparameters or the label definition), never a Stage 2 code change:
pre-tuning (M2-002) Platt wins (0.130 vs 0.127); post-XGBoost-tuning (Decision 023/M2-003)
isotonic flips ahead (0.166 vs 0.145); post-label-re-estimation (Decision 025/M2-005)
isotonic still wins but the race tightens (0.2146 vs 0.2116); post-RF-tuning
(Decision 047/M2-013) it flips back to Platt (0.2271 vs 0.2195). The
**architecture-family** ranking — recalibration (isotonic/Platt) beats feature-based
stacking every time, often by a wide margin — is the stable, principled finding.
Isotonic-vs-Platt within the top two is a genuinely close race (margins ≤0.02 every
time), decided entirely by what Stage 1 or the label looked like that round, not by any
property of the calibration methods themselves.

---

### M2-4. Random Forest replaced XGBoost as your official Stage 1 model — why, and how close was it?

**Shape:** Deliberate-vs-incidental

It was **not** a deliberate model-family preference. Random Forest becoming official
(Decision 025/M2-005) fell out entirely as a side effect of the label-estimator change
(k=2/exact-week → k=3/harmonic, see M2-5): the same automated `select_official_model()`
procedure (`baseline_classifier.py:565-578`) was simply re-run under the new label, and RF
happened to win median PR-AUC by a **margin of 0.004** (0.377 vs. 0.373 for XGBoost) — a
very close call, not a decisive architectural case for trees-with-Gini over gradient
boosting. Be honest about this margin if asked "why RF" — there is no mechanistic
explanation documented for why RF specifically edges XGBoost under the new label; see
M2-19.

---

### M2-5. Your label formula changed from k=2/exact-week to k=3/harmonic — walk me through what changed and why.

**Shape:** Mechanism

Original (Decision 019, kickoff): `outbreak = 1 if cases > exact_per_(District,Week)_mean
+ 2.0 * exact_per_(District,Week)_sd`, via `compute_historical_stats()`
(`labels.py:75-109`, kept in code as a control, not deleted). Current (Decision 025, same
day, later): `outbreak = 1 if cases > harmonic_seasonal_curve(District,Year) + 3.0 *
residual_SE`, via `compute_historical_stats_harmonic()` (`labels.py:127-202`) — a 1-harmonic
OLS regression on week-of-year, refit expanding per year on strictly-prior real data;
`historical_sd` is now the regression's residual standard error (one value per
district-year), not a per-exact-week sample SD. This was a deliberate, audited change: 6
candidate estimators × 3 k values were tested before choosing, and the change is
documented to flip at least one real flagship case — Colombo's 2025 Wk15 label goes from
1→0 because its old exact-week SD (87.7) was much smaller than the harmonic SD (209.0). It
reduces the aggregate "outbreak rate" from 18.4% to 8.6% at the cost of that one
high-variance-district case.

---

### M2-6. A PR-AUC of 0.41-0.42 sounds mediocre — is it?

**Shape:** Is-that-actually-good

Holdout prevalence is only ~1.5% (~40 positive rows of ~2,600); a PR-AUC of 0.41-0.42
represents roughly a 27-28x uplift over a no-skill/prevalence baseline — a raw PR-AUC
number alone genuinely does look unimpressive without that comparison point, and it's on
you to supply it, not the number itself. One thin spot: the module's own
discrimination-vs-calibration diagnostic (uplift 3.65x median, up to 13.2x) was computed
under the **pre-Decision-025 label** and was never recomputed after the label changed —
`MODULE_CONTEXT.md` doesn't flag that specific diagnostic as stale relative to the current
label. If pressed on the exact uplift ratio today, say the ratio needs recomputation under
the current label rather than citing the old 3.65x/13.2x figures as current.

---

### M2-7. Your alert threshold is 0.10, not 0.5, and two-thirds of your alerts are false positives — is that a flaw?

**Shape:** Is-that-actually-good

Deliberate, not an oversight: τ=0.100 is the F2-optimal threshold for early-warning
recall (Decision 024), computed as `argmax(F2)` over validation-split rows carrying the
official architecture's probability (`risk_thresholds.py:88-104`) — F2 weights recall
above precision by design, appropriate for surveillance where missing an outbreak is
costlier than a false alarm. Precision at that threshold is 34.2% — roughly 2 of 3 alerts
are false positives — an explicit, accepted trade-off, not hidden, but it needs this
framing every time it's cited: a >10% calibrated probability triggers an alert, not "50%+
chance of outbreak."

---

### M2-8. A stacked model beat your production PR-AUC by a wide margin and caught 15 more outbreaks — why isn't it production?

**Shape:** Contradiction-check

Stacked XGBoost + Module 1 forecast features (M2-007D) beats Platt/isotonic on holdout
PR-AUC (0.465 vs. 0.412 at the time, +0.054, clearing a pre-registered ≥0.02 gate) and
alert recall (77.5% vs. 60%) — but Brier Skill Score goes **negative** (-0.067) and alert
precision collapses (0.194 vs. 0.338). The decision was "accept the feature signal, defer
the production switch" — a deliberately non-adopted positive discrimination result,
because ranking ability and calibration are different properties (see M2-18) and this
project's Stage 2 selection metric is BSS, not PR-AUC alone.

---

### M2-9. You tested fixing the exact feature that caused the Wk25 false negative — did it work?

**Shape:** Is-that-actually-good (honest limitation)

No. M2-016 (Decision 049) tested substituting `case_anomaly_lag_2` for `case_anomaly_lag_1`
whenever the prior week is `is_reporting_anomaly`-flagged — mirroring a fix that worked for
Module 1. Result: validation median PR-AUC 0.3865 vs. baseline 0.3917 — worse, rejected.
Holdout was deliberately never checked against this specific fix, so whether it would have
prevented the Colombo/Gampaha 2026 Wk25 false negative is genuinely unknowable under this
project's own no-peek-at-holdout rule — say exactly that if asked "so did you fix it," not
a hedged version of "yes."

---

### M2-10. You rejected SMOTE once, then rejected it again — was the second test redundant?

**Shape:** Deliberate-vs-incidental

No — the second test used corrected reasoning, not the same argument twice. Decision
021's original SMOTE rejection reasoning ("it blurs the temporal fold boundary") was later
found, on the team's own review, to be imprecise. M2-006 re-tested with a corrected,
leakage-safe SMOTENC and reconfirmed the **conclusion** (reject) on stronger, corrected
grounds — a validation-improves/holdout-regresses pattern. Good example of the project
correcting its own reasoning, not just restating a prior conclusion.

---

### M2-11. You tested feeding Module 3's spatial risk into Module 2 — what happened?

**Shape:** Deliberate-vs-incidental

Rejected. M2-014 tested consuming Module 3's `Risk` output (`m3_risk_lag_1/2`, lagged 1-2
weeks, gap-safe) as a Stage 1 feature — a genuine cross-module (M3→M2) feature-fusion
attempt, not just an assumed-unnecessary idea. Result: validation median PR-AUC got worse
(0.3838 vs. 0.3896 without it). Plausible reason: `case_anomaly_lag_1/2` already dominates
feature importance, and Module 3's `Risk` is itself a spatially-smoothed transform of the
same underlying case-count signal — redundant, not new information.

---

### M2-12. Is `is_reporting_anomaly` actually used in Module 2, or just computed and ignored?

**Shape:** Mechanism

Used, via two concrete paths: (1) `feature_engineering.py:295-300` masks
`case_anomaly_lag_1/2` to `NaN` the week after a flagged week
(`case_zscore.where(~stats["is_reporting_anomaly"].fillna(False))`). (2)
`reporting_anomalies.py:142-149`'s `mask_untrusted_cases()` ORs `is_imputed` with
`is_reporting_anomaly` into one "untrusted" mask, consumed by `feature_engineering.py:204`
to mask `cases_lag_1-4`/rolling stats before they're derived. This is a Decision 028
mechanism shared with Module 1 (same function, same file), not something Module 2 built
independently — but note this is a cross-module utility outside the true shared
preprocessing layer, never touching Module 3 (see the cross-module file's `is_reporting_anomaly` entry).

---

### M2-13. Why does `case_anomaly_lag_1/2` dominate Stage 1 importance?

**Shape:** Mechanism (why)

Because the outbreak label itself is a threshold on a harmonic-expectation z-score
(`compute_historical_stats_harmonic()`, see M2-5); `case_anomaly_lag_1/2` is last week's
own observation of that same underlying statistic
(`case_zscore = (Number_of_Cases - historical_mean) / historical_sd`,
`feature_engineering.py:262-314`). The top feature being the most temporally-proximate
lagged echo of the exact statistic the label is built from is a sharp, slightly
adversarial framing worth being ready for: it's not literal leakage (it's lagged, and the
label uses the *current* week's value while the feature uses *last* week's), but it does
mean the classifier's strongest signal is structurally tied to the label's own
construction, not independent evidence.

---

### M2-14. How exactly was Module 2's feature-importance test conducted — same procedure as Module 1's?

**Shape:** How (procedure)

Yes, the same single-frozen-model pattern. `run_stage1_pipeline()`
(`baseline_classifier.py:756-765`) trains `final_model = train_final_production_model(...)`
once, then calls `compute_feature_importance(final_model, official_model)` once on that
single fit — not averaged or cross-validated across the 13 walk-forward folds, and not
computed on the same model instances that produced the reported holdout PR-AUC/recall
numbers (which come from `train_and_predict_holdout`, a separately-trained fit). Confirmed
directly in code (`baseline_classifier.py:667-690, 756-765`) — this mirrors Module 1's own
scope caveat (M1-6) exactly.

---

### M2-15. How exactly did you empirically validate the label threshold (k=2, then k=3)?

**Shape:** How (procedure)

A candidate sweep, not a single chosen value: Decision 019's kickoff audit tested k ∈
{1.5, 2.0, 2.5} against a class-balance sanity band (2%-40% outbreak rate per district,
via `scripts/data_audit_module2.py`) before locking k=2 as a "reasonable middle default."
Decision 025 later tested 6 candidate estimators × 3 k values (including the harmonic
model and k=3) before adopting the current harmonic/k=3 combination — chosen specifically
because it reduces the aggregate rate from 18.4% to 8.6%, closer to WHO/CDC-style
single-digit epidemic-alerting norms, at the documented cost of flipping some
high-variance-district cases (see M2-5).

---

### M2-16. Why does Platt scaling fit on `logit(p)` instead of raw `p`?

**Shape:** Mechanism (why)

That is the actual definition of Platt scaling.
`compensation_model.py:376-387`: `X_train = _logit(train_df[BASE_PROB_COL]...).reshape(-1,
1)`, then a standard `LogisticRegression` fit on that single log-odds feature. Fitting
directly on a bounded `[0,1]` raw probability would not be standard Platt scaling — it
would be an ad hoc single-feature regression on a bounded variable, without the
log-odds transform that gives the fit a numerically well-behaved linear relationship to
work with.

---

### M2-17. How exactly is your F2-optimal alert threshold (τ=0.10) computed — argmax of what, on which data?

**Shape:** How (procedure)

`risk_thresholds.py:88-104`: `alert_threshold = argmax(F2)`, `high_threshold =
argmax(F0.5)` (clipped up if it would fall below the alert threshold), computed only on
rows where `population == official_architecture` and `split == "validation"`. Fold 1 is
excluded automatically (it never carries the official architecture's calibrated
probabilities, being the fold-1 no-op passthrough) and holdout is excluded by
construction — the threshold is chosen entirely on validation, never touching holdout.

---

### M2-18. Why can a model's ranking (PR-AUC) improve while its calibration (BSS) gets worse at the same time?

**Shape:** Mechanism (why)

Because they measure different properties of the same scores. PR-AUC only cares about the
relative *ordering* of predicted probabilities against true labels; BSS penalizes the
absolute probability *scale* against observed frequency. A per-fold-retrained
`scale_pos_weight`-based imbalance correction (used in Stage 1's XGBoost/RF training) can
systematically distort the probability scale — hurting BSS — while still preserving or
even improving the relative rank order of scores — helping PR-AUC. This is exactly what
happens in M2-007D (see M2-8) and is independently confirmed by the M2-008 symmetric
ablation, which found stacked probability correction fails even when climate is routed
identically to how Module 1 handles it — the bottleneck is the scale-distortion mechanism
itself, not a missing feature.

---

### M2-19. Why did Random Forest edge out XGBoost by only 0.004 PR-AUC after the label changed — do you actually know why, mechanistically?

**Shape:** Deliberate-vs-incidental (honest limitation)

No mechanistic explanation is documented, and none should be invented. This is a close
empirical result from an automated model-selection procedure
(`select_official_model()`, `baseline_classifier.py:565-578`) re-run under the new label
— not evidence that Random Forest's impurity-based splitting is structurally better suited
to a harmonic-threshold label than XGBoost's gradient boosting. The honest answer to "why
RF" is: it won a close automated comparison once the label changed, and the team has not
investigated further why, rather than manufacturing a post hoc architectural justification.
