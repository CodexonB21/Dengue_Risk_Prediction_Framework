# Stage 2 Upgrade Experiment Plan (M1-006 / M2-007)

**Status:** M1-006A/B + M2-007A/C/D complete (2026-07-29); M1-006C + M2-007B/E pending  
**Date drafted:** 2026-07-29  
**Authors:** Team Codexon  
**Purpose:** Extend the residual-compensation framework with research-backed Stage 2 upgrades for Module 1 (forecasting) and Module 2 (classification), with explicit leakage guards and holdout-gated adoption.

---

## Baseline to Beat (current production, post M1-005 / M2-006)

### Module 1 holdout (104 weeks × 25 districts, non-imputed)

| Model | Median MASE | Median sMAPE | Pooled holdout sMAPE |
|---|---:|---:|---:|
| SARIMA only | 0.622 | 67.4% | 79.4% |
| **Hybrid (current)** | **0.386** | **35.0%** | **42.3%** |
| Improvement | 23/25 districts MASE ↓, median **32.9%** | — | — |

Rolling 1-step (operational, separate estimand): median holdout sMAPE **39.0%**.

### Module 2 holdout (official: RF Stage 1 + isotonic Stage 2)

| Metric | Stage 1 (RF) | Stage 2 (isotonic, selected) |
|---|---:|---:|
| PR-AUC | 0.429 | 0.412 |
| ROC-AUC | 0.885 | 0.882 |
| Recall @ 0.5 | 0.55 | 0.45 |
| **Alert recall @ 0.14** | — | **~0.60** |
| **Alert precision @ 0.14** | — | **~0.34** |

---

## Shared Rules (both modules)

1. **No retraining on holdout.** All upgrades must preserve Decision 009/010 walk-forward + 2-year holdout.
2. **Holdout-gated adoption.** An upgrade is accepted only if holdout metrics improve on pre-registered criteria (below) without validation-only overfitting.
3. **Same test set.** Compare all variants on identical 2,600 non-imputed holdout rows unless noted.
4. **Document every decision** in `RESEARCH_DECISIONS.md`, `CHANGELOG.md`, relevant `EXPERIMENT_LOG.md`.
5. **Do not cite operational/live outputs** as validation evidence.

---

# Experiment M1-006: Advanced Stage 2 Compensation (Forecasting)

## Research question

Can log-scale (multiplicative) residual compensation and a lightweight reporting-delay layer improve holdout forecast accuracy beyond additive `residual = actual − sarima_prediction`, especially on outbreak-adjacent weeks, without breaking the residual-compensation thesis narrative?

## Phases (implement in order; each phase is a separate ablation)

### M1-006A — Log-scale / multiplicative residuals

**Change:**
```text
r_log = log1p(actual) − log1p(sarima_prediction)
final_prediction = expm1(log1p(sarima_prediction) + predicted_r_log)
```
Stage 2 XGBoost predicts `r_log` instead of additive residual. Clip `final_prediction ≥ 0`.

**Implementation touchpoints:**
- `src/module1_forecasting/compensation_model.py` — target column, inverse transform in output builder
- `src/module1_forecasting/combine.py` — final forecast assembly
- `src/module1_forecasting/rolling_one_step.py` — same inverse transform
- Optional: only apply log-residual for districts where Stage 1 already uses `use_log1p=True` (ablation)

**Metrics (primary — holdout, per district + pooled):**
- Median MASE (vs seasonal naive and vs current additive hybrid)
- Median sMAPE, MAE, RMSE
- % districts with MASE improvement vs current hybrid
- Diebold-Mariano test vs current hybrid (pooled + holdout-only)

**Secondary (pre-registered slices, not for adoption alone):**
- sMAPE on 2026 Wk22–23 (ramp)
- sMAPE on 2026 Wk25 (catch-up spike — expect limited gain; document honestly)
- Rolling 1-step median holdout sMAPE (operational)

**Leakage checks:**
- Stage 2 train target uses only out-of-sample SARIMA preds from prior folds (unchanged Decision 010)
- `log1p(actual)` for target only on rows where residual is computed from fold OOS preds — never in-sample SARIMA residuals for training
- Feature columns unchanged; no future case counts in features

**Accept if:** Median holdout MASE ≤ current hybrid (0.386) AND ≥ 20/25 districts not worse by >5% relative MASE; OR median sMAPE improves ≥3 pp with ≤2 districts severely harmed (>25% MASE increase).

---

### M1-006B — Reporting-delay / nowcasting layer (extends Decision 028)

**Change:** Add a simple reporting-state feature group + optional nowcast adjustment:

1. **Features (fold-agnostic, masked):**
   - `weeks_since_reporting_anomaly` (cap at 4)
   - `reporting_rebound_ratio_lag1` = cases[t−1] / max(cases[t−2], 1) when prior week was flagged
   - `suspected_backfill_week` = bool (from existing `is_reporting_anomaly`)

2. **Optional nowcast target for flagged weeks only (ablation):**
   When scoring week *t* and week *t−1* is `is_reporting_anomaly`, replace `cases_lag_1` input with `max(cases_lag_2, rolling_mean_cases_4w)` — imputation for feature derivation only, not labels.

3. **Do NOT** rewrite raw `Number_of_Cases` in the evaluation table.

**Implementation touchpoints:**
- `src/preprocessing/reporting_anomalies.py` — export helper for rebound features
- `src/module1_forecasting/feature_engineering.py` — new feature group
- `research_context/FEATURE_ENGINEERING_SPEC.md` — document before coding
- Retrain Stage 2 only if features change (Stage 1 SARIMA unchanged)

**Metrics:** Same as M1-006A.

**Leakage checks:**
- Rebound features use only past weeks relative to prediction week
- Nowcast imputation uses only information available before week *t*
- Flagged weeks excluded from residual **targets** if they remain untrusted (same as Decision 028)

**Accept if:** Combined with best of 006A or additive baseline, median holdout MASE improves OR 2026 Wk22–23 pooled sMAPE improves ≥5 pp without >2 pp degradation on full-holdout median sMAPE.

---

### M1-006C — Distributional Stage 2 (optional stretch)

**Change:** Quantile XGBoost for residual (τ = 0.1, 0.5, 0.9). Point forecast = median quantile.

**Metrics:** Pinball loss + interval coverage (80% PI) on holdout; secondary: median MASE vs point baseline.

**Accept if:** Median MASE within 5% of best point model AND 80% PI coverage ∈ [70%, 90%] pooled.

---

## M1-006 deliverables

| Artifact | Path |
|---|---|
| Predictions | `data/processed/module1/final_combined_predictions_m1_006_<variant>.csv` |
| Metrics | `outputs/metrics/module1/m1_006_<variant>_vs_baseline.csv` |
| Experiment log | `module_1_forecasting/EXPERIMENT_LOG.md` (M1-006) |
| Decision | `research_context/RESEARCH_DECISIONS.md` (Decision 030 if accepted) |

---

# Experiment M2-007: Advanced Stage 2 Compensation (Classification)

## Research question

Can logit-residual correction, cost-sensitive learning, M1-fed momentum features, and consecutive-week alert rules improve holdout PR-AUC and alert recall/precision beyond isotonic calibration alone?

## Phases (implement in order)

### M2-007A — Logit-residual Stage 2 (new architecture)

**Change:** Add architecture `logit_residual` alongside isotonic/platt/stacked:

```text
logit(p_final) = logit(p_stage1) + g(features)
p_final = sigmoid(logit(p_final))
```

Train `g` as pooled XGBoost regressor on **out-of-sample** Stage 1 probabilities only (mirror M1 fold structure). Clip probabilities to [ε, 1−ε] before logit.

**Implementation touchpoints:**
- `src/module2_classification/compensation_model.py` — new architecture branch
- Benchmark via existing BSS/PR-AUC framework (Decision 022)

**Metrics (primary — holdout):**
- PR-AUC, ROC-AUC
- Brier score, Brier Skill Score vs Stage 1
- At F2-optimal alert threshold (re-derived per variant): precision, recall, F1, F2
- At fixed 0.14 threshold: precision, recall (compare to ~0.34 / ~0.60 baseline)

**Leakage checks:**
- `g` trained only on OOS Stage 1 probs from folds 1..k−1 when predicting fold k
- Holdout model trained on all validation folds only
- No `Number_of_Cases` at week *t* in features (unchanged)
- Do not use holdout labels for threshold selection

**Accept if:** Holdout PR-AUC > 0.412 (current isotonic) OR alert recall ≥ 0.65 at alert=0.14 with precision ≥ 0.30.

---

### M2-007B — Cost-sensitive Stage 2 (isotonic + logit variants)

**Change:** For any tree-based Stage 2 (`logit_residual`, `stacked_xgboost`):
- `scale_pos_weight` tuned on fold-train prevalence (not global)
- Optional focal-loss custom objective (ablation)

**Metrics:** Same as M2-007A.

**Accept if:** Holdout alert recall improves ≥5 pp vs matched non-cost variant at same threshold scan, without PR-AUC drop >0.02.

