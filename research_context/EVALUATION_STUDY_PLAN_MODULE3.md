# Evaluation Study Plan — Module 3 (Hybrid Spatial Hotspot Detection)

## Purpose of This File

Same purpose and format as `EVALUATION_STUDY_PLAN_MODULE1.md` / `_MODULE2.md` — a viva-
preparation curriculum built entirely from what is actually implemented and decided in this
repository, not from generic KDE/spatial-statistics textbook knowledge.

**Read this warning before anything else, same as Module 2's Session 0.** Module 3's headline
result **flipped from a null/negative finding to a genuine, bootstrap-confirmed positive one**,
and it did so in five distinct steps. If you learn only the final answer without the arc, you
will not survive a follow-up question, because the older (superseded) claim — "Stage 2 improves
case-fit by ~51%" — is still sitting in some already-drafted report/slide language and is **not**
the same claim as the current, correct one. Session 0 exists to make sure you always state the
*current* claim precisely.

Source files: `module_3_spatial/MODULE_CONTEXT.md` (957 lines — this is Module 3's primary
record; unlike Modules 1/2, most Module 3 decisions live here rather than in
`RESEARCH_DECISIONS.md`), `module_3_spatial/EXPERIMENT_LOG.md` (M3-001 through M3-015),
`RESEARCH_DECISIONS.md` Decisions 050–051, `QUESTIONS_FOR_DEFENSE.md`,
`PRESENTATION_MODULE3_SLIDES.md` / `PRESENTATION_MODULE3_COPY_PASTE.md` (both current, updated
2026-08-08 after M3-015 — there is no separate v1/v2 split here the way Module 2 has).

**Owner of this module:** Karunarathna R.M.D.R.R. (214099D). Same team-readiness expectation as
Modules 1 and 2 — any member may be asked about any module.

---

## Session 0 — The Result Arc: Null → Beats Nobody → Beats Everybody (learn this before anything else)

Five stages, in order — **memorize this table**, it is the single most important thing in this
module and the one most likely to trip you up if skipped:

| Stage | What was tried | Headline finding |
|---|---|---|
| **M3-005** (original) | 16 climate/demographic covariates, Stage 2 target = absolute residual | **Null**: Stage 2 slightly *worsens* aggregate fit vs. Stage 1 alone (MAE 20.19→20.54) |
| **M3-008** (Decision 050) | Added own-district lags of the *absolute* residual (1–4 weeks) | **Looks like a big win**: MAE 20.54→9.96 (~51% reduction) vs. Stage 1 — **but this number alone is misleading, see next row** |
| **M3-010/M3-011** | Checked M3-008 against a trivial "just carry last week's own residual forward, no model at all" baseline | **The 51% figure was mostly free**: naive persistence alone reaches MAE 9.44 — **actually beats the RF** (9.96). Stacking a "correction beyond persistence" was also tried and was worse than both. |
| **M3-012–M3-014** | Re-evaluated with hotspot-ranking metrics (M3-012, persistence still wins); tried blending RF+persistence (M3-013, a real improvement over the RF alone but only a statistical tie with persistence, and a real loss on rank correlation); tried isotonic calibration adapted from Module 2 (M3-014, failed cleanly, root-caused) | **Three more honest rejections**, each for a specific, understood reason |
| **M3-015 (Decision 051, current production)** | Diagnosed the absolute residual as strongly heteroscedastic (large outbreak weeks dominate the loss); switched the target to a **relative** residual, `(actual − Risk_0)/(Risk_0+1)`, exactly reconstructed back to an absolute Risk | **Genuine win, bootstrap-confirmed**: beats **both** Stage 1 alone *and* naive persistence, on every reported metric |

**Current production claim — this is what you say, always, going forward:**
> "Stage 2's final formulation beats both the spatial baseline alone and a naive no-model
> persistence baseline, on correlation, MAE, RMSE, and rank-based hotspot metrics — confirmed by
> a week-level bootstrap, not just a raw aggregate table. Getting here took four rejected
> mechanisms first, each tested honestly and understood, not guessed past."

