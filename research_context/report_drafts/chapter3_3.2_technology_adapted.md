# Chapter 3 — Section 3.2 Technology Adapted

**Source of truth:** `requirements.txt`, `src/dashboard/app.py`, module pipelines, Decisions 021–026  
**Status:** Draft for Word paste  
**Last updated:** 2026-07-30

---

## 3.2 Technology Adapted

This section describes the programming language, development environments, libraries, and collaboration tools used to implement the residual compensation modeling framework. Only technologies that support the current dengue risk prediction pipeline are included. Tools that appeared in earlier planning notes but were not adopted in the final implementation, such as a separate React frontend or Flask/Django API backend, are omitted.

### 3.2.1 Programming Languages

Python was selected as the primary programming language for the project because it provides a mature ecosystem for epidemiological data processing, statistical time-series modelling, machine learning, geospatial analysis, and interactive dashboard development within a single environment. This was important for a three-module residual compensation framework in which forecasting, outbreak classification, and spatial hotspot analysis needed to share common data structures while still allowing module-specific modelling choices.

In practice, Python supported the full research workflow: loading and aligning district-week dengue and climate tables, fitting SARIMA baselines, training residual and classification models, computing spatial statistics, evaluating walk-forward and holdout performance, and serving the early-warning dashboard. The language’s readability also supported collaborative development across Modules 1, 2, and 3, since each module could be maintained as a separate Python package while still consuming shared preprocessing outputs.

**Approx. word count:** 150 words

---

### 3.2.2 Development Environments and Tools

Several development environments were used for complementary stages of the research workflow.

Jupyter Notebooks were used for exploratory data analysis, rapid prototyping of preprocessing and feature ideas, and visual inspection of forecasts, residuals, calibration behaviour, and class balance. The notebook format was particularly useful during early diagnostic work, where iterative plotting of district-level time series and residual patterns helped refine modelling assumptions before those steps were frozen into production scripts.

The main modular implementation was developed in a local integrated development environment, primarily Cursor IDE, with Visual Studio Code used as a compatible alternative where needed. These environments supported structured Python packages under `src/`, scripted pipeline orchestration, debugging of walk-forward validation logic, and integration with Git-based collaboration. This modular script-first approach was preferred over notebook-only development because the residual compensation design required reproducible, leakage-safe stages that could be re-run idempotently for Modules 1 and 2.

Cloud notebook platforms such as Google Colab were not required as a core production environment. The project’s dominant workloads are tabular statistical and tree-based models rather than GPU-intensive deep learning, and the accepted pipelines were executed locally against versioned data artifacts.

**Approx. word count:** 210 words

---

### 3.2.3 Libraries and Frameworks

The residual compensation framework depends on a coordinated set of Python libraries rather than a single modelling package. These libraries support the full analytical chain from district-week data preparation through baseline modelling, residual or probability compensation, spatial hotspot analysis, and early-warning visualisation. They were selected according to their suitability for statistical forecasting, tabular machine learning, geospatial computation, and interactive dashboard delivery within the same research codebase. For clarity, the libraries used in the project are grouped below according to their role in the pipeline.

**Data handling and numerical computing.**  
Pandas and NumPy formed the foundation for data loading, cleaning, temporal alignment, lag construction, anomaly feature generation, and table manipulation across the shared and module-specific preprocessing layers. These libraries were essential for maintaining district-week epidemiological and meteorological series in a consistent tabular form before modelling.

**Statistical time-series modelling.**  
Statsmodels and pmdarima were used for Module 1 Stage 1. SARIMA order search and forecasting relied on pmdarima’s `auto_arima` workflow and statsmodels-compatible seasonal ARIMA fitting, with climate covariates deliberately excluded from Stage 1. SciPy supported supporting numerical and statistical operations used in diagnostics and related computations. STL decomposition was considered as a possible future baseline ablation but was not part of the accepted production Stage 1 stack.

