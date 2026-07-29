# Sri Lanka Dengue Early-Warning Dashboard — Observer Guide

**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Team Codexon · FYP**  
**App path:** `src/dashboard/app.py`  
**Run:** `streamlit run src/dashboard/app.py`

---

## Purpose

This dashboard is an **operational early-warning view** for Sri Lanka dengue. It is **not** a model-evaluation report.

It answers:

> *Given the latest data we have right now, which districts look risky — recently and over the next few weeks?*

It combines two **frozen** production models (trained offline; never retrained in the app):

| Module | Question it answers |
|---|---|
| **Module 1** | How many cases might we see in the next 8 weeks? |
| **Module 2** | How likely is an **outbreak** (case surge above normal) in each week? |

---

## One-sentence pitch

> *This dashboard turns our research models into a live decision-support screen: recent outbreak risk by district, expected case counts ahead, and how that risk may evolve over the next eight epidemiological weeks.*

**Always add immediately:**

> *These are **operational forecasts**, not the holdout accuracy numbers from our thesis experiments.*

---

## How to run

### Prerequisites

Ensure dashboard CSV outputs exist. Run the refresh pipeline once:

```bash
python scripts/refresh_dashboard_data.py
```

Or skip weather fetch if raw Open-Meteo files are already current:

```bash
python scripts/refresh_dashboard_data.py --skip-weather
```

### Launch

```bash
streamlit run src/dashboard/app.py
```

From the project root, with the virtual environment activated.

### Refresh from the app

Use the sidebar **Refresh data** button to rerun `scripts/refresh_dashboard_data.py`.  
Check **Skip weather fetch** for offline refresh when weather files are up to date.

---

## Data the dashboard reads

The app is a **read-only consumer** of precomputed CSV outputs:

| File | Source script | Role |
|---|---|---|
| `data/processed/module2/live_risk_predictions.csv` | `live_scoring.py` | Recent-week outbreak risk |
| `data/processed/module2/future_risk_predictions.csv` | `forecast_future_risk.py` | Forward outbreak risk (horizon 0–8) |
| `data/processed/module1/future_forecast.csv` | `forecast_future.py` | 8-week case forecast |
| `data/processed/module1/weekly_modeling_table.csv` | preprocessing | Historical case counts |
| `data/processed/shared/climate_weekly.csv` | `shared.py` | Climate freshness check |
| `outputs/metrics/dashboard_refresh_manifest.csv` | `refresh_dashboard_data.py` | Last refresh timestamp |

---

## Page layout

### Top banner — data freshness

Shows three values:

- **Last case epi-week** — newest week with reported dengue counts (e.g. `2026 Wk25`)
- **Last observed climate epi-week** — newest week with real weather in the pipeline
- **Last refresh** — UTC timestamp when outputs were last regenerated

**Explain to observers:** *We always show how old the inputs are, so nobody mistakes stale data for a live signal.*

### Metric tiles

Repeat case week, climate week, and count of loaded output files (should be **3/3**).

---

## National overview

### Districts with alert at horizon 1

Number of districts where **next week's** forward risk crosses the alert threshold.

- **Alert threshold:** calibrated probability ≥ **0.14** (from production threshold scan, Decision 025)
- **`alert_flag = True`** means *worth attention*, not *outbreak confirmed*

### District-week alerts across horizons 1–4

Broader count of alert conditions over the **next four forward weeks**.

### Top 5 districts by max forward calibrated probability

Districts with the **highest peak outbreak probability** anywhere in the 8-week forward window.

**Explain to observers:** *This is a national triage list — where to look first if resources are limited.*

---

## Sidebar controls

| Control | Purpose |
|---|---|
| **District** | Select one of 25 districts for drill-down |
| **Skip weather fetch** | Offline refresh when weather CSVs are already current |
| **Refresh data** | Rerun full pipeline (preprocessing → forecasts → scoring) |

**Explain to observers:** *The app only reads CSV outputs; it never retrains models. Refresh updates the data feeding frozen checkpoints.*

---

## District drill-down — three tabs

Select a district in the sidebar, then use the tabs below.

### Tab A: Recent risk

**Source:** `live_risk_predictions.csv`  
**Shows:** Outbreak probability for the **last 8 observed weeks** in that district.

| Column | Meaning |
|---|---|
| `calibrated_probability` | Outbreak probability (0–1) after Stage 2 isotonic calibration |
| `risk_tier` | **low** / **medium** / **high** |
| `alert_flag` | `True` if probability ≥ 0.14 |
| `feature_completeness_pct` | Share of numeric input features that are non-missing (100% = fully informed) |
| `already_scored_in_pipeline` | That week was inside training/evaluation history — **not independent validation** |

**Chart:** Line of calibrated probability over recent weeks; dotted line at **0.14** = alert threshold.

**Explain:** *This is the “what's happening now / very recently” view — inputs are real observed cases and climate where available.*

---

### Tab B: Case forecast

**Sources:** `weekly_modeling_table.csv` (history) + `future_forecast.csv` (forward)

**Shows:**

- **Actual** — last ~52 weeks of reported cases
- **Forecast (M1)** — Module 1's 8-week-ahead prediction (`final_prediction` = SARIMA + residual correction)

**Explain:** *Module 1 estimates how many cases might occur. Module 2 estimates whether conditions look like an outbreak. High cases ≠ high outbreak risk if the district baseline is also high.*

**Caveat:** Multi-week case forecasts compound error recursively; uncertainty grows with horizon.

---

### Tab C: Forward risk

**Source:** `future_risk_predictions.csv`  
**Shows:** Outbreak probability from **now (horizon 0)** through **8 weeks ahead**.

