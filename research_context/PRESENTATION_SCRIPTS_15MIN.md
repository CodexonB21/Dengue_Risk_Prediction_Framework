# FYP Presentation Scripts — 15 Minutes
## A Residual Compensation Modeling Framework for Dengue Risk Prediction

**Team Codexon**

| Member | Index | Module | Speaking time |
|---|---|---|---|
| Bandara H.R.B.G.M. | 214029P | Module 1 + **Project Introduction (recommended)** | 3 min intro + 4 min M1 = **7 min** |
| Nethma L.H.K. | 214140X | Module 2 | **4 min** |
| Karunarathna R.M.D.R.R. | 214099D | Module 3 | **4 min** |

**Total:** 15 minutes (modules & features only — allow Q&A separately if the panel schedules it)

**Speaking rate assumed:** ~140–150 words/minute (practice and trim locally)

---

# PART A — PROJECT INTRODUCTION (3 minutes)
**Recommended presenter:** Bandara (214029P) — opens the deck and hands off to own Module 1 seamlessly  
**Alternative:** Split 1 minute each (Problem → Framework → Modules overview) — trim paragraphs if splitting

**Slides to show:** Title → Team → Aim/Problem → High-level architecture (Figure 5.1 or overview) → Three-module summary

---

### Script — Project Introduction (~430 words ≈ 3:00)

Good morning / afternoon. We are **Team Codexon**, and our project is **A Residual Compensation Modeling Framework for Dengue Risk Prediction**.

Dengue remains a major public health burden in Sri Lanka. Case counts rise with complex seasonal and climate-driven patterns, but much of the response is still reactive — action often starts after incidence has already increased. A core limitation is that decision-makers need **more than one type of risk signal**: they need to know **how many cases** are expected, **whether the current week looks like an outbreak-risk state**, and **where burden is concentrating geographically**. Many existing approaches address only one of these questions, or treat prediction as a single black-box model that leaves systematic error uncorrected.

Our research proposes a **residual compensation framework** at **district-week level** across **25 districts**. The shared idea is simple: a **baseline model** captures the main pattern first; a **second stage** then corrects the structured error the baseline leaves behind. Compensation means different things in each module — case residual correction, probability calibration, or spatial adjustment — but the philosophy is the same.

The framework has **three complementary modules**. **Module 1** forecasts weekly case counts — the magnitude layer. **Module 2** classifies outbreak risk and produces calibrated alerts and risk tiers. **Module 3** detects spatial hotspots and maps where burden concentrates. Outputs are integrated in a **Streamlit early-warning dashboard** for joint interpretation. This is **decision-support research**.

Our objectives align directly with these three modules: hybrid time-series forecasting, hybrid outbreak classification with calibrated alerts, and hybrid spatial hotspot detection. I will now walk through **Module 1 — Hybrid Time-Series Case Forecasting**.

**[Handoff if intro presenter ≠ Bandara:]** I will now hand over to Bandara for Module 1.

---

# PART B — MODULE 1 (4 minutes)
**Presenter:** Bandara H.R.B.G.M. (214029P)  
**Slides:** M1-1 through M1-7 (see `PRESENTATION_MODULE1_COPY_PASTE.md`)

---

### Script — Module 1 (~560 words ≈ 4:00)

**[Slide 1 — Module introduction] (~0:45)**

Module 1 is our **hybrid time-series case forecasting** pipeline. It answers: **how many dengue cases do we expect next week in each district?**

The research gap is that classical time-series models capture temporal trends but still leave structured error from **climate lags, monsoon effects, and recent case dynamics**. Single-stage machine learning often mixes baseline and correction into one opaque model. Our novelty is **two-stage residual compensation**: a **climate-free SARIMA Stage 1**, then a **climate-aware XGBoost Stage 2** trained only on **out-of-sample** residuals.

**[Slide 2 — Two-stage design + Figure 6.2] (~0:45)**

Stage 1 fits **per-district SARIMA** on weekly case counts only. Stage 2 predicts the residual — actual minus SARIMA — using epidemiological lags, climate lags and anomalies, monsoon indicators, and residual-lag features. The final forecast is **SARIMA prediction plus predicted residual**. We use one **pooled XGBoost model** with district as a categorical feature, and we enforce **leakage-safe** training throughout.

**[Slide 3 — Data & protocol] (~0:30)**

Data comes from **Ministry of Health weekly reports** and **Open-Meteo climate**, aligned to a shared epi-week calendar. Evaluation uses **fourteen walk-forward folds** plus an untouched **two-year holdout** per district. Primary metric: **MASE** against a seasonal-naive benchmark.

