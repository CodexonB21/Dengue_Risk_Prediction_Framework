# Evaluation Study Plan — Module 2 (Hybrid Outbreak Risk Classification)

## Purpose of This File

Same purpose and format as `EVALUATION_STUDY_PLAN_MODULE1.md` — a viva-preparation curriculum
built entirely from what is actually implemented and decided in this repository, not from
generic classifier/calibration textbook knowledge.

**Read this warning before anything else.** Module 2's numbers changed **more times** than
Module 1's, because each of Stage 1's model choice, Stage 2's architecture, the label's own
statistical estimator, and the alert/tier thresholds are all coupled — changing any one of them
correctly triggers a recompute of the others. This is good research practice (nothing was left
stale), but it means **old numbers you might stumble across in the repo are not wrong, they are
superseded**, and quoting one from the wrong point in that chain in a viva will make you look
inconsistent even though the project itself is not. Session 0 below exists specifically to
inoculate you against this before you learn anything else.

Source files for this plan: `module_2_classification/MODULE_CONTEXT.md`,
`module_2_classification/EXPERIMENT_LOG.md` (M2-001 through M2-016), `RESEARCH_DECISIONS.md`
(Decisions 019–028, 046–049), `FEATURE_ENGINEERING_SPEC.md` (Module 2 sections),
`QUESTIONS_FOR_DEFENSE.md`, `PRESENTATION_MODULE2_SLIDES_v2.md` /
`PRESENTATION_MODULE2_COPY_PASTE_v2.md`.

**Owner of this module:** Nethma L.H.K. (214140X). Same team-readiness expectation as Module 1
applies — any member may be asked about any module.

---

## Session 0 — Why the Numbers Kept Changing (learn this before anything else)

Four things are coupled, in this order, and each change downstream of it is a **necessary**
recompute, not an inconsistency:

```text
1. Label estimator / k        →  changes which weeks count as "outbreak"
2. Stage 1 model + tuning     →  changes the raw probability distribution
3. Stage 2 architecture       →  which calibration method best fits THAT distribution
4. Alert / tier thresholds    →  re-selected fresh from THAT calibrated distribution
```

**The actual history, in order — memorize this table, it is the single most re-askable thing
in this module:**