**Must be able to say, if asked "so does the model actually work or not — I'm seeing
conflicting numbers in the drafts":**
> "The 51% figure you may see elsewhere in early drafts was real but incomplete — it only
> compared against the untouched spatial baseline, not against the much stronger 'do nothing,
> just repeat last week's error' comparison, which we later ran ourselves and which the model
> actually lost to at that point. We then diagnosed *why* — the residual we were modeling was
> heteroscedastic, so a few huge outbreak weeks dominated training — fixed the target
> definition, not the feature set, and the corrected model now beats both comparisons. The
> current, correct number is what's in Chapter 7.5 and the current slide deck; anything citing
% the old 51%-vs-Stage-1-only framing is superseded."

---

## Session 1 — Orientation: What Module 3 Actually Answers, and Why Its Validation Looks Different

**Read:** `MODULE_CONTEXT.md` "Purpose", "Current Architecture", Open Questions #4/#5

Module 3 answers **"where is dengue burden spatially concentrated, and does that concentration
shift once demographic/environmental context is accounted for?"** — a fundamentally different
question from Module 1 (how many) or Module 2 (is this abnormal). Two structural differences
from Modules 1/2 that you must be able to explain immediately, because they look like omissions
if you don't:

1. **No temporal train/test holdout.** Modules 1/2 reserve the final weeks in time. Module 3's
   question is spatial, not temporal — its validation axis is **5-fold spatial K-means CV**:
   districts are clustered by GADM centroid location and held out as whole units, never split
   across folds. Every row of the final output already comes from a model that never saw that
   district during training, for every week — there is no separate "held-out test week" the way
   Modules 1/2 have, because the thing being validated (spatial generalization) is orthogonal to
   time.
2. **Geographically Weighted Regression (GWR) was considered and explicitly rejected** before
   Random Forest was chosen. With only 25 spatial units, GWR's local weighting is statistically
   unreliable — not enough neighbors per local fit. Random Forest was chosen specifically for
   robustness with limited-N tabular data. This is a real "alternative considered" data point,
   not a default choice.

**Must be able to say:**
> "Module 3 doesn't use a temporal holdout because its research question is spatial
> generalization, not future-time prediction — validating with 5-fold spatial K-means CV, where
> entire districts are held out, is the methodologically correct analogue for that question. We
> also explicitly considered and rejected Geographically Weighted Regression before choosing
> Random Forest, because 25 spatial units is too few for GWR's local weighting to be reliable."

**Self-check:**
- Q: If there's no temporal holdout, how do we know the spatial risk map isn't overfit to any
  specific week?
- A: Every row of `hybrid_risk_map.csv` comes from a spatial-CV fold that never saw that
  district during training, *regardless of which week is picked* — the out-of-fold property
  holds uniformly across the whole dataset, not just for one reserved slice. This was verified
  directly, not assumed, when the question was raised (see the Visualization section of
  `MODULE_CONTEXT.md`).

---

## Session 2 — Data and the Spatial Layer

**Read:** `MODULE_CONTEXT.md` "Data Pipeline Note"

Module 3 reads the same shared case/climate/population tables as Modules 1/2, plus a spatial
layer unique to it:

| Layer | Detail |
|---|---|
| District boundaries | **GADM v4.1 Level-1** (25 districts) — Level-2 (323 DS-division units) exists but is **not used**; know this distinction if asked about spatial grain |
| Elevation | Static per district, extracted from the raw Open-Meteo CSV headers (not a separate dataset) |
| Population density | **Derived**, not a raw column — `Estimated_Population / district land area`, computed from the same reprojected GADM polygons used for centroids. Sanity-checked against real demographics: Colombo highest (3,356/km²), Mullaitivu lowest (41/km²) |

Module 3 does **not** need Module 1's week-53 merge or `weather_code` exclusion policy — those
remain Module-1-scoped (Decision 013); Module 3 aggregates weather to the same weekly epi-week
grid but inherits it read-only from the shared layer.

**Must be able to say:**
> "Module 3 works at district level using GADM Level-1 boundaries — 25 units, matching Modules
> 1 and 2's district scope exactly, so all three modules' outputs key on the same geography.
> Finer sub-district analysis was considered out of scope and flagged as future work, not
> attempted and abandoned."

---

## Session 3 — Stage 1: KDE Baseline and Moran's I Validation

**Read:** `MODULE_CONTEXT.md` "Stage 1 — Baseline", "KDE_baseline: Two Valid Uses, Not a
Contradiction"

