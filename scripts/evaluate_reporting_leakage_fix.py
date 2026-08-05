"""M1-019 (Step 1 of the reporting-catch-up-spike scoping plan): does
Decision 030's ~3% median-MASE improvement survive if the reporting-anomaly
mechanism's leakage pathway is closed?

Verified during scoping: `is_reporting_anomaly[T]` (the retrospective flag,
`reporting_anomalies.flag_reporting_anomalies()`) needs `cases[T+1]` to
confirm week *T* was a reporting delay. Every downstream consumer that uses
`is_reporting_anomaly[T-1]` as a feature/mask for predicting row *T*
(`feature_engineering.build_fold_agnostic_features()`'s `cases_lag_1`
nowcast correction and Feature Group 6; `compensation_model.
build_residual_lags()`'s `residual_lag_1/2` masking) therefore has its
value - or, for `reporting_rebound_ratio_lag1`, its very presence/absence -
determined in part by `cases[T]`, the quantity Stage 2's residual target at
row *T* is a function of. This is a narrow (few near-boolean signals, not
the raw value) but real leakage pathway in a feature set already promoted
to production (Decision 028/030).

This script builds a LEAKAGE-CLOSED variant using
`reporting_anomalies.flag_reporting_dip_causal()` (uses only `cases[T-2]`,
`cases[T-1]` - no future data) IN PLACE OF the retrospective flag,
everywhere the retrospective flag currently feeds masking/features, then
re-runs the full Stage 2 training + combine pipeline unchanged and compares
median holdout MASE against the current production numbers.

Nothing here touches the retrospective `is_reporting_anomaly` column itself
or any production artifact - all outputs use the existing
`feature_variant="causal_safe"` suffix mechanism (`module1_stage2_paths`).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_COMBINED_METRICS_PATH,
    MODULE1_FEATURES_DIR,
    MODULE1_PROCESSED_DIR,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.combine import run_combine_pipeline  # noqa: E402
from src.module1_forecasting.compensation_model import run_stage2_pipeline  # noqa: E402
from src.module1_forecasting.feature_engineering import build_module1_feature_table  # noqa: E402
from src.preprocessing.reporting_anomalies import flag_reporting_dip_causal  # noqa: E402

logger = logging.getLogger(__name__)

FEATURE_VARIANT = "causal_safe"
CAUSAL_SAFE_WEEKLY_PATH = MODULE1_PROCESSED_DIR / "weekly_modeling_table_causal_safe.csv"
CAUSAL_SAFE_FEATURE_TABLE_PATH = MODULE1_FEATURES_DIR / "stage2_feature_table_causal_safe.csv"


def build_causal_safe_weekly_table() -> Path:
    """Copy of `weekly_modeling_table.csv` with `is_reporting_anomaly`
    REPLACED (same column name, so no downstream code needs to change) by
    the causal (leakage-free) dip flag. Written to its own path - the real
    table is never touched."""
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    flagged = flag_reporting_dip_causal(weekly_df)
    weekly_df = weekly_df.merge(
        flagged[["District", "Year", "Week", "is_reporting_dip_causal"]],
        on=["District", "Year", "Week"], how="left",
    )
    weekly_df["is_reporting_anomaly"] = weekly_df["is_reporting_dip_causal"].fillna(False)
    weekly_df = weekly_df.drop(columns=["is_reporting_dip_causal"])

    CAUSAL_SAFE_WEEKLY_PATH.parent.mkdir(parents=True, exist_ok=True)
    weekly_df.to_csv(CAUSAL_SAFE_WEEKLY_PATH, index=False)
    logger.info(
        "Wrote causal-safe weekly table (%d rows, %d flagged is_reporting_anomaly, "
        "vs. %d in the real retrospective column) -> %s.",
        len(weekly_df), int(weekly_df["is_reporting_anomaly"].sum()),
        int(pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH)["is_reporting_anomaly"].sum()),
        CAUSAL_SAFE_WEEKLY_PATH,
    )
    return CAUSAL_SAFE_WEEKLY_PATH


def run_evaluation() -> None:
    weekly_path = build_causal_safe_weekly_table()

    logger.info("Building causal-safe Stage 2 feature table...")
    features = build_module1_feature_table(input_path=weekly_path)
    CAUSAL_SAFE_FEATURE_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(CAUSAL_SAFE_FEATURE_TABLE_PATH, index=False)
    logger.info("Wrote %d causal-safe feature rows -> %s.", len(features), CAUSAL_SAFE_FEATURE_TABLE_PATH)

    logger.info("Running Stage 2 (causal-safe)...")
    run_stage2_pipeline(
        feature_variant=FEATURE_VARIANT,
        weekly_table_path=weekly_path,
        feature_table_path=CAUSAL_SAFE_FEATURE_TABLE_PATH,
    )

    logger.info("Running combine (causal-safe)...")
    run_combine_pipeline(feature_variant=FEATURE_VARIANT)

    paths = module1_stage2_paths(feature_variant=FEATURE_VARIANT)
    causal_safe_metrics = pd.read_csv(paths["combined_metrics"])
    production_metrics = pd.read_csv(MODULE1_COMBINED_METRICS_PATH)

    def _median_holdout_mase(df: pd.DataFrame) -> float:
        rows = df.loc[(df["fold_id"] == "holdout") & (df["model"] == "stage1_plus_stage2")]
        return float(rows["mase"].median())

    prod_mase = _median_holdout_mase(production_metrics)
    causal_mase = _median_holdout_mase(causal_safe_metrics)

    logger.info("=" * 70)
    logger.info("Production (current, has the leak) median holdout MASE:   %.4f", prod_mase)
    logger.info("Causal-safe (leakage-closed) median holdout MASE:         %.4f", causal_mase)
    logger.info("Delta: %+.4f (%+.1f%%)", causal_mase - prod_mase, 100 * (causal_mase - prod_mase) / prod_mase)
    logger.info("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_evaluation()