| Column | Meaning |
|---|---|
| `horizon_step` | 0 = latest real week; 1 = next week; … 8 = furthest ahead |
| `prediction_type` | `observed_week` or `forward_week` |
| `cases_source` | `actual` / `na` / `module1_forecast` — provenance of case inputs |
| `climate_source` | `observed` / `forecast` / `mixed` / `missing` — weather data quality |
| `uses_module1_cases` | `True` when Module 1 predictions feed case-lag features (horizon ≥ 2) |
| `evidence_tier` | Always `operational` in this view |

**Chart:** Bar chart of calibrated probability by horizon step, colored by risk tier.

#### Horizon steps — plain language

| Horizon | Meaning |
|---|---|
| **0** | Risk for the most recent week with case reports |
| **1** | Next week — real case history for lags; current-week case count withheld (leakage guard) |
| **2–8** | True forward weeks — case lags partly fed by Module 1 forecasts; climate may include Open-Meteo forecast API data |

**Explain:** *Further out = more assumptions (predicted cases + forecast weather). Treat horizons 2–8 as early-warning scenarios, not precise predictions.*

---

## Risk tiers

| Tier | Threshold | Plain-language meaning |
|---|---|---|
| **Low** | &lt; 0.14 | Background / routine monitoring |
| **Medium** | 0.14 – 0.35 | Elevated concern — consider preparedness |
| **High** | ≥ 0.35 | Strong model signal — prioritize surveillance and response |

These are **model-based alerts**, not confirmed epidemiological outbreaks.

Production thresholds (Decision 025): alert **0.140**, high-confidence **0.350**.

---

## Operational vs holdout validation

| Aspect | Holdout / walk-forward (thesis) | Dashboard (operational) |
|---|---|---|
| Purpose | Honest model skill estimate | Decision-support / early warning |
| Models | Same frozen checkpoints | Same frozen checkpoints |
| Case inputs | Real observed lags only | M1 `final_prediction` for forward lags when real cases unavailable |
| Climate | Historical observed only | Observed + Open-Meteo forecast API |
| Evidence tier | Validation | `operational` — never cite as PR-AUC/BSS |

**Viva framing:**

> *We validated model skill on held-out historical data in the thesis pipeline. The dashboard applies the same frozen production checkpoints to the latest available inputs for decision support, with explicit labeling that forward outputs are operational, not validation evidence.*

See also: `research_context/QUESTIONS_FOR_DEFENSE.md` (forward risk vs holdout section).

---

## What to say in a demo / viva

### Do say

1. Two-stage hybrid framework: statistical baseline + ML correction (cases); classifier + calibration (risk).
2. Dashboard closes the loop from research models to operational monitoring.
3. Module 1 outputs feed Module 2 forward risk — intentional integration for multi-week early warning (Decision 027).
4. Transparency: freshness, feature completeness, data sources, and operational tier are all visible.

### Do not say

1. *“This proves our model accuracy”* — holdout PR-AUC/BSS live in experiment logs.
2. *“High risk = outbreak happening”* — it is probability of exceeding a historical epidemic threshold.
3. *“Forward week 8 is as reliable as week 1”* — uncertainty compounds.

---

## Suggested 2-minute walkthrough

1. **Open national view** — *“Data through 2026 Wk25; climate refreshed; last refresh timestamp shown.”*
2. **Point to alert counts** — *“X districts flagged for attention next week nationally.”*
3. **Pick Colombo or Gampaha** — *“Recent risk tab: probability rose over the last 8 weeks.”*
4. **Case forecast tab** — *“Module 1 expects cases to continue elevated over the next 8 weeks.”*
5. **Forward risk tab** — *“Module 2 shows how outbreak probability may evolve; note `uses_module1_cases` and `climate_source` for weeks ahead.”*
6. **Close with caveat** — *“Operational early warning — complements, not replaces, official surveillance and our published holdout metrics.”*

---

## Known limitations

1. **Forecast API horizon** — Open-Meteo Forecast API covers ~16 days; horizons 7–8 may have partial weekly climate.
2. **Error compounding** — Multi-week case lags fed by Module 1 forecasts; forward risk uncertainty grows with horizon.
3. **Production model training** — Checkpoints trained on all available history, including weeks shown on the dashboard.
4. **sklearn version** — If you see `InconsistentVersionWarning` (1.8.0 vs 1.9.0), scoring still runs; pin `scikit-learn==1.8.0` for strict reproducibility.
5. **No retraining in app** — Refresh updates inputs and rescoring only; model weights are frozen in `models/`.

---

## Related documentation

| File | Content |
|---|---|
| `research_context/CURRENT_ARCHITECTURE.md` | Dashboard integration layer |
| `research_context/PIPELINE_ARCHITECTURE_PLAN.md` | Refresh pipeline stage order |
| `research_context/RESEARCH_DECISIONS.md` | Decision 027 (M1-fed forward risk) |
| `research_context/DATA_DICTIONARY.md` | Output column definitions |
| `module_1_forecasting/MODULE_CONTEXT.md` | Module 1 forward forecast |
| `module_2_classification/MODULE_CONTEXT.md` | Live + forward risk scoring |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty charts / “CSV not found” | Outputs not generated | Run `python scripts/refresh_dashboard_data.py --skip-weather` |
| `API returned no new dates` (weather fetch) | Weather files already current | Expected; use `--skip-weather` |
| `parse_dates` / missing column error | Stale app code | Pull latest `app.py`; restart Streamlit |
| All forward `climate_source = observed` | Forward weeks within observed calendar range | Normal for near-term horizons; forecast/mixed appear further out |
| sklearn version warnings | Model saved with different sklearn version | Pin sklearn or ignore for demo |