- **Method**: case-count-weighted Gaussian KDE over district centroids, Silverman bandwidth
  (a standard rule-of-thumb, chosen for the same "too few spatial units for anything fancier"
  reason as the GWR rejection), computed as one fixed 25×25 kernel matrix (a property of the
  geography, not refit per week).
- **Validation**: **Global Moran's I = 0.70, p = 0.001** — genuine, statistically significant
  spatial clustering, computed on the aggregated (mean) KDE surface across all weeks.
- **A representative-week check, not just the aggregate**: Moran's I was recomputed for a peak
  week, a low week, and a monsoon-representative week specifically to check the aggregated
  result wasn't an artifact of averaging ~1,000 weeks together:

  | Week | I | Significant |
  |---|---|---|
  | 2017 Wk29 (peak, also SW monsoon — Sri Lanka's worst recorded dengue year) | 0.728 | Yes |
  | 2007 Wk13 (low case week) | 0.735 | Yes |
  | 2021 Wk1 (NE monsoon representative) | 0.031 | **No** |

  **This nuance must always accompany the I=0.70 headline, not be dropped**: clustering is
  strong in most conditions but not universal — the NE-monsoon week shows no significant spatial
  structure at all. This same week later turns out to be Stage 2's weakest week too (Session 6)
  — a coherent, not coincidental, pattern.

**The single trickiest technical concept in Module 3 — the two uses of `KDE_baseline`:**
> "Raw `KDE_baseline` is a properly-normalized density surface — it integrates to 1 over space,
> so its absolute magnitude is tiny (max ~4.5e-7). That's fine for Moran's I, which is
> scale-invariant and only cares about the *relative* clustering pattern. But a residual
> `actual − KDE_baseline` only means something if both sides are on a comparable scale — raw
> `KDE_baseline` made the 'residual' numerically indistinguishable from the raw case count
> itself (correlation over twelve nines). We fixed this by mass-conserving `KDE_baseline` per
> week — rescaling it so it sums to that week's real total case count across districts — which
> keeps the KDE surface's spatial redistribution *shape* while making its magnitude meaningful
% as a subtractable baseline. This dropped the spurious correlation from 0.9999999 to a genuine
> 0.678."

**Self-check:**
- Q: Doesn't rescaling the KDE baseline change what Moran's I validated?
- A: No — Moran's I was computed on the raw, properly-normalized surface, which is the correct
  form for a scale-invariant clustering test. The rescaled form is a *separate, later* use for
  Stage 2's subtraction step; both are the same underlying spatial shape used for two genuinely
  different, individually-correct purposes, not an inconsistency.

---

## Session 4 — Stage 2, the Iterative Loop, and Why It Only Runs Once

**Read:** `MODULE_CONTEXT.md` "Stage 2 — Residual Compensation" (top), "Stage 2 Implementation
Status", "Stage 2 Promotion: Own-District Residual Lags"

**Current production target and update rule (post-M3-015):**

```text
relative_residual = (Actual_case_intensity − Current_Risk) / (Current_Risk + 1)
Risk_t = Risk_(t-1) + alpha * predicted_relative_residual_t * (Risk_(t-1) + 1)
```

with `alpha = 1.0` (no shrinkage) and the loop **capped at 1 iteration by design**, not run to
convergence. Both of these facts have a tested, not assumed, justification:

- **Why alpha went 0.05 → 1.0**: the *literal* spec formula (no damping) genuinely diverges
  under honest out-of-fold evaluation — `max_delta` grew every iteration and `Risk` went
  physically negative (down to −1,414). Root cause: several original features
  (`population_density`, `Estimated_Population`, `elevation_m`) are static per-district, so a
  held-out district's prediction is genuine extrapolation error, and feeding that error back at
  full magnitude compounds iteration over iteration — the same instability gradient boosting
  avoids with a learning rate. `alpha=0.05` was the smallest value tested that converged cleanly
  (verified across `{1.0, 0.3, 0.15, 0.05}`). Once own-district residual lags were added
  (M3-008), the model had a genuine dynamic anchor even for a held-out district, which resolved
  the extrapolation instability directly — `alpha=1.0` became the best-performing choice again,
  not a reversion for its own sake.
- **Why the loop caps at 1 iteration, not 4**: the residual lag features are computed *once*,
  fixed relative to `Risk_0` (a historical fact). Retraining on iteration *t*'s evolving target
  while those features still describe "relative to `Risk_0`" is theoretically incoherent past
  iteration 1 — and this was verified empirically, not just reasoned about: forcing iterations
  2–4 anyway produced an **oscillating, non-converging** `max_delta` (578→240→167→190) that
  degraded an already-good iteration-1 result.
- **The dual convergence check (numeric `max_delta` + Moran's I of the residual) is still
  computed every run for diagnostic value**, even though it no longer gates further iterations.
  A genuinely important finding here: the spatial-clustering half of the check is satisfied
  **trivially, from iteration 1, by Stage 1's KDE baseline alone** — verified by computing
  Moran's I on `Number_of_Cases − Risk_0` directly (zero RF involvement): I=−0.166, p=0.133,
  essentially identical to the post-RF result. **The RF's real job is therefore district-level
  burden correction, not further spatial de-clustering** — Stage 1 already did that job. This
  was checked directly after an earlier, looser causal claim was proposed and found to need
  correcting (a self-correction, disclosed as such).

**Must be able to say:**
> "The iterative loop's design — full-magnitude updates, capped at one pass — looks unusual next
> to a naive 'just keep looping until it converges' idea, but both choices were forced by
> evidence, not picked for simplicity: the literal spec diverges without damping, and the
> residual-lag features that later made full-magnitude updates safe are, by construction,
> incoherent to retrain against a target that's already moved past the point those features
> describe."

**Self-check:**
- Q: If Moran's I is always trivially satisfied from iteration 1, why keep computing it at all?
- A: It's genuine diagnostic evidence that Stage 1's baseline is doing its job (capturing the
  spatial-clustering structure), and the framework itself is described as general — a noisier
  dataset or a coarser spatial baseline that left real residual clustering behind would engage
  this criterion and justifiably drive further iterations. Removing the check would remove the
  evidence that this dataset doesn't need to.

---

## Session 5 — Feature Engineering

**Read:** `MODULE_CONTEXT.md` "Stage 2 Implementation Status" (feature list), "Stage 2 Promotion"

| Feature group | Members | Note |
|---|---|---|
| Current-week climate | `rain_sum (mm)`, `temperature_2m_mean (°C)` | One canonical column each — `precipitation_sum` was excluded as a rainfall candidate because it's identical to `rain_sum` for Sri Lanka (no snow, so Open-Meteo's two totals never diverge here) |
| Lagged climate | rainfall/temperature lag 2/3/4 weeks | Shorter lag depth than Modules 1/2 (which go to lag 8/4) |
| Climate anomaly | vs. historical mean for that (District, Week) across **all years** (not a strictly-prior-years expanding window) | **Deliberately different leakage treatment from Modules 1/2** — defensible here specifically because Module 3's validation axis is spatial K-means CV, not temporal walk-forward, so a full-sample per-week mean does not leak across a *spatial* fold the way it would across a *temporal* one |
| Static covariates | elevation, population, **derived** population density | See Session 2 |
| Mahalanobis anomaly score | multivariate anomaly across rainfall/temperature/elevation/population, computed against the full dataset's mean/covariance | Captures "how unusual is this district-week's whole combination of conditions," accounting for correlation between the four variables |
| **Own-district relative-residual lags 1–4 (current dominant features, ~81% combined importance)** | `relative_residual_lag_1..4` | Supersedes the M3-008 absolute-residual lags (still present as secondary features, ~5% combined importance) — this is what actually made `alpha=1.0` safe (Session 4) |
| Seasonal | Monsoon SW/NE dummy | Simpler than Modules 1/2's cyclic `sin_week`/`cos_week` |

**A leakage-adjacent design choice worth knowing**: lag features use `.shift()` on each
district's own time-ordered rows, not calendar-week arithmetic — because of the ~2 known
genuinely-absent `(District, Year, Week)` cells, a shifted value could rarely be the previous
*available* week rather than strictly N calendar weeks prior. Module 3 does not impute (no such
decision was made, unlike Modules 1/2's `is_imputed` policy) — this is an accepted, documented
limitation, not an oversight.

**A companion diagnostic worth citing if asked about spatial spillover**: does a neighboring
district's own recent error carry extra information? Checked directly — a Queen-contiguous
neighbor's lagged residual correlates −0.30 with a district's own current residual, but that
drops to a negligible 0.03 **partial** correlation once the district's own lag_1 is already
accounted for. **Neighboring districts' errors carry no information a district's own recent
history doesn't already provide** — a clean, checked null result that justified *not* adding
neighbor-lag features, rather than leaving the idea untested.

**Self-check:**
- Q: Why is the climate-anomaly leakage treatment different here than in Module 1/2?
- A: Leakage is defined relative to the validation axis. Modules 1/2 split by *time*, so a
  future-looking global average would leak future information into an earlier fold. Module 3
  splits by *space* — a full-sample, all-years per-week average doesn't reveal anything about
  which *district* is held out, so it's safe under spatial CV specifically. Applying the same
  rule blindly across modules without this reasoning would be the actual mistake.

---

## Session 6 — Current Results and How to Present the Arc Honestly

**Read:** `MODULE_CONTEXT.md` "Stage 2: Four Follow-Up Compensation Mechanisms Tested",
`RESEARCH_DECISIONS.md` Decision 051, `PRESENTATION_MODULE3_SLIDES.md`

**Current, correct headline table (Decision 051 / M3-015 — cite this, not the M3-008 figures):**

| Model | corr | MAE | RMSE |
|---|---|---|---|
| Stage 1 alone (`Risk_0`) | 0.8241 | 20.54 | 48.20 |
| Naive persistence (no model at all) | 0.9493 | 9.44 | 26.63 |
| **Stage 2 final (relative residual, current production)** | **0.9592** | **8.03** | **24.02** |

Confirmed via a **week-level paired bootstrap** (2,000 resamples) — not just this raw aggregate
table, which the project's own experience (M3-013) already showed can look like a clean win and
not survive closer scrutiny. This time it does survive: the improvement holds across 4 of 5
spatial folds and is accompanied by a hotspot-ranking companion metric (Spearman rank
correlation, precision@k) that also favors the current model, not just the fit metrics.

**Two honest caveats, ready but not volunteered on a slide:**
- The RMSE win is present in *every* spatial fold but is proportionally larger in the
  highest-case-volume fold (Colombo/Gampaha's cluster) than in the other four.
- The model performs **notably worse at the NE-monsoon representative week** (2021 Wk1) —
  exactly the same week already flagged in Stage 1's own Moran's I check as the one week lacking
  significant spatial clustering (Session 3). This is a coherent, not coincidental,
  cross-checked limitation: a week without real spatial structure is also the week Module 3's
  spatially-informed correction struggles most on.

**Do not quote exact Spearman/precision@k values for M3-015 from memory** — verify them against
`outputs/metrics/module3/hotspot_ranking_evaluation.csv` before citing a specific number in a
viva; this plan deliberately does not fabricate one.

**Must be able to say (the "so what"):**
> "Stage 2's final formulation is a genuine improvement, not just over the untouched spatial
> baseline but over the much harder bar of 'a model that does nothing clever, just repeats last
> week's own error' — and we know this because we built that comparison ourselves and reported
> it even when our first two attempts lost to it. The fix that finally worked came from
> diagnosing *why* the residual was hard to learn — it was heteroscedastic, so a handful of huge
> outbreak weeks dominated training — not from trying another feature set on the same target."

**Self-check:**
- Q: What does Stage 2 actually contribute, mechanistically, if a naive persistence baseline
  gets so close?
- A: The RF's genuine, checked value is controlling the *severity* of large errors/overshoots
  (better RMSE, fewer physically-nonsensical negative-Risk rows than naive persistence: 4.8% vs.
  9.1% clipped) using climate/demographic/monsoon context persistence can't see, on top of now
  also winning outright on typical-case accuracy (MAE) once the relative-residual reformulation
  fixed the heteroscedasticity problem. This nuance — "persistence gets you most of the way,
  Stage 2 gets you the rest and dampens the worst cases" — is a more honest and more defensible
  framing than "the RF alone explains the result."

---

## Session 7 — The Rigor Story: What Was Tried and Rejected Along the Way

**Read:** `EXPERIMENT_LOG.md` M3-005, M3-010 through M3-014

| Tried | Result |
|---|---|
| Original 16 climate/demographic covariates only (M3-005) | Null — Stage 2 marginally *worsens* aggregate fit vs. Stage 1 |
| Stacked "predict only the correction beyond persistence" (M3-011) | Worse than **both** naive persistence and the official RF on every metric — RFs are non-linear, so pre-subtracting a dominant feature isn't equivalent to including it as a plain input, and the idea still failed when tested directly |
| Output-level blend of RF + persistence (M3-013) | A real, bootstrap-confirmed improvement over the RF **alone**, but only a statistical **tie** with persistence on MAE/precision@5 and a real, significant **loss** on Spearman rank correlation — not adopted |
| Isotonic calibration adapted from Module 2's own Stage 2 (M3-014) | **Failed cleanly, root-caused, not left unexplained**: degradation concentrated almost entirely in the Colombo/Gampaha fold — the calibration curve, fit on the other four lower-magnitude folds, has no data to extrapolate from and clips the real range, badly underpredicting exactly the biggest outbreak weeks. A structural mismatch between calibration's implicit same-range assumption and Module 3's *geographically-clustered* CV folds, unlike Module 2's random folds where every fold shares a similar distribution |

**Must be able to say — this is Module 3's strongest single sentence, borrow its structure for
any "did you just get lucky" question:**
> "We didn't stop at the first null result, and we didn't stop at the second rejection either.
> We tried four mechanically different compensation ideas — including one borrowed directly from
> Module 2 — rejected two of them with a specific, root-caused reason each, and only found the
> genuine improvement by diagnosing *why* the residual was hard to learn in the first place,
> rather than trying yet another feature set on the same, wrong target scale."

**Self-check:**
- Q: Why did the isotonic calibration idea work for Module 2 but fail for Module 3?
- A: Module 2's validation folds are random splits of *time*, so every fold shares a similar
  score distribution for calibration to learn from. Module 3's folds are *geographic clusters*
  of districts, so the highest-magnitude cluster (Colombo/Gampaha) can end up entirely outside
  the range any other fold's calibration curve has seen — a structural property of spatial CV
  that a direct port of Module 2's mechanism didn't account for until it was tested and
  root-caused here.

---

## Session 8 — Visualization Engineering and Operational Extensions

**Read:** `MODULE_CONTEXT.md` "Visualization: Continuous Risk Surface", "Forward Operational
Hotspot Forecast"

Two things worth knowing beyond the modeling, because "code explanation" and "output
explanation" rubric points extend to these:

**The continuous risk-surface interpolation went through three real, checked iterations**, not
one: a country-wide-bandwidth kernel average was rejected because a wide bandwidth let distant
districts dilute the local signal (a real 12% expected gap came out as only 1.3%); a
per-district-bandwidth variant was rejected because it broke symmetry and actually **reversed**
the expected direction; k-nearest-neighbor Inverse Distance Weighting (k=4, later tuned to
power=4) was adopted because only the physically closest districts contribute at all, matching
the intended "risk points toward whichever neighbor has more cases" behavior. This is purely a
rendering-layer technique — it does not feed back into the RF or the iterative loop, and does
not change any committed Stage 1/2 output.

**Forward operational hotspot forecast (Decision 052)**: Module 3 has no forecasting capability
of its own (Stage 1's KDE weighting and Stage 2's residual target both require a known case
count), so its forward forecast **reads Module 1's `future_forecast.csv`** as a case-count
proxy — a one-directional, read-only cross-module dependency, consistent with each module's
scope rules. Every output row is tagged `evidence_tier="operational"` and must never be cited
alongside Stage 1's Moran's I or Stage 2's spatial-CV figures.

**Must be able to say, if asked why the map "looks smooth":**
> "The smooth continuous surface is a visualization technique, Inverse Distance Weighting over
> the 25 already-computed district risk scores — it doesn't add any new modeling, and we
> explicitly tested and rejected two other interpolation methods before choosing it, because
> they either diluted or reversed the expected spatial signal."

---

## Session 9 — Rehearsed Defense Answers

**Read:** `QUESTIONS_FOR_DEFENSE.md` "Does Module 3's hybrid (spatial baseline + Random Forest)
approach actually beat a simple, no-model baseline?" — this is Module 3's single most
comprehensive prepared answer and directly mirrors Session 0 of this plan; use its
"Defense one-liner" verbatim as your opening sentence, then be ready to name each of the four
rejected mechanisms if asked to go deeper.

**Other likely questions and where the answer lives:**
- "Why 25 districts and not finer sub-district units?" → Session 1/2 (scope decision, flagged
  as future work, not attempted-and-abandoned).
- "Why Random Forest and not GWR, given this is a spatial problem?" → Session 1 (GWR
  statistically unreliable at N=25).
- "Doesn't lacking a temporal holdout make this less rigorous than Modules 1/2?" → Session 1
  (different validation axis for a different research question, not a missing rigor step).
- "Is the improvement uniform across the country?" → No — be ready to name the NE-monsoon
  exception honestly (Session 6), the same way Module 1 names Kilinochchi/Mannar and Module 2
  names its Colombo/Gampaha Wk25 case.

---

## Session 10 — Delivery: Slides, Timing, What to Say vs. Hold Back

**Read:** `PRESENTATION_MODULE3_SLIDES.md` in full — this deck **is already current** (updated
2026-08-08 for M3-015; unlike Module 2, there is no separate stale v1 to accidentally present
from), but read the explicit **2026-08-08 update note at the top of the file** before presenting
— it explains exactly what flipped and why Table 7.6 is now safe to show as a positive result.

**Recommended 7-slide sequence**: gap & goal → two-stage design (Figure 6.4) → data layers →
Stage 1 Moran's I (positive rows only) → Stage 2 features + importance chart → Figure 7.5 peak
risk map + Table 7.6 → summary & three-module complementarity.

**Speaker guardrails:**
- Say: "Moran's I ≈ 0.70 confirms significant spatial clustering"; "Stage 2's correction is
  driven mainly by each district's own recent case history, with climate/demographics
  secondary"; "Stage 2 genuinely improves case-fit and hotspot ranking over both Stage 1 and a
  naive no-model baseline, confirmed with a bootstrap test."
- Avoid volunteering: the NE-monsoon non-significant week, the two earlier null/rejected design
  iterations (M3-005, M3-010/011 — mention only if asked how the final design was reached), or
  claiming the improvement is uniform everywhere.

**Concrete pre-submission action item (flag to the team now, not on presentation day):** per
`CHAPTER_STATUS.md`'s 2026-08-08 update note, `figure_5_5_module3_architecture.drawio`'s **text**
was corrected for M3-015's relative-residual framing, but its **PNG export was not** (no draw.io
CLI was available at the time) — and `figure_6_4_module3_implementation.png` inherits that same
staleness since it was adapted from Figure 5.5. **Both PNGs need a manual re-export before
submission**, or the architecture diagrams will visually contradict the current Stage 2
description in Chapters 5–7 and the slide deck.

---

## Quick-Reference Cheat Sheet (for the day of the evaluation)

```text
WHAT:      Case-weighted Gaussian KDE (Stage 1, Silverman bandwidth) -> Random
           Forest predicting a RELATIVE spatial residual (Stage 2), single-pass
           update (alpha=1.0), rescaled/reconstructed exactly back to Risk.
VALIDATION: 5-fold spatial K-means CV (whole districts held out) - no temporal
           holdout, because the research question is spatial, not future-time.
STAGE 1:   Global Moran's I = 0.70, p = 0.001 (significant clustering) - but
           NOT universal: NE-monsoon representative week (2021 Wk1) not
           significant, and later also Stage 2's weakest week (coherent, not
           coincidental).
HEADLINE (current, M3-015):  corr 0.96 / MAE 8.0 / RMSE 24.0, beating BOTH
           Stage 1 alone (corr 0.82 / MAE 20.5 / RMSE 48.2) AND naive
           persistence (corr 0.95 / MAE 9.4 / RMSE 26.6) - bootstrap-confirmed.
THE ARC:   null result (M3-005) -> looked like a win but lost to naive
           persistence (M3-008 -> M3-010/011) -> three more mechanisms tried
           and honestly rejected (M3-012/013/014) -> relative-residual
           reformulation (M3-015) finally wins on every metric. ALWAYS state
           the current claim, not the superseded 51%-vs-Stage-1-only one.
RIGOR:     GWR rejected before RF was chosen (N=25 too small); alpha=1.0 only
           safe once own-district lags were added; isotonic calibration (borrowed
           from Module 2) failed for a root-caused, module-3-specific reason
           (geographic CV folds break calibration's same-range assumption).
ACTION ITEM: Figure 5.5/6.4 PNGs still show the pre-M3-015 (stale) architecture
           text visually - re-export before submission.
```
