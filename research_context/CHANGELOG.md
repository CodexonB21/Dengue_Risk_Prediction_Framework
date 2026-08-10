# Changelog

This file records important project changes.

Use it to track why the architecture, features, models, or decisions changed over time.

---

## 2026-08-08 - Figure 5.1 (system architecture) revised: climate-into-Stage-2 label, M1→M3 operational arrow, drawio drift fixed

### Module
Report / Diagrams (all modules)

### Change
A user-proposed alternative high-level architecture sketch (single-lane-per-module, a
"Data/Model Gateway" box) was reviewed against `CURRENT_ARCHITECTURE.md`,
`PIPELINE_ARCHITECTURE_PLAN.md`, and the already-accepted Figure 5.1. The sketch omitted
the shared-vs-module-specific preprocessing split (Decision 013) and both real
cross-module operational links, and invented a "Gateway"/versioned-artifact component
that does not exist in this project. Rather than adopt that structure, the existing
Figure 5.1 layout (`generate_figure_5_1_architecture.py`,
`figure_5_1_system_architecture.drawio`) was kept and corrected instead:

1. Module 1's Stage 2 box now reads "XGBoost residual (+ climate lags/anomalies)" — the
   diagram previously implied Stage 2 was climate-blind; only Stage 1/SARIMA is
   climate-free (Decision 001).
2. Added a second dashed cross-module arrow, Module 1 → Module 3, labelled "operational
   forward only (Decision 031)" — Module 3's forward hotspot forecast
   (`forecast_future.py`) was implemented after Figure 5.1 was first drawn and had never
   been added to it. The existing Module 1 → Module 2 arrow (Decision 027) is unchanged.
3. Found and fixed a real artifact-sync bug: `figure_5_1_system_architecture.drawio` (the
   hand-editable source) still read "Stage 2: Isotonic calibration" and "RF residual
   (α=0.05)" for Modules 2/3 even though the PNG generator script had already been
   corrected to Platt scaling / α=1 relative residual on 2026-08-07/M3-015 — the drawio
   file was never brought in sync at that time. Both now agree.

### Reason
Keep the report's system-architecture figure accurate to the latest accepted decisions
and prevent a diagram-vs-implementation conflict from being carried into the final
report uncaught.

### Documentation Updated
`research_context/REPORT_DIAGRAM_PLAN.md`,
`research_context/report_drafts/chapter5_5.2_high_level_architecture.md`,
`research_context/report_drafts/diagrams/generate_figure_5_1_architecture.py`,
`research_context/report_drafts/diagrams/figure_5_1_system_architecture.drawio`,
`research_context/report_drafts/diagrams/figure_5_1_system_architecture.png` (and its
`figure_high_level_system_architecture.png` alias) regenerated.

---

## 2026-08-08 - Module 3: M3-015 documentation/dashboard closeout - decision entries backfilled, dashboard text and next-week panel updated

### Module
Module 3 / Dashboard

### Change
Follow-up to the same-day M3-015 promotion (see the entry directly below): closed three
remaining documentation/dashboard gaps found while auditing what else needed updating.

1. **`RESEARCH_DECISIONS.md` gap closed**: added Decision 050 (M3-008's own-district
   residual-lag promotion, documented retroactively - it never had a real entry) and
   Decision 051 (M3-015's relative-residual promotion). Also corrected
   `module_3_spatial/MODULE_CONTEXT.md`'s pre-existing mis-citation of "Decision 032" for
   M3-008 - Decision 032 is actually an unrelated Module 1 entry (M1-011's rolling DM
   test); the citation now points to the new Decision 050.
2. **Dashboard `research_evidence.py` Module 3 panel was stale**: hardcoded prose still
   described the pre-M3-015 absolute-residual model (MAE 20.54->9.96, "does NOT beat
   naive baseline on MAE") - the same class of staleness already caught and fixed for
   Module 2 after Decision 047 (2026-08-07 entry above). Updated to describe the
   relative-residual mechanism and cite the correct, current numbers; the "beats naive
   persistence" section flipped from `st.warning` to `st.success` since that's now true.
3. **Module 3's next-week forecast panel refactored** to match Module 1's
   `_render_nowcast_panel()` design (module/evidence badges, a 3-metric row, a national
   top-5 table) instead of the previous ad hoc inline block - new
   `_render_m3_forecast_panel()` in `operational_monitoring.py`. The 3 metrics now surface
   the M3-015 mechanics directly (Forecast Hybrid Risk / Stage 1 baseline / relative
   correction applied), replacing the old 2-metric version that only showed the final
   Risk and case count. New `load_m3_hotspot_forecast()` in `data_loaders.py`, named to
   match `load_m1_nowcast()`'s convention (previously loaded via the bare generic
   `load_csv()`). Deliberately keeps using only ONE of Module 3's four map styles (the
   Folium heat-cloud already in use) - not the full four-view switcher the historical
   Hybrid Risk map section offers, since this is a compact summary panel.

### Reason
User asked to close out the three items flagged after the M3-015 promotion, and
separately asked that Module 3's dashboard "next week" panel match the design already
used for Modules 1/2, with exactly one map style chosen rather than all four.

### Impact
- No production model, metric, or default artifact changed - documentation and
  dashboard-presentation-layer only.
- Verified via `streamlit.testing.v1.AppTest`: `app.py`, `operational_monitoring.py`, and
  `research_evidence.py` all load with zero exceptions; the new panel's metrics render
  real values (spot-checked: Ampara forecast Hybrid Risk 69.6, Stage 1 baseline 49.3,
  relative correction +0.40).

### Documentation Updated
`research_context/RESEARCH_DECISIONS.md` (Decisions 050, 051),
`module_3_spatial/MODULE_CONTEXT.md` (citation fix; dashboard panel description),
`research_context/CHANGELOG.md` (this entry).

---

## 2026-08-08 - Module 3: four compensation mechanisms tested against the naive-persistence gap; relative-residual reformulation found as a genuine, stress-tested improvement (M3-012 through M3-015)

### Module
Module 3

### Change
Following M3-010/M3-011's finding that the official Stage 2 RF loses to a
naive "carry last week's own error forward" baseline on MAE and rank
metrics, four genuinely different compensation mechanisms were tested in
sequence:

1. **M3-012**: added Spearman rank correlation / precision@k as a companion
   evaluation lens (matches Module 3's actual hotspot-detection purpose
   better than MAE/RMSE) - persistence wins on this lens too, confirming
   rather than overturning M3-010.
2. **M3-013**: blended the RF's and persistence's final predictions
   (output-level, not stacking - M3-011 already rejected stacking). A
   week-level paired bootstrap (added specifically to stress-test what
   initially looked like a clean win in the raw aggregate table) showed the
   blend is a real, robust improvement over the RF alone, but only a
   statistical tie with persistence on MAE/precision@5 and a real loss on
   Spearman rho. Not adopted.
3. **M3-014**: adapted Module 2's own compensation mechanism (isotonic
   calibration of a raw score against outcomes, zero covariates) to Module
   3. Failed cleanly - root-caused to a structural mismatch: Module 3's
   geographically-clustered spatial CV folds put the highest-magnitude
   district cluster (Colombo/Gampaha) entirely out of range of the training
   folds' calibration curve, which has no covariates to extrapolate with
   (unlike the RF). Rejected.
4. **M3-015**: a direct diagnostic (not assumed) found Stage 1's raw error
   strongly heteroscedastic (error magnitude scales with predicted
   magnitude) - modeling the RELATIVE residual instead of the absolute one
   produces an RF that beats both naive persistence and the official RF on
   every metric, confirmed via a week-level bootstrap and broad across 4 of
   5 spatial folds (two honest caveats: RMSE's win concentrates in the
   highest-volume fold, and the model underperforms at the already-flagged
   structurally-different NE-monsoon week). Candidate for promotion to
   official Stage 2, pending explicit confirmation.

### Reason
User asked to keep searching for a genuine, defensible improvement over the
naive baseline after M3-010/M3-011's honest null result, explicitly steering
away from environmental/demographic-only feature engineering (already tried
and null, M3-005) toward mechanisms different in kind - output blending, a
calibration-based mechanism borrowed from Module 2, and finally a direct
diagnostic of the residual's own structure.

### Impact
- New files: `src/module3_spatial/hotspot_ranking_evaluation.py`,
  `blended_persistence_rf.py`, `isotonic_calibration.py`,
  `relative_residual_compensation.py` - all additive, exploratory scripts;
  none modify the official pipeline (`compensation_model.py`,
  `iterative_loop.py`, `evaluate.py`) yet.
- New `src/config.py` path constants for each script's metrics outputs
  (comparison tables, bootstrap CIs, fold breakdowns, decile bias tables).
- No production model, feature set, or default artifact changed - M3-015's
  relative-residual RF is documented as a candidate only.

### Documentation Updated
`module_3_spatial/EXPERIMENT_LOG.md` (M3-012 through M3-015),
`module_3_spatial/MODULE_CONTEXT.md` (new section + Evaluation Direction
update), `research_context/QUESTIONS_FOR_DEFENSE.md`,
`research_context/CHANGELOG.md` (this entry).

### Status
M3-012/013/014: investigated and resolved (two rejected, one partial).
M3-015: **promoted to official Stage 2 (2026-08-08), user-confirmed.**
`compensation_model.py`/`iterative_loop.py`/`evaluate.py`/`forecast_future.py`
updated to the relative-residual target and reconstruction formula and
rerun end-to-end; regenerated `hybrid_risk_map.csv`,
`future_hotspot_forecast.csv`, `results_summary.txt`, and related metrics/
figures verified to reproduce M3-015's own validated numbers. Frozen
scripts (`alpha_sweep.py`/M3-006, `stacked_persistence_experiment.py`/
M3-011) re-verified unaffected - the latter rerun post-promotion and
confirmed to reproduce its exact original numbers (only `n_jobs=-1` float
noise at the 13th significant digit, the same class M3-009 already
documented; reverted, not committed).

---

## 2026-08-07 - Module 2 case-anomaly-lag carry-forward substitution tested and rejected (M2-016/Decision 049)

### Module
Module 2

### Change
Following the Wk25 annotation work, investigated the mechanism behind Colombo/Gampaha's 2026
Wk25 false negative (real outbreak, `label=1`, but scored "low"/"medium" risk): traced to
`case_anomaly_lag_1` (Stage 1's dominant feature, ~35% importance) going `NaN` because the
preceding week shares Module 1's `is_reporting_anomaly` flag. Tested substituting
`case_anomaly_lag_2` for the masked value (mirroring Module 1's Decision 030 `cases_lag_1`
substitution) via a new `carry_forward_masked_lag1` parameter on
`feature_engineering.compute_case_anomaly_lags()`/`build_module2_feature_table()`, benchmarked
in `scripts/m2_016_case_anomaly_lag1_carryforward.py` against the current production Random
Forest hyperparameters (Decision 047) on the same 13 walk-forward folds.

### Reason
User asked to build and holdout-test the fix rather than speculate about whether it would help.

### Impact
- **Rejected**: validation median PR-AUC regressed slightly (0.3865 vs. baseline 0.3917).
  Holdout was NOT examined, per the project's pre-registered "validation wins first, holdout
  checks once" rule — the specific Wk25 row that motivated this experiment sits inside that
  untouched block, so whether the fix would have helped THAT prediction remains genuinely
  unknown, by design (no result was allowed to leak from peeking).
- New `carry_forward_masked_lag1` parameter defaults to `False` (production behavior
  unchanged) but is kept in the codebase as a documented, tested-and-rejected variant.
- No production model, feature table, or default artifact changed.

### Documentation Updated
`research_context/RESEARCH_DECISIONS.md` (new Decision 049), `module_2_classification/
MODULE_CONTEXT.md` (Open Question #11), `module_2_classification/EXPERIMENT_LOG.md` (M2-016),
`research_context/CHANGELOG.md` (this entry).

---

## 2026-08-07 - Reporting-anomaly weeks annotated in Figure 7.2 and the dashboard's Recent Risk tab

### Module
Module 1 / Module 2 / Report / Dashboard

### Change
User flagged that the 2026 Wk25 Colombo/Gampaha spike (real cases 1,138/1,294 vs. both
Module 1 forecast lines staying flat, and Module 2's live-scoring probability sitting where
it does) would look like an unexplained model failure to an evaluator seeing it cold, in
both the academic report and the dashboard, and asked whether to suppress it. Decided
against suppression (would look worse if discovered, and contradicts the dashboard's own
established 2026-08-07 redesign philosophy of surfacing `is_reporting_anomaly` rather than
hiding it) - instead extended the existing annotation pattern to the two places that were
still missing it:

1. **`generate_figure_7_2_7_3.py`** (`make_figure_7_2`): merges in `is_reporting_anomaly`
   from `weekly_modeling_table.csv` (not present in `final_combined_predictions.csv` itself)
   and marks the week immediately AFTER any flagged week with an "X" + callout. Data-driven,
   not hardcoded to Wk25 - it also caught a second, earlier Colombo event (~2026 Wk14) that a
   hardcoded fix would have missed.
2. **`src/dashboard/views/operational_monitoring.py`** (`tab_recent`, "Recent risk" tab):
   `live_risk_predictions.csv` didn't carry the case counts in its displayed table or the
   `is_reporting_anomaly` flag at all. Added `Number_of_Cases` to the displayed columns,
   merged in the flag from `m1_weekly` (already loaded in this view), and added the same
   marker + caption pattern already used on the neighboring "Case forecast" tab.

### Reason
See above - an evaluator-facing artifact showing a large, unexplained-looking miss is a
worse outcome than showing the same miss WITH the already-documented explanation attached.
This is the same treatment the 2026-08-07 dashboard redesign already gave the "Case
forecast" tab; it had just not been extended to Figure 7.2 or the "Recent risk" tab yet.

### Impact
- `figure_7_2_module1_holdout_forecasts.png` regenerated with the new annotations.
- `operational_monitoring.py` edit verified via a `streamlit.testing.v1.AppTest` run
  (Overview → Operational Monitoring, district=Colombo and Gampaha) - zero exceptions.
- No model, threshold, or evaluation metric changed - this is presentation-layer only.
- Separately, confirmed (not yet acted on) that `live_scoring.py`'s calibrated probability
  for Colombo/Gampaha Wk25 (~0.50/0.58) differs substantially from the walk-forward/holdout
  evaluation's calibrated probability for the same week (~0.05) - expected per the documented
  evidence-tier distinction (different feature/model vintage), but flagged here in case it's
  worth a closer look later.

### Documentation Updated
`research_context/REPORT_DIAGRAM_PLAN.md` (Figure 7.2 entry), `research_context/CHANGELOG.md`
(this entry).

---

## 2026-08-07 - Report diagrams (Figures 5.1, 5.4, 5.6) corrected ahead of poster redesign

### Module
Report / Diagrams

### Change
Auditing the report's architecture diagrams before redesigning them for the final-evaluation
poster surfaced two staleness issues the 2026-08-06 text-only correction had missed. Fixed both:

1. **Figure 5.1** (top-level architecture) and **Figure 5.4** (Module 2 architecture) still
   rendered "Isotonic Regression" for Module 2 Stage 2 and plain "Random Forest" for Stage 1 —
   `REPORT_DIAGRAM_PLAN.md`'s prose had already been corrected for Decision 047/M2-013 on
   2026-08-06, but the actual diagram files were never regenerated to match. Both now read
   "Random Forest (tuned)" → "Platt scaling".
2. **Figure 5.6** (integration/dashboard) predated the same day's dashboard redesign (4-page
   multipage app) and the Prospective Tracking evidence tier (Decisions 041/048) — it showed a
   generic single dashboard box and only two evidence tiers. Corrected to list the actual four
   pages (Overview / Research Evidence / Operational Monitoring / Prospective Tracking) and
   three evidence tiers (added Prospective Tracking).

Figures 5.3 (Module 1) and 5.5 (Module 3) were checked against their current `MODULE_CONTEXT.md`
files and found already accurate — not modified.

### Reason
User requested a poster-presentation redesign of the architecture diagrams; per the Diagram and
Figure Rules, the latest architecture documentation must be checked before proposing/redrawing
any diagram. That check found the report's own source-of-truth figures had drifted from the
decisions they were supposed to reflect.

### Impact
- `figure_5_1_system_architecture.png`/`figure_high_level_system_architecture.png` regenerated
  via (edited) `generate_figure_5_1_architecture.py`.
- `figure_5_4_module2_architecture.drawio` text corrected; new companion
  `generate_figure_5_4_module2_architecture.py` added so the PNG renders directly from the
  drawio's content and cannot drift out of sync again (no draw.io CLI available in this
  environment to export the edited XML directly).
- `figure_5_6_integration_dashboard.drawio` text corrected (dashboard pages + evidence tiers);
  new companion `generate_figure_5_6_integration_dashboard.py` added, same rationale.
- `figure_5_5_module2_architecture.drawio` (explicitly superseded legacy layout, kept for
  reference only) was left unchanged — it is not the figure referenced by the report.
- `research_context/REPORT_DIAGRAM_PLAN.md` updated with the correction notes above.

### Status
Complete. Poster-specific diagrams (separate from these report figures) follow in the same
session.

### Documentation Updated
`research_context/REPORT_DIAGRAM_PLAN.md`, `research_context/CHANGELOG.md` (this entry).

---

## 2026-08-07 - Dashboard redesigned into a 4-page multipage app for evaluator self-explanatoriness

### Module
Dashboard / Integration Layer

### Change
Full restructure of `src/dashboard/` from a single `app.py` + `pages.py` (two radio-button
"pages") + `evidence_data.py` into a real Streamlit multipage app: `app.py` (sidebar +
`st.navigation`) dispatching to four file-based pages under `views/`
(`overview.py`, `research_evidence.py`, `operational_monitoring.py`,
`prospective_tracking.py`), plus three new supporting modules - `data_loaders.py` (single
cached CSV/shapefile loading surface, replacing three separately-cached/uncached copies),
`components.py` (`evidence_badge`/`module_badge` pills, a `GLOSSARY` feeding both a sidebar
expander and inline column tooltips, `get_thresholds()` as the one permitted place to read
alert/high thresholds, `prospective_tracker_panel()`), and `theme.py` (module identity
colors copied from the Figure 5.1 diagram generator, kept strictly separate from the
existing YlOrRd risk-magnitude colorscale). Six previously-computed-but-unwired files are
now shown: `nowcast_next_week.csv`/`nowcast_prediction_log.csv`/
`nowcast_prospective_accuracy.csv` (Module 1) and `stage2_uncertainty_bands.csv`/
`risk_prediction_log.csv`/`risk_prospective_accuracy.csv` (Module 2). Honest per-district/
per-week caveats already documented in research files but previously invisible in-app are
now surfaced directly (M1 Kilinochchi/Mannar/Vavuniya holdout regressions, M3's NE-monsoon
non-significant Moran's I week, `is_reporting_anomaly` markers on the case-forecast chart).
`pages.py`/`evidence_data.py` retired; `DASHBOARD_GUIDE.md` trimmed to a developer/run
reference now that the narrative content (evidence-tier meanings, column glossary,
walkthrough order, "what not to say") lives in the app itself.

### Reason
User feedback: "the current dashboard is not self-explanatory or user-friendly" and needed
to be shown usefully to evaluators. Auditing the existing dashboard while planning the fix
surfaced a real, independent bug worth fixing in the same pass: the Research Evidence
page's Module 2 metrics (PR-AUC, architecture name, alert threshold) were read from a
frozen `production_stack_evaluation_summary.csv` snapshot dated 2026-07-29 that predates
Decision 047/M2-013 (Random Forest retuning flipped Stage 2 isotonic -> Platt and moved
thresholds 0.14/0.35 -> 0.10/0.50) - the dashboard was silently showing stale
pre-promotion numbers as if current. Separately, `streamlit-folium` (imported by the
Module 3 map tab) was missing from the project's actual `.venv`.

### Impact
- `evidence_data.py::m2_holdout_summary()` (now `data_loaders.py`) rewritten to read live
  from the same sources the production scoring pipeline itself uses
  (`scoring_utils.official_stage2_architecture()`/`load_production_thresholds()`,
  `stage2_compensation_metrics.csv`, `risk_threshold_holdout_comparison.csv`) instead of
  the frozen snapshot - verified: now correctly reports `architecture='platt'`,
  `alert_threshold=0.1`, `pr_auc=0.4228`.
- `streamlit-folium` installed into `.venv`.
- Verified end-to-end via `streamlit.testing.v1.AppTest` (not just import checks) across
  all four pages, including a real navigation switch between them - zero exceptions.
- A real bug found and fixed mid-implementation: initial `st.Page(callable, ...)`
  registration (with an anonymous `lambda` for the Operational Monitoring page) could not
  be verified by `AppTest.switch_page()` at all and carried a real risk of unstable page
  identity across reruns (a fresh lambda object every script run); switched to file-based
  `st.Page(path, ...)` registration, which is independently testable and matches
  Streamlit's more conventional multipage pattern.
- No production model, threshold-selection logic, or evaluation pipeline changed - this is
  entirely dashboard/presentation-layer work plus the one live-data-source correctness fix
  above.

### Status
Complete; verified via `AppTest` smoke checks. Delivered in reviewed phases (bug/env fix →
components/theming → data consolidation → multipage + Overview → wiring in the 6 files →
honest-caveats polish) per user request.

### Documentation Updated
- `research_context/CURRENT_ARCHITECTURE.md` (Integration Layer section, Last Updated).
- `research_context/CHANGELOG.md` (this entry).
- `src/dashboard/DASHBOARD_GUIDE.md` (trimmed to developer/run reference).

---

## 2026-08-07 - Module 2: prospective forward-risk accuracy tracker added (M2-015/Decision 048)

### Module
Module 2

### Change
Added `src/module2_classification/risk_tracking.py`, mirroring Decision 041/M1-017's
nowcast tracker exactly: `append_to_risk_log()` (wired into `forecast_future_risk.
run_forward_risk()`, default on) permanently logs every genuinely-forward prediction row;
`reconcile_risk_log()` (wired into `refresh_dashboard_data.py` as a new
`module2_risk_reconcile` step) joins the log against real outcomes once a logged target
week resolves, recomputing the actual epidemic-threshold label fresh each time. New config
paths `MODULE2_RISK_LOG_PATH` / `MODULE2_RISK_PROSPECTIVE_ACCURACY_PATH`.

### Reason
User asked whether Module 2 can predict next week's outbreak risk. Confirming this
required actually running the forward-scoring scripts, which crashed - two real,
previously-latent bugs, both only surfaced because Decision 047 made Platt scaling the
official Stage 2 architecture for the first time ever:
1. `scoring_utils.score_feature_rows()` scored Platt exactly like isotonic - calling
   `.predict()` on the raw 1D probability instead of `.predict_proba()` on its log-odds,
   2D-reshaped. Fixed with an explicit `platt` branch mirroring
   `compensation_model.fit_and_calibrate`'s own logic, plus type assertions.
2. `compute_case_anomaly_lags()` crashed scoring forward weeks - `forecast_future_risk.py`'s
   synthetic row never set `is_reporting_anomaly`, upcasting the whole column to float once
   NaN-filled and breaking a boolean negation. Fixed at the root (field added to the
   synthetic row) and defensively (`.fillna(False).astype(bool)`).

Once both scripts ran clean, the same evidence-tier gap Module 1 already had before
Decision 041 was still open: a forward prediction has no ground truth to check against
until the target week actually passes. The tracker closes that gap the only honest way -
by logging now and waiting.

### Impact
- Both live/forward scoring bugs fixed; `live_scoring.py` and `forecast_future_risk.py`
  now run correctly against the current (tuned-RF/Platt) production model.
- New permanent artifacts: `data/processed/module2/risk_prediction_log.csv` (seeded with
  200 rows), `outputs/metrics/module2/risk_prospective_accuracy.csv` (0/200 resolved so
  far, correctly - none of those weeks have happened yet).
- Concrete finding while verifying the fix: next week's (2026 Wk26) forward scoring shows
  7/25 districts "high" tier and 20/25 crossing the alert threshold, closely matching the
  most recent real observed week's split (9 high/8 medium/8 low) - driven by genuinely
  large case counts (Colombo 1,138; Gampaha 1,294), not a scoring artifact. Flagged for the
  team to verify against source data, not investigated further here.
- `module_2_classification/MODULE_CONTEXT.md` (new "Prospective Forward-Risk Accuracy
  Tracking" section + bug-fix note), `module_2_classification/EXPERIMENT_LOG.md` (new
  entry M2-015), `research_context/RESEARCH_DECISIONS.md` (new Decision 048).

### Status
Bugs fixed and verified by rerun. Tracker adopted as new operational infrastructure.

---

## 2026-08-06 - Chapter 7 (Module 2 sections) updated to v2 drafts after Decision 047 - v1 kept

### Module
Module 2 / Report

### Change
Created `research_context/report_drafts/chapter7_7.4_module2_v2.md` and
`chapter7_7.6_7.8_comparative_discussion_summary_v2.md` reflecting Decision
047/M2-013's numbers (tuned Random Forest, Platt-scaled Stage 2, τ=0.10/0.50,
updated Table 7.7 from a rerun of `scripts/m2_009_m1_alert_baseline.py`). The
v1 files are UNCHANGED, per explicit instruction, so both versions exist
side by side - same precedent as the existing `chapter7_evaluation.md` /
`chapter7_m1_m2_evaluation.md` (legacy) pair.

