"""M1-007: residual_lag_3/4 + residual_ewma_4 Stage 2 feature extension.

Phase 2 of the Module 1 remediation plan - targets the finding that 23/25
districts still fail Ljung-Box (lag 26) on `actual - final_prediction` even
after Stage 2 (`combine.py`'s existing diagnostic). `residual_lag_1/2`
already dominate Stage 2's feature importance by a wide margin
(`xgboost_feature_importance.csv`); this ablation asks whether two more
lags plus a smoothed EWMA of the same leakage-safe residual series
(`compensation_model.RESIDUAL_LAG_EXTENSION_COLUMNS`) capture any of the
autocorrelated structure that survives at lag 26.

Runs the full Stage 2 + combine pipeline under
`feature_variant="m1_007_residual_ext"` (writes to `_m1_007_residual_ext`
suffixed artifact paths - the production default paths are never touched by
this script), then compares against the untouched production
`combined_vs_baseline_metrics.csv` on:

1. Ljung-Box (lag 26) pass rate on the 23 currently-failing districts.
2. Median holdout MASE (must not regress vs. the M1-006B production
   baseline).

Both criteria must hold for adoption (Decision 023's holdout-gated pattern:
propose via validation evidence, confirm via holdout, never search against
the holdout). Prints a verdict; does not modify production artifacts or
promote anything automatically.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS, module1_stage2_paths  # noqa: E402
from src.module1_forecasting.combine import run_combine_pipeline  # noqa: E402
from src.module1_forecasting.compensation_model import RESIDUAL_EXT_VARIANT, run_stage2_pipeline  # noqa: E402

logger = logging.getLogger(__name__)

LJUNG_BOX_ALPHA = 0.05


def _validation_aggregate_row(metrics_df: pd.DataFrame, district: str) -> pd.Series:
    mask = (
        (metrics_df["District"] == district)
        & (metrics_df["model"] == "stage1_plus_stage2")
        & (metrics_df["fold_id"] == "validation_aggregate")
    )
    return metrics_df.loc[mask].iloc[0]


def _holdout_row(metrics_df: pd.DataFrame, district: str) -> pd.Series:
    mask = (
        (metrics_df["District"] == district)
        & (metrics_df["model"] == "stage1_plus_stage2")
        & (metrics_df["fold_id"] == "holdout")
    )
    return metrics_df.loc[mask].iloc[0]


def run_ablation(districts: list[str] = DISTRICTS) -> pd.DataFrame:
    logger.info("Running Stage 2 (feature_variant=%s)...", RESIDUAL_EXT_VARIANT)
    run_stage2_pipeline(feature_variant=RESIDUAL_EXT_VARIANT)
    logger.info("Running combine (feature_variant=%s)...", RESIDUAL_EXT_VARIANT)
    run_combine_pipeline(feature_variant=RESIDUAL_EXT_VARIANT)

    baseline_paths = module1_stage2_paths()
    variant_paths = module1_stage2_paths(feature_variant=RESIDUAL_EXT_VARIANT)
    baseline_metrics = pd.read_csv(baseline_paths["combined_metrics"])
    variant_metrics = pd.read_csv(variant_paths["combined_metrics"])

    rows = []
    for district in districts:
        base_val = _validation_aggregate_row(baseline_metrics, district)
        var_val = _validation_aggregate_row(variant_metrics, district)
        base_hold = _holdout_row(baseline_metrics, district)
        var_hold = _holdout_row(variant_metrics, district)
        rows.append({
            "District": district,
            "baseline_ljung_box_p26": base_val["ljung_box_pvalue_lag26"],
            "variant_ljung_box_p26": var_val["ljung_box_pvalue_lag26"],
            "baseline_fails_lb26": bool(base_val["ljung_box_pvalue_lag26"] < LJUNG_BOX_ALPHA),
            "variant_fails_lb26": bool(var_val["ljung_box_pvalue_lag26"] < LJUNG_BOX_ALPHA),
            "baseline_holdout_mase": base_hold["mase"],
            "variant_holdout_mase": var_hold["mase"],
            "baseline_validation_mase": base_val["mase"],
            "variant_validation_mase": var_val["mase"],
        })
    comparison = pd.DataFrame(rows)

    n_baseline_fail = int(comparison["baseline_fails_lb26"].sum())
    n_variant_fail = int(comparison["variant_fails_lb26"].sum())
    n_newly_passing = int((comparison["baseline_fails_lb26"] & ~comparison["variant_fails_lb26"]).sum())
    n_newly_failing = int((~comparison["baseline_fails_lb26"] & comparison["variant_fails_lb26"]).sum())
    median_holdout_baseline = comparison["baseline_holdout_mase"].median()
    median_holdout_variant = comparison["variant_holdout_mase"].median()

    ljung_box_improved = n_variant_fail < n_baseline_fail
    holdout_not_regressed = median_holdout_variant <= median_holdout_baseline

    logger.info(
        "Ljung-Box (lag 26) failing districts: baseline %d/25 -> variant %d/25 "
        "(%d newly passing, %d newly failing).",
        n_baseline_fail, n_variant_fail, n_newly_passing, n_newly_failing,
    )
    logger.info(
        "Median holdout MASE: baseline %.3f -> variant %.3f (%s).",
        median_holdout_baseline, median_holdout_variant,
        "not regressed" if holdout_not_regressed else "REGRESSED",
    )
    verdict = "ADOPT" if (ljung_box_improved and holdout_not_regressed) else "REJECT"
    logger.info(
        "Adoption criterion (Ljung-Box pass rate improves AND holdout MASE does not regress): %s",
        verdict,
    )

    out_path = variant_paths["combined_metrics"].parent / "m1_007_residual_ext_vs_baseline.csv"
    comparison.to_csv(out_path, index=False)
    logger.info("Wrote per-district comparison to %s.", out_path)
    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_ablation()
