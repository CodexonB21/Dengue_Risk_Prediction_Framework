"""Leakage-safe join of Module 1 walk-forward OOS forecasts into Module 2 Stage 2.

M2-007D features (used by tree-based Stage 2 architectures only):

- ``m1_final_prediction_lag_1`` — M1 hybrid ``final_prediction`` from week *t−1*
- ``m1_forecast_momentum`` — ``m1_final_prediction_lag_1 − cases_lag_2``

M1 predictions MUST come from walk-forward out-of-sample rows in
``final_combined_predictions.csv`` (or an explicit variant path). Never use
in-sample SARIMA or a production model refit that includes holdout in training
when scoring holdout rows.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

M1_FORECAST_FEATURE_COLUMNS = [
    "m1_final_prediction_lag_1",
    "m1_forecast_momentum",
]


def load_m1_oos_predictions(path: Path) -> pd.DataFrame:
    """Load M1 combined predictions and keep one OOS row per (District, Year, Week)."""
    m1 = pd.read_csv(path)
    required = {"District", "Year", "Week", "final_prediction"}
    missing = required - set(m1.columns)
    if missing:
        raise ValueError(f"M1 predictions at {path} missing columns: {sorted(missing)}")

    # Walk-forward file may contain duplicate keys only if multiple splits overlap;
    # keep validation+holdout rows (exclude any duplicate fold artifacts if present).
    m1 = m1.sort_values(["District", "Year", "Week", "split"])
    m1 = m1.drop_duplicates(subset=["District", "Year", "Week"], keep="last")
    return m1[["District", "Year", "Week", "final_prediction", "split", "fold_id"]].copy()


def build_m1_forecast_lags(
    calendar_df: pd.DataFrame,
    m1_predictions_df: pd.DataFrame,
) -> pd.DataFrame:
    """Gap-safe ``m1_final_prediction_lag_1`` on the full M2 weekly calendar."""
    calendar = calendar_df[["District", "Year", "Week"]].drop_duplicates()
    merged = calendar.merge(
        m1_predictions_df.rename(columns={"final_prediction": "m1_final_prediction"}),
        on=["District", "Year", "Week"],
        how="left",
    )
    merged = merged.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    merged["m1_final_prediction_lag_1"] = merged.groupby("District")["m1_final_prediction"].shift(1)

    out = merged[["District", "Year", "Week", "m1_final_prediction_lag_1"]].copy()
    n_with_m1 = int(out["m1_final_prediction_lag_1"].notna().sum())
    logger.info(
        "Built M1 forecast lag: %d / %d calendar rows have m1_final_prediction_lag_1.",
        n_with_m1, len(out),
    )
    return out
