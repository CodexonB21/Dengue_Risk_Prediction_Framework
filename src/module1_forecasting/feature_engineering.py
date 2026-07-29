"""Module 1 Stage 2 feature engineering.

Reads `data/processed/module1/weekly_modeling_table.csv` and builds Stage 2
(XGBoost residual compensation) features per
`research_context/FEATURE_ENGINEERING_SPEC.md`, writing the fold-agnostic
portion to `data/features/module1/`.

Per `research_context/PIPELINE_ARCHITECTURE_PLAN.md`, features split into two
categories:

- **Fold-agnostic** (Feature Groups 1, 2, 4): pure shifts/rolling windows of
  already-observed values - case lags, rolling case stats, rate of change,
  climate lags, cyclic week encoding, monsoon indicators. Safe to compute
  once, globally, regardless of how walk-forward folds are later drawn.
  `build_fold_agnostic_features` computes these and `run_feature_engineering`
  writes them to disk.
- **Fold-aware** (Feature Group 3): climate anomalies
  (`rainfall_anomaly`/`temperature_anomaly`/`humidity_anomaly`). These
  MUST be recomputed separately inside each walk-forward fold
  (`src/module1_forecasting/validation.py`), using only that fold's training
  window, or they leak future climate norms into early folds. This module
  exposes `compute_fold_climate_anomalies` as a function to be called once
  per fold by the (not-yet-built) Stage 1/2 pipeline - it is intentionally
  NOT written to the global feature file.

Explicitly out of scope here: `sarima_prediction`/`residual_lag_1`/
`residual_lag_2` (Feature Group 5) - produced by the Stage 1 model once it
exists, accepted as input columns, not computed by this script.

`weather_code` is excluded from the output feature table (Decision 008,
Module-1-scoped) - it remains present upstream in
`data/processed/module1/weekly_modeling_table.csv`.
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
    MODULE1_FEATURES_DIR,
    MODULE1_STAGE2_FEATURE_TABLE_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MONSOON_WEEKS_NE,
    MONSOON_WEEKS_SW,
)

logger = logging.getLogger(__name__)

# Raw climate columns used as the "rainfall"/"temperature"/"humidity" source
# for lag and anomaly features. Module 1 Open Question #5 ("Should rain_sum
# or precipitation_sum be preferred?") is RESOLVED as of the Stage 2 session
# (2026-07-27): precipitation_sum is used. Open-Meteo's own documentation
# confirms precipitation_sum = rain + showers + snowfall (liquid equivalent),
# while rain_sum excludes showers entirely. Sri Lanka's monsoon rainfall is
# heavily convective-shower-driven, so rain_sum risked systematically
# undercounting real water input relevant to mosquito-breeding habitat -
# precipitation_sum is the more complete signal. See RESEARCH_DECISIONS.md
# Decision 008.
RAINFALL_COLUMN = "precipitation_sum (mm)"
TEMPERATURE_COLUMN = "temperature_2m_mean (\u00b0C)"
HUMIDITY_COLUMN = "relative_humidity_2m_mean (%)"
WEATHER_CODE_COLUMN = "weather_code (wmo code)"

CASE_LAGS = (1, 2, 3, 4)
RAINFALL_LAGS = range(2, 9)   # 2-8
TEMPERATURE_LAGS = range(1, 5)  # 1-4
HUMIDITY_LAGS = range(1, 5)   # 1-4
ROLLING_WINDOW = 4
WEEKS_PER_YEAR = 52


# ---------------------------------------------------------------------------
# Fold-agnostic features (Feature Groups 1, 2, 4)
# ---------------------------------------------------------------------------

def build_fold_agnostic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the Stage 2 features that are pure shifts/windows of
    already-observed values and are therefore safe to compute once, globally
    (FEATURE_ENGINEERING_SPEC.md Feature Groups 1, 2, 4).
    """
    df = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    out = df.copy()
    grouped = df.groupby("District")

    # --- Feature Group 1: case-trend features ---
    for lag in CASE_LAGS:
        out[f"cases_lag_{lag}"] = grouped["Number_of_Cases"].shift(lag)

    # Rolling stats use only the ROLLING_WINDOW weeks strictly BEFORE the
    # current row (shift(1) before rolling) - the current week's own case
    # count is exactly what Stage 2 is trying to correct, so it must never
    # leak into its own feature row.
    out["rolling_mean_cases_4w"] = grouped["Number_of_Cases"].transform(
        lambda s: s.shift(1).rolling(ROLLING_WINDOW).mean()
    )
    out["rolling_std_cases_4w"] = grouped["Number_of_Cases"].transform(
        lambda s: s.shift(1).rolling(ROLLING_WINDOW).std()
    )

    # Rate of change: absolute (not percent) difference between the two most
    # recent known lags. A percent-change formulation would blow up (or
    # divide by zero) given this project's well-documented zero-inflation
    # (see DATA_DICTIONARY.md Data Quality Notes) - this is an implementation
    # choice, not a settled research decision, flagged for future review.
    out["rate_of_change"] = out["cases_lag_1"] - out["cases_lag_2"]

    # --- Feature Group 2: lagged climate features ---
    for lag in RAINFALL_LAGS:
        out[f"rainfall_lag_{lag}"] = grouped[RAINFALL_COLUMN].shift(lag)
    for lag in TEMPERATURE_LAGS:
        out[f"temperature_lag_{lag}"] = grouped[TEMPERATURE_COLUMN].shift(lag)
    for lag in HUMIDITY_LAGS:
        out[f"humidity_lag_{lag}"] = grouped[HUMIDITY_COLUMN].shift(lag)

    # --- Feature Group 4: seasonal / contextual indicators ---
    # Safe because Module 1 preprocessing already collapsed week 53 into
    # week 52 (Decision 007), so Week is always in [1, 52] here.
    out["sin_week"] = np.sin(2 * np.pi * out["Week"] / WEEKS_PER_YEAR)
    out["cos_week"] = np.cos(2 * np.pi * out["Week"] / WEEKS_PER_YEAR)
    out["monsoon_indicator_SW"] = out["Week"].isin(MONSOON_WEEKS_SW).astype(int)
    out["monsoon_indicator_NE"] = out["Week"].isin(MONSOON_WEEKS_NE).astype(int)

    return out


