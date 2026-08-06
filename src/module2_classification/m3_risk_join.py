"""Leakage-safe join of Module 3's spatial Hybrid Risk score into Module 2
Stage 1 (M2-014).

**Why lagged, not same-week (the leakage fix over the originally-proposed
idea):** Module 3's `Risk` for a given (District, Year, Week) is built from
that SAME week's real case counts - `Risk_0` (the KDE baseline) is
mass-conserved per `(Year, Week)` so it sums to that week's actual total
case count across districts, spatially redistributed by proximity to
case-heavy neighbours (`module_3_spatial/MODULE_CONTEXT.md`'s "KDE_baseline:
Two Valid Uses" section). Using `Risk` from the SAME week as a Module 2
Stage 1 feature would leak a transformation of the very case counts the
outbreak label is derived from. Using week *t-1*'s `Risk` instead is safe -
the same "prior week only" principle every other Module 2 lag feature
(`cases_lag_1`, `case_anomaly_lag_1`) already follows.

**Disclosed, not fixed, secondary caveat:** Module 3's own Stage 2 RF
correction uses a climate-anomaly feature computed from the FULL-HISTORY
mean (all years, not strictly-prior), because Module 3's own validation axis
is spatial K-means CV, not temporal (`module_3_spatial/MODULE_CONTEXT.md`'s
feature-engineering "Design notes" - explicitly justified there for Module
3's own purposes). Lagging `Risk` by one week does not remove this: an EARLY
Module 2 fold's `m3_risk_lag_1` value was computed using knowledge of LATER
years' average climate. This is a genuine, if minor, temporal-leakage
vector into Module 2's walk-forward folds, inherited from Module 3's design,
not newly introduced here. Judged disproportionate to fix given its likely
small practical size (Module 3's own evaluation found this RF correction
does not even improve Module 3's own aggregate fit - MAE +1.74% worse than
the KDE baseline alone, `module_3_spatial/MODULE_CONTEXT.md` Stage 2
evaluation table - so its climate-anomaly nuance is a small piece of a
correction that is itself small and unproven) - flagged explicitly here so
it is a disclosed, considered limitation, not a silent gap.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

M3_RISK_FEATURE_COLUMNS = [
    "m3_risk_lag_1",
    "m3_risk_lag_2",
]


def load_m3_risk_predictions(path: Path) -> pd.DataFrame:
    """Load Module 3's `hybrid_risk_map.csv` and keep one row per
    (District, Year, Week)."""
    m3 = pd.read_csv(path)
    required = {"District", "Year", "Week", "Risk"}
    missing = required - set(m3.columns)
    if missing:
        raise ValueError(f"Module 3 hybrid risk map at {path} missing columns: {sorted(missing)}")
    m3 = m3.drop_duplicates(subset=["District", "Year", "Week"], keep="last")
    return m3[["District", "Year", "Week", "Risk"]].copy()


def build_m3_risk_lags(calendar_df: pd.DataFrame, m3_predictions_df: pd.DataFrame) -> pd.DataFrame:
    """Gap-safe `m3_risk_lag_1/2` on the full Module 2 weekly calendar - same
    full-calendar-reindex-then-shift construction as `m1_forecast_join.py`'s
    `build_m1_forecast_lags` (Decision 015's pattern), so a calendar gap
    never pulls in a stale prior value."""
    calendar = calendar_df[["District", "Year", "Week"]].drop_duplicates()
    merged = calendar.merge(
        m3_predictions_df.rename(columns={"Risk": "m3_risk"}),
        on=["District", "Year", "Week"],
        how="left",
    )
    merged = merged.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    grouped = merged.groupby("District")["m3_risk"]
    merged["m3_risk_lag_1"] = grouped.shift(1)
    merged["m3_risk_lag_2"] = grouped.shift(2)

    out = merged[["District", "Year", "Week"] + M3_RISK_FEATURE_COLUMNS].copy()
    n_with_m3 = int(out["m3_risk_lag_1"].notna().sum())
    logger.info("Built Module 3 risk lags: %d / %d calendar rows have m3_risk_lag_1.", n_with_m3, len(out))
    return out
