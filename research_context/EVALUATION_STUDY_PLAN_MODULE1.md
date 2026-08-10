# Evaluation Study Plan — Module 1 (Hybrid Time-Series Case Forecasting)

## Purpose of This File

This is a **study/viva-preparation curriculum**, not report content. It exists to take someone
with zero prior exposure to this project or to the code, and get them to the point where they
can confidently explain, defend, and answer follow-up questions on Module 1 in a formal
evaluation.

It is built entirely from what is actually implemented and decided in this repository
(`RESEARCH_DECISIONS.md`, `module_1_forecasting/MODULE_CONTEXT.md`,
`module_1_forecasting/EXPERIMENT_LOG.md`, `QUESTIONS_FOR_DEFENSE.md`,
`FEATURE_ENGINEERING_SPEC.md`, `DATA_DICTIONARY.md`, and the presentation packs) — not from
generic ARIMA/XGBoost textbook knowledge. Cross-reference those files directly whenever this
plan says "see Decision NNN" or "see M1-0XX".

Companion files (to be produced separately): `EVALUATION_STUDY_PLAN_MODULE2.md`,
`EVALUATION_STUDY_PLAN_MODULE3.md`, `EVALUATION_STUDY_PLAN_SHARED.md` (shared preprocessing,
dashboard/integration, and whole-project questions that don't belong to one module).

**Owner of this module:** Bandara H.R.B.G.M. (214029P). If you are not Bandara, treat this as
learning someone else's work well enough to defend it as a team — evaluators may ask any team
member about any module.

**A note on how to read this version:** every session below now opens with a **"In plain
words"** box that explains the idea the way you'd explain it to a friend, with an everyday
example. The precise technical sentences (the "Must be able to say" quotes and the tables) are
kept exactly as written, because those are the actual words you need to be able to say in the
room — the plain-language box is there so you understand *what those sentences mean* before you
try to memorize them, not to replace them.

---

## How to Use This Plan

Work through the sessions in order — each builds on the last. For each session:

1. Read the listed source file section(s) first — this plan summarizes and organizes them, it
   does not replace them.
2. Read the "In plain words" box, then the "Must be able to say" box — these are the sentences
   you should be able to produce unprompted.
3. Attempt the self-check questions *before* looking at the linked answer.
4. Only move on once you can answer the self-check questions without notes.

Budget roughly 1 focused session per row below (9 sessions + 1 gap-closing session).

---

## Session 1 — Orientation: What Is This Project and Where Does Module 1 Fit

**Read:** `PROJECT_CONTEXT.md`, `CURRENT_ARCHITECTURE.md` (top section + Module 1 section)

**In plain words:** Imagine three separate helpers, each answering a different question about
dengue in Sri Lanka:

- Module 1 (yours) answers **"how many dengue cases will district X have next week?"** — a
  number, like a weather forecast temperature.
- Module 2 answers **"is district X having an unusually bad week right now?"** — a yes/no flag,
  like a smoke alarm.
- Module 3 answers **"which parts of the map are the hottest right now?"** — a location, like a
  heat map on the news.

All three helpers use the *same trick* to do their job well: first make a simple guess, then
have a second, smarter step fix that guess's mistakes using extra clues the first guess ignored.

```text
Baseline model output + residual/error compensation = improved final output
```

- Module 1 (yours): baseline = SARIMA (a simple guesser using only past case counts), correction
  = XGBoost fixing that guess using climate and other clues.
- Module 2: baseline = Random Forest classifier, correction = **probability calibration**
  (not a residual regression — a binary label makes that ill-posed, see Session 7).
- Module 3: baseline = KDE + Moran's I spatial surface, correction = spatial residual
  adjustment via Random Forest.

Do not blur these three together — evaluators will test whether you understand why three
separate modules exist rather than one combined model. A simple way to say why: a single "is it
bad?" alarm can't also tell you "how many cases exactly" or "where on the map" — each question
needs its own kind of answer.

**Must be able to say:**
> "Module 1 forecasts weekly dengue case counts per district using a two-stage residual
> compensation design: a SARIMA baseline models the normal temporal pattern, and an XGBoost
> model corrects the baseline's leftover error using climate and epidemiological features the
> baseline deliberately excludes."

**Self-check:**
- Q: Why not just feed climate data into SARIMA directly (SARIMAX) instead of a two-stage
  design?
- A: See Decision 001 — if climate enters Stage 1, the baseline may absorb the climate signal
  itself, leaving weaker/less informative residuals for Stage 2 to learn from. Keeping Stage 1
  climate-free is what makes the residual meaningful for the compensation architecture. This is
  a deliberate research design choice, not an oversight.
  **Plain-words version:** if you already gave the first guesser every clue (rain, temperature,
  everything), there's nothing left for the second helper to notice and fix — like handing all
  the hints to Student A, leaving Student B (whose only job is to catch Student A's mistakes)
  with nothing useful to correct.

**Deep Dive — the cross-module question you will likely get even while presenting only Module 1:**
"If Module 1 already forecasts case counts, why do you need Module 2's separate alert system at
all — couldn't you just flag an outbreak whenever Module 1's forecast crosses a threshold?" This
was actually tested (`QUESTIONS_FOR_DEFENSE.md`, M2-009 comparison, holdout, 2,600 district-weeks,
40 true outbreaks):

| Rule | PR-AUC | Recall | Precision | F2 | Alerts raised |
|---|---:|---:|---:|---:|---:|
| Module 2 production (isotonic-calibrated RF, τ=0.14) | 0.412 | 0.600 | 0.338 | 0.519 | 71 |
| Module 1 forecast > same epidemic threshold | 0.063 | 0.225 | 0.563 | 0.256 | 16 |
| Module 1 forecast > fixed 100-case cutoff (naive) | 0.063 | 0.500 | 0.073 | 0.231 | 273 |
| Oracle (perfect hindsight) | 0.302 | 1.000 | 1.000 | 1.000 | 40 |

**Plain-words takeaway:** turning Module 1's number into a yes/no alarm by just picking a cutoff
performs far worse (PR-AUC 0.063) than Module 2's purpose-built classifier (PR-AUC 0.412) — about
6.5× worse at ranking which weeks are genuinely outbreak weeks. A forecast optimized to get the
*count* close is not the same tool as a classifier optimized to correctly rank *how abnormal* a
week is — this is the concrete evidence behind "each question needs its own kind of answer" from
the plain-words box above, not just an assertion.

---

## Session 2 — The Data (evaluation point: "Dataset")

**Read:** `DATA_DICTIONARY.md` (sections 1–3, 6–7), `MODULE_CONTEXT.md` "Resolved Data
Questions" + "Raw Data Audit Findings"

**In plain words:** Three spreadsheets, roughly:

1. **Dengue case counts** — how many people got dengue, per district, per week, going back
   about 19-and-a-half years.
2. **Weather** — daily rainfall/temperature/humidity for each district.
3. **Population** — how many people live in each district, but only measured 3 times (2001,
   2012, 2024 census years) — everything in between is an educated guess (a straight line drawn
   between the two nearest known points, like estimating your age on a date between two
   birthdays).

**What the datasets actually are:**

| Dataset | Grain | Coverage | Source |
|---|---|---|---|
| Epidemiological (dengue cases) | District × MoH epi-week | 2006-12-23 → 2026-06-21 (~19.5 yrs), 25 districts | Sri Lanka MoH Weekly Epidemiological Report, scraped |
| Meteorological (climate) | Daily, per-district (single point) | 2007-01-01 → rolling refresh (observed + ~16-day forecast) | Open-Meteo Archive + Forecast API |
| Population/census | Per district, 3 points only | 2001, 2012, 2024 | National census |

Key facts you must be able to quote:

- **25 official districts** (not 26): `Kalmunai` (a real ~19-year case series with no weather
  station) was merged into `Ampara` — Decision 012. Know *why*: Kalmunai is administratively
  inside Ampara, and dropping it would discard ~17,500 real cases. (Plain words: two
  neighbourhoods that are really part of the same city get counted together, because one of them
  never had its own weather station to give it separate climate data.)
- **Sri Lanka MoH epidemiological week**, not ISO calendar week — a project-specific
  time unit. Some years have 53 weeks (2009, 2016, 2019, 2021); Module 1 merges week 53 into
  week 52 (Decision 007) to keep SARIMA's seasonal period fixed at m=52. **Module 2 does not do
  this** (Decision 020) — know this divergence, evaluators may probe cross-module consistency.
  (Plain words: like a school year that occasionally has 53 weeks instead of 52 — Module 1 folds
  that extra week into the last one so every year looks the same length, which its forecasting
  method needs; Module 2 doesn't need that and keeps the real week count.)
- **Zero-inflation is real but concentrated**: pooled 13.7% zero-case weeks, but this ranges
  from ~0.5% (Colombo) to ~53% (Mullaitivu). Not a uniform problem — a per-district property.
  (Plain words: Colombo almost always has at least one case reported each week — like a busy shop
  that always has customers — while Mullaitivu often has entire weeks with zero cases, like a
  quiet shop that's sometimes empty all day.)
- **Climate is single-point-per-district**, not a spatial average — a genuine Open-Meteo
  constraint, documented as a limitation, not something the pipeline can fix. (Plain words: one
  weather station's reading is used to represent an entire district, even though rain in the
  north of a district can differ from rain in the south.)
- **Extensive raw data cleaning was actually done**, by the team, not assumed clean: 5
  week-boundary collisions, 2 district-name typos, 30 chronologically-mislabeled weeks (28
  hand-corrected against original MoH source pages, 2 more caught during verification), 3 more
  date-entry errors found by a full-calendar day-count scan. This is genuine evidence of data
  diligence — cite it if asked "how do you know your data is reliable?"
- **Missing weeks are imputed, not dropped or zero-filled**: seasonal-naive imputation
  (same district, same epi-week, averaged across other years), flagged `is_imputed`, and
  **excluded from every evaluation metric** (Decision 011). Only 104 district-week rows
  (<0.5% of the dataset) needed this. (Plain words: if a week's real number is missing, we don't
  guess "zero cases" — that would falsely look like a healthy week. Instead we look at that same
  calendar week in other years and average them, the way you might guess a missing electricity
  bill by averaging that same month's bill from other years.)
- **Population is a reporting-layer denominator only** (`cases_per_100k`), never the modeling
  target (Decision 006) — this avoids reopening Module 2/3's label definitions. Three war-
  affected districts (Kilinochchi, Mullaitivu, Mannar) have a non-monotonic population trend
  from wartime displacement that linear interpolation can't fully capture — a documented,
  accepted limitation, not silently ignored.

**Must be able to say:**
> "We work with weekly case counts for 25 districts over roughly 19.5 years, aligned to Sri
> Lanka's MoH epidemiological week calendar, plus daily climate data from Open-Meteo aggregated
> to the same weekly grid. Before any modeling, we ran a full data audit that found and fixed
> concrete, traceable errors — duplicate week labels, mislabeled dates, a merged district with
> no weather station — rather than assuming the raw scrape was clean."

**Self-check:**
- Q: If an evaluator asks "how do you know the imputed weeks don't bias your results?" — what
  do you say?
- A: Imputed weeks are flagged with `is_imputed` and excluded from every accuracy metric
  (RMSE/MAE/sMAPE/MASE) and from Stage 2 targets — they exist so the series stays regularly
  spaced (a SARIMA requirement) without silently corrupting reported performance. Only 104 of
  ~25,350 rows are affected.
  **Plain-words version:** we mark the guessed weeks with a sticky note ("this one's a guess")
  and never let those guessed weeks count when we grade how good the model is.

**Deep Dive — the exact numbers behind "zero-inflation is real but concentrated"
(`DATA_DICTIONARY.md` Section 7):** pooled zero-case-week rate 13.7%, concentrated in
`Mullaitivu` (52.8%), `Kilinochchi` (47.7%), `Mannar` (40.4%), `Ampara` (32.9%), `Vavuniya`
(32.3%); near-zero for the high-incidence districts, `Colombo` (0.5%) and `Kandy` (1.4%).

**Deep Dive — exactly which weeks needed imputation, if asked to be specific:** four weeks were
missing for **all 25 districts simultaneously** — `2015 Wk30`, `2020 Wk1`, `2021 Wk42`,
`2022 Wk43` (likely a single nationwide source-website outage, not a per-district data problem) —
plus one extra gap each for `Ampara` and for `Kilinochchi`/`Mullaitivu` (moot once the week-53
merge applies), and three extra gaps for `Kalmunai` (folded into the Ampara merge). 104
district-week rows total, under 0.5% of the ~25,350-row dataset.

**Deep Dive — the population-interpolation limitation, with the real numbers behind it:**

| District | 2001 | 2012 | 2024 | 2001→2012 | 2012→2024 |
|---|---:|---:|---:|---:|---:|
| Kilinochchi | 127,263 | 113,510 | 136,710 | −10.8% | +20.4% |
| Mullaitivu | 121,667 | 92,238 | 122,619 | −24.2% | +32.9% |
| Mannar | 151,577 | 99,570 | 123,756 | −34.3% | +24.3% |

This dip-then-recovery pattern is consistent with the final phase of the Sri Lankan civil war
(concentrated in these Vanni-region districts, ending May 2009) — straight-line interpolation
between 2001 and 2012 cannot recover the true wartime population path, which is why
`cases_per_100k` for these three districts in that period carries an explicit caveat rather than
being treated as precise.

**Deep Dive — a small, still-open data quirk worth knowing about (Open Question #11):** the raw
weather CSVs are not consistently date-formatted across districts — `Colombo`'s file alone uses
M/D/Y while the others use a different convention. This hasn't been shown to cause a downstream
error, but it's flagged as an open item rather than silently trusted.

**What else could be done (an honest answer if asked "how would you improve the dataset with more
resources"):** climate is single-point-per-district, a genuine Open-Meteo constraint — a finer
spatial grid (multiple stations per district, spatially interpolated) would reduce this if such
data became available. Case counts are also only available at weekly, district-aggregate
resolution from the MoH source; daily or facility-level data, if ever released, would let both
Module 1 and Module 2 operate at finer temporal resolution, at the cost of a much heavier
data-cleaning burden than the one already documented here.

---

## Session 3 — Methodology and Why It Was Chosen (evaluation point: "Suitable methodology,
alternatives considered")

**Read:** `RESEARCH_DECISIONS.md` Decisions 001, 002, 009, 010, 014; `MODULE_CONTEXT.md`
"Validation Strategy" and "Five design decisions approved before implementation"

**In plain words:** Two ideas carry this whole session, and both have everyday analogies:

1. **Leakage** (letting a model see information it shouldn't have yet) is like studying for an
   exam with the answer key already in your hand — you'll look brilliant on that one exam, but
   you haven't actually learned anything, and you'll fail a genuinely new question.
2. **Walk-forward validation with a locked-away final test** is like practicing on last year's
   and the year before's exam papers, always practicing only on *older* papers, and keeping this
   year's real, brand-new final exam sealed in an envelope until the very end — you only open it
   once, for the real grade.

Every methodology choice below exists to avoid leakage or to test the design honestly, rather
than to make the numbers look better.

This is the session evaluators will spend the most time on, because "suitable and justified
methodology, alternatives and approvals considered" is a named rubric point and Module 1 has an
unusually rich paper trail for it. Learn the **reasoning**, not just the final design — every
one of these was a considered choice with a rejected alternative.

| Design choice | Alternative considered | Why rejected |
|---|---|---|
| SARIMA, climate-free (Decision 001) | SARIMAX with climate built in | Baseline would absorb climate signal, weakening the residual Stage 2 needs |
| One SARIMA per district (Decision 002) | One pooled national SARIMA | Dengue dynamics differ by district; pooling would hide/fabricate district-specific seasonality |
| Walk-forward validation + untouched 104-week holdout (Decision 009) | Single static train/test split | Unreliable estimate over a ~19-year series; a static split is a known "unrealistic split" risk |
| Stage 2 trained only on out-of-sample residuals (Decision 010) | In-sample fitted residuals | In-sample residuals understate real error, which would inflate the apparent benefit of compensation — a leakage risk specific to this two-stage design |
| Pooled Stage 2 (one XGBoost, `District` as a feature) (Decision 014, later re-tested directly, Decision 045/M1-021) | 25 independent per-district XGBoost models | **Actually tested, not assumed**: per-district was decisively worse (validation MASE +28.4%, only 4/25 districts improved) |
| `reg:absoluteerror` (MAE) loss (Decision 014) | Standard `reg:squarederror` | Squared error let one district's (Vavuniya) catastrophic SARIMA divergence corrupt every other district's correction in the pooled model |
| Non-seasonal SARIMA left as-is for 18/25 districts (Open Question #12) | Force seasonal differencing (`D=1`) | Computationally infeasible at scale (7+ min/fit vs ~0.01s); **and** the pre-registered diagnostic showed non-seasonal districts benefit *more* from Stage 2, so there was no evidence reworking Stage 1 would help the combined pipeline |

**Two of these rows deserve a plain-language example each, since they're the ones most likely to
get a follow-up question:**

- **Pooled vs. per-district (Stage 2):** "pooled" means one XGBoost model is trained on all 25
  districts' data together (with a `District` label so it can still tell them apart), like one
  recipe used by 25 different cooks who each add their own name tag. "Per-district" means each
  district gets its own separate, independently-trained model — 25 completely separate recipes.
  The team actually tried both and measured which was better, rather than assuming — pooled won
  clearly.
- **MAE loss vs. squared-error loss:** one district (Vavuniya) had a SARIMA forecast that went
  wildly wrong in one time period (predicting ~30 million cases against an actual ~6). Squared
  error loss punishes big mistakes *extremely* hard, so this one enormous, freak mistake dragged
  the *whole* pooled model's training off course for every other district too — like one
  extremely loud kid in a classroom shouting so loud that the teacher ends up planning the entire
  lesson around that one kid, ignoring everyone else who was doing fine. Switching to MAE loss
  (which treats every mistake's size more evenly, big or small) fixed this.

**The core methodological argument you must be able to defend, unprompted:**
> "Every major design choice in Module 1 was either derived from a specific, named risk
> (leakage, an unrealistic split, pooling structure) or later verified by directly testing the
> alternative rather than assuming it. We didn't just pick SARIMA→XGBoost and stop — we ran six
> further ablations after the pipeline was working (hyperparameter search, per-district models,
> STL+SARIMA, warm-starting, refit cadence, extra residual lags) specifically to check whether
> the accepted design still held up, and it did."

**Must be able to say (on validation protocol specifically):**
> "We reserve the final 104 weeks (2 years) per district as a holdout, touched only once for
> final reporting. Everything else — SARIMA order selection, XGBoost training — uses 14
> expanding-window walk-forward folds, so every fold's model only ever sees data from before
> that fold's window. Stage 2 always trains on genuinely out-of-sample SARIMA residuals, never
> in-sample ones, because in-sample residuals would make the compensation look better than it
> really is."

**Self-check:**
- Q: A skeptical evaluator says "isn't 25 separate SARIMA models just more parameters to
  overfit with?" How do you respond?
- A: Per-district SARIMA fits are not arbitrary flexibility — each is walk-forward validated on
  its own history and scored against its own untouched holdout, so overfitting would show up as
  poor holdout performance for that district, which is reported honestly (e.g. Kilinochchi and
  Mannar *do* get worse on holdout — see Session 6). The alternative (one pooled SARIMA) was
  reasoned to be worse, not tested directly like Stage 2's pooling question was — that is an
  honest asymmetry in how deep the two decisions were checked, worth stating plainly rather than
  overclaiming.

**Deep Dive — four more decisions with the same "alternative considered, why rejected" shape,
useful ammunition for "what else could you have done" follow-ups:**

| Design choice | Alternative considered | Why rejected |
|---|---|---|
| Population as a reporting-layer denominator only, `cases_per_100k` alongside raw counts (Decision 006) | Change the modeling target itself to incidence per 100k | Would cascade into Module 2/3's label definitions and reopen Decisions 001/002; kept additive instead |
| Merge Kalmunai into Ampara (Decision 012) | Drop Kalmunai entirely, or model it as its own 26th district | Dropping would discard a real ~19-year, ~17,500-case history; modeling it separately is impossible since it has no matching Open-Meteo weather station |
| `residual_lag_1/2` built via full-calendar reindex + shift (Decision 015) | A naive `.shift()` directly on the sparse validation+holdout rows | Would silently treat fold 14's last residual as "1 week ago" for the holdout block's first row, when it is actually ~26 weeks stale — a real, previously-undocumented gap between the last walk-forward fold and the holdout start |
| `is_reporting_anomaly` heuristic flag: ≥75% case drop after ≥100 prior-week cases, followed by ≥2.5× rebound (Decision 028) | Trust the raw case counts as-is, with no anomaly flag | The 2026 Colombo/Gampaha Wk24→Wk25 pattern (507→20→1,138) looks like delayed-reporting catch-up, not a genuine epidemiological collapse-then-explosion; left unflagged, the case-lag features would "learn" from what is really a data artifact |

**Deep Dive — the honest, prepared answer to "what else could you have tried" (not a deflection):**
Only SARIMA and XGBoost were used as the two stages. Other baseline time-series models exist
(Prophet, exponential smoothing state-space models, TBATS for multiple seasonality) and other
correction-model families exist (LightGBM, CatBoost, a small LSTM/GRU) — none were benchmarked
against SARIMA/XGBoost. That is a deliberate scope decision, not an oversight: the research
question was "does a two-stage residual-compensation architecture help," not "which exact model
pair is globally optimal." The correct, honest answer if asked directly: "testing whether the
architecture generalizes across different baseline/correction model choices is legitimate future
work, but it wasn't necessary to answer this project's specific research question — and every
model-selection question this project *did* ask (pooled vs. per-district, MAE vs. squared loss,
hyperparameter tuning) was tested empirically, not assumed," the same honesty pattern as Session
7's ablation arc.

---

## Session 4 — Feature Engineering (evaluation point: "Feature engineering")

**Read:** `FEATURE_ENGINEERING_SPEC.md` (Module 1 sections only, down to "Excluded Feature:
weather_code"), `RESEARCH_DECISIONS.md` Decisions 003, 008, 015

**In plain words:** "Features" are just the extra clues we hand to the second helper (XGBoost)
so it can figure out where SARIMA's simple guess went wrong. Think of it like a detective: raw
case numbers alone are like only knowing "the crime happened Tuesday." Adding rainfall, how
unusual that rainfall was, the season, and how wrong last week's guess was, gives the detective
much more to work with.

Learn the six feature groups **by purpose**, not just by name — evaluators will ask "why does
this feature exist" more than "list the features":

| Group | Features | What it captures | Leakage-safety note |
|---|---|---|---|
| 1. Case-trend | `cases_lag_1..4`, rolling mean/std (4w), rate of change | Short-term momentum/volatility SARIMA may underrepresent during nonlinear outbreak growth | Fold-agnostic (pure shifts of past values); masked to `NaN` where `is_imputed`/`is_reporting_anomaly` |
| 2. Lagged climate | rainfall lag 2–8w, temperature/humidity lag 1–4w | Delayed causal chain: mosquito breeding cycle + extrinsic incubation period means today's climate drives cases weeks later | Fold-agnostic |
| 3. Climate anomalies | rainfall/temperature/humidity anomaly | Deviation from the *expected* value for that district-week — more aligned with "unusual" conditions than raw seasonal climate | **Fold-aware** — long-term mean recomputed per walk-forward fold from training data only, never globally (this is the single most leakage-sensitive feature group; know it cold) |
| 4. Seasonal/contextual | `sin_week`, `cos_week`, monsoon SW/NE indicators | Annual cycle and monsoon timing, encoded cyclically so week 52 and week 1 are "close" | Fold-agnostic; depends on the week-53 merge (Decision 007) to keep the period fixed |
| 5. Residual-specific | `sarima_prediction`, `residual_lag_1/2` | Lets Stage 2 learn that Stage 1's *own error* is autocorrelated | Built via full-calendar reindex + shift (Decision 015) — not a naive shift, because of a real ~26-week gap between the last walk-forward fold and the holdout block |
| 5b. Pooled-model support | `District` | Lets one pooled model still distinguish district-specific error behavior | Required by the pooling decision (014), not part of the original spec |
| 6. Reporting-delay state (M1-006B) | `weeks_since_reporting_anomaly`, `reporting_rebound_ratio_lag1`, `suspected_backfill_week` | Encodes suspected reporting catch-up dynamics so Stage 2 can discount untrustworthy recent lags | Added later after a real leakage/data-quality finding (Session 8) |

**Simple examples for the two trickiest ideas here:**

- **Lag feature (Group 1/2):** a "lag 1" feature just means "last week's value." If this week's
  rainfall lag_2 is high, that's just saying "it rained a lot 2 weeks ago" — simple, and safe,
  because it's already-known history.
- **Climate anomaly (Group 3), and why it needs special care:** an "anomaly" isn't "how much rain
  fell" — it's "how much MORE or LESS rain fell than what's *normal* for this district in this
  week of the year." To know what's "normal," you need an average computed from past years. The
  danger: if you calculate that average using years the model hasn't reached yet in a given
  practice round, you're accidentally letting it peek into the future — like calculating "the
  normal temperature for March" using data from a March that hasn't happened yet in your
  practice timeline. So this average is always recalculated fresh, using only the years available
  up to that point.

**Why `precipitation_sum` and not `rain_sum`:** `precipitation_sum = rain_sum + showers_sum +
snowfall_sum`. Sri Lanka's monsoon rainfall is heavily convective-shower-driven, so `rain_sum`
alone would systematically undercount real water input relevant to mosquito breeding (Decision
008).

**Why `weather_code` is excluded:** categorical, largely redundant with the continuous
rainfall/temperature/humidity variables already used, which are more physically precise for
dengue transmission drivers (Decision 008). Flagged as a possible future ablation
(`thunderstorm_day_count`), not built.

**The single most important leakage-safety idea to be able to explain clearly:**
> "Climate anomalies can't be computed once over the whole dataset, because the 'long-term
> average' for a district-week would then include years the model hasn't reached yet in a given
> walk-forward fold — that's future information leaking backward. So the anomaly's baseline
> average is recomputed inside every fold, using only that fold's own training window. Plain
> lag features don't have this problem because they're just a shift of an already-observed
> value — a genuinely different leakage-safety category, and knowing which group needs which
> treatment is itself part of the contribution."

**Self-check:**
- Q: Why is `residual_lag_1` the single most important Stage 2 feature (486 total gain, by far
  the largest)?
- A: It means Stage 1's own error is autocorrelated — last week's SARIMA miss predicts this
  week's SARIMA miss. This is independently confirmed by the Ljung-Box test on Stage 1
  residuals (23/25 districts show significant autocorrelation), so the feature importance
  result and the statistical diagnostic agree with each other — not a coincidence, a consistent
  finding from two different angles.
  **Plain-words version:** if SARIMA underestimated cases last week, it will very likely
  underestimate them again this week too — the mistake has a "memory." Knowing last week's
  mistake size is one of the single best clues for guessing this week's mistake size.

**Deep Dive — the full gain-based feature ranking, not just `residual_lag_1` in isolation:**
`residual_lag_1` (486 total gain) and `residual_lag_2` (297) dominate, followed by
`rolling_mean_cases_4w` (79), `cases_lag_3` (78), `cases_lag_1` (72), `rolling_std_cases_4w` (52),
`cases_lag_4` (50), then climate-lag and seasonal features (`rainfall_lag_5`, `cos_week`,
`sarima_prediction` itself). Plain words: the model leans overwhelmingly on "how wrong was Stage 1
recently" and "what's the recent case trend," with climate and seasonality playing a real but
secondary role — an honest, checkable answer if asked "so is this really a climate-driven model?"

**Deep Dive — the exact reporting-delay feature formulas (Feature Group 6, M1-006B), in case
you're asked to define one precisely:**
- `suspected_backfill_week` = 1 if `is_reporting_anomaly` is true at week *t*, else 0.
- `weeks_since_reporting_anomaly` = weeks since the most recently flagged week (0 if week *t*
  itself is flagged; capped at 4; `NaN` if no anomaly exists yet in that district's history).
- `reporting_rebound_ratio_lag1` = `cases[t-1] / max(cases[t-2], 1)`, computed only when week
  *t-1* was itself flagged as a reporting anomaly.
- Nowcast imputation: when scoring the most recent real week, `cases_lag_1` is replaced with
  `max(cases_lag_2, rolling_mean_cases_4w)` rather than trusting a just-reported (and possibly
  still-incomplete) case count directly.

**Deep Dive — features that exist in the spec but were never built (a ready, honest answer to
"what would you add with more time"):** `fogging_indicator` (mosquito-control spraying events) and
`rainfall_temperature_interaction` are both listed in `FEATURE_ENGINEERING_SPEC.md` as optional
features, explicitly gated on "only if data quality and availability support them" — not built
because no reliable fogging-schedule dataset exists, not because they were judged unhelpful.
Separately, Decision 008 names a derived `thunderstorm_day_count` feature (built from the excluded
`weather_code` column) as a specific future ablation candidate. These three are concrete, sourced
answers, not generic hand-waving.

---

## Session 5 — Code Walkthrough (evaluation point: "Code explanation")

**Read:** `MODULE_CONTEXT.md` "Implementation Plan" + "Implementation Status" sections. Then
open the actual files listed below in the repo and skim their docstrings/top-level structure —
you do not need to memorize implementation lines, but you must be able to say what each file's
job is and in what order they run.

**In plain words:** Think of this as an assembly line. Raw data comes in one end; a finished
forecast comes out the other. Each numbered step below is one station on the line, and each
station only does its own job before passing the work to the next station.

**Pipeline order** (this is what `main.py` orchestrates, idempotently — each stage skipped if
its output already exists, `--force` reruns, `--stages` runs a subset):

```text
1. src/config.py                        District list, monsoon week constants, paths
2. src/preprocessing/shared.py          Module-agnostic: Kalmunai→Ampara merge, epi-week
                                         calendar, climate weekly aggregation, population
3. src/preprocessing/module1_preprocessing.py
                                         Module-specific: week-53 merge, missing-week
                                         imputation + is_imputed flag, merge climate/
                                         population, cases_per_100k
4. src/module1_forecasting/validation.py
                                         Walk-forward fold generator (14 folds + holdout),
                                         enforces the no-leakage rule structurally
5. src/module1_forecasting/feature_engineering.py
                                         Builds Stage 2's feature table; separates
                                         fold-agnostic features (safe globally) from
                                         fold-aware ones (must be recomputed per fold)
6. src/module1_forecasting/baseline_sarima.py
                                         Stage 1: per-district auto_arima order search,
                                         per-fold refit + forecast, AR-root stability guard
7. src/module1_forecasting/compensation_model.py
                                         Stage 2: pooled XGBoost per fold, MAE loss,
                                         residual-lag construction
8. src/module1_forecasting/combine.py   final_prediction = sarima_prediction +
                                         predicted_residual (0-floor clipped); metrics
9. src/module1_forecasting/evaluate.py  RMSE/MAE/sMAPE/MASE, Diebold-Mariano test,
                                         residual variance reduction, Ljung-Box
10. src/module1_forecasting/forecast_future.py / rolling_one_step.py
                                         Separate, clearly-labeled forward/nowcast paths
                                         — NOT part of the validated backtest (see Session 8)
```

**Why the shared-vs-module-specific split matters (Decision 013):** a transformation belongs in
`shared.py` only if *every* module would make the same choice for the same reason (e.g. fixing
a data-entry error). The week-53 merge, `weather_code` exclusion, and missing-week imputation
were originally implemented as if they were shared, general-purpose fixes — but they actually
exist to satisfy **SARIMA's specific assumptions** (fixed 52-week seasonal period). Keeping them
in `module1_preprocessing.py` instead of `shared.py` meant Module 2 could later make its own,
different choice (it kept week 53 unmerged — Decision 020) without inheriting Module 1's
modeling-specific decision by accident. (Plain words: it's like a shared kitchen where every
chef washes and chops the same base vegetables together — but one chef's habit of always
removing the seeds, which only matters for *their* recipe, should stay in *their* own station,
not become something every other chef is forced to do too without being asked.)

**Must be able to say:**
> "The codebase separates a shared preprocessing layer, used identically by all three modules,
> from each module's own preprocessing and feature engineering. This isn't just tidiness — it
> came from catching a real mistake, where SARIMA-specific fixes had been implemented as if they
> were general-purpose, which would have silently imposed Module 1's assumptions on Module 2 and
> 3 before their own designs were even finalized."

**Self-check:**
- Q: If asked to point at "the leakage guard" in the code, what do you name?
- A: `validation.py`'s `fit_window()` (only exposes data up to a fold's cutoff — structurally
  hard to misuse), and `feature_engineering.py`'s `compute_fold_climate_anomalies(df,
  train_mask)`, which is deliberately never written to a single global file for exactly this
  reason.

**Deep Dive — five extra implementation decisions worth knowing (`MODULE_CONTEXT.md` "Stage 1
Implementation Status"):**
1. SARIMA's *order* search (`auto_arima`) runs once per district on the full pre-holdout history,
   not refit per walk-forward fold — benchmarked as computationally infeasible per fold (7+
   minutes per fit at full search depth). Only the order is fixed this way; every fold still
   refits the model's *parameters* fresh on that fold's own training window.
2. Forecasts are clipped to a 0 floor for both the `raw` and `log1p` transform candidates — case
   counts cannot be negative.
3. `enforce_stationarity=False, enforce_invertibility=False` lets `auto_arima` search freely, with
   Decision 017's AR-root guard added afterward specifically to catch when this freedom produces
   an explosive, non-stationary fit.
4. MASE (against a seasonal-naive m=52 benchmark) is the deciding metric for order/transform
   selection, not AIC alone.
5. The holdout block is forecast and scored exactly once, using the already-finalized
   per-district configuration — nothing about the holdout numbers ever fed back into order or
   transform selection.

**Deep Dive — the standalone scripts, and exactly what question each one answers (useful if asked
"is this used in production or just for the report"):**
- `rolling_one_step.py` — "if we refit SARIMA every single week on all data strictly before that
  week, then forecast just one week ahead, how accurate are we in practice?" (Decision 029) — the
  evaluation mode closest to genuine weekly production deployment.
- `forecast_future.py`'s `run_nowcast()` — the actual "predict next week" production output, using
  vintage-ensembled SARIMA (Decision 040) rather than a single fit.
- `nowcast_tracking.py` — permanent infrastructure (Decision 041) that logs every nowcast
  prediction and later reconciles it against the real reported case count once that week's data
  arrives, so the nowcast's real-world accuracy is tracked honestly over time, not just assumed.

---

## Session 6 — Results and How to Interpret Them (evaluation point: "Output/results
explanation")

**Read:** `MODULE_CONTEXT.md` "Stage 1 Implementation Status" and "Stage 2 Implementation
Status" (per-district tables), `QUESTIONS_FOR_DEFENSE.md` "Why does Stage 1 SARIMA often have no
seasonal component"

**In plain words, what the metrics mean before you look at the numbers:**

- **MASE** compares your forecast's mistake size to the mistake size of the simplest possible
  guess (just repeating last week's number forward). A MASE around 1 means "about as good as
  that trivial guess"; well below 1 means "clearly better than it." Lower is better.
- **The DM test** answers "is Model B *reliably* better than Model A, or could this difference
  just be luck/noise?" — a statistical fairness check, not just eyeballing which number is
  smaller.
- **The Ljung-Box test** answers "are there still hidden, repeating patterns left in our
  mistakes, or do our mistakes now look like plain random noise?" If a pattern is still there, it
  means there's more the model *could* have learned but didn't yet.

**Headline numbers you must know exactly (holdout is the validated number to lead with):**

| Metric | Stage 1 only | Stage 1 + Stage 2 |
|---|---|---|
| Median validation-aggregate MASE | 0.967 | 0.590 (**39.0%** reduction) |
| Median holdout MASE | 0.622 | 0.375 (**39.7%** reduction) |
| Districts improving on validation MASE | — | **25/25** |
| Districts improving on holdout MASE | — | **23/25** (Kilinochchi, Mannar worsen, not significantly) |
| DM test significant, validation+holdout scope | — | 14/25 districts |
| DM test significant, holdout-only scope (stricter) | — | 5/25 districts |
| Residual variance reduction positive | — | 22/25 districts (up to 81% for Trincomalee) |
| Ljung-Box still significant post-Stage-2 (lag 26) | 23/25 (pre) | **23/25 still significant** — Stage 2 reduces error *magnitude*, does not fully remove autocorrelated structure |

**How to talk about this without overclaiming:**
- Lead with: "residual compensation improved forecast accuracy for all 25 districts on the
  validation-aggregate metric, and for 23 of 25 on the untouched holdout block, with a median
  ~40% MASE reduction."
- If pressed on statistical significance: be honest that the DM test only reaches `p<0.05` for
  a minority of districts at the strictest (holdout-only) scope — this is **expected**, not a
  weakness to hide, given per-district holdout sample size is only 104 observations. Frame it as
  "directionally consistent, not universally significant at this sample size" — this is a
  correct academic framing, not a hedge. (Plain words: with only 104 data points per district,
  it's hard for a statistical test to be fully confident even when the improvement is real and
  consistent in direction — like being fairly sure a coin is weighted after 104 flips, but not
  yet "beyond all doubt" sure.)
- If pressed on the residual autocorrelation surviving Stage 2: this is a genuine, honestly
  reported limitation — Stage 2 reduces the *size* of errors substantially but does not fully
  "whiten" them; real structure likely remains for a different Stage 2 architecture or more
  residual lags to capture (the latter was tried and rejected, Decision 033 — see Session 7).

**Must be able to say (the "so what" of the result):**
> "The result supports the residual-compensation hypothesis: a deliberately simple, univariate
> SARIMA baseline leaves structured, learnable error, and a climate-aware XGBoost correction
> captures a meaningful share of it — median MASE improved by about 40% on data the model never
> saw during selection. It does not fully solve forecasting — real autocorrelated structure
> remains in most districts — which is an honest, expected outcome, not a failure of the
> design."

**Self-check:**
- Q: Two districts (Kilinochchi, Mannar) get *worse* on holdout. Doesn't that undermine the
  claim?
- A: No — it is disclosed, not hidden, and neither regression is statistically significant
  (`p ≈ 0.33–0.40`). More importantly, this is exactly the kind of honest per-district reporting
  the DM test and residual-variance-reduction metrics were added specifically to surface
  (Decision 016) — a single aggregate number would have hidden this; per-district reporting
  didn't.

**Deep Dive — the full Stage 1 per-district table, for when an evaluator names a specific
district (`MODULE_CONTEXT.md` "Stage 1 Implementation Status"):**

| District | Transform | Order | Seasonal Order | Validation MASE | Holdout MASE |
|---|---|---|---|---|---|
| Ampara | log1p | (0,1,1) | (0,0,0,52) | 0.97 | 0.43 |
| Anuradhapura | log1p | (0,1,2) | (1,0,0,52) | 0.79 | 0.53 |
| Badulla | raw | (1,1,1) | (1,0,0,52) | 1.36 | 0.55 |
| Batticaloa | log1p | (0,1,1) | (0,0,0,52) | 1.92 | 0.59 |
| Colombo | log1p | (1,1,1) | (0,0,0,52) | 1.63 | 0.65 |
| Galle | log1p | (0,1,1) | (0,0,0,52) | 1.21 | 1.17 |
| Gampaha | raw | (2,1,0) | (0,0,0,52) | 1.05 | 0.74 |
| Hambantota | raw | (0,1,1) | (0,0,0,52) | 0.96 | 0.95 |
| Jaffna | raw | (2,1,2) | (1,0,0,52) | 2.22 | 0.32 |
| Kalutara | log1p | (2,1,1) | (0,0,0,52) | 1.42 | 0.66 |
| Kandy | log1p | (0,1,1) | (0,0,0,52) | 1.27 | 0.43 |
| Kegalle | raw | (0,1,2) | (0,0,0,52) | 0.59 | 0.33 |
| Kilinochchi | log1p | (0,1,1) | (1,0,0,52) | 1.45 | 2.15 |
| Kurunegala | log1p | (1,1,1) | (0,0,0,52) | 0.86 | 0.38 |
| Mannar | raw | (0,0,0) | (1,0,0,52) | 0.81 | 1.12 |
| Matale | log1p | (1,1,2) | (0,0,0,52) | 0.84 | 1.28 |
| Matara | log1p | (2,1,2) | (0,0,0,52) | 0.94 | 1.45 |
| Monaragala | log1p | (1,1,2) | (1,0,0,52) | 0.63 | 0.62 |
| Mullaitivu | log1p | (0,1,1) | (0,0,0,52) | 2.92 | 0.53 |
| Nuwara Eliya | log1p | (0,1,2) | (0,0,0,52) | 0.93 | 1.37 |
| Polonnaruwa | log1p | (1,1,2) | (1,0,0,52) | 1.04 | 0.78 |
| Puttalam | log1p | (0,1,1) | (0,0,0,52) | 0.89 | 0.31 |
| Ratnapura | raw | (2,1,0) | (0,0,0,52) | 0.90 | 1.11 |
| Trincomalee | log1p | (0,1,2) | (0,0,0,52) | 1.04 | 0.41 |
| Vavuniya | raw | (1,0,2) | (0,0,0,52) | 0.37 | 0.42 |

Summary: 17/25 use `log1p`, 8 use raw counts; 13/25 beat seasonal-naive on validation, 18/25 do on
holdout; **18/25 selected configs have no seasonal component at all** despite `m=52` — this is the
"Supervisor Flag" behind Session 8: Stage 1 is a deliberately simple baseline, not the paper's
main contribution.

**Deep Dive — the full Stage 2 per-district table (post-Decision-017 fix), including the two
districts that get worse:**

| District | Val MASE (S1) | Val MASE (S1+S2) | Val % improvement | Holdout MASE (S1) | Holdout MASE (S1+S2) | Holdout % improvement |
|---|---|---|---|---|---|---|
| Ampara | 0.97 | 0.62 | 35.7% | 0.43 | 0.27 | 36.3% |
| Anuradhapura | 0.79 | 0.46 | 42.0% | 0.53 | 0.38 | 28.7% |
| Badulla | 1.36 | 0.72 | 46.6% | 0.55 | 0.33 | 39.5% |
| Batticaloa | 1.92 | 0.66 | 65.5% | 0.59 | 0.25 | 56.9% |
| Colombo | 1.63 | 0.84 | 48.2% | 0.65 | 0.32 | 50.6% |
| Galle | 1.21 | 0.64 | 46.6% | 1.17 | 0.51 | 56.1% |
| Gampaha | 1.05 | 0.63 | 40.6% | 0.74 | 0.35 | 52.1% |
| Hambantota | 0.96 | 0.50 | 48.1% | 0.95 | 0.50 | 47.5% |
| Jaffna | 2.22 | 0.79 | 64.3% | 0.32 | 0.16 | 48.9% |
| Kalutara | 1.42 | 0.78 | 44.9% | 0.66 | 0.45 | 32.7% |
| Kandy | 1.27 | 0.58 | 54.3% | 0.43 | 0.29 | 31.2% |
| Kegalle | 0.59 | 0.39 | 34.0% | 0.33 | 0.26 | 22.1% |
| Kilinochchi | 1.45 | 1.37 | 5.3% | 2.15 | 2.41 | **-11.7%** |
| Kurunegala | 0.86 | 0.35 | 59.0% | 0.38 | 0.27 | 28.5% |
| Mannar | 0.81 | 0.61 | 24.4% | 1.12 | 1.15 | **-3.0%** |
| Matale | 0.84 | 0.42 | 50.3% | 1.28 | 1.02 | 20.5% |
| Matara | 0.94 | 0.39 | 59.1% | 1.45 | 0.62 | 57.0% |
| Monaragala | 0.63 | 0.54 | 14.6% | 0.62 | 0.51 | 17.5% |
| Mullaitivu | 2.92 | 2.42 | 17.1% | 0.53 | 0.45 | 16.2% |
| Nuwara Eliya | 0.93 | 0.59 | 36.9% | 1.37 | 1.02 | 25.4% |
| Polonnaruwa | 1.04 | 0.71 | 31.9% | 0.78 | 0.58 | 26.2% |
| Puttalam | 0.89 | 0.52 | 40.9% | 0.31 | 0.18 | 41.9% |
| Ratnapura | 0.90 | 0.51 | 43.5% | 1.11 | 0.48 | 57.0% |
| Trincomalee | 1.04 | 0.57 | 44.9% | 0.41 | 0.19 | 53.6% |
| Vavuniya | 0.37 | 0.29 | 23.7% | 0.42 | 0.37 | 10.3% |

**Deep Dive — real-world sanity check for the two districts an evaluator is most likely to name,
since they had the real 2026 outbreak:**

| Mode | Colombo Wk22–23 sMAPE | Gampaha Wk22–23 sMAPE | Wk25 (actual → predicted) |
|---|---|---|---|
| Flat 104-week holdout | 21.5% | 19.8% | 1,138→246 / 1,294→153 |
| Rolling 1-step (Decision 029) | **13.4%** | **13.1%** | 1,138→121 / 1,294→95 |

Neither mode caught the acute Wk25 spike itself (both were fooled by the Wk24 reporting-dip
artifact — see Session 8), but rolling evaluation is honestly closer for the weeks leading up to
it.

**Deep Dive — where the real evidence lives on disk, if asked to show it live:**
- `outputs/metrics/module1/sarima_walk_forward_metrics.csv`, `combined_vs_baseline_metrics.csv`,
  `diebold_mariano_results.csv`, `xgboost_feature_importance.csv` — the core production tables
  behind every number in this session.
- `outputs/figures/module1/acf_residuals_final_{Colombo,Kandy,Kilinochchi,Mullaitivu}.png` — the
  autocorrelation plots behind the Ljung-Box claim (a representative sample across
  seasonal/non-seasonal and best/worst-performing districts, not all 25).
- `outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png` — the 8-week forward forecast
  plots referenced in Decision 018.

---

## Session 7 — The Rigor Story: Six Rejected Ablations (this is Module 1's strongest asset for
"alternatives and approvals considered")

**Read:** `MODULE_CONTEXT.md` "Investigation Summary: Module 1 Remediation Arc",
`QUESTIONS_FOR_DEFENSE.md` "After all this investigation, is Module 1's forecasting accuracy
actually better than before?"

**In plain words:** "Ablation" just means "try removing or changing one thing and see if it
actually helps." Think of an athlete who already has a good training routine, then tests eight
different tweaks (a new diet, a different warm-up, sleeping more, etc.) one at a time to see if
any of them genuinely improve race times — most tweaks won't help, and that's a useful result
too, because it proves the original routine wasn't left unexamined.

After the core pipeline was built and validated, the team ran **15 further experiments (M1-007
through M1-021) across 25 decisions**, specifically to stress-test whether the accepted design
still held up against plausible alternatives. This is unusually strong evidence for the
"alternatives and approvals considered" rubric point — most student projects don't do this.
Know the shape of the argument, not just the list:

**What was tried and rejected (each holdout- or safeguard-gated, not just eyeballed):**

| Tried | Result |
|---|---|
| Extra residual lags (`residual_lag_3/4` + EWMA) | Validation improved, **holdout regressed** — rejected |
| STL+SARIMA on 3 non-seasonal districts | 0/3 beat existing SARIMA on validation |
| SARIMA warm-starting | No effect on predictions, 5–10× slower |
| Less-frequent SARIMA refit | No stability gain despite being cheaper |
| Robust ensemble aggregation (median/trimmed-mean) | No improvement over plain mean |
| Real-time reporting-catch-up-spike adjustment | Only 42.9% precision overall (worse for Colombo/Gampaha specifically) — ruled out |
| 40-candidate XGBoost hyperparameter search | Best candidate beat baseline on **every validation-fold safeguard**, then **failed the one-time holdout check** (+3.6% worse) |
| Per-district Stage 2 (vs. pooled) | Decisively worse (+28.4% validation MASE) — directly confirmed the original pooling decision |

**The one thing that *was* accepted:** vintage-ensembled SARIMA for the production **nowcast**
(predict-next-week) — averaging the current week's SARIMA fit with the last 3 weeks' own
independently-fitted forecasts for the same target week. This is a different evidence tier from
the headline holdout MASE (Session 6) — it improves the *operational, real-time* next-week
prediction, not the backtested 104-week holdout number, which is unchanged at 0.374. (Plain
words: instead of trusting only this week's single forecast, we also look back at what the last
3 weeks' own forecasts *said this same target week would be*, and average all of them — several
independent opinions averaged together, rather than trusting one.)

**Must be able to say — this is arguably the single most defense-ready sentence in the whole
module:**
> "The hyperparameter search result is the clearest demonstration of why our holdout discipline
> matters: a configuration that beat production across every one of 13 validation folds still
> regressed on the untouched holdout block. If we had picked hyperparameters by validation
> performance alone, we would have shipped a worse model. That's not a hypothetical justification
> for the holdout rule — it's a documented case of the rule catching a real mistake before it
> happened."
> (Plain words: it's like a student who aces every single practice test but then does worse on
> the real final exam — proof that "acing practice" alone isn't enough evidence to trust, which
> is exactly why the real final exam is kept sealed and separate.)

**Self-check:**
- Q: If nothing structural improved after 15 experiments, was this wasted effort?
- A: No — this is explicitly framed (correctly) as a stress-test, not a search for a headline
  number. A stable result under six independent rejected alternatives is itself evidence the
  original design was well-chosen, and the one real win found (the nowcast ensemble) came out of
  the same process. Reporting negative results honestly, with the safeguard that rejected them,
  is stronger evidence of rigor than silently not trying them.

**Deep Dive — the complete M1-007 through M1-021 arc, experiment by experiment (the table above is
the compressed version — this is the full list, useful if an evaluator names a specific
experiment):**

| ID | What was tested | Result | Verdict |
|---|---|---|---|
| M1-007 | Extra residual lags (`residual_lag_3/4` + EWMA) | Validation MASE improved 0.651→0.597, but holdout regressed 0.374→0.395 | Rejected |
| M1-008 | Full 25-district rolling-mode DM test | Only 2/25 significant (`Ratnapura`, `Badulla`), both *worse* — but not a fair replication (different SARIMA refit regime) | Reported, not acted on |
| M1-009 | Per-district Stage 2 shrinkage weight | `Monaragala` and `Vavuniya` improved (holdout 0.513→0.505, 0.365→0.359); `Kilinochchi`/`Mannar` not selected | Partial adopt |
| M1-010 | Genuine next-week nowcast + bug fix | Found and fixed a silent bug where every forecast since the M1-006B promotion had been failing | Kept as new deliverable |
| M1-011 | Root-cause the rolling-mode DM gap | Weekly-refit vs. fold-refit SARIMA predictions barely correlated (mean r=0.13) | Root cause documented |
| M1-012 | STL+ARIMA pilot on 3 non-seasonal districts | 0/3 beat existing SARIMA on validation | Rejected |
| M1-013 | SARIMA warm-starting | Predictions virtually identical, but 5–10× slower | Rejected |
| M1-014 | Less-frequent SARIMA refit (every 4 weeks) | ~4× cheaper, no stability gain | Rejected |
| M1-015 | Vintage-ensembled SARIMA (rolling mode) | Stage-2-helps districts rose 10/25→24/25; sMAPE 58.8%→56.8% | Accepted |
| M1-016 | Promote ensembling to production nowcast | Verified exactly backward-compatible when disabled | Promoted |
| M1-017 | Prospective nowcast-accuracy tracking | Permanent logging infrastructure added | Accepted |
| M1-018 | Robust ensemble aggregation (median/trimmed-mean) | No better than plain mean (11.75 vs. 11.70 median abs. error) | Not promoted |
| M1-019 | Real-time reporting-dip detector; leakage check | 100% recall but only 42.9% precision (worse still for Colombo 46.2%, Gampaha 30.0%); leakage found but not material (0.3655 vs. 0.3741) | Rejected |
| M1-020 | 40-candidate XGBoost hyperparameter search | Best candidate beat baseline on every validation safeguard, then regressed on holdout (+3.6%) | Rejected |
| M1-021 | Per-district Stage 2 vs. pooled | Decisively worse (+28.4% validation MASE), only 4/25 districts improved | Rejected |

**Deep Dive — "what else could still be done" (the direct, evidence-based answer to "what would
you try next," beyond the one line already in Session 9):**
1. **Option B from M1-019** (not built): attach a "possible reporting dip" uncertainty flag to the
   nowcast output itself, rather than auto-correcting the case count in real time (which was tried
   and rejected for poor precision).
2. **Targeted, non-shrinkage Stage 2 changes** for the specific districts pooling is known to
   underperform (`Mannar`, `Vavuniya`, `Monaragala`) — shrinkage already fixed 2 of the 3
   (Decision 034); a more targeted architecture change for `Mannar` specifically was never
   attempted.
3. **Fold-specific correction for `Mannar`/`Kilinochchi`'s holdout regression** — both trace to
   specific pathological folds (e.g. `Mannar`'s explosive-AR fold 13), and a fold-aware correction
   (rather than a blanket shrinkage weight) was identified as a possible next step but not built.
4. **A different Stage 2 architecture targeting the surviving autocorrelation directly** — since
   23/25 districts still fail Ljung-Box after Stage 2, and simply adding more lags of the same
   dominant signal was tried and rejected (M1-007).

---

## Session 8 — Known Limitations and Open Questions (be ready to volunteer these calmly, not
be caught by them)

**Read:** `MODULE_CONTEXT.md` "Supervisor Flag: Non-Seasonal SARIMA", Open Questions #14–19,
`QUESTIONS_FOR_DEFENSE.md` (the two "actual-vs-predicted gap" Q&As)

**In plain words:** every real research project has weak spots. The strong move isn't hiding
them — it's being able to calmly explain *exactly* what each weak spot is, why it happened, and
what was done to check it, before anyone even asks.

| Limitation | One-line explanation | Why it's not a red flag |
|---|---|---|
| 18/25 districts have no seasonal SARIMA component despite `m=52` | AIC-driven order search chose `D=0` for all 25; forcing `D=1` is computationally infeasible at scale | Diagnostic showed non-seasonal districts benefit *more* from Stage 2 — the annual cycle Stage 1 misses is exactly what Stage 2's seasonal/climate features are designed to catch |
| Kilinochchi/Mannar get worse on holdout | Concentrated in specific pathological folds (e.g. Mannar's explosive-AR fold 13), not a general Stage 2 failure | Not statistically significant; a per-district shrinkage weight already fixed 2 *other* districts (Monaragala, Vavuniya) this way |
| 23/25 districts still fail Ljung-Box after Stage 2 | Stage 2 reduces error magnitude but doesn't fully remove autocorrelation | Extra residual lags were tried and rejected (holdout regressed) — an honestly-reported open problem, not an unexamined one |
| Shared climate pipeline lagged behind case data during the 2026 Wk25 outbreak | A real operational data-currency gap, since fixed (Decision 027) | Was found, disclosed, and fixed — a good "we monitor our own pipeline" story |
| 2026 Wk25 Colombo/Gampaha forecast error (~8-10× underestimate) | A specific, traceable reporting-delay artifact (Wk24 case counts crashed to near-zero then rebounded) poisoned the `residual_lag_1`/case-lag inputs both models trust most | You can name the exact corrupted data point and mechanism — this is a strong answer, not a shrug; a real-time fix was tried and explicitly rejected (only 42.9% precision) rather than left untested |
| Rolling one-step-ahead evaluation shows weaker Stage 2 benefit (10/25 vs 23/25 holdout) | Root-caused to weekly-refit SARIMA instability (weakly correlated with fold-refit SARIMA, r≈0.13), not a Stage 2 transferability failure | Investigated with warm-starting and refit-cadence experiments before concluding; led directly to the accepted vintage-ensemble fix |
| Forward 8-week forecasts have no ground truth | `feature_completeness_pct` (56%→44% over the horizon) is reported per row, not hidden | Explicitly kept separate from validated holdout evidence — never cited as equivalent |

**Must be able to say:**
> "We know exactly where this pipeline's weak points are, because we went looking for them
> deliberately, rather than only checking the metrics that make the headline number look good.
> Every limitation here has a named cause, and most have a tried-and-explained-why-rejected fix
> attempt behind them."

**Deep Dive — one more limitation not in the table above, worth being ready for: some districts'
validation and holdout MASE diverge sharply.** `Jaffna` scores 2.22 on the walk-forward validation
aggregate but only 0.32 on the untouched holdout; `Puttalam` similarly goes from 0.89 to 0.31 —
disclosed as Open Question #15, not hidden. Overall, 18/25 districts have holdout MASE below 1
versus only 13/25 for the validation aggregate, meaning the two evidence sources don't always tell
the same story for a given district — the honest response is to report both, not whichever one
looks better.

**Deep Dive — the exact numbers behind "root-caused to weekly-refit SARIMA instability":** mean
correlation between weekly-refit and fold-refit SARIMA predictions across districts is only
**r=0.13**, and several districts are near zero or even negative (`Kegalle` -0.14, `Gampaha`
-0.03, `Kurunegala` -0.06) — the two fitting regimes can disagree substantially even though both
are correct implementations of the same model, simply because refitting weekly on a short, noisy
series is inherently less stable than refitting on a full annual fold.

**Deep Dive — the exact precision numbers behind the rejected real-time reporting-dip fix:** the
causal (real-time-safe) detector achieved 100% recall but only 42.9% precision overall, and was
worse specifically in the two highest-volume districts an evaluator is most likely to ask about:
`Colombo` (46.2%) and `Gampaha` (30.0%) — it would have raised far more false alarms than correct
ones in exactly the districts that matter most operationally.

---

## Session 9 — Rehearsed Defense Answers

**Read:** `QUESTIONS_FOR_DEFENSE.md` in full (Module 1 relevant entries; skim the Module 2/3 ones
for cross-module questions like "why is Module 2 needed if Module 1 already forecasts cases")

Do a mock Q&A pass out loud, using the "Defense one-liner" from each relevant entry as your
opening sentence, then be ready to go one level deeper if asked to elaborate. The file already
contains fully rehearsed answers for:

- Why two stages exist; what happens to the compensation output; what if residuals are random
- Why Stage 1 often has no seasonal component
- Holdout vs. rolling/nowcast evidence tiers (do not conflate them)
- Why pooled Stage 2 beats per-district (ablation evidence)
- The reporting-anomaly leakage pathway — found, quantified, confirmed non-material
- The rejected hyperparameter search (holdout discipline demonstration)
- Whether accuracy actually improved after the whole M1-007–M1-021 arc
- The 2026 Wk25 Colombo/Gampaha forecast miss, in both technical and plain-language form
- Why Module 2 is not redundant with Module 1 (cross-module — you may get this even presenting
  only Module 1)

**Must be able to say, if asked "what would you do differently / next":**
> "A different Stage 2 architecture that targets the surviving autocorrelation directly, rather
> than more lags of the same dominant signal, is the most promising untried direction — that's
> a specific, evidence-based answer, not a generic 'more data would help'."

**Deep Dive — three more verbatim cross-module Q&As worth having ready, in case you're asked about
Modules 2/3 while presenting Module 1 (`QUESTIONS_FOR_DEFENSE.md`):**

- **"Why does Module 2 use isotonic/Platt calibration instead of a climate/residual correction
  like Module 1?"** → Module 2 *does* use climate and case history — in Stage 1. Stage 2's
  dominant error turned out to be probability miscalibration, not missing weather signal. A
  symmetric ablation (M2-008) tested adding climate to Module 2's Stage 2 and found it made things
  worse (holdout PR-AUC 0.424 vs. the climate-free version's 0.462).
- **"Do you use weather anomalies in both Module 1 and Module 2?"** → Yes, both use fold-aware
  rainfall/temperature/humidity anomalies, just at different stages: Module 1 applies them in
  Stage 2 to explain SARIMA residuals; Module 2 applies them in Stage 1 to rank outbreak risk.
- **"Does Module 3's hybrid approach actually beat a simple no-model baseline?"** → An earlier
  version of its Stage 2 model was honestly found to be *worse* than a naive persistence baseline
  on plain MAE (9.96 vs. 9.44) — before a later reformulation (modeling the *relative*, not
  absolute, residual) produced a version that beats both naive persistence and the original model
  on every metric (MAE 8.03 vs. 9.44/20.54). The same "test the trivial baseline first" discipline
  applies project-wide, not just in Module 1.

---

## Session 10 — Delivery: Slides, Timing, What to Say vs. What to Hold Back

**Read:** `PRESENTATION_MODULE1_SLIDES.md` in full, `PRESENTATION_MODULE1_COPY_PASTE.md`

Module 1's slide deck is already drafted and deliberately **presentation-safe** — it excludes
negative results from the main deck (non-seasonal SARIMA count, Kilinochchi/Mannar holdout
losses, partial DM significance, surviving Ljung-Box failures, the 2026 Wk25 miss, full
per-district tables). This is intentional slide hygiene, not concealment — **all of it must
still be ready to give verbally if the evaluator asks**, from the report / this study plan, not
volunteered unprompted on a slide.

**Recommended 6-slide sequence** (from the slide pack): gap & goal → two-stage design (Figure
6.2) → data & protocol → Stage 1/Stage 2 implementation + feature importance → results (Figure
7.2 holdout forecasts, Figure 7.3 MASE comparison, Table 7.1) → summary & contribution.

**Speaker guardrails to rehearse saying naturally, not reading:**
- Say: "Residual compensation improved MASE for all districts on validation and for the
  majority on holdout, with a median holdout improvement of about 33%."
- Avoid: naming underperforming districts unprompted, claiming universal statistical
  significance, or implying the system is deployment-ready.
- If challenged on an excluded topic (e.g. "why does Stage 1 have no seasonality for most
  districts?"), answer fully and calmly from Session 8/9 — the report and this plan already have
  the answer; do not act surprised or defensive.

**Deep Dive — the exact "excluded from slides" list, verbatim, so you know precisely what's being
deliberately held back (and must still be ready to give verbally):** the 18/25 non-seasonal SARIMA
count; the `Kilinochchi`/`Mannar` holdout worsening; the DM test's partial significance (14/25,
5/25); Ljung-Box still failing for 23/25; the `Vavuniya`/`Mannar` explosive-AR-root story; the
reporting-delay spike's unpredictability; forward forecasts having no ground truth; M1-006B's real
improvement rate (22/25, not a clean 25/25); the ACF diagnostic plots; and the full 25-district
MASE table with its two negative entries. None of this is hidden from the *evaluator* — it's held
off the *slide*, per the deck's own stated policy: "This pack includes supporting results and
design strengths only. Negative outcomes, partial failures, and methodological caveats stay in the
report and viva prep."

---

## Gap-Closing Session — Things a Thesis Supervisor Would Flag Before You Present

Acting as a critical reviewer of the *evaluation readiness*, not just the technical work, three
things stand out from `CHAPTER_STATUS.md` that are outside Module 1's technical content but
directly threaten the rubric points you listed:

1. **"Relevant background, literature, and previous systems covered?"** — Chapter 2 (Literature
   Review) is listed as **Not Started** in `CHAPTER_STATUS.md`. Module 1's own defense answers
   assume you can cite prior dengue-forecasting work (hybrid SARIMA/ML approaches, climate-driven
   dengue models) to justify the research gap. Right now only two citation placeholders exist
   (Uduwanage et al., Uelmen Jr. et al.) — this needs real literature before an evaluator asks
   "what does the existing literature say about hybrid dengue forecasting, and how does this
   differ?" and gets a placeholder answer. **Recommend prioritizing this before Module 2/3 study
   plans if evaluation is imminent** — it's a project-wide gap, not module-specific, but it will
   be asked about while you're presenting Module 1's "novelty" claim specifically (Slide M1-1).
2. **Chapter 1's Aim (1.5.1) is not finalized** — objectives (1.5.2) are drafted, but the aim
   statement itself is still pending. An evaluator asking "what exactly was your aim?" deserves a
   single crisp sentence, not an in-progress draft.
3. **No timeline/Gantt or task-distribution document was found in `research_context/`.** If
   "realistic timeline, fair task distribution, clear individual plans" is a formal rubric
   criterion, this repository currently has no artifact for it (Appendix A covers *what* each
   member contributed, retrospectively, not a *planned* timeline). Flag this to the team now —
   it's a quick document to produce but easy to be blindsided by if genuinely required.

None of these are Module 1 code/methodology weaknesses — they are report-completeness and
team-process gaps that sit alongside Module 1's technical content in the same evaluation. Worth
raising with the team before the study plan moves on to Module 2/3.

---

## Quick-Reference Cheat Sheet (for the day of the evaluation)

```text
WHAT:     SARIMA (Stage 1, climate-free, per-district) → XGBoost (Stage 2, pooled,
          MAE loss) on out-of-sample residuals.
WHY TWO STAGES: keep baseline pure so residual carries real climate/nonlinear signal.
VALIDATION: 14 walk-forward folds + untouched 104-week (2-year) holdout, per district.
HEADLINE:  25/25 districts improve validation MASE; 23/25 improve holdout MASE;
           median holdout MASE 0.622 -> 0.375 (-39.7%).
HONEST LIMITS: DM test significant for only 5/25 at strictest scope; 23/25 still
           fail Ljung-Box; Kilinochchi/Mannar worsen on holdout (not significant).
RIGOR:     6 further ablations tried after the core pipeline worked, all correctly
           rejected via holdout/safeguard gating; 1 accepted (nowcast ensembling).
DATA:      25 districts, ~19.5 years weekly cases (MoH), daily Open-Meteo climate,
           real cleaning work done (collisions, typos, date errors), imputation
           flagged and excluded from scoring, not hidden.
```

**One-paragraph plain-English summary, if you remember nothing else:**
> Every week, for each of Sri Lanka's 25 districts, we make a simple first guess at next week's
> dengue case count using only that district's own case-count history (SARIMA). Then a second
> model (XGBoost) looks at how wrong that first guess usually is, plus rainfall, temperature, the
> season, and how wrong it was *last* week, and produces a correction. Adding the correction to
> the first guess gives the final forecast. We tested this fairly — always practicing on older
> data and grading on a locked-away, never-seen block of the newest data — and the correction step
> made the forecast about 40% more accurate on that locked-away test, for almost every district.
> We also tried eight other tweaks afterward to make sure we weren't missing something better;
> only one (averaging several recent weeks' own forecasts for real-time use) actually helped.
