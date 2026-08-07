# Sri Lanka Dengue Early-Warning Dashboard — Developer Guide

**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction
**Team Codexon · FYP**
**App path:** `src/dashboard/app.py`
**Run:** `streamlit run src/dashboard/app.py`

This file is a **developer/run reference**, not an observer script. The narrative an
evaluator needs — what the framework is, evidence-tier meanings, column glossary, page
walkthrough order, honest per-district/per-week limitations — now lives **in the app
itself** (Overview page, in-page captions, sidebar glossary expander, `help=` tooltips on
tables and metrics), so a cold-opening evaluator does not need this document, a separate
narrator, or a memorized "do say / do not say" script. Keeping that content in two places
is exactly what let the dashboard's thresholds go stale in the past (Decision 047 changed
production to τ=0.10/Platt while this guide and the app both still said τ=0.14/isotonic
for over a week) — do not re-duplicate it here.

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

From the project root, with the virtual environment (`.venv`) activated.

### Refresh from the app

Use the sidebar **Refresh operational data** button to rerun `scripts/refresh_dashboard_data.py`.
Check **Skip weather fetch** for offline refresh when weather files are up to date.

---

## Architecture

Four pages under `src/dashboard/views/`, registered as file-based `st.Page` entries in
`app.py` (real Streamlit multipage via `st.navigation`, not the old radio-button
fake-paging) — file-based, not callable-based, so each page has a stable identity across
reruns and is independently testable via `streamlit.testing.v1.AppTest.switch_page()`.

| File | Page | Notes |
|---|---|---|
| `views/overview.py` | Overview | Cold-open story; all numbers read live, nothing hardcoded |
| `views/research_evidence.py` | Research Evidence | Holdout-validated — safe to cite |
| `views/operational_monitoring.py` | Operational Monitoring | Reads `st.session_state["district_select"]` directly (file-based pages can't receive function arguments from `app.py`) |
| `views/prospective_tracking.py` | Prospective Tracking | Self-checking accuracy trackers for forward predictions |

Supporting modules (not pages themselves):

| File | Role |
|---|---|
| `data_loaders.py` | Every CSV/shapefile read in the app, one `@st.cache_data`-backed surface, mtime-keyed |
| `components.py` | `evidence_badge()`, `module_badge()`, `GLOSSARY`/`render_glossary_sidebar()`/`column_help()`, `get_thresholds()` (the **only** place alert/high thresholds may be read from — never hardcode them), `prospective_tracker_panel()` |
| `theme.py` | Module identity colors (matching the thesis's Figure 5.1 diagram) and the reserved risk-magnitude colorscale — kept as two separate color languages, never mixed |

`data/processed/module2/live_risk_predictions.csv`, `future_risk_predictions.csv`,
`data/processed/module1/future_forecast.csv`, `nowcast_next_week.csv`,
`nowcast_prediction_log.csv`, `outputs/metrics/module1/nowcast_prospective_accuracy.csv`,
`data/processed/module2/stage2_uncertainty_bands.csv`, `risk_prediction_log.csv`, and
`outputs/metrics/module2/risk_prospective_accuracy.csv` are all read-only inputs — see
`src/config.py` for their path constants and each source script's own docstring for how
they're produced.

---

## Related documentation

| File | Content |
|---|---|
| `research_context/CURRENT_ARCHITECTURE.md` | Dashboard integration layer |
| `research_context/PIPELINE_ARCHITECTURE_PLAN.md` | Refresh pipeline stage order |
| `research_context/RESEARCH_DECISIONS.md` | Decision 027 (M1-fed forward risk), Decision 047 (current thresholds/architecture) |
| `research_context/DATA_DICTIONARY.md` | Output column definitions |
| `research_context/QUESTIONS_FOR_DEFENSE.md` | Evidence-tier discipline, per-district/per-week honest limitations |
| `module_1_forecasting/MODULE_CONTEXT.md`, `module_2_classification/MODULE_CONTEXT.md` | Module-specific implementation status |

---

## Known limitations

1. **Forecast API horizon** — Open-Meteo Forecast API covers ~16 days; horizons 7–8 may have partial weekly climate.
2. **Error compounding** — Multi-week case lags fed by Module 1 forecasts; forward risk uncertainty grows with horizon.
3. **Production model training** — Checkpoints trained on all available history, including weeks shown on the dashboard.
4. **sklearn version** — If you see `InconsistentVersionWarning`, scoring still runs; pin the sklearn version used to train the frozen models for strict reproducibility.
5. **No retraining in app** — Refresh updates inputs and rescoring only; model weights are frozen in `models/`.
6. **Uncertainty bands are validated-tier only** — Module 2's Venn-Abers bands (Research Evidence page) are computed on holdout/validation folds; forward-week predictions do not yet have bands.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Empty charts / "CSV not found" | Outputs not generated | Run `python scripts/refresh_dashboard_data.py --skip-weather` |
| `API returned no new dates` (weather fetch) | Weather files already current | Expected; use `--skip-weather` |
| `ModuleNotFoundError: streamlit_folium` | Package listed in `requirements.txt` but not installed in the active `.venv` | `./.venv/Scripts/python.exe -m pip install streamlit-folium` |
| `parse_dates` / missing column error | Stale app code | Pull latest `app.py`/`views/`; restart Streamlit |
| All forward `climate_source = observed` | Forward weeks within observed calendar range | Normal for near-term horizons; forecast/mixed appear further out |
| sklearn version warnings | Model saved with different sklearn version | Pin sklearn or ignore for demo |
| Prospective Tracking page shows "0 resolved" | Expected until real calendar weeks pass | Not a bug — see the page's own explanation |
