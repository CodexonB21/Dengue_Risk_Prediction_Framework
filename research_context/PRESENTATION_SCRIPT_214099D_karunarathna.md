# Speaker Script — Karunarathna R.M.D.R.R. (214099D)
## Module 3 — Hybrid Spatial Hotspot Detection = **4 minutes**

**Project:** A Residual Compensation Modeling Framework for Dengue Risk Prediction  
**Print note:** One page — you close the 15-minute segment.

---

### YOUR SLIDES (in order)

| # | Slide | Figure |
|---|---|---|
| 1 | M3-1 Module intro | — |
| 2 | M3-2 Two-stage design | **Fig 6.4** |
| 3 | M3-3 Data stack | table |
| 4 | M3-4 KDE + Moran's I | Table 7.5 |
| 5 | M3-5 Stage 2 features | **feature_importance.png** |
| 6 | M3-6 Peak risk map | **Fig 7.5** |
| 7 | M3-7 Summary | — |

**Key numbers:** Moran's I **0.702** (p=0.001) · pop_density top feature · corr(Risk,Cases) **~0.82** · 2017 Wk29 peak map

---

## MODULE 3 SCRIPT (~4:00)

**OPENING:** *Thank you, Nethma.*

**[M3-1 · 0:45]** Module 3: **Hybrid Spatial Hotspot Detection** — *Where is burden concentrating?*  
**Gap:** M1/M2 are temporal; no **geographic concentration** view. Raw maps ignore **spatial clustering** and **demographic/environmental context**.  
**Novelty:** **Residual compensation in space** — **KDE + Moran's I** baseline, **RF Stage 2** with population/climate — third axis: **magnitude, outbreak, location**.

**[M3-2 + Fig 6.4 · 0:40]** Stage 1: **case-weighted KDE** + **Moran's I**. Stage 2: **spatial residual** (actual − risk), iterative update **α=0.05**. **5-fold spatial CV** (whole districts held out). **IDW = visualisation only**.

**[M3-3 · 0:30]** **GADM L1 — 25 districts**. Master table: **cases, climate, population, elevation, geometry**.

**[M3-4 + Table 7.5 · 0:40]** Aggregated **Moran's I = 0.702**, **p = 0.001** — significant clustering. Peak **2017 Wk29** and low-burden weeks also significant — KDE baseline is spatially valid.

**[M3-5 + importance fig · 0:45]** Stage 2 led by **population density (~41%)** and **population (~18%)**, plus **temperature/rainfall**. Correction = **demographic + environmental**, not distance alone.

**[M3-6 + Fig 7.5 · 0:50]** **Hero slide.** Fig 7.5: **2017 Wk29** peak — risk in **SW corridor** (**Colombo, Gampaha, Kalutara**). Matches known **2017 epidemic** geography. **corr ≈ 0.82** with observed burden.

**[M3-7 · 0:30]** Module 3 = **spatial layer**; maps in dashboard with M1 & M2. Together: **how many · outbreak risk · where**.  
**CLOSING:** *Thank you — that completes our presentation.*

---

### REMINDERS
- **Lead with the map** on slide 6 — strongest visual  
- Don’t claim **sub-district** targeting or **Stage 2 beats Stage 1 on MAE**  
- Don’t show **2021 NE-monsoon** non-significant week  
- Pause 1 beat before “Thank you” for panel

---
