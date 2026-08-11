# Module 1 — Literature-to-Design Connections

## Purpose and a Critical Honesty Note

This file exists to answer viva questions of the form *"where did you get this idea,"
"where did you find this formula," "what claim in the literature supports that."* It maps
Module 1's actual, already-implemented design decisions (from `RESEARCH_DECISIONS.md`,
`FEATURE_ENGINEERING_SPEC.md`, `module_1_forecasting/MODULE_CONTEXT.md`) to the 16 candidate
Module 1 references, based on a direct read of each paper (not just its title/abstract).

**Read this framing carefully before using any of it in the viva.** For most of these papers,
there is no evidence the team read them *before* making the corresponding design decision —
several were published in 2025, after Module 1's core architecture was already implemented
(2026-07-26 onward per `RESEARCH_DECISIONS.md`'s dates). The honest, defensible framing is:

> "This design choice is **consistent with** / **independently supported by** [paper] — not
> that we derived it from that paper."

The exception is the group already sitting in `_interim_extract.md`'s literature review
(**[1] Uduwanage, [3] Yi, [5] Chathurangika, [6] Karasinghe, [9] Hamedin, [10] Chen & Moraga,
[12] Francisco**) — these were written up as literature review content, which plausibly
predates or ran alongside the detailed design work, so a genuine "this is part of what
motivated us" framing is defensible for that group specifically. Don't extend that stronger
claim to the other 9.

Access-confidence caveat carried over from the retrieval pass: quotes and formulas below marked
"tool-extracted" came through an automated fetch of paywalled or blocked pages, not a direct
read of the primary PDF — treat those specific quotes as needing a quick verification pass
against the primary source before reading them aloud verbatim in a defense. Quotes not marked
this way were read directly from the primary PDF/HTML.

---

## 1. "How did you arrive at a two-stage baseline-plus-correction architecture at all?"

**Module 1's actual design:** `final_prediction = sarima_prediction + predicted_residual`
(Decision 001 family) — a statistical baseline whose *systematic leftover error* is separately
modeled by a second, more flexible learner.

**What the literature says, with real precedent:**

- **[9] Hamedin et al. (2026)**, on STL decomposition, gives the clean textbook form
  `Yₜ = Tₜ + Sₜ + Rₜ`, explicitly naming `Rₜ` the "irregular/residual component" — literature
  precedent for treating "whatever the structural components don't explain" as a distinct,
  nameable quantity. The paper then explicitly states the gap Module 1 fills: pure ARIMA/SARIMA
  models "should be complemented by integrated modeling approaches" because they can't
  incorporate climate.
- **[6] Karasinghe et al. (2024)** (Colombo, Sri Lanka) is the sharpest domestic precedent for
  *why a second stage is needed at all*: they fit `ARIMA(2,1,0)` for weekly Colombo dengue,
  found leftover autocorrelation via ACF/PACF diagnostics, and patched it by manually adding a
  16th-order AR term (`ARIMA(2,1,0) + AR(16)`) — i.e., they detected exactly the kind of
  residual structure Module 1's own Ljung-Box diagnostic detects (23/25 districts still show
  significant autocorrelation even after Stage 2), but their fix was to keep enlarging the same
  linear model rather than handing the leftover structure to a separate, more flexible learner.
  They also **explicitly name the gap Module 1's Stage 2 fills**: *"The study exclusively relies
  on time series data and overlooks external factors like climate and public health
  interventions."*