**Machine learning and residual compensation.**  
Scikit-learn provided preprocessing utilities, evaluation metrics, Random Forest classification and regression components, and probability-calibration methods, including the isotonic regression used as Module 2’s official Stage 2 compensator. XGBoost was used as Module 1’s Stage 2 residual compensation model and was also benchmarked within Module 2 Stage 1 model selection. Random Forest, accessed through scikit-learn, is the official Module 2 Stage 1 classifier after the Decision 025 label re-estimation benchmark. LightGBM was not adopted in the final stack. Optuna was used for Module 2 Stage 1 hyperparameter search experiments. The `imbalanced-learn` package was included for a controlled SMOTENC audit, but synthetic oversampling was rejected for production; class reweighting remains the accepted imbalance-handling strategy.

**Spatial analysis and mapping.**  
GeoPandas and Shapely supported district-boundary handling and geospatial operations for Module 3 and dashboard map overlays. Libpysal and esda supported spatial weights construction and Moran’s I assessment of clustering in the spatial baseline. Folium, together with `streamlit-folium`, was used to present interactive map-based hotspot and risk visualisations in the dashboard.

**Visualization and dashboard.**  
Matplotlib and Seaborn were used for research figures such as forecast comparisons, residual diagnostics, and reliability diagrams. Plotly supported interactive charts inside the dashboard. Streamlit was selected as the dashboard framework because it allowed the team to expose module outputs as an early-warning decision-support interface without building a separate web backend. The dashboard consumes versioned CSV and spatial artifacts rather than serving models through a custom Flask/Django API or a React frontend.

**Suggested Table:**  
Table 3.1: Summary of technologies used in the residual compensation framework and their project roles.

| Category | Technology | Primary project role |
|---|---|---|
| Language | Python | End-to-end modelling and dashboard implementation |
| IDE / notebooks | Cursor IDE, Jupyter | Modular pipeline development; exploratory analysis |
| Data / numerics | Pandas, NumPy, SciPy | Cleaning, feature tables, numerical computing |
| Time-series | statsmodels, pmdarima | Module 1 SARIMA baseline |
| Machine learning | scikit-learn, XGBoost, Optuna | Classification, residual compensation, calibration, tuning |
| Spatial | GeoPandas, Shapely, libpysal, esda, Folium | Hotspot baseline, Moran’s I, map visualisation |
| Dashboard | Streamlit, Plotly | Early-warning decision-support interface |
| Collaboration | Git, GitHub | Version control across modules |

**Approx. word count:** 520 words

---

### 3.2.4 Version Control and Collaboration

Git and GitHub were used for version control and team collaboration across the three analytical modules and the dashboard integration layer. Because Module 1, Module 2, and Module 3 evolved in parallel under a shared residual compensation philosophy, version control was necessary to keep preprocessing decisions, experiment scripts, model artifacts, and documentation synchronised. GitHub also supported issue tracking, code review, and reproducible recovery of experiment states associated with the living research documentation in `research_context/`.

**Approx. word count:** 90 words

---

## Combined section word count

**Approx. total for 3.2:** ~970 words

## Notes for Team

- Removed from interim draft as not part of the accepted implementation: Flask/Django, React.js, Dash-as-primary, LightGBM, SARIMAX-as-Stage-1, STL-as-production, Command Center / real-time scenario simulation, Google Colab as required GPU environment.
- Clarified `imbalanced-learn`: audit only; SMOTE rejected (Decision 026).
- Clarified official models: Module 1 Stage 2 = XGBoost; Module 2 Stage 1 = Random Forest; Module 2 Stage 2 = isotonic (scikit-learn).
- Cursor IDE named as primary local IDE, consistent with project documentation; VS Code noted as compatible alternative.
- Table 3.1 is optional but useful; keep prose even if the table is included.
- If supervisor prefers the finer `REPORT_STRUCTURE.md` split (3.2–3.9 separate technology subsections), this 3.2 block can be redistributed later without changing technical claims.
