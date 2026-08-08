"""Exploratory alpha sweep for FIT QUALITY, not convergence (Critique Point
2 / EXPERIMENT_LOG.md M3-006).

`iterative_loop.py` already swept alpha in {1.0, 0.3, 0.15, 0.05} (M3-004),
but only to find which alpha satisfies the STRICT convergence criterion
(`max_delta < epsilon`) fastest - alpha=0.05 won because it is the smallest
value tested, not because it was tuned for accuracy. `evaluate.py` (M3-005)
then found Stage 2 shows a null/negative aggregate-fit result at that
alpha. This script asks a different, explicitly exploratory question: does
ANY of the same 4 alpha values, run for the FULL 4-iteration budget
regardless of whether the strict convergence criterion is ever satisfied,
produce a genuine improvement in fit to actual case counts?

**This does NOT replace alpha=0.05 as Module 3's official reported
result.** Per M3-004/M3-005, alpha=0.05 remains the sole value that
actually satisfies the loop's own convergence criterion within budget -
a non-convergent alpha cannot legitimately be reported as "the" final
model, since it would contradict the loop's own stopping rule. This script
exists only to answer, honestly and separately, whether accuracy and
convergence-speed point the same direction or trade off against each other
- logged as its own metrics file, never merged into `results_summary.txt`.

**OUTCOME NOTE (2026-08-05, EXPERIMENT_LOG.md M3-008 - added after the fact,
does not change this script's code/behavior)**: this sweep's answer, with
the ORIGINAL 16-feature set, was "no - none of the 4 alphas beat Stage 1
alone." The real fix turned out to be a missing feature (own-district
residual lag features), not an alpha retune - see M3-008, which promoted
`alpha=1.0` (with the new features) to the official pipeline. This script
is deliberately left UNCHANGED (still imports the original `FEATURE_COLUMNS`
with no residual lags) so its numbers stay byte-for-byte reproducible as a
historical record of the pre-M3-008 finding.
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

from src.config import MODULE3_ALPHA_SWEEP_METRICS_PATH, MODULE3_METRICS_DIR  # noqa: E402
from src.module3_spatial.compensation_model import build_spatial_folds, load_training_table, rescale_kde_baseline  # noqa: E402
from src.module3_spatial.iterative_loop import MORAN_RANDOM_SEED, out_of_fold_predict  # noqa: E402

# Frozen at 4 (NOT imported from iterative_loop.py's own MAX_ITERATIONS,
# which M3-008 changed to 1 for the official pipeline) - this ablation's
# reported numbers swept the full 4-iteration budget per alpha and must
# stay reproducible regardless of later changes to the official pipeline.
MAX_ITERATIONS = 4

logger = logging.getLogger(__name__)

# Same 4 values M3-004 already tested for convergence speed - reused here,
# not re-chosen, so the two experiments are directly comparable.
ALPHA_VALUES = (1.0, 0.3, 0.15, 0.05)


def _fit_metrics(risk: np.ndarray, actual: np.ndarray) -> dict:
    return {
        "corr": float(np.corrcoef(risk, actual)[0, 1]),
        "mae": float(np.mean(np.abs(actual - risk))),
        "rmse": float(np.sqrt(np.mean((actual - risk) ** 2))),
    }


def run_alpha_sweep() -> pd.DataFrame:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    np.random.seed(MORAN_RANDOM_SEED)

    df = load_training_table()
    df = rescale_kde_baseline(df)
    folds_df = build_spatial_folds()
    number_of_cases = df["Number_of_Cases"].to_numpy(dtype=float)
    risk_0 = df["kde_baseline_rescaled"].to_numpy(dtype=float)

    rows = []
    for alpha in ALPHA_VALUES:
        risk_prev = risk_0.copy()
        residual_target = number_of_cases - risk_prev
        for t in range(1, MAX_ITERATIONS + 1):
            predicted_residual = out_of_fold_predict(df, folds_df, residual_target)
            risk_t = risk_prev + alpha * predicted_residual

            metrics = _fit_metrics(risk_t, number_of_cases)
            rows.append({"alpha": alpha, "iteration": t, **metrics})
            logger.info(
                "alpha=%.2f iteration=%d: corr=%.4f mae=%.3f rmse=%.3f",
                alpha, t, metrics["corr"], metrics["mae"], metrics["rmse"],
            )

            residual_target = number_of_cases - risk_t
            risk_prev = risk_t

    result = pd.DataFrame(rows)
    stage1_metrics = _fit_metrics(risk_0, number_of_cases)
    result = pd.concat(
        [pd.DataFrame([{"alpha": None, "iteration": 0, **stage1_metrics}]), result], ignore_index=True
    )
    result.to_csv(MODULE3_ALPHA_SWEEP_METRICS_PATH, index=False)
    logger.info("Alpha sweep (accuracy) written to %s.", MODULE3_ALPHA_SWEEP_METRICS_PATH)

    best = result.loc[result["alpha"].notna(), "mae"].idxmin()
    logger.info(
        "Best MAE across the sweep: alpha=%.2f iteration=%d MAE=%.3f (Stage 1 alone MAE=%.3f).",
        result.loc[best, "alpha"], result.loc[best, "iteration"], result.loc[best, "mae"], stage1_metrics["mae"],
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_alpha_sweep()
