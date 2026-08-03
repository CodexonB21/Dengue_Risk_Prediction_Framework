# Speaker Script — Bandara H.R.B.G.M. (214029P)
## Project Introduction (3 min) + Module 1 (4 min) = **7 minutes**

**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Print note:** ~2 pages — intro + module; practice with timer.

---

### YOUR SLIDES (in order)

| # | Slide | Script file |
|---|---|---|
| 1 | Title / Team | — |
| 2–8 | Intro (7 slides) | **`PRESENTATION_SCRIPTS_INTRO_SLIDES.md`** (~2:30) |
| 9 | M1-1 Module intro | below |
| 10 | M1-2 Two-stage design | **Fig 6.2** |
| 11 | M1-3 Data & protocol | — |
| 12 | M1-4 Stage 1 & 2 features | — |
| 13 | M1-5 Results: Stage 1 vs Stage 1+2 | **`PRESENTATION_SCRIPTS_M1_RESULTS.md`** |
| 14 | M1-6 Results Cont. — Figure 7.2 | **`PRESENTATION_SCRIPTS_M1_RESULTS.md`** |
| 15 | M1-7 Holdout MASE — Figure 7.3 | **`PRESENTATION_SCRIPTS_M1_RESULTS.md`** |
| 16 | M1-8 Summary | below |

**Intro per-slide scripts:** `research_context/PRESENTATION_SCRIPTS_INTRO_SLIDES.md`  
**Key numbers:** Val MASE +43.5% (25/25) · Holdout +32.7% · MASE ~0.62→0.37

---

## PART 1 — INTRO SLIDES (~2:30)

Use **`PRESENTATION_SCRIPTS_INTRO_SLIDES.md`** — one short script per slide (Introduction → Background → Problem → Aim → Objectives → Modules → Architecture). Architecture slide gets ~50 sec; others ~20–30 sec each.

**Handoff:** *“I will now present Module 1 — Hybrid Time-Series Case Forecasting.”*

---

## PART 2 — MODULE 1 (~4:00)

**[M1-1 · 0:45]** Module 1 forecasts **weekly district case counts** — *how many cases next week?*  
**Gap:** Classical models miss structured error from **climate, monsoon, case dynamics**. **Novelty:** **SARIMA Stage 1** (climate-free) + **XGBoost Stage 2** on **out-of-sample residuals**.

**[M1-2 + Fig 6.2 · 0:45]** Stage 1: per-district **SARIMA**. Stage 2: predicts **residual = actual − SARIMA** using climate lags, anomalies, monsoon, residual lags. Final = **SARIMA + predicted residual**. **Pooled XGBoost**, leakage-safe.

**[M1-3 · 0:30]** Data: **MoH weekly cases** + **Open-Meteo climate**. **14 walk-forward folds** + **2-year holdout**. Metric: **MASE**.

**[M1-4 · 0:40]** Top features: **residual_lag_1/2**, rolling cases, rainfall, season — Stage 2 corrects **structured SARIMA error**.

**Results slides — use `PRESENTATION_SCRIPTS_M1_RESULTS.md`:**

**[M1-5 · 0:30]** Headline MASE: **25/25** val improve; median **+43.5%** val, **+32.7%** holdout; **0.62 → 0.37**.

**[M1-6 + Fig 7.2 · 0:40]** **Colombo & Gampaha** holdout: orange **Stage 1+2** tracks actuals; dashed SARIMA misses peaks.

**[M1-7 + Fig 7.3 · 0:35]** **All 25 districts**: orange shifts left vs grey — broad national improvement.

**[M1-8 · 0:25]** Module 1 = **magnitude layer**; feeds dashboard.  
**HANDOFF:** *I now hand over to **Nethma** for **Module 2 — Outbreak Risk Classification**.*

---

### REMINDERS
- Point at figures; don’t read every decimal  
- Say “decision support” / “early warning”  
- Don’t name weak districts or DM partial significance  
- Pause before handoff; wait for Nethma

---
