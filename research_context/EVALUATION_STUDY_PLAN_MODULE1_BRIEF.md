# Module 1 — Quick Study Guide (Simplified)

## What this file is

This is a **short version** of `EVALUATION_STUDY_PLAN_MODULE1.md`, built for fast revision —
for someone who has never seen this project before. Every technical word is explained the first
time it's used. It keeps only what you need to *understand and explain* Module 1; it drops the
long deep-dive tables and duplicate examples from the full plan.

If you need the full evidence trail (exact numbers, every ablation, every source file), go back
to `EVALUATION_STUDY_PLAN_MODULE1.md` — this file is for learning the shape of the argument
quickly, not for citing exact figures under pressure.

---

## 1. Glossary — read this first

| Term | Plain-English meaning |
|---|---|
| **SARIMA** | "Seasonal AutoRegressive Integrated Moving Average." A classic statistics method that predicts a number (here: next week's dengue cases) using only *that same number's own past pattern* — its trend and repeating yearly cycle. It does not look at rainfall, temperature, or anything else. |
| **XGBoost** | A machine-learning model that learns patterns from many input clues (features) to predict a number. Here, it's used to predict *how wrong SARIMA's guess will be*, using rainfall, temperature, season, and past mistakes as clues. |
| **Residual** | "Actual value − predicted value." Simply: the size and direction of the model's mistake. `residual = actual_cases − sarima_prediction`. |
| **Residual compensation** | The two-step trick this whole module is built on: make a simple guess (SARIMA), then train a second model to predict and fix that guess's mistake (the residual). `final_prediction = sarima_prediction + predicted_residual`. |
| **Baseline** | The first, simpler model (SARIMA here) — a deliberately basic starting guess. |
| **Feature** | An input clue given to a model, e.g. "rainfall 3 weeks ago" or "last week's forecast error." |
| **Lag feature** | A feature that just means "the value N weeks ago." E.g. `cases_lag_1` = last week's case count. |
| **Leakage** | Accidentally letting a model see information from the future during training — makes results look better than they really are, like taking an exam with the answer key. This project actively guards against it (see Section 3). |
| **Walk-forward validation** | Testing a time-series model fairly: always train on older data, test on the next chunk of newer data, then slide forward and repeat. Never test on data older than what you trained on. |
| **Holdout set** | A final block of the most recent data (here: last 104 weeks = 2 years, per district) that is *never touched* until the very last, one-time final check — like a sealed final exam. |
| **MASE** (Mean Absolute Scaled Error) | The main accuracy score used here. It compares the model's mistakes to the mistakes of the simplest possible guess (just repeating last week's number). **MASE ≈ 1** → "about as good as a trivial guess." **MASE well below 1** → clearly better. Lower is better. |
| **RMSE / MAE / sMAPE** | Other standard error-size metrics (root-mean-squared error, mean absolute error, symmetric mean absolute percentage error). All answer "how far off were we," in different units/weightings. |
| **DM test** (Diebold-Mariano test) | A statistics test that answers "is Model B *reliably* better than Model A, or could this just be luck?" A result is only trusted as a real improvement if this test says the difference is unlikely due to chance (a **p-value** below 0.05). |
| **Ljung-Box test** | Checks whether a model's mistakes still contain a repeating, learnable pattern, or whether they now look like random noise. If the test is "significant," a pattern is still there — meaning there's more the model could theoretically learn. |
| **Autocorrelation** | When a value is related to its own past values — e.g., last week's mistake predicts this week's mistake. |
| **Ablation** | An experiment where you deliberately change or remove one part of a working system to see if that change actually helps. Most ablations in Module 1 were tried and *rejected* (see Section 6) — that's still a useful, valid result. |
| **Pooled model** | One single model trained on all 25 districts' data together (told apart by a `District` label). |
| **Per-district model** | A separate, independently-trained model for each of the 25 districts (25 total models). |
| **Epi-week** | Sri Lanka's Ministry of Health "epidemiological week" calendar — not quite the same as a normal calendar week. Some years have 53 such weeks instead of 52. |
| **Nowcast** | A live, real-time "predict next week" output, used operationally — different from the backtested holdout evaluation. |
| **Vintage-ensembled SARIMA** | For the nowcast only: instead of trusting one SARIMA fit, average the current week's fit with the last 3 weeks' own independent forecasts for the same target week — several opinions averaged, not one. |

---

## 2. The big picture: three modules, one shared trick

- **Module 1 (this one):** "How many dengue cases next week, per district?" → a number.
- **Module 2:** "Is this an outbreak right now?" → yes/no.
- **Module 3:** "Where on the map is the risk highest?" → a location.

All three use the same idea — **baseline guess + correction step = better final answer** — but
each needs its own kind of answer, so they are not merged into one model. (Evidence: turning
Module 1's forecast into a yes/no alarm by picking a cutoff scores far worse — PR-AUC 0.063 —
than Module 2's purpose-built classifier — PR-AUC 0.412 — about 6.5× worse at correctly flagging
outbreak weeks.)

