"""Single source of truth for all dashboard data loading.

Every CSV/shapefile read in the dashboard goes through `_cached_csv()` (or
`load_district_geometry()` for the one shapefile), both `@st.cache_data`,
keyed on each file's own mtime rather than wall-clock time - a real pipeline
rerun invalidates the cache correctly, but switching between pages never
re-parses a file that hasn't changed. Consolidates what used to be split
between `app.py`'s own `load_csv`/`_load` and `evidence_data.py`'s uncached
`_read_csv` (evidence_data.py is retired; these names are kept identical to
minimize call-site churn in `pages.py`).
"""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
import streamlit as st

from src.config import (
    MODULE1_NOWCAST_ACCURACY_PATH,
    MODULE1_NOWCAST_LOG_PATH,
    MODULE1_NOWCAST_PATH,
    MODULE2_RISK_LOG_PATH,
    MODULE2_RISK_PROSPECTIVE_ACCURACY_PATH,
    MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH,
    MODULE2_STAGE2_METRICS_PATH,
    MODULE3_CONVERGENCE_LOG_PATH,
    MODULE3_FUTURE_HOTSPOT_FORECAST_PATH,
    MODULE3_MORANS_I_METRICS_PATH,
    MODULE3_PERSISTENCE_BASELINE_PATH,
    MODULE3_RF_FEATURE_IMPORTANCE_PATH,
    MODULE3_STAGE_COMPARISON_PATH,
    GADM_LEVEL1_SHAPEFILE_PATH,
    OUTPUTS_DIR,
)
from src.module2_classification.scoring_utils import (
    load_production_thresholds,
    official_stage2_architecture,
)
from src.module2_classification.uncertainty_bands import OUTPUT_PATH as MODULE2_UNCERTAINTY_BANDS_PATH
from src.module3_spatial.kde_baseline import GADM_NAME_FIXES

PRODUCTION_STACK_PATH = OUTPUTS_DIR / "metrics" / "production_stack_evaluation_summary.csv"
M2_009_BASELINE_PATH = OUTPUTS_DIR / "metrics" / "module2" / "m2_009_m1_alert_baseline.csv"
M2_009_SUMMARY_PATH = OUTPUTS_DIR / "metrics" / "module2" / "m2_009_summary.csv"
M1_DISTRICT_HOLDOUT_PATH = OUTPUTS_DIR / "metrics" / "module1" / "production_stack_m1_district_comparison.csv"
RELIABILITY_HOLDOUT_FIG = OUTPUTS_DIR / "figures" / "module2" / "reliability_diagram_holdout.png"


def _file_mtime(path: Path) -> float | None:
    return path.stat().st_mtime if path.exists() else None


@st.cache_data(show_spinner=False)
def _cached_csv(path_str: str, mtime: float | None) -> pd.DataFrame:
    _ = mtime  # part of the cache key only - forces a reload when the file's mtime changes
    path = Path(path_str)
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    for col in ("Week_Start_Date", "Week_End_Date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def load_csv(path: Path) -> pd.DataFrame:
    """Public entry point for any dashboard CSV read - callers pass a `Path`;
    mtime-based cache invalidation happens transparently."""
    return _cached_csv(str(path), _file_mtime(path))


@st.cache_data(show_spinner=False)
def load_district_geometry() -> gpd.GeoDataFrame:
    """District polygons in native EPSG:4326 (lat/lon) - NOT the UTM-reprojected
    version kde_baseline.py's load_district_boundaries() returns, which is in
    meters and wrong for Plotly's choropleth (expects geographic coordinates).
    """
    if not GADM_LEVEL1_SHAPEFILE_PATH.exists():
        return gpd.GeoDataFrame()
    gdf = gpd.read_file(GADM_LEVEL1_SHAPEFILE_PATH)
    gdf["District"] = gdf["NAME_1"].replace(GADM_NAME_FIXES)
    return gdf[["District", "geometry"]]


def load_production_stack() -> pd.DataFrame:
    return load_csv(PRODUCTION_STACK_PATH)


def load_m2_009_baseline() -> pd.DataFrame:
    return load_csv(M2_009_BASELINE_PATH)


def load_m2_009_summary() -> pd.DataFrame:
    return load_csv(M2_009_SUMMARY_PATH)


def load_m1_district_holdout() -> pd.DataFrame:
    return load_csv(M1_DISTRICT_HOLDOUT_PATH)


def m1_holdout_summary(stack: pd.DataFrame) -> dict[str, str | float | int]:
    row = stack.loc[stack["module"] == "M1"]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "median_mase_sarima": r.get("pre_median_mase"),
        "median_mase_hybrid": r.get("post_median_mase"),
        "median_smape_sarima": r.get("pre_median_smape"),
        "median_smape_hybrid": r.get("post_median_smape"),
        "districts_improved_mase": int(r["districts_improved_mase"]) if pd.notna(r.get("districts_improved_mase")) else "—",
        "n_districts": int(r["n_districts"]) if pd.notna(r.get("n_districts")) else 25,
    }


