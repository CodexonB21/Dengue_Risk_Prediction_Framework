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
RAW_SPATIAL_DIR = RAW_DIR / "spatial"
GADM_LEVEL1_SHAPEFILE_PATH = RAW_SPATIAL_DIR / "gadm41_LKA_1.shp"

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

# --- Module 3 layer outputs ---
MODULE3_PROCESSED_DIR = PROCESSED_DIR / "module3"
MODULE3_MASTER_TABLE_PATH = MODULE3_PROCESSED_DIR / "master_table.csv"
MODULE3_FEATURES_DIR = FEATURES_DIR / "module3"
MODULE3_BASELINE_RISK_PATH = MODULE3_FEATURES_DIR / "baseline_risk.csv"
MODULE3_METRICS_DIR = OUTPUTS_DIR / "metrics" / "module3"
MODULE3_MORANS_I_METRICS_PATH = MODULE3_METRICS_DIR / "morans_i_validation.csv"
MODULE3_STAGE2_FEATURE_TABLE_PATH = MODULE3_FEATURES_DIR / "stage2_feature_table.csv"
MODULE3_MODELS_DIR = MODELS_DIR / "module3"
MODULE3_RF_FOLDS_DIR = MODULE3_MODELS_DIR / "rf_folds"
MODULE3_RF_FINAL_MODEL_PATH = MODULE3_MODELS_DIR / "rf_final_model.joblib"
MODULE3_RF_METRICS_PATH = MODULE3_METRICS_DIR / "rf_stage2_metrics.csv"
MODULE3_RF_FEATURE_IMPORTANCE_PATH = MODULE3_METRICS_DIR / "rf_feature_importance.csv"
MODULE3_SPATIAL_CV_FOLDS_PATH = MODULE3_METRICS_DIR / "spatial_cv_folds.csv"
MODULE3_CONVERGENCE_LOG_PATH = MODULE3_METRICS_DIR / "iterative_convergence_log.csv"
MODULE3_HYBRID_RISK_MAP_PATH = MODULE3_FEATURES_DIR / "hybrid_risk_map.csv"
MODULE3_FIGURES_DIR = OUTPUTS_DIR / "figures" / "module3"
MODULE3_CONVERGENCE_PLOT_PATH = MODULE3_FIGURES_DIR / "convergence_plot.png"
MODULE3_FEATURE_IMPORTANCE_PLOT_PATH = MODULE3_FIGURES_DIR / "feature_importance.png"
MODULE3_RESULTS_SUMMARY_PATH = MODULE3_METRICS_DIR / "results_summary.txt"
MODULE3_STAGE_COMPARISON_PATH = MODULE3_METRICS_DIR / "stage1_vs_stage2_comparison.csv"
MODULE3_RISK_SURFACE_PLOT_PATH = MODULE3_FIGURES_DIR / "risk_surface_peak_week.png"
MODULE3_MAHALANOBIS_STATS_PATH = MODULE3_MODELS_DIR / "mahalanobis_stats.joblib"
MODULE3_FUTURE_HOTSPOT_FORECAST_PATH = MODULE3_PROCESSED_DIR / "future_hotspot_forecast.csv"
MODULE3_ALPHA_SWEEP_METRICS_PATH = MODULE3_METRICS_DIR / "alpha_sweep_accuracy.csv"
MODULE3_POPULATION_DENSITY_PDP_PLOT_PATH = MODULE3_FIGURES_DIR / "population_density_pdp.png"

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
M1_STAGE2_RESIDUAL_MODE = "additive"  # "additive" (M1-005 baseline) | "log" (M1-006A)

MODULE1_XGBOOST_PREDICTIONS_PATH = MODULE1_PROCESSED_DIR / "xgboost_stage2_predictions.csv"
MODULE1_XGBOOST_MODELS_DIR = MODULE1_MODELS_DIR / "xgboost_folds"
MODULE1_XGBOOST_FINAL_MODEL_PATH = MODULE1_MODELS_DIR / "xgboost_final_model.json"
MODULE1_XGBOOST_METRICS_PATH = MODULE1_METRICS_DIR / "xgboost_stage2_metrics.csv"
MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH = MODULE1_METRICS_DIR / "xgboost_feature_importance.csv"

