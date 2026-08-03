## 7.3 Module 1: Forecasting Evaluation

### 7.3.1 Experimental setup

Module 1 Stage 1 fits per-district SARIMA models on weekly case counts only. Stage 2 predicts the SARIMA residual with a pooled XGBoost regressor using case-lag, climate-lag and anomaly, seasonal, residual-lag, and—under the current production path—reporting-delay features. Evaluation uses 14 expanding-window walk-forward folds plus a 104-week holdout block per district. The core residual-compensation comparison reported below corresponds to the regenerated pipeline after Stage 1 stationarity safeguards (Decision 017 / experiment M1-003). The current production stack additionally includes reporting-delay features promoted under Decision 030 / M1-006B. Imputed rows are excluded from scoring.

### 7.3.2 Stage 1 vs Stage 1+2 residual compensation

Across all 25 districts, Stage 1+2 improved validation-aggregate MASE for 25/25 districts relative to Stage 1 only. On the untouched holdout block, 23/25 districts improved. The two holdout exceptions were Kilinochchi and Mannar; neither showed a statistically significant worsening under the Diebold–Mariano test. These exceptions are retained in the narrative rather than omitted, because the research claim is directional and material improvement for most districts, not universal perfection.

**Table 7.1: Headline Stage 1 versus Stage 1+2 MASE improvement (Decision 017 / M1-003)**

| Scope | Median MASE improvement (Stage 1 → Stage 1+2) | Districts improved |
|---|---|---|
| Validation aggregate | 43.5% | 25/25 |
| Holdout | 32.7% | 23/25 |

Median absolute holdout MASE moved from approximately 0.622 (Stage 1) to approximately 0.375 (Stage 1+2) in the Decision 017 regenerated comparison. Selected district examples from the same comparison include strong holdout gains for Colombo (0.65 → 0.32), Gampaha (0.74 → 0.35), and Batticaloa (0.59 → 0.25), alongside limited or negative holdout movement for Kilinochchi and Mannar. The median percentage reductions indicate that residual compensation recovers a substantial fraction of error left by the climate-free SARIMA baseline, while the absolute MASE values show that the compensated forecasts also move below the seasonal-naive scale for the typical district.

A full per-district Stage 1 versus Stage 1+2 MASE table may be placed in an appendix if the main chapter needs to remain compact; the source artefact is `outputs/metrics/module1/combined_vs_baseline_metrics.csv`, with narrative confirmation in `module_1_forecasting/MODULE_CONTEXT.md`.

### 7.3.3 Statistical significance

At the pooled validation-and-holdout Diebold–Mariano scope, 14/25 districts showed Stage 2 significantly better than Stage 1 (`p < 0.05`). At the stricter holdout-only scope, 5/25 districts reached significance. No district showed a statistically significant worsening at either scope. This pattern is interpreted honestly: residual compensation is directionally beneficial and often material, but universal statistical significance is not claimed at the per-district holdout sample size of 104 weeks. Diebold–Mariano therefore supports selective confidence rather than a blanket significance claim. The corresponding district-level test results are recorded in `outputs/metrics/module1/diebold_mariano_results.csv`.

### 7.3.4 Production stack refinement (M1-006B)

After promotion of reporting-delay / nowcasting-state features (M1-006B; Decision 030), the default production path achieved a further modest holdout refinement on top of the residual-compensation architecture.

**Table 7.2: Production stack holdout refinement after M1-006B**

| Metric (holdout) | Pre-promotion | Post-promotion (current) |
|---|---|---|
| Median MASE | 0.386 | 0.374 |
| Median sMAPE | 35.0% | 34.2% |
| Districts improved (MASE vs prior stack) | — | 22/25 |

These figures refine the production feature set; they do not replace the Stage 1 versus Stage 1+2 comparison as the primary evidence that compensation itself helps. The production median holdout MASE of 0.374 is therefore best read as the current operating point of an already-validated residual-compensation pipeline.

### 7.3.5 Interpretation and limits

Residual compensation substantially reduces average forecast error relative to SARIMA alone for most districts. Remaining structure in residuals—Ljung–Box still significant for many districts—indicates that Stage 2 reduces error magnitude without fully whitening residuals. Extreme catch-up weeks associated with suspected reporting dynamics remain difficult. Rolling one-step evaluation can improve near-term outbreak-week error relative to a flat multi-step holdout block, but flat holdout MASE remains the primary validated backtest evidence and must not be conflated with operational rolling analogues. Forward forecast files without ground truth are excluded from the skill claims above and must not be used as Figure 7.2 evidence.

As shown in Figure 7.2, selected district trajectories illustrate how Stage 1+2 tracks observed case intensity more closely than Stage 1 alone during the holdout window. Figure 7.3 summarises the district-level holdout MASE comparison that underlies Table 7.1, including the Kilinochchi and Mannar exceptions.

[Insert Figure 7.2 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_2_module1_holdout_forecasts.png`)*

**Figure 7.2: Example actual versus Stage 1 versus Stage 1+2 weekly case forecasts for selected districts (e.g. Colombo and Gampaha holdout windows)**

[Insert Figure 7.3 here]
*(PNG: `research_context/report_drafts/diagrams/figure_7_3_module1_holdout_mase.png`)*

**Figure 7.3: District-level holdout MASE comparison of Stage 1 versus Stage 1+2**

**Approx. word count:** 920 words

**Notes for Team:**
- Standalone: `research_context/report_drafts/chapter7_7.3_module1.md`
- Prefer M1-003 / Decision 017 for the compensation claim; cite M1-006B only as production refinement
- Figures 7.2 and 7.3 generated (2026-07-30) from holdout predictions + `combined_vs_baseline_metrics.csv`
- Do **not** use `future_forecast_*.png` for Figure 7.2 (operational, no ground truth)
- Optional appendix: full 25-district MASE table
- Transition: next topic is **7.4 Module 2** (+ Tables 7.3–7.4, Figure 7.4)