# ---------------------------------------------------------------------------
# Fold-aware features (Feature Group 3) - NOT written globally
# ---------------------------------------------------------------------------

def compute_fold_climate_anomalies(
    df: pd.DataFrame,
    train_mask: pd.Series,
    rainfall_col: str = RAINFALL_COLUMN,
    temperature_col: str = TEMPERATURE_COLUMN,
    humidity_col: str = HUMIDITY_COLUMN,
) -> pd.DataFrame:
    """Compute rainfall/temperature/humidity anomalies for ONE walk-forward
    fold, using only that fold's training rows (`train_mask == True`) to
    establish the long-term district-week climate norm:

        anomaly = current_week_value - long_term_mean_for_same_district_and_week

    MUST be called separately, with a different `train_mask`, for every
    walk-forward fold (`src/module1_forecasting/validation.py`,
    Decisions 009/010) - computing this once globally over the full history
    would leak future climate norms into early folds
    (FEATURE_ENGINEERING_SPEC.md Feature Group 3).

    Returns a DataFrame (aligned to `df`'s row order/index) with columns
    `rainfall_anomaly`, `temperature_anomaly`, `humidity_anomaly` for every
    row in `df`. Callers should only actually use the rows relevant to that
    fold (its own train + validation rows) - anomalies for rows outside a
    fold, computed against that fold's norm, are not meaningful and must not
    be reused across folds.
    """
    if not train_mask.any():
        raise ValueError("train_mask has no True rows - cannot compute a training-window norm.")

    value_cols = [rainfall_col, temperature_col, humidity_col]
    train_norms = df.loc[train_mask].groupby(["District", "Week"])[value_cols].mean()

    keys = pd.MultiIndex.from_arrays([df["District"].to_numpy(), df["Week"].to_numpy()])
    norms = train_norms.reindex(keys)

    anomalies = pd.DataFrame(index=df.index)
    anomalies["rainfall_anomaly"] = df[rainfall_col].to_numpy() - norms[rainfall_col].to_numpy()
    anomalies["temperature_anomaly"] = df[temperature_col].to_numpy() - norms[temperature_col].to_numpy()
    anomalies["humidity_anomaly"] = df[humidity_col].to_numpy() - norms[humidity_col].to_numpy()

    n_unresolved = norms.isna().any(axis=1).sum()
    if n_unresolved:
        logger.warning(
            "%d rows have no training-window climate norm for their "
            "(District, Week) - likely a fold whose training window is "
            "shorter than one full annual cycle, or a (District, Week) with "
            "no non-missing climate reading in that window.",
            int(n_unresolved),
        )

    return anomalies


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_module1_feature_table(
    input_path: Path = MODULE1_WEEKLY_MODELING_TABLE_PATH,
) -> pd.DataFrame:
    df = pd.read_csv(input_path, parse_dates=["Week_Start_Date", "Week_End_Date"])
    features = build_fold_agnostic_features(df)
    return features.drop(columns=[WEATHER_CODE_COLUMN], errors="ignore")


def run_feature_engineering() -> pd.DataFrame:
    MODULE1_FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    features = build_module1_feature_table()
    features.to_csv(MODULE1_STAGE2_FEATURE_TABLE_PATH, index=False)

    logger.info(
        "Wrote %d feature rows (%d columns) to %s. Fold-aware climate "
        "anomalies are NOT included here - call "
        "compute_fold_climate_anomalies() per walk-forward fold instead.",
        len(features), features.shape[1], MODULE1_STAGE2_FEATURE_TABLE_PATH,
    )
    return features


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_feature_engineering()
