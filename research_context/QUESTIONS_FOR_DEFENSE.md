# Questions for Defense

This file contains prepared explanations for supervisor, evaluator, and viva-style questions.

Update this file whenever a new important question is asked or a better explanation is developed.

---

## Why do we use two stages?

We use two stages to separate baseline pattern learning from error correction.

Stage 1 captures the expected structure using a baseline model. Stage 2 learns what the baseline missed by modeling the residual or error.

This makes the framework more interpretable than a black-box single-stage model.

---

## What happens to the compensation output?

The compensation model predicts the baseline model's error.

For Module 1:

```text
Final Forecast = SARIMA Forecast + Predicted Residual
```

The compensation stage does not replace the baseline. It corrects it.

---

## What if the residuals are random?

If residuals are random, compensation may not improve the result.

That is still a valid finding because it means the baseline model has already captured most learnable structure for that district or period.

This should be checked using residual diagnostics such as ACF plots, Ljung-Box tests, and performance comparison.

---

## Why are module-specific documents needed?

The project has three separate modules handled by different team members.

Module-specific documents prevent confusion and allow each module to evolve independently while still following the overall residual compensation framework.

---

## How do we avoid outdated Cursor rules?

The Cursor rule file should not contain detailed static research facts. Instead, it should instruct Cursor to read the latest markdown files and update them when decisions change.

The latest documentation should be treated as the source of truth, not the conversation history.

---

## Why does Stage 1 SARIMA often have no seasonal component (18/25 districts)?

**Short answer:** AIC-driven `auto_arima` order selection, with `m=52`, frequently chose `seasonal_order=(0,0,0,52)` — a plain non-seasonal ARIMA — even though weekly dengue data is strongly seasonal. This is a known limitation of Stage 1 **in isolation**, not a silent bug we ignored.

**What we found:**
- OCSB and Canova-Hansen both selected `D=0` for all 25 districts; only 7/25 got a seasonal AR term.
- **12/25 districts** have Stage-1-only validation MASE > 1 (worse than a seasonal-naive “repeat last year’s same week” benchmark).
- Forcing seasonal differencing (`D=1`) was tested and found computationally infeasible at pipeline scale (7+ minutes per fit vs ~0.01s for the fixed-order refits used everywhere else).

**Why we did not rework Stage 1:**
- The residual-compensation design deliberately keeps climate and explicit seasonality out of Stage 1 (Decision 001) so Stage 2 can learn those signals from residuals.
- We ran the pre-registered diagnostic after Stage 2 was built: the **18 non-seasonal districts improved more** with Stage 2 (median 44.9% validation / 39.1% holdout MASE reduction) than the 7 seasonal districts (31.9% / 26.2%). Stage 2’s `sin_week`/`cos_week`, monsoon indicators, and climate features appear to be compensating for the annual cycle Stage 1 missed.
- Reworking Stage 1 now would risk weakening the residual signal Stage 2 is designed to correct, with no evidence the **combined** pipeline would improve.

**How to present this honestly:**
- Report Stage 1-only metrics separately from Stage 1+Stage 2 — do not oversell Stage 1 as a strong standalone forecaster for all districts.
- Frame the contribution as: *baseline + residual compensation improves forecasts*, not *SARIMA alone is optimal*.
- Flag explicitly to the supervisor: “Stage 1 is a deliberately simple, AIC-selected univariate baseline; its seasonal weakness is a documented limitation that Stage 2 substantially addresses.”

**If challenged:** “Would STL+SARIMA be better?” — Possible ablation for future work, but superseded for this thesis by empirical evidence that Stage 2 already captures the missing seasonal structure. Not required to validate the residual-compensation hypothesis.

**Evidence:** `models/module1/sarima_selected_configs.csv`, M1-001/M1-002 experiment log, Open Question #12 resolution in `module_1_forecasting/MODULE_CONTEXT.md`.

---

## How is forward/dashboard risk different from holdout validation?

**Short answer:** Holdout metrics measure **model skill on past data** the pipeline never used for selection; dashboard forward outputs measure **what the frozen production models say about upcoming weeks** using forecast climate and (for multi-week risk) Module 1 predicted case lags.

| Aspect | Holdout / walk-forward | Operational forward (`future_risk_predictions.csv`) |
|---|---|---|
| Purpose | Honest skill estimate | Decision-support / early warning |
| Models | Same checkpoints, but scored on historical rows | Frozen `final_production_model.*` |
| Case inputs | Real observed lags only | M1 `final_prediction` for lags when real cases unavailable |
| Climate | Observed only (historical) | Observed + Open-Meteo forecast API |
| Evidence tier | Validation | `operational` — never cite as PR-AUC/BSS |

**Thesis framing:** “We validated the framework on held-out history; the dashboard applies the same frozen models operationally with clearly labeled uncertainty and without retraining.”
