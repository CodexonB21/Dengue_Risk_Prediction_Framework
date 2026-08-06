## 7.4 Module 2: Outbreak Classification Evaluation

**Version note:** this is a v2 revision of `chapter7_7.4_module2.md`, updated after Decision 047/M2-013 (Random Forest hyperparameter tuning, adopted 2026-08-06). The v1 file is retained unchanged for reference; this file supersedes it as the current source for pasting into the report.

### 7.4.1 Experimental setup and outbreak labelling

Module 2 uses fold-aware epidemic-threshold labels under the harmonic seasonal estimator with `k = 3.0` (Decision 025). Evaluation uses 13 walk-forward folds with a four-year minimum training depth, plus a two-year holdout block of 2,600 district-weeks. Under the current label, holdout outbreak prevalence is approximately 1.5% (about 40 positive rows), so holdout metrics carry higher sampling variance than under earlier, superseded label definitions and are not directly comparable to pre–Decision-025 numbers. Stage 2 fold `k` trains only on official Stage 1 out-of-sample probabilities from earlier folds.

### 7.4.2 Stage 1 discrimination

Model-type selection (Random Forest over Logistic Regression and XGBoost, Decision 025) was made first, by median validation PR-AUC across the same 13 folds this section reports throughout.

**Table 7.3: Stage 1 model comparison under the current harmonic label**

| Model | Median validation PR-AUC (13 folds) |
|---|---|
| Logistic Regression | 0.355 |
| XGBoost (tuned params) | 0.382 |
| Random Forest (selected model type) | 0.390 |

Random Forest was subsequently given its own hyperparameter search (Decision 047/M2-013) — a step Decision 025's label re-estimation had not included, since only XGBoost had previously been tuned (Decision 023), for an architecture no longer selected. A 50-trial Optuna search (`class_weight="balanced"` held fixed) found `n_estimators=472, max_depth=16, min_samples_leaf=11, min_samples_split=18, max_features="sqrt"`, raising median validation PR-AUC to **0.395** and, on the untouched holdout block, improving PR-AUC from 0.413 to **0.423**, ROC-AUC from 0.883 to **0.905**, and Brier score from 0.028 to **0.018**. Two related levers tested in the same experiment — `class_weight="balanced_subsample"` and an untuned Gradient Boosting benchmark (listed as a candidate model in earlier project documentation but never previously run) — both underperformed the tuned Random Forest and were not adopted. Pooled modelling continued to outperform per-district modelling on the pre-registered median PR-AUC comparison. Case-anomaly lags dominate feature importance, consistent with a label that encodes recent seasonal exceedance, documented as an expected near-label signal rather than an accidental leakage of current-week cases. The modest PR-AUC gaps among tree models remain less important than the consistent finding that Stage 1 ranks rare outbreak weeks far above chance under a prevalence-sensitive metric.

### 7.4.3 Stage 2 calibration compensation

Stage 1 raw probabilities remain poorly calibrated relative to base-rate forecasts (holdout Brier Skill Score −0.19), motivating Stage 2. Tuning Stage 1's Random Forest changed its probability distribution enough to flip Stage 2's architecture selection.

**Table 7.4: Stage 2 architecture comparison (post-tuning), validation and holdout**

| Architecture | Median validation BSS | Validation PR-AUC | Holdout BSS | Holdout PR-AUC |
|---|---:|---:|---:|---:|
| Stage 1 raw | −0.334 | 0.426 | −0.189 | 0.423 |
| Stacked XGBoost | −0.040 | 0.345 | −0.025 | 0.466 |
| Logit-residual | −0.014 | 0.368 | 0.001 | 0.320 |
| Isotonic | 0.220 | 0.390 | 0.259 | 0.419 |
| **Platt (selected)** | **0.227** | **0.426** | **0.267** | **0.423** |

