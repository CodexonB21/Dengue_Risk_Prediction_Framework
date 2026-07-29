"""Load holdout-validated research metrics for the dashboard evidence view."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import OUTPUTS_DIR

PRODUCTION_STACK_PATH = OUTPUTS_DIR / "metrics" / "production_stack_evaluation_summary.csv"
M2_009_BASELINE_PATH = OUTPUTS_DIR / "metrics" / "module2" / "m2_009_m1_alert_baseline.csv"
M2_009_SUMMARY_PATH = OUTPUTS_DIR / "metrics" / "module2" / "m2_009_summary.csv"
M1_DISTRICT_HOLDOUT_PATH = OUTPUTS_DIR / "metrics" / "module1" / "production_stack_m1_district_comparison.csv"
RELIABILITY_HOLDOUT_FIG = OUTPUTS_DIR / "figures" / "module2" / "reliability_diagram_holdout.png"


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_production_stack() -> pd.DataFrame:
    return _read_csv(PRODUCTION_STACK_PATH)


def load_m2_009_baseline() -> pd.DataFrame:
    return _read_csv(M2_009_BASELINE_PATH)


def load_m2_009_summary() -> pd.DataFrame:
    return _read_csv(M2_009_SUMMARY_PATH)


def load_m1_district_holdout() -> pd.DataFrame:
    return _read_csv(M1_DISTRICT_HOLDOUT_PATH)


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


def m2_holdout_summary(stack: pd.DataFrame) -> dict[str, str | float | int]:
    row = stack.loc[stack["module"] == "M2"]
    if row.empty:
        return {}
    r = row.iloc[0]
    return {
        "architecture": r.get("architecture", "isotonic"),
        "alert_threshold": r.get("alert_threshold", 0.14),
        "pr_auc": r.get("post_pr_auc"),
        "alert_recall": r.get("post_alert_recall"),
        "alert_precision": r.get("post_alert_precision"),
    }