# --- Module 1 combined final forecast (Decision 010; src/module1_forecasting/combine.py) ---
MODULE1_FINAL_PREDICTIONS_PATH = MODULE1_PROCESSED_DIR / "final_combined_predictions.csv"
MODULE1_COMBINED_METRICS_PATH = MODULE1_METRICS_DIR / "combined_vs_baseline_metrics.csv"
MODULE1_DM_TEST_PATH = MODULE1_METRICS_DIR / "diebold_mariano_results.csv"


def module1_stage2_paths(
    residual_mode: str | None = None,
    feature_variant: str | None = None,
) -> dict[str, Path]:
    """Return Stage 2 / combine artifact paths for residual mode + feature variant.

    Production additive baseline uses default paths. Ablations write to
    ``_*`` suffix paths so M1-005 artifacts are preserved.
    """
    mode = residual_mode or M1_STAGE2_RESIDUAL_MODE
    suffix_parts: list[str] = []
    if feature_variant:
        suffix_parts.append(feature_variant)
    if mode != "additive":
        suffix_parts.append(f"m1_006_{mode}")
    if not suffix_parts:
        return {
            "xgboost_predictions": MODULE1_XGBOOST_PREDICTIONS_PATH,
            "xgboost_models_dir": MODULE1_XGBOOST_MODELS_DIR,
            "xgboost_final_model": MODULE1_XGBOOST_FINAL_MODEL_PATH,
            "xgboost_metrics": MODULE1_XGBOOST_METRICS_PATH,
            "xgboost_feature_importance": MODULE1_XGBOOST_FEATURE_IMPORTANCE_PATH,
            "final_predictions": MODULE1_FINAL_PREDICTIONS_PATH,
            "combined_metrics": MODULE1_COMBINED_METRICS_PATH,
            "dm_test": MODULE1_DM_TEST_PATH,
        }
    suffix = "_".join(suffix_parts)
    return {
        "xgboost_predictions": MODULE1_PROCESSED_DIR / f"xgboost_stage2_predictions_{suffix}.csv",
        "xgboost_models_dir": MODULE1_MODELS_DIR / f"xgboost_folds_{suffix}",
        "xgboost_final_model": MODULE1_MODELS_DIR / f"xgboost_final_model_{suffix}.json",
        "xgboost_metrics": MODULE1_METRICS_DIR / f"xgboost_stage2_metrics_{suffix}.csv",
        "xgboost_feature_importance": MODULE1_METRICS_DIR / f"xgboost_feature_importance_{suffix}.csv",
        "final_predictions": MODULE1_PROCESSED_DIR / f"final_combined_predictions_{suffix}.csv",
        "combined_metrics": MODULE1_METRICS_DIR / f"combined_vs_baseline_metrics_{suffix}.csv",
        "dm_test": MODULE1_METRICS_DIR / f"diebold_mariano_results_{suffix}.csv",
    }

# --- Module 1 forward production forecast (beyond last available data;
# src/module1_forecasting/forecast_future.py) - distinct from the validated
# holdout evaluation above: no ground truth exists yet to score against.
MODULE1_FUTURE_FORECAST_PATH = MODULE1_PROCESSED_DIR / "future_forecast.csv"

# Operational rolling 1-step-ahead evaluation (distinct from the 104-week
# one-shot holdout forecast in baseline_sarima.forecast_holdout).
MODULE1_ROLLING_ONE_STEP_PATH = MODULE1_PROCESSED_DIR / "rolling_one_step_predictions.csv"
MODULE1_ROLLING_ONE_STEP_METRICS_PATH = MODULE1_METRICS_DIR / "rolling_one_step_metrics.csv"

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

