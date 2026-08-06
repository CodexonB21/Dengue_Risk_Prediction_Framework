"""Orchestrate dashboard data refresh: weather -> preprocessing -> forecasts -> scoring."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DASHBOARD_REFRESH_MANIFEST_PATH,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE1_NOWCAST_ACCURACY_PATH,
    MODULE1_NOWCAST_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE2_FUTURE_RISK_PREDICTIONS_PATH,
    MODULE2_LIVE_RISK_PREDICTIONS_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    SHARED_CLIMATE_WEEKLY_PATH,
)

logger = logging.getLogger(__name__)

PYTHON = sys.executable


def _run_step(name: str, command: list[str]) -> None:
    logger.info("START %s: %s", name, " ".join(command))
    result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Step '{name}' failed with exit code {result.returncode}")
    logger.info("DONE %s", name)


def _summarize_outputs() -> pd.DataFrame:
    rows = []

    def _max_epi(path: Path, label: str) -> None:
        if not path.exists():
            rows.append({"artifact": label, "rows": 0, "max_year": None, "max_week": None})
            return
        df = pd.read_csv(path, usecols=lambda c: c in {"Year", "Week", "District"})
        rows.append({
            "artifact": label,
            "rows": len(df),
            "max_year": int(df["Year"].max()) if "Year" in df.columns and len(df) else None,
            "max_week": int(df.loc[df["Year"] == df["Year"].max(), "Week"].max())
            if "Year" in df.columns and len(df) else None,
        })

    _max_epi(SHARED_CLIMATE_WEEKLY_PATH, "climate_weekly")
    _max_epi(MODULE1_WEEKLY_MODELING_TABLE_PATH, "module1_weekly")
    _max_epi(MODULE2_WEEKLY_MODELING_TABLE_PATH, "module2_weekly")
    _max_epi(MODULE1_FUTURE_FORECAST_PATH, "future_forecast")
    _max_epi(MODULE1_NOWCAST_PATH, "nowcast_next_week")
    _max_epi(MODULE1_NOWCAST_ACCURACY_PATH, "nowcast_prospective_accuracy")
    _max_epi(MODULE2_LIVE_RISK_PREDICTIONS_PATH, "live_risk")
    _max_epi(MODULE2_FUTURE_RISK_PREDICTIONS_PATH, "future_risk")
    summary = pd.DataFrame(rows)
    summary["refreshed_at_utc"] = datetime.now(timezone.utc).isoformat()
    DASHBOARD_REFRESH_MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(DASHBOARD_REFRESH_MANIFEST_PATH, index=False)
    logger.info("Refresh manifest written to %s", DASHBOARD_REFRESH_MANIFEST_PATH)
    return summary


def run_refresh(skip_weather: bool = False) -> pd.DataFrame:
    if not skip_weather:
        _run_step(
            "fetch_open_meteo_weather",
            [PYTHON, str(PROJECT_ROOT / "scripts" / "fetch_open_meteo_weather.py")],
        )
    else:
        logger.info("SKIP fetch_open_meteo_weather (--skip-weather)")

    _run_step("shared_preprocessing", [PYTHON, "-m", "src.preprocessing.shared"])
    _run_step("module1_preprocessing", [PYTHON, "-m", "src.preprocessing.module1_preprocessing"])
    _run_step("module2_preprocessing", [PYTHON, "-m", "src.preprocessing.module2_preprocessing"])
    _run_step("module1_forecast_future", [PYTHON, "-m", "src.module1_forecasting.forecast_future"])
    _run_step(
        "module1_nowcast",
        [PYTHON, "-m", "src.module1_forecasting.forecast_future", "--nowcast"],
    )
    _run_step(
        "module1_nowcast_reconcile",
        [PYTHON, "-m", "src.module1_forecasting.nowcast_tracking"],
    )
    _run_step("module2_live_scoring", [PYTHON, "-m", "src.module2_classification.live_scoring"])
    _run_step(
        "module2_forecast_future_risk",
        [PYTHON, "-m", "src.module2_classification.forecast_future_risk"],
    )
    return _summarize_outputs()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh all dashboard CSV outputs.")
    parser.add_argument(
        "--skip-weather",
        action="store_true",
        help="Skip Open-Meteo fetch (offline dev when raw weather is already current).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_refresh(skip_weather=args.skip_weather)