---

### M2-007C — Consecutive-week alert rule (post-processing, no retrain)

**Change:** Add rule on top of calibrated probabilities:

```text
alert_flag = (calibrated_probability >= τ) OR
             (calibrated_probability >= τ_ramp AND cases_lag_1 / cases_lag_2 >= ρ)
```

Grid-search `τ_ramp`, `ρ` on validation folds only; apply selected rule to holdout.

**Implementation touchpoints:**
- `src/module2_classification/risk_thresholds.py` or new `alert_rules.py`
- `live_scoring.py` — apply same rule

**Metrics:** Holdout precision/recall/F2 vs single-threshold baseline at same alert rate budget.

**Leakage checks:**
- Rule parameters fit on validation only
- `cases_lag_1/2` masked for `is_imputed` and `is_reporting_anomaly` (Decision 028)

**Accept if:** Recall ≥ 0.65 with precision ≥ baseline (0.34) OR F2 improves ≥0.05 at holdout.

---

### M2-007D — M1-fed features in evaluation-safe pipeline

**Change:** Add Stage 2 features from Module 1 OOS forecasts:
- `m1_final_prediction_lag_1`
- `m1_forecast_momentum` = m1_lag_1 − cases_lag_2

**Critical:** Join holdout-safe M1 preds from `final_combined_predictions.csv` / walk-forward files — **never** in-sample SARIMA or production model fit on holdout.

For forward weeks only: already approved (Decision 027). This phase extends to **historical validation/holdout rows** using fold OOS M1 outputs only.

**Implementation touchpoints:**
- `src/module2_classification/feature_engineering.py`
- Join script or merge in `compensation_model.py`
- New Decision superseding Decision 019 deferral for **evaluation-only** M1 integration

**Metrics:** Same as M2-007A; slice metrics on 2026 Wk20–25.

**Leakage checks:**
- M1 preds used at week *t* must come from Stage 1+2 walk-forward OOS for that row's fold — not refit-on-all-data production model
- Document join keys `(District, Year, Week, fold_id)`

**Accept if:** Holdout PR-AUC gain ≥ 0.02 OR alert recall @ 0.14 gain ≥ 5 pp without precision collapse (<0.25).

---

### M2-007E — Ramp-sensitive labels (optional, higher scope)

**Change:** Add secondary label `label_ramp` = 1 when cases exceed threshold for **2 consecutive weeks** (district-adaptive k). Ablation only — do not replace primary label without supervisor sign-off.

**Metrics:** PR-AUC on ramp label vs epidemic threshold label.

**Accept if:** Ramp label PR-AUC > 0.50 on holdout AND thesis narrative updated.

---

## M2-007 deliverables

| Artifact | Path |
|---|---|
| Predictions | `data/processed/module2/stage2_compensated_predictions_m2_007_<variant>.csv` |
| Threshold scan | `outputs/metrics/module2/m2_007_<variant>_threshold_scan.csv` |
| Experiment log | `module_2_classification/EXPERIMENT_LOG.md` (M2-007) |
| Decision | `research_context/RESEARCH_DECISIONS.md` (Decision 031 if accepted) |

---

## Recommended implementation order (fresh session)

1. Read mandatory context (see kickoff prompt below).
2. **M1-006A** (log residuals) — smallest code change, clear ablation.
3. **M2-007C** (alert rule) — quick win, no retrain.
4. **M2-007A** (logit-residual) — core M2 upgrade.
5. **M1-006B** (reporting-delay features).
6. **M2-007D** (M1-fed features, leakage-critical).
7. **M2-007B** / **M1-006C** / **M2-007E** — time permitting.

---

## Defense talking points (pre-write)

- **Thesis continuity:** All variants extend "Stage 1 baseline + Stage 2 correction," not replace the framework.
- **Why not SMOTE:** M2-006 already rejected; cost-sensitive weights preferred.
- **Why log / logit:** Handles skewed counts and bounded probabilities — standard in hybrid epidemiological models.
- **Honest limits:** Reporting catch-up spikes may remain hard even after 006B; report slice metrics separately.

---

## References to cite (literature hooks)

- Hybrid ARIMA + ML error correction ( epidemiological forecasting reviews )
- Log-Gaussian / multiplicative error models for count time series
- Reporting delay / nowcasting in infectious disease surveillance (CDC/Euro surveillance methods)
- Logit residual / probability calibration (Platt 1999; Niculescu-Mizil & Caruana 2005)
- Cost-sensitive learning for rare events (Elkan 2001)
- Consecutive-week anomaly detection in syndromic surveillance
