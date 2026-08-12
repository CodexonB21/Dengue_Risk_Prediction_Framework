---
name: module1-poster-image-cues
description: Condensed image-anchored cue card for presenting the Module 1 poster — one short beat per figure in Final Evaluation/Images, not a script to memorize
metadata:
  type: report_support
---

# Module 1 — Presentation Cue Card (by image)

**Purpose:** you already know this material — this page exists so the *image on screen*
triggers the point, not your memory of a paragraph. Each beat is a handful of short
cues, not sentences to recite. The full prose version (with every citation spelled out)
stays in `MODULE1_POSTER_STORYTELLING_SCRIPT.md` — use that only if you want to re-read
the reasoning behind a beat, not as the thing you memorize.

Numbers below match the current source docs (`module_1_forecasting/MODULE_CONTEXT.md`,
verified 2026-08-12). If a number on the poster itself ever changes, update here too.

---

## Opening line (no image)

"Given a district's case history, what should we expect next week — and where does a
simple model's own guess go wrong?"

---

## 1 — `Module_1_architecture.png`

- Two stages: **SARIMA** (case history only) → **XGBoost** (predicts SARIMA's error)
- Stage 1 deliberately **climate-blind** — Decision 001, so the residual has one clean
  meaning: "what case history alone can't explain"
- `Final = SARIMA prediction + predicted residual`
- Lit hooks: Karasinghe 2024 patched this gap by hand (AR-16); Uduwanage 2025 put
  climate *into* the baseline (SARIMAX) — we went the other way on purpose; Liu/Hossain
  2025 named SARIMA+XGBoost as **unbuilt future work** — we built it

---

## 2 — `2 PDQ 0 case.png`

- `auto_arima`, per district (not one national model)
- **18 of 25 districts → seasonal_order = (0,0,0,52)** — all zero
- Surprising: dengue is known to be strongly seasonal, but the model picked no seasonal
  term at all
- Means: SARIMA never looks at "same week, last year" — only recent weeks

---

## 3 — `3 seasonal_differencing_test_heatmap.png`

- OCSB + Canova-Hansen, raw and log1p — **all green, D=0, all 25 districts**
- Not `auto_arima` being lazy — two independent formal tests **agree**
- So: whatever seasonal signal exists has nowhere to go but the residual → sets up next
  slide

---

## 4 — `4 acf_residuals_Colombo.png`

- X = lag (weeks), Y = residual autocorrelation, shaded band = "just noise"
- Slow decay from ~1.0, only enters the noise band around **lag ~30**
- Not a sharp cutoff → residual is **not white noise** — real structure left over
- This is the direct visual justification for building Stage 2 at all

---

## 5 — `5 xgboost_feature_importance.png`

- Top two by far: **residual_lag_1, residual_lag_2** — Stage 2 leans hardest on its own
  recent error history
- Climate lags (rainfall/humidity/temperature) present but spread thin across many
  features, not concentrated in one
- Rainfall lag window (2–8 wks) matches Uduwanage 2025's biology (~2–3 months egg→case)
  and Tuan 2024 Vietnam's independently-found ~10-week lag — two methods, same answer
- Group 6 features (`weeks_since_reporting_anomaly`, `suspected_backfill_week`) — added
  after the reporting-delay fix, ties forward to beat 10

---

## 6 — `6 figure_7_3_module1_holdout_mase.png`

- Each row = district; grey = Stage 1 only; orange = improved; **red diamond = didn't**
- Line at MASE=1 = seasonal-naive baseline
- **23/25 improve**, 2 don't: **Kilinochchi** (worst gap) and **Mannar**
- Headline: **43.5% median validation improvement, 32.7% median holdout improvement**

---

## 7 — `7 key outcomes.png`

- Just read it straight: two-stage SARIMA→XGBoost, gains across all 25 on validation,
  majority on an **untouched 2-year holdout**
- **32.7% holdout / 43.5% validation / 23 of 25 districts**

---

## `diebold_mariano_significance.png`

- Two panels: pooled (bigger sample) vs. holdout-only (stricter, n=104/district)
- **12/25 significant pooled → 5/25 significant holdout-only**
- Not every improvement is statistically distinguishable from noise — say this plainly,
  don't let "23/25 improved" imply "23/25 proven"
- Kilinochchi/Mannar/Mullaitivu sit as red diamonds — directionally worse, not
  *significantly* worse (p ≈ 0.33–0.40)

---

## `ljung_box_before_after.png` — the critique beat

- Lag 26: **23/25 → 23/25** still significant leftover autocorrelation. Lag 52: **22/25
  → 22/25**. Stage 2 barely moves this number.
- Say it straight: Stage 2 fixes the *point forecast* (MASE), not the *residual
  structure* — that's a real, named limitation, not swept under the rug
- This is what triggered the second act: **15 experiments** (Aug 4–6), most rejected on
  their own evidence (40-candidate hyperparameter search won validation, +3.6% *worse*
  on holdout → kept production; per-district Stage 2 tested directly, **28% worse**,
  only 4/25 districts preferred it — Monaragala/Mannar/Vavuniya/Matale)
- One thing survived and shipped: **vintage-ensembled SARIMA nowcast** — averaging
  independent refits took rolling Stage-2-helps from **10/25 to 24/25 districts**
- Honest headline: after all 15 experiments, the validated backtest number **didn't
  move** — 0.374 median holdout MASE, same as before. That's the point: most plausible
  weak spots got actually checked, not assumed away.

---

## `figure_7_2_module1_holdout_forecasts.png` — the data-quality ceiling

- Orange (Stage 1+2) visibly tracks actual better than flat grey (Stage 1) for most of
  the window — that's the compensation effect, visually
- Two flagged spikes (✕): a small one mid-holdout, and the big one at the very end —
  Colombo crashes to ~20 then jumps to **1,138**; Gampaha crashes to ~24 then **1,294**
- Not a real epidemic shape — a health-system **reporting backlog**, not a true
  week-by-week signal; this is the real 2026 Colombo/Gampaha outbreak sitting inside the
  untouched holdout
- We built a real-time version of this detector and **rejected** it: 42.9% overall
  precision, worse specifically where it matters — 46.2% Colombo, 30.0% Gampaha. Flagged
  (`is_reporting_anomaly`), not silently patched — the harder, more honest call

---

## Closing line (no image)

"Compensation is real, but it isn't universal — Kilinochchi and Mannar say so, openly,
on the chart you just saw. What this module proves is that a simple, interpretable
baseline, corrected by a model that studies its own mistakes, does measurably better —
with its real limits shown alongside its real gains, not hidden behind them."

---

## Notes for Team

- This is a **companion** to `MODULE1_POSTER_STORYTELLING_SCRIPT.md`, not a replacement
  — the full script still holds every citation and the complete remediation-arc detail
  if an evaluator pushes on any single beat. Nothing was deleted from that file.
- Image order above follows the numbered files (`1`–`7`) with the three unnumbered
  images (`diebold_mariano_significance`, `ljung_box_before_after`,
  `figure_7_2_module1_holdout_forecasts`) slotted in where they land narratively — right
  after the headline (beat 7) for the significance caveat, then the critique, then the
  data-quality ceiling. Reorder here if the physical poster layout puts them elsewhere.
- Numbers verified directly against `module_1_forecasting/MODULE_CONTEXT.md` on
  2026-08-12: DM 12/25 pooled + 5/25 holdout, Ljung-Box 23/25→23/25 (lag26) and
  22/25→22/25 (lag52), per-district ablation +28.4%, hyperparameter search +3.6% holdout
  regression, causal dip detector 42.9%/46.2%/30.0%, vintage-ensemble 10/25→24/25.
- Unresolved from the full script's own notes, not fixed here: that file's "Notes for
  Team" section claims it uses "corrected 14/25 and 5/25" for the DM counts, but its
  body text and this cue card both say **12/25** (matching the actual figure). Worth a
  quick pass to reconcile that one stray note next time either file is touched.
