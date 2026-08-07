# Speaker Script — Nethma L.H.K. (214140X)
## Module 2 — Hybrid Outbreak Risk Classification = **4 minutes**

**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Print note:** One page — start when Bandara hands over.

---

### YOUR SLIDES (in order)

| # | Slide | Figure |
|---|---|---|
| 1 | M2-1 Module intro | — |
| 2 | M2-2 Two-stage design | **Fig 6.3** |
| 3 | M2-3 Label & protocol | — |
| 4 | M2-4 Stage 1 RF | Table 7.3 |
| 5 | M2-5 Isotonic calibration | **Fig 7.4** |
| 6 | M2-6 Alerts & tiers | tables |
| 7 | M2-7 Summary | Table 7.7 |

**Key numbers:** RF PR-AUC 0.377 (val) / 0.429 (holdout) · BSS 0.2315 · Alert τ=0.14 · Recall 45%→60%

---

## MODULE 2 SCRIPT (~4:00)

**OPENING:** *Thank you, Bandara.*

**[M2-1 · 0:45]** Module 2: **Hybrid Outbreak Risk Classification** — *Is this an outbreak-risk week?* → **alerts & tiers**.  
**Gap:** Existing models estimate probability but **do not adjust using climate anomalies or seasonal environmental variations** [1]. Raw scores aren’t **decision-ready** for fixed cutoffs.  
**Novelty:** Stage 1 **Random Forest** with **climate anomalies, lags, monsoon/season**; Stage 2 **isotonic calibration** = our residual compensation for classification.

**[M2-2 + Fig 6.3 · 0:45]** Stage 1 → **outbreak probability**. Stage 2 → **calibrated probability** → **alert** (τ **0.14**) and **low/medium/high tiers** (high ≥ **0.35**). **Harmonic epidemic label, k=3**. Stage 2 uses **out-of-sample** Stage 1 probs only.

**[M2-3 · 0:30]** **13 walk-forward folds** + **2-year holdout**. Stage 1: **PR-AUC**. Stage 2: **Brier Skill Score**.

**[M2-4 + Table 7.3 · 0:40]** Benchmarked LR, RF, XGBoost — **Random Forest selected** (val PR-AUC **0.377**). Holdout: PR-AUC **0.429**, ROC-AUC **0.885**. Top features: **case_anomaly_lags**.

**[M2-5 + Fig 7.4 · 0:50]** **Isotonic** selected (holdout BSS **0.2315**). Fig 7.4: calibrated probs **closer to reliability diagonal** than raw Stage 1.

**[M2-6 · 0:40]** Alert τ **0.14**: recall **45% → 60%**, better **F2**. Tiers: **low / medium / high** — outbreak rates increase monotonically (e.g. high tier **~49–71%** on holdout/val).

**[M2-7 · 0:30]** Module 2 = **outbreak-alert layer**. Not replaceable by thresholding M1 forecasts (M2 PR-AUC **0.412** vs **0.063–0.28** for M1 rules).  
**HANDOFF:** *I hand over to **Karunarathna** for **Module 3 — Spatial Hotspot Detection**.*

---

### REMINDERS
- Use **isotonic** Fig 7.4 only (not old Platt PNGs)  
- Don’t quote **precision** unless asked  
- Don’t say “Stage 1 was miscalibrated” — say “Stage 2 calibrates”  
- Replace [1] with your citation if panel asks

---
