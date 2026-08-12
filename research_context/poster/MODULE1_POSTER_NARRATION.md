---
name: module1-poster-narration
description: Spoken walkthrough script for presenting the Module 1 (Hybrid Time-Series Case Forecasting) poster to an evaluator
metadata:
  type: report_support
---

# Module 1 Poster Walkthrough Script

**Purpose:** spoken narration for an evaluator/viva walkthrough of the Module 1 poster
panel (system diagram + holdout MASE plot + key-outcomes chart). Organized to move
left-to-right, top-to-bottom across the panel, in a **why → how → outcome** pattern for
every decision point. Target delivery time: ~4-5 minutes for the full walk; a 90-second
condensed version is marked at the end for time-boxed judging rounds.

All figures/numbers below are taken from `module_1_forecasting/MODULE_CONTEXT.md` and
`research_context/QUESTIONS_FOR_DEFENSE.md` as of 2026-08-11. If any number on the
printed poster is later corrected, update this script from the same source files —
do not let this drift into a separate "the poster said X" narrative.

---

## 0. Opening (10-15 sec)

*(Stand beside the panel, gesture to the title.)*

"This is Module 1 of our residual compensation framework for dengue risk prediction —
Hybrid Time-Series Case Forecasting. The question it answers is: **how many dengue
cases will a district report next week?** The core idea is a two-stage hybrid: a
simple, interpretable baseline model, corrected by a learned model that studies where
the baseline tends to be wrong."

---

## 1. Input panel — why these two inputs

*(Point to the Input bullet list, top-left.)*

**What:** weekly dengue case counts per district, 2007–2026, from MoH epi-week reports;
and daily climate — rainfall, temperature, humidity — from Open-Meteo, aggregated to
weekly.

**Why two separate sources, not one merged table from the start:** because the two
stages of this pipeline are deliberately given different information. Stage 1 only
ever sees case history. Climate is held back and given only to Stage 2. That split is
the central design decision of this module, and everything downstream exists to
support it.

---

## 2. Methodology — Data Preprocessing

*(Point to "Data Preprocessing" box in the diagram, top-center-left.)*

**How:** two district-name typos were corrected; `Kalmunai`, which has a real 19-year
case history but no matching weather station, was merged into `Ampara` so every
modeled district has complete climate coverage; occasional 53-week calendar years are
merged into week 52 so the seasonal period stays fixed at 52 for SARIMA; the small
number of genuinely missing weeks are imputed and flagged with an `is_imputed`
indicator rather than silently filled.

**Why it matters to say out loud:** a reviewer's first instinct with any forecasting
claim is "is the underlying series clean?" This step is the answer — 26 raw districts
became a defensible set of 25, and every imputed point is traceable, not invisible.

---

## 3. Stage 1 — SARIMA baseline

*(Point to the SARIMA box.)*

**How:** one SARIMA model is fitted per district, using case counts only, with orders
selected by a constrained stepwise `auto_arima` search rather than manual tuning.

**Why SARIMA, and why per-district:** dengue transmission is strongly seasonal and
autocorrelated at the district level, and 25 districts have genuinely different
epidemic dynamics — pooling them into one baseline model would blur that. SARIMA gives
an interpretable, statistically grounded per-district reference point.

**Why climate is deliberately excluded here — the "why" an evaluator will most likely
push on:** this isn't an oversight. It's Decision 001 of the framework, made so that
Stage 1's error — the residual — has a known, interpretable source: whatever the case
history alone couldn't explain, which is largely the climate-driven and other
non-linear structure Stage 2 is built to learn. If climate went into Stage 1 as well,
Stage 2's target would be a mixture of unexplained noise and leftover climate signal,
and we'd lose the ability to say cleanly what each stage contributes.

---

## 4. Stage 2 — XGBoost residual compensation

*(Point to the Feature Engineering and XGBoost boxes, right side.)*

**How — features:** case lags and rolling statistics, climate lags and anomalies,
monsoon indicators for both the south-west (weeks 20–38) and north-east (weeks 44–52,
1–8) monsoons, cyclic week-of-year encodings, and lags of the residual itself.

**How — training:** a single **pooled** XGBoost model across all 25 districts, with
`District` included as a categorical feature, trained only on **out-of-sample**
residuals — i.e. the residual a district's SARIMA model produced on data it hadn't
seen, never on in-sample fit error. That last point is what keeps this from being
leakage: if Stage 2 trained on in-sample residuals, it would just be learning to
predict SARIMA's own overfitting, not real forecast error.