**Module 1's one-sentence definition:**
> Module 1 forecasts weekly dengue case counts per district using a two-stage residual
> compensation design: a SARIMA baseline captures the normal time pattern, and an XGBoost model
> corrects its leftover error using climate and epidemiological clues the baseline deliberately
> ignores.

---

## 3. The data (short version)

| Dataset | What it is | Coverage |
|---|---|---|
| Dengue case counts | Weekly cases per district (Sri Lanka MoH reports) | 2006-12-23 → 2026-06-21, 25 districts |
| Weather | Daily rainfall/temperature/humidity per district (Open-Meteo) | 2007 → present |
| Population | Census counts, only 3 real measurements (2001, 2012, 2024); years between are a straight-line estimate | Used only to compute `cases_per_100k`, never as the model's target |

Key facts worth knowing:

- **25 districts, not 26** — `Kalmunai` (no weather station) was merged into `Ampara`, because
  dropping it would waste ~17,500 real recorded cases.
- Some years have a 53rd epi-week; Module 1 merges it into week 52 so its yearly cycle length
  stays fixed (needed for SARIMA). Module 2 keeps the real week count instead — a deliberate
  difference between modules, not an inconsistency.
- **Missing weeks are estimated, not zero-filled** — filling with 0 would falsely look like "no
  cases." Instead, the same week from other years is averaged. These estimated rows are flagged
  and **excluded from every accuracy score**, so they can't make results look artificially good.
  Only 104 of ~25,350 rows needed this (under 0.5%).
- The team found and fixed real data errors before modeling (duplicate week labels, mislabeled
  dates, a district merge) — evidence the raw data was checked, not assumed clean.
- Zero-case weeks vary hugely by district: Colombo almost never has one (0.5%); Mullaitivu often
  does (~53%) — a per-district pattern, not a uniform data problem.

---

## 4. Methodology — the "why this, not that" table

This is the most important section for a viva: **every choice below was made to avoid leakage,
avoid an unrealistic test, or was directly tested against its alternative** — not picked
arbitrarily.

| What was chosen | What was considered instead | Why the alternative was rejected |
|---|---|---|
| SARIMA with **no climate data** | SARIMAX (SARIMA + climate built in) | If climate went into the baseline, the baseline would "use up" the climate signal itself, leaving a weaker, less informative mistake for Stage 2 to learn from |
| **One SARIMA per district** | One shared national SARIMA for all districts | Dengue behaves differently district to district; one shared model would hide or fake district-specific seasonal patterns |
| **Walk-forward validation + a locked 104-week holdout** | One single fixed train/test split | A single split gives an unreliable, easily-lucky/unlucky estimate over a ~19-year series |
| Stage 2 trained only on **out-of-sample** SARIMA mistakes | Training on in-sample (already-seen) mistakes | In-sample mistakes look smaller than real mistakes, which would make the correction step look better than it truly is |
| **One pooled XGBoost** for all districts (`District` as a feature) | 25 separate per-district XGBoost models | Actually tested head-to-head: per-district was clearly worse (+28.4% error on validation, only 4/25 districts improved) |
| **MAE loss** (treats all mistake sizes fairly evenly) | Standard squared-error loss | One district's (Vavuniya) SARIMA forecast went wildly wrong once; squared-error loss punishes big mistakes so hard that this one freak error dragged the whole shared model's training off course for every other district too |
| Left several districts **without a seasonal SARIMA term** | Force every district to have one | Forcing it was too slow to run at this scale, and a check showed non-seasonal districts actually benefit *more* from Stage 2's correction — so there was no real evidence forcing it would help |

**Core sentence to say out loud:**
> "Every major design choice here either came from a named risk — leakage, an unfair test split,
> pooling structure — or was directly tested against its alternative rather than assumed."

---

## 5. Feature engineering (the clues given to XGBoost)

Six groups of features, grouped by **what question each answers**:

| Group | Example features | What it tells the model |
|---|---|---|
| Recent case trend | last 1-4 weeks' case counts, rolling average | Is the outbreak accelerating or slowing right now? |
| Delayed climate effect | rainfall from 2-8 weeks ago, temperature/humidity 1-4 weeks ago | Mosquito breeding + disease incubation take time, so today's cases relate to *past* weather, not this week's |
| Climate anomaly | "how much more/less rain than usual for this week of the year" | Unusual weather matters more than raw weather |
| Season | cyclic week-of-year encoding, monsoon flags | Captures the yearly dengue cycle |
| Stage 1's own mistake | last week's/2-weeks-ago SARIMA error | SARIMA's mistakes tend to repeat — last week's error predicts this week's |
| Reporting-delay signals | "was there a suspicious case-count dip recently?" | Real data glitch found in 2026 (see Section 7) — flags weeks where the raw numbers likely aren't trustworthy yet |

**Why "climate anomaly" needs special care:** to know what's "unusual" rainfall, you need an
average of "normal" rainfall for that week. That average must only use years the model would
actually have seen at that point in time — otherwise you're secretly letting it peek at future
years. So this average is recalculated fresh for every validation round, not computed once over
the whole dataset.