# Module 2 outbreak label (Decision 019, research_context/RESEARCH_DECISIONS.md;
# mean/SD ESTIMATOR superseded by Decision 025). Retires the old
# OUTBREAK_THRESHOLD fixed-count placeholder: the label is a threshold,
# `mean + EPIDEMIC_THRESHOLD_K * SD`, applied per (District, Week) using only
# strictly-prior years - see src/module2_classification/labels.py. The
# ORIGINAL (Decision 019) mean/SD estimator computed an exact per-(District,
# Week) sample mean/SD, k=2 chosen via scripts/data_audit_module2.py. That
# exact-week estimator was found (Decision 025, Open Question #8) to be too
# noisy from small per-week sample sizes - pooled "outbreak" prevalence was
# 18-25% of weeks, well above WHO/CDC's typical single-digit-percent epidemic
# alert rate. Decision 025 replaces the mean/SD estimator with a per-district
# harmonic regression (EPIDEMIC_THRESHOLD_N_HARMONICS harmonics of week-of-year,
# refit expanding per year on strictly-prior real data) - historical_mean is
# the fitted seasonal curve, historical_sd is the fit's residual standard
# error. k was re-audited for this new estimator (scripts/
# audit_label_stabilization.py) rather than assumed to carry over unchanged,
# since the SD quantity's meaning changed - k=3.0 chosen to bring pooled
# prevalence to 8.6% (vs. k=2.0's 12.3%), closer to the WHO/CDC aspiration
# cited in Open Question #8, with no degenerate district at either k.
EPIDEMIC_THRESHOLD_K = 3.0
EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS = 3
EPIDEMIC_THRESHOLD_N_HARMONICS = 1

# Module 2 Stage 1 baseline classifier (Decision 021,
# research_context/RESEARCH_DECISIONS.md). Module-2-specific override of
# src/module1_forecasting/validation.py's DEFAULT_MIN_TRAIN_YEARS=3, which was
# tuned for SARIMA's seasonal-cycle needs, not for this label's own
# 3-strictly-prior-years history requirement (EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS
# above). The two 3-year windows overlap exactly, so at the SARIMA-tuned
# default, fold 1's ENTIRE training window has zero rows with a defined label,
# for every district simultaneously (a calendar-driven effect that pooling
# across districts cannot rescue). min_train_years=4 guarantees fold 1's
# training window contains at least one year of genuinely trainable rows.
# Verified empirically: 13 walk-forward folds result (vs Module 1's 14).
MODULE2_MIN_TRAIN_YEARS = 4

# --- Module 2 Stage 1 (baseline classifier; src/module2_classification/baseline_classifier.py) ---
MODULE2_BASELINE_PREDICTIONS_PATH = MODULE2_PROCESSED_DIR / "baseline_classifier_predictions.csv"
MODULE2_BASELINE_METRICS_PATH = MODULE2_METRICS_DIR / "baseline_classifier_metrics.csv"
MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH = MODULE2_METRICS_DIR / "baseline_classifier_feature_importance.csv"
MODULE2_POOLED_VS_DISTRICT_PATH = MODULE2_METRICS_DIR / "pooled_vs_per_district_comparison.csv"
MODULE2_BASELINE_MODELS_DIR = MODULE2_MODELS_DIR / "baseline_classifier"
MODULE2_BASELINE_FINAL_MODEL_PATH = MODULE2_BASELINE_MODELS_DIR / "final_production_model"

# --- Module 2 Stage 2 (probability/classification-error compensation;
# src/module2_classification/compensation_model.py; Decision 022) ---
MODULE2_STAGE2_PREDICTIONS_PATH = MODULE2_PROCESSED_DIR / "stage2_compensated_predictions.csv"
MODULE2_STAGE2_METRICS_PATH = MODULE2_METRICS_DIR / "stage2_compensation_metrics.csv"
MODULE2_STAGE2_POOLED_VS_DISTRICT_PATH = MODULE2_METRICS_DIR / "stage2_pooled_vs_per_district_comparison.csv"
MODULE2_STAGE2_MODELS_DIR = MODULE2_MODELS_DIR / "stage2_compensation"
MODULE2_STAGE2_FINAL_MODEL_PATH = MODULE2_STAGE2_MODELS_DIR / "final_production_model"
MODULE2_FIGURES_DIR = OUTPUTS_DIR / "figures" / "module2"