def m2_holdout_summary(stack: pd.DataFrame | None = None) -> dict[str, str | float | int]:
    """Current Module 2 holdout evidence, read live from the same sources the
    production scoring pipeline itself uses (`scoring_utils.py`) - NEVER from
    the frozen `production_stack_evaluation_summary.csv` snapshot (dated
    2026-07-29), which hardcodes `architecture="isotonic"`/`alert_threshold=0.14`
    and predates Decision 047/M2-013 (Random Forest retuning flipped Stage 2
    to Platt scaling and moved thresholds to 0.10/0.50). The `stack` parameter
    is accepted-but-unused for call-site backward compatibility.
    """
    _ = stack
    if not MODULE2_STAGE2_METRICS_PATH.exists():
        return {}
    architecture = official_stage2_architecture()
    metrics = load_csv(MODULE2_STAGE2_METRICS_PATH)
    holdout_row = metrics.loc[(metrics["architecture"] == architecture) & (metrics["split"] == "holdout")]
    if holdout_row.empty:
        return {}
    r = holdout_row.iloc[0]

    alert_threshold, _high_threshold = load_production_thresholds()
    alert_recall, alert_precision = None, None
    if MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH.exists():
        thresh_cmp = load_csv(MODULE2_RISK_THRESHOLD_HOLDOUT_COMPARISON_PATH)
        match = thresh_cmp.loc[(thresh_cmp["threshold"] - alert_threshold).abs() < 1e-6]
        if not match.empty:
            alert_recall = float(match.iloc[0]["recall"])
            alert_precision = float(match.iloc[0]["precision"])

    return {
        "architecture": architecture,
        "alert_threshold": round(alert_threshold, 3),
        "pr_auc": float(r["pr_auc"]),
        "roc_auc": float(r["roc_auc"]),
        "brier_skill_score": float(r["brier_skill_score"]),
        "alert_recall": alert_recall,
        "alert_precision": alert_precision,
    }


def load_m3_morans_i() -> pd.DataFrame:
    return load_csv(MODULE3_MORANS_I_METRICS_PATH)


def load_m3_convergence_log() -> pd.DataFrame:
    return load_csv(MODULE3_CONVERGENCE_LOG_PATH)


def load_m3_feature_importance() -> pd.DataFrame:
    return load_csv(MODULE3_RF_FEATURE_IMPORTANCE_PATH)


def load_m3_stage_comparison() -> pd.DataFrame:
    return load_csv(MODULE3_STAGE_COMPARISON_PATH)


def load_m3_persistence_baseline() -> pd.DataFrame:
    return load_csv(MODULE3_PERSISTENCE_BASELINE_PATH)


def m3_morans_i_summary(morans_df: pd.DataFrame) -> dict[str, float | bool]:
    if morans_df.empty:
        return {}
    row = morans_df.loc[morans_df["check"] == "aggregated"]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {"I": float(r["I"]), "p_sim": float(r["p_sim"]), "significant": bool(r["significant"])}


def m3_convergence_summary(log_df: pd.DataFrame) -> dict[str, float | int | bool]:
    if log_df.empty:
        return {}
    r = log_df.iloc[-1]
    return {
        "n_iterations": int(r["iteration"]),
        "converged": bool(r["stopped"]),
        "max_delta": float(r["max_delta"]),
        "epsilon": float(r["epsilon"]),
    }


# --- Previously-unwired operational/prospective files (Phase 4) ---------------

def load_m1_nowcast() -> pd.DataFrame:
    """Module 1's genuine single-week-ahead prediction (vintage-ensembled
    SARIMA + Stage 2), distinct from the 8-week `future_forecast.csv` already
    used elsewhere in the dashboard - this is the specific horizon=1 output
    Decision 040/M1-016 promoted to production."""
    return load_csv(MODULE1_NOWCAST_PATH)


def load_m3_hotspot_forecast() -> pd.DataFrame:
    """Module 3's genuine next-week spatial forecast (Decision 031/M3-007,
    relative-residual RF as of Decision 051/M3-015) - the spatial-axis
    analogue of `load_m1_nowcast()` above, named the same way for
    consistency across the three modules' "next week" panels."""
    return load_csv(MODULE3_FUTURE_HOTSPOT_FORECAST_PATH)


def load_m1_nowcast_log() -> pd.DataFrame:
    return load_csv(MODULE1_NOWCAST_LOG_PATH)


def load_m1_nowcast_accuracy() -> pd.DataFrame:
    """Rows appear here ONLY once resolved against real data (Decision 041/
    M1-017) - an empty result means no logged nowcast week has happened yet,
    not that the tracker is broken."""
    return load_csv(MODULE1_NOWCAST_ACCURACY_PATH)


def load_m2_risk_log() -> pd.DataFrame:
    return load_csv(MODULE2_RISK_LOG_PATH)


def load_m2_risk_prospective_accuracy() -> pd.DataFrame:
    """Rows appear here ONLY once resolved against a real recomputed label
    (Decision 048/M2-015) - same "empty is honest, not broken" semantics as
    `load_m1_nowcast_accuracy()`."""
    return load_csv(MODULE2_RISK_PROSPECTIVE_ACCURACY_PATH)


def load_m2_uncertainty_bands() -> pd.DataFrame:
    """Per-row Venn-Abers uncertainty interval `[venn_abers_p0, venn_abers_p1]`
    around Stage 2's calibrated probability (M2-012) - computed over
    validation/holdout folds only (validated tier), not forward weeks."""
    return load_csv(MODULE2_UNCERTAINTY_BANDS_PATH)
