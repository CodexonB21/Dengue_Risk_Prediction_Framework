"""M1-015: full 25-district rolling one-step evaluation with the vintage-
ensemble SARIMA prediction (`rolling_one_step._vintage_ensemble_step`).

A cheap 60-week, 6-district check (`scripts/` ad hoc, see EXPERIMENT_LOG.md
M1-015) found the ensembled SARIMA prediction correlates MORE closely with
fold-refit SARIMA than the plain cold weekly refit does, for 5/6 districts
tested (e.g. Colombo: r=0.181 -> 0.265; Kandy: r=0.444 -> 0.512), at
essentially the same per-week cost (still one fresh refit per week - the
ensemble only adds a few cheap `.forecast()` calls on already-fitted
vintages). This script runs the full 25-district comparison to check
whether that stability improvement translates into a real DM-test/MASE
improvement over the plain rolling baseline
(`rolling_one_step_dm_test.csv`, `rolling_one_step_predictions.csv`).

Mirrors `run_rolling_one_step_parallel.py`'s process-pool-per-district
pattern exactly; only the per-district worker call differs
(`ensemble_window=4` passed through). Output is written to separate,
`_ensemble`-suffixed paths - the production rolling baseline files are
never touched by this script.
"""

from __future__ import annotations

import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_METRICS_DIR,
    MODULE1_PROCESSED_DIR,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.residual_transform import validate_residual_mode  # noqa: E402
from src.module1_forecasting.rolling_one_step import (  # noqa: E402
    _load_selected_configs,
    compute_dm_results_rolling,
    rolling_one_step_district,
    summarize_metrics,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
)

logger = logging.getLogger(__name__)

ENSEMBLE_WINDOW = 4
OUTPUT_PATH = MODULE1_PROCESSED_DIR / "rolling_one_step_predictions_ensemble.csv"
METRICS_PATH = MODULE1_METRICS_DIR / "rolling_one_step_metrics_ensemble.csv"
DM_PATH = MODULE1_METRICS_DIR / "rolling_one_step_dm_test_ensemble.csv"


def _run_one(district: str, mode: str, min_train_weeks: int, ensemble_window: int) -> pd.DataFrame:
    """Worker entry point - module-level, picklable args only (Windows spawn)."""
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    sarima_configs = _load_selected_configs()
    paths = module1_stage2_paths(mode)
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))
    return rolling_one_step_district(
        district, weekly_df, sarima_configs[district], xgb_model,
        min_train_weeks=min_train_weeks, target_keys=None, residual_mode=mode,
        ensemble_window=ensemble_window,
    )


def main(max_workers: int = 12) -> None:
    mode = validate_residual_mode(M1_STAGE2_RESIDUAL_MODE)
    min_train_weeks = DEFAULT_MIN_TRAIN_YEARS * DEFAULT_WEEKS_PER_YEAR
    t0 = time.time()

    frames: list[pd.DataFrame] = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_one, d, mode, min_train_weeks, ENSEMBLE_WINDOW): d for d in DISTRICTS
        }
        for fut in as_completed(futures):
            district = futures[fut]
            df = fut.result()
            logger.info(
                "Done %s: %d rows (%.0fs elapsed, %d/%d districts complete)",
                district, len(df), time.time() - t0, len(frames) + 1, len(DISTRICTS),
            )
            frames.append(df)

    result = pd.concat(frames, ignore_index=True).sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT_PATH, index=False)

    metrics = summarize_metrics(result)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(METRICS_PATH, index=False)

    dm_results = compute_dm_results_rolling(result, scope="all_ensemble")
    DM_PATH.parent.mkdir(parents=True, exist_ok=True)
    dm_results.to_csv(DM_PATH, index=False)

    n_helps = int((dm_results["mean_loss_diff"] > 0).sum())
    n_sig = int((dm_results["p_value"] < 0.05).sum())
    logger.info(
        "Wrote %d rows -> %s, %d metrics rows -> %s, %d DM rows -> %s. Total %.0fs.",
        len(result), OUTPUT_PATH, len(metrics), METRICS_PATH, len(dm_results), DM_PATH, time.time() - t0,
    )
    logger.info(
        "Ensemble rolling DM test: %d/25 districts helping (mean_loss_diff>0), %d/25 significant (p<0.05).",
        n_helps, n_sig,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