### Reason
Decision 047 made the existing v1 chapter text and Table 7.7 numbers stale
(wrong architecture name, wrong thresholds, wrong tier rates); user asked
for the report to be brought current without losing the old version.

### Impact
- `scripts/m2_009_m1_alert_baseline.py`'s hardcoded "isotonic, tau=0.14" row
  label replaced with one read dynamically from the data, so it cannot
  silently go stale the same way again.
- `research_context/CHAPTER_STATUS.md` updated with a dated note pointing at
  the v2 files and the still-outstanding stale artifacts: the combined
  `chapter7_evaluation.md`, `PRESENTATION_MODULE2_{SLIDES,COPY_PASTE}.md`,
  and the report's manually-composed Figure 7.4 asset
  (`report_drafts/diagrams/figure_7_4_module2_reliability.png`, dated
  2026-07-30, predating this update) - none of these were edited this pass.

### Status
v2 drafted; v1 retained; adoption (replacing v1, or merging into the
combined chapter file) left for the team to decide.

---

## 2026-08-06 - Module 2: two live/forward scoring bugs found and fixed - Platt scaling and forward-week feature construction were both silently broken

### Module
Module 2

### Change
Rerunning `live_scoring.py` and `forecast_future_risk.py` after Decision 047 (the first
time Platt scaling has ever been the official Stage 2 architecture) surfaced two real,
previously-latent bugs, neither triggered while isotonic was the only architecture ever
run through these scripts:
1. `scoring_utils.score_feature_rows()`'s generic Stage 2 branch called
   `stage2_model.predict(predicted_probability)` on a bare 1D array. Isotonic accepts
   that directly; Platt's `LogisticRegression` needs the LOG-ODDS of the probability
   (2D-reshaped), and `.predict()` on a classifier returns a discrete class label, not a
   probability - both errors were latent because Platt was never live-scored before.
   Fixed with an explicit `platt` branch mirroring `compensation_model.fit_and_calibrate`'s
   own Platt logic exactly, plus a type assertion on both branches so a future architecture
   change fails loudly instead of silently miscomputing.
2. `feature_engineering.compute_case_anomaly_lags()`'s `~stats["is_reporting_anomaly"]`
   raised `TypeError: bad operand type for unary ~: 'float'` when scoring forward
   (synthetic) weeks - `forecast_future_risk.py`'s synthetic row dict never set
   `is_reporting_anomaly`, so concatenating it with real rows upcast the whole column to
   float wherever NaN appeared, breaking the boolean negation. Fixed at the root
   (`is_reporting_anomaly: False` added to the synthetic row) and defensively
   (`.fillna(False).astype(bool)` before negating, protecting any future caller from the
   same class of bug).

### Reason
User asked directly whether Module 2 can currently predict next week's outbreak risk.
Checking required actually rerunning the forward-scoring scripts against today's
retrained models rather than trusting stale output files (dated 2026-07-29, before
Decision 047) - both scripts crashed on the first attempt.

### Impact
- `data/processed/module2/{live_risk_predictions,future_risk_predictions}.csv`
  regenerated under the current tuned-RF/Platt production stack.
- Both scripts now run cleanly. Next-week (2026 Week 26) forward scoring: 7/25 districts
  "high" tier, 13 "medium", 5 "low" - broadly consistent with the most recent REAL
  observed week's tier split (9 high/8 medium/8 low from `live_scoring.py`'s own log),
  suggesting a genuine current elevated-risk signal in the underlying case data rather
  than a forward-extrapolation artifact - flagged for the team to look at, not
  investigated further here.
- This is "operational" evidence-tier output (per `evidence_tier` column /
  `QUESTIONS_FOR_DEFENSE.md`'s existing holdout-vs-operational distinction) - it must not
  be cited as a holdout-validated skill claim, only as what the frozen production model
  currently says about the coming week.

### Status
Fixed and verified by rerun. Not yet added as a formal EXPERIMENT_LOG entry (this is a
bug fix in operational infrastructure, not a research ablation) - noted here for the
Living Documentation trail.

---

## 2026-08-06 - Module 2 documentation/report completion pass - all remaining stale isotonic/threshold references fixed

### Module
Module 2 / Report

### Change
Follow-up to the same-day Chapter 7 v2 update: fixed every remaining Module-2-specific
report, presentation, and planning artefact still asserting the pre–Decision-047 facts
(isotonic as official Stage 2, τ=0.14/high=0.35, pre-tuning holdout numbers). Created,
v1 retained unchanged in every case:
- `chapter7_evaluation_v2.md` (full combined Chapter 7)
- `chapter5_5.4.2_module2_v2.md`, `chapter6_6.5_module2_v2.md` (standalone Analysis/Design
  and Implementation sections)
- `PRESENTATION_MODULE2_SLIDES_v2.md`, `PRESENTATION_MODULE2_COPY_PASTE_v2.md`

Edited in place (planning/reference docs, not graded chapters, with dated notes rather
than full duplication):
- `REPORT_DIAGRAM_PLAN.md` (multiple Module 2 diagram-plan entries)
- `PRESENTATION_DIAGRAM_DESCRIPTIONS_M1_M2.md`
- `research_context/report_drafts/diagrams/generate_figure_7_4.py` — the underlying bug
  fixed at the source: it hardcoded "isotonic" in the plot legend/title/docstring instead
  of reading the actual selected architecture from the data. Now labels dynamically from
  the `architecture` column, so this cannot silently go stale again the way it just did.
  Rerun to regenerate `figure_7_4_module2_reliability.png` (now correctly shows Platt).

### Reason
User asked to complete the Module 2 documentation refresh rather than leave it partially
done - the isotonic/τ=0.14 staleness turned out to be more widespread than the three items
originally flagged (Chapter 5 and 6's standalone Module 2 sections and the presentation
decks all made the same now-false claims).

### Impact
- No production code changed in this pass (all changes are documentation, presentation
  content, and one plotting-script label fix).
- `CHAPTER_STATUS.md` updated throughout (Chapter 5, 6, 7 sections) with dated notes
  pointing at every new v2 file and confirming the figure fix.
- **Deliberately not done:** the combined `chapter5_analysis_and_design.md` and
  `chapter6_implementation.md` mega-files still have v1 text inline for their Module 2
  subsections - re-splicing a full multi-section combined file for a one-section change
  was judged disproportionate; the standalone `_v2` files are the current source until the
  team merges them in.

### Status
Complete for all explicitly-requested and discovered items; combined-file re-splicing
explicitly deferred.

---

## 2026-08-06 - Module 2: Random Forest hyperparameter tuning adopted - genuine holdout-confirmed improvement, cascades into Stage 2 architecture flip and new thresholds (M2-013/Decision 047)

### Module
Module 2

### Change
`RF_PARAMS` in `src/module2_classification/baseline_classifier.py` updated to Optuna-tuned
values (`n_estimators=472, max_depth=16, min_samples_leaf=11, min_samples_split=18,
max_features="sqrt"`, `class_weight="balanced"` unchanged) after a 50-trial search
(`scripts/m2_013_stage1_rf_refresh.py`) beat the prior hand-picked defaults on validation AND
the one-time holdout check. Two other levers tested alongside (`class_weight=
"balanced_subsample"`; untuned Gradient Boosting) were negative and not adopted. The full
Module 2 pipeline (Stage 1 -> Stage 2 -> risk thresholds) was rerun under the new
hyperparameters to keep every artifact consistent.

### Reason
Random Forest became Stage 1's official model via Decision 025's label re-estimation but had
never itself been hyperparameter-tuned - it inherited defaults chosen before it was even
selected. Only XGBoost had gone through this treatment (Decision 023), for an architecture no
longer in production. User asked for this to actually be tested, alongside two other untried
levers, rather than left as an assumption.

### Impact
- Stage 1 holdout: PR-AUC 0.4129 -> 0.4228, ROC-AUC 0.883 -> 0.905, Brier 0.028 -> 0.018.
- **Stage 2's official architecture flipped isotonic -> platt** (median validation BSS 0.2271
  vs. 0.2195) - the tuned RF's changed probability distribution drove this, the same mechanism
  (opposite direction) as Decision 023's earlier XGBoost-tuning-driven flip. Holdout BSS
  improved 0.2315 -> 0.2673.
- **Alert threshold moved 0.140 -> 0.100; high-confidence boundary moved 0.350 -> 0.500**
  (re-selected fresh from the new probability distribution).
- Holdout alert-rule recall improved 60.0% -> 62.5% at similar precision (33.8% -> 34.2%);
  tier separation improved (low/medium/high observed rate 0.6%/13.3%/48.8% ->
  0.6%/20.4%/62.5%, medium/high holdout counts small - 49/24 rows).
- `research_context/report_drafts/chapter7_7.4_module2.md` is now STALE - cites pre-adoption
  numbers throughout, and its Figure 7.4 note about which calibration method the reliability
  diagram shows is now backwards (says isotonic, current production is platt). Flagged, not
  yet rewritten.
- New reusable, additive infrastructure: `fit_and_predict`'s `model_params` override (RF/LR
  path, default `None` reproduces prior behaviour exactly) and a `gradient_boosting` model path
  (not in `MODEL_NAMES`, so it never affects automatic model selection).
- `research_context/RESEARCH_DECISIONS.md` (new Decision 047), `module_2_classification/
  MODULE_CONTEXT.md` (Stage 1/Stage 2/Risk Thresholds sections), `module_2_classification/
  EXPERIMENT_LOG.md` (new entry M2-013).

### Status
Adopted

---

## 2026-08-06 - Module 2: leakage-safe lagged Module 3 risk feature tested and rejected (M2-014)

### Module
Module 2

### Change
Added `src/module2_classification/m3_risk_join.py` (new, inert - not imported
by any production stage): builds `m3_risk_lag_1/2` from Module 3's
`hybrid_risk_map.csv` `Risk` column, lagged 1-2 weeks per district
(gap-safe, same construction as `m1_forecast_join.py`). Benchmarked the
official Random Forest with vs. without these features added
(`scripts/m2_014_m3_risk_feature.py`).

### Reason
A same-week version of this idea was proposed earlier and found, before any
code was written, to have a real leakage bug (Module 3's `Risk` is
mass-conserved to that week's own actual case total). User asked for the
corrected, lagged version to actually be built and tested, not just
designed.

### Impact
- Validation median PR-AUC got WORSE with the feature added (0.3838 vs.
  0.3896 without) - holdout not checked (pre-registered rule: only spent on
  a validation winner). Rejected.
- Plausible reason: `case_anomaly_lag_1/2` already dominate Stage 1 feature
  importance, and Module 3's `Risk` is itself largely a spatially-smoothed
  transform of the same underlying case-count signal - likely redundant
  information plus one extra week of staleness, not new signal.
- No production feature set or model changed.
- `module_2_classification/EXPERIMENT_LOG.md` (new entry M2-014).

### Status
Rejected

---

## 2026-08-06 - Module 2: Venn-Abers uncertainty bands added as a companion output (M2-012)

### Module
Module 2

### Change
Added `src/module2_classification/uncertainty_bands.py`: a new, purely
additive companion output that wraps Stage 2's calibrated probability with a
statistically principled uncertainty interval, using the Inductive
Venn-Abers Predictor (IVAP) built on `sklearn.isotonic.IsotonicRegression` -
the same primitive the official isotonic Stage 2 calibrator already uses.
Same no-leakage fold structure as Stage 2's own calibrator. Standalone, not
wired into `main.py`'s `PIPELINE_STAGES` (same precedent as
`live_scoring.py`/`forecast_future_risk.py`).

### Reason
User asked to build and evaluate an uncertainty-quantification companion
output after two other proposed improvements (Stage 1 ensembling, M2-010;
district-adaptive label `k`, M2-011) failed to clear the holdout bar or
resolve their motivating problem - this one was specifically chosen because
it does not touch any existing point prediction or spend the holdout as a
selection check, so it carries no equivalent failure risk.

### Impact
- New output: `data/processed/module2/stage2_uncertainty_bands.csv`
  (18,200 rows: validation folds 2-13 + holdout).
- Point-estimate agreement with the official `calibrated_probability` is
  very close (correlation 0.997, mean |difference| 0.004) - confirms
  correctness and that no existing headline number changes.
- Interval width scales sensibly with risk tier (holdout mean width: low
  0.001, medium 0.004, high 0.011) - the real payoff, giving each calibrated
  probability an honest "how much should this be trusted" companion
  statement.