| Event | Label (k) | Stage 1 (selected) | Stage 2 (selected) | Alert τ / high tier |
|---|---|---|---|---|
| Decision 019/021 (kickoff) | exact-per-week, k=2.0 | XGBoost | — | — |
| Decision 022/023 (Stage 2 built, Stage 1 tuned) | exact-per-week, k=2.0 | XGBoost (tuned) | isotonic | — |
| Decision 024 (thresholds added) | exact-per-week, k=2.0 | XGBoost (tuned) | isotonic | 0.170 / 0.570 |
| **Decision 025 (label re-estimated — M2-005)** | **harmonic regression, k=3.0** | **Random Forest** (flips — label shape changed) | isotonic (still) | 0.140 / 0.350 |
| **Decision 047 (RF itself tuned — M2-013, current)** | harmonic regression, k=3.0 | **Random Forest, tuned** | **Platt** (flips — Stage 1's output distribution changed) | **0.100 / 0.500** |

**Current production, as of this writing (2026-08-07):** harmonic-regression label (`k=3.0`) →
tuned Random Forest Stage 1 → Platt scaling Stage 2 → alert threshold **0.100**, high tier
**≥0.500**. Every number in the rest of this plan uses this row unless explicitly marked
"historical."

**Must be able to say, if asked "didn't your model keep changing? isn't that a sign of
instability?":**
> "Each change was a direct, evidence-driven consequence of the one before it, not an
> unrelated pivot. When we re-estimated the label to fix a genuine over-flagging problem, Stage
> 1's best model changed because the target itself changed shape. When we later tuned Stage 1's
> hyperparameters, its probability distribution shifted enough that a different calibration
> method became the better fit — that's Stage 2 doing exactly its job, adapting to whatever
> Stage 1 currently produces. Every one of these changes was checked on the untouched holdout
> block before being adopted, the same discipline used everywhere else in the project."

---

## Session 1 — Orientation: What Module 2 Actually Predicts, and Why It's Not a Residual Regression

**Read:** `MODULE_CONTEXT.md` "Current Architecture", `RESEARCH_DECISIONS.md` Decision 022's
Reason section, `QUESTIONS_FOR_DEFENSE.md` "Why does Module 2 use isotonic calibration instead
of climate/residual compensation like Module 1?"

Module 2 answers **"is this district-week epidemiologically abnormal?"** — a binary question —
not "how many cases" (Module 1) or "where is risk concentrated" (Module 3). The two-stage
design still follows the shared philosophy (`baseline + compensation = improved output`), but
**"compensation" means something different here than in Module 1**, and this is the single most
important conceptual point to get right before anything else:

> Module 1's residual is `actual_cases − sarima_prediction` — a continuous quantity, well-posed
> to regress on. For a binary label, the equivalent quantity would be `label −
> predicted_probability` for one Bernoulli observation — a high-variance, almost-pure-noise
> target with no clean way to keep `probability + predicted_residual` inside `[0, 1]`. This was
> recognized and rejected **before any code was written** (Decision 022), not discovered by
> trial and error. Compensation in Module 2 instead means **probability calibration** — fixing
> the *scale* of Stage 1's probabilities so a fixed threshold is meaningful — benchmarked
> against a literal stacked-feature correction model, which consistently lost.

**Must be able to say:**
> "Module 2 is a two-stage hybrid, same as Module 1, but Stage 2's job is recalibrating Stage
> 1's probability output, not regressing a residual. A literal port of Module 1's residual
> formula is statistically ill-posed for a binary target — we identified that during design,
> before writing any Stage 2 code, and benchmarked three well-posed alternatives instead."

**Self-check:**
- Q: If residual regression doesn't work for a binary label, why does Module 2 still count as
  "residual compensation" in the project's overall framing?
- A: Because it corrects the same underlying failure mode — a *systematic, learnable* error
  left by the baseline (a distorted probability scale caused by imbalance-correction machinery)
  — using the same two-stage separation-of-concerns idea. The correction target had to be
  redesigned per-task; the philosophy (baseline captures the main signal, Stage 2 fixes a known
  systematic weakness) did not.

---

## Session 2 — Data, Preprocessing Divergence from Module 1, and the Label

**Read:** `MODULE_CONTEXT.md` "Data Pipeline Note" + Open Question #9,
`FEATURE_ENGINEERING_SPEC.md` "Label Definition" section, `RESEARCH_DECISIONS.md` Decisions 019,
020, 025

Module 2 reads the **same shared tables** as Module 1 (`data/processed/shared/`), but makes its
own, independently-reviewed preprocessing choices (per Decision 013 — a module never inherits
another module's modeling-specific choice automatically):

| Choice | Module 1 | Module 2 | Why they differ |
|---|---|---|---|
| Week 53 (2009/2016/2019/2021) | **Merged** into week 52 (Decision 007) | **Kept unmerged** (Decision 020) | Merging would sum two real weeks' case counts before the epidemic threshold is computed — could spuriously trip the threshold and would contaminate week 52's cross-year mean/SD for *every* year, not just the four merged ones. SARIMA has no such per-week threshold semantic, so this exposure is Module-2-specific. |
| `is_imputed` masking | Applied to case lags/rolling stats | Applied to case lags/rolling stats **AND** the label itself | A real consistency bug was found and fixed during Module 2's dedicated preprocessing review (Decision 020) — originally only the label and `case_anomaly_lag` used the masking. |
| `weather_code` | Excluded (Decision 008) | Excluded (Decision 008 reasoning reconfirmed independently) | Same conclusion, reached by an independent review, not copied. |

**The label — this is the most important, most-likely-to-be-probed piece of Module 2:**

```text
outbreak(District, Year, Week) = 1 if Number_of_Cases > historical_mean(District, Week)
                                       + k * historical_sd(District, Week)
                                = 0 otherwise
```

- `historical_mean`/`historical_sd` use **only strictly-prior years** (an expanding window) —
  this is a **label-leakage** guard, a genuinely different risk category from Module 1's
  feature-leakage guard (Session 4 of the Module 1 plan). Computing this once globally would let
  every fold "know" about outbreak years that haven't happened yet.
- **The estimator itself was replaced (Decision 025), and you must know why**: the original
  estimator (exact sample mean/SD for that exact `(District, Week)` number, from as few as 3–15
  prior years) flagged **18–25% of all weeks** as "outbreak" — far above the single-digit-%
  WHO/CDC norm, because small-sample noise was flagging much of each district's ordinary
  seasonal (monsoon) peak, not just genuine anomalies. The current estimator fits one smooth
  **harmonic regression curve** (1 harmonic of week-of-year) per district-year, using that
  district's entire strictly-prior history, and uses the regression's residual SE as the SD.
  This pools a whole season's information instead of one exact week number, cutting pooled
  prevalence to **8.6%** while *also* reducing the undefined-label rate (16.0% → 10.7%) — a
  genuine win on both axes, not a trade-off.
- `k = 3.0` (was 2.0 under the old estimator — re-audited, not carried over unchanged, since the
  new estimator's SD is a structurally different quantity).
- **Honest, disclosed limitation**: raising the bar to fix the aggregate over-flagging problem
  also raises the threshold hardest in high-variance districts. Colombo's 2025 Wk15 (277 cases)
  is genuinely a real, motivating example: it was already correctly labeled `1` under the old
  estimator, but the new `k=3.0` estimator's much larger Colombo residual SD (209.0 vs. the old
  estimator's 87.7) actually **flips that specific row's label to `0`**. This is disclosed
  explicitly, not hidden, and a district-specific/variance-adaptive `k` is flagged as future
  work (see Session 7 — this was investigated, not just noted).

**Must be able to say:**
> "The outbreak label isn't an arbitrary fixed case count — it's a statistical exceedance
> threshold computed per district and week, using only years strictly before the row being
> labeled, so no fold can see its own future. We found the original version of this threshold
> was too noisy and over-flagged ordinary seasonal peaks, fixed it with a per-district harmonic
> regression that pools a whole season's data, and openly disclose that fixing the aggregate
> problem changed the label for at least one specific high-variance case we know about."

**Self-check:**
- Q: Why does Module 2 keep week 53 unmerged when Module 1 merges it?
- A: Merging would alter the case-count total feeding directly into a per-week statistical
  threshold used to define the *label itself* — a label-leakage-adjacent risk unique to
  classification. Module 1's SARIMA only needs a fixed 52-week seasonal period; it never
  computes a per-week statistic that a merge could distort.

---

## Session 3 — Methodology and Justified Alternatives

**Read:** `RESEARCH_DECISIONS.md` Decisions 021, 022, 025, 026; `MODULE_CONTEXT.md` "Stage 1
Implementation Status"

| Design choice | Alternative considered | Why rejected |
|---|---|---|
| `MODULE2_MIN_TRAIN_YEARS = 4` → 13 folds (not Module 1's 3-year/14-fold default) | Reuse Module 1's `DEFAULT_MIN_TRAIN_YEARS=3` | **Verified empirically, not assumed**: at 3 years, fold 1's entire training window has *zero* rows with a defined label for every district simultaneously — a calendar-driven effect, not something pooling could rescue |
| Pooled Stage 1 (Random Forest, `District` as a feature) | 25 per-district classifiers | **Tested directly**: pooled median PR-AUC 0.500 vs. per-district 0.287 (original XGBoost-era check); reconfirmed again after the label changed (0.373 vs. 0.343) |
| `class_weight="balanced"` / per-fold `scale_pos_weight` for imbalance | SMOTE/SMOTENC oversampling | **Audited twice**: rejected the first time on (later-corrected) reasoning; re-audited empirically after a literature review suggested it (Decision 026) — best SMOTENC variant's validation gain evaporates on holdout; every SMOTENC variant improved XGBoost's validation PR-AUC but *worsened* its holdout PR-AUC |
| Isotonic/Platt recalibration for Stage 2 | A literal `label − probability` residual regression | Statistically ill-posed for a Bernoulli target (Session 1) — considered and rejected at design time, not after building it |
| Fixed absolute probability thresholds for alerts/tiers | Quantile cutoffs (e.g. "top 10% of weeks are always high risk") | Quantile cutoffs would force a constant "high risk" rate regardless of true epidemic conditions — meaningless once probabilities are genuinely calibrated |
| F2-optimal alert threshold / F0.5-optimal high-tier boundary | A single, arbitrary 0.5 cutoff | 0.5 is the wrong operating point for a rare-event, recall-matters-more early-warning task — F-beta at two deliberately asymmetric points encodes *which kind of error matters more* at each tier, rather than inventing an ad hoc per-tier rule |

**Must be able to say (on why Stage 1 chose PR-AUC, not accuracy):**
> "With an outbreak prevalence around 8–18% depending on the label version, a classifier that
> always predicts 'no outbreak' already gets high accuracy — in fact Stage 1's own diagnostic
> shows accuracy is *below* a majority-class baseline in most validation folds, despite strong
> discrimination. PR-AUC is the metric that actually rewards ranking rare positive weeks
> correctly, which is what an early-warning system needs."

**Self-check:**
- Q: The SMOTENC audit's "best" variant actually improved Random Forest's validation PR-AUC.
  Why wasn't it adopted?
- A: That gain evaporated on the untouched holdout block (a statistical wash) and cost holdout
  recall — the wrong direction for a system deliberately tuned to favor recall (Decision 024).
  This is the same "validation-improves/holdout-regresses" failure pattern the project's
  holdout-once discipline exists to catch (see Session 7 for the parallel Module 1 case).

---

## Session 4 — Feature Engineering

**Read:** `FEATURE_ENGINEERING_SPEC.md` Module 2 sections (Groups M2-1 through M2-6, "Explicitly
Excluded"), `MODULE_CONTEXT.md` "Current Feature Direction"

| Group | Features | Purpose | Leakage-safety category |
|---|---|---|---|
| M2-1 Case-trend | `cases_lag_1..4`, rolling mean/std (4w), `rate_of_change`, `momentum_vs_rolling_mean` | Short-term case dynamics | Fold-agnostic; `is_imputed` masked (fixed consistency bug, Decision 020) |
| M2-2 Lagged climate (new vs. original plan) | rainfall 2–8w, temperature/humidity 1–4w | Dengue's ~2–8-week transmission delay; **added after review** because the original plan only had anomalies, which miss this delayed signal | Fold-agnostic |
| M2-3 Current-week climate + anomalies | current rainfall/temp/humidity + fold-aware anomalies | Unlike Module 1, Module 2's Stage 1 has **no climate-free purity constraint** — real-time weather is observable before case counts are confirmed, so it's a legitimate current-week feature here | Anomalies are **fold-aware** (reuses Module 1's `compute_fold_climate_anomalies` unchanged — module-agnostic code, not duplicated) |
| M2-4 Seasonal/contextual | `sin_week`, `cos_week`, monsoon indicators | Annual/monsoon cycle | Fold-agnostic; Module-2-local `MODULE2_MONSOON_WEEKS_NE` override handles week 53 (falls in the NE monsoon window) since week 53 isn't merged here |
| **M2-5 Case-level seasonal anomaly lags** | `case_anomaly_lag_1/2` | The single dominant Stage 1 signal — see below | Safe to compute **once, globally** (a *different*, provably-equivalent leakage-guard architecture from M2-3's — do not conflate the two) |
| M2-6 Pooled-model support | `District` | Lets pooled model retain district-specific behavior | — |

**The most important feature-engineering fact in this module:** `case_anomaly_lag_1` (0.352)
and `case_anomaly_lag_2` (0.268) together account for **over 60% of total feature importance**
in the official model. This is expected, not a red flag: `case_zscore` (the un-lagged version)
uses the *same* `historical_mean`/`historical_sd` machinery as the label itself, so at the
label's own `k`, an un-lagged `case_zscore` would be almost the label — this is exactly why only
the **lagged** versions are exposed as features, and the raw `Number_of_Cases`/`cases_per_100k`
are explicitly excluded from the feature matrix entirely (a documented leakage/metadata guard,
`FEATURE_ENGINEERING_SPEC.md`).

**Why M2-5 is safe to compute globally while M2-3's anomaly must be fold-aware — know this
distinction cold, it is a favorite "do you actually understand leakage or just follow a rule"
probe:**
> "`case_anomaly_lag`'s `historical_mean`/SD only ever uses years strictly before the row's own
> calendar year — which is exactly what any walk-forward fold's validation year needs. Computing
> it once globally is provably equivalent to computing it per fold for this specific
> construction. Module 1's climate anomaly is different: its 'long-term mean' is frozen at each
> fold's *training-window cutoff*, a rolling quantity that genuinely changes fold to fold, so it
> cannot be computed once without leaking."

**Self-check:**
- Q: Why is `Year` (raw) excluded from the feature matrix?
- A: It's monotonically increasing with the walk-forward split structure itself — a raw `Year`
  feature risks the model partially exploiting which fold a row belongs to, rather than genuine
  seasonal/climate signal.

---

## Session 5 — Code Walkthrough

**Read:** `MODULE_CONTEXT.md` "Implementation Plan" and Stage 1/2 Implementation Status sections

```text
1. src/preprocessing/module2_preprocessing.py   Week-53-kept, imputation + consistent NaN
                                                 masking, climate/population merge
2. src/module2_classification/labels.py         Fold-aware epidemic-threshold label;
                                                 compute_historical_stats (superseded, kept
                                                 for audit) + compute_historical_stats_harmonic
                                                 (current)
3. src/module2_classification/feature_engineering.py
                                                 FOLD_AGNOSTIC_FEATURE_COLUMNS (explicit
                                                 enumerated list — never "all columns minus
                                                 an exclude list"); case-anomaly lags reuse
                                                 labels.py's current estimator
4. src/module2_classification/baseline_classifier.py
                                                 Stage 1: LR/RF/XGBoost benchmark, pooled
                                                 architecture, class-weight imbalance handling
5. src/module2_classification/compensation_model.py
                                                 Stage 2: isotonic/Platt/stacked-XGBoost
                                                 benchmark by Brier Skill Score
6. src/module2_classification/risk_thresholds.py
                                                 Permanent pipeline stage: F2-optimal alert
                                                 threshold, F0.5-optimal high-tier boundary
7. src/module2_classification/evaluate.py       accuracy/precision/recall/specificity/f1/
                                                 roc_auc/pr_auc/brier/fbeta/threshold_scan
8. src/module2_classification/main.py           Idempotent orchestration, mirrors Module 1
9. src/module2_classification/live_scoring.py, forecast_future_risk.py, risk_tracking.py,
   uncertainty_bands.py                         Operational tier — NOT in main.py's
                                                 PIPELINE_STAGES, same precedent as Module 1's
                                                 forecast_future.py
```

**A real bug story worth knowing (M2-015)**: when Stage 2's official architecture flipped from
isotonic to Platt (Decision 047), the live/forward scoring code — untouched by the pipeline's
own idempotent stages, since it isn't wired into `main.py` — broke silently, because it called
`.predict()` uniformly for every architecture, which is correct for isotonic but wrong for
Platt (which needs log-odds input and `.predict_proba()`). This was only caught because the team
directly asked "can this actually predict next week right now" and ran it. **Lesson worth citing
in a viva**: code paths outside the automated, holdout-evaluated pipeline can silently drift out
of sync with a model change, and this project found that by testing the capability directly
rather than assuming it still worked.

**Self-check:**
- Q: Why does `feature_engineering.py` build its feature matrix from an explicit enumerated
  list rather than "all columns minus an exclude list"?
- A: That's exactly the pattern that let the original `Number_of_Cases`/`cases_per_100k`
  label-leakage risk go unnoticed during the first implementation pass — an explicit allowlist
  fails safe (a new column is invisible until deliberately added) instead of failing open (a new
  column is included by default unless someone remembers to exclude it).

---

## Session 6 — Results and How to Interpret Them

**Read:** `MODULE_CONTEXT.md` "Stage 1 Implementation Status" (Decision 047 update at the top),
"Stage 2 Implementation Status", "Risk Thresholds"; `PRESENTATION_MODULE2_COPY_PASTE_v2.md`

**The conceptual result you must explain before any number — the discrimination/calibration
split:**

Stage 1's "success" has two independent dimensions that tell *different* stories:

| Dimension | Question it answers | Result |
|---|---|---|
| Discrimination (PR-AUC) | Can it rank outbreak weeks above non-outbreak weeks? | **Strong** — beats the correct no-skill baseline (prevalence itself) in every validation fold and the holdout, median uplift 3.65x |
| Calibration (raw Brier Skill Score) | Are the probability *values* themselves trustworthy? | **Poor, by design** — negative BSS in most folds (median -0.11), i.e. worse than a trivial base-rate forecast |

This split is *why* Stage 2 exists — it is the direct evidence that probability recalibration is
a load-bearing prerequisite, not optional polish. `scale_pos_weight`/`class_weight` imbalance
correction improves ranking under a reweighted loss but distorts the raw probability scale — a
known, expected effect, not a modeling defect.

**Current production headline numbers (post Decision 047 — cite these, not older ones):**

| Metric | Value |
|---|---|
| Stage 1 (tuned Random Forest) holdout PR-AUC | **0.423** |
| Stage 1 holdout ROC-AUC | 0.905 |
| Stage 1 holdout Brier | 0.018 |
| Stage 2 (Platt) median validation BSS | 0.227 (vs. isotonic 0.220, both vs. Stage 1 raw ≈ −0.33) |
| Stage 2 (Platt) holdout BSS | **0.267** |
| Alert threshold (F2-optimal) | 0.100 |
| High-confidence tier boundary (F0.5-optimal) | 0.500 |
| Holdout recall, naive 0.5 cutoff | 37.5% |
| Holdout recall, calibrated τ=0.100 | **62.5%** |
| Holdout tier separation (observed outbreak rate) | Low 0.6% → Medium 20.4% → High 62.5% |

**Must be able to say (the "so what"):**
> "Stage 1 ranks outbreak-risk weeks well, but its raw probabilities are not directly usable for
> a fixed alert threshold, because imbalance correction distorts their scale — we showed this
> quantitatively, not just assumed it. Stage 2's calibration fixes that scale without touching
> ranking (Platt scaling is a monotonic transform, so PR-AUC/ROC-AUC are mathematically
> unchanged by construction), and the resulting risk tiers show strong, monotonic separation on
> data never used to pick the thresholds — nearly doubling usable early-warning recall versus a
> naive 0.5 cutoff."

**Honest caveats to be ready with, not to volunteer unprompted:**
- The holdout block under the current label has only **~40 positive rows** (1.5% prevalence) —
  meaningfully noisier than the original label's ~187 positives. State this if asked about
  confidence in the exact holdout percentages.
- Alert threshold precision at τ=0.100 is **34.2%** — most alerts are false alarms, an accepted
  and explained trade-off for an early-warning system (Decision 024's F2 framing), not something
  to hide, but also not something to lead with on a slide.

**Self-check:**
- Q: If Platt scaling can't change ranking, why does the holdout PR-AUC number (0.423) appear
  identical for "Stage 1" and "Stage 1+2"?
- A: Because that's mathematically guaranteed, not a coincidence or a missing improvement —
  Platt scaling (and isotonic regression) are both monotonic transforms of the raw score, so any
  metric that only depends on the *ranking* of predictions (PR-AUC, ROC-AUC) is unchanged by
  construction. Only metrics sensitive to the actual probability *values* (Brier, BSS,
  reliability) can show Stage 2's effect — this is worth stating proactively so it doesn't read
  as "Stage 2 did nothing."

---

## Session 7 — The Rigor Story: Rejected Ablations

**Read:** `EXPERIMENT_LOG.md` entries M2-006, M2-007A/D, M2-010, M2-011, M2-014, M2-016

Module 2 has its own rich arc of tested-and-rejected alternatives, parallel in spirit to Module
1's M1-007–M1-021 arc:

| Tried | Result |
|---|---|
| SMOTENC oversampling (4 variants × 2 models, Decision 026) | Best variant's validation gain evaporates on holdout; XGBoost variants improve validation but *worsen* holdout across the board — rejected |
| Stacked XGBoost Stage 2 (feature-based correction, M2-002/003/005/013) | Consistently underperforms isotonic/Platt every time it's been re-benchmarked, including after the label and Stage 1 both changed |
| Logit-residual Stage 2 variant (M2-007A) | Rejected — see `QUESTIONS_FOR_DEFENSE.md` |
| Leakage-safe M1 forecast lags fed into stacked Stage 2 (M2-007D) | PR-AUC improves (+0.054 vs. isotonic) but BSS regresses and precision @ fixed τ collapses — not promoted |
| Symmetric climate-free-Stage-1 ablation (M2-008) | Confirms the bottleneck isn't "climate was already in Stage 1" — even a Module-1-style split doesn't make stacked correction competitive |
| Stage 1 model ensembling — blend RF+XGBoost+LR (M2-010, Decision 046) | Blend wins decisively on validation (+0.039 PR-AUC), **then regresses on holdout** — the exact validation-improves/holdout-regresses pattern the holdout-once rule exists to catch (a direct parallel to Module 1's Decision 044/M1-020) |
| Per-district adaptive `k` for the label (M2-011) | **Mixed, not adopted**: genuinely narrows cross-district prevalence spread, but works *against* fixing the motivating Colombo 2025 Wk15 case — a real tension disclosed, not resolved by fiat |
| Module 3's spatial risk score, lagged, as a Stage 1 feature (M2-014) | Rejected — makes validation PR-AUC slightly worse; likely redundant with `case_anomaly_lag` since Module 3's KDE baseline is itself a spatially-smoothed transform of the same case-count signal |
| Carry forward `case_anomaly_lag_2` when `lag_1` is masked by a reporting anomaly (M2-016) | Rejected — validation PR-AUC regresses slightly; mixed per-fold direction; holdout deliberately not checked since the motivating case sits inside it |

**Must be able to say:**
> "Two of these findings mirror Module 1's own experience almost exactly, independently: a
> model-ensembling idea that won cleanly on validation and then failed the one-time holdout
> check, and a targeted fix for a specific real-world false negative that was tested honestly
> and rejected because it didn't clear the pre-registered validation bar — even though we
> couldn't even check whether it would have fixed the specific case that motivated it, because
> that case sits inside the untouched holdout block."

---

## Session 8 — Known Limitations and the Colombo/Gampaha Wk25 Case Study

**Read:** `MODULE_CONTEXT.md` Open Question #11 (Decision 049/M2-016),
`QUESTIONS_FOR_DEFENSE.md` "why did BOTH the forecast (Module 1) and the outbreak classification
(Module 2) go badly wrong for Wk25 2026"

This is likely the single best cross-module defense story available, because it shows the *same*
root cause breaking two different modules in two mechanistically different, precisely
diagnosed ways:

- Colombo/Gampaha's real cases went 507→**20**→1,138 (and 502→**24**→1,294) across three weeks
  — a reporting-delay artifact (Wk24 undercounted, folded into Wk25), already flagged by the
  shared `is_reporting_anomaly` detector (Decision 026/028) independently of this specific
  question.
- **Module 1's** most-trusted feature (`residual_lag_1`) was poisoned by the artificially low
  Wk24 count.
- **Module 2's** most-trusted feature (`case_anomaly_lag_1`, ~35% of Random Forest importance)
  was **masked to `NaN`** for the same reason (the reporting-anomaly guard applies to both
  modules), and `RandomForestClassifier`'s median-imputer filled that gap with approximately
  "no anomaly" — exactly the wrong prior during a genuine accelerating outbreak. Result: Colombo
  and Gampaha, both genuine outbreaks (`label=1`), were scored "low"/"medium" risk instead of
  "high" — a real, disclosed false negative.
- **The obvious fix was tried and rejected** (M2-016, Session 7) — carrying forward
  `case_anomaly_lag_2` did not clear the validation bar, and whether it would have fixed this
  *specific* row is genuinely unknown, since that row sits inside the untouched holdout block
  and the project's own rule is "validation wins first, holdout checks once."

**Must be able to say:**
> "One shared data artifact — a single mis-timed reporting dip — broke both Module 1 and Module
> 2's top feature at the same moment, because both modules lean hardest on 'what just happened.'
> We can name the exact mechanism in each module precisely, we tried the natural fix for each,
> and we can explain honestly why each fix was rejected, rather than either hiding the failure
> or claiming an untested fix would have worked."

**Other limitations to have ready:**
- Holdout positive-class count is small (~40 rows) under the current label — read exact holdout
  percentages with appropriate caution.
- Module 1 integration into Stage 2 remains deferred (fold-boundary misalignment between the two
  modules' walk-forward schemes — a real engineering cost, not an oversight); the one experiment
  that tried it anyway in an ablation-only path (M2-007D) found a ranking gain but a calibration
  cost, reinforcing why it isn't the default.
- Live/forward-scoring code has already been caught out of sync with a model change once
  (M2-015) — disclosed as a real lesson about non-pipeline code, not swept under the rug.

---

## Session 9 — Rehearsed Defense Answers

**Read:** `QUESTIONS_FOR_DEFENSE.md` in full for the Module 2 entries (and the two Module
1/Module 2 cross-cutting ones)

Already-rehearsed answers exist for:
- Why Module 2 uses calibration instead of a Module-1-style residual model
- Why Module 2 is needed at all if Module 1 already forecasts case counts (cross-module —
  **current headline comparison, from the v2 slide pack**: Module 2 production alerts reach
  holdout PR-AUC **0.423** vs. **0.063–0.280** for various ways of thresholding Module 1's raw
  forecast instead — Module 2 is not redundant)
- Do weather/climate anomalies get used in both modules (yes — Module 1 in Stage 2, Module 2 in
  Stage 1; know why the placement differs, Session 1's climate-free-Stage-1 rule is Module 1
  only)
- The Colombo/Gampaha Wk25 cross-module failure (Session 8)

**New item to add, specific to Module 2's own arc — rehearse this explicitly, it is not yet
written as a one-liner anywhere else:**
> "Why did your official Stage 1 model and Stage 2 architecture both change over the project?"
→ Answer using Session 0's table: the label was re-estimated first to fix a real over-flagging
problem (evidence: pooled prevalence dropped from 18–25% to 8.6%), which changed Stage 1's best
model as a direct, expected consequence of the target's shape changing; tuning Stage 1
afterward changed its probability distribution, which is exactly the kind of shift Stage 2's
architecture-selection step is designed to react to. Every step was holdout-gated before being
adopted.

---

## Session 10 — Delivery: Slides, Timing, What to Say vs. Hold Back

**Read:** `PRESENTATION_MODULE2_SLIDES_v2.md` in full — **use v2, not the v1 file**, which still
describes the pre-tuning isotonic-era stack and will contradict everything in Session 0 if mixed
in.

**Recommended 7-slide sequence**: gap & goal → two-stage design (Figure 6.3, needs re-export
per the slide pack's own note — it still labels Stage 2 "isotonic") → label & protocol → Stage 1
results (Table 7.3) → Stage 2 calibration (Figure 7.4, also needs recomposing for the same
reason) → alerts & tiers → summary & Module 1 complementarity.

**Speaker guardrails:**
- Say: "Random Forest (tuned) with Platt-scaling calibration is the production stack";
  "calibrated alerts nearly double usable recall versus a naive cutoff"; "risk tiers show
  ordered outbreak separation."
- Avoid volunteering: raw Stage 1 negative BSS, the full rejected-ablation list, precision
  numbers (34.2%) unless asked, or the isotonic→Platt architecture flip's mechanism unless
  directly asked — the honest answer (Stage 1 tuning changed the probability distribution) is
  fine to give *if asked*, per the slide pack's own guardrail, just not something to lead with.
- **Watch the figure/table versions**: this module has more superseded artifacts floating
  around than any other (v1 vs v2 slide packs, v1 vs v2 report chapter files, a v1 PNG that
  still says "isotonic"). Before presenting, confirm you are looking at a Decision-047-era
  asset, not a Decision-025-era or Decision-022-era one.

---

## A Note on Report-Chapter File Versions (Module-2-specific gotcha)

Per `CHAPTER_STATUS.md`, Module 2's report sections exist in **two versions** because of the
Decision 047 (Random Forest tuning) flip:

| Chapter section | Current (v2) | Superseded (v1, kept for reference only) |
|---|---|---|
| 5.4.2 (Module 2 design) | `chapter5_5.4.2_module2_v2.md` | `chapter5_5.4.2_module2.md` |
| 6.5 (Module 2 implementation) | `chapter6_6.5_module2_v2.md` | `chapter6_6.5_module2.md` |
| 7.4 (Module 2 evaluation) | `chapter7_7.4_module2_v2.md` | `chapter7_7.4_module2.md` |
| 7.6–7.8 (comparative/discussion/summary) | `..._v2.md` | `...md` |

**If you are asked to help finalize or present from these chapters, always confirm you are
reading the `_v2` file.** The combined mega-files (`chapter5_analysis_and_design.md`,
`chapter6_implementation.md`) still have the stale v1 text spliced in for their Module 2
sections as of the last `CHAPTER_STATUS.md` update — flag this to the team before final
submission if it hasn't been re-spliced by then.

---

## Quick-Reference Cheat Sheet (for the day of the evaluation)

```text
WHAT:      Random Forest (Stage 1, tuned, pooled) -> Platt scaling (Stage 2) on
           out-of-sample probabilities -> alert_flag / risk_tier.
WHY CALIBRATION, NOT RESIDUAL: label - probability is ill-posed for a binary target
           (Decision 022) - rejected at design time, not after building it.
LABEL:     outbreak = cases > harmonic-seasonal-mean(district,week) + 3*SD, strictly-
           prior-years only (label-leakage guard, distinct from feature-leakage).
VALIDATION: 13 walk-forward folds (MIN_TRAIN_YEARS=4) + untouched 2-year holdout.
HEADLINE:  Holdout PR-AUC 0.423 (Stage 1, strong discrimination); Stage 1 raw
           calibration poor (negative BSS most folds) -> Stage 2 (Platt) fixes it,
           holdout BSS 0.267; alert tau=0.100 raises holdout recall 37.5% -> 62.5%.
KEY INSIGHT: discrimination (can it rank?) and calibration (are probabilities
           trustworthy?) are separate, and Stage 1 only has the first - THIS is why
           Stage 2 exists.
RIGOR:     SMOTENC, Stage-1 ensembling, adaptive-k label, Module-3 spatial feature,
           M1-forecast-fed stacked Stage 2, and a targeted Wk25 false-negative fix
           were all tested and honestly rejected via the same holdout discipline.
NUMBERS CHANGED BECAUSE: label re-estimated (fixed real over-flagging) -> changed
           Stage 1's best model -> Stage 1 tuned -> changed Stage 2's best
           architecture -> thresholds re-selected. Each step holdout-gated.
```
