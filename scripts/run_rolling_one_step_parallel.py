"""Parallel driver for `rolling_one_step.run_rolling_one_step(scope="all")`.

Phase 1 of the Module 1 remediation plan needs the full 25-district,
`scope="all"` rolling one-step backtest - a genuinely new run: every prior
full-25-district rolling run used `scope="holdout"` only (104 weeks/district,
see `module_1_forecasting/EXPERIMENT_LOG.md` M1-005's "2,600 rows" figure =
25 x 104). A serial timing test on one district (`Kilinochchi`, 858 rows)
took ~520s, i.e. ~3.6 hours serial for all 25 districts - each district's
rolling loop in `rolling_one_step.rolling_one_step_district()` is fully
independent (its own SARIMA refit per week, its own feature history), so
this script parallelizes across districts with a process pool instead.

Each worker reloads `weekly_modeling_table.csv`, the SARIMA configs, and the
frozen XGBoost model independently (cheap - a few hundred ms each) rather
than passing model objects across the process boundary, which avoids
pickling issues with `xgboost.XGBRegressor` on Windows' spawn-based
multiprocessing.

Output is byte-identical in format to `rolling_one_step.run_rolling_one_step`
(same three CSVs) - this script only changes HOW the rows are computed, not
what they mean or how they're evaluated. `summarize_metrics()` and
`compute_dm_results_rolling()` are reused unchanged.
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
    MODULE1_ROLLING_ONE_STEP_DM_PATH,
    MODULE1_ROLLING_ONE_STEP_METRICS_PATH,
    MODULE1_ROLLING_ONE_STEP_PATH,
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


def _run_one(district: str, mode: str, min_train_weeks: int) -> pd.DataFrame:
    """Worker entry point - must be module-level and take only picklable
    (str/int) arguments for Windows' spawn-based ProcessPoolExecutor."""
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
    )


def main(max_workers: int = 12) -> None:
    mode = validate_residual_mode(M1_STAGE2_RESIDUAL_MODE)
    min_train_weeks = DEFAULT_MIN_TRAIN_YEARS * DEFAULT_WEEKS_PER_YEAR
    t0 = time.time()

    frames: list[pd.DataFrame] = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_one, d, mode, min_train_weeks): d for d in DISTRICTS}
        for fut in as_completed(futures):
            district = futures[fut]
            df = fut.result()
            logger.info(
                "Done %s: %d rows (%.0fs elapsed, %d/%d districts complete)",
                district, len(df), time.time() - t0, len(frames) + 1, len(DISTRICTS),
            )
            frames.append(df)

    result = pd.concat(frames, ignore_index=True).sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    MODULE1_ROLLING_ONE_STEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE1_ROLLING_ONE_STEP_PATH, index=False)

    metrics = summarize_metrics(result)
    MODULE1_ROLLING_ONE_STEP_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(MODULE1_ROLLING_ONE_STEP_METRICS_PATH, index=False)

    dm_results = compute_dm_results_rolling(result, scope="all")
    MODULE1_ROLLING_ONE_STEP_DM_PATH.parent.mkdir(parents=True, exist_ok=True)
    dm_results.to_csv(MODULE1_ROLLING_ONE_STEP_DM_PATH, index=False)

    logger.info(
        "Wrote %d rows -> %s, %d metrics rows -> %s, %d DM rows -> %s. Total %.0fs.",
        len(result), MODULE1_ROLLING_ONE_STEP_PATH,
        len(metrics), MODULE1_ROLLING_ONE_STEP_METRICS_PATH,
        len(dm_results), MODULE1_ROLLING_ONE_STEP_DM_PATH,
        time.time() - t0,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
