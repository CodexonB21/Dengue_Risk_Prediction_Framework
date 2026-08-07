# Chapter 5 — Section 5.4.2 Module 2 Design

**Status:** Paste-ready topic draft
**Last updated:** 2026-08-06 (v2 — Stage 2 architecture updated after Decision 047/M2-013)
**Previous section:** 5.4.1 Module 1 design (+ Figure 5.3)
**Next topic:** 5.4.3 Module 3 design (+ Figure 5.5)
**Supersedes:** `chapter5_5.4.2_module2.md` (v1 retained unchanged, not deleted)

---

### 5.4.2 Module 2: Hybrid Outbreak Risk Classification

The design of Module 2 complements Module 1 by estimating outbreak risk rather than case magnitude. It operates at the same district-week resolution across all 25 administrative districts and reuses the shared epidemiological and climate base tables, but applies Module 2–specific labelling, preprocessing, and a different interpretation of residual compensation. Whereas Module 1 corrects an additive case-count residual, Module 2 compensates systematic miscalibration in predicted outbreak probability. The module does not forecast weekly case totals and does not produce spatial hotspot surfaces; those responsibilities remain with Modules 1 and 3.

Four design objectives guide the module. First, outbreak labels must be defined in a district- and week-aware manner without leaking future history into the threshold. Second, Stage 1 must produce a usable baseline outbreak probability from epidemiological and climate context. Third, Stage 2 must compensate systematic probability error through a calibrated mapping rather than a literal residual regression on a binary outcome. Fourth, calibrated probabilities must be convertible into interpretable early-warning outputs under temporally valid walk-forward and holdout evaluation.

Figure 5.4 summarises the Module 2 component flow from shared inputs through preprocessing, labelling, baseline classification, probability compensation, and decision outputs.

**[Insert Figure 5.4 here]**

**Figure 5.4:** High-level architecture of Module 2 — Hybrid Outbreak Risk Classification (Random Forest baseline → probability compensation via Platt scaling → alert / risk-tier outputs).

**Shared input layer.** Module 2 consumes the shared epidemiological weekly table and the shared weekly climate table. Shared cleaning already includes the Kalmunai→Ampara merge so that classification is performed on the same 25-district geography used by Module 1. Shared cleaning does not impose Module 1's SARIMA calendar constraints; Module 2's own preprocessing and labelling choices are applied independently under Decision 013.

**Module-specific preprocessing.** Two decisions distinguish Module 2 from Module 1. Week 53 is retained as its own epidemiological week because merging week 53 into week 52 would sum two real weeks before the epidemic threshold is computed, risking a spurious outbreak label and contaminating week-52 historical statistics across years. Missing scrape-gap weeks are still filled with a seasonal-naive imputation and flagged with `is_imputed`, but imputed case values are masked to missing before derivation of case-based features so that fabricated counts cannot enter lag, rolling, or label inputs for neighbouring real weeks.

**Fold-aware epidemic-threshold labelling.** Outbreak status is defined by a statistical epidemic threshold rather than a fixed case-count cutoff. For each district and epidemiological week, a label is positive when observed cases exceed a historical mean plus a tuned multiple of historical dispersion, with both moments estimated from strictly prior years only. The production design uses a harmonic seasonal estimator for these historical moments and a tuned multiplier `k`. Weeks with insufficient prior history receive an undefined label and are excluded from training and scoring rather than forced to zero.

**Stage 1 — Random Forest baseline classifier.** Stage 1 is a pooled binary classifier with district as a categorical feature. The accepted Stage 1 model is Random Forest, selected after comparison with Logistic Regression and XGBoost under walk-forward validation on the current label definition (Decision 025), and subsequently given its own hyperparameter search (Decision 047) after remaining on hand-picked defaults through that model-type selection. Unlike Module 1 Stage 1, Module 2 Stage 1 includes climate features—lagged and current-week precipitation, temperature, and humidity, together with fold-aware climate anomalies—because the task is direct risk discrimination rather than isolation of a climate-free temporal baseline. Class imbalance is handled by class reweighting in the production design; synthetic oversampling (SMOTE-family methods) and a per-bootstrap reweighting variant were both audited and rejected (Decisions 026 and 047). The Stage 1 output is a predicted outbreak probability for each district-week.

**Stage 2 — probability compensation via Platt scaling.** Stage 2 receives the Stage 1 predicted probability and applies a calibration mapping as the official probability-compensation layer, selected after benchmarking against isotonic regression and a stacked contextual correction model. In architectural terms:

```text
calibrated_probability = g(predicted_probability)
```

where `g(·)` denotes the fitted calibration mapping — currently Platt scaling (a logistic regression fit on the log-odds of the Stage 1 probability), selected over isotonic regression after Stage 1's own hyperparameter tuning changed its output probability distribution enough to flip which calibration method wins. This formulation deliberately avoids treating a binary outbreak label as if it admitted a Module 1–style additive residual regression. Secondary decision-support outputs are then derived using fixed absolute probability thresholds: a binary `alert_flag` and a three-level `risk_tier` (low / medium / high). Exact threshold values are reported with evaluation results in Chapter 7.

**Output, validation, and intended users.** Primary outputs are the calibrated probability and the derived alert/risk-tier signals. Module 2 uses expanding-window walk-forward validation with a module-specific minimum training-history setting that ensures early folds contain enough defined labels, followed by an untouched holdout block. Discrimination (notably PR-AUC) and calibration (notably Brier Skill Score) are both first-class design concerns. Intended users are district-level public health analysts who need interpretable early-warning signals complementary to case-magnitude forecasts. The module is positioned as a research decision-support component rather than a clinically certified deployment system.

Table 5.2 summarises the design contrast with Module 1.

**[Insert Table 5.2 here]**

**Table 5.2:** Design contrast between Module 1 and Module 2 residual-compensation architectures.

| Design aspect | Module 1 | Module 2 |
|---|---|---|
| Prediction target | Weekly case count | Outbreak risk (binary label → probability) |
| Stage 1 model | Per-district SARIMA | Pooled Random Forest classifier (tuned) |
| Climate in Stage 1 | Excluded | Included |
| Week-53 policy | Merge into week 52 | Keep unmerged |
| Stage 2 target | Case residual | Probability calibration |
| Stage 2 model | XGBoost regressor | Platt scaling (logistic regression on the log-odds) |
| Final decision output | `final_prediction` (cases) | `calibrated_probability`, `alert_flag`, `risk_tier` |

As shown in Table 5.2, Modules 1 and 2 share a residual-compensation philosophy while differing in stage semantics, climate placement, and calendar handling. This deliberate divergence is part of the framework design: each module's second stage corrects the error type that remains after its own baseline.

**Approx. word count:** 650 words

**Notes for Team:**
- Stage 1 official model = **Random Forest** (Decision 025), tuned (Decision 047) — not the pre-Decision-025 XGBoost selection, and not the pre-Decision-047 hand-picked hyperparameters.
- Stage 2 = **Platt-scaling calibration** (Decision 047 flipped this from isotonic — Stage 1's tuning changed its own probability distribution, not a Stage 2 code change), not climate-anomaly residual ML.
- Do not paste numeric alert/tier thresholds into Chapter 5 design text; keep them for Chapter 7 (post-Decision-047: alert 0.100, high 0.500).
- Figure assets: `research_context/report_drafts/diagrams/figure_5_4_module2_architecture.drawio` (+ `.png`) — caption text updated above; the diagram itself may still need its "isotonic" label swapped for "Platt scaling" if drawn explicitly.
