"""M1-020: walk-forward-validated XGBoost hyperparameter search for Stage 2.

`compensation_model.XGB_BASE_PARAMS` has been fixed since the project's
earliest implementation - `max_depth=3, learning_rate=0.05, subsample=0.8,
colsample_bytree=0.8, reg_lambda=1.0, min_child_weight=5` - never tuned via
any validation process. This script runs a randomized search over those six
hyperparameters, scoring every candidate against the SAME walk-forward
folds (2-14) production selection already uses, via `combine.
compute_district_fold_metrics()` (unchanged, reused verbatim) - so a
candidate's score is directly comparable to the published
`combined_vs_baseline_metrics.csv` numbers, not a bespoke metric.

The holdout block is never touched during search - only a candidate that
clears the overfitting safeguard below gets a single, final holdout check.

Overfitting safeguard: a candidate only counts as a real improvement if it
beats the baseline's median MASE AND improves in a majority of the 13
scored folds AND a majority of the 25 districts - not just a lower
aggregate number, which could be one or two folds' worth of noise (mirrors
Decision 037's shrinkage-search caution).
"""

from __future__ import annotations

import logging
import random
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS, MODULE1_METRICS_DIR, MODULE1_WEEKLY_MODELING_TABLE_PATH  # noqa: E402
from src.module1_forecasting.combine import compute_district_fold_metrics  # noqa: E402
from src.module1_forecasting.compensation_model import (  # noqa: E402
    N_FOLDS,
    XGB_BASE_PARAMS,
    assemble_stage2_table,
    train_and_predict_fold,
    train_and_predict_holdout,
)
from src.module1_forecasting.residual_transform import combine_stage2_forecast  # noqa: E402

logger = logging.getLogger(__name__)

OUTPUT_PATH = MODULE1_METRICS_DIR / "stage2_hyperparameter_search.csv"
N_CANDIDATES = 40
SEED = 42

SEARCH_SPACE = {
    "max_depth": [2, 3, 4, 5, 6],
    "learning_rate": [0.02, 0.03, 0.05, 0.08, 0.12, 0.2],
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "reg_lambda": [0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
    "min_child_weight": [1, 3, 5, 10, 15, 20],
}


def sample_candidates(n: int, seed: int = SEED) -> list[dict]:
    """Candidate 0 is always the current production defaults - every other
    candidate is an independently-drawn random point, deduplicated."""
    rng = random.Random(seed)
    candidates = [{k: XGB_BASE_PARAMS[k] for k in SEARCH_SPACE}]
    seen = {tuple(candidates[0].values())}
    while len(candidates) < n:
        cand = {k: rng.choice(v) for k, v in SEARCH_SPACE.items()}
        key = tuple(cand.values())
        if key in seen:
            continue
        seen.add(key)
        candidates.append(cand)
    return candidates


def score_candidate(stage2_df: pd.DataFrame, weekly_df: pd.DataFrame, xgb_params: dict) -> dict:
    """Run folds 2-14 with `xgb_params`, score via
    `compute_district_fold_metrics()` exactly as production does. Returns
    per-fold and per-district MASE for the overfitting safeguard, plus the
    aggregate median."""
    frames = []
    for fold_num in range(1, N_FOLDS + 1):
        predicted, trained, _ = train_and_predict_fold(stage2_df, fold_num, xgb_params=xgb_params)
        target_rows = stage2_df.loc[stage2_df["fold_id_numeric"] == fold_num].copy()
        target_rows["predicted_residual"] = predicted
        target_rows["final_prediction"] = combine_stage2_forecast(
            target_rows["sarima_prediction"].to_numpy(), predicted, mode="additive",
        )
        frames.append(target_rows)
    predictions_df = pd.concat(frames, ignore_index=True)

    all_rows = []
    for district in DISTRICTS:
        all_rows.extend(compute_district_fold_metrics(district, weekly_df, predictions_df))
    metrics_df = pd.DataFrame(all_rows)

    val_rows = metrics_df[
        (metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] != 1)
    ]
    per_fold_median = val_rows.groupby("fold_id")["mase"].median()
    per_district_median = val_rows.groupby("District")["mase"].median()

    return {
        "aggregate_median_mase": float(val_rows["mase"].median()),
        "per_fold_median": per_fold_median,
        "per_district_median": per_district_median,
    }