**Why pooled, not one XGBoost per district — this was tested, not assumed:** a
same-conditions ablation trained 25 separate per-district Stage 2 models instead. It
was decisively worse — validation-aggregate median MASE 0.747 vs. the pooled model's
0.582, with only 4 of 25 districts and 1 of 13 folds improving. The four districts that
*did* do better without pooling (Monaragala, Mannar, Vavuniya, Matale) are flagged as a
targeted future-work direction, not evidence the pooled design is wrong overall.

---

## 5. Combine Outputs

*(Point to the purple "Combine Outputs" box and the equation.)*

"`Final Prediction = ŷ_SARIMA + predicted residual`, clipped at zero because case
counts can't be negative. This is the whole mechanism — Stage 2 doesn't replace the
baseline, it corrects it."

---

## 6. Model Evaluation — why this much validation machinery

*(Point to the Model Evaluation bullet block.)*

**How:** 14 expanding-window annual walk-forward folds, plus a completely untouched
2-year (104-week) holdout block that played no part in any model-selection or
hyperparameter decision. Metrics: RMSE, MAE, sMAPE, MASE, residual variance reduction,
and the Diebold–Mariano significance test.

**Why walk-forward, not a single train/test split:** a single split can flatter or
punish a model depending on which weeks happen to land in the test set, especially
with only ~19 years of weekly data per district. Walk-forward averages across 14
independent forecast origins, so one unlucky fold — this genuinely happened for
Vavuniya in one fold — can't distort the headline number.

**Why MASE is the headline metric, not RMSE alone:** MASE is scale-free. Colombo
reports hundreds of weekly cases, Mullaitivu reports a handful — RMSE alone would make
cross-district comparison meaningless. MASE compares each district's error to its own
naive-seasonal baseline, so "improvement" means the same thing everywhere on this
poster.

**Why the Diebold–Mariano test, in addition to the improvement percentages:** a
percentage improvement alone doesn't say whether that improvement could be noise.
DM formally tests whether Stage 2's forecast errors are significantly smaller than
Stage 1's, district by district — which is what lets us say plainly, later, when an
improvement is *not* statistically distinguishable from zero, instead of overclaiming.

---

## 7. The system diagram, read end-to-end

*(Step back, trace the full diagram left to right with one hand.)*

"So end to end: weekly dengue cases go through shared preprocessing into a per-district
SARIMA baseline, which produces a base prediction and, from that, a residual. In
parallel, climate and engineered features go through feature engineering into a pooled
XGBoost model that has learned, from history, how to predict that residual. The two
outputs are combined — baseline plus predicted correction — into the final compensated
weekly forecast per district."

---

## 8. The holdout MASE dot plot — reading it live

*(Point to the purple-bordered chart, lower-right of the main panel.)*

**How to read it:** each row is a district, sorted by holdout performance. The grey dot
is Stage 1 (SARIMA) alone; the orange dot is Stage 1+2 where it improved; a red diamond
marks the two districts where it didn't. The vertical reference line at MASE = 1 is the
seasonal-naive baseline — anything left of it beats "just repeat last year's value for
this week."

**Why show every district instead of just the median:** the median (32.7% holdout
improvement) can hide districts that got worse. Showing all 25 is the more honest
version of the claim, and it's also more informative — it shows *where* the method's
limits are, not just that it works on average.

**Why Kilinochchi and Mannar don't improve, and why that's not swept aside:**
Kilinochchi shows the largest gap on this chart — worse than the pre-fix baseline —
and Mannar is the other exception, newly negative. Both are small-population, low-count
districts with noisier series. Critically, the Diebold–Mariano test shows neither
degradation is statistically significant (p ≈ 0.33–0.40) — so the honest reading is
"directionally worse, not reliably worse," not "the model failed here."

---

## 9. Key Outcomes panel — the headline claim

*(Move to the second panel.)*

"Across all 25 districts on validation, and 23 of 25 on the untouched holdout, the
SARIMA + XGBoost pipeline beats the SARIMA-only baseline. Median improvement: 43.5%
on validation, 32.7% on holdout."

**Why report validation and holdout as two separate numbers, not one blended figure:**
validation draws on far more data (14 folds × 52 weeks) and gives statistical power;
holdout is smaller but was never touched during any modeling decision. Reporting both,
and showing that both point the same direction, is what makes this result credible
rather than an artifact of tuning against the same data used to judge it.

