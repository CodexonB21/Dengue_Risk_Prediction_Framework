# Chapter 5 — Section 5.4.1 Module 1 Design

**Status:** Paste-ready topic draft  
**Last updated:** 2026-07-30  
**Previous section:** 5.3 Data Architecture and Pipeline Design  
**Next topic:** 5.4.2 Module 2 design (+ Figure 5.4)

---

## 5.4 High-Level Architecture of Individual Modules

Having established the shared data and pipeline boundaries, this section describes the internal design of each analytical module. Each subsection follows the same pattern: purpose and scope, Stage 1 baseline, Stage 2 compensation, and expected outputs.

### 5.4.1 Module 1: Hybrid Time-Series Case Forecasting

The design of Module 1 is organised as a district-level weekly forecasting pipeline with a strict separation between a climate-free temporal baseline and a climate-aware residual compensator. The module estimates expected dengue case magnitude for all 25 administrative districts of Sri Lanka. It does not classify outbreak labels and does not produce spatial hotspot surfaces; those responsibilities belong to Modules 2 and 3. Its role in the overall framework is to provide a quantitative estimate of incidence over short forecasting horizons so that subsequent risk interpretation and alerting can be grounded in a forecast of case burden.

Four design objectives guide the module. First, Stage 1 must capture the regular temporal structure of weekly district case series using an interpretable statistical baseline. Second, climate-driven and nonlinear deviations must remain in the residual, which requires deliberately excluding climate covariates from Stage 1. Third, Stage 2 must learn and correct structured residual error using lagged epidemiological and climate features. Fourth, evaluation must follow temporally valid walk-forward and holdout protocols so that no future information leaks into model selection or residual training.

Figure 5.3 summarises the Module 1 component flow from shared inputs through preprocessing, baseline forecasting, residual extraction, compensation, and final forecast generation.

**[Insert Figure 5.3 here]**

**Figure 5.3:** High-level architecture of Module 1 — Hybrid Time-Series Case Forecasting (SARIMA baseline → residual extraction → XGBoost compensation → final case forecast).

**Shared input layer.** Module 1 consumes the shared epidemiological weekly table and, for Stage 2 only, the shared weekly climate table. Shared cleaning already includes the Kalmunai→Ampara merge so that the forecasting module models exactly the 25 official districts. Shared cleaning does not apply SARIMA-specific calendar constraints; those remain inside Module 1’s own preprocessing step, consistent with Decision 013.

**Module-specific preprocessing.** Two transformations are applied only inside Module 1. In years with 53 Ministry of Health epidemiological weeks, week 53 is merged into week 52 so that every district-year has exactly 52 rows, matching SARIMA’s fixed seasonal period (`m = 52`). Weeks that are missing from the source case data (scrape gaps) are imputed using a seasonal-naive method—the same district and same epidemiological week averaged across other years—and flagged with an `is_imputed` indicator. Imputed weeks remain available for continuity of the time series but are excluded from evaluation metrics and from serving as Stage 2 prediction targets.

**Stage 1 — SARIMA baseline.** A SARIMA model is fitted independently for each district on historical weekly case counts only. Climate covariates are excluded from Stage 1 by design (Decision 001). Keeping Stage 1 climate-free ensures that climate-driven deviations remain in the residual for Stage 2 to learn, rather than being absorbed into the baseline. Where appropriate, a `log1p` transform of case counts is selected on a per-district basis during order search; predictions are inverse-transformed back to the raw case-count scale before residual construction and evaluation. Orders are selected once per district on the pre-holdout history and then held fixed during walk-forward refitting.

**Residual extraction.** For every district-week observation used in residual learning, the residual is defined as the difference between the observed case count and the Stage 1 prediction. Only out-of-sample SARIMA residuals are used for Stage 2 training. In-sample fitted residuals are excluded because they systematically underestimate true baseline error and would inflate the apparent benefit of compensation.

**Stage 2 — XGBoost residual compensation.** An XGBoost regression model is trained to predict the Stage 1 residual. The Stage 2 feature set is organised into groups: lagged case counts, rolling case trend statistics, rate-of-change indicators, lagged rainfall/precipitation (within the biologically relevant lag window), lagged temperature and humidity, climate anomaly features, seasonal cyclic encodings (`sin_week` / `cos_week`), monsoon indicators, the SARIMA prediction itself, and residual lag features. Reporting-delay and nowcasting indicators are included where they help the compensator handle irregular reporting patterns. Stage 2 is designed as one pooled model across districts (with district as a categorical feature) and uses a robust absolute-error objective so that extreme residual outliers in one district cannot dominate training for all districts.

**Output and intended users.** The primary output is a district-week forecast of expected dengue cases, obtained by adding the predicted residual to the SARIMA forecast. These forecasts support early-warning interpretation and may also inform complementary outbreak-risk analysis in Module 2 under the operational forward pathway. Forecast quality is evaluated using time-series metrics under the walk-forward and holdout protocol described above; numeric results are reported in Chapter 7. Intended users are district-level public health analysts and decision-makers who require short-horizon estimates of case burden for planning and situational awareness. The module is positioned as a research decision-support component rather than a clinically certified or fully operational deployment system.

**Approx. word count:** 580 words

**Notes for Team:**
- Do not write SARIMAX for Stage 1; climate enters only in Stage 2.
- Keep numeric MASE/DM results for Chapter 7.
- Confirm figure numbering against the final List of Figures.
- Figure assets: `research_context/report_drafts/diagrams/figure_5_3_module1_architecture.drawio` (+ `.png`).
- Prefer the new 4-column figure over the legacy vertical `figure_5_4_module1_architecture.drawio`.
