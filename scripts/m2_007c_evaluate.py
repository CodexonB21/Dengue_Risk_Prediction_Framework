"""Evaluate M2-007C ramp alert rule vs single-threshold baseline (no retrain)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_METRICS_DIR,
    MODULE2_STAGE1_FEATURE_TABLE_PATH,
    MODULE2_STAGE2_PREDICTIONS_PATH,
)
from src.module2_classification.alert_rules import (  # noqa: E402
    _metric_row,
    apply_ramp_alert_rule,
    attach_case_lags,
    grid_search_ramp_rule,
    select_ramp_parameters,
)
from src.module2_classification.risk_thresholds import (  # noqa: E402
    _official_architecture,
    scan_alert_thresholds,
    select_thresholds,
    selection_population,
)

logger = logging.getLogger(__name__)

BASELINE_RECALL_AT_014 = 0.60
BASELINE_PRECISION_AT_014 = 0.34


def run_m2_007c_evaluation() -> pd.DataFrame:
    predictions_df = pd.read_csv(MODULE2_STAGE2_PREDICTIONS_PATH)
    official_architecture = _official_architecture(predictions_df)
    enriched = attach_case_lags(predictions_df, MODULE2_STAGE1_FEATURE_TABLE_PATH)

    population = selection_population(enriched, official_architecture)
    scan_df = scan_alert_thresholds(population)
    alert_threshold, _high_threshold = select_thresholds(scan_df)
    logger.info("Base alert threshold tau=%.3f (F2-optimal).", alert_threshold)

    ramp_scan = grid_search_ramp_rule(population, tau=alert_threshold)
    tau_ramp, rho = select_ramp_parameters(ramp_scan)
    logger.info("Selected ramp rule: tau_ramp=%.3f, rho=%.2f (validation F2-max).", tau_ramp, rho)

    out_dir = MODULE2_METRICS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ramp_scan_path = out_dir / "m2_007_c_ramp_grid_search.csv"
    ramp_scan.to_csv(ramp_scan_path, index=False)

    holdout = enriched[
        (enriched["architecture"] == official_architecture) & (enriched["split"] == "holdout")
    ]
    y_true = holdout["label"].to_numpy(dtype=float)
    prob = holdout["calibrated_probability"].to_numpy(dtype=float)
    lag1 = holdout["cases_lag_1"].to_numpy(dtype=float)
    lag2 = holdout["cases_lag_2"].to_numpy(dtype=float)
    mask = ~np.isnan(y_true)

    baseline_flags = prob >= alert_threshold
    ramp_flags = apply_ramp_alert_rule(
        prob, lag1, lag2, tau=alert_threshold, tau_ramp=tau_ramp, rho=rho,
    )

    rows = [
        _metric_row(y_true, baseline_flags, tau=alert_threshold, tau_ramp=None, rho=None, rule_name="single_threshold", mask=mask),
        _metric_row(y_true, ramp_flags, tau=alert_threshold, tau_ramp=tau_ramp, rho=rho, rule_name="ramp_rule_m2_007c", mask=mask),
    ]
    # Fixed 0.14 comparison point from M2-006 baseline reporting
    if abs(alert_threshold - 0.14) > 1e-6:
        flags_014 = prob >= 0.14
        rows.append(_metric_row(y_true, flags_014, tau=0.14, tau_ramp=None, rho=None, rule_name="fixed_0.14", mask=mask))

    holdout_df = pd.DataFrame(rows)
    holdout_path = out_dir / "m2_007_c_holdout_comparison.csv"
    holdout_df.to_csv(holdout_path, index=False)

    ramp_row = holdout_df[holdout_df["rule"] == "ramp_rule_m2_007c"].iloc[0]
    baseline_row = holdout_df[holdout_df["rule"] == "single_threshold"].iloc[0]
    accept = (
        ramp_row["recall"] >= 0.65 and ramp_row["precision"] >= BASELINE_PRECISION_AT_014
    ) or (ramp_row["f2"] - baseline_row["f2"] >= 0.05)

    summary = pd.DataFrame([{
        "variant": "m2_007_c",
        "tau": alert_threshold,
        "tau_ramp": tau_ramp,
        "rho": rho,
        "holdout_recall_baseline": baseline_row["recall"],
        "holdout_precision_baseline": baseline_row["precision"],
        "holdout_f2_baseline": baseline_row["f2"],
        "holdout_recall_ramp": ramp_row["recall"],
        "holdout_precision_ramp": ramp_row["precision"],
        "holdout_f2_ramp": ramp_row["f2"],
        "accept_criterion": accept,
    }])
    summary_path = out_dir / "m2_007_c_summary.csv"
    summary.to_csv(summary_path, index=False)

    print("=== M2-007C ramp alert rule (holdout) ===")
    print(holdout_df.to_string(index=False))
    print(f"\nSummary accept={accept}")
    print(f"Wrote grid search -> {ramp_scan_path}")
    print(f"Wrote holdout comparison -> {holdout_path}")
    return holdout_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_m2_007c_evaluation()