**[Slide 4 — Stage 1 & 2 features] (~0:40)**

Top Stage 2 drivers include **residual lag one and two** — showing that SARIMA error is autocorrelated and learnable — plus rolling case intensity and rainfall and seasonal features. This confirms Stage 2 is correcting structured baseline error, not replacing the temporal model entirely.

**[Slides 5–6 — Results, Figures 7.2 & 7.3] (~1:15)**

On results: residual compensation improved **validation MASE for all twenty-five districts**, with a **median improvement of about forty-three percent** on validation and **thirty-two percent** on holdout. Median holdout MASE moved from about **0.62 to 0.37**. Figure 7.2 shows **Colombo and Gampaha** holdout trajectories — Stage 1 plus 2 tracks observed cases more closely than SARIMA alone. Figure 7.3 shows **broad district-level improvement** across the country.

**[Slide 7 — Summary] (~0:25)**

Module 1 is the framework’s **magnitude layer**. It feeds the dashboard and supports complementary analysis in Modules 2 and 3. I now hand over to **Nethma** for **Module 2 — Outbreak Risk Classification**.

---

# PART C — MODULE 2 (4 minutes)
**Presenter:** Nethma L.H.K. (214140X)  
**Slides:** M2-1 through M2-7 (see `PRESENTATION_MODULE2_COPY_PASTE.md`)

---

### Script — Module 2 (~560 words ≈ 4:00)

**[Slide 1 — Module introduction] (~0:45)**

Thank you, Bandara. Module 2 is **Hybrid Outbreak Risk Classification**. It answers: **is this district-week in an elevated outbreak-risk state?** — and converts that into **alerts and risk tiers**.

The research gap is that **existing outbreak prediction models estimate probability but do not adjust predictions using climate anomalies or seasonal environmental variations**. Baseline probability scores also tend to be **poorly calibrated** for fixed early-warning cutoffs. Our novelty is a **two-stage hybrid pipeline**: Stage 1 **Random Forest** integrates **climate anomalies, lagged climate, monsoon and seasonal indicators** with epidemiological features; Stage 2 **isotonic regression** compensates probability error — our task-appropriate form of residual compensation for classification.

**[Slide 2 — Design + Figure 6.3] (~0:45)**

Stage 1 outputs **predicted outbreak probability**. Stage 2 produces **calibrated probability**, then we derive an **alert flag** at threshold **zero point one four** and **low, medium, high risk tiers** with high tier from **zero point three five** upward. Labels use a **fold-aware harmonic epidemic threshold** with **k equals three**. Stage 2 trains only on **out-of-sample** Stage 1 probabilities — no leakage.

**[Slide 3 — Label & protocol] (~0:30)**

We evaluate with **thirteen walk-forward folds** and a **two-year holdout**. Stage 1 is scored by **PR-AUC** for rare-event discrimination; Stage 2 by **Brier Skill Score** for calibration quality.

**[Slide 4 — Stage 1 + Table 7.3] (~0:40)**

We benchmarked **Logistic Regression, Random Forest, and XGBoost**. **Random Forest** was selected with median validation PR-AUC **zero point three seven seven**. On holdout: PR-AUC **zero point four two nine**, ROC-AUC **zero point eight eight five**. Leading features are **lagged case anomalies**, consistent with epidemic-threshold labelling.

**[Slide 5 — Stage 2 + Figure 7.4] (~0:50)**

**Isotonic regression** was selected over Platt scaling by validation BSS, with holdout BSS **zero point two three one five**. Figure 7.4 shows **calibrated probabilities track observed outbreak rates** more reliably than raw Stage 1 scores — closer to the reliability diagonal.

**[Slide 6 — Alerts & tiers] (~0:40)**

At alert threshold **zero point one four**, holdout **recall rises from forty-five to sixty percent**, with improved **F2 score**. Risk tiers show **clear separation**: low tiers have low observed outbreak rates; high tiers have much higher rates — on both validation and holdout.

**[Slide 7 — Summary + Table 7.7] (~0:30)**

Module 2 is the **outbreak-alert layer**. Module 2 alerts are **not replaceable** by simply thresholding Module 1 forecasts — holdout PR-AUC for production alerts is **zero point four one two** versus far lower for magnitude-only rules. I hand over to **Karunarathna** for **Module 3 — Spatial Hotspot Detection**.

---

# PART D — MODULE 3 (4 minutes)
**Presenter:** Karunarathna R.M.D.R.R. (214099D)  
**Slides:** M3-1 through M3-7 (see `PRESENTATION_MODULE3_COPY_PASTE.md`)

---