**Most important single feature:** last week's SARIMA mistake (`residual_lag_1`) — by a wide
margin. This matches an independent statistical check (Ljung-Box test) showing 23 of 25
districts have mistakes that repeat week to week — two different methods agreeing on the same
finding.

---

## 6. Results — the headline numbers

| Metric | Baseline (SARIMA only) | With correction (SARIMA + XGBoost) |
|---|---|---|
| Median holdout MASE (the trusted, final number) | 0.622 | **0.375** (≈40% better) |
| Districts that improved on the validation rounds | — | 25 / 25 |
| Districts that improved on the final holdout | — | 23 / 25 |

**How to talk about this honestly:**
- Lead with: "the correction step improved accuracy for all 25 districts during validation, and
  23 of 25 on the untouched final test, with about a 40% error reduction."
- Two districts (Kilinochchi, Mannar) got slightly *worse* on the final holdout — disclosed
  openly, and the difference is not statistically significant.
- The DM test (checks if the improvement is real, not luck) only reaches strict statistical
  significance for a minority of districts at its strictest setting — expected, since each
  district's final test only has 104 data points, which limits how confident any statistical
  test can be, even for a real, consistent improvement.
- Even after the correction, 23/25 districts still show some repeating pattern left in their
  mistakes (Ljung-Box test) — the correction shrinks mistakes, it doesn't erase all structure.
  This is disclosed as an honest limitation, not hidden.

**The "so what":**
> A deliberately simple baseline leaves a learnable mistake behind, and a climate-aware
> correction model captures a meaningful share of it — about 40% median error reduction on data
> never used for model selection. It doesn't fully solve forecasting — real patterns remain in
> most districts — an expected, honestly-reported outcome.

---

## 7. Rigor: things that were tried and correctly rejected

After the core two-stage system worked, the team tried 8 further changes specifically to check
whether the design still held up. Most did **not** help — and that itself is useful evidence the
original design wasn't left unexamined.

| Tried | What happened |
|---|---|
| More past-mistake features (extra lags) | Looked better in validation, but got *worse* on the final holdout test — rejected |
| A different baseline model (STL+SARIMA) for tricky districts | Didn't beat the existing SARIMA — rejected |
| "Warm-starting" SARIMA (reusing old fits) | No accuracy change, 5-10× slower — rejected |
| Refitting SARIMA less often | No stability benefit despite being cheaper — rejected |
| Averaging forecasts differently (median instead of mean) | No improvement — rejected |
| Auto-correcting suspected reporting glitches in real time | Too many false alarms (only 42.9% precision) — rejected |
| Extensive hyperparameter tuning (40 tuning combinations tried) | Best option beat the current model on every practice round, but then did *worse* on the final holdout — rejected. **This is the strongest argument for why the holdout rule matters**: without it, a worse model would have been shipped. |
| Separate model per district instead of one shared model | Clearly worse (+28.4% error) — rejected, confirming the original pooling choice |

**The one change that *was* kept:** for the live, real-time "next week" prediction only
(not the scored holdout test), averaging the current SARIMA fit with the last 3 weeks' own
forecasts for that same week improved real-time accuracy. This is a separate, operational
improvement — it does not change the headline holdout number above.

---

## 8. Known limitations (say these before being asked)

| Limitation | Why it happened | Why it's not a hidden weakness |
|---|---|---|
| Most districts (18/25) have no seasonal term in their SARIMA model | The automatic model-order search chose not to use one | Those same districts benefit *more* from the correction step, which is designed to catch exactly this kind of missed seasonal signal |
| Two districts get worse on the final holdout | Traced to specific unusual data periods for those districts, not a general failure | Not statistically significant; the same fix (per-district weighting) already helped two *other* districts |
| Some repeating pattern remains in mistakes after correction (23/25 districts) | Correction reduces mistake *size*, not all repeating structure | Adding more of the same feature type was tried and made things worse — an honestly reported open problem |
| A 2026 real-world forecast miss for two districts | A genuine reporting-delay glitch in the raw case data (a temporary count crash-then-rebound) fed bad information into the model's most-trusted feature | The exact cause is identified and named; a real-time fix was tried and honestly rejected for being too unreliable, rather than left untested |

---

## 9. One paragraph — if you remember nothing else

> Every week, for each of Sri Lanka's 25 districts, we make a simple first guess at next week's
> dengue case count using only that district's own case history (SARIMA). A second model
> (XGBoost) then looks at how wrong that guess usually is, plus rainfall, temperature, season,
> and last week's mistake size, and produces a correction. Adding the correction to the first
> guess gives the final forecast. We tested this fairly — always practicing on older data, and
> grading once on a locked-away block of the newest data — and the correction made forecasts
> about 40% more accurate on that locked-away test, for almost every district. We then tried
> eight further changes to check we weren't missing something better; only one — averaging
> several recent weeks' own forecasts for real-time use — actually helped.

---

**For exact figures, per-district tables, every ablation ID, and source file references, see
the full version:** `EVALUATION_STUDY_PLAN_MODULE1.md`.
