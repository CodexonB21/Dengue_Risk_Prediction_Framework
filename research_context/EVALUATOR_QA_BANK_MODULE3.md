---
name: evaluator-qa-bank-module3
description: Mechanism/is-it-good/contradiction/deliberate-vs-incidental Q&A bank for Module 3 (Hybrid Spatial Hotspot Detection), companion to QUESTIONS_FOR_DEFENSE.md
metadata:
  type: report_support
---

# Evaluator Q&A Bank — Module 3 (Hybrid Spatial Hotspot Detection)

Companion to `research_context/QUESTIONS_FOR_DEFENSE.md`, which has only one Module 3
entry (the null-result-to-relative-residual arc). This file is the module's thinnest of
the three going in — most of these entries are genuinely new ground, not duplicates.

Answers are terse defense ammunition — cite exact file/line or Decision/M3-0xx number.

---

### M3-1. What exactly computes feature importance in your Random Forest, and does it match Module 1 or Module 2?

**Shape:** Mechanism

`compensation_model.py:386`: `pd.DataFrame({"feature": STAGE2_FEATURE_COLUMNS_V2,
"importance": final_model.feature_importances_})` — sklearn's default
`RandomForestRegressor.feature_importances_`, i.e. **mean decrease in impurity (Gini/
variance-reduction)** computed from training data, not held-out permutation importance
(no call to `sklearn.inspection.permutation_importance` exists anywhere in `src/`,
confirmed by a full-tree grep). This matches Module 2's **current** Random Forest
importance mechanism exactly (`baseline_classifier.py:682`, same MDI statistic) but
differs from Module 1's XGBoost gain-based importance
(`compensation_model.py:827`, `get_score(importance_type="gain")`). The M2/M3
convergence is incidental — both independently picked a scikit-learn Random Forest and
used its default attribute; no decision anywhere in the repo coordinates or even
discusses standardizing this statistic across modules.

---

### M3-2. Walk me through exactly how your KDE baseline and Moran's I are computed.

**Shape:** Mechanism

Weighted Gaussian KDE with Silverman bandwidth:
`gaussian_kde(coords.T, bw_method="silverman")` (`kde_baseline.py:145-151`); the fitted
`.covariance` is reused to build a fixed 25×25 kernel matrix
(`multivariate_normal(mean=coords[i], cov=covariance).pdf(coords)`, lines 154-162), and
`KDE_baseline` is one matrix multiply per week: `pivot.to_numpy() @ kernel` (line 194).
Global Moran's I: `Queen.from_dataframe(...)` (queen contiguity,
`libpysal.weights.Queen`), row-standardized weights, `Moran(mean_kde, w,
permutations=999)` (`esda.moran.Moran`) — computed on the **per-district mean of
`KDE_baseline` across all weeks**, not the raw per-week surface. `np.random.seed(13)` is
set once (`run_kde_baseline()` line 288) because `esda.Moran`'s permutation test draws
from NumPy's global RNG with no `seed` kwarg of its own — an unseeded rerun gave p_sim
0.2850 then 0.2860 for the NE-monsoon week (see M3-6); the seeded, authoritative value is
0.279.

---

### M3-3. Your headline is "~51% MAE reduction" — does a zero-modeling baseline get most of that for free?

**Shape:** Is-that-actually-good

Yes, at the time that headline was current. `persistence_baseline.py`'s "carry last
week's own absolute residual forward" baseline — zero modeling — recovers ~93% of the
51% MAE reduction on its own, and actually **beats** the official Stage 2 RF on MAE
(9.4386 vs. 9.9621, M3-010) and on two independent rank metrics (Spearman 0.849 vs.
0.813; precision@5 0.784 vs. 0.759, M3-012). The RF's real, defensible edge in that
generation of the model was RMSE and outlier/clipping control, not typical-case MAE — a
narrower claim than "51% reduction" implies on its own. Note this specific "~51%" and
"9.9621" pair describes the **pre-M3-015** absolute-residual RF, superseded by the
relative-residual model (M3-15) — don't quote it as the current model's number.

---