### Script — Module 3 (~560 words ≈ 4:00)

**[Slide 1 — Module introduction] (~0:45)**

Thank you, Nethma. Module 3 is **Hybrid Spatial Hotspot Detection**. It answers: **where is dengue burden concentrating across districts?**

Temporal modules tell us magnitude and outbreak state, but not **geographic concentration**. Raw case maps ignore **neighbour influence and spatial clustering**, and geography-only surfaces miss **demographic and environmental context**. Our novelty extends **residual compensation to the spatial domain**: a **KDE baseline validated with Moran’s I**, then **Random Forest Stage 2 correction** using population and climate covariates — completing the framework’s third axis: **magnitude, outbreak state, and location**.

**[Slide 2 — Design + Figure 6.4] (~0:40)**

Stage 1 builds a **case-weighted Gaussian KDE** surface and validates clustering with **Global Moran’s I**. Stage 2 predicts **spatial residuals** — observed intensity minus current risk — and updates risk iteratively with **shrinkage alpha zero point zero five**. Validation uses **five-fold spatial K-means CV** so whole districts stay together in each fold. **IDW maps are visualisation only** — they do not change model estimates.

**[Slide 3 — Data stack] (~0:30)**

We work at **GADM Level-1 — twenty-five districts**. The master table joins **weekly cases, climate, census population, elevation, and district geometry** from shared project pipelines.

**[Slide 4 — Stage 1 + Table 7.5] (~0:40)**

Aggregated **Global Moran’s I is zero point seven zero two** with **p equals zero point zero zero one** — significant spatial clustering. Peak week **2017 week twenty-nine** and low-burden weeks also show strong clustering, confirming the KDE baseline is spatially meaningful.

**[Slide 5 — Stage 2 features + importance figure] (~0:45)**

Stage 2 is driven mainly by **population density** and **estimated population**, with supporting **temperature and rainfall** terms. So correction reflects **demographic burden and environmental context**, not proximity alone.

**[Slide 6 — Figure 7.5 peak map] (~0:50)**

Figure 7.5 shows the **hybrid risk surface for 2017 week twenty-nine** — the national outbreak peak. Elevated risk concentrates in the **south-western coastal corridor** — **Colombo, Gampaha, Kalutara** — matching known epidemic geography. Risk correlates strongly with observed burden — correlation about **zero point eight two**.

**[Slide 7 — Summary] (~0:30)**

Module 3 delivers **district-level hotspot maps** integrated in the dashboard alongside Modules 1 and 2. Together, the framework provides **three complementary views** of dengue risk for early-warning decision support. Thank you.

---

# TIMING CHEAT SHEET

| Segment | Presenter | Target | Cumulative |
|---|---|---|---|
| Project introduction | Bandara (recommended) | 3:00 | 3:00 |
| Module 1 | Bandara | 4:00 | 7:00 |
| Module 2 | Nethma | 4:00 | 11:00 |
| Module 3 | Karunarathna | 4:00 | 15:00 |

**If running long:** Trim Module 1 results examples first; keep one results figure per module.  
**If running short:** Expand Figure 7.2 walkthrough (M1) or Figure 7.5 geography (M3) by 20–30 seconds.

---

# DELIVERY NOTES (ALL SPEAKERS)

1. **Point at figures** when citing numbers — do not read every decimal off dense tables.
2. **Soft language:** “decision support”, “early warning”, “designed to support” — not “deployed”, “guaranteed”, “clinical”.
3. **Do not volunteer** holdout exceptions, null M3 aggregate-fit, or low M2 precision unless asked.
4. **Handoffs:** Pause, name the next speaker, next speaker says “Thank you, [name]” — keeps timing clean.
5. **Practice with timer** — 15 minutes is strict; modules section is exactly **4 + 4 + 4** if intro stays at 3.

---

# SLIDE-TO-SPEAKER MAP (FULL DECK ORDER)

| Order | Content | Speaker |
|---|---|---|
| 1 | Title / team | Intro speaker |
| 2 | Problem / aim / framework overview | Intro speaker |
| 3 | Figure 5.1 architecture (optional in intro) | Intro speaker |
| 4–10 | Module 1 slides | Bandara |
| 11–17 | Module 2 slides | Nethma |
| 18–24 | Module 3 slides | Karunarathna |
| 25+ | Conclusion / Q&A thank-you (if in deck) | Any / rotate |

Adjust slide numbers to match your merged PowerPoint.

---

**Status:** Script ready (2026-07-31)  
**Files used:** `PRESENTATION_MODULE{1,2,3}_COPY_PASTE.md`, Chapter 1 drafts, presentation-safe policy