---

## 10. Colombo forecast chart — reading the anomaly honestly

*(Point to the Colombo actual/Stage 1/Stage 1+2 line chart.)*

**How to read it:** black is actual reported cases, grey dashed is the SARIMA-only
baseline, orange is the compensated Stage 1+2 forecast. For most of the holdout window
the orange line visibly tracks the black line more closely than the flat grey one —
that's the compensation effect, visually.

**Why the two flagged spikes are marked, not hidden:** these mark a documented
reporting-delay event — Colombo's reported cases went 507 → 20 → 1,138 across three
consecutive weeks (Gampaha showed the same pattern: 502 → 24 → 1,294). That's not a
real epidemic curve; a genuine outbreak doesn't crash to near-zero for one week and
then quadruple. It's most consistent with a health-system reporting backlog — week 24's
real cases likely weren't fully counted before the report went out, and were folded
into week 25's number instead. Both models missed this the same way because their
single most trusted signal is "what just happened" — Stage 2's top feature is exactly
the residual from the previous week — so an artificially low prior week told both
models the trend had just dropped, right before the true jump.

**Why we didn't just fix it with a real-time detector, and why that's the stronger
answer to give an evaluator:** one was built and tested — a rule to catch this kind of
suspicious dip and correct the forecast in real time. It was rejected: only 42.9%
overall precision, and worse specifically for Colombo and Gampaha (46.2% / 30.0%).
More than half of its real-time flags would have been false alarms on a genuine
decline, which would do more harm than the occasional missed spike. Leaving it
uncorrected, but transparently flagged via the `is_reporting_anomaly` indicator in the
data, is the more defensible engineering decision — it's evaluated and documented,
not swept under the rug.

---

## 11. Closing (10-15 sec)

"So Module 1's contribution is a validated, statistically tested demonstration that a
simple, interpretable time-series baseline plus a learned residual-compensation model
outperforms the baseline alone — consistently on validation, and on the majority of
districts on data the pipeline never saw during development, with the exceptions and
known failure modes reported alongside the headline numbers rather than hidden from
them."

---

## Condensed 90-second version (time-boxed judging)

1. "Module 1 forecasts weekly dengue cases per district using a two-stage hybrid:
   SARIMA baseline, climate-free by design, corrected by a pooled XGBoost model that
   learns to predict the baseline's own residual error from climate and engineered
   features."
2. "Validated on 14 walk-forward folds plus an untouched 2-year holdout: 25 of 25
   districts improve on validation, 23 of 25 on holdout, median MASE improvement 43.5%
   and 32.7% respectively."
3. "The two holdout exceptions — Kilinochchi and Mannar — are shown directly on the
   chart, and neither degradation is statistically significant by Diebold–Mariano."
4. "This Colombo spike is a known, investigated reporting-delay artifact, not a hidden
   model failure — we tested and rejected a real-time fix because it would have created
   more false alarms than it solved, and documented the event instead."

---

## Anticipated evaluator questions (from `research_context/QUESTIONS_FOR_DEFENSE.md`)

**Q: Why not let SARIMA use climate too, since it's freely available?**
A: That would remove the clean interpretation of the residual as "what case history
alone can't explain." It's a deliberate research-design choice (Decision 001), not a
missed opportunity — Stage 2 is where climate contributes.

**Q: Why one pooled model instead of one XGBoost per district — wouldn't per-district
be more precise?**
A: Tested directly; per-district was 28% worse in aggregate and only helped 4 of 25
districts. Pooling lets the model borrow strength across districts with similar
dynamics; the few districts that prefer per-district treatment are noted as future
work, not ignored.

**Q: Doesn't the Colombo chart show the model failing badly?**
A: It shows one specific, explained data-quality event — a reporting delay — not a
general forecasting failure. We tested a real-time correction for exactly this pattern
and rejected it because it produced more false alarms than it prevented; the honest
choice was to flag, not silently patch, the anomaly.

**Q: If Kilinochchi and Mannar get worse, is the "23/25" claim overstating success?**
A: No — both are reported explicitly on the chart, and their apparent worsening is not
statistically significant (Diebold–Mariano p ≈ 0.33–0.40), so the honest claim is
"consistently non-worse across all districts, materially better in the large majority,"
which is exactly what's stated.
