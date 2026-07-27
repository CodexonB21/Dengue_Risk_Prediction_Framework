"""Central configuration for the dengue prediction framework.

All paths are derived from PROJECT_ROOT so preprocessing/feature-engineering
code works regardless of the working directory it's invoked from. Scripts
should import paths and shared constants from here rather than hardcoding
strings (see `research_context/PIPELINE_ARCHITECTURE_PLAN.md`).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# --- Raw data sources ---
RAW_EPI_PATH = RAW_DIR / "epidemiological" / "dengue_cases_corected.csv"
RAW_WEATHER_DIR = RAW_DIR / "weather"
RAW_POPULATION_PATH = RAW_DIR / "population" / "population_by_district.csv"

# --- Shared layer outputs (module-agnostic; src/preprocessing/shared.py) ---
SHARED_DIR = PROCESSED_DIR / "shared"
SHARED_EPI_WEEK_CALENDAR_PATH = SHARED_DIR / "epi_week_calendar.csv"
SHARED_CLIMATE_WEEKLY_PATH = SHARED_DIR / "climate_weekly.csv"
SHARED_POPULATION_ANNUAL_PATH = SHARED_DIR / "population_annual.csv"
SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH = SHARED_DIR / "epidemiological_weekly.csv"

# --- Module 2 layer outputs ---
MODULE2_PROCESSED_DIR = PROCESSED_DIR / "module2"
MODULE2_WEEKLY_MODELING_TABLE_PATH = MODULE2_PROCESSED_DIR / "weekly_modeling_table.csv"
MODULE2_FEATURES_DIR = FEATURES_DIR / "module2"
MODULE2_STAGE1_FEATURE_TABLE_PATH = MODULE2_FEATURES_DIR / "stage1_feature_table.csv"
MODULE2_MODELS_DIR = MODELS_DIR / "module2"
MODULE2_METRICS_DIR = OUTPUTS_DIR / "metrics" / "module2"
MODULE2_LABEL_BALANCE_AUDIT_PATH = MODULE2_METRICS_DIR / "label_balance_audit.csv"

# --- Module 1 layer outputs ---
MODULE1_PROCESSED_DIR = PROCESSED_DIR / "module1"
MODULE1_WEEKLY_MODELING_TABLE_PATH = MODULE1_PROCESSED_DIR / "weekly_modeling_table.csv"
MODULE1_FEATURES_DIR = FEATURES_DIR / "module1"
MODULE1_STAGE2_FEATURE_TABLE_PATH = MODULE1_FEATURES_DIR / "stage2_feature_table.csv"

# --- Module 1 Stage 1 (SARIMA baseline; src/module1_forecasting/baseline_sarima.py) ---
MODULE1_SARIMA_PREDICTIONS_PATH = MODULE1_PROCESSED_DIR / "sarima_stage1_predictions.csv"
MODULE1_MODELS_DIR = MODELS_DIR / "module1"
MODULE1_SARIMA_CONFIG_PATH = MODULE1_MODELS_DIR / "sarima_selected_configs.csv"
MODULE1_METRICS_DIR = OUTPUTS_DIR / "metrics" / "module1"
MODULE1_SARIMA_METRICS_PATH = MODULE1_METRICS_DIR / "sarima_walk_forward_metrics.csv"
MODULE1_FIGURES_DIR = OUTPUTS_DIR / "figures" / "module1"

# --- Module 1 Stage 2 (XGBoost residual compensation; src/module1_forecasting/compensation_model.py) ---
MODULE1_XGBOOST_PREDICTIONS_PATH = MODULE1_PROCESSED_DIR / "xgboost_stage2_predictions.csv"
MODULE1_XGBOOST_MODELS_DIR = MODULE1_MODELS_DIR / "xgboost_folds"
MODULE1_XGBOOST_FINAL_MODEL_PATH = MODULE1_MODELS_DIR / "xgboost_final_model.json"
MODULE1_XGBOOST_METRICS_PATH = MODULE1_METRICS_DIR / "xgboost_stage2_metrics.csv"
MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH = MODULE1_METRICS_DIR / "xgboost_feature_importance.csv"

# --- Module 1 combined final forecast (Decision 010; src/module1_forecasting/combine.py) ---
MODULE1_FINAL_PREDICTIONS_PATH = MODULE1_PROCESSED_DIR / "final_combined_predictions.csv"
MODULE1_COMBINED_METRICS_PATH = MODULE1_METRICS_DIR / "combined_vs_baseline_metrics.csv"
MODULE1_DM_TEST_PATH = MODULE1_METRICS_DIR / "diebold_mariano_results.csv"

# --- Module 1 forward production forecast (beyond last available data;
# src/module1_forecasting/forecast_future.py) - distinct from the validated
# holdout evaluation above: no ground truth exists yet to score against.
MODULE1_FUTURE_FORECAST_PATH = MODULE1_PROCESSED_DIR / "future_forecast.csv"

# 25 official Sri Lankan districts modeled post Kalmunai -> Ampara merge
# (Decision 012). Kalmunai is a real ~19-year case series with no matching
# Open-Meteo weather station; it is folded into Ampara upstream and is never
# modeled as its own district.
DISTRICTS = [
    "Ampara", "Anuradhapura", "Badulla", "Batticaloa", "Colombo", "Galle",
    "Gampaha", "Hambantota", "Jaffna", "Kalutara", "Kandy", "Kegalle",
    "Kilinochchi", "Kurunegala", "Mannar", "Matale", "Matara", "Monaragala",
    "Mullaitivu", "Nuwara Eliya", "Polonnaruwa", "Puttalam", "Ratnapura",
    "Trincomalee", "Vavuniya",
]  # 25 official districts, post Kalmunai->Ampara merge (Decision 012)

# Sri Lanka monsoon epi-week ranges (FEATURE_ENGINEERING_SPEC.md Feature
# Group 4). Assumes a fixed 52-week epi-year (Decision 007's week-53 merge
# is applied upstream of any code that consumes these).
MONSOON_WEEKS_SW = list(range(20, 39))          # weeks 20-38
MONSOON_WEEKS_NE = list(range(44, 53)) + list(range(1, 9))  # weeks 44-52, 1-8

# Module 2 outbreak label (Decision 019, research_context/RESEARCH_DECISIONS.md).
# Retires the old OUTBREAK_THRESHOLD fixed-count placeholder: the label is now
# a fold-aware epidemic threshold, `mean + EPIDEMIC_THRESHOLD_K * SD`, computed
# per (District, Week) from strictly-prior years only - see
# src/module2_classification/label_definition.py. k=2 was confirmed via
# scripts/data_audit_module2.py (no degenerate per-district outbreak rate at
# k in {1.5, 2.0, 2.5}); flagged as a kickoff default, not a final validated
# choice - see Module 2 Open Question #8 (seasonal-peak-vs-anomaly caveat).
EPIDEMIC_THRESHOLD_K = 2.0
EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS = 3