Platt scaling now beats isotonic regression on median validation Brier Skill Score (0.227 vs. 0.220) and is selected per the same pre-registered rule that previously favoured isotonic — the flip is driven entirely by Stage 1's changed probability distribution after tuning, the same upstream-tuning mechanism that flipped Stage 2 the other way after Decision 023's earlier XGBoost tuning, not a Stage 2 code change. Because Platt scaling is a strictly monotonic transform of Stage 1's probability, holdout PR-AUC and ROC-AUC are identical to Stage 1 raw's own figures (0.423/0.905) — only the calibration (Brier/BSS), not the ranking, changes. Stacked XGBoost reaches the highest holdout PR-AUC (0.466) but a negative BSS on both splits, consistent with earlier findings that its own imbalance weighting reintroduces a probability-scale distortion; it remains unselected because BSS, not PR-AUC, is Stage 2's primary metric. As shown in Figure 7.4, Stage 1 raw probabilities lie systematically off the perfect-calibration diagonal, whereas the now-official Platt-scaled Stage 2 probabilities sit closer to observed outbreak rates on both the validation and holdout panels.

### 7.4.4 Alert thresholds and risk tiers

Validation-selected absolute thresholds, re-selected fresh from the new calibrated-probability distribution, are an alert threshold τ = 0.10 (F2-oriented) and a high-confidence boundary of 0.50 (F0.5-oriented) — both higher than the pre-tuning values (0.14/0.35) would suggest on their own, since threshold selection uses the same validation folds. At τ = 0.10, holdout recall is 62.5%, versus 37.5% under a naive 0.5 cutoff, with precision 34.2% and F2 = 0.536 — a modest but real improvement over the pre-tuning production figures (60.0% recall, 33.8% precision, F2 = 0.519). Observed outbreak rates by risk tier remain ordered and, on holdout, separate more cleanly than before: low 0.6%, medium 20.4%, high 62.5% (previously 0.6%/13.3%/48.8%), though the medium (n = 49) and high (n = 24) holdout groups remain small and their exact percentages should be read with the same sampling-variance caution as before.

### 7.4.5 Rejected ablations

Several alternatives were tested and not adopted for production. SMOTENC oversampling (M2-006) failed to improve holdout PR-AUC despite validation gains. Logit-space residual correction (M2-007A) did not beat Platt/isotonic. A climate-free Stage 1 with climate-stacked Stage 2 (M2-008) was rejected because stacked BSS remained weaker than the production calibrator. Module 1 forecast features in a tree Stage 2 (M2-007D) showed some ranking signal but were not promoted. Following the Random Forest tuning above, three further ablations were tested and also rejected: an ensemble of Stage 1's three benchmarked models, which won on validation but regressed on the untouched holdout block (M2-010); a district-specific, variance-adaptive relabeling rule, which genuinely narrowed cross-district prevalence variation but did not resolve the specific under-flagged case that motivated it (M2-011); and a lagged spatial risk feature drawn from Module 3's hybrid risk map, corrected for an earlier same-week leakage concern but still not beating the current feature set on validation (M2-014). These negatives, alongside the one genuine improvement above, illustrate that Module 2's Stage 2 form is probability calibration refined by careful, individually tested hyperparameter and feature choices, not an assumption that any plausible extension will help.

[Insert Figure 7.4 here]
*(PNG: `outputs/figures/module2/reliability_diagram_{validation,holdout}.png`, regenerated under the current production pipeline — now shows Platt, not isotonic)*

**Figure 7.4: Module 2 reliability diagrams comparing Stage 1 raw probabilities with Platt-scaled Stage 2 calibration (validation and holdout)**

**Approx. word count:** 900 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.4_module2_v2.md` — supersedes `chapter7_7.4_module2.md` (v1 retained, not deleted)
- Figure 7.4 source PNGs were regenerated automatically by the M2-013 pipeline rerun and already show Platt — no separate figure-regeneration step needed, only the caption/description text changed
- Thresholds: τ = 0.10 / high = 0.50 (post–Decision 047), superseding τ = 0.14 / 0.35
- Holdout reliability panel remains sparse (~40 positives) — interpret cautiously in viva, same caveat as before
- Transition: next topic is **7.5 Module 3** (unchanged by this revision)
