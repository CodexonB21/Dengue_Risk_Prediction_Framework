"""Stage 2 vs. naive persistence baseline (EXPERIMENT_LOG.md M3-010).

M3-008 promoted own-district residual lags into Stage 2's RF and found
`residual_rescaled_lag_1` + `residual_rescaled_lag_2` = 89.8% combined
feature importance - the RF's headline improvement (MAE 20.54 -> 9.96) is
overwhelmingly driven by two lag columns, not the original 16
climate/demographic features. That raises an obvious, defense-panel-grade
question M3-008 never directly answered: does the RF's spatial CV output
actually beat the trivial arithmetic of just copying last week's own
residual forward (`predicted_residual_t = residual_rescaled_lag_1`, no
model, no training, no fold structure)?

This is a fair, like-for-like comparison, not a strawman: the naive
predictor is combined with Risk_0 via the SAME formula the official model
uses (`Risk_t = Risk_0 + SHRINKAGE_ALPHA * predicted_residual`,
`iterative_loop.py`'s `alpha=1.0`) and clipped at 0 the same way, evaluated
on the SAME 25,123-row table `compensation_model.py::prepare_training_table()`
produces. The naive predictor needs no train/test split at all (it uses
only a district's own past, always available at real inference time), so
there is no leakage question to resolve before trusting it - unlike the
RF, which requires the spatial CV structure specifically to avoid
overfitting.
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

from src.config import (  # noqa: E402
    MODULE3_HYBRID_RISK_MAP_PATH,
    MODULE3_METRICS_DIR,
    MODULE3_PERSISTENCE_BASELINE_PATH,
)
from src.module3_spatial.compensation_model import prepare_training_table  # noqa: E402
from src.module3_spatial.iterative_loop import SHRINKAGE_ALPHA  # noqa: E402

logger = logging.getLogger(__name__)


def _fit_metrics(pred: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(pred, actual)[0, 1]),
        "mae": float(np.mean(np.abs(actual - pred))),
        "rmse": float(np.sqrt(np.mean((actual - pred) ** 2))),
    }


def run_persistence_baseline() -> pd.DataFrame:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = prepare_training_table()
    hybrid = pd.read_csv(MODULE3_HYBRID_RISK_MAP_PATH)[["District", "Year", "Week", "Risk"]]
    merged = df.merge(hybrid, on=["District", "Year", "Week"], how="inner")
    if len(merged) != len(hybrid):
        raise ValueError(
            f"Expected the merge to preserve all {len(hybrid)} hybrid_risk_map.csv "
            f"rows, got {len(merged)}."
        )

    number_of_cases = merged["Number_of_Cases"].to_numpy(dtype=float)
    risk_0 = merged["kde_baseline_rescaled"].to_numpy(dtype=float)
    risk_rf = merged["Risk"].to_numpy(dtype=float)  # official Stage 2, out-of-fold RF

    # Naive persistence: no model at all - just carry last week's own
    # residual forward, combined via the SAME alpha/clipping the official
    # model uses, so the only thing being isolated is "RF vs. arithmetic
    # copy," not a different combination formula.
    predicted_residual_persistence = merged["residual_rescaled_lag_1"].to_numpy(dtype=float)
    risk_persistence_unclipped = risk_0 + SHRINKAGE_ALPHA * predicted_residual_persistence
    n_clipped = int((risk_persistence_unclipped < 0).sum())
    risk_persistence = np.clip(risk_persistence_unclipped, 0.0, None)

    stage1 = _fit_metrics(risk_0, number_of_cases)
    persistence = _fit_metrics(risk_persistence, number_of_cases)
    stage2_rf = _fit_metrics(risk_rf, number_of_cases)

    comparison = pd.DataFrame(
        [
            {"model": "Stage 1 alone (Risk_0, rescaled KDE_baseline)", **stage1},
            {"model": "Naive persistence (Risk_0 + last week's own residual, no model)", **persistence},
            {"model": "Stage 2 RF, official (Risk_0 + out-of-fold RF residual)", **stage2_rf},
        ]
    )
    comparison.to_csv(MODULE3_PERSISTENCE_BASELINE_PATH, index=False)

    rf_beats_persistence = stage2_rf["mae"] < persistence["mae"]
    logger.info(
        "Naive persistence: corr=%.4f, MAE=%.4f, RMSE=%.4f (%d/%d rows clipped at 0). "
        "Stage 2 RF (official): corr=%.4f, MAE=%.4f, RMSE=%.4f. "
        "RF beats naive persistence on MAE: %s.",
        persistence["corr"], persistence["mae"], persistence["rmse"],
        n_clipped, len(merged),
        stage2_rf["corr"], stage2_rf["mae"], stage2_rf["rmse"],
        rf_beats_persistence,
    )
    logger.info("Persistence baseline comparison written to %s.", MODULE3_PERSISTENCE_BASELINE_PATH)

    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_persistence_baseline()
