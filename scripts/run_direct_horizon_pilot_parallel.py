"""Parallel driver for `direct_horizon_pilot.run_direct_horizon_pilot(scope="all")`.

Mirrors `scripts/run_rolling_one_step_parallel.py`'s pattern exactly (same
reasoning: each district's loop in `rolling_direct_and_recursive_district()`
is fully independent - its own SARIMA refits, its own feature/residual
history - so this parallelizes across districts with a process pool rather
than running all 25 serially).

A serial timing check on two districts (`Colombo`, `Mannar`, holdout scope
only - 104 weeks each) took ~2-4 minutes per district, roughly double
`rolling_one_step.py`'s per-origin cost (this script also reconstructs a
recursive comparison step and runs 2 extra XGBoost predicts per origin, on
top of asking SARIMA for `n_periods=2` instead of 1). Full history is ~13-14x
longer per district than the holdout window alone, so a serial `scope="all"`
run across all 25 districts would take several hours - parallelized here the
same way the existing rolling one-step backtest was.
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
    MODULE1_DIRECT_HORIZON_PILOT_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.direct_horizon_pilot import (  # noqa: E402
    MAX_HORIZON_DEFAULT,
    rolling_direct_and_recursive_district,
)
from src.module1_forecasting.residual_transform import validate_residual_mode  # noqa: E402
from src.module1_forecasting.rolling_one_step import _load_selected_configs  # noqa: E402
from src.module1_forecasting.validation import DEFAULT_MIN_TRAIN_YEARS, DEFAULT_WEEKS_PER_YEAR  # noqa: E402

logger = logging.getLogger(__name__)


def _run_one(district: str, mode: str, min_train_weeks: int, max_horizon: int) -> pd.DataFrame:
    """Worker entry point - must be module-level and take only picklable
    (str/int) arguments for Windows' spawn-based ProcessPoolExecutor."""
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    sarima_configs = _load_selected_configs()
    paths = module1_stage2_paths(mode)
    xgb_model = xgb.XGBRegressor()
    xgb_model.load_model(str(paths["xgboost_final_model"]))
    return rolling_direct_and_recursive_district(
        district, weekly_df, sarima_configs[district], xgb_model,
        min_train_weeks=min_train_weeks, target_keys=None, residual_mode=mode,
        max_horizon=max_horizon,
    )


def main(max_workers: int = 12, max_horizon: int = MAX_HORIZON_DEFAULT) -> None:
    mode = validate_residual_mode(M1_STAGE2_RESIDUAL_MODE)
    min_train_weeks = DEFAULT_MIN_TRAIN_YEARS * DEFAULT_WEEKS_PER_YEAR
    t0 = time.time()

    frames: list[pd.DataFrame] = []
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_one, d, mode, min_train_weeks, max_horizon): d for d in DISTRICTS}
        for fut in as_completed(futures):
            district = futures[fut]
            df = fut.result()
            logger.info(
                "Done %s: %d rows (%.0fs elapsed, %d/%d districts complete)",
                district, len(df), time.time() - t0, len(frames) + 1, len(DISTRICTS),
            )
            frames.append(df)

    result = pd.concat(frames, ignore_index=True).sort_values(["District", "origin_Year", "origin_Week"]).reset_index(drop=True)
    MODULE1_DIRECT_HORIZON_PILOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE1_DIRECT_HORIZON_PILOT_PATH, index=False)

    logger.info(
        "Wrote %d direct-horizon-pilot rows -> %s. Total %.0fs.",
        len(result), MODULE1_DIRECT_HORIZON_PILOT_PATH, time.time() - t0,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
