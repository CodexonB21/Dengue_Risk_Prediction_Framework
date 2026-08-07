# Presentation Scripts — Intro Slides (Before Module 1)

**Team Codexon** · Per-slide scripts · **Recommended presenter:** Bandara (214029P)  
Use after title/team slides, before Module 1.

**Total:** ~2:15–2:45 (architecture gets slightly more time)

---

## Slide 1 — Introduction (~20 sec)

Dengue is a major burden in Sri Lanka, driven by climate and seasonality. Public-health response is still largely reactive. Many models treat risk as one task and leave baseline error uncorrected. We propose a **Residual Compensation Modeling Framework** with three modules: case forecasting, outbreak-risk classification, and spatial hotspot detection.

**~40 words**

---

## Slide 2 — Background of the Study (~20 sec)

Transmission in Sri Lanka is linked to rainfall, temperature, humidity, and monsoon patterns. Surveillance already reports cases at **district–week** level. Yet many models rely on cases alone or a single-stage method, so baseline forecasts still carry structured residual error and rarely become usable early-warning tools.

**~45 words**

---

## Slide 3 — Problem in Brief (~25 sec)

The core problem is **reactive management** without an integrated early-warning picture. Decision-makers need case magnitude, outbreak state, and spatial concentration together. Key gaps are isolated tasks, uncorrected baseline residuals, underused climate signals, and weak **district-week** preparedness.

**~40 words**

---

## Slide 4 — Aim of the Project (~20 sec)

Our aim is to develop a **Hybrid Error Compensation Modeling Framework** for dengue risk prediction. It improves weekly case forecasting, outbreak-risk classification, and spatial hotspot detection by correcting baseline-model error through task-specific residual, probability, or spatial compensation at **district–week** level.

**~45 words**

---

## Slide 5 — Research Objectives (~30 sec)

Objective one: residual compensation forecasting with **SARIMA** and **XGBoost** for weekly district cases. Objective two: hybrid outbreak classification with probability calibration, alert flags, and risk tiers. Objective three: spatial hotspot detection using **KDE**, **Moran's I**, and environmental–demographic residual correction.

**~45 words**

---

## Slide 6 — Proposed Solution — Modules (~25 sec)

**Module 1** forecasts weekly cases using a climate-free SARIMA baseline and XGBoost residual compensation. **Module 2** estimates district-week outbreak probability and improves reliability through calibration. **Module 3** detects spatial hotspots using a KDE and Moran's I baseline with demographic and environmental adjustment.

**~45 words**

---

## Slide 7 — High Level Architecture (~50 sec)

This diagram shows the full pipeline. **Epidemiology, climate, and spatial data** are cleaned, aligned, and normalised into shared features. Three parallel modules then run: **SARIMA to XGBoost** for case forecasting, **Random Forest to isotonic calibration** for outbreak risk and tiers, and **KDE plus Moran's I to spatial residual adjustment** for hotspot mapping. All outputs feed a **Streamlit early-warning dashboard** with forecast charts, risk alerts, and hotspot maps — giving decision-makers one integrated view rather than three separate models.

**~85 words**

---

## Handoff to Module 1

*“I will now present Module 1 — Hybrid Time-Series Case Forecasting.”*

---

## Slide-to-time summary

| Slide | Topic | Time |
|---|---|---|
| 1 | Introduction | ~0:20 |
| 2 | Background | ~0:20 |
| 3 | Problem in Brief | ~0:25 |
| 4 | Aim | ~0:20 |
| 5 | Research Objectives | ~0:30 |
| 6 | Proposed Solution — Modules | ~0:25 |
| 7 | High Level Architecture | ~0:50 |
| **Total** | | **~2:30** |

---

**Notes:**
- Match slide wording: “Hybrid Error Compensation” on Aim slide; “Residual Compensation” elsewhere is fine in speech
- Do not over-explain bullet points — point at slide and move on
- Architecture slide: trace left → centre → right once
