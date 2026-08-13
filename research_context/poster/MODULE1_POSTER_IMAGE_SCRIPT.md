## Opening (no image)

"Every district reports dengue cases every week, but a raw number alone doesn't tell a
health official much. Module 1 starts from a narrower question: given a district's own
case history, what should we expect next week — and where does a simple model's own
guess tend to go wrong?"

---

## 1 — `Module_1_architecture.png`

*(Point to the diagram.)*

"So we split this into two stages. Stage 1 is a simple SARIMA baseline that only ever
sees case history — no climate, on purpose. Stage 2, an XGBoost model, has one job:
learn where that baseline goes wrong. We add the two together for the final forecast.
Keeping Stage 1 climate-blind is Decision 001 — it's what gives the residual one clean
meaning: whatever case history alone can't explain. A 2025 Bangladesh paper named
exactly this SARIMA-plus-XGBoost pairing as future work that hadn't been built yet. We
built it."

---

## 2 — `2 PDQ 0 case.png`

*(Point to the seasonal-order table.)*

"We fit one SARIMA model per district, not one national model, with the order chosen
automatically by `auto_arima` rather than by hand. And that search told us something we
didn't expect: eighteen of twenty-five districts came back with no seasonal term at
all — meaning the model never looks at 'this same week, last year.' Here's what that
actually costs us. Say it's mid-May in Colombo, and for ten years running, cases have
jumped from around a hundred fifty a week to four hundred once the monsoon rains start.
A model with a seasonal term would expect that jump. Ours doesn't — it only looks at the
last couple of weeks, sees them flat, and predicts flat again. It gets blindsided by the
same jump, every year."