def run_search(n_candidates: int = N_CANDIDATES) -> pd.DataFrame:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    logger.info("Assembling Stage 2 feature table (once, reused across all candidates)...")
    stage2_df = assemble_stage2_table()

    candidates = sample_candidates(n_candidates)
    logger.info("Scoring %d candidates (candidate 0 = current production defaults)...", len(candidates))

    results = []
    baseline_fold_medians = None
    baseline_district_medians = None
    t0 = time.time()
    for i, cand in enumerate(candidates):
        t_start = time.time()
        scored = score_candidate(stage2_df, weekly_df, cand)
        elapsed = time.time() - t_start
        if i == 0:
            baseline_fold_medians = scored["per_fold_median"]
            baseline_district_medians = scored["per_district_median"]
            n_folds_better = n_districts_better = None
        else:
            n_folds_better = int((scored["per_fold_median"] < baseline_fold_medians).sum())
            n_districts_better = int((scored["per_district_median"] < baseline_district_medians).sum())

        row = {**cand, "aggregate_median_mase": scored["aggregate_median_mase"],
               "n_folds_better_than_baseline": n_folds_better,
               "n_districts_better_than_baseline": n_districts_better,
               "seconds": round(elapsed, 1)}
        results.append(row)
        logger.info(
            "[%d/%d] mase=%.4f folds_better=%s districts_better=%s (%.1fs, %.0fs elapsed total)",
            i + 1, len(candidates), scored["aggregate_median_mase"], n_folds_better, n_districts_better,
            elapsed, time.time() - t0,
        )

    results_df = pd.DataFrame(results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d candidate results to %s.", len(results_df), OUTPUT_PATH)

    baseline_mase = results_df.iloc[0]["aggregate_median_mase"]
    challengers = results_df.iloc[1:]
    qualifying = challengers[
        (challengers["aggregate_median_mase"] < baseline_mase)
        & (challengers["n_folds_better_than_baseline"] > (N_FOLDS - 1) / 2)
        & (challengers["n_districts_better_than_baseline"] > len(DISTRICTS) / 2)
    ]
    logger.info("=" * 70)
    logger.info("Baseline (production defaults) aggregate median MASE: %.4f", baseline_mase)
    logger.info("Candidates clearing the overfitting safeguard: %d/%d", len(qualifying), len(challengers))
    if len(qualifying):
        best = qualifying.sort_values("aggregate_median_mase").iloc[0]
        logger.info("Best qualifying candidate: %s", best.to_dict())
    logger.info("=" * 70)
    return results_df


def run_holdout_check(xgb_params: dict) -> float:
    """One-time holdout confirmation for a winning candidate - never used to
    pick between candidates (Decision 009 unchanged)."""
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    stage2_df = assemble_stage2_table()
    predicted, _ = train_and_predict_holdout(stage2_df, xgb_params=xgb_params)
    holdout_rows = stage2_df.loc[stage2_df["split"] == "holdout"].copy()
    holdout_rows["predicted_residual"] = predicted
    holdout_rows["final_prediction"] = combine_stage2_forecast(
        holdout_rows["sarima_prediction"].to_numpy(), predicted, mode="additive",
    )

    all_rows = []
    for district in DISTRICTS:
        all_rows.extend(compute_district_fold_metrics(district, weekly_df, holdout_rows))
    metrics_df = pd.DataFrame(all_rows)
    holdout_metrics = metrics_df[(metrics_df["model"] == "stage1_plus_stage2") & (metrics_df["fold_id"] == "holdout")]
    median_mase = float(holdout_metrics["mase"].median())
    logger.info("Holdout median MASE with candidate hyperparameters: %.4f", median_mase)
    return median_mase


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_search()