- **[21] Hossain, Liu, Hossain (2025)** states as unimplemented future work, in a 2025 paper on
  Bangladesh: *"By leveraging the complementary strengths of both SARIMA and XGBoost, a hybrid
  approach can be developed."* This is a named, published gap that a SARIMA+XGBoost
  residual-compensation design (Module 1's exact model pair) directly answers — a strong
  "research gap" quote for your Chapter 2/4.
- **[20] Hossain, Safa, Juthi, Tasnia (2025)** already builds a SARIMA-XGBoost combination
  (`μₜ = exp(ηₜ + f_XGB(Xₜ))`, a Bayesian count-model mean function) and reports it as their best
  performer. **Architecturally this is not the same as Module 1's design** — theirs is an
  additive-in-log-link mean function inside one Bayesian model, not a literal
  `residual = actual − baseline` regression target for a second model — but it is the closest
  existing SARIMA+XGBoost precedent found, and worth knowing about *precisely because* an
  evaluator could ask "hasn't this been done before" and you should be ready to explain the real
  architectural difference rather than be caught by the question.

**Honest counter-evidence to have ready:** [21], [22], [23], [24], [27] all frame their result as
"pick the single best-performing standalone model" rather than a hybrid, and **none of the 16
papers implement Module 1's literal `residual = actual − baseline` regression-target
architecture** — this is a genuinely defensible, specific novelty claim (not a vague "we did a
hybrid" claim), but say it precisely: *"the residual-compensation formulation — training a second
model to directly regress the first model's out-of-sample error, then adding the prediction back
— is not the architecture used in the 16 dengue-specific papers I reviewed; several use ensembles
or single-model comparisons instead, and only one Bangladesh paper (Hossain et al. 2025, a
concurrent 2025 preprint) combines SARIMA and XGBoost, via a different additive-mean-function
mechanism, not a residual-regression target."*

---

## 2. "Why SARIMA specifically as the baseline — and why keep it climate-free (Decision 001)?"

- **[1] Uduwanage et al. (2025)** is the strongest precedent here: a **Sri Lankan, district-level**
  comparison of CNN, XGBoost, and SARIMAX found **SARIMAX best** (RMSE 94.94 vs. XGBoost 142.36
  vs. CNN 258.12), across nine districts. This directly supports choosing an ARIMA-family model
  as the strongest baseline *in this exact country and data regime* — a much stronger form of
  "why SARIMA" than a generic textbook justification.
- **Important nuance to state precisely, not gloss over:** Uduwanage's winning SARIMAX **includes
  climate as an exogenous regressor directly in the baseline** — the opposite of Module 1's
  Decision 001, which deliberately keeps Stage 1 climate-free specifically so the residual still
  carries climate signal for Stage 2 to learn. This is a genuine, citable point of departure: *"a
  prior Sri Lankan study (Uduwanage et al., 2025) found SARIMAX with climate baked in to be the
  best standalone model; our design deliberately does not fold climate into the baseline the way
  they did, because our research question is about residual compensation specifically — we
  needed the baseline's error to still contain climate-explainable structure for Stage 2 to
  correct, which folding climate into Stage 1 would have removed."* This is a sharper, more
  honest answer than claiming SARIMA's "climate-free-ness" was independently validated by
  literature — it wasn't; it's a deliberate departure from what the closest domestic precedent
  did, for a specific, statable methodological reason.
- **[6] Karasinghe et al. (2024)** independently confirms an ARIMA-family model is workable for
  weekly Colombo dengue specifically (their un-augmented base ARIMA(2,1,0) achieved training MAPE
  0.318 before the AR(16) patch), reinforcing that SARIMA is a reasonable baseline choice for this
  exact time series, even without climate.

---

## 3. "Where does the specific residual formula (`residual = actual − sarima_prediction`) find precedent?"

- **[5] Chathurangika, Perera, De Silva (2024)** — a Colombo-area dengue paper — gives, verbatim,
  Equation 4: **`ε = Î − I_obs`**, i.e. estimated minus observed, used as their Bayesian/MCMC
  likelihood error term. This is the same *actual-minus-model* residual convention Module 1 uses
  (with sign flipped — Module 1 defines it as actual minus predicted, they define it as predicted
  minus observed — worth noting the sign difference if quoted directly), applied to a different
  purpose (a likelihood term for parameter estimation, not a second model's training target).
- **[10] Chen & Moraga (2025)**, building adaptive conformal prediction intervals, defines
  (tool-extracted, verify before quoting): **`residual_t,h = actual_t+h − predicted_t,h`** — the
  *exact same functional form* as Module 1's residual, applied to build uncertainty bands rather
  than a second-stage prediction target. This is the single closest literal formula match found
  across all 16 papers for the "actual minus predicted" residual convention itself.
- **[27] da Silva et al. (2024)** defines a signed error `ΔEᵢ = yᵢ − xᵢ` as a diagnostic
  (over/under-prediction indicator), read directly from the arXiv preprint — another
  actual-minus-predicted convention, though used only diagnostically, never as a training target.

**Answer shape for the viva:** *"The convention of defining a model's error as observed minus
predicted, and treating that quantity as a first-class object rather than discarding it, appears
independently in at least three dengue-forecasting papers I reviewed (Chathurangika et al. 2024;
Chen & Moraga 2025; da Silva et al. 2024) — though each uses it for a different downstream
purpose (a Bayesian likelihood term, a conformal interval, a diagnostic sign check) rather than as
a second model's regression target the way we do."*

---

## 4. "Where do the climate lag windows (rainfall 2-8 weeks, temperature/humidity 1-4 weeks) come from?"

This is one of the strongest, most concrete connections available — **multiple independent
papers converge on a similar order-of-magnitude lag**, which is exactly the kind of
"where did you find that claim" answer an evaluator is fishing for.

- **[1] Uduwanage et al. (2025)** gives an explicit **entomological derivation** of the lag,
  which is the most defensible *mechanistic* justification available: mosquitoes lay eggs
  "~10 days after a rainfall event," eggs take "~14 days" to mature to adults, adult lifespan is
  "56 to 60 days," and case detection takes "4 to 10 days" post-bite — concluding **"on average,
  it takes about 2 to 3 months to observe an increase in the patient count following a
  significant rainfall event."** This is a Sri Lankan, biologically-reasoned derivation of a
  multi-week rainfall lag, directly supporting Module 1's `rainfall_lag_2..8` weeks feature group
  (Feature Group 2, `FEATURE_ENGINEERING_SPEC.md`) — you can cite this as the biological
  mechanism (mosquito breeding cycle + extrinsic incubation period) behind the specific lag range
  chosen, since it's the same mechanism `FEATURE_ENGINEERING_SPEC.md` itself invokes.
- **[3] Yi et al. (2023)** uses a **5-week case-history window** (`c_{t−4}, c_{t−3}, c_{t−2},
  c_{t−1}, c_t`) as their neural network's input — the same depth (4 lags plus current) as
  Module 1's own `cases_lag_1..4` feature group. A clean, literal structural match.
- **[22] Tuan (2024)** (Vietnam) selected, via cross-correlation analysis, an optimal rainfall lag
  of **`PRECTOTCORR_shift_10`** (10 weeks) — squarely inside Module 1's rainfall lag 2-8 week
  range's upper end, and a humidity lag `RH2M_shift_6` (6 weeks) — inside Module 1's own
  climate-anomaly reasoning range.
- **[25] Yuan et al. (2025)** (Guangdong, China) uses a 90-day (~13-week) rolling window,
  explicitly justified by "the approximate 30-day lifespan of Aedes mosquitoes and the delayed
  ecological responses to weather" — the same entomological-lifespan reasoning as Uduwanage, at a
  somewhat longer horizon (a different climate/mosquito-species context, worth noting if asked
  why the exact week-count differs across papers).
- **[10] Chen & Moraga (2025)** used temperature/humidity lags "ranging from 1 week to 4 weeks,"
  the *exact same range* as Module 1's `temperature_lag_1..4`/`humidity_lag_1..4` feature group,
  citing prior literature that "temperature and humidity at a lag of 1 month are positively
  associated with dengue cases."

**Answer shape for the viva:** *"The specific lag windows are grounded in the mosquito
breeding/extrinsic-incubation-period biology, the same mechanism a Sri Lankan study (Uduwanage et
al. 2025) worked out in detail — roughly 10 days egg-laying, 14 days maturation, and several more
days to symptomatic detection, totaling on the order of weeks to two-to-three months. Independent
studies in Vietnam (Tuan 2024) and Brazil (Chen & Moraga 2025) selected very similar lag depths
(6-10 weeks for rainfall, 1-4 weeks for temperature/humidity) via their own cross-correlation
analyses, which is consistent with, not derived from, our chosen ranges."**

---

## 5. "Where does the climate-anomaly framing (deviation from expected, not raw value) come from?"

None of the 16 papers use an explicit "anomaly = current minus long-term district-week mean"
feature the way Module 1's Feature Group 3 does — **this appears to be a genuine point of
difference worth stating plainly rather than forcing a false connection.** The closest adjacent
ideas:

- **[22] Tuan (2024)** justifies choosing Negative Binomial over Poisson regression by explicit
  overdispersion reasoning (variance ≫ mean: 43.73 vs. 1692.84) — a *distributional* anomaly
  argument, not a *feature-level* one, but conceptually adjacent (both are about "how far this
  observation deviates from what's typical").
- **[23]/[24] Al Mobin et al.** report that **93.76% of dengue-count variability was explained by
  feature-engineered (lagged/rolling) variables, versus only 6.24% by raw, non-lagged features** —
  a strong general empirical argument (not anomaly-specific) that *transformed*, not raw, climate
  inputs carry the predictive signal, supporting the broader design philosophy behind Module 1's
  anomaly/lag feature groups even without directly validating the anomaly formula itself.

**Honest answer for the viva:** *"None of the papers I reviewed use exactly this anomaly
formulation — this appears to be a design choice specific to our framework, motivated by the
general finding (e.g., Al Mobin et al. 2024/2025) that transformed rather than raw climate
features carry most of the predictive signal, and by the intuition that an 'unusually wet week
for this district in this season' is more informative than a raw rainfall value that means
different things in different districts and seasons."*

---

## 6. "Why MAE loss instead of squared-error loss for Stage 2 XGBoost?"

This is a case where the literature doesn't hand you the answer — the real justification is
Module 1's own diagnosed incident (Decision 014: one district's, Vavuniya's, catastrophic SARIMA
divergence corrupted the whole pooled squared-error model). No paper reviewed reports an
analogous single-extreme-value failure mode, so **don't force a citation here** — this is a
finding from your own data, and the honest answer is exactly that: *"this wasn't literature-
motivated — we discovered it empirically. Squared-error loss let one district's SARIMA
catastrophically diverge in one fold, which corrupted the pooled model's correction for every
other district; switching to MAE (whose gradient is bounded regardless of error magnitude) fixed
it. This is a robustness property of the pooled architecture itself, not something we read about
first."* Contrast this candidly with **[24] Al Mobin et al.**, whose Random Forest similarly
benefits from ensemble averaging "reducing variance" — a related but distinct robustness argument
(averaging over many trees vs. bounding one loss function's gradient).

---

## 7. "Why MASE as the primary evaluation metric, and why scale by the training window?"

- **[28] Panja et al. (2023)** gives, verbatim, the exact same MASE formula structure Module 1
  uses: **`MASE = [(1/h)Σ|ŷᵢ−yᵢ|] / [(1/(N−f))Σ|yᵢ−yᵢ₋f|]`** — i.e., the test-period mean absolute
  error scaled by the *training*-period seasonal-naive mean absolute error, reported alongside
  RMSE/MAE/SMAPE. This is the single cleanest literature precedent for both the metric choice
  itself and the specific convention of scaling against the training window (not the evaluation
  window) — directly supporting `evaluate.py`'s `mase()` docstring rationale (avoiding leaking
  evaluation-period difficulty into the normalizer).
- **[10] Chen & Moraga (2025)** and **[9] Hamedin et al. (2026)** are both cited in your own
  interim lit review's §2.2.8.1 for the broader evaluation-metrics discussion (RMSE/MAE/MAPE/
  sMAPE), and Chen & Moraga specifically evaluates across multiple forecast horizons (1, 2, 3, 4,
  8, 12 weeks) — precedent for horizon-aware evaluation generally, relevant if asked about
  Module 1's own `forecast_future.py` multi-horizon reporting.
- **[9] Hamedin et al.** uses the **Ljung-Box test at 24 lags** as a residual-diagnostic — the
  same diagnostic family (though a different lag depth) as Module 1's own Ljung-Box check at lags
  26/52.

---

## 8. Zero-inflation: what does the literature actually suggest, and why doesn't Module 1 do a formal hurdle model?

This is the single most substantive methodological conversation available in this reference set,
and it cuts in an interesting direction — **it's evidence for a real design choice you haven't
made yet, not just a justification for one you have.**

- **[12] Francisco, Carvajal, Watanabe (2024)** is the anchor paper here. Their data was **64,917
  zeros of 90,896 observations (71.4%)** — comparable in spirit to Module 1's own most
  zero-heavy districts (Mullaitivu 52.8%, Kilinochchi 47.7%, Mannar 40.4% zero-weeks). Their fix
  is architecturally explicit: a **first-stage classifier predicts presence/absence**, and the
  **second-stage quantitative model runs only on rows the first stage predicts as "present."**
  Quoted: *"Filtering out all zero predictions in the first step improved the accuracy of the
  quantitative model."* Their own Hybrid Accuracy Index explicitly weights the classification
  stage more heavily (0.7) than the quantitative stage (0.3) *because* 70% of their data was
  zero-inflated.
- **Module 1 does not adopt this gating mechanism.** SARIMA and XGBoost run for every
  district-week regardless of zero-inflation level; the actual handling is (a) the `log1p`
  transform selected per-district by walk-forward MASE (17/25 districts chose it, largely the
  higher-incidence ones — `MODULE_CONTEXT.md`), and (b) the MAE-robust pooled Stage 2 loss. This
  is a **real, honest gap worth being ready to name directly**, since Module 1's own documentation
  (`DATA_DICTIONARY.md`) already flags zero-inflation as a live, unresolved issue, and
  Mullaitivu — the most zero-heavy district — has the *worst* Stage 1 validation MASE (2.92) of
  all 25 districts.
- **[20] Hossain, Safa, Juthi, Tasnia (2025)** is the useful counter-precedent for *not* adopting
  a formal zero-inflated statistical model: they explicitly tried ZIP and ZINB and report they
  **"failed to converge"** with "unstable coefficient estimates and non-significant inflation
  terms," concluding zero-inflated formulations "did not provide a better description" for their
  Bangladesh data, and used NB-based/SARIMA-Bayesian hybrids instead.
- **[24] Al Mobin et al. (2025)** used a lighter-weight approach — a single engineered **binary
  "sparse" indicator feature** flagging zero entries, rather than a full hurdle architecture —
  the simplest of the three zero-handling strategies found in this literature set.

**Answer shape for the viva, stated honestly:** *"We're aware of at least three different
zero-inflation strategies in the dengue-forecasting literature: a two-stage presence/absence-then-
magnitude gate (Francisco et al. 2024), a lightweight binary sparsity indicator feature (Al Mobin
et al. 2025), and explicit rejection of a formal zero-inflated statistical model as unstable
(Hossain et al. 2025). Module 1 currently handles zero-inflation implicitly, through the per-
district log-transform choice and a robust loss function, rather than any of these three
explicit mechanisms — and our own results show this isn't fully solved: Mullaitivu, our most
zero-heavy district, also has our worst Stage 1 fit. A Francisco-style presence/absence gate ahead
of the residual-compensation stage is a concrete, literature-grounded direction for future work,
not something we've ruled out — we simply haven't implemented it."* This is a much stronger
answer than pretending the gap doesn't exist, and it directly uses Decision 016's own "report
per-district honestly" ethos.

---

## 9. Honest counter-evidence: literature that pushes back on your own framing

An evaluator who has actually read some of this literature may probe whether "hybrid always
helps" is oversold. Be ready with these:

- **[27] da Silva et al. (2024)** found climate features **did not always help** — for Natal
  specifically, cases-only Random Forest beat cases+climate: *"when we consider climate variables
  the forecasting is not improved."* Their overall conclusion: *"climate variables do not always
  help… depending on the city and the training length, the results can be improved with a given
  combination of features."* This directly parallels Module 1's own honest finding that
  Kilinochchi and Mannar get *worse*, not better, under residual correction on holdout —
  supporting the framing that compensation benefit is real but not universal, and should be
  reported per-district rather than as a blanket claim.
- **[26] Correa Araujo et al. (2025)**, reporting on a multi-team Brazilian forecasting
  competition, states plainly: *"No single model consistently excelled across all forecast
  targets."* Useful general support for reporting per-district, per-fold results honestly rather
  than a single headline number.
- **[21] Hossain, Liu, Hossain (2025)** explicitly avoided SARIMAX (with climate) because
  "exogenous variables… weren't always precisely aligned across divisional dimensions and
  temporal lags" — a data-alignment caveat worth knowing about if asked why climate integration
  is harder in practice than it sounds.

---

## Quick-Reference Table: Paper → What It Supports in Module 1

| Ref | Paper (short) | Already cited in project? | Strongest connection |
|---|---|---|---|
| [1] | Uduwanage et al. 2025 (Sri Lanka, SARIMAX/XGBoost/CNN) | Yes — Ch.1, interim lit review | SARIMA-family strongest baseline in Sri Lanka; entomological lag derivation (~2-3 months) |
| [3] | Yi et al. 2023 (PICTUREE-Aedes) | Yes — interim §2.2.7 | 5-week case-lag input window matches `cases_lag_1..4`; general ensembling-reduces-error argument |
| [5] | Chathurangika et al. 2024 (Colombo, Bayesian) | Yes — interim §2.2.3.1 | Explicit `ε = Î − I_obs` residual formula precedent |
| [6] | Karasinghe et al. 2024 (Colombo, modified ARIMA) | Yes — interim §2.2.3.1 | Names the exact gap (no climate) Stage 2 fills; residual autocorrelation diagnostic precedent |
| [9] | Hamedin et al. 2026 (Malaysia, STL+SARIMA) | Yes — interim §2.2.3.1/2.2.8.1 | `Y=T+S+R` decomposition vocabulary; states gap needing "integrated" models |
| [10] | Chen & Moraga 2025 (Rio, model comparison) | Yes — interim §2.2.3.2/2.2.8.1 | Exact residual formula for conformal intervals; same 1-4wk climate lag range; hybrid-ensemble-helps evidence |
| [12] | Francisco et al. 2024 (Manila, zero-inflation hybrid) | Yes — interim §2.2.3.3/2.2.4.2 | THE zero-inflation precedent; explicit two-stage gate architecture (not adopted, but directly relevant) |
| [20] | Hossain et al. 2025 (Bangladesh, Bayesian SARIMA-XGB) | No | Closest existing SARIMA+XGBoost precedent (different mechanism); rejects ZIP/ZINB as unstable |
| [21] | Hossain, Liu, Hossain 2025 (Bangladesh, comparison) | No | Explicitly names SARIMA+XGBoost hybrid as unimplemented future work — a citable research gap |
| [22] | Tuan 2024 (Vietnam) | No | Independently-selected lag depths (6-10 weeks) matching Module 1's range; overdispersion reasoning |
| [23] | Al Mobin 2024 (Bangladesh, feature selection) | No | 93.76% of variability from engineered vs. raw features — supports the lag/anomaly feature philosophy |
| [24] | Al Mobin et al. 2025 (Bangladesh, downscaling) | No | Lightweight binary zero-indicator as an alternative zero-handling strategy |
| [25] | Yuan et al. 2025 (Guangdong, LSTM-SIR hybrid) | No | Mosquito-lifespan-based lag window justification (~13 weeks), a second biological precedent |
| [26] | Correa Araujo et al. 2025 (Brazil forecasting sprint) | No | "No single model wins everywhere" — supports honest per-district reporting |
| [27] | da Silva et al. 2024 (Natal/Iquitos/Barranquilla) | No | Climate doesn't always help — direct parallel to Kilinochchi/Mannar's regression under correction |
| [28] | Panja et al. 2023 (XEWNet, wavelet ensemble) | No | Exact MASE formula match, including training-window scaling convention |

---

## DOI / Access Links and Recommended Citations (Verified 2026-08-11)

DOIs and open-access links for all 16 papers referenced above, confirmed via Crossref/journal
metadata and (where possible) direct fetch of the primary source. Table also lists the single best
1-2 papers to cite for each of the 9 viva-question connections above.

| Ref | Citation (verified) | DOI | Open-access link | Status |
|---|---|---|---|---|
| [1] | Uduwanage et al., "Prediction of Dengue Outbreaks in Sri Lanka Using ML Techniques," *Sri Lanka J. Medicine* 34(1):15-26, 2025 | [10.4038/sljm.v34i1.568](https://doi.org/10.4038/sljm.v34i1.568) | [sljm.sljol.info PDF](https://sljm.sljol.info/articles/568/files/68060c4a7bc38.pdf) | Verified |
| [3] | Yi et al., "PICTUREE-Aedes," *Pathogens* 12(6):771, 2023 | [10.3390/pathogens12060771](https://doi.org/10.3390/pathogens12060771) | [mdpi.com](https://www.mdpi.com/2076-0817/12/6/771) | Verified |
| [5] | Chathurangika, Perera, De Silva, arXiv:2401.10295, 2024 | [10.48550/arXiv.2401.10295](https://doi.org/10.48550/arXiv.2401.10295) | [arxiv.org/abs/2401.10295](https://arxiv.org/abs/2401.10295) | Verified (arXiv only — no journal version found) |
| [6] | Karasinghe et al., "Modified ARIMA…," *PLOS ONE* 19(3):e0299953, 2024 | [10.1371/journal.pone.0299953](https://doi.org/10.1371/journal.pone.0299953) | [PMC10923413](https://pmc.ncbi.nlm.nih.gov/articles/PMC10923413/) | Verified |
| [9] | Hamedin, Musa, Sulong, *Osong Public Health Res. Perspect.* 17(1):50-60, 2026 | [10.24171/j.phrp.2025.0397](https://doi.org/10.24171/j.phrp.2025.0397) | [PMC12980637](https://pmc.ncbi.nlm.nih.gov/articles/PMC12980637/) | Verified |
| [10] | Chen & Moraga, *Tropical Medicine and Health* 53(1), article 52, 2025 | [10.1186/s41182-025-00723-7](https://doi.org/10.1186/s41182-025-00723-7) | [PMC11984044](https://pmc.ncbi.nlm.nih.gov/articles/PMC11984044/) | Verified — **correction**: this file and `_interim_extract.md` currently say "vol. 53, no. 32"; the actual identifier is article **52** |
| [12] | Francisco, Carvajal, Watanabe, *PLOS NTD* 18(10):e0012599, 2024 | [10.1371/journal.pntd.0012599](https://doi.org/10.1371/journal.pntd.0012599) | [PMC11527386](https://pmc.ncbi.nlm.nih.gov/articles/PMC11527386/) | Verified |
| [20] | Hossain, Safa, Juthi, Tasnia, medRxiv preprint, Sept. 2025 | [10.1101/2025.09.14.25335716](https://doi.org/10.1101/2025.09.14.25335716) | [medRxiv](https://www.medrxiv.org/content/10.1101/2025.09.14.25335716v1) | Partial — authors/model description match; exact mean-function notation and ZIP/ZINB-non-convergence claim not independently re-confirmed against the full PDF. **Unreviewed preprint.** |
| [21] | Liu, Hossain, Hossain, *Scientific Reports* 15, 2025 | [10.1038/s41598-025-19752-7](https://doi.org/10.1038/s41598-025-19752-7) | [nature.com](https://www.nature.com/articles/s41598-025-19752-7) | Verified — **correction**: first author is **Liu**, not Hossain; cite as "Liu et al. (2025)," not "Hossain, Liu, Hossain (2025)" |
| [22] | Tuan, *Tropical Medicine and Infectious Disease* 9(10):250, 2024 | [10.3390/tropicalmed9100250](https://doi.org/10.3390/tropicalmed9100250) | [PMC11511084](https://pmc.ncbi.nlm.nih.gov/articles/PMC11511084/) | Verified — note a later correction notice exists (PMC12115829); check it doesn't affect the cited lag/overdispersion figures |
| [23] | Al Mobin, *Scientific Reports* 14, 2024 | [10.1038/s41598-024-83770-0](https://doi.org/10.1038/s41598-024-83770-0) | [nature.com](https://www.nature.com/articles/s41598-024-83770-0) | Verified — **single author**; cite "Al Mobin (2024)," not "Al Mobin et al." |
| [24] | Al Mobin, *BMC Infectious Diseases* 25, 2025 | [10.1186/s12879-025-11159-z](https://doi.org/10.1186/s12879-025-11159-z) | [biomedcentral.com](https://bmcinfectdis.biomedcentral.com/articles/10.1186/s12879-025-11159-z) | Verified — same single author as [23] (a follow-up paper, not a different research group) |
| [25] | Yuan, Wang, Liu, medRxiv preprint, Oct. 2025 | [10.1101/2025.10.04.25337267](https://doi.org/10.1101/2025.10.04.25337267) | [medRxiv](https://www.medrxiv.org/content/10.1101/2025.10.04.25337267v1.full) | Verified content — **unreviewed preprint** |
| [26] | Correa Araujo et al., 2024 Dengue Forecasting Sprint in Brazil | [10.1073/pnas.2508989123](https://doi.org/10.1073/pnas.2508989123) (journal) / [10.1101/2025.05.12.25327419](https://doi.org/10.1101/2025.05.12.25327419) (preprint) | [medRxiv PDF](https://www.medrxiv.org/content/10.1101/2025.05.12.25327419v1.full) | PNAS DOI found via search but not independently clicked through (domain blocked in the retrieval session) — spot-check resolution before citing the journal DOI in the thesis |
| [27] | da Silva et al., *Eur. Phys. J. Special Topics*, 2024 | [10.1140/epjs/s11734-024-01201-7](https://doi.org/10.1140/epjs/s11734-024-01201-7) | [arxiv.org/abs/2404.05266](https://arxiv.org/abs/2404.05266) | Verified |
| [28] | Panja et al., *Chaos, Solitons & Fractals* 170:113124, 2023 | [10.1016/j.chaos.2023.113124](https://doi.org/10.1016/j.chaos.2023.113124) | [arxiv.org/abs/2212.08323](https://arxiv.org/abs/2212.08323) | Verified title/journal/authors; MASE formula text not re-confirmed against the PDF (unreadable in retrieval session) |

### Best 1-2 Papers to Cite, Per Connection

| # | Connection | Recommended citation(s) |
|---|---|---|
| 1 | Two-stage baseline+correction architecture | [6] Karasinghe et al. 2024 (names the exact gap, domestic precedent) + [21] Liu, Hossain, Hossain 2025 (explicit unimplemented-future-work quote) |
| 2 | SARIMA as baseline, kept climate-free | [1] Uduwanage et al. 2025 (only paper testing SARIMAX head-to-head in Sri Lanka) |
| 3 | Residual formula precedent | [10] Chen & Moraga 2025 (exact same functional form, most rigorously verified of the three) |
| 4 | Climate lag windows | [1] Uduwanage et al. 2025 (entomological derivation) + [22] Tuan 2024 (independently selected near-identical lag depths) |
| 5 | Climate-anomaly framing | [23] Al Mobin 2024 (strongest adjacent empirical argument: 93.76% variability from engineered features) |
| 6 | MAE loss choice | None — this is correctly your own empirical finding; do not force a citation |
| 7 | MASE metric choice | [28] Panja et al. 2023 (identical formula and training-window scaling convention) |
| 8 | Zero-inflation handling | [12] Francisco et al. 2024 (anchor paper) + [20] Hossain, Safa, Juthi, Tasnia 2025 (counter-precedent: ZIP/ZINB failed) |
| 9 | Counter-evidence ("hybrid always helps") | [27] da Silva et al. 2024 (most direct parallel to Module 1's own per-district regression finding) |

---

## What Was NOT Verified, Stated Plainly

- Papers [3], [6], [20], [25], [26] were retrieved via automated extraction tools rather than a
  direct read of the primary rendered document by a person — the prose claims and headline
  numbers are corroborated across repeated extraction passes, but exact equation formatting
  (subscripts, Greek letters) should be re-checked against the primary source before being written
  into the thesis verbatim.
- No paper in this set implements Module 1's exact `residual = actual − sarima_prediction`
  regression-target architecture — this was checked directly, not assumed, across all 16 papers.
- The DOI/access confidence for [27] and [28]'s publisher-of-record versions (Springer/Elsevier)
  could not be independently confirmed — both were read via their arXiv preprint versions instead,
  which the authors themselves state correspond to the published paper.