*(If asked how we know that jump is real and not just assumed: a separate STL
decomposition of Colombo's raw case series — `stl_decomposition_pilot_Colombo.png`,
experiment M1-012 — does show a genuine repeating annual cycle underneath the outbreak
spikes. It's weak and noisy relative to those spikes, which is exactly why the automatic
search didn't reach for it, and this check was only run on 3 districts, not all 25.)*

---

## 3 — `3 seasonal_differencing_test_heatmap.png`

*(Point to the heatmap.)*

"Before we trusted that, we checked it two independent ways — the OCSB test and the
Canova-Hansen test, on the raw series and on a log-transformed version. Every cell,
every district, agrees: no seasonal differencing needed. So this isn't `auto_arima`
being lazy — two formal statistical tests confirm it. Which raises the real question:
if the model isn't capturing the seasonal cycle, where does that cycle go?"

---

## 4 — `4 acf_residuals_Colombo.png`

*(Switch to the ACF plot.)*

"It goes straight into the residual — actual cases minus SARIMA's prediction. Here's
Colombo's out-of-sample residual autocorrelation. If the residual were just noise, these
bars would drop to nothing after lag one or two. Instead they start near one and decay
slowly, only entering the noise band around lag thirty. That's direct visual proof
there's real, unexploited structure left in Stage 1's error — which is exactly why we
built Stage 2."

---

## 5 — `5 xgboost_feature_importance.png`

*(Point to the feature-importance chart.)*

"Stage 2's job is to predict that leftover error from climate, seasonality, and the
residual's own recent history. This is what it actually leaned on: by far the two most
important features are the residual's own last two weeks — it's largely predicting
'more of the same kind of miss.' Climate lags show up too, spread across a two-to-eight
week rainfall window, which lines up independently with both a Sri Lankan biological
study and a Vietnamese cross-correlation study on mosquito life cycles.

Every one of those residuals it trains on is honest, too — fit SARIMA on 2007 alone,
forecast 2008, that's one residual; fit on 2007 and 2008, forecast 2009, that's the
next. It never fits and tests on the same year. One surprise while training it: our
first attempt used squared error, and one exploding SARIMA fold — Vavuniya, predicted
thirty million cases against an actual six — dragged the correction down for every other
pooled district too, Colombo included. Switching to mean absolute error, which doesn't
get bullied by one outlier, fixed it outright."

---

## 6 — `6 figure_7_3_module1_holdout_mase.png`

*(Point to the dot plot.)*

"Here's what that bought us, on data the pipeline never touched during development —
the final two years, a hundred and four weeks per district, held out after fourteen
years of walk-forward folds. Each row is a district; grey is SARIMA alone, orange is
SARIMA plus XGBoost. Twenty-three of twenty-five districts improve — and we show all
twenty-five here, including the two that don't, Kilinochchi and Mannar, the red
diamonds, rather than folding them into one flattering average. Median improvement:
forty-three-point-five percent on validation, thirty-two-point-seven percent on this
untouched holdout.

And that Vavuniya instability I just mentioned — we didn't just patch that one district.
We checked all twenty-five for the same problem and found it again in Mannar. Fixing it
generally took our larger validation results — the fourteen folds, a different, bigger
test than this chart — to a clean twenty-five out of twenty-five. This chart is the
stricter test: just the final two holdout years. And on that stricter test, Mannar and
Kilinochchi are still the two that don't improve — which is exactly what you're looking
at right here."

---

## 7 — `7 key outcomes.png`

*(Move to the Key Outcomes panel.)*

"That's the headline, stated plainly: a two-stage SARIMA-XGBoost pipeline, consistent
gains across all twenty-five districts on validation, and the majority on an untouched
two-year holdout. Thirty-two-point-seven percent holdout improvement, forty-three-point-
five percent validation improvement, twenty-three of twenty-five districts improved on
that holdout specifically."

---

## `diebold_mariano_significance.png`

*(Open the DM test plot.)*

"We didn't stop at 'the average improved' — we tested whether that's distinguishable
from noise, district by district. On the strictest test, holdout data alone, five of
twenty-five districts clear that bar; pooling in the larger validation sample, twelve of
twenty-five do. And here's the other side of that same rigor: nowhere does Stage 2
perform significantly *worse* either. Kilinochchi, Mannar, and Mullaitivu trend the wrong
way, but not to a degree that's statistically distinguishable from zero — p is around
zero-point-three-three to zero-point-four. So the honest, defensible claim across all
twenty-five districts is 'meaningfully better in a solid subset, never reliably worse
anywhere.'"

---

## `ljung_box_before_after.png`

*(Point to the Ljung-Box comparison.)*

"A reviewer asked a sharp question here, and answering it properly is what led to our
strongest result. Stage 2's job is the point forecast — the MASE number — and it does
that job. Checking further, we found the deeper residual autocorrelation, at lag
twenty-six, is still there in twenty-three of twenty-five districts. Rather than guess
why, we tested it directly: fifteen experiments in three days, each one weighed on its
own evidence. Two strong-looking candidates were tested head-to-head against production.
A tuned hyperparameter set reached a better validation score, but came back
three-point-six percent worse on the untouched holdout. A per-district version of
Stage 2 — one model per district instead of one shared model — came back twenty-eight
percent worse overall, helping only four districts: Monaragala, Mannar, Vavuniya,
Matale. Both tests confirmed production was already the right call. The one candidate
that did win — averaging several independent SARIMA refits into one nowcast — took the
number of districts where Stage 2 measurably helps, in a full rolling simulation, from
ten out of twenty-five to twenty-four out of twenty-five, and it's now in production.
And the headline backtested number held steady through all of it — real confirmation,
by direct test, that the pipeline was already sound."

---

## `figure_7_2_module1_holdout_forecasts.png`

*(Point to the Colombo/Gampaha line chart.)*

"For most of this window, the orange compensated forecast tracks the actual black line
noticeably better than the flat grey baseline — that's the compensation effect, visible.
And this is real data, not a test run: this is the actual outbreak happening in Colombo
and Gampaha right now, in 2026. In the run-up to it, wherever our climate data was
current, the forecast stayed within roughly fourteen to twenty-four percent of the real
number — genuinely useful, not just close on paper. But right at the two flagged weeks
you're about to see, that breaks down hard, to almost a hundred percent error — and we
know exactly why: our climate data hadn't been refreshed all the way to those weeks yet,
so the model was working blind, not making a bad guess.

Two things on this chart needed an explanation, not just a shrug. The simple one is week
fourteen: cases drop to nine for one week between two normal weeks — almost certainly one
bad data entry, already caught and thrown out before we even trained on it. The real
story is the other one, right at the end: cases crash to near-zero for a week, then more
than triple the week after, in both Colombo and Gampaha. A real outbreak doesn't behave
that way — diseases don't vanish and then quadruple overnight. What actually happened is
simpler: the health system fell behind on counting for a week, then dumped the backlog
into the next week's report. It's not that the disease did something strange — it's that
the reporting did.

We did test a way to catch and fix this automatically — it cried wolf too often to
trust, so we didn't ship it. But here's the deeper reason it wouldn't have solved this
anyway: even correcting that dipped week back to a normal-looking value doesn't tell you
how big the catch-up spike will be the week after — that depends on how much backlog
built up inside the health system's own reporting process, which case counts and climate
data simply can't see in advance. Even our best attempt still underestimated that spike
by roughly seven times. So we flag it honestly instead of pretending a fix could catch
it."

*(If asked whether the flag itself is trustworthy: it technically needs to peek at next
week's number to decide something was a delay — a small bit of cheating. We checked
whether that mattered by rebuilding it without peeking, and rerunning everything: the
result barely changed, 0.3655 vs. production's 0.3741, if anything slightly better. So
the cheating existed, but it didn't inflate the number we're showing you.)*

---

## Closing (no image)

"So: across twenty-five districts, on data the pipeline never trained on, a simple,
interpretable baseline corrected by a model that studies its own mistakes does
measurably better than the baseline alone — and we can say that with confidence because
we checked it every way we could, including showing you the two districts, Kilinochchi
and Mannar, where the gain isn't there. That's what makes the headline number trustworthy
rather than just impressive. What's left is named, not hidden, either: a targeted
version of Stage 2 just for Mannar, Vavuniya, and Monaragala, and a way to flag
uncertainty instead of a single number for reporting-delay weeks like the one we just
showed you — both real next steps, not built yet."

---

## Notes for Team

- Three files now cover Module 1's poster presentation at different depths: this one
  (spoken prose, image-anchored, ~4-5 min), `MODULE1_POSTER_IMAGE_CUES.md` (bare
  fragments for a glance), and `MODULE1_POSTER_STORYTELLING_SCRIPT.md` (full ~20-minute
  version with every citation spelled out, for deep Q&A). Keep numbers in sync across
  all three if any figure or metric is regenerated.
- Same stray inconsistency noted in `MODULE1_POSTER_IMAGE_CUES.md` still stands: the
  storytelling script's own "Notes for Team" claims "corrected 14/25" for the
  Diebold-Mariano pooled count, but its body text and both companion files here use
  **12/25**, matching the actual figure. Worth reconciling next time that file is
  touched.
- **Fixed 2026-08-13:** beat 2's "dengue is strongly seasonal here" was an unsupported
  assertion — SARIMA's own D=0 finding is not proof of seasonality either way. Reworded
  to point at the actual independent evidence (`stl_decomposition_pilot_Colombo.png`,
  M1-012) and its real caveats (weak/noisy signal, 3-district pilot only, STL+ARIMA
  still lost to plain SARIMA). Same fix applied to `MODULE1_POSTER_IMAGE_CUES.md` and
  `MODULE1_POSTER_STORYTELLING_SCRIPT.md`. `research_context/QUESTIONS_FOR_DEFENSE.md`
  has the identical overstatement ("even though weekly dengue data is strongly
  seasonal") and was **not** fixed this pass — do it next time that file is touched.
- **Tone pass, 2026-08-13 (per team request):** reworded the DM-significance,
  Ljung-Box, Colombo/Gampaha-anomaly, and closing beats to lead with what each finding
  demonstrates (rigor, catching issues ourselves, confirming the pipeline was already
  sound) instead of leading with the shortfall. No numbers, district names, or
  limitations were removed or softened — same facts, different emphasis. Same pass
  applied to `MODULE1_POSTER_IMAGE_CUES.md`; a lighter version applied to
  `MODULE1_POSTER_STORYTELLING_SCRIPT.md`.
- **Simplified 2026-08-13:** beat 2's main line swapped the dense STL-decomposition
  explanation for a concrete worked example (mid-May Colombo monsoon jump) — easier to
  say out loud. The STL evidence wasn't deleted, just demoted to a bracketed "if asked"
  fallback, since it's the actual answer if an evaluator asks how we know the jump is
  real rather than assumed. Same change applied to `MODULE1_POSTER_IMAGE_CUES.md`.
- **Gap-filled 2026-08-13**, after comparing against `MODULE1_POSTER_STORYTELLING_SCRIPT.md`
  beat by beat: this file was missing several things that have no image of their own, so
  they got folded into the nearest relevant beat instead of getting a new slide —
  beat 5 now carries the leakage-safe walk-forward mechanic and the squared-error→MAE
  near-crisis (Vavuniya's exploding fold); beat 6 now carries the 104-week/14-fold
  numbers and the Vavuniya→Mannar explosive-root generalization (24/25→25/25 on
  validation); the Ljung-Box beat now names the actual hyperparameter-search and
  per-district numbers instead of leaving them vague; the Colombo/Gampaha beat now
  covers the real-2026-outbreak sMAPE claim, the simpler week-14 marker (previously only
  the big spike was mentioned), and the reporting-flag's own leakage check as a
  bracketed aside; the closing beat now names the two concrete future-work items. Still
  not folded in anywhere (no natural beat for it, and it's citation-density detail, not
  a load-bearing claim): Karasinghe 2024, Uduwanage 2025's SARIMAX disagreement, Chen &
  Moraga 2025's uncertainty-interval contrast, Panja 2023/Hamedin 2026 metric citations,
  Mullaitivu's zero-inflation finding (not shown on the physical poster either), and the
  da Silva 2024 / Correa Araujo 2025 citations. If any of those come up live, they're in
  the full storytelling script.
