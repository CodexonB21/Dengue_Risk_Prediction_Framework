"""Module 2 outbreak label definition (Decision 019).

Implements the fold-aware epidemic-threshold label:

    threshold(District, Week, Year) = historical_mean + k * historical_SD
    outbreak = 1 if Number_of_Cases > threshold else 0

where `historical_mean`/`historical_SD` for a given row are computed from
that (District, Week)'s case counts in STRICTLY-PRIOR years only (an
expanding window, never the full series) - this is a genuine LABEL-leakage
guard, distinct in kind from Module 1's feature-only climate-anomaly guard
(`compute_fold_climate_anomalies`): computing this once globally would let
every walk-forward fold "see" whether later years turned out to be outbreak
years relative to a mean that includes those same later years.

`is_imputed` rows are handled with two separate, deliberate rules:
1. They are EXCLUDED from the historical mean/SD calculation itself - a
   seasonal-naive-imputed value is, by construction, close to that (District,
   Week)'s existing mean and would artificially dampen the computed
   historical_SD for surrounding real years if it were allowed to contribute.
2. Their own resulting `label` is always set to NaN (undefined), never 0 or
   1 - a label computed from a fabricated case count is not a real
   observation and must not be used as a Stage 1 training/scoring target.

A `(District, Week, Year)` row's label is also NaN (undefined, not 0) if
fewer than `min_prior_years` strictly-prior REAL (non-imputed) years of data
exist for that (District, Week) - mirrors `validation.py`'s
`DEFAULT_MIN_TRAIN_YEARS` philosophy of refusing to manufacture a value from
insufficient history.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    EPIDEMIC_THRESHOLD_K,
    EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
)


def compute_historical_stats(
    df: pd.DataFrame,
    min_prior_years: int = EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
) -> pd.DataFrame:
    """Return `df` with `historical_mean`/`historical_sd` columns added.

    For each row, these are computed from that row's (District, Week) group,
    using only REAL (non-`is_imputed`) observations from years strictly
    before the row's own `Year`. Implemented as
    `expanding(min_periods=...).agg().shift(1)` on a series where imputed
    values have been masked to NaN first: shifting AFTER expanding means row
    i receives the expanding statistic computed through row i-1 (i.e.
    strictly-prior rows only), and pandas' `min_periods` counts non-NaN
    observations only (verified: masked/imputed rows do not count toward
    satisfying `min_periods`, nor do they pull the mean/SD toward their own
    fabricated value).
    """
    if "is_imputed" not in df.columns:
        raise ValueError("df must have an is_imputed column (from module2_preprocessing.py).")

    df = df.sort_values(["District", "Week", "Year"]).reset_index(drop=True)
    clean_cases = df["Number_of_Cases"].where(~df["is_imputed"])

    grouped = clean_cases.groupby([df["District"], df["Week"]], sort=False)
    df["historical_mean"] = grouped.transform(
        lambda s: s.expanding(min_periods=min_prior_years).mean().shift(1)
    )
    df["historical_sd"] = grouped.transform(
        lambda s: s.expanding(min_periods=min_prior_years).std().shift(1)
    )
    return df


def compute_epidemic_threshold_labels(
    df: pd.DataFrame,
    k: float = EPIDEMIC_THRESHOLD_K,
    min_prior_years: int = EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
) -> pd.DataFrame:
    """Return `df` with `historical_mean`, `historical_sd`, `threshold`,
    `label` columns added (Decision 019).

    `label` is a nullable float in {0.0, 1.0, NaN} - NaN means "undefined"
    (insufficient prior history, or the row itself is `is_imputed`), never a
    silent default to 0. Callers (Stage 1 training/scoring code) must drop or
    explicitly handle NaN labels rather than treating them as negatives.
    """
    df = compute_historical_stats(df, min_prior_years=min_prior_years)
    df["threshold"] = df["historical_mean"] + k * df["historical_sd"]

    df["label"] = np.nan
    defined = df["threshold"].notna() & ~df["is_imputed"]
    df.loc[defined, "label"] = (
        df.loc[defined, "Number_of_Cases"] > df.loc[defined, "threshold"]
    ).astype(float)

    return df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)


if __name__ == "__main__":
    from src.config import MODULE2_WEEKLY_MODELING_TABLE_PATH

    table = pd.read_csv(MODULE2_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    labeled = compute_epidemic_threshold_labels(table)

    n_total = len(labeled)
    n_defined = int(labeled["label"].notna().sum())
    n_outbreak = int((labeled["label"] == 1.0).sum())
    print(f"Total rows: {n_total}")
    print(f"Defined labels: {n_defined} ({n_defined / n_total * 100:.1f}%)")
    print(f"Outbreak-labeled rows: {n_outbreak} ({n_outbreak / n_defined * 100:.2f}% of defined)")
