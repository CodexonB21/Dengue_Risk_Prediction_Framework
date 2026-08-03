# Chapter 6 — Section 6.4 Module 1 Implementation (+ Figure 6.2)

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 6.3 Shared Preprocessing (+ Figure 6.1)  
**Next topic:** 6.5 Implementation of Module 2 (+ Figure 6.3)  
**Full chapter:** `research_context/report_drafts/chapter6_implementation.md`

---

## 6.4 Implementation of Module 1: Hybrid Time-Series Case Forecasting

Module 1 was implemented as a layered district-week forecasting pipeline: Module 1–specific temporal adjustments on the shared base tables, Stage 1 SARIMA baseline forecasting, Stage 2 feature construction, and pooled XGBoost residual compensation. The implementation follows the accepted residual-compensation principle:

```text
residual = actual_cases − sarima_prediction
final_prediction = sarima_prediction + predicted_residual
```

Figure 6.2 summarises this implementation flow from preprocessing through final forecast combination.

**[Insert Figure 6.2 here]**

**Figure 6.2:** Implementation pipeline of Module 1 — Hybrid Time-Series Case Forecasting (Module 1 preprocessing → SARIMA → residual features → XGBoost → final forecast).

### 6.4.1 Module 1 Preprocessing

Module 1 preprocessing begins from the shared epidemiological and climate tables and applies only those temporal adjustments required by SARIMA and by Stage 2 feature construction. In years containing fifty-three MoH epidemiological weeks (2009, 2016, 2019, and 2021), week 53 was merged into week 52 by summing cases and averaging climate columns. This yields a regular fifty-two-week seasonal period compatible with `sin_week` / `cos_week` encodings and with SARIMA’s fixed seasonal period. Remaining genuine missing weeks were filled by a seasonal-naive rule that replaces an absent district-week with the mean of the same district and week number across other available years. Every filled row was flagged with `is_imputed = True` so that imputed magnitudes could later be excluded from residual targets and from primary accuracy metrics while still contributing lag context for subsequent real weeks.

Climate was then joined on `(District, Year, Week)`, and population was joined annually to support reporting-layer incidence where required. The categorical `weather_code` column remained present in the processed Module 1 table but was excluded at feature selection, consistent with Decision 008. Suspected reporting-anomaly weeks were additionally flagged so that case-derived lag features could mask untrusted values without deleting the underlying reported counts. The resulting weekly modelling table therefore contains a complete district-week panel suitable for Stage 1 fitting and Stage 2 feature derivation without silently treating missing weeks as zero cases.

### 6.4.2 Stage 1: Per-District SARIMA Baseline

Stage 1 fits one SARIMA model per district using weekly `Number_of_Cases` only. Climate covariates are deliberately excluded so that residual compensation remains meaningful and so that Stage 1 does not absorb the climate signal that Stage 2 is intended to learn (Decision 001). Candidate orders and an optional `log1p` transform were explored with constrained `auto_arima` search on pre-holdout history; thereafter, each walk-forward fold refitted a fixed-order model on that fold’s own training window only. Selected configurations were held fixed across folds and the holdout block. Predictions were inverse-transformed to the raw case-count scale before residual construction, and forecasts were clipped at zero to avoid nonsensical negative case counts. Explosive or non-stationary autoregressive roots were guarded against during fitting so that divergent fold forecasts would be recorded as missing rather than allowed to contaminate later residual training. Stage 1 therefore produces out-of-sample `sarima_prediction` values for every validation and holdout district-week that can serve as honest residual targets under Decision 010.

### 6.4.3 Stage 2: XGBoost Residual Compensation

Stage 2 predicts the SARIMA residual rather than re-predicting the raw case count from scratch. Feature groups comprise lagged and rolling case-trend features (lags 1–4, 4-week rolling mean/standard deviation, rate of change); lagged precipitation (`precipitation_sum`, lags 2–8), temperature, and humidity; fold-aware climate anomalies recomputed from each fold’s training window only; seasonal encodings (`sin_week`, `cos_week`) and southwest/northeast monsoon indicators; residual lags constructed by full-calendar reindexing before shifting; reporting-delay state features where adopted; and the SARIMA prediction itself. District is included as a categorical feature because Stage 2 is implemented as a single pooled XGBoost model rather than twenty-five independent district models, giving early folds enough training mass while still allowing district-specific error behaviour.

Training uses the robust objective `reg:absoluteerror` so that rare extreme Stage 1 residuals cannot dominate a pooled squared-error loss and silently corrupt compensation for every other district. Rows flagged as imputed are excluded from residual targets, climate anomalies are never computed from future norms relative to a fold’s cutoff, and residual lags are never allowed to jump across the structural gap between the final validation fold and the holdout block.

### 6.4.4 Training Protocol and Artefacts

Module 1 training follows Decision 009: expanding-window annual walk-forward folds on the pre-holdout history, with the final approximately two years reserved as an untouched holdout block (104 weeks per district under the Module 1 calendar). Within each fold, Stage 1 is refitted on data available up to the fold cutoff, Stage 2 is trained only on prior out-of-sample residuals, and the final forecast is formed by adding the predicted residual to the SARIMA prediction, with non-negative clipping applied to the combined prediction. Metrics are computed after excluding imputed evaluation rows; quantitative accuracy is reserved for Chapter 7.

The pipeline was implemented as an idempotent sequence of scripts rather than as an interactive notebook workflow. Principal artefacts include the Module 1 weekly modelling table, Stage 1 prediction and selected-configuration files, the Stage 2 feature table, fold-wise and final XGBoost model files, combined prediction tables, and metrics and figures under the Module 1 outputs directory. A separate forward-forecast script generates recursive multi-step operational forecasts beyond the last observed case week, and a rolling one-step evaluator provides an operational-deployment analogue; both are kept distinct from the holdout-validated evidence path so that research claims and prototype forward outputs are never conflated. As illustrated in Figure 6.2, Stage 1 remains case-only, while climate and anomaly structure enter only through Stage 2 residual learning.

**Approx. word count:** 880 words

**Suggested Figure:**
Figure 6.2: Module 1 implementation pipeline.  
Asset: `research_context/report_drafts/diagrams/figure_6_2_module1_implementation.png` (adapted from Figure 5.3; Word caption = 6.2).

**Notes for Team:**
- Do not write SARIMAX-with-climate for Stage 1.
- Do not claim rolling case features were SARIMA inputs.
- Keep MASE / DM numbers for Chapter 7.
- Next: **6.5 Module 2 (+ Figure 6.3)**.
