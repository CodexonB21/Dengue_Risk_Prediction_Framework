"""Exploratory ablation (EXPERIMENT_LOG.md M3-011) - NOT the official
pipeline. Frozen once run; do not modify after the finding is written up.

M3-010 (`persistence_baseline.py`) found the official Stage 2 RF does NOT
beat naive persistence (`predicted_residual_t = residual_rescaled_lag_1`,
no model) on MAE (9.96 vs. 9.44), though it wins on corr and RMSE and
clips roughly half as many rows to zero. This experiment tests one
concrete fix: instead of asking the RF to predict the raw residual (which
already has `residual_rescaled_lag_1` as one of 20 input features, but
must implicitly reconstruct persistence's near-identity effect through
tree splits), have the RF predict the CORRECTION beyond persistence
(`target = residual_rescaled - residual_rescaled_lag_1`) and add its
out-of-fold prediction back onto the naive persistence baseline:

    predicted_residual_blend = residual_rescaled_lag_1 + predicted_correction
    Risk_blend = Risk_0 + SHRINKAGE_ALPHA * predicted_residual_blend, clipped at 0

This is not mathematically identical to the original formulation for a
Random Forest (unlike a linear model): pre-subtracting the dominant lag_1
effect removes most of the target's variance (heavily skewed by the 2017
outbreak) before the trees ever see it, which changes where they spend
their split budget. Whether that helps is an empirical question, tested
here, not assumed.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE3_METRICS_DIR, MODULE3_STACKED_PERSISTENCE_PATH  # noqa: E402
from src.module3_spatial.compensation_model import (  # noqa: E402
    STAGE2_FEATURE_COLUMNS,
    build_spatial_folds,
    prepare_training_table,
)
from src.module3_spatial.iterative_loop import SHRINKAGE_ALPHA, out_of_fold_predict  # noqa: E402

logger = logging.getLogger(__name__)


def _fit_metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(pred, actual)[0, 1]),
        "mae": float(np.mean(np.abs(actual - pred))),
        "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
    }


def run_stacked_persistence_experiment() -> pd.DataFrame:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = prepare_training_table()
    folds_df = build_spatial_folds()

    number_of_cases = df["Number_of_Cases"].to_numpy(dtype=float)
    risk_0 = df["kde_baseline_rescaled"].to_numpy(dtype=float)
    residual_actual = df["residual_rescaled"].to_numpy(dtype=float)
    residual_lag1 = df["residual_rescaled_lag_1"].to_numpy(dtype=float)

    def _risk_from_predicted_residual(predicted_residual: np.ndarray) -> np.ndarray:
        unclipped = risk_0 + SHRINKAGE_ALPHA * predicted_residual
        return np.clip(unclipped, 0.0, None)

    # --- Baseline 1: Stage 1 alone ---
    stage1 = _fit_metrics(risk_0, number_of_cases)

    # --- Baseline 2: naive persistence (no model) ---
    risk_persistence = _risk_from_predicted_residual(residual_lag1)
    persistence = _fit_metrics(risk_persistence, number_of_cases)

    # --- Baseline 3: official Stage 2 RF (predicts raw residual directly) ---
    predicted_residual_rf = out_of_fold_predict(
        df, folds_df, residual_actual, feature_cols=STAGE2_FEATURE_COLUMNS,
    )
    risk_rf = _risk_from_predicted_residual(predicted_residual_rf)
    rf_direct = _fit_metrics(risk_rf, number_of_cases)

    # --- Experimental: RF predicts the correction beyond persistence ---
    correction_target = residual_actual - residual_lag1
    predicted_correction = out_of_fold_predict(
        df, folds_df, correction_target, feature_cols=STAGE2_FEATURE_COLUMNS,
    )
    predicted_residual_blend = residual_lag1 + predicted_correction
    risk_blend = _risk_from_predicted_residual(predicted_residual_blend)
    blend = _fit_metrics(risk_blend, number_of_cases)

    comparison = pd.DataFrame(
        [
            {"model": "Stage 1 alone (Risk_0)", **stage1},
            {"model": "Naive persistence (no model)", **persistence},
            {"model": "Stage 2 RF, official (predicts raw residual)", **rf_direct},
            {"model": "Stacked: RF predicts correction beyond persistence", **blend},
        ]
    )
    comparison.to_csv(MODULE3_STACKED_PERSISTENCE_PATH, index=False)

    logger.info("Comparison:\n%s", comparison.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    logger.info("Written to %s.", MODULE3_STACKED_PERSISTENCE_PATH)

    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stacked_persistence_experiment()
