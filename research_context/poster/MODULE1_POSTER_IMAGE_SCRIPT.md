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
all — `seasonal_order = (0,0,0,52)`. Dengue is strongly seasonal here, so on paper that
looks wrong. It means these models never look at 'same week, one year ago' — only
recent weeks."

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
study and a Vietnamese cross-correlation study on mosquito life cycles."

---

## 6 — `6 figure_7_3_module1_holdout_mase.png`

*(Point to the dot plot.)*

"Here's what that bought us, on data the pipeline never touched during development.
Each row is a district; grey is SARIMA alone, orange is SARIMA plus XGBoost. Twenty-
three of twenty-five districts improve. Two don't — Kilinochchi and Mannar, the red
diamonds — and we're not hiding them. Median improvement: forty-three-point-five percent
on validation, thirty-two-point-seven percent on this untouched holdout."

---

## 7 — `7 key outcomes.png`

*(Move to the Key Outcomes panel.)*

"That's the headline, stated plainly: a two-stage SARIMA-XGBoost pipeline, consistent
gains across all twenty-five districts on validation, and the majority on an untouched
two-year holdout. Thirty-two-point-seven percent holdout improvement, forty-three-point-
five percent validation improvement, twenty-three of twenty-five districts improved."

---

## `diebold_mariano_significance.png`

*(Open the DM test plot.)*

"We didn't stop at 'the average improved' — we tested whether that's distinguishable
from noise, district by district. Pooling validation and holdout, twelve of twenty-five
districts clear that bar. On the stricter test, holdout alone, only five of twenty-five
do. That's not something we're hiding — it's why we say 'better for most districts,' not
'proven everywhere.' Kilinochchi, Mannar, and Mullaitivu sit as the directionally-worse
diamonds, but even that isn't statistically significant — p is around zero-point-three-
three to zero-point-four."

---

## `ljung_box_before_after.png`

*(Point to the Ljung-Box comparison.)*

"Here's the honest limitation a reviewer pushed us on. Stage 2 fixes the point
forecast — the MASE number — but it barely touches the underlying autocorrelation.
Twenty-three of twenty-five districts still show significant leftover structure at lag
twenty-six, before and after Stage 2. That critique started a second act: fifteen
experiments over three days, most rejected on their own evidence — a hyperparameter
search that won on validation but lost by three-point-six percent on the untouched
holdout, a per-district version of Stage 2 that was twenty-eight percent worse in
aggregate. The one thing that survived — averaging several independent SARIMA refits
into one nowcast — took the number of districts where Stage 2 actually helps, in a full
rolling simulation, from ten out of twenty-five to twenty-four out of twenty-five. After
all fifteen experiments, the headline backtested number didn't move. That's not a
failure to find something — it's evidence that we actually checked, instead of assumed."

---

## `figure_7_2_module1_holdout_forecasts.png`

*(Point to the Colombo/Gampaha line chart.)*

"For most of this window, the orange compensated forecast tracks the actual black line
noticeably better than the flat grey baseline — that's the compensation effect, visible.
But look at the very end: Colombo's actual cases crash to twenty, then jump to eleven-
thirty-eight the next week. Gampaha does the same thing. That's not a real epidemic
curve — a genuine outbreak doesn't crash to near-zero and then quadruple. It's a health-
system reporting backlog. We built a real-time detector for exactly this pattern and
rejected it — only forty-two-point-nine percent precision overall, worse specifically for
Colombo and Gampaha. Flagging the anomaly honestly, rather than silently patching it,
was the harder but more defensible call."

---

## Closing (no image)

"So: compensation is real, but it isn't universal — Kilinochchi and Mannar say so,
openly, right on that chart. What this module proves is that a simple, interpretable
baseline, corrected by a model that studies its own mistakes, does measurably better
than the baseline alone — with its real limits shown alongside its real gains, not
hidden behind them."

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
