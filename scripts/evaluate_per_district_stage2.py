"""M1-021: per-district Stage 2 models vs. the current pooled model.

Revisits the pooled-model decision (Decision 002/014) with everything else
held fixed - same hyperparameters, same feature set minus the now-redundant
`District` categorical, same walk-forward folds, same evaluation function
(`combine.compute_district_fold_metrics()`, unchanged, reused verbatim) - a
single-variable test, not a broader search.

Handles the central risk explicitly (see `compensation_model.py`'s
`MIN_TRAINABLE_ROWS_PER_DISTRICT`/`MIN_ROWS_FOR_EARLY_STOPPING_PER_DISTRICT`):
per-district training data is ~25x thinner than pooled at the same fold, so
early folds are expected to behave like Stage-1-only (no-op) for many
districts by construction, not a bug.

Same overfitting safeguard and one-time-holdout-check discipline as M1-020
(`scripts/search_stage2_hyperparameters.py`).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS, MODULE1_COMBINED_METRICS_PATH, MODULE1_METRICS_DIR, MODULE1_WEEKLY_MODELING_TABLE_PATH  # noqa: E402
from src.module1_forecasting.combine import compute_district_fold_metrics  # noqa: E402
from src.module1_forecasting.compensation_model import (  # noqa: E402
    N_FOLDS,
    assemble_stage2_table,
    train_and_predict_fold_per_district,
    train_and_predict_holdout_per_district,
)
from src.module1_forecasting.residual_transform import combine_stage2_forecast  # noqa: E402

logger = logging.getLogger(__name__)

OUTPUT_PATH = MODULE1_METRICS_DIR / "stage2_per_district_vs_pooled.csv"


def _finalize(rows: pd.DataFrame) -> pd.DataFrame:
    rows = rows.copy()
    rows["final_prediction"] = combine_stage2_forecast(
        rows["sarima_prediction"].to_numpy(), rows["predicted_residual"].to_numpy(), mode="additive",
    )
    return rows


def run_validation_comparison() -> pd.DataFrame:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    logger.info("Assembling Stage 2 feature table...")
    stage2_df = assemble_stage2_table()

    frames = []
    for fold_num in range(1, N_FOLDS + 1):
        fold_rows = train_and_predict_fold_per_district(stage2_df, fold_num)
        frames.append(fold_rows)
        n_trained = int(fold_rows["stage2_trained"].sum())
        logger.info("Fold %d: %d/%d district-rows had a real (non-no-op) fit.", fold_num, n_trained, len(fold_rows))
    predictions_df = _finalize(pd.concat(frames, ignore_index=True))

    all_rows = []
    for district in DISTRICTS:
        all_rows.extend(compute_district_fold_metrics(district, weekly_df, predictions_df))
    metrics_df = pd.DataFrame(all_rows)
    val_rows = metrics_df[(metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] != 1) & (metrics_df["fold_id"] != "holdout")]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    val_rows.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d validation-fold rows to %s.", len(val_rows), OUTPUT_PATH)
    return val_rows


def apply_safeguard(per_district_val_rows: pd.DataFrame) -> dict:
    baseline = pd.read_csv(MODULE1_COMBINED_METRICS_PATH)
    baseline_val = baseline[
        (baseline["model"] == "stage1_plus_stage2") & (baseline["fold_id"] != "1")
        & (baseline["fold_id"] != "holdout") & (baseline["fold_id"] != "validation_aggregate")
    ]

    per_district_val_rows = per_district_val_rows.copy()
    per_district_val_rows["fold_id"] = per_district_val_rows["fold_id"].astype(str)
    baseline_val = baseline_val.copy()
    baseline_val["fold_id"] = baseline_val["fold_id"].astype(str)

    candidate_agg = float(per_district_val_rows["mase"].median())
    baseline_agg = float(baseline_val["mase"].median())

    baseline_fold_median = baseline_val.groupby("fold_id")["mase"].median()
    candidate_fold_median = per_district_val_rows.groupby("fold_id")["mase"].median()
    n_folds_better = int((candidate_fold_median < baseline_fold_median.reindex(candidate_fold_median.index)).sum())

    baseline_district_median = baseline_val.groupby("District")["mase"].median()
    candidate_district_median = per_district_val_rows.groupby("District")["mase"].median()
    n_districts_better = int((candidate_district_median < baseline_district_median.reindex(candidate_district_median.index)).sum())

    n_folds = candidate_fold_median.shape[0]
    n_districts = candidate_district_median.shape[0]
    qualifies = (
        candidate_agg < baseline_agg
        and n_folds_better > (n_folds - 1) / 2
        and n_districts_better > (n_districts - 1) / 2
    )

    logger.info("=" * 70)
    logger.info("Baseline (pooled) validation-aggregate median MASE: %.4f", baseline_agg)
    logger.info("Per-district candidate validation-aggregate median MASE: %.4f", candidate_agg)
    logger.info("Folds better: %d/%d | Districts better: %d/%d", n_folds_better, n_folds, n_districts_better, n_districts)
    logger.info("Clears overfitting safeguard: %s", qualifies)
    logger.info("=" * 70)
    return {
        "baseline_agg": baseline_agg, "candidate_agg": candidate_agg,
        "n_folds_better": n_folds_better, "n_folds": n_folds,
        "n_districts_better": n_districts_better, "n_districts": n_districts,
        "qualifies": qualifies,
    }


def run_holdout_check() -> float:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    stage2_df = assemble_stage2_table()
    holdout_rows = _finalize(train_and_predict_holdout_per_district(stage2_df))

    all_rows = []
    for district in DISTRICTS:
        all_rows.extend(compute_district_fold_metrics(district, weekly_df, holdout_rows))
    metrics_df = pd.DataFrame(all_rows)
    holdout_metrics = metrics_df[(metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] == "holdout")]
    median_mase = float(holdout_metrics["mase"].median())
    logger.info("Per-district holdout median MASE: %.4f", median_mase)
    return median_mase


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    val_rows = run_validation_comparison()
    result = apply_safeguard(val_rows)
    if result["qualifies"]:
        logger.info("Safeguard cleared - running the one-time holdout check...")
        run_holdout_check()
    else:
        logger.info("Safeguard not cleared - no holdout check performed (per pre-registered rule).")