### M3-4. You borrowed Module 2's calibration trick and it failed — why, mechanically?

**Shape:** Contradiction-check

`isotonic_calibration.py:122`: `IsotonicRegression(out_of_bounds="clip",
increasing=True)`, fit per spatial fold on the other 4 folds
(`out_of_fold_isotonic_calibrate`, lines 108-130). `out_of_bounds="clip"` is the exact
failure mechanism: fold 0 (Colombo/Gampaha/Kandy/Kegalle/Kurunegala/Puttalam) has a peak
case count of 2,631 — more than double any other fold's peak (889-1,430) — so its
calibration curve, fit only on the other 4 folds, has never seen anything close to that
range and clips fold 0's real values down to whatever the training folds' max output was.
Root-caused via a per-fold RMSE breakdown: 37.4 → 65.9 (+76%), concentrated entirely in
fold 0; folds 1-4 unaffected (M3-014). This is specific to Module 3's **geographically
clustered** CV, contrasted explicitly against Module 2's random folds
(`isotonic_calibration.py`'s own docstring), where every fold shares a similar
distribution — the calibration idea itself isn't broken, the fold structure that fed it
here is.

---

### M3-5. Your relative-residual fix improved RMSE — is that win real, or is one fold doing all the work?

**Shape:** Is-that-actually-good

Real but fold-concentrated. The aggregate RMSE win over the prior official RF (24.01 vs.
25.11) is driven almost entirely by fold 0 (Colombo/Gampaha, 32.3 vs. 37.5) — in 3 of the
other 4 folds, the **prior** (pre-M3-015) official RF actually had better RMSE than the
new relative-residual model (M3-015 Results, caveat 1). Report both: the aggregate win is
genuine and bootstrap-confirmed on MAE/Spearman/precision@5, but RMSE specifically is not
a uniform win across folds.

---

### M3-6. There's one week where your own Stage 1 says there's no significant spatial clustering — how does Stage 2 do there?

**Shape:** Contradiction-check

Notably worse. The NE-monsoon representative week (2021 Wk1) is Stage 1's own
non-significant case: Moran's I = 0.031, p_sim = 0.279 (M3-001) — the one week where the
whole spatial-clustering premise doesn't hold. Stage 2's relative-residual model performs
markedly worse there too — Spearman 0.36 vs. persistence's 0.74 and the official RF's
0.76 (M3-015) — the same week is the weak point for both stages, not independently
diagnosed twice by coincidence.

---

### M3-7. If I rerun your persistence-baseline script right now, do I get the same table as your M3-010 results?

**Shape:** Mechanism / is-that-actually-good

No. Unlike `alpha_sweep.py`, `stage2_experiments.py`, and
`stacked_persistence_experiment.py` — which `MODULE_CONTEXT.md`/`EXPERIMENT_LOG.md`
explicitly document as frozen for reproducibility — `persistence_baseline.py` and
`hotspot_ranking_evaluation.py` read the "official RF" column dynamically from whatever
`Risk` column is currently in `hybrid_risk_map.csv` on disk (`build_model_predictions()`,
`hotspot_ranking_evaluation.py:61-79`), while "Naive persistence" is always computed from
the absolute-scale `residual_rescaled_lag_1` regardless. Rerunning today would report the
current (M3-015, relative-residual) model's numbers under the identical "Stage 2 RF,
official" label the M3-010 table used for the older absolute-residual model — not a bug,
but a real reproducibility trap this project's docs don't call out anywhere for these two
specific scripts.

---

### M3-8. Why Random Forest over GWR for Stage 2?

**Shape:** Deliberate-vs-incidental (thin evidence, flagged honestly)

A stated a priori rationale, not a benchmarked comparison: `MODULE_CONTEXT.md:989` —
"considered, not used. With only 25 spatial units, local weighting is statistically
unreliable; Random Forest was chosen instead for robustness with limited-N tabular data."
With N=25 districts, a geographically-weighted local regression needs enough nearby
spatial neighbors per district to fit a stable local model, which is plausible but was
never actually tested. This is genuinely thinner evidence than most of Module 3's other
decisions — say so directly if pressed, rather than presenting it as equally
benchmark-backed as e.g. the relative-residual reformulation (M3-15).

---

### M3-9. Your M3-012 table says Spearman 0.813 for "the official RF" — is that still the current model?

**Shape:** Contradiction-check

No — a stale point-in-time snapshot. M3-012's embedded Spearman/precision@5 figures
(0.813 / 0.759) describe the pre-M3-015 absolute-residual RF. `MODULE_CONTEXT.md` never
flags, in that same section, that "official RF" now refers to the M3-015 relative-residual
model, whose own Spearman is 0.889 per M3-015's own results table. Cite the M3-015 number
(0.889) as current; only cite 0.813 explicitly as "the earlier absolute-residual model's
figure" if the historical comparison itself is the point.

---

### M3-10. Where does the "~81% combined importance" figure for your current features actually come from — verified?

**Shape:** Is-that-actually-good (now verified)

Checked directly against the committed CSV (`outputs/metrics/module3/rf_feature_importance.csv`):
`relative_residual_lag_1` = 0.6724, `lag_2` = 0.1353, `lag_3` = 0.0302, `lag_4` = 0.0219 —
summing to **86.0%** for the relative lags alone, not ~81% as `MODULE_CONTEXT.md`'s prose
states. Including the four legacy absolute `residual_rescaled_lag_*` columns
(still present in `STAGE2_FEATURE_COLUMNS_V2`, ~5.0% combined) brings the total
own-district-residual-lag share to **~91%**. Use the verified 86.0%/91% figures, not the
prose "~81%" — this closes a gap flagged as unverifiable in an earlier research pass.

---

### M3-11. Two different things in your docs are both called "naive persistence" — same baseline?

**Shape:** Contradiction-check

No — different target scales, different scripts, different dates.
`persistence_baseline.py`'s baseline (MAE 9.4386, M3-010) is the **absolute**-residual
naive predictor: `predicted_residual_persistence = residual_rescaled_lag_1`.
`relative_residual_compensation.py`'s "relative persistence" (MAE 8.17, M3-015) is the
**relative**-residual analogue: `relative_residual_lag_1` (own-district, one week back).
Citing "the naive baseline" without specifying which one risks sounding inconsistent when
it's actually two intentionally distinct comparisons built at different stages of the
investigation.

---

### M3-12. Why do own-district relative-residual lags now dominate Stage 2 importance?

**Shape:** Mechanism (why)

Because they fix a directly-diagnosed problem with the *previous* target scale, not
because lag features are inherently powerful. A diagnostic of Stage 1's raw absolute
error found it strongly heteroscedastic — `corr(Risk_0, |Number_of_Cases - Risk_0|) =
0.7795`, `corr(log(Risk_0), log(|residual|+1)) = 0.8106`
(`relative_residual_compensation.py:5-6`) — meaning error magnitude scales with predicted
magnitude, so every prior absolute-residual model let the handful of huge outbreak weeks
dominate the learning signal. Dividing by `(Risk_0 + 1)` (the same "+1" guard used
elsewhere in the pipeline) normalizes for this, and own-district lags of that
*normalized* quantity give the RF a magnitude-consistent dynamic anchor that transfers
across districts of wildly different case volumes — verified as genuine epidemic
persistence, not a computational artifact, since `kde_baseline_rescaled[t]` only ever uses
week t's own case counts, never t-1's (`compensation_model.py:106-109`). See M3-10 for the
verified current combined-importance figure (86.0%/91%, not the prose "~81%").

---

### M3-13. How exactly did you test for heteroscedasticity before deciding to switch to a relative-residual target?

**Shape:** How (procedure)

A direct correlation diagnostic, not an assumption: `corr(Risk_0, |Number_of_Cases -
Risk_0|) = 0.7795` and, checking whether a log transform changes the conclusion,
`corr(log(Risk_0), log(|Number_of_Cases - Risk_0| + 1)) = 0.8106`
(`relative_residual_compensation.py:5-6`, run as a scratchpad check with "results
committed here for reproducibility"). The scope is the full pooled dataset (all
districts, all weeks) — a global diagnostic run once, before any cross-validation
comparison, to establish whether the target itself had a structural problem worth fixing,
rather than trying another feature set on the same (flawed) target scale.

---

### M3-14. How exactly is your spatial ranking metric (precision@k) computed?

**Shape:** How (procedure)

`_precision_at_k(actual, predicted, k)` (`hotspot_ranking_evaluation.py:86-89`): for each
week, take the set of districts in the actual top-k by case count
(`actual.nlargest(k).index`) and the set of districts in the predicted top-k by risk score
(`predicted.nlargest(k).index`); precision@k = size of their intersection divided by k.
Computed per week for each model column, then aggregated (`compute_weekly_rank_metrics()`,
lines 92-111) — weeks with zero case-count variance are skipped entirely (Spearman is
undefined there, same precedent as `kde_baseline.select_representative_weeks()`'s own
exclusion rule), not silently included as a degenerate 0 or 1.

---

### M3-15. Why is the iterative correction loop capped at exactly 1 iteration?

**Shape:** Mechanism (why)

Not a time/compute budget cap — a diagnosed necessity.
`iterative_loop.py:278-287`/M3-008: iterations 2-4 were tested and shown to **oscillate**
(`max_delta`: 578 → 240 → 167 → 190, non-converging), because once fixed,
relative-to-`Risk_0` lag features were introduced, further iteration became theoretically
incoherent (each iteration would be recomputing a "relative" quantity against a baseline
that itself just moved). Capping at 1 iteration is a documented response to that
oscillation, not an arbitrary stopping point chosen upfront.

---

### M3-16. How does the shrinkage-alpha blending formula actually work, and why did alpha change from 0.05 to 1.0?

**Shape:** How (procedure) + Deliberate

`iterative_loop.py:236`: `risk_t = risk_prev + alpha * predicted_relative_residual *
(risk_prev + 1)` — reconstructs the absolute risk exactly (not approximately) from the
relative-residual prediction. Alpha was forced down to 0.05 (M3-004, tested {1.0, 0.3,
0.15, 0.05} explicitly) because at higher values, static per-district features caused the
correction to diverge under out-of-fold CV — 0.05 was the only value that numerically
converged within budget at the time. It was raised back to 1.0 only after own-district
residual lags (M3-008/Decision 050) gave the RF "a genuine dynamic anchor," which resolved
the root cause of the original divergence — both alpha values are evidence-driven
decisions tied to a specific diagnosed problem, not defaults that drifted.

---

### M3-17. Does Module 3's hybrid approach actually beat a simple, no-model baseline? (pointer)

**Shape:** Is-that-actually-good

Already covered in depth in `QUESTIONS_FOR_DEFENSE.md`'s existing Module 3 entry — the
full null-result-to-relative-residual arc (M3-010 through M3-015), including the two
honest caveats (RMSE win concentrated in one fold; worse at the NE-monsoon week). This
file's entries above (M3-3, M3-5, M3-6, M3-9, M3-10, M3-12) supply additional
mechanism-level and verification detail that complements, not duplicates, that existing
answer.

---

### M3-18. Two things you fixed in your own decision log — did the fix always get applied everywhere it should have?

**Shape:** Deliberate-vs-incidental (meta, self-correction discipline)

Mostly, with one loose end. Decision 050 explicitly corrects an earlier erroneous
"Decision 032" citation, and Decision 052/M3-016 explicitly corrects an earlier erroneous
"Decision 031" citation (both had pointed to unrelated Module 1 entries) — both
corrections are reflected in `MODULE_CONTEXT.md` and `RESEARCH_DECISIONS.md`. But
`module_3_spatial/EXPERIMENT_LOG.md:1169` (M3-008's own "Documentation Updated" list)
still reads the stale "Decision 032" — that specific instance was never fixed. A good,
honest example of the project's self-correction discipline to cite, with the caveat that
one instance of it is itself still incomplete — worth fixing before citing this as
evidence of thoroughness.