- An initial per-bin validity check was designed wrong (conflated a narrow
  per-point interval with a binned group's own sampling noise) - caught,
  corrected, and documented transparently in the eval script rather than
  silently dropped or misreported as a validity failure.
- `module_2_classification/MODULE_CONTEXT.md` (new "Uncertainty
  Quantification" section), `module_2_classification/EXPERIMENT_LOG.md`
  (new entry M2-012).

### Status
Adopted (companion output, standalone script)

---

## 2026-08-06 - Module 2: adaptive-k label audit run - homogenizes prevalence, does not fix the Colombo near-miss (M2-011)

### Module
Module 2

### Change
Read-only audit (`scripts/m2_011_adaptive_k_label.py`) testing a per-district
`k` in the epidemic-threshold label instead of Decision 025's single global
`k=3.0` - the harmonic mean/SD estimator itself was reused unchanged;
`labels.py` was not modified. Per-district `k` was chosen as the smallest
grid value bringing that district's own pooled prevalence at or below a 10%
target.

### Reason
Decision 025 flagged district-specific/variance-adaptive `k` as a candidate
future refinement (the global `k=3.0` fixes an aggregate-prevalence problem
but not every individual district, e.g. the documented Colombo 2025 Wk15
near-miss). User asked to actually test this idea and evaluate the result.

### Impact
- Cross-district prevalence spread narrowed (std 2.41pp -> 1.29pp) without
  worsening the pooled undefined rate (10.72% -> 10.72%) - a genuine partial
  win on the homogenization goal.
- Did **not** fix the Colombo 2025 Wk15 case: Colombo's own large
  `historical_sd` (209.0) means the prevalence-target rule assigns it a
  HIGHER `k` (3.5, vs. global 3.0), raising its threshold rather than
  lowering it - homogenizing cross-district prevalence and lowering one
  high-variance district's specific threshold are in tension under this
  selection rule, not aligned.
- 2017 Wk29 Colombo/Gampaha (the worst recorded epidemic year) remained
  correctly flagged under both the global and adaptive label - no regression
  on the one hard "must never miss this" sanity check.
- No pipeline rerun performed - `labels.py`, Stage 1, Stage 2, and thresholds
  are all unchanged. Adopting this would require a `feature_variant`-suffixed
  full rerun (mirrors M2-007/M2-008's pattern); left as an open decision given
  the mixed result, not committed to unilaterally.
- `module_2_classification/MODULE_CONTEXT.md` (Open Question #8 status note),
  `module_2_classification/EXPERIMENT_LOG.md` (new entry M2-011).

### Status
Audited - adoption decision pending team input.

---

## 2026-08-06 - Module 2: Stage 1 ensembling tested and rejected - holdout regression (M2-010/Decision 046)

### Module
Module 2

### Change
Benchmarked three ways of blending Stage 1's three existing models' (Random
Forest, XGBoost, Logistic Regression) out-of-fold probabilities instead of
selecting one official model (`scripts/m2_010_stage1_ensemble.py`, read-only
- reused already-computed OOF probabilities, no refitting): a simple average
of all three, a simple average of RF+XGBoost, and a no-leakage fold-aware
logistic stacking blend.

### Reason
User asked whether ensembling could improve on Decision 025's single-model
selection (Random Forest), given the three benchmarked models' validation
PR-AUCs were already close (0.358-0.377).

### Impact
- On the exact 13-fold median-PR-AUC protocol Stage 1 selection itself uses,
  the simple three-model average won on validation (0.4156 vs. Random
  Forest's 0.3766) - triggering the pre-registered one-time holdout check.
- **Holdout check showed a regression**: 0.3968 vs. Random Forest's 0.4292 -
  the same validation-improves/holdout-regresses pattern already documented
  for Module 1 (Decision 044). Not promoted.
- Production Stage 1 unchanged - still a single official Random Forest
  model.
- Secondary, non-decisive observation: on a folds-2-13-only window (needed to
  make the logistic-stacking variant comparable), plain XGBoost outscores
  both Random Forest and every ensemble variant - flagged for future
  reference, not acted on.
- `research_context/RESEARCH_DECISIONS.md` (new Decision 046),
  `module_2_classification/EXPERIMENT_LOG.md` (new entry M2-010).

### Status
Rejected

---

## 2026-08-06 - Module 1: defense entries drafted for the remediation arc

### Module
Module 1

### Change
Added five Q&A-style entries to `research_context/QUESTIONS_FOR_DEFENSE.md`: (1) why
Stage 2 stays pooled rather than per-district, backed by the M1-021/Decision 045 ablation
numbers; (2) the reporting-anomaly leakage pathway found and verified not to have
inflated Decision 030 (M1-019/Decision 043); (3) why the winning hyperparameter-search
candidate was rejected after failing the holdout check (M1-020/Decision 044); (4) the
vintage-ensembled SARIMA nowcast improvement and why it is evidence-backed
(M1-015/016/Decision 039/040); (5) a synthesis entry answering "is accuracy actually
better now?" that distinguishes the unchanged holdout MASE (0.374) from the accepted
nowcast improvement, so the two evidence tiers are not conflated under questioning.

### Reason
User asked to draft defense material from the just-consolidated remediation arc summary,
per the Living Documentation Rule's "Defense explanation improved" mapping.

### Impact
Documentation only - no code, model, or default changed.

### Status
Reference material - extend if new findings from this arc surface during further review
or if a supervisor/evaluator raises a related question not yet covered.

---

## 2026-08-06 - Module 1: remediation arc consolidated (M1-007–M1-021 summary)

### Module
Module 1

### Change
Added a consolidated "Investigation Summary" section to `module_1_forecasting/
MODULE_CONTEXT.md` (placed after the Supervisor Flag/Open Questions section) covering
the full M1-007–M1-021 arc: what was accepted (Decisions 040/041, and 034 from the
earlier phase), what was rejected (Decisions 033/036/037/038/042/043/044/045, plus one
ad hoc null check), what was learned diagnostically without being a fix (Decisions
035/043, the Colombo Wk14/Wk24-25 data-quality ceiling), and what remains open but not
built (Option B uncertainty flagging, targeted per-district Stage 2 for 3 districts).

### Reason
User asked to stop and consolidate findings after a run of 15 experiments across three
sessions - this is a documentation task (per the Living Documentation Rule), not a new
finding, so it belongs here rather than as another experiment entry.

### Impact
Documentation only - no code, model, or default changed. The bottom line recorded:
production holdout median MASE is unchanged at 0.374; the one deployed improvement is
the nowcast (Decision 040), not the backtested pipeline itself.

### Status
Reference summary - update it if a future session reopens or extends this arc.

---

## 2026-08-06 - Module 1: per-district Stage 2 rejected - pooling confirmed by direct ablation (M1-021)

### Module
Module 1

### Change
Tested training 25 separate per-district Stage 2 models instead of the current pooled
model (Decision 002/014), holding hyperparameters, feature set (minus the now-redundant
`District` categorical), fold structure, and evaluation method fixed. A three-tier data-
sufficiency rule (no-op below 104 trainable rows, fixed tree count 104-207, early
stopping at 208+) protected against fitting on token amounts of per-district data.
**Decisively worse**: validation-aggregate median MASE 0.7473 vs. pooled's 0.5821
(+28.4%), only 1/13 folds and 4/25 districts improved - no holdout check performed
(safeguard not cleared). The 4 districts that improved (`Monaragala`, `Mannar`,
`Vavuniya`, `Matale`) are already-flagged cases where pooled Stage 2 underperforms.

### Reason
Following up on the user's request to try a genuinely structural change (not another
tuning pass) after every recent tuning ablation returned null - this directly tests, for
the first time with real evidence, the pooling decision itself.

### Impact
New, additive functions `train_and_predict_fold_per_district()`/
`train_and_predict_holdout_per_district()` in `compensation_model.py` (existing pooled
functions untouched). Fixed a latent bug in `_prepare_xy()` (only categorical-encodes
`District` when present in `feature_columns` - harmless until this experiment needed a
feature set without it). New `scripts/evaluate_per_district_stage2.py`. No production
default changed.

### Status
Rejected. Stage 2 remains pooled - directly confirms Decision 002/014's original
reasoning with ablation evidence.

---

## 2026-08-06 - Module 1: XGBoost hyperparameter search rejected - winner failed the holdout check (M1-020)

### Module
Module 1

### Change
Ran a 40-candidate randomized search over Stage 2's XGBoost hyperparameters
(`max_depth, learning_rate, subsample, colsample_bytree, reg_lambda, min_child_weight`,
fixed and never tuned since the earliest implementation), scored via
`combine.compute_district_fold_metrics()` on walk-forward folds 2-14 only - the exact
function/metric production already publishes (verified: candidate 0, the production
defaults, reproduced the published 0.5821 validation-aggregate median MASE exactly).
5/39 candidates cleared a pre-registered overfitting safeguard (beat baseline AND a
majority of folds AND a majority of districts); the best reached 0.5659 (-2.8%). **The
one-time holdout check on that single candidate showed a regression**: 0.3874 vs.
production's 0.3741 (+3.6%) - rejected. No other qualifying candidate was checked against
holdout, per the pre-registered rule.

### Reason
Following up on the user's request to scope and then run a proper walk-forward-validated
hyperparameter search - the genuinely untried lever after every other Stage 1/2 tuning
attempt this session returned null.

### Impact
New `scripts/search_stage2_hyperparameters.py`. Additive, backward-compatible `xgb_params`
override on `train_and_predict_fold()`/`train_and_predict_holdout()`/
`_fit_with_early_stopping()` (`compensation_model.py`) - default `None` reproduces
production behavior exactly. No production default changed.

### Status
Rejected. Production `XGB_BASE_PARAMS` unchanged.

---

## 2026-08-06 - Module 1: reporting-guard leakage pathway audited (not material); real-time catch-up adjustment ruled out (M1-019)

### Module
Module 1

### Change
While scoping the reporting catch-up spike problem (Colombo/Gampaha 2026 Wk24-25),
found that the retrospective reporting-anomaly detector (`flag_reporting_anomalies()`,
Decision 026/028) needs the rebound week's own case count to confirm a dip, so features/
masks derived from it are subtly informed by the very week they help predict - a real
leakage pathway. Two follow-up checks:

1. **Materiality check**: built a leakage-closed variant (new
   `reporting_anomalies.flag_reporting_dip_causal()`, no rebound confirmation) and
   re-ran the full Stage 2 + combine pipeline (`scripts/evaluate_reporting_leakage_fix.py`,
   new `assemble_stage2_table()`/`run_stage2_pipeline()` path overrides). Result: median
   holdout MASE 0.3655 (leakage-closed) vs. 0.3741 (production) - **not worse, if
   anything slightly better**. Decision 030's promotion stands; no retraction needed.
2. **Real-time usability check**: characterized the causal detector's precision/recall
   against the retrospective flag (`scripts/evaluate_causal_dip_detector.py`) - 100%
   recall, only 42.9% precision (worse for `Colombo`/`Gampaha`: 46.2%/30.0%). **Rules
   out** building any real-time point-forecast adjustment for catch-up spikes - more
   than half of live flags would be false alarms on a genuine decline.

### Reason
Following up on the reporting-catch-up-spike scoping plan's own recommendation: verify
research integrity (the leakage pathway) and get real numbers on real-time detector
viability before building anything.

### Impact
New `flag_reporting_dip_causal()`, `scripts/evaluate_causal_dip_detector.py`,
`scripts/evaluate_reporting_leakage_fix.py`. Additive path-override params on
`compensation_model.assemble_stage2_table()`/`run_stage2_pipeline()` (production
defaults unchanged). No production artifact or default path changed - all new outputs
use isolated `_causal_safe` suffixes.

### Status
Leakage documented, verified not material (no action needed). Real-time point-forecast
adjustment (Option A) rejected. Uncertainty-flagging alternative (Option B) remains open,
not built.

---

## 2026-08-05 - Module 1: retroactive nowcast spot-check scaled up; robust aggregation tested, not promoted (M1-018)

### Module
Module 1

### Change
Scaled the retroactive nowcast spot-check from 175 to 600 (district, week) pairs (25
districts x last 24 known weeks) and added selectable Stage 1 ensemble aggregation rules
(`aggregation="mean"|"median"|"trimmed_mean"`) to test whether a robust-to-outliers
combination reduces the individual-week noise seen in the smaller sample.
`forecast_future._ensembled_next_week_sarima()` was split into
`_collect_vintage_forecasts()` (fitting) and `_aggregate_vintage_forecasts()`
(aggregation) so comparing rules doesn't require refitting per rule;
`forecast_district()` gained a `precomputed_sarima_forecast` override for the same
reason.

**Results**: the bigger sample confirms a real but more modest improvement (median
absolute error -10%, mean -10%, individual-week win rate 56.8% - not near-universal, and
lower than the smaller sample's noisier 59%, consistent with that being sample noise, not
a weakening effect). Median and trimmed-mean do NOT meaningfully beat plain mean (a ~1%
difference, and mathematically identical to each other at `ensemble_window=4`) - the
remaining per-week noise looks like genuine forecast uncertainty, not an artifact of
vintage combination. `Mannar` is a clean, complete loser regardless of aggregation
(0/24 weeks) - a distinct, already-diagnosed Stage 1 issue (Decision 017).

### Reason
User asked whether the noisier-than-expected first spot-check could be reduced by (a) a
bigger sample and (b) a more robust ensemble aggregation.

### Impact
Modified `forecast_future.py` (new aggregation infrastructure, `aggregation="mean"`
remains the only production default), `scripts/backtest_nowcast_ensemble.py` (rewritten
to compare 3 aggregation rules efficiently). No production default changed.

### Status
Accepted as evidence; robust aggregation not promoted (no clear benefit found).

---

## 2026-08-05 - Module 1: prospective nowcast accuracy tracking added (M1-017)

### Module
Module 1

### Change
New `src/module1_forecasting/nowcast_tracking.py`: `append_to_nowcast_log()` (wired into
`run_nowcast()`, on by default) permanently logs every nowcast prediction
(`data/processed/module1/nowcast_prediction_log.csv`); `reconcile_nowcast_log()` (new
`module1_nowcast_reconcile` step in `scripts/refresh_dashboard_data.py`) joins the log
against real case counts as they arrive, writing
`outputs/metrics/module1/nowcast_prospective_accuracy.csv`. Seeded with the already-
generated 2026 Wk26 nowcast (25 rows); first reconciliation correctly shows 0/25 resolved.

### Reason
M1-016's production change (vintage-ensembled SARIMA) has no existing evidence source that
can check its real-world accuracy - every other Module 1 metric scores against data
already in the dataset. This builds the only honest way to get that evidence: log now,
resolve as real weeks pass.

### Impact
New file `nowcast_tracking.py`; modified `forecast_future.py` (`run_nowcast()` now logs by
default, new `--no-log` CLI flag), `scripts/refresh_dashboard_data.py` (new step), `src/config.py`
(two new path constants). Pure infrastructure - no existing model or evaluation changed.

### Status
Accepted. `nowcast_prospective_accuracy.csv` will grow additively as real weeks resolve;
check it periodically rather than assuming silence means nothing to report.

---

## 2026-08-05 - Module 1: vintage-ensembled SARIMA promoted to the production nowcast (M1-016)

### Module
Module 1

### Change
`forecast_future.run_nowcast()` (the production "predict next week using all data up to
now" pathway) now defaults to the vintage-ensembled Stage 1 prediction validated at full
25-district scale in M1-015/Decision 039: instead of one SARIMA fit, it averages, in
transformed space, `MODULE1_NOWCAST_ENSEMBLE_WINDOW` (4) independent fits on the history
trimmed back by 0-3 additional weeks, each extended forward to the same next-week target
(new `forecast_future._ensembled_next_week_sarima()`). Each vintage is refit fresh (a
one-off nowcast call has no persisted state to reuse, unlike the rolling evaluator) -
`ensemble_window` fits instead of 1, still cheap. `forecast_district()`/
`run_future_forecast()` gained an `ensemble_window` parameter defaulting to `None`
(unaffected 8-week recursive path); only `run_nowcast()` defaults it on. New
`n_sarima_vintages` output column for transparency. Verified backward-compatible
(`ensemble_window=None` reproduces the old single-fit numbers exactly). Production
`nowcast_next_week.csv` regenerated for all 25 districts.

### Reason
User asked to bring the M1-015 rolling-evaluation improvement into the actual production
nowcast, after confirming it does not change the core Stage 1 -> Stage 2 architecture.

### Impact
Modified `forecast_future.py`, `src/config.py` (new `MODULE1_NOWCAST_ENSEMBLE_WINDOW`
constant). Does NOT touch Stage 2, the additive combination formula, `run_future_forecast()`'s
default 8-week path, or the validated walk-forward/holdout pipeline (`main.py`,
`combine.py`) - the headline holdout MASE numbers are unaffected. CLI: `--nowcast
[--ensemble-window N]`.

### Status
Accepted.

---

## 2026-08-04 - Module 1: vintage-ensembled SARIMA accepted (M1-015); less-frequent refit rejected (M1-014)

### Module
Module 1

### Change
Two more candidate fixes for the weekly-SARIMA-refit instability found in M1-011/Decision
035, tested after warm-starting (M1-013) was rejected:

1. **M1-014 (Decision 038, rejected):** refitting every 4 weeks instead of weekly, using
   `SARIMAXResults.append(refit=False)` to incorporate new data between refits without
   re-optimizing. ~4x cheaper but no meaningful stability improvement on a cheap sample -
   not run at full scale.
2. **M1-015 (Decision 039, ACCEPTED):** averaging each week's fresh SARIMA forecast with
   the last 3 weeks' own independently-fitted models' forecasts for the same target week
   (`rolling_one_step._vintage_ensemble_step()`, cheap `.forecast()` extension, no extra
   refitting cost). Full 25-district test: districts with Stage 2 helping in rolling mode
   rose from 10/25 to **24/25**; rolling sMAPE improved for 22/25 districts (median 58.8%
   → 56.8%, several districts improving 10-15%). **This is the first broad accuracy
   improvement found across the entire M1-007 through M1-015 investigation arc.**

### Reason
User asked to try the two remaining candidates flagged after M1-013's rejection.

### Impact
New: `rolling_one_step._low_freq_refit_step()`, `_vintage_ensemble_step()` (both additive,
off by default). New scripts: `scripts/run_rolling_one_step_ensemble_parallel.py`. No
production Stage 1/2 default path changed - both evaluated via `_ensemble`/isolated
artifact paths. **Recommended follow-up** (not implemented this session): extend
`forecast_future.run_nowcast()` to use the same vintage-ensemble approach, since the
production nowcast currently uses a single SARIMA refit and does not yet benefit from
this finding.

### Status
M1-014: Rejected. M1-015: **Accepted** - the strongest positive result across this whole
remediation effort, pending a decision on rolling it into the production nowcast path.

---

## 2026-08-04 - Module 1: SARIMA warm-starting tested and rejected (M1-013)

### Module
Module 1

### Change
Tested whether seeding each week's rolling SARIMAX refit with the previous week's
converged parameters (`start_params`) stabilizes weekly-refit predictions - the leading
untried candidate flagged after M1-011 root-caused the rolling-mode DM gap to weekly
SARIMA refit instability. Added backward-compatible `start_params`/`return_params`
parameters to `baseline_sarima.fit_and_forecast()` and a `warm_start` parameter to
`rolling_one_step.rolling_one_step_district()` (both off/unset by default - no existing
caller's behavior changes). A cheap 60-week/2-district check, run before any full-scale
evaluation, found warm-started and cold-started predictions are virtually identical while
warm-started fits take 5-10x longer per fit - fully falsifying the hypothesis without
needing the originally-planned full 25-district run (which was therefore skipped, a
disclosed scope decision, not a silent gap).

### Reason
User asked to build and test the warm-start idea proposed as the most evidence-backed
lever for improving next-week prediction accuracy, after being told upfront it was
untested and not guaranteed to work.

### Impact
Modified `baseline_sarima.py`, `rolling_one_step.py` (both additive/backward-compatible).
No production code path, model, or default artifact changed - `warm_start=False` remains
the only path used anywhere by default.

### Status
Rejected. Open Question #17 (weekly SARIMA refit instability) remains open; untried
candidates are a less frequent refit cadence or cross-refit smoothing/ensembling.

---

## 2026-08-04 - Module 1 follow-up: rolling-DM gap root-caused; STL+ARIMA pilot rejected

### Module
Module 1

### Change
Two follow-up investigations from the prior remediation pass (Decisions 035-036,
`EXPERIMENT_LOG.md` M1-011/M1-012):

1. **M1-011 (Decision 035):** root-caused Open Question #17 (why rolling-mode Stage 2
   benefit is far weaker than the holdout backtest's). New `scripts/
   diagnose_rolling_dm_gap.py` re-scored every rolling-evaluated week with the walk-
   forward fold model that actually owned that week (via `compensation_model.
   compute_fold_boundaries()`), using new `sarima_prediction_overrides`/`model_resolver`
   parameters added to `rolling_one_step.rolling_one_step_district()` (pure
   recombination, no retraining). **Result: this made things worse, not better**
   (Stage-2-helps districts 10/25 → 8/25; DM-significant 2/25 → 0/25) - ruling out "the
   frozen model generalizes poorly" as the cause. Instead, weekly-refit and fold-refit
   SARIMA predictions for the same historical weeks are barely correlated (mean r=0.13),
   and this drift correlates with rolling-mode error (mean r=0.26). **Conclusion: weekly
   SARIMA refit instability itself is the dominant driver**, not Stage 2. A more stable
   refit cadence is flagged as future work, not implemented this session.
2. **M1-012 (Decision 036):** piloted STL + ARIMA (`src/module1_forecasting/
   stl_arima.py`, using `statsmodels.tsa.forecasting.stl.STLForecast`) on 3 non-seasonal
   districts (`Colombo`, `Gampaha`, `Kurunegala`), targeting the 18/25-non-seasonal-
   SARIMA finding. **Rejected**: 0/3 districts beat their existing SARIMA on validation
   MASE; a visual decomposition check confirmed this is a genuine result, not an
   implementation artifact. No wider rollout planned.

Per the user's explicit framing before this work began, neither investigation was
expected or promised to improve accuracy - both are reported honestly regardless of
outcome, consistent with the project's established practice.

### Reason
User asked to run the remaining candidate investigations flagged at the end of the prior
session and see whether they produced improvements.

### Impact
New: `scripts/diagnose_rolling_dm_gap.py`, `scripts/pilot_stl_arima.py`,
`src/module1_forecasting/stl_arima.py`. Modified: `rolling_one_step.py` (new reusable
`sarima_prediction_overrides`/`model_resolver` parameters, default behavior unchanged).
No production Stage 1/2 config, model, or default artifact changed.

### Status
M1-011: accepted as a documented root cause (not a fix). M1-012: rejected.

---

## 2026-08-04 - Module 1 remediation pass: next-week nowcast + three Stage 2 ablations + an important rolling-DM caveat

### Module
Module 1

### Change
Four related pieces of work addressing a prior review's critique of Module 1, executed as
a phased plan (`Decisions 031-034`, `EXPERIMENT_LOG.md` M1-007 through M1-010):

1. **M1-010 (Decision 031):** `forecast_future.run_nowcast()` - genuine `horizon=1`
   "predict next week using all data up to now" production output
   (`nowcast_next_week.csv`), wired into `refresh_dashboard_data.py`. Both this and
   `future_forecast.csv` now carry an `evidence_tier` column. Found and fixed a latent bug:
   `forecast_district()` had never been updated for the M1-006B reporting-delay features
   added to production `FEATURE_COLUMNS` (Decision 030), so `run_future_forecast()` had
   been raising `KeyError` since that 2026-07-29 promotion - `future_forecast.csv` was
   stale and regenerated with the fix.
2. **M1-008 (Decision 032):** first full 25-district rolling one-step `--scope all`
   backtest (new `scripts/run_rolling_one_step_parallel.py`, ~43 min parallelized vs. a
   projected ~3.6h serial) plus a new higher-sample Diebold-Mariano test
   (`rolling_one_step.compute_dm_results_rolling()`). **Important finding, flagged not
   spun**: only 2/25 districts reach significance (both showing Stage 2 significantly
   worse), and only 10/25 show Stage 2 helping at all in this deployment-faithful mode -
   markedly weaker than the holdout backtest's 23/25-improve headline. Identified a real
   methodological reason this is NOT a simple bigger-n replication (fold-refit vs.
   weekly-refit SARIMA input-distribution mismatch against the frozen final model) -
   flagged as new Open Question #17, the module's current highest priority.
3. **M1-007 (Decision 033):** `residual_lag_3/4` + causal EWMA Stage 2 feature extension,
   targeting the 23/25-districts-fail-Ljung-Box gap. **Rejected**: validation MASE
   improved but holdout MASE regressed (0.374 → 0.395) - kept as an ablation switch only.
4. **M1-009 (Decision 034):** per-district Stage 2 shrinkage weight
   (`residual_transform.combine_stage2_forecast(weight=...)`, `shrinkage.py`), targeting
   `Kilinochchi`/`Mannar`'s holdout regression. **Correctly declined to "fix" either
   target district** (their problem is fold-specific, not validation-visible); instead
   found a small, holdout-confirmed win for two different districts (`Monaragala`,
   `Vavuniya`, ~1.6% each). Available via `apply_shrinkage=True`, not promoted to
   default production given the small magnitude.

STL+SARIMA (targeting the 18/25-non-seasonal-districts finding) remains explicitly
deferred a third time - flagged as the largest remaining lift, not attempted this session.

### Reason
User requested the critique points from a prior review be addressed, plus a genuine
production "predict next week" capability.

### Impact
New files: `scripts/run_rolling_one_step_parallel.py`, `scripts/m1_007_residual_lag_extension.py`,
`src/module1_forecasting/shrinkage.py`. Modified: `forecast_future.py`, `rolling_one_step.py`,
`compensation_model.py`, `combine.py`, `residual_transform.py`, `config.py`,
`refresh_dashboard_data.py`. Regenerated: `future_forecast.csv` (bugfix), new
`nowcast_next_week.csv`, `rolling_one_step_predictions.csv`/`_metrics.csv`, new
`rolling_one_step_dm_test.csv`. Production Stage 1/2 defaults **unchanged** - every
ablation writes to isolated `feature_variant`-suffixed paths.

### Status
Accepted (M1-010, M1-008 as evidence/capability), Rejected (M1-007), Partial adopt (M1-009,
not wired into default production path).

---

## 2026-07-31 - Presentation outlines: presentation-safe revision (all modules)

### Module
Presentation / Modules 1–3

### Change
Revised `PRESENTATION_MODULE{1,2,3}_SLIDES.md` to exclude negative results and questionable material from slide content. Each file now has a presentation-safe policy, trimmed slide decks (6–7 slides), and an *Excluded from slides (report/viva only)* reference table. Report chapters retain full honest evaluation.

### Reason
User requested presentation decks that do not surface failures, null results, or caveats that weaken the viva narrative.

### Impact
Slides lead with strengths (MASE gains, calibration BSS, Moran’s I, risk map); limitations stay in report/viva prep only.

### Status
Accepted.

---

## 2026-07-31 - Presentation outline: Module 3 slides

### Module
Presentation / Module 3

### Change
Added slide-ready Module 3 pack outline: `research_context/PRESENTATION_MODULE3_SLIDES.md` (8 core slides + optional related-works and extra risk surfaces). Maps to Figs 6.4/7.5, Tables 7.5–7.6, plus `feature_importance.png` and `convergence_plot.png`. Emphasises Moran’s I nuance and M3-005 null aggregate-fit honesty.

### Reason
Complete the three-module FYP presentation outlines.

### Impact
All module slide packs now available under `research_context/PRESENTATION_MODULE{1,2,3}_SLIDES.md`.

### Status
Accepted.

---

## 2026-07-31 - Presentation outline: Module 2 slides

### Module
Presentation / Module 2

### Change
Added slide-ready Module 2 pack outline: `research_context/PRESENTATION_MODULE2_SLIDES.md` (8 core slides + optional related-works and live-scoring). Uses Decision 025 production numbers (Random Forest → isotonic; τ = 0.14 / high = 0.35). Maps to Figs 6.3/7.4 and Tables 7.3/7.4/7.7.

### Reason
Continue FYP presentation module packs after Module 1 outline.

### Impact
Module 2 presentation content and asset checklist ready for PowerPoint/Google Slides; guards against superseded XGBoost / τ = 0.17 claims.

### Status
Accepted.

---

## 2026-07-31 - Presentation outline: Module 1 slides

### Module
Presentation / Module 1

### Change
Added slide-ready Module 1 pack outline: `research_context/PRESENTATION_MODULE1_SLIDES.md` (8 core slides + optional related-works and operational-check). Maps content to existing Figs 6.2, 7.2, 7.3 and Tables 7.1–7.2; flags missing feature-importance chart.

### Reason
Team is building FYP presentation module packs using the sample deck structure as a guide.

### Impact
Module 1 presentation content and asset checklist are ready to convert into PowerPoint/Google Slides.

### Status
Accepted.

---

## 2026-07-30 - Report figure: Figure 5.1 high-level system architecture

### Module
Report writing (Chapter 5 / system overview)

### Change
Created whole-system architecture diagram:
- `figure_5_1_system_architecture.png` (+ alias `figure_high_level_system_architecture.png`)
- `figure_5_1_system_architecture.drawio`
- Generator: `generate_figure_5_1_architecture.py`
Shows data acquisition → Decision 013 shared preprocessing → three parallel residual-compensation modules → evaluation → Streamlit dashboard.

### Reason
Figure 5.1 was planned but missing; needed for Chapter 5 and viva/system overview.

### Impact
High-level architecture figure ready for Word paste.

### Status
Accepted.

---

## 2026-07-30 - Report draft: Appendix A Individual Contributions

### Module
Report writing (Appendix A)

### Change
Rewrote Appendix A from interim progress narratives to completed-project contributions. Module leads retained (Bandara M1, Nethma M2, Karunarathna M3). Shared workloads split: WER scrape (Bandara), Open-Meteo climate (Nethma), spatial/demographic layers (Karunarathna), plus shared Decision 013 cleaning, dashboard views, and report sections. File: `research_context/report_drafts/appendix_a_individual_contributions.md`.

### Reason
Interim appendix wording was outdated (“upcoming phases”, SARIMAX/NASA-era claims) and did not reflect equal shared preprocessing ownership.

### Impact
Appendix A paste-ready for Word; team should confirm name/coordinator details.

### Status
Accepted for drafting.

---

## 2026-07-30 - Report structure + draft: Chapters 8 and 9

### Module
Report writing (Chapters 8–9)

### Change
Accepted Chapter 8 structure (**8.1 Conclusion**, **8.2 Further Work**) and Chapter 9 structure (**9.1–9.5**). Drafted paste-ready `chapter8_conclusion_further_work.md` (~1,180 words) and `chapter9_challenges_limitations.md` (~1,530 words). Updated `REPORT_STRUCTURE.md` and `CHAPTER_STATUS.md`.

### Reason
Evaluation chapter complete; closing chapters needed before Word freeze.

### Impact
Chapters 8–9 ready for paste; References / Appendices still pending.

### Status
Accepted; drafts complete.

---

## 2026-07-30 - Report draft: Chapter 7.6–7.8 (comparative, discussion, summary)

### Module
Report writing (Chapter 7)

### Change
Polished paste-ready **7.6 Cross-Module Comparative Analysis** (incl. Table 7.7 / M2-009), **7.7 Discussion**, and **7.8 Summary**. Chapter 7 topic-by-topic set (7.1–7.8) complete (~4,475 words). Updated `REPORT_DIAGRAM_PLAN.md` with Table 7.7.

### Reason
Final topics in the Chapter 7 drafting sequence after Modules 1–3 evaluation sections.

### Impact
Full Chapter 7 ready for Word paste; remaining visual gap is Figure 7.1 protocol schematic.

### Status
Accepted for drafting (Word paste pending).

---

## 2026-07-30 - Report figures: Chapter 7 Figure 7.5 (Module 3 risk surface)

### Module
Report writing (Chapter 7)

### Change
Copied peak-week IDW risk surface to `figure_7_5_module3_risk_surface.png` (from `outputs/figures/module3/risk_surface_peak_week.png`, 2017 Week 29). Polished section 7.5 with Tables 7.5–7.6 and honest M3-005 null aggregate-fit wording.

### Reason
Section 7.5 needed the canonical Module 3 visualisation figure for Word paste.

### Impact
Section 7.5 paste-ready; Figures 7.2–7.5 now created (Figure 7.1 protocol schematic still pending).

### Status
Accepted.

---

## 2026-07-30 - Report figures: Chapter 7 Figure 7.4 (Module 2 isotonic reliability)

### Module
Report writing (Chapter 7)

### Change
Generated `figure_7_4_module2_reliability.png` from `stage2_compensated_predictions.csv` (selected isotonic architecture). Polished section 7.4 with Tables 7.3–7.4. Explicitly rejected older Platt-labelled reliability PNGs under `outputs/figures/module2/`.

### Reason
Figure 7.4 must match Decision 025 / production Stage 2 = isotonic, not superseded Platt diagrams.

### Impact
Section 7.4 paste-ready with correct calibration figure.

### Status
Accepted.

---

## 2026-07-30 - Report figures: Chapter 7 Figures 7.2 and 7.3 (Module 1)

### Module
Report writing (Chapter 7)

### Change
Generated paste-ready PNGs:
- `figure_7_2_module1_holdout_forecasts.png` from `final_combined_predictions.csv` (Colombo/Gampaha holdout)
- `figure_7_3_module1_holdout_mase.png` from `combined_vs_baseline_metrics.csv` (holdout MASE Stage 1 vs Stage 1+2)
Script: `research_context/report_drafts/diagrams/generate_figure_7_2_7_3.py`. Updated `REPORT_DIAGRAM_PLAN.md` and Chapter 7 drafts.

### Reason
Section 7.3 needed evidence figures matching Table 7.1; existing `future_forecast_*.png` files are operational and unsuitable.

### Impact
Figures 7.2–7.3 ready for Word paste; medians match documented 0.622 → 0.374 holdout MASE; Kilinochchi/Mannar exceptions marked.

### Status
Accepted.

---

## 2026-07-30 - Report structure: Accepted Chapter 7 Evaluation (full 7.1–7.8)

### Module
Report writing (Chapter 7)

### Change
Accepted full three-module Chapter 7 structure (7.1 Introduction → 7.2 Strategy → 7.3 Module 1 → 7.4 Module 2 → 7.5 Module 3 → 7.6 Comparative → 7.7 Discussion → 7.8 Summary). Updated `REPORT_STRUCTURE.md`, `CHAPTER_STATUS.md`, and `REPORT_DIAGRAM_PLAN.md` (Figures 7.1–7.5; Tables 7.1–7.6). Full paste-ready draft written to `research_context/report_drafts/chapter7_evaluation.md`, superseding the M1/M2-only numbering in `chapter7_m1_m2_evaluation.md`.

### Reason
Module 3 results are available; Chapter 6 implementation is complete; Evaluation needed a locked outline matching Modules 1–3 with honest M3 null aggregate-fit reporting.

### Impact
Chapter 7 ready for topic paste / Word assembly; figure PNGs still to be exported from `outputs/`.

### Status
Accepted; draft complete (figures pending).

---

## 2026-07-30 - Report draft: Full Chapter 6 Implementation (hybrid 6.1–6.8)

### Module
Report writing (Chapter 6)

### Change
Accepted hybrid Chapter 6 structure and wrote full paste-ready draft in `research_context/report_drafts/chapter6_implementation.md` (~4,840 words): corrected datasets (Open-Meteo; GADM L1; census/elevation; no NASA POWER/CHIRPS production stack), Decision 013 shared pipeline, Module 1 SARIMA→XGBoost, Module 2 RF→isotonic, Module 3 KDE/Moran→RF iterative α=0.05 (IDW viz-only), Streamlit research/operational dashboard. Updated `REPORT_STRUCTURE.md`, `CHAPTER_STATUS.md`, `REPORT_DIAGRAM_PLAN.md`. Created Figures 6.1–6.5 under `report_drafts/diagrams/`.

### Reason
Interim Chapter 6 was obsolete; Module 3 is now complete and Chapter 5 design is finalized — Implementation needed a full corrected rewrite.

### Impact
Chapter 6 ready for Word paste; evaluation numbers remain in Chapter 7.

### Status
Accepted for drafting (Word paste pending).

---

## 2026-07-30 - Report draft: Chapter 5.6 Summary (Chapter 5 topic drafts complete)

### Module
Report writing (Chapter 5)

### Change
Drafted paste-ready **5.6 Summary** (~175 words) in `research_context/report_drafts/chapter5_5.6_summary.md`, synced into `chapter5_analysis_and_design.md`. Names official Stage 1/2 models per module and closes Chapter 5 with transition to Implementation.

### Reason
Final topic in the Chapter 5 topic-by-topic drafting sequence.

### Impact
Chapter 5 sections 5.1–5.6 paste-ready; Figures 5.3–5.6 created. Remaining: Word paste; optional Figures 5.1–5.2 export.

### Status
Accepted for drafting (awaiting Word paste).

---

## 2026-07-30 - Report draft + Figure 5.6: Chapter 5.5 Integration design

### Module
Report writing (Chapter 5)

### Change
Drafted paste-ready **5.5 Integration and Output Design** (~520 words) in `research_context/report_drafts/chapter5_5.5_integration.md`, synced into `chapter5_analysis_and_design.md`, and created **Figure 5.6** (`figure_5_6_integration_dashboard.drawio` + PNG). Shows M1/M2/M3 outputs → Streamlit → dashboard views → research vs operational evidence tiers.

### Reason
Topic-by-topic Chapter 5 drafting after 5.4.3; integration needed matching section + diagram depth aligned with the research/operational dashboard split.

### Impact
Figures 5.3–5.6 and sections 5.4.1–5.5 ready for Word paste; remaining Chapter 5 topic is 5.6 Summary (short).

### Status
Accepted for drafting (awaiting Word paste).

---

## 2026-07-30 - Report draft + Figure 5.5: Chapter 5.4.3 Module 3 design

### Module
Report writing (Chapter 5)

### Change
Drafted paste-ready **5.4.3 Module 3** (~610 words) in `research_context/report_drafts/chapter5_5.4.3_module3.md`, synced into `chapter5_analysis_and_design.md`, and created **Figure 5.5** (`figure_5_5_module3_architecture.drawio` + PNG). Architecture shown: KDE + Moran’s I → RF residual compensation → iterative update (`α = 0.05`) → hybrid risk map; IDW marked visualization-only.

### Reason
Topic-by-topic Chapter 5 drafting after 5.4.2 / Figure 5.4; Module 3 needed matching section + diagram depth aligned with verified implementation.

### Impact
All three module design subsections (5.4.1–5.4.3) and Figures 5.3–5.5 are ready for Word paste; next topic is 5.5 Integration (+ Figure 5.6).

### Status
Accepted for drafting (awaiting Word paste).

---

## 2026-07-30 - Report draft + Figure 5.4: Chapter 5.4.2 Module 2 design

### Module
Report writing (Chapter 5)

### Change
Drafted paste-ready **5.4.2 Module 2** (~620 words) with Table 5.2 in `research_context/report_drafts/chapter5_5.4.2_module2.md`, synced into `chapter5_analysis_and_design.md`, and created corrected **Figure 5.4** (`figure_5_4_module2_architecture.drawio` + PNG) in the same four-column style as Figure 5.3. Architecture shown: Random Forest Stage 1 → isotonic Stage 2 → alert/risk-tier outputs.

### Reason
Topic-by-topic Chapter 5 drafting after 5.4.1 / Figure 5.3; Module 2 needed matching section + diagram depth.

### Impact
Chapter 5 Module 2 design + figure ready for Word paste; next topic is 5.4.3 Module 3 (+ Figure 5.5).

### Status
Accepted for drafting (awaiting Word paste).

---

## 2026-07-30 - Figure 5.3 Module 1 architecture created (from interim diagram)

### Module
Report writing (Chapter 5 / diagrams)

### Change
Created corrected **Figure 5.3** Module 1 high-level architecture from the interim four-column diagram: `research_context/report_drafts/diagrams/figure_5_3_module1_architecture.drawio` (+ PNG). Key fixes: Stage 2 = **XGBoost only** (not RF/XGBoost); climate source = **Open-Meteo**; metrics = **RMSE/MAE/sMAPE/MASE**; climate excluded from Stage 1; residual equations retained.

### Reason
User requested the Module 1 architecture figure before drafting 5.4.2, using the old interim figure as the visual template.

### Impact
Figure ready for Word paste under section 5.4.1; next topic remains 5.4.2 Module 2 (+ Figure 5.4).

### Status
Accepted for drafting (Word paste pending).

---

## 2026-07-30 - Report draft: Chapter 5.4.1 Module 1 design (+ Figure 5.3)

### Module
Report writing (Chapter 5)

### Change
Expanded paste-ready section **5.4.1 Module 1: Hybrid Time-Series Case Forecasting** in `research_context/report_drafts/chapter5_5.4.1_module1.md` (~580 words), synced into `chapter5_analysis_and_design.md`, and aligned Figure 5.3 caption/notes in `REPORT_DIAGRAM_PLAN.md` / `CHAPTER_STATUS.md`.

### Reason
Topic-by-topic Chapter 5 drafting after 5.3; Module 1 design needed fuller narrative (shared vs module-specific preprocessing, SARIMA-only Stage 1, residual interface, XGBoost Stage 2) with explicit Figure 5.3 placement.

### Impact
Chapter 5 Module 1 design subsection ready for Word paste; next topic is 5.4.2 Module 2 (+ Figure 5.4).

### Status
Accepted for drafting (awaiting Word paste / figure export).

---

## 2026-07-30 - Module 3 verified complete (Stage 1 + Stage 2 + evaluation + risk surface)

### Module
Module 3 / Report writing

### Change
Verified against living docs and `outputs/metrics/module3/results_summary.txt` that Module 3 is implementation-complete: Stage 1 KDE+Moran's I, Stage 2 RF residual compensation with iterative loop (`alpha=0.05`), evaluation, continuous risk-surface rendering. Updated `CHAPTER_STATUS.md` so Module 3 is no longer treated as deferred for architecture/approach chapters; Chapter 6/7 Module 3 subsections remain to be drafted from these artifacts.

### Key results (do not oversell Stage 2 fit)
- Stage 1 aggregated Moran’s I = **0.70**, p_sim = **0.001** (significant clustering); NE-monsoon representative week not significant (nuance to report).
- Stage 2 spatial CV residual MAE ≈ **33.1**, RMSE ≈ **54.8**.
- Iterative loop converges at **iteration 1** with `alpha=0.05`.
- Stage 1 vs Stage 2 fit to cases: corr **0.824 → 0.821**, MAE/RMSE marginally **worse** after Stage 2 — verified null/negative aggregate-fit result (M3-005); Stage 2 value is mainly explanatory (population/climate feature importance), not aggregate error reduction at chosen alpha.
- Top features: `population_density` (~0.41), `Estimated_Population` (~0.18).

### Status
Module 3 research pipeline: complete. Report chapters 6.x/7.x Module 3 text: pending.

---

## 2026-07-30 - Report draft: Expanded Chapter 5 Analysis and Design

### Module
Report writing (Chapter 5)

### Change
Accepted expanded Chapter 5 structure (5.1–5.6) and drafted full design content in `research_context/report_drafts/chapter5_analysis_and_design.md`. Updated `REPORT_STRUCTURE.md`, `CHAPTER_STATUS.md`, and `REPORT_DIAGRAM_PLAN.md` (Figures 5.1–5.6; Tables 5.1–5.2; Module 1/2 figure captions renumbered 5.3/5.4).

### Reason
Interim Chapter 5 was figure-heavy and outdated (undifferentiated preprocessing, fine-scale wording, Module 3/figure-only gaps). Needed major-chapter design depth with Decision 013 shared vs module-specific architecture.

### Impact
Team can paste Analysis and Design text into Word. Earlier 5.3.1/5.3.2 numbering superseded by 5.4.x.

### Status
Drafting

---

## 2026-07-30 - Report draft: Expanded Chapter 4 Our Approach

### Module
Report writing (Chapter 4)

### Change
Accepted expanded Chapter 4 structure (4.1–4.9) and drafted full conceptual content for sections 4.2–4.9 in `research_context/report_drafts/chapter4_our_approach.md`. Updated `REPORT_STRUCTURE.md`, `CHAPTER_STATUS.md`, and `REPORT_DIAGRAM_PLAN.md` (Figures 4.1–4.5; Tables 4.1–4.2).

### Reason
Interim Chapter 4 was too short and technically outdated (fine-scale, SARIMAX, undecided Stage-2 models, Module 2 climate residual Stage 2, Command Centre / scenario simulation). Chapter 4 needed major-chapter depth while staying conceptual (design/implementation/metrics remain in Chapters 5–7).

### Impact
Team can paste expanded Our Approach text into Word. Module 3 included at conceptual approach depth. Earlier nested 4.2.1/4.2.2 draft numbering superseded.

### Status
Drafting

---

## 2026-07-29 - Report draft: Chapter 7 Module 1/2 Evaluation

### Module
Report writing (Chapter 7)

### Change
Created evaluation-and-results draft for Modules 1 and 2 (strategy, forecasting metrics, classification/calibration, M2-009 redundancy test, limitations). Saved at `research_context/report_drafts/chapter7_m1_m2_evaluation.md`. Updated Chapters 4–6 drafts + Module 2 draw.io so Stage 1 official model is Random Forest (M2-005). Updated `CHAPTER_STATUS.md`.

### Reason
Interim Chapter 7 was a progress narrative written before M1/M2 experiments were complete; final report needs evidence-based evaluation sections.

### Impact
Team can replace interim Ch 7 M1/M2 content in Word. Module 3 remains a placeholder. Research vs operational evidence tiers stated explicitly.

### Status
Drafting

---

## 2026-07-29 - Report draft: Chapter 5.3.1 / 5.3.2 (Modules 1–2 design)

### Module
Report writing (Chapter 5)

### Change
Created corrected design-architecture draft text for sections 5.3.1 (Module 1) and 5.3.2 (Module 2), replacing interim figure-only placeholders. Saved at `research_context/report_drafts/chapter5_5.3.1_5.3.2.md`. Added planned Figures 5.4/5.5 to `REPORT_DIAGRAM_PLAN.md`. Updated `CHAPTER_STATUS.md`.

### Reason
Interim Chapter 5 left Module 1/2 architecture as caption-only figures; final report needs structural design text aligned to SARIMA→XGBoost and XGBoost→isotonic architectures.

### Impact
Team can paste Module 1/2 design sections and redraw figures without waiting for Module 3. Section 5.3.3 remains deferred.

### Status
Drafting

---

## 2026-07-29 - Report draft: Chapter 6.2.1 / 6.2.2 / 6.3.1 / 6.3.2 (Modules 1–2)

### Module
Report writing (Chapter 6)

### Change
Created corrected final-report draft text for epidemiological and Open-Meteo datasets plus Module 1/2 implementation (preprocessing through Stage 1/2 modelling). Saved at `research_context/report_drafts/chapter6_6.2_6.3_m1_m2.md`. Updated `CHAPTER_STATUS.md`.

### Reason
Interim Chapter 6 used NASA POWER, incomplete preprocessing stories, and pre-decision Module 2 labelling/feature assumptions; M1/M2 training stages were largely missing.

### Impact
Team can paste updated M1/M2 dataset and implementation sections into Word without waiting for Module 3. Sections 6.2.3 / 6.3.3 remain deferred.

### Status
Drafting

---

## 2026-07-29 - Report draft: Chapter 4.2.1 and 4.2.2 (Modules 1–2)

### Module
Report writing (Chapter 4)

### Change
Created corrected final-report draft text for sections 4.2.1 (Module 1 forecasting approach) and 4.2.2 (Module 2 classification approach) from the interim report baseline, aligned to current living documentation. Saved at `research_context/report_drafts/chapter4_4.2.1_4.2.2.md`. Updated `CHAPTER_STATUS.md`.

### Reason
Interim report architecture wording was outdated (fine-scale claims, SARIMAX, undecided RF/XGBoost, Module 2 Stage 2 described as climate residual ML).

### Impact
Team can paste updated Module 1/2 approach sections into Word without waiting for Module 3. Module 3 (4.2.3) remains deferred.

### Status
Drafting

---

## 2026-07-29 - Dashboard split: research evidence vs operational prototype

### Module
Integration layer (dashboard)

### Change
Restructured `src/dashboard/app.py` into two sidebar views: **Research evidence** (holdout-validated M1/M2 metrics, M2-009 redundancy table, district MASE chart, calibration figure) and **Operational prototype** (existing live/forward monitoring with stronger disclaimers). New modules `evidence_data.py`, `pages.py`. Updated `DASHBOARD_GUIDE.md` walkthrough.

### Reason
Chat review concluded forward/dashboard outputs are not thesis-accuracy evidence; dashboard should demonstrate integration without being mistaken for validation.

### Impact
Default page is research evidence (viva-safe). Operational numbers labeled `evidence_tier: operational` throughout. No model retraining.

### Status
Accepted

---

## 2026-07-29 - M2-009 Module 1-Derived Alert Baseline (Module 2 Redundancy Test)

### Module
Module 2 (cross-module with Module 1)

### Change
Formalized holdout comparison: M2 production alerts vs thresholding M1 `final_prediction` (fair epidemic-threshold rule + naive fixed-100 rule). New read-only script `scripts/m2_009_m1_alert_baseline.py`.

### Reason
Defense question: Module 2 may appear redundant if Module 1 already forecasts cases. Empirical proof needed on the same holdout block and outbreak label.

### Impact
**Module 2 justified.** M2 PR-AUC 0.412 / recall 0.60 vs M1-threshold PR-AUC 0.063 / recall 0.225. M2 catches 15 outbreaks M1-threshold misses. Artifacts: `outputs/metrics/module2/m2_009_*.csv`. Production unchanged.

### Status
Accepted (evidence for thesis defense)

---

## 2026-07-29 - M2-008 Symmetric Climate-Free Stage 1 + Climate Stage 2 Ablation

### Module
Module 2

### Change
Ran Module 1–symmetric ablation: climate-free Stage 1 (case history + seasonality) + climate-only stacked Stage 2 correction. New script `scripts/m2_008_symmetric_ablation.py`, feature constants in `feature_engineering.py`, variant artifact paths via `module2_stage1_paths` / `--feature-variant m2_008`.

### Reason
Defense question: is Module 2’s isotonic Stage 2 only because climate was already in Stage 1? Test whether withholding climate from Stage 1 and routing it through Stage 2 stacked correction reproduces Module 1’s residual-compensation benefit.

### Impact
**Rejected.** Stacked climate Stage 2 holdout PR-AUC 0.424 vs climate-free Stage 1 raw 0.462; BSS −0.22. Production isotonic unchanged. Artifacts: `outputs/metrics/module2/m2_008_{vs_production,summary}.csv`, `*_m2_008` variant CSVs.

### Status
Experimental (ablation only; production unchanged)

---

```markdown
## YYYY-MM-DD - Short Change Title

### Module
Module name or All modules

### Change
What changed?

### Reason
Why was the change made?

### Impact
What files/code/models are affected?

### Status
Accepted / Rejected / Experimental / Superseded
```

---

## 2026-07-29 - Production stack promotion (M1-006B + M2 isotonic)

### Module
All modules (M1 + M2 production defaults)

### Change
Promoted M1-006B Feature Group 6 to default Module 1 paths (refit
`feature_engineering` → `stage2_xgboost` → `combine` → `xgboost_final_model.json`).
Confirmed M2 production: isotonic Stage 2, τ=0.14 alert threshold, no ramp rule.
Ablations retained at `_m1_006_a`, `_m1_006_b`, `_m2_007_d` variant paths.

### Reason
User sign-off on recommended production stack after Stage 2 upgrade experiments.

### Results
M1 holdout median MASE 0.386 → **0.374**, median sMAPE 35.0 → **34.2**, 22/25 districts
improved; M2 holdout unchanged (PR-AUC 0.412, recall 0.60, precision 0.338 @ 0.14).
See `scripts/evaluate_production_stack.py` and `production_stack_*` metrics.

### Impact
Default M1/M2 artifacts refreshed; Decision 030 accepted; backup at
`outputs/metrics/production_promotion_backup_2026-07-29/`.

### Status
Accepted

---

## 2026-07-29 - M2-007D M1-fed Stage 2 features (implemented, PR-AUC gate met, production deferred)

### Module
Module 2

### Change
Leakage-safe join of M1 OOS `final_prediction` lags into tree-based Stage 2 (`m1_final_prediction_lag_1`, `m1_forecast_momentum`). New `m1_forecast_join.py`, `--feature-variant m2_007_d`, evaluation script `scripts/m2_007d_evaluate.py`.

### Reason
M2-007D experiment — test whether Module 1 forecast signal improves Module 2 discrimination when joined evaluation-safely.

### Results
Holdout PR-AUC for `stacked_xgboost` + M1 features **0.465** vs isotonic **0.412** (+0.054; passes ≥0.02 gate). Alert recall @ 0.14 rises to **0.775** but precision falls to **0.194**; BSS **−0.067**. Official validation selector still **isotonic**. **Feature signal accepted; architecture switch deferred.**

### Impact
`m1_forecast_join.py`, `compensation_model.py`, `config.py`, `m2_007_d_*` artifacts. Official Stage 2 unchanged (isotonic).

### Status
Experimental (partial accept — ablation path only)

---

## 2026-07-29 - M1-006B reporting-delay features (implemented, acceptance met)

### Module
Module 1

### Change
Feature Group 6: `weeks_since_reporting_anomaly`, `reporting_rebound_ratio_lag1`, `suspected_backfill_week`; nowcast `cases_lag_1` when prior week flagged. Evaluation via `feature_variant='m1_006_b'` paths.

### Reason
M1-006B experiment — extend Decision 028 with learnable reporting-state features.

### Results
Median holdout MASE 0.374 vs 0.386; 22/25 districts improved; Colombo/Gampaha gain. **Proposed Decision 030.**

### Impact
`reporting_anomalies.py`, `feature_engineering.py`, `compensation_model.py`, `config.py`, `m1_006_b_*` artifacts.

### Status
Accepted (promoted to default paths 2026-07-29; see production stack entry above)

---

## 2026-07-29 - M2-007A logit-residual Stage 2 (implemented, rejected)

### Module
Module 2

### Change
Added `logit_residual` architecture to `compensation_model.py` and evaluation script `scripts/m2_007a_evaluate.py`. Live-scoring hook in `scoring_utils.py`.

### Reason
Execute M2-007A — test M1-style logit/residual compensation for probability calibration.

### Results
Holdout PR-AUC 0.324 vs isotonic 0.412; alert recall @ 0.14 drops to 0.125. **Rejected.**

### Impact
`compensation_model.py`, `scoring_utils.py`, `m2_007_a_*` metrics. Official architecture unchanged (isotonic).

### Status
Experimental (rejected for production)

---

## 2026-07-29 - M1-006A log-residual ablation + M2-007C ramp alert rule (implemented, rejected for production)

### Module
Module 1 + Module 2

### Change
- **M1-006A:** Added `src/module1_forecasting/residual_transform.py` and `--residual-mode {additive,log}` switch across Stage 2 / combine / rolling / forward forecast. Log variant artifacts: `*_m1_006_log.csv` / `xgboost_final_model_m1_006_log.json`. Comparison: `outputs/metrics/module1/m1_006_log_vs_baseline.csv`.
- **M2-007C:** Added `src/module2_classification/alert_rules.py` and `scripts/m2_007c_evaluate.py` for consecutive-week ramp alert post-processing. Optional hook in `scoring_utils.apply_risk_tiers`.

### Reason
Execute first two phases of `STAGE2_UPGRADE_EXPERIMENT_PLAN.md` with holdout-gated adoption.

### Results
- M1-006A: median holdout MASE 0.375 vs 0.386 baseline (−2.9%), but median sMAPE flat (+0.2 pp), only 15/25 districts beat additive, Colombo/Gampaha regress. **Rejected** for production; additive baseline retained.
- M2-007C: holdout recall unchanged (0.60), precision −0.9 pp vs τ=0.14. **Rejected** for production; single-threshold alerting retained.

### Impact
`src/config.py`, `compensation_model.py`, `combine.py`, `rolling_one_step.py`, `forecast_future.py`, `main.py`, new M1/M2 metrics CSVs, both `EXPERIMENT_LOG.md` files.

### Status
Experimental (ablation code kept; production defaults unchanged)

---

## 2026-07-29 - Stage 2 Upgrade Experiment Plan (M1-006 / M2-007)

### Module
Module 1 + Module 2

### Change
Added `research_context/STAGE2_UPGRADE_EXPERIMENT_PLAN.md` — phased ablation plan for log-scale / reporting-delay Stage 2 (M1) and logit-residual / cost-sensitive / alert-rule / M1-fed Stage 2 (M2), with holdout metrics, leakage checks, acceptance criteria, and implementation order. Stub entries added to both `EXPERIMENT_LOG.md` files.

### Reason
User requested a research-backed path to improve forecast accuracy and outbreak recall/precision beyond current additive residuals (M1) and isotonic calibration (M2).

### Impact
Planning document only; no code or model changes yet.

### Status
Planned

---

## 2026-07-29 - Reporting-Lag Guard + Rolling 1-Step Operational Evaluator (Decisions 028–029, M1-005)

### Module
Module 1 (with Module 2 preprocessing/feature parity for the guard column)

### Change
**Fix 1 (Decision 028):** Added `src/preprocessing/reporting_anomalies.py` to flag suspected delayed-reporting weeks (`is_reporting_anomaly`) when prior-week cases ≥100, current week drops ≥75%, and the next week rebounds ≥2.5× (or exceeds the prior week). Wired into Module 1/2 preprocessing and feature engineering via `mask_untrusted_cases()` — case-derived lags, rolling stats, M2 `case_anomaly_lag_*`, and M1 `build_residual_lags()` all null suspect values before shifting. Raw `Number_of_Cases` is preserved for labels/evaluation.

**Fix 2 (Decision 029):** Added `src/module1_forecasting/rolling_one_step.py` — weekly SARIMA refit on all data strictly before week *t*, 1-step forecast, frozen Stage 2 XGBoost checkpoint. Outputs `rolling_one_step_predictions.csv` and period sMAPE summaries. Also hardened `_save_xgboost_model()` in `compensation_model.py` (atomic save + correct `.json` temp suffix for Windows/XGBoost 2.x).

### Reason
Colombo/Gampaha 2026 Wk24 reporting dips poisoned `cases_lag_1` for Wk25; the flat 104-week SARIMA holdout is a poor proxy for real weekly deployment. These fixes address the two highest-priority operational failure modes identified in the M1-004 climate retest post-mortem.

### Impact
33 M1 / 26 M2 rows flagged across all districts (including Colombo/Gampaha 2026 Wk24). Holdout MASE: 23/25 districts improved (median 32.9%). Rolling 1-step (Colombo/Gampaha): holdout-all sMAPE 21.2%/26.7%; 2026 Wk22–23 sMAPE ~13% (vs ~21% on flat holdout); Wk25 spike still missed (~7× underestimate) — documented limit, not solved.

### Status
Accepted

---

## 2026-07-29 - Dashboard Observer Guide

### Module
Integration layer (dashboard)

### Change
Added `src/dashboard/DASHBOARD_GUIDE.md` — observer/demo guide covering page layout, column definitions, risk tiers, operational vs holdout distinction, walkthrough script, and troubleshooting. Updated `app.py` docstring to reference the guide.

### Reason
Support thesis demo, viva defense, and stakeholder handoff without relying on chat or ad-hoc explanation.

### Impact
Documentation only; no pipeline or model changes.

### Status
Accepted

---

## 2026-07-29 - Early Warning Dashboard, Climate Refresh, Module 2 Forward Risk (M1-fed)

### Module
All modules (Integration layer + Module 1/2 operational scoring)

### Change
Added operational early-warning infrastructure:
- `scripts/fetch_open_meteo_weather.py` — Open-Meteo Archive (observed gap-fill) + Forecast API extension for all 25 district CSVs, with daily `climate_data_source` tagging (`observed`/`forecast`).
- `scripts/refresh_dashboard_data.py` — end-to-end refresh orchestrator (weather → preprocessing → M1 forward forecast → M2 live + forward risk).
- `src/module2_classification/scoring_utils.py` — shared frozen-model scoring helpers extracted from `live_scoring.py`.
- `src/module2_classification/forecast_future_risk.py` — forward operational risk (M1 `final_prediction` feeds case-derived lag features for multi-week-ahead rows).
- `src/dashboard/app.py` — Streamlit early-warning dashboard (overview + district drill-down).
- `shared.py` / `module1_preprocessing.py` — propagate `climate_data_source` through weekly climate aggregation; weather glob restricted to `open-meteo-*.csv`.
- `src/config.py` — `MODULE2_FUTURE_RISK_PREDICTIONS_PATH`, `FORECAST_HORIZON_WEEKS`, `DASHBOARD_REFRESH_MANIFEST_PATH`.

Climate gap closed: raw weather extended through 2026-08-13; shared `climate_weekly.csv` now reaches 2026 Wk25; live scoring `feature_completeness_pct` restored to 100% on latest weeks.

### Reason
Thesis operational deliverable: integrate Module 1 case forecasts and Module 2 risk scoring into a refreshable dashboard, closing the documented ~4-week climate-currency gap (Open Questions #16/#10) and enabling multi-week-ahead forward risk using user-approved M1-fed case lags.

### Impact
New scripts and CSV outputs (`future_risk_predictions.csv`, `climate_fetch_manifest.csv`, `dashboard_refresh_manifest.csv`). No model retraining. Forward outputs tagged `evidence_tier=operational` — distinct from holdout-validated metrics.

### Status
Accepted

---

## 2026-07-29 - Module 1 Completion Scope: Non-Seasonal SARIMA Flagged for Supervisor; Other Follow-Ups Deferred

### Module
Module 1

### Change
Documented the non-seasonal SARIMA finding (18/25 districts, Open Question #12) as an explicit supervisor-facing flag rather than a silent limitation. Added a prepared defense answer in `research_context/QUESTIONS_FOR_DEFENSE.md` and a "Supervisor Flag" section in `module_1_forecasting/MODULE_CONTEXT.md`. Confirmed no Stage 1 rework — Stage 2 already compensates more for non-seasonal districts.

Team decision: defer remaining Module 1 follow-ups (climate currency refresh, rolling 1-week-ahead evaluation, STL+SARIMA ablation, Ljung-Box follow-up features, rainfall lag ablation, holdout divergence investigation) as not blocking thesis completion given the validated compensation-framework results.

### Reason
Thesis scope is historical validation of the residual-compensation hypothesis, not operational early-warning certification. The non-seasonal SARIMA issue must be disclosed honestly because 12/25 Stage-1-only configs fail seasonal naive, but empirical evidence shows Stage 2 addresses it — reworking Stage 1 is not justified.

### Impact
Documentation only — no code or pipeline rerun. Updated `research_context/QUESTIONS_FOR_DEFENSE.md`, `module_1_forecasting/MODULE_CONTEXT.md`, `research_context/CHANGELOG.md`.

### Status
Accepted

---

## 2026-07-28 - Module 2 Live/Production Risk Scoring Added; New Climate-Currency-Gap Finding

### Module
Module 2

### Change
Added `src/module2_classification/live_scoring.py` (new, standalone - not
wired into `main.py`'s idempotent `PIPELINE_STAGES`, same precedent as Module
1's `forecast_future.py`). Recomputes Stage 1's feature table fresh from the
current `weekly_modeling_table.csv`, attaches full-history climate anomalies,
scores the most recent N weeks per district (default 8) through the frozen
Stage 1 + Stage 2 final-production models (model/architecture type read
dynamically from each stage's metrics CSV `selected` column, never
hardcoded), and applies the persisted alert/high-confidence risk thresholds.
Outputs `data/processed/module2/live_risk_predictions.csv`.

While building/testing this script, discovered that Module 2 shares Module
1's Open Question #16 climate-currency gap: `weekly_modeling_table.csv`'s
case counts extend through 2026 Wk25 but every climate column stops 4 weeks
earlier (2026 Wk21) for all 25 districts, since both modules consume the same
shared climate pipeline. `feature_completeness_pct` drops from 100% to 60%
over the most recent 4 scored weeks as a result.

### Reason
Module 2's training/evaluation pipeline (Stage 1 -> Stage 2 -> risk
thresholds) only ever scores against data already inside the dataset
(walk-forward folds, the 2-year holdout). There was no way to produce a risk
classification for the dashboard's actual use case - "what does the model say
about the most recent real weeks, right now" - without manually rerunning the
entire walk-forward benchmark. Unlike Module 1, no SARIMA-style recursive
multi-step extrapolation is needed: every Stage 1 feature is a lag of a prior
week or that week's own already-reported climate, never that week's own case
count, so as long as the raw data already covers the target week, every
feature is a real observation.

### Impact
New: `src/module2_classification/live_scoring.py`,
`data/processed/module2/live_risk_predictions.csv`. Config: added
`MODULE2_LIVE_RISK_PREDICTIONS_PATH` to `src/config.py`. Documentation:
`module_2_classification/MODULE_CONTEXT.md` new "Live/Production Risk
Scoring" section and new Open Question #10 (climate-currency gap). No
production training/evaluation code changed.

### Status
Accepted. First real-world spot check (current data through 2026 Wk25)
correctly flags 9 districts `high` and 6 `medium`, including `Colombo` and
`Gampaha` - the same two districts already independently confirmed as a real,
ongoing 2026 outbreak in `module_1_forecasting/MODULE_CONTEXT.md`. The
climate-currency-gap finding remains open (shared fix with Module 1's Open
Question #16: rerun the shared climate preprocessing/Open-Meteo fetch).

---

## 2026-07-28 - Module 2 SMOTENC Oversampling Audited and Rejected; Decision 021 Reconfirmed (Decision 026, M2-006)

### Module
Module 2

### Change
Added `scripts/audit_smote_imbalance.py` (read-only diagnostic, added
`imbalanced-learn` to `requirements.txt`) and used it to benchmark leakage-safe
SMOTENC oversampling (fit strictly on each fold's own training rows, `District`
as a `categorical_features` column) against the current
`class_weight`/`scale_pos_weight`-only approach, across 4 variants x 2 models
(Random Forest, XGBoost), on the identical 13 walk-forward folds + holdout
used by production `baseline_classifier.py`.

### Reason
A user request to research accuracy-improvement techniques beyond this repo
surfaced SMOTE-family oversampling as a commonly cited lever for imbalanced
outbreak classification in the literature. Decision 021 had already rejected
SMOTE, but on a reasoning ("blurs the temporal fold boundary") that doesn't
precisely describe the real risk of oversampling this pipeline's lagged
features - the reasoning needed correcting, so the underlying conclusion was
re-tested empirically rather than assumed to still hold, per this project's
"critique assumptions, don't just agree" rule.

### Impact
No production code changed - `baseline_classifier.py` and all its outputs are
unchanged. Result: **rejected**. For Random Forest (official model), the best
SMOTENC variant shows a small validation-median PR-AUC gain (+0.0096) that
evaporates on holdout (effectively a wash) and costs holdout recall. Every
SMOTENC variant improved XGBoost's validation PR-AUC but worsened its holdout
PR-AUC - a validation-improves/holdout-regresses pattern the pre-registered
holdout check exists to catch. A consistent secondary finding (better raw
Brier/calibration under SMOTENC) is judged likely redundant with Stage 2's
existing isotonic recalibration. `research_context/RESEARCH_DECISIONS.md`
(new Decision 026), `module_2_classification/EXPERIMENT_LOG.md` (new entry
M2-006), `module_2_classification/MODULE_CONTEXT.md` (Open Question #4
addendum), `requirements.txt` (added `imbalanced-learn`). New artifacts:
`scripts/audit_smote_imbalance.py`, `outputs/metrics/module2/
smote_imbalance_audit.csv`.

### Status
Rejected

---

## 2026-07-28 - Module 2 Label Mean/SD Estimator Replaced With Harmonic Regression; k Re-Audited to 3.0 (Decision 025, M2-005)

### Module
Module 2

### Change
Added `scripts/audit_label_stabilization.py` (read-only diagnostic, mirrors
`scripts/data_audit_module2.py`'s original k-audit) and used it to compare 6
candidate `historical_mean`/`historical_sd` estimators for Decision 019's
outbreak-threshold label formula (`exact_week` control, `windowed` at
window=1/2/3, `harmonic` at 1/2 harmonics) x 3 `k` values each, plus an
explicit spot-check of Colombo District/2025/Week 15. **Adopted harmonic
regression (`compute_historical_stats_harmonic`, `n_harmonics=1`) with
`k=3.0`** as the new official estimator in
`src/module2_classification/labels.py`, replacing Decision 019's exact-per-
(District, Week) sample mean/SD (kept in the codebase, not deleted, marked
superseded). `src/module2_classification/feature_engineering.py`'s
`compute_case_anomaly_lags` switched to match (Group M2-5 reuses the same
estimator as the label by design). `src/config.py`: `EPIDEMIC_THRESHOLD_K`
`2.0` -> `3.0`; new `EPIDEMIC_THRESHOLD_N_HARMONICS = 1`. Reran the full
Module 2 pipeline end to end (`feature_engineering` through
`stage2_risk_thresholds`, `--force`).

**Important correction to the motivating evidence, surfaced before
implementing anything**: the task's flagship example (Colombo 2025 Wk15,
277 cases, cited as a label defect) was verified directly against the
running pipeline and found to be **already correctly labeled `1`
(outbreak)** under the OLD estimator (`threshold=256.4 < 277`). The actual
issue was a Stage 2 calibration near-miss (isotonic-calibrated probability
0.155, just under the pre-existing 0.170 alert threshold) - not a label
problem. The real, addressed problem is the separately-documented 18-25%
pooled "outbreak" prevalence (well above WHO/CDC's single-digit-percent
norm), which this change reduces to 8.57% while also reducing the
undefined-label rate (16.0% -> 10.7%). **Window-pooling was tested and
rejected**: it increases the SD estimate in high-variance districts,
raising (not lowering) their threshold. **Honest limitation, not hidden**:
the chosen `k=3.0` raises Colombo's own threshold enough that its 2025
Wk15 row's label actually FLIPS from `1` to `0` under the new estimator -
an expected consequence of one global `k` fixing an aggregate-prevalence
problem, flagged as an open follow-up (district-specific/variance-adaptive
`k`), not silently presented as a clean win.

Full pipeline rerun surfaced further downstream consequences of the label
change: **Stage 1's official model selection flipped from XGBoost to
Random Forest** (median validation PR-AUC 0.3766 vs. 0.3726), Stage 2's
architecture contest tightened considerably (isotonic 0.2146 vs. Platt
0.2116 median BSS, both markedly improved vs. Stage 1 raw), and risk
thresholds recalibrated lower (alert 0.170 -> 0.140, high-confidence 0.570
-> 0.350) to track the new, lower prevalence.

### Reason
Open Question #8 (flagged at Decision 019's kickoff, never acted on until
now) argued the single-week `mean + k*SD` threshold was too noisy from
small per-week sample sizes. An audit-first approach (rather than assuming
a fix direction) was required per the user's explicit instruction, and
that audit's first useful output was disproving the specific motivating
example rather than confirming it - a finding that had to be surfaced
honestly before proceeding, per this project's "critique assumptions"
mandate, rather than silently implementing a fix for a problem that (in
that specific case) didn't exist.

### Impact
New file `scripts/audit_label_stabilization.py`. New outputs:
`outputs/metrics/module2/{label_stabilization_audit,
label_stabilization_spot_check}.csv`. Modified
`src/module2_classification/labels.py` (new
`compute_historical_stats_harmonic`/`_harmonic_design`; old
`compute_historical_stats` kept, marked superseded),
`src/module2_classification/feature_engineering.py` (estimator switched for
`case_anomaly_lag_1/2`), `src/config.py` (`EPIDEMIC_THRESHOLD_K` and new
`EPIDEMIC_THRESHOLD_N_HARMONICS`). Regenerated
`data/features/module2/stage1_feature_table.csv`,
`data/processed/module2/{baseline_classifier_predictions,
stage2_compensated_predictions, stage2_risk_tier_predictions}.csv`, all
Stage 1/2/threshold metrics and figures, and both stages' model artifacts.
Updated `research_context/RESEARCH_DECISIONS.md` (new Decision 025),
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-005; M2-001
through M2-004 explicitly marked as measured against the superseded
label), `module_2_classification/MODULE_CONTEXT.md` (Open Question #8
resolved; Stage 1/Stage 2 Implementation Status refreshed),
`research_context/FEATURE_ENGINEERING_SPEC.md` (Label Definition and Group
M2-5 updated), `research_context/PIPELINE_ARCHITECTURE_PLAN.md`
(`labels.py` entry and status banner updated).

### Status
Accepted. M2-001 through M2-004's numeric results are superseded by
M2-005 (a different label = a different, non-comparable target); their
qualitative findings (pooled beats per-district, isotonic/Platt beat
stacked XGBoost for Stage 2, F-beta thresholds beat a naive 0.5 cutoff)
remain valid. A district-specific/variance-adaptive `k` is flagged as an
open follow-up, not implemented this round.

---

## 2026-07-28 - Module 2 Stage 2 Risk Thresholds Implemented and Run (Decision 024, M2-004)

### Module
Module 2

### Change
Implemented `src/module2_classification/risk_thresholds.py` per Decision
024's design and ran it end to end. Added `fbeta_score()` and
`threshold_scan()` to `src/module2_classification/evaluate.py`; added risk-
threshold path constants to `src/config.py`; wired `stage2_risk_thresholds`
into `src/module2_classification/main.py`'s `PIPELINE_STAGES` as the final
stage. Completes Decision 022's deferred risk-tier item.

Selected an **F2-optimal alert threshold (0.170)** and an **F0.5-optimal
high-confidence tier boundary (0.570)**, chosen purely from the official
Stage 2 architecture's validation-fold rows (folds 2-13), holdout reserved
for the final check. On the untouched holdout block, switching from the
naive 0.5 cutoff to 0.170 nearly doubles recall (39.9% -> 68.6%) at the
expected precision cost, improving F2 from 0.437 to 0.574. Risk-tier
empirical separation is strong and monotonic on both splits: observed
outbreak rate 2.6% (low) -> 22.0% (medium) -> 76.7% (high) on holdout.

### Reason
The naive 0.5 cutoff used throughout Stage 1/2 benchmarking was always
documented as an untuned diagnostic, not a real decision threshold. An
early-warning system should weight recall over precision (F2) for its
primary alert, and precision over recall (F0.5) for a "high confidence"
label - one consistent F-beta framework at two operating points, avoiding
an arbitrary rule and staying consistent with Decision 022's earlier
rejection of quantile-based cutoffs.

### Impact
New file `src/module2_classification/risk_thresholds.py`. New outputs:
`data/processed/module2/stage2_risk_tier_predictions.csv`,
`outputs/metrics/module2/{risk_threshold_scan,
risk_threshold_holdout_comparison}.csv`. Updated
`module_2_classification/MODULE_CONTEXT.md` ("Target Direction" fully
resolved, new "Risk Thresholds" subsection), `module_2_classification/
EXPERIMENT_LOG.md` (new entry M2-004), `research_context/
RESEARCH_DECISIONS.md` (new Decision 024), `research_context/
PIPELINE_ARCHITECTURE_PLAN.md` (new `risk_thresholds.py` entry).

### Status
Accepted. Module 2's "Target Direction" ambiguity (calibrated probability
vs. risk tier vs. binary alert) is now fully resolved with concrete,
holdout-evaluated artifacts for all three.

---

## 2026-07-28 - Module 2 Stage 1 XGBoost Hyperparameters Tuned via Optuna, Adopted; Stage 2 Rerun (Decision 023, M2-003)

### Module
Module 2

### Change
Added a standalone `scripts/tune_stage1_xgboost.py` (Optuna TPE search, 60
trials, 13-fold median PR-AUC objective, holdout-gated adopt/reject
verdict) and an optional `xgb_params` override parameter to
`baseline_classifier.fit_and_predict`. Ran the search; holdout PR-AUC
improved 0.5380 -> 0.5577 (+0.0198) and holdout ROC-AUC improved 0.8978 ->
0.9109 under the tuned hyperparameters versus Decision 021's hand-picked
defaults - **adopted**, `XGB_BASE_PARAMS` in `baseline_classifier.py`
updated permanently. Reran Stage 1 and Stage 2 end to end with `--force`.

XGBoost remained Stage 1's selected model and pooled remained the winning
architecture, as expected. Unexpectedly, **Stage 2's official architecture
flipped from Platt scaling to isotonic regression** (median Brier Skill
Score 0.166 vs. Platt's 0.145) purely as a consequence of Stage 1's
reshaped probability distribution - no Stage 2 code changed. Isotonic
mildly regresses PR-AUC vs. Stage 1 raw (flagged automatically by the
existing Decision 022 gating check, not blocked, since BSS is the primary
metric).

### Reason
Following M2-002's finding that Stage 2 recalibration cannot itself improve
discrimination (by construction, for monotonic methods), the team asked
whether Stage 1's own discrimination could be improved before considering a
larger Module 2 redesign. Hand-picked hyperparameters (Decision 021) were
never claimed optimal, only conservative; a holdout-gated Optuna search
(not gated on the same fold-median metric already used for model-type
selection, to avoid compounding a second round of the same mild selection
bias) is the correct way to test that.

### Impact
`src/module2_classification/baseline_classifier.py`'s `fit_and_predict` gained
an optional `xgb_params` parameter; `XGB_BASE_PARAMS` permanently updated.
New files: `scripts/tune_stage1_xgboost.py`,
`outputs/metrics/module2/{xgboost_tuning_trials,
xgboost_tuning_holdout_comparison}.csv`. Regenerated:
`data/processed/module2/{baseline_classifier_predictions,
stage2_compensated_predictions}.csv` and all dependent metrics/model
artifacts. Updated `module_2_classification/MODULE_CONTEXT.md` (Stage 1 and
Stage 2 Implementation Status sections), `module_2_classification/
EXPERIMENT_LOG.md` (new entry M2-003; M2-002 marked superseded),
`research_context/RESEARCH_DECISIONS.md` (new Decision 023; Decision 022's
status corrected), `research_context/PIPELINE_ARCHITECTURE_PLAN.md`
(tuned-params note).

### Status
Accepted. M2-002's specific numeric results (Platt selected, exact BSS/
PR-AUC values) are superseded by M2-003; M2-002's qualitative findings
(stacked XGBoost underperforms, pooled beats per-district) remain valid.

---

## 2026-07-28 - Module 2 Stage 2 Compensation Model Implemented and Run (M2-002)

### Module
Module 2

### Change
Implemented `src/module2_classification/compensation_model.py` per Decision
022's design and ran it end to end. Added `brier_skill_score()` and
`reliability_curve()` to `src/module2_classification/evaluate.py`; added
Stage 2 path constants to `src/config.py`; wired `stage2_compensation` into
`src/module2_classification/main.py`'s `PIPELINE_STAGES`.

**Platt scaling selected** as the official Stage 2 architecture: median
Brier Skill Score improved from -0.043 (Stage 1 raw) to +0.130 on the 12
trainable validation folds, and from -0.080 to +0.292 on the untouched
holdout block. PR-AUC/ROC-AUC are numerically *identical* to Stage 1 raw in
both splits, confirming Decision 022's "no discrimination regression" gate
holds exactly (Platt scaling is a strictly monotonic transform, so ranking
cannot change by construction). Isotonic regression also improved
calibration substantially but is not selected (lower median BSS than
Platt). Stacked XGBoost did not improve calibration (median BSS still
negative, -0.074) - a genuine negative result attributed to its own
per-fold `scale_pos_weight` likely reintroducing a similar probability-scale
distortion to Stage 1's. Pooled-vs-per-district was re-validated
empirically for Stage 2 (stacked-XGBoost arbiter) and again favors pooled,
mirroring Decision 021's Stage-1 finding. Reliability diagrams confirm Stage
1 was systematically overconfident (not underconfident) across most of the
probability range, and Platt scaling pulls both the validation and holdout
curves close to the diagonal.

### Reason
Stage 1's negative Brier skill score (M2-001) meant its raw probabilities
were not usable as real risk estimates despite strong discrimination.
Benchmarking three well-posed architectures (rather than assuming one)
produced clear, reproducible evidence for which correction actually works,
and the exact PR-AUC/ROC-AUC equality for the winning architecture is a
strong internal-consistency check that the implementation is correct.

### Impact
New outputs: `data/processed/module2/stage2_compensated_predictions.csv`,
`outputs/metrics/module2/{stage2_compensation_metrics,
stage2_pooled_vs_per_district_comparison}.csv`,
`outputs/figures/module2/reliability_diagram_{validation,holdout}.png`,
`models/module2/stage2_compensation/`. Updated
`module_2_classification/MODULE_CONTEXT.md` ("Stage 2 Implementation
Status" section, Open Question #5 resolved) and
`module_2_classification/EXPERIMENT_LOG.md` (new entry M2-002).

### Status
Accepted. The fixed-threshold risk-tier follow-up (deferred in Decision 022)
is now unblocked, since a real calibrated-probability distribution exists.

---

## 2026-07-28 - Module 2 Stage 2 Design Finalized (Decision 022)

### Module
Module 2

### Change
A dedicated planning session (no code written) finalized Module 2 Stage 2's
design before implementation began. Key outcome: a literal port of Module 1
Stage 2's `residual = actual - sarima_prediction` formula was examined and
rejected as statistically ill-posed for a binary label (`label -
predicted_probability` for a single Bernoulli observation is a
high-variance, low-information target, with no clean way to keep
`predicted_probability + predicted_residual` inside `[0, 1]`). Three
numerically well-posed architectures are benchmarked instead, selected by
median Brier Skill Score: isotonic regression (pooled, feature-free), Platt
scaling (pooled, feature-free, logistic regression on
`logit(predicted_probability)` - not raw `p`), and a stacked XGBoost model
on `[predicted_probability, contextual features, District,
probability_residual_lag_1/2]` -> `label`. An XGBoost `base_margin`-warm-
started variant was considered as the most literal translation of Module
1's residual metaphor that stays well-posed, but deferred as a future
ablation rather than built now (the stacked model already covers its
expected benefit and is more flexible).

Also decided: a Decision-010-style no-leakage rule (fold *k* trains only on
prior folds' out-of-sample Stage 1 probabilities, fold 1 is a no-op
passthrough, yielding 12 trainable folds vs. Stage 1's 13); pooled-vs-per-
district re-validated empirically via the stacked-XGBoost architecture as
arbiter, not assumed from Decision 021; calibrated probability as the
primary output with risk-tier labels as a secondary output using fixed (not
quantile) thresholds, values deferred until the real calibrated
distribution can be inspected; Module 1 forecast integration deferred again
as a concrete post-Stage-2 ablation (the two modules' fold boundaries are
misaligned - 14 folds/`MIN_TRAIN_YEARS=3` vs. 13 folds/`MIN_TRAIN_YEARS=4`
- so merging requires a dedicated leakage audit, not a simple merge); Open
Question #8 (consecutive-week trigger) stays deferred.

### Reason
Working through the design before writing code caught a real statistical
problem (the ill-posed residual target) that a direct copy of Module 1's
architecture would have produced. Benchmarking three architectures rather
than picking one a priori follows the same evidentiary standard already
used for Stage 1's model selection (Decision 021).

### Impact
No code changes yet - implementation follows in a subsequent session.
Updated `research_context/RESEARCH_DECISIONS.md` (new Decision 022),
`module_2_classification/MODULE_CONTEXT.md` (Open Questions #5/#6 updated,
Target Direction resolved, "Possible Stage 2 Models" resolved, new "Stage 2
Design Status" section), `research_context/FEATURE_ENGINEERING_SPEC.md`
(new Module 2 Stage 2 feature-group section), and this file.

### Status
Accepted (design); implementation and results pending.

---

## 2026-07-28 - Module 2 Stage 1 Baseline Classifier Implemented

### Module
Module 2

### Change
Implemented `src/module2_classification/evaluate.py` (classification
metrics: `accuracy`, `precision`, `recall`, `specificity`, `f1`, `roc_auc`,
`pr_auc`, `brier_score`, `prevalence`, `confusion_counts`, mirroring Module
1's masked-pure-function style), `src/module2_classification/
baseline_classifier.py` (the full Stage 1 pipeline), and
`src/module2_classification/main.py` (idempotent orchestration mirroring
`module1_forecasting/main.py`'s `PIPELINE_STAGES` pattern). Ran the full
pipeline end to end.

Stage 1 benchmarks Logistic Regression / Random Forest / XGBoost per
walk-forward fold, pooled across all 25 districts (`District` as a
categorical feature). A critical fold-1 fix was found and applied before
the benchmark could run at all: `validation.py`'s SARIMA-tuned
`DEFAULT_MIN_TRAIN_YEARS=3` left fold 1's entire training window with
**zero** rows that have a defined label - the label's own
3-strictly-prior-years requirement (Decision 019) overlaps exactly with
that window, for every district simultaneously. A new, Module-2-specific
`MODULE2_MIN_TRAIN_YEARS=4` (`src/config.py`) fixes this, yielding 13
walk-forward folds (vs. Module 1's 14). The pooled architecture choice was
validated **empirically**, not assumed by analogy with Module 1 Stage 2: a
dedicated XGBoost-only comparison found pooled median PR-AUC (0.500) far
exceeds per-district median PR-AUC (0.287) across the 13 folds. **XGBoost
selected** as the official Stage 1 model by median validation PR-AUC (vs.
Random Forest 0.462, Logistic Regression 0.437); its held-out final-block
PR-AUC is 0.538. A second correction was made mid-implementation: the
original premise that "tree-based models handle NaN natively" is only true
for XGBoost among the three benchmarked models - `sklearn`'s
`RandomForestClassifier` requires explicit imputation, added via a shared
`ColumnTransformer` (also used for Logistic Regression).

### Reason
Module 2's Stage 1 had no code yet, and its fold design needed to be
verified empirically (not assumed to mirror Module 1's) before any model
could be honestly benchmarked - the label's own strictly-prior-years
construction interacts with the walk-forward minimum-training-window
parameter in a way specific to a classification target, not a regression
target. The pooled-vs-per-district architecture question was likewise a
genuine design decision requiring its own evidence, not simply inherited
from Module 1 Stage 2's precedent (a different target type, and a
different, coincidental cause of early-fold data thinness).

### Impact
Added `src/module2_classification/evaluate.py`, `src/module2_classification/
baseline_classifier.py`, `src/module2_classification/main.py` (all
previously placeholders). Added `data/processed/module2/
baseline_classifier_predictions.csv` (58,500 rows), `outputs/metrics/
module2/{baseline_classifier_metrics, pooled_vs_per_district_comparison,
baseline_classifier_feature_importance}.csv`, `models/module2/
baseline_classifier/{fold_1..13, holdout, final_production_model}.json`.
Updated `src/config.py` (`MODULE2_MIN_TRAIN_YEARS` and 6 new output path
constants). Updated `research_context/RESEARCH_DECISIONS.md` (new Decision
021), `module_2_classification/MODULE_CONTEXT.md` (Open Question #4
resolved, new "Stage 1 Implementation Status" section), `module_2_
classification/EXPERIMENT_LOG.md` (new entry M2-001),
`research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section
updated; `labels.py` filename correction), `research_context/
FEATURE_ENGINEERING_SPEC.md` (baseline classifier probability now
available for Stage 2).

### Status
Accepted.

---

## 2026-07-28 - Module 2 Kickoff: Outbreak Label Definition Decided

### Module
Module 2

### Change
Formalized Module 2's foundational research decision (Decision 019): the
outbreak classification target is a fold-aware **epidemic-threshold** label —
`outbreak = 1 if Number_of_Cases > historical_mean(District, Week) + k *
historical_SD(District, Week)`, with `historical_mean`/`historical_SD`
computed from strictly-prior years only (no label leakage), `k=2` as a
literature-standard default pending an empirical class-balance audit, and a
minimum 3-strictly-prior-years history requirement before a label is defined.
This retires `src/config.py`'s `OUTBREAK_THRESHOLD = 50` placeholder. Also
decided: Module 2's Stage 1 will be built independently of Module 1 (no
SARIMA/XGBoost forecast consumption yet) — deferred, not abandoned, per Open
Question #6.

Updated `module_2_classification/MODULE_CONTEXT.md` (Open Questions #1-3
resolved, #6 annotated deferred, new #7 for `k` calibration; new
"Implementation Plan" section), `research_context/FEATURE_ENGINEERING_SPEC.md`
(Module 2's label formula and feature categories made concrete, explicit note
that Module 1 integration is deferred), and
`research_context/PIPELINE_ARCHITECTURE_PLAN.md` (Module 2 Layer section
expanded from a placeholder into a concrete build plan covering
preprocessing, label definition, feature engineering, and both stages).

### Reason
Module 2 had no code yet, and its most fundamental open question (how an
"outbreak" is even defined) was blocking all downstream work. A single fixed
count threshold is not defensible across 25 districts with very different
baseline incidence (per the already-documented zero-inflation heterogeneity);
a per-district-week statistical threshold is both more defensible and
naturally resolves two other open questions (district-specificity, threshold
justification) at the same time.

### Impact
`research_context/RESEARCH_DECISIONS.md` (new Decision 019),
`module_2_classification/MODULE_CONTEXT.md`,
`research_context/FEATURE_ENGINEERING_SPEC.md`,
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`. No code changes yet in this
entry — implementation (`scripts/data_audit_module2.py`,
`src/preprocessing/module2_preprocessing.py`,
`src/module2_classification/label_definition.py`, etc.) follows in subsequent
work and will be logged separately once run.

### Status
Accepted (label definition and Module 1 sequencing); `k=2` remains tunable
pending the empirical class-balance audit.

---

## 2026-07-28 - Module 2 Label Class-Balance Audit Run; k=2 Finalized

### Module
Module 2

### Change
Added `scripts/data_audit_module2.py` (new, read-only diagnostic mirroring
`scripts/data_audit_module1.py`'s style) and ran it against
`data/processed/shared/epidemiological_weekly.csv` (25,348 rows, 25
districts) for Decision 019's epidemic-threshold label at `k ∈ {1.5, 2.0,
2.5}`. No district produced a degenerate outbreak rate (outside a [2%, 40%]
sanity band) at any candidate. `k=2` is finalized: pooled outbreak rate 18.4%
(range 12.6%-25.2% across districts), 15.7% of rows undefined (< 3
strictly-prior years of history, concentrated in each district's earliest
years, correctly excluded rather than defaulted to 0). Full per-district,
per-`k` results written to `outputs/metrics/module2/label_balance_audit.csv`.

**Methodological finding, flagged rather than silently accepted**: an
18-25%-of-weeks outbreak rate is considerably higher than typical WHO/CDC
epidemic-alert rates (usually single-digit %), suggesting the single-week
`mean + k*SD` threshold is flagging much of each district's normal seasonal
(monsoon) peak rather than only genuinely anomalous spikes. Recorded as new
Module 2 Open Question #8 - candidate follow-ups (requiring >=2 consecutive
weeks above threshold, or deseasonalizing before computing the anomaly) are
noted but not implemented this session; `k=2` proceeds as the kickoff's
working default, not a final validated label definition.

### Reason
`k` needed empirical confirmation, not an assumed literature value, given
Module 1's already-documented cross-district zero-inflation heterogeneity
(e.g. `Mullaitivu` 52.8% zero-weeks vs `Colombo` 0.5%) which could plausibly
have produced degenerate per-district label rates at a naively chosen `k`.

### Impact
Added `scripts/data_audit_module2.py`,
`outputs/metrics/module2/label_balance_audit.csv`. Updated
`research_context/RESEARCH_DECISIONS.md` (Decision 019's `k` finalized with
evidence and the seasonal-peak caveat), `module_2_classification/MODULE_CONTEXT.md`
(Open Question #7 resolved, new Open Question #8).

### Status
Accepted (`k=2` as kickoff default); Open Question #8 (single-week vs
consecutive-week / deseasonalized trigger) left open for future refinement.

---

## 2026-07-28 - Module 2 Preprocessing, Label Definition, and Stage 1 Feature Engineering Implemented

### Module
Module 2

### Change
Implemented `src/preprocessing/module2_preprocessing.py` (own week-53/
missing-week/`weather_code` decisions per Decision 013, mirroring but not
inheriting Module 1's pattern; output: `data/processed/module2/
weekly_modeling_table.csv`, 25,350 rows, matching Module 1's row count since
the underlying policy choices happened to align), `src/module2_classification/
labels.py` (Decision 019's fold-aware epidemic-threshold label -
`compute_historical_stats`/`compute_epidemic_threshold_labels`; verified
18.35% pooled outbreak rate at `k=2`, consistent with the earlier audit's
18.41%), and `src/module2_classification/feature_engineering.py` (Stage 1
features).

Feature engineering was deliberately paused mid-implementation for a
dedicated review (prompted by the user, not yet fully finalized) before
Stage 1 modeling code was written on top of it. That review found and fixed
a real leakage risk (the first pass carried `Number_of_Cases`/`cases_per_100k`
- the exact quantity the label is thresholded on - forward as if they were
usable features) and added two new feature groups beyond the original
feature-direction bullet list: lagged climate (`rainfall_lag_2-8`,
`temperature_lag_1-4`, `humidity_lag_1-4`, capturing dengue's ~2-8-week
transmission delay, which anomaly-only features miss) and case-level
seasonal-anomaly lags (`case_anomaly_lag_1/2`, conceptually similar to Module
1's `residual_lag`). Also added `momentum_vs_rolling_mean` (reduces
zero-inflation noise vs. a bare `rate_of_change`) and current-week raw
climate features (a deliberate divergence from Module 1's Stage-1
climate-free rule, since Decision 001 is Module-1-scoped). Final feature
table: 25,350 rows x 53 columns (32 enumerated in
`FOLD_AGNOSTIC_FEATURE_COLUMNS`), written to `data/features/module2/
stage1_feature_table.csv`.

Also documented, as a subtle but important correctness point: the
case-anomaly lag's `historical_mean`/`historical_sd` (reused from `labels.py`)
use a per-ROW expanding, strictly-prior-calendar-year construction, which is
safe to compute ONCE globally - a different (and here, provably equivalent)
leakage-guard architecture than the climate anomaly's per-FOLD frozen
construction (reused unchanged from Module 1). The two must not be conflated.

### Reason
A classifier trained on `cases_per_100k` (or the raw case count itself) as a
feature would trivially "predict" its own label rather than learn genuine
epidemiological structure - this had to be fixed with an explicit, enumerated
feature-column list before any Stage 1 model could be honestly evaluated.
The two new feature groups were added because the original feature-direction
list (anomalies only, no lags; no case-level anomaly signal) would have left
out signal Module 1's own design already demonstrated as valuable
(`residual_lag_1/2` was Module 1's single most important Stage 2 feature).

### Impact
Added `src/preprocessing/module2_preprocessing.py`,
`src/module2_classification/labels.py`,
`src/module2_classification/feature_engineering.py` (rewritten once after
the review), `data/processed/module2/weekly_modeling_table.csv`,
`data/features/module2/stage1_feature_table.csv`. Updated `src/config.py`
(Module 2 path constants, `EPIDEMIC_THRESHOLD_K`/`_MIN_PRIOR_YEARS`),
`research_context/FEATURE_ENGINEERING_SPEC.md` (Module 2 feature groups
finalized in detail), `module_2_classification/MODULE_CONTEXT.md` (Current
Feature Direction section rewritten).

### Status
Accepted.

---

## 2026-07-28 - Module 2 Preprocessing Review: Week 53 Kept Unmerged; is_imputed Masking Made Consistent

### Module
Module 2

### Change
Before starting Stage 1 modeling, paused (prompted by the user) to review the
three Decision-013-independent preprocessing choices flagged as unreviewed
kickoff defaults in the prior entry (Decision 020,
`research_context/RESEARCH_DECISIONS.md`):

1. **Week 53 (2009, 2016, 2019, 2021) is no longer merged into week 52** —
   reverses the kickoff default. `src/preprocessing/module2_preprocessing.py`'s
   week-53 merge functions were removed entirely; `find_missing_weeks`/
   `validate_weekly_modeling_table` now expect 53 weeks for those four years,
   52 otherwise.
2. **`is_imputed` rows are now masked to `NaN` before deriving `cases_lag_1-4`,
   `rolling_mean_cases_4w`, `rolling_std_cases_4w`, `rate_of_change`, and
   `momentum_vs_rolling_mean`** in `src/module2_classification/
   feature_engineering.py` — previously only `case_anomaly_lag_1/2` had this
   masking, a real inconsistency found during the review, not just a design
   preference.
3. **`weather_code` exclusion reconfirmed unchanged** — no Module-2-specific
   reason found to revisit Module 1's original redundancy reasoning.
4. Added `MODULE2_MONSOON_WEEKS_NE` (`= MONSOON_WEEKS_NE + [53]`) since week
   53 (late December) is now exposed to the monsoon-indicator feature and
   falls inside the NE monsoon window; the shared `MONSOON_WEEKS_NE` constant
   assumes Module 1's merged 52-week structure and must not be mutated.

Both preprocessing outputs were regenerated: `data/processed/module2/
weekly_modeling_table.csv` (25,450 rows, up from 25,350; 102 rows flagged
`is_imputed`, up from ~100) and `data/features/module2/
stage1_feature_table.csv` (unchanged shape: 53 columns, 32 fold-agnostic
features). Verified post-fix that `cases_lag_1` for the week immediately
following an imputed week is now `NaN` rather than the previously-silent
fabricated value.

### Reason
Merging week 53 into week 52 sums two real weeks' case counts *before* the
epidemic threshold is computed — for Module 2 specifically (unlike Module 1,
which only needs total magnitude for SARIMA) this risks (a) spuriously
tripping the outbreak threshold from merge arithmetic alone, and (b)
contaminating week 52's cross-year `historical_mean`/`SD` (used by
`labels.py`) for every year, not just the four merged ones — a genuine
label-integrity concern, not just a simplification worth revisiting later.
The `is_imputed` masking gap was an inconsistency: the label and
`case_anomaly_lag_*` already excluded fabricated seasonal-naive values from
biasing a statistic, but plain case-trend features did not.

### Impact
Modified `src/preprocessing/module2_preprocessing.py` (week-53 merge
functions removed; `find_missing_weeks`/`validate_weekly_modeling_table`
updated for variable weeks-per-year), `src/module2_classification/
feature_engineering.py` (masking fix; `MODULE2_MONSOON_WEEKS_NE` added).
Regenerated `data/processed/module2/weekly_modeling_table.csv` and
`data/features/module2/stage1_feature_table.csv`. The `k=2` label-balance
audit (`outputs/metrics/module2/label_balance_audit.csv`) required no rerun —
`scripts/data_audit_module2.py` already read the unmerged shared table
directly. Updated `research_context/RESEARCH_DECISIONS.md` (Decision 020),
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`, `module_2_classification/
MODULE_CONTEXT.md`, `research_context/FEATURE_ENGINEERING_SPEC.md`.

### Status
Accepted.

---

## 2026-07-27 - Module 1 Stage 2 XGBoost Residual Compensation Implemented

### Module
Module 1

### Change
Implemented `src/module1_forecasting/compensation_model.py`, `combine.py`,
and `main.py` (all previously placeholders), added `dm_test()` and
`ljung_box_diagnostics()` to `evaluate.py`, and ran the full pipeline
end-to-end against all 25 districts. Stage 2 is a **pooled** XGBoost
regressor (all 25 districts trained together, `District` as a categorical
feature) - one model per Stage 1 walk-forward fold (reusing Stage 1's exact
14 folds via `fold_id`/`split`), trained on pooled non-imputed out-of-sample
residuals from prior folds only. `combine.py` computes
`final_prediction = sarima_prediction + predicted_residual` (Decision 010)
and reports Stage-1-only vs Stage-1+Stage-2 accuracy (RMSE/MAE/sMAPE/MASE),
a Diebold-Mariano test, residual variance reduction, and a final Ljung-Box
check. `main.py` orchestrates the full pipeline (shared preprocessing ->
module1 preprocessing -> feature engineering -> Stage 1 -> Stage 2 ->
combine) idempotently, skipping any stage whose output already exists unless
`--force` is passed.

Also: `feature_engineering.py`'s `RAINFALL_COLUMN` switched from the
provisional `rain_sum (mm)` to `precipitation_sum (mm)` (Open Question #5,
resolved - see Decision 008) and `stage2_feature_table.csv` regenerated
before Stage 2 was built; `requirements.txt` gained an explicit `scipy` pin;
`src/config.py` gained the Stage 2/combine path constants.

**Major mid-implementation finding and fix**: the first full run used the
standard `objective="reg:squarederror"` and produced a deeply suspicious
result - 23/25 districts got *worse* with Stage 2 than without (e.g.
Colombo's RMSE rose from 162.8 to 274.0). Root cause: Stage 1's SARIMA
diverged catastrophically for `Vavuniya` in one walk-forward fold (2010
weeks 42-51, forecasts reaching ~30 million cases/week against an actual
mean of ~6/week - a residual of roughly -30,000,000). Because Stage 2 pools
every district into one squared-error-loss model, this single extreme value
dominated training globally and corrupted predicted residuals for every
*other* district too. Switching to `objective="reg:absoluteerror"` (MAE -
bounded gradient, immune to any single outlier's magnitude) fixed this
immediately. This is now documented as a required robustness property of
the pooled-model architecture (Decision 014), not a one-off patch. Stage 1's
Vavuniya divergence itself was not fixed at the source this session (flagged
as a new open question instead - Stage 1 is a separate, already-accepted
stage).

**A second, previously-undocumented structural finding**: there is a real
~26-week gap per district between the last walk-forward fold's validation
window and the holdout block's start (used as SARIMA training data for the
holdout fit but never scored out-of-sample). `residual_lag_1/2` are
therefore built by reindexing each district's residual onto the full weekly
calendar before taking `shift(1)/shift(2)`, rather than naively shifting the
sparse validation+holdout rows directly - the latter would have silently
treated fold 14's last residual as "1 week ago" for the holdout block's
first row (Decision 015).

**Result**: 24/25 districts improve on both validation-aggregate and holdout
MASE (median 42.8%/28.7% across all 25 districts); `Kilinochchi` is the sole
exception. Diebold-Mariano reaches significance (`p < 0.05`) for 12/25
districts at the larger validation+holdout scope, 4/25 at the stricter
holdout-only scope. The 18 non-seasonal-SARIMA districts show a larger
median improvement (43.2%/37.2%) than the 7 seasonal-SARIMA districts
(28.5%/24.3%), resolving Open Question #12 in favor of the original
sequencing bet (no Stage 1 rework currently justified). 23/25 districts
still show significant residual autocorrelation post-Stage-2 (Ljung-Box lag
26), an honest limitation flagged for future work.

### Reason
Stage 2's purpose is to learn systematic, predictable structure in Stage 1's
out-of-sample forecast error using climate, seasonal, and lagged-residual
features that SARIMA (deliberately univariate, per Decision 001) cannot see.
The pooled architecture was chosen over per-district models because
per-district training data is too thin for a many-feature GBM in early
walk-forward folds; the robust-loss fix was required once that pooling was
found to also pool a single district's data-quality problem into every
other district's correction.

### Impact
`src/module1_forecasting/compensation_model.py`, `combine.py`, `main.py`
(implemented), `evaluate.py` (`dm_test`, `ljung_box_diagnostics` added),
`feature_engineering.py` (`RAINFALL_COLUMN` changed), `src/config.py` (new
path constants), `requirements.txt` (`scipy` added). New data artifacts:
`data/processed/module1/xgboost_stage2_predictions.csv`,
`data/processed/module1/final_combined_predictions.csv`,
`models/module1/xgboost_folds/`, `models/module1/xgboost_final_model.json`,
`outputs/metrics/module1/xgboost_feature_importance.csv`,
`outputs/metrics/module1/xgboost_stage2_metrics.csv`,
`outputs/metrics/module1/combined_vs_baseline_metrics.csv`,
`outputs/metrics/module1/diebold_mariano_results.csv`,
`outputs/figures/module1/acf_residuals_final_*.png`.

### Status
Accepted

---

## 2026-07-27 - Module 1 Stage 1 SARIMA Baseline Implemented

### Module
Module 1

### Change
Implemented `src/module1_forecasting/baseline_sarima.py` and
`src/module1_forecasting/evaluate.py` (both previously 1-line placeholders)
and ran the full pipeline against all 25 districts. For each district,
`pmdarima.auto_arima` proposes a candidate SARIMA order for raw counts and
for `log1p` counts (one-time, constrained stepwise search on the full
pre-holdout history); both candidates are then genuinely walk-forward
validated (14 expanding-window folds, fixed-order `SARIMAX` refit per fold
per Decision 010) and the lower-aggregate-MASE transform is kept per
district. The final 104-week holdout block is forecast and scored once with
the winning config. Five design decisions were reviewed and approved before
implementation: (1) order search uses full pre-holdout history rather than
per-fold search (infeasible at scale - already benchmarked); (2) forecasts
from both candidates are clipped to a 0 floor after inverse-transforming;
(3) `SARIMAX` fits relax `enforce_stationarity`/`enforce_invertibility` for
robustness; (4) MASE (seasonal-naive scale) is the single deciding metric
for transform/config selection, with all four metrics logged for
transparency; (5) the holdout block is scored now (not deferred), clearly
labeled as a one-time, non-tuning report.

Also added: `src/config.py` (`MODULE1_SARIMA_PREDICTIONS_PATH`,
`MODULE1_SARIMA_CONFIG_PATH`, `MODULE1_SARIMA_METRICS_PATH`, plus their
parent-directory constants); `requirements.txt` pins for `pmdarima==2.1.1`,
`xgboost==3.2.0`, `statsmodels==0.14.6` (all already installed, previously
unpinned).

**Significant finding**: the seasonal-differencing test (`auto_arima`'s
default OCSB test, cross-checked against Canova-Hansen — both agree)
selected `D=0` for all 25 districts, and the constrained stepwise search
added no seasonal MA term for any district either. **18 of 25** selected
configs ended up with `seasonal_order=(0,0,0,52)` — a plain, non-seasonal
ARIMA despite `m=52` being specified. Forcing `D=1` was tested directly and
found computationally infeasible at scale (a single `D=1, m=52` SARIMAX fit
took 7+ minutes vs. ~0.01s for the `D=0` fixed-order refits used everywhere
else in this pipeline). This is documented as the top open finding from
Stage 1 (`module_1_forecasting/MODULE_CONTEXT.md` Open Question #12), not
silently patched over: 12/25 districts have validation-fold MASE > 1 (worse
than a naive "repeat last year's same week" forecast), and Ljung-Box tests
show significant residual autocorrelation in 23/25 districts, consistent
with the annual cycle not being captured by these particular selected
models. Zero-inflation % was checked as a possible explanation and largely
ruled out as the dominant driver (`Vavuniya`, one of the sparsest districts,
is the single best performer; `Colombo`, essentially never sparse, still
underperforms).

### Reason
Stage 2 (residual compensation) cannot be built without genuine
out-of-sample Stage 1 residuals to train on (Decision 010) - this was the
last blocking step before Stage 2 work can begin. The open SARIMA
order/log-transform questions (`module_1_forecasting/MODULE_CONTEXT.md`
Open Questions #1, #8) needed a concrete, evidence-based per-district
resolution rather than a single global assumption, given the project's
already-documented zero-inflation heterogeneity.

### Impact
- Added: `data/processed/module1/sarima_stage1_predictions.csv` (20,800
  rows), `models/module1/sarima_selected_configs.csv` (25 rows),
  `outputs/metrics/module1/sarima_walk_forward_metrics.csv` (400 rows),
  `outputs/figures/module1/acf_residuals_{Colombo,Kandy,Mullaitivu,
  Kilinochchi}.png`.
- Updated: `src/module1_forecasting/baseline_sarima.py`,
  `src/module1_forecasting/evaluate.py`, `src/config.py`, `requirements.txt`.
- Updated: `module_1_forecasting/MODULE_CONTEXT.md` (Open Questions #1, #2,
  #3, #7, #8 resolved/updated; new Open Questions #12-13; new "Stage 1
  Implementation Status" section), `module_1_forecasting/EXPERIMENT_LOG.md`
  (first real entry, M1-001), `research_context/RESEARCH_DECISIONS.md`
  (Decisions 009/010 status Proposed -> Accepted, implementation notes
  added).
- Explicitly untouched this session (per plan): `compensation_model.py`,
  `combine.py`, `main.py`.

### Status
Accepted (Stage 1 pipeline code and outputs). The AIC/seasonal-structure
finding (Open Question #12) is flagged Open, pending a future ablation
(STL+SARIMA or a forecast-horizon-aware order criterion) - not yet
resolved, and worth raising with the thesis supervisor before treating
Stage 1's absolute performance numbers as final.

---

## 2026-07-26 - Living Cursor Context System Added

### Module
All modules

### Change
Introduced living project documentation and Cursor rules so the agent can read and update project context as the research evolves.

### Reason
The project architecture, decisions, features, and approaches may change over time. Static rules can become outdated.

### Impact
Added/updated:

- `.cursor/rules/codexon_fyp.mdc`
- `research_context/PROJECT_CONTEXT.md`
- `research_context/CURRENT_ARCHITECTURE.md`
- `research_context/RESEARCH_DECISIONS.md`
- `research_context/CHANGELOG.md`
- module-specific context files

### Status
Accepted

---

## 2026-07-26 - Module 1 Data Realities Confirmed and New Decisions Proposed

### Module
Module 1 (with cross-module implication for Module 3 via population data)

### Change
User confirmed actual data characteristics for Module 1: full 2007–2026 weekly/daily coverage, Sri Lanka MoH epi-week standard (scraped), consistent district names, census population data (2001/2012/2024), single-point-per-district climate data (Open-Meteo constraint), and heavy zero-inflation in weekly case counts. Based on these facts, six new decisions were proposed (006–011): population used as a reporting-layer normalization only (not a Stage 1 target change), week-53 merged into week-52 for seasonal consistency, `weather_code` excluded from the feature set, walk-forward validation with a held-out final test block, a no-leakage rule for Stage 2 residual training, and a seasonal-naive imputation + flagging policy for missing weeks.

### Reason
Confirming real data characteristics resolved several previously open questions in `DATA_DICTIONARY.md` and `module_1_forecasting/MODULE_CONTEXT.md`, and surfaced new risks (zero-inflation, 53-week years, residual leakage) that needed explicit, documented handling before implementation begins.

### Impact
Updated:

- `research_context/DATA_DICTIONARY.md` (epi-week definition, spatial resolution caveat, population/census section, data quality notes)
- `research_context/RESEARCH_DECISIONS.md` (Decisions 006–011, all status Proposed pending final sign-off)
- `research_context/FEATURE_ENGINEERING_SPEC.md` (`weather_code` exclusion, week-53 merge note, feature change log)
- `module_1_forecasting/MODULE_CONTEXT.md` (resolved data questions, new zero-inflation open question, validation strategy, updated evaluation metrics)

### Status
Proposed (decisions 006–011 pending final user sign-off before implementation)

---

## 2026-07-26 - Raw Module 1 Data Audited and Cleaned

### Module
Module 1

### Change
Ran a full read-only audit (`scripts/data_audit_module1.py`, newly added) against the actual raw files placed in `data/raw/epidemiological/` and `data/raw/weather/`. Found and worked with the user through a joint iterative fix of five `(District, Year, Week)` collisions in the case data (2010 week 34/35 mislabeling, a 2012/2013 year-boundary mislabel, a 2014 week 2/3 double-track ambiguity, and a 2022/2023 year-boundary mislabel with a corrupted date). Also found and fixed two single-row district-name typos (`Moneragala`, `Puttlam`). Confirmed `Kalmunai` has a real 19-year case history but no matching weather station, and decided (Decision 012) to merge it into `Ampara`. Confirmed the `Humidity/` weather subfolder is fully redundant with `Weather (Except Humidity)/` (byte-identical humidity values) and should be dropped as a source. Corrected the earlier zero-inflation characterization: it is concentrated in 5 Northern/Eastern districts, not universal. Confirmed the earlier "encoding corruption" concern was a chat-display artifact, not a real file issue.

### Reason
The raw case data had genuine week-numbering integrity issues that would have silently corrupted any merge with climate data (row fan-out) and any SARIMA seasonal fitting (broken 7-day cadence) if left unresolved.

### Impact
- `data/raw/epidemiological/dengue_cases_corected.csv` — corrected in place by the user, verified by re-running the audit script until 0 duplicate rows remained.
- `research_context/DATA_DICTIONARY.md` — epi-week definition, climate source-folder guidance, and Data Quality Notes table updated with verified facts.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 012 (Kalmunai → Ampara merge, Accepted); confirmed scope note added to Decision 011.
- `module_1_forecasting/MODULE_CONTEXT.md` — to be updated with final confirmed district list and data status.
- Added `scripts/data_audit_module1.py` as a reusable, read-only diagnostic — safe to re-run after any future edits to the raw case file.

### Status
Accepted (data-cleaning outcomes); Decision 012 Accepted; Decisions 006-011 remain Proposed pending pipeline implementation

---

## 2026-07-26 - Layered Pipeline Architecture Adopted; Detailed Build Plan Created

### Module
All modules

### Change
Corrected a design flaw: several transformations (week-53 merge, missing-week imputation, `weather_code` exclusion) had been implicitly treated as general-purpose data cleaning, when they actually exist to satisfy Module 1's SARIMA-specific assumptions. Adopted a layered pipeline (Decision 013): a shared, module-agnostic preprocessing stage (`data/processed/shared/`) feeding into separate module-specific preprocessing and feature-engineering stages (`data/processed/moduleN/`, `data/features/moduleN/`). Also corrected the missing-week count under Decision 011 using a more rigorous method (true label-gap detection instead of row-count comparison): the real picture is 4 weeks missing nationwide across all districts, plus a few district-specific gaps, totaling 104 rows (not the smaller, less accurate estimate previously recorded). Created a detailed technical build plan covering the shared layer and the full Module 1 pipeline, ready to implement.

### Reason
Applying Module-1-specific transformations at a shared layer would have silently discarded real data and imposed unproven feature-selection choices on Module 2 and Module 3 before their own designs are finalized.

### Impact
- Added `docs/PIPELINE_ARCHITECTURE_PLAN.md` (new, detailed technical build plan).
- `research_context/CURRENT_ARCHITECTURE.md` — added the layered pipeline diagram and guiding principle.
- `research_context/RESEARCH_DECISIONS.md` — added Decision 013; re-scoped Decisions 007, 008, 011 to Module 1 only; corrected Decision 011's confirmed missing-week count.
- `research_context/FEATURE_ENGINEERING_SPEC.md` — added fold-aware computation requirement for climate anomaly features.
- `module_1_forecasting/MODULE_CONTEXT.md` — added an Implementation Plan section.
- `module_2_classification/MODULE_CONTEXT.md`, `module_3_spatial/MODULE_CONTEXT.md` — added data pipeline consumption notes clarifying they do not inherit Module 1's modeling-specific choices.

### Status
Accepted

---

## 2026-07-27 - Population Census Data Placed; Decision 006 Finalized

### Module
Module 1 (cross-module implication for Module 3)

### Change
Placed the population census file at `data/raw/population/population_by_district.csv`
(2001/2012/2024, 25 districts, wide format). Corrected the source's `Moneragala`
spelling to `Monaragala` on ingestion to match the rest of the pipeline. Confirmed
`Kalmunai` needs no separate population row (administratively part of Ampara).
Finalized Decision 006's interpolation method: linear between census points,
linear extrapolation using the 2012→2024 slope for 2025-2026. This was previously
the last blocker on Shared Layer Step 4 in `PIPELINE_ARCHITECTURE_PLAN.md`.

### Reason
The pipeline-implementation prompt drafted for the next session needed a real answer
for the population step rather than an open TODO.

### Impact
- Flagged a genuine methodological limitation while reviewing the data: `Kilinochchi`,
  `Mullaitivu`, and `Mannar` show a non-monotonic 2001→2012→2024 population trend
  (sharp decline then recovery), consistent with civil-war-era displacement in the
  Vanni region ending 2009 — right when the case/climate data begins. Linear
  interpolation can't recover the true 2007-2012 population path for these 3
  districts. Since population is a reporting-layer-only denominator (Decision 006),
  this doesn't touch the modeling target, but `cases_per_100k` for these districts in
  that period should be reported with an explicit caveat. Documented in
  `DATA_DICTIONARY.md` Section 3 and `RESEARCH_DECISIONS.md` Decision 006.
- `research_context/DATA_DICTIONARY.md` — new Population section content, source file
  location, coverage check, district-name correction, limitation table rows.
- `research_context/RESEARCH_DECISIONS.md` — Decision 006 status Proposed → Accepted.
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` — Shared Step 4 unblocked, exact
  melt/interpolate/extrapolate steps specified, Open Items list updated.
- `module_1_forecasting/MODULE_CONTEXT.md` — Resolved Data Questions updated.

### Status
Accepted

---

## 2026-07-27 - Shared Preprocessing Layer and Module 1 Pipeline Implemented

### Module
All modules (shared layer); Module 1 (preprocessing, validation, feature engineering)

### Change
Implemented and ran, end to end against the real data, everything specified
in `PIPELINE_ARCHITECTURE_PLAN.md`'s Stage 0 / Shared Layer / Module 1 Layer
sections: `src/config.py` (real 25-district list, `MONSOON_WEEKS_SW`/`_NE`),
`src/preprocessing/shared.py` (Kalmunai->Ampara merge, master epi-week
calendar, climate weekly aggregation, population interpolation),
`src/preprocessing/module1_preprocessing.py` (week-53 merge, seasonal-naive
imputation, climate + population merge, `cases_per_100k`), and two new
files, `src/module1_forecasting/validation.py` (walk-forward fold generator,
`fit_window`/`get_holdout_series` no-leakage helpers) and
`src/module1_forecasting/feature_engineering.py` (fold-agnostic Stage 2
features + a `compute_fold_climate_anomalies` function for the fold-aware
ones). `baseline_sarima.py`/`compensation_model.py`/`combine.py`/
`evaluate.py`/`main.py` remain out of scope (SARIMA order selection, log1p
vs raw, etc. are still open research questions).

While spot-checking the master epi-week calendar (explicitly required by the
build plan before trusting it downstream), found a **new, previously
undiscovered data-quality issue distinct from the 5 collisions fixed
2026-07-26**: 30 `(Year, Week)` labels across 2008-2024 have a date stamp
that essentially all districts agree on (so it never showed up as a
duplicate-key or per-row disagreement) but that is chronologically
inconsistent with neighbouring weeks - almost certainly a page-level MoH
scrape error for that specific week, not a per-row transcription slip. This
measurably breaks the day-to-week join for climate aggregation on 15 of
those weeks (375 of 25,350 rows in `weekly_modeling_table.csv` have no
matching climate because of this; a further 125 rows have no climate for
the separate, expected reason that climate coverage doesn't extend into the
2006/2026 boundary years). Also confirmed the 4 documented nationwide case-data
gaps (`2015 Wk30`, `2020 Wk1`, `2021 Wk42`, `2022 Wk43`) have zero raw rows
for any district at all - not even a calendar entry - and added a
conservative `fill_isolated_calendar_gaps` step to `shared.py` that
sequentially infers a date only when it fits an unambiguous single 7-day
slot; this recovered dates for 3 of the 4 (`2020 Wk1` could not be dated -
2019's confirmed week-53 already runs through 2020-01-03, leaving no gap for
a "week 1"). None of this was silently patched into "correct" values - it
is fully logged, written to diagnostic CSVs
(`epi_week_calendar_chronology_issues.csv`,
`epi_week_calendar_disagreements.csv`) in `data/processed/shared/`, and
flagged for the same joint human-review process used for the earlier 5
collisions.

### Reason
The build plan explicitly required spot-checking the calendar-construction
step for ties/ambiguous cases before trusting it downstream; doing so
surfaced a real, previously-unknown, and non-trivial data quality issue
(distinct in kind from the already-fixed collisions) that affects climate
feature completeness for ~2% of Module 1's weekly rows.

### Impact
- Added: `data/processed/shared/{epi_week_calendar.csv, climate_weekly.csv,
  population_annual.csv, epidemiological_weekly.csv,
  epi_week_calendar_disagreements.csv,
  epi_week_calendar_chronology_issues.csv}`.
- Added: `data/processed/module1/weekly_modeling_table.csv`.
- Added: `data/features/module1/stage2_feature_table.csv`.
- Updated: `src/config.py`, `src/preprocessing/shared.py`,
  `src/preprocessing/module1_preprocessing.py`.
- Added: `src/module1_forecasting/validation.py`,
  `src/module1_forecasting/feature_engineering.py`.
- Updated: `module_1_forecasting/MODULE_CONTEXT.md` (implementation status,
  deviations from plan, 3 new open questions #9-11),
  `research_context/PIPELINE_ARCHITECTURE_PLAN.md` (status/last-updated,
  new open item for the chronology-issue discovery),
  `research_context/DATA_DICTIONARY.md` (new Data Quality Notes rows).

### Status
Accepted (pipeline code); the newly discovered 30-week date-mislabeling
issue is flagged Open, pending team review - not yet resolved.

---

## 2026-07-27 - Systematic Date-Mislabeling Issue Resolved in Raw Epidemiological Data

### Module
Module 1 (raw data feeds all downstream shared/Module 1 outputs)

### Change
Resolved the 30-week systematic date-mislabeling issue discovered while
implementing the shared preprocessing layer (previous entry). The user
manually corrected 28 of the 30 flagged `(Year, Week)` labels in
`dengue_cases_corected.csv` against the original MoH source pages,
reporting back a detailed row-by-row account of what was found and fixed
(mostly month-field-off-by-one errors and week-boundary overlaps). The
assistant then re-ran the pipeline and cross-checked every one of the 30
against the regenerated calendar, which found:

- **2 of the 30 the user's pass had missed** (`2009 Wk24`, `2023 Wk40`) —
  both had the same month-field error as the other 28, just not caught
  during manual review. Corrected by the assistant.
- **A full-calendar day-count scan** (checking *every* week in the dataset
  for exactly 7 days and a clean 1-day gap to its neighbour, not just the
  overlap-based check that found the original 30) surfaced 3 more
  previously-undetected date-entry errors that don't manifest as overlaps
  and so were invisible to both the original diagnostic and the user's
  manual review: `2010 Wk9` (end date literally before its start date),
  `2011 Wk48` (start date 3 days late, producing a 4-day week), and
  `2013 Wk39`/`Wk40` (a 1-day boundary misplacement). Corrected by the
  assistant.
- The 2 outstanding per-row disagreements from the original diagnostic
  (`Ampara 2013 Wk51`, `Ampara 2023 Wk14`) were also corrected.
- **2 weeks accepted as irregular by design**: `2009 Wk17` (8 days) and
  `2009 Wk22` (6 days) each sit in a stretch with a genuine 1-day
  surplus/deficit in the source that cannot be fixed by editing one date
  without opening a new gap with an already-correct neighbour — verified
  concretely rather than assumed (the assistant initially "fixed" `2009
  Wk17` by shortening it, found this created a brand-new 2-day gap with
  `Wk18`, and reverted the change).
- **1 low-priority item left open**: a genuine 3-day gap between `2025
  Wk52` and `2026 Wk1` at the live-scrape edge of the dataset.
- Also fixed a minor pipeline robustness bug found during verification:
  `shared.py` previously only wrote the two chronology/disagreement
  diagnostic CSVs when non-empty, so a clean re-run after fixing the
  underlying data left a stale issues file on disk from the previous run.
  `run_shared_preprocessing()` now always rewrites both files.

Re-ran the full pipeline (`shared.py` → `module1_preprocessing.py` →
`feature_engineering.py`) after every fix to confirm no regressions.
`epi_week_calendar_chronology_issues.csv` and
`epi_week_calendar_disagreements.csv` are now both empty. All 375 climate
rows previously blocked by this issue in `weekly_modeling_table.csv` are
now populated; the only remaining 150 "no matching climate" rows are the
expected boundary cases (2006 Wk52 before climate coverage begins, 2020
Wk1's dateless rows, 2026 Wk22-25 after current climate coverage ends).

### Reason
The 30-week issue was flagged as needing joint human review before
correcting the raw source, per the same process used for the 5 collisions
fixed 2026-07-26. Verifying the user's fixes against the regenerated
calendar (rather than trusting the fix count at face value) surfaced
additional real errors invisible to both the original overlap-only
diagnostic and manual source-page review, which would have silently
persisted into the modeling data otherwise.

### Impact
- `data/raw/epidemiological/dengue_cases_corected.csv` — corrected in place
  (28 rows by the user; 5 more date fixes + 2 disagreement fixes + 3 stale
  `Month`-column cosmetic fixes by the assistant; all changes verified via
  full pipeline re-run).
- `src/preprocessing/shared.py` — diagnostic CSVs now always rewritten
  (fixes staleness bug).
- Regenerated: all `data/processed/shared/*.csv`,
  `data/processed/module1/weekly_modeling_table.csv`,
  `data/features/module1/stage2_feature_table.csv`.
- `research_context/DATA_DICTIONARY.md` — Data Quality Notes rows updated
  from Open to Resolved, with exact before/after values for every fix and
  the two accepted-irregular-week exceptions documented.
- `research_context/PIPELINE_ARCHITECTURE_PLAN.md` — Open Item 4 marked
  resolved; Open Item 5 (`2020 Wk1` dateless week) remains open and
  unrelated to this fix.
- `module_1_forecasting/MODULE_CONTEXT.md` — Open Question #10 marked
  resolved with full detail; `climate_weekly.csv` row count updated
  (24,950 → 25,300).

### Status
Accepted. Open Item 5 (`2020 Wk1`) and the `2025 Wk52`/`2026 Wk1` 3-day
gap remain open, unrelated data-quality items requiring separate team
decisions.

---

## 2026-07-26 - Module-Level Documentation Structure Added

### Module
All modules

### Change
Created separate module folders with their own `MODULE_CONTEXT.md` and `EXPERIMENT_LOG.md` files.

### Reason
Three team members work on separate modules. Each module needs its own source of truth.

### Impact
Added:

- `module_1_forecasting/MODULE_CONTEXT.md`
- `module_1_forecasting/EXPERIMENT_LOG.md`
- `module_2_classification/MODULE_CONTEXT.md`
- `module_2_classification/EXPERIMENT_LOG.md`
- `module_3_spatial/MODULE_CONTEXT.md`
- `module_3_spatial/EXPERIMENT_LOG.md`

### Status
Accepted

---

## 2026-07-27 - Raw Weather Folder Flattened; Build Plan Relocated

### Module
All modules (Module 1 most directly affected)

### Change
The user moved the 25 canonical per-district weather CSVs out of the nested
`data/raw/weather/Weather (Except Humidity)/` subfolder directly into
`data/raw/weather/`, and deleted the now-redundant `data/raw/weather/Humidity/`
subfolder entirely (both subfolders no longer exist). Separately,
`PIPELINE_ARCHITECTURE_PLAN.md` was relocated from `docs/` to
`research_context/` (the `docs/` folder no longer exists). Updated all path
references accordingly: `DATA_DICTIONARY.md`, `module_1_forecasting/MODULE_CONTEXT.md`,
`PIPELINE_ARCHITECTURE_PLAN.md` itself (weather path), and `scripts/data_audit_module1.py`
(simplified to a single `WEATHER_DIR` with no Humidity-comparison logic); and all
`docs/PIPELINE_ARCHITECTURE_PLAN.md` cross-references in `CURRENT_ARCHITECTURE.md`,
`RESEARCH_DECISIONS.md`, `FEATURE_ENGINEERING_SPEC.md`, and all three
`MODULE_CONTEXT.md` files were repointed to `research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Reason
Keep living documentation and scripts in sync with the actual raw-data folder
layout and file locations on disk, so pipeline code written against these paths
doesn't break.

### Impact
Weather ingestion in the upcoming `src/preprocessing/shared.py` should read
`data/raw/weather/*.csv` directly (no subfolder). All references to
`docs/PIPELINE_ARCHITECTURE_PLAN.md` should be read as
`research_context/PIPELINE_ARCHITECTURE_PLAN.md`.

### Status
Accepted

---

## 2026-07-27 - Stage 1 Explosive-AR-Root Fix; Real-World Outbreak Sanity Check

### Module
Module 1

### Change
Fixed the `Vavuniya`/`Mannar` SARIMA divergence flagged as Open Question #14
during Stage 2 development: `baseline_sarima.fit_and_forecast()` now checks
every fitted SARIMAX model's combined AR polynomial roots and treats any fit
with a root on or inside the unit circle (non-stationary/explosive despite
`enforce_stationarity=False`) as a failed fit (`NaN` for that fold), instead
of returning an unbounded-growth forecast. Confirmed via a full 25-district
scan that this affects exactly two folds: `Vavuniya` fold 1 (2010, AR(1)
coefficient 1.266) and `Mannar` fold 13 (2022, seasonal AR coefficient
1.162). The full Stage 1 → Stage 2 → combine pipeline was regenerated
(`main.py --force --stages stage1_sarima stage2_xgboost combine`, ~62
minutes). `compensation_model.py` (`_trainable_mask()`) and `combine.py`
(`residual_variance_reduction()` switched to `np.nanvar`) were hardened to
correctly handle the newly-possible `NaN` residual rows. Also fixed a
sign-convention bug found while re-verifying results: `evaluate.dm_test`'s
docstring had `mean_loss_diff`'s interpretation backwards (the code was
already correct; only the prose was wrong).

Separately, while investigating whether the framework could predict the
real, ongoing 2026 Colombo/Gampaha dengue outbreak (the dataset already
extends to 2026 week 25, which includes the actual spike inside the
untouched holdout block), found that the shared climate data pipeline has
not been refreshed past 2026 week 21 - leaving every climate feature `NaN`
for weeks 22-25, exactly the weeks containing the outbreak spike.

### Reason
The Vavuniya/Mannar divergence was previously only mitigated at the Stage 2
level (Decision 014's MAE loss switch contained the symptom) but never
fixed at the source, and was explicitly flagged in Open Question #14 as
worth a targeted look. A user question about the framework's real-world
predictive accuracy on the current outbreak prompted revisiting this fix
before further real-world evaluation, and separately surfaced the climate
data currency gap as a distinct, actionable finding.

### Impact
- `data/processed/module1/sarima_stage1_predictions.csv`,
  `models/module1/sarima_selected_configs.csv`,
  `outputs/metrics/module1/sarima_walk_forward_metrics.csv`,
  `data/processed/module1/xgboost_stage2_predictions.csv`,
  `data/processed/module1/final_combined_predictions.csv`,
  `outputs/metrics/module1/combined_vs_baseline_metrics.csv`, and
  `outputs/metrics/module1/diebold_mariano_results.csv` all regenerated.
- Stage 2's headline result improved from 24/25 to **25/25 districts**
  improving on validation-aggregate MASE; median validation MASE
  improvement 43.5% (was ~42.8%), median holdout MASE improvement 32.7%
  (was ~28.7%). `Vavuniya` went from one of the most fragile districts to
  one of the best. Holdout win rate is 23/25 (`Kilinochchi`, `Mannar` show
  small, non-significant holdout regressions).
- `module_1_forecasting/MODULE_CONTEXT.md` (Open Question #14 resolved and
  fixed; Open Question #12's numbers refreshed; new Open Question #16 for
  the climate-data-lag/real-world-outbreak finding; "Stage 1/2
  Implementation Status" sections fully refreshed).
- `research_context/RESEARCH_DECISIONS.md` (new Decision 017; Decision 016
  annotated as superseded by it).
- `module_1_forecasting/EXPERIMENT_LOG.md` (new entry M1-003).
- The climate data pipeline currency gap (2026 weeks 22-25) is flagged but
  **not yet fixed** - re-running the shared climate preprocessing (Open-Meteo
  fetch) through the current date is a follow-up action item.

### Status
Accepted

---

## 2026-07-27 - Module 1 Forward Production Forecast Added

### Module
Module 1

### Change
Added `src/module1_forecasting/forecast_future.py` (new): generates a
genuine forward forecast for 8 weeks beyond the last available case-count
week (2026 weeks 26-33), for all 25 districts. Stage 1 is refit on each
district's entire available history and forecasts 8 steps ahead in one
deterministic call; Stage 2 applies the existing final production XGBoost
model recursively (real historical values feed the first 1-2 future weeks'
lag features, then the script's own prior-step predictions feed all later
weeks). A `feature_completeness_pct` diagnostic is reported per row to
quantify declining confidence with horizon. Outputs
`data/processed/module1/future_forecast.csv` and illustrative plots for
`Colombo`/`Gampaha`.

### Reason
Prompted by the user asking whether Module 1's testing was complete and
whether it can predict genuinely future case counts - a different question
from the already-answered "does the holdout MASE improve" (M1-002/M1-003).
No existing script in the pipeline could answer this: walk-forward
validation and the holdout block both score against data already present in
the dataset, not genuinely new weeks.

### Impact
- New file `data/processed/module1/future_forecast.csv` (200 rows) and new
  plots `outputs/figures/module1/future_forecast_{Colombo,Gampaha}.png`.
- `src/config.py`: added `MODULE1_FUTURE_FORECAST_PATH`.
- For the real-outbreak districts: `Colombo`'s forecast settles to a
  ~460-470/week plateau (from a pre-spike ~300-500/week baseline);
  `Gampaha`'s settles to a ~1,360-1,370/week plateau (from ~200-500/week) -
  both clearly elevated but not simply repeating the single week-25 spike
  value (1,138/1,294), consistent with the model discounting what may be a
  partly reporting-lag-driven outlier (a suspicious week-24 dip precedes the
  spike in both districts).
- `feature_completeness_pct` declines from 56.2% (horizon step 1) to 43.8%
  (steps 5-8) as `residual_lag_1/2` become fully recursive and climate lags
  run out of range - reported explicitly rather than hidden.
- Deliberately **not** wired into `main.py`'s orchestration and does **not**
  close Open Question #16's climate-data-currency gap or substitute for the
  still-not-built rolling 1-week-ahead re-evaluation - both remain open.
- `research_context/RESEARCH_DECISIONS.md` (new Decision 018).
- `module_1_forecasting/MODULE_CONTEXT.md` (new "Forward Production
  Forecast" section).
- `module_1_forecasting/EXPERIMENT_LOG.md` (new entry M1-004).

### Status
Accepted