# --- Module 2 risk-tier thresholds (alert threshold + low/medium/high tiers;
# src/module2_classification/risk_thresholds.py; Decision 024) ---
MODULE2_RISK_TIER_PREDICTIONS_PATH = MODULE2_PROCESSED_DIR / "stage2_risk_tier_predictions.csv"
MODULE2_RISK_THRESHOLD_SCAN_PATH = MODULE2_METRICS_DIR / "risk_threshold_scan.csv"
MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH = MODULE2_METRICS_DIR / "risk_threshold_holdout_comparison.csv"

# --- Module 2 live/production scoring (genuinely new incoming weeks, for
# dashboard consumption; src/module2_classification/live_scoring.py) ---
MODULE2_LIVE_RISK_PREDICTIONS_PATH = MODULE2_PROCESSED_DIR / "live_risk_predictions.csv"

# --- Module 2 forward operational risk (beyond last case week; M1-fed case
# lags; src/module2_classification/forecast_future_risk.py) ---
MODULE2_FUTURE_RISK_PREDICTIONS_PATH = MODULE2_PROCESSED_DIR / "future_risk_predictions.csv"


def module2_stage1_paths(feature_variant: str | None = None) -> dict[str, Path]:
    """Return Stage 1 artifact paths; ablations use a ``_<variant>`` suffix."""
    if not feature_variant:
        return {
            "predictions": MODULE2_BASELINE_PREDICTIONS_PATH,
            "metrics": MODULE2_BASELINE_METRICS_PATH,
            "importance": MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH,
            "pooled_vs_district": MODULE2_POOLED_VS_DISTRICT_PATH,
            "models_dir": MODULE2_BASELINE_MODELS_DIR,
            "final_model": MODULE2_BASELINE_FINAL_MODEL_PATH,
        }
    suffix = feature_variant
    models_dir = MODULE2_MODELS_DIR / f"baseline_classifier_{suffix}"
    return {
        "predictions": MODULE2_PROCESSED_DIR / f"baseline_classifier_predictions_{suffix}.csv",
        "metrics": MODULE2_METRICS_DIR / f"baseline_classifier_metrics_{suffix}.csv",
        "importance": MODULE2_METRICS_DIR / f"baseline_classifier_feature_importance_{suffix}.csv",
        "pooled_vs_district": MODULE2_METRICS_DIR / f"pooled_vs_per_district_comparison_{suffix}.csv",
        "models_dir": models_dir,
        "final_model": models_dir / "final_production_model",
    }


def module2_stage2_paths(feature_variant: str | None = None) -> dict[str, Path]:
    """Return Stage 2 artifact paths; ablations use a ``_<variant>`` suffix."""
    if not feature_variant:
        return {
            "predictions": MODULE2_STAGE2_PREDICTIONS_PATH,
            "metrics": MODULE2_STAGE2_METRICS_PATH,
            "pooled_vs_district": MODULE2_STAGE2_POOLED_VS_DISTRICT_PATH,
        }
    suffix = feature_variant
    return {
        "predictions": MODULE2_PROCESSED_DIR / f"stage2_compensated_predictions_{suffix}.csv",
        "metrics": MODULE2_METRICS_DIR / f"stage2_compensation_metrics_{suffix}.csv",
        "pooled_vs_district": MODULE2_METRICS_DIR / f"stage2_pooled_vs_per_district_comparison_{suffix}.csv",
    }

# Shared forward horizon for Module 1 case forecast and Module 2 forward risk.
FORECAST_HORIZON_WEEKS = 8

# --- Dashboard outputs ---
DASHBOARD_REFRESH_MANIFEST_PATH = OUTPUTS_DIR / "metrics" / "dashboard_refresh_manifest.csv"
