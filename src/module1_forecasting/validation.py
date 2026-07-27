"""Module 1 walk-forward validation harness.

Implements Decisions 009/010 (`research_context/RESEARCH_DECISIONS.md`) as
small, reusable, hard-to-misuse functions:

- Decision 009: reserve the final ~2 years (104 weeks) per district as a
  held-out test block, untouched until final reporting; use expanding-window
  walk-forward validation (annual folds) on the remaining history.
- Decision 010: any Stage 1/Stage 2 fitting code must only ever see data up
  to its fold's cutoff - never the full raw series.

The API is deliberately structured so that "seeing the whole series" is
awkward: callers get index/label pairs from `generate_walk_forward_folds`
and must go through `fit_window` (or the `iter_walk_forward_windows`
convenience wrapper) to materialize a training slice, rather than being
handed `district_series` directly.

Out of scope this session: the actual SARIMA/XGBoost fitting code
(`baseline_sarima.py`, `compensation_model.py`) that will consume these
folds - only the fold-generation infrastructure is built here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import DISTRICTS  # noqa: E402

DEFAULT_WEEKS_PER_YEAR = 52
DEFAULT_HOLDOUT_YEARS = 2
DEFAULT_MIN_TRAIN_YEARS = 3


def get_district_series(
    df: pd.DataFrame, district: str, value_col: str = "Number_of_Cases"
) -> pd.Series:
    """Extract one district's chronologically-ordered series from the Module
    1 weekly modeling table, indexed by a stable (Year, Week) key.

    Per Decision 002, SARIMA is fit separately per district - this is the
    standard entry point for turning the multi-district table into a single
    district's series before generating folds.
    """
    district_df = df[df["District"] == district].sort_values(["Year", "Week"])
    if district_df.empty:
        raise ValueError(f"No rows found for district '{district}'.")

    index = pd.MultiIndex.from_frame(district_df[["Year", "Week"]], names=["Year", "Week"])
    return pd.Series(district_df[value_col].to_numpy(), index=index, name=value_col)


def fit_window(series: pd.Series, up_to_index) -> pd.Series:
    """Return the slice of `series` usable for fitting a model whose
    forecast origin is `up_to_index` (inclusive).

    This is the ONLY sanctioned way for Stage 1/Stage 2 fitting code to
    access historical data for a given fold (Decision 010). It structurally
    prevents accidentally handing a model the full raw series - and
    therefore the validation/holdout period - by construction: callers only
    ever get data up to a cutoff, never the series itself.
    """
    return series.loc[:up_to_index]


def get_holdout_series(
    series: pd.Series,
    holdout_years: int = DEFAULT_HOLDOUT_YEARS,
    weeks_per_year: int = DEFAULT_WEEKS_PER_YEAR,
) -> pd.Series:
    """Return the final held-out block (Decision 009) - reserved for FINAL
    reporting only. Must never be touched during fold generation, SARIMA
    order selection, or XGBoost hyperparameter tuning.
    """
    holdout_size = holdout_years * weeks_per_year
    if holdout_size >= len(series):
        raise ValueError(
            f"Holdout window ({holdout_size} weeks) is not smaller than the "
            f"series itself ({len(series)} weeks)."
        )
    return series.iloc[-holdout_size:]


def generate_walk_forward_folds(
    district_series: pd.Series,
    holdout_years: int = DEFAULT_HOLDOUT_YEARS,
    step: str = "year",
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    weeks_per_year: int = DEFAULT_WEEKS_PER_YEAR,
) -> Iterator[tuple[pd.Index, pd.Index]]:
    """Yield (train_index, val_index) label-pairs for expanding-window
    walk-forward validation on a single district's ordered weekly series.

    Implements Decisions 009/010: the final `holdout_years` years
    (`holdout_years * weeks_per_year` weeks, 104 by default) are NEVER
    returned in any fold - they are reserved untouched for final reporting
    only. Folds step forward by `step` (currently only "year" is supported)
    over the remaining history, expanding the training window each time.

    `min_train_years` guards against an unreasonably small initial training
    window for a 52-period-seasonal SARIMA model (a single seasonal cycle is
    not enough to estimate seasonal structure reliably).

    Yields index LABELS (not raw data) - use `fit_window`/`get_holdout_series`
    to materialize the corresponding series slices.
    """
    if step != "year":
        raise NotImplementedError("Only step='year' walk-forward folds are currently supported.")

    n = len(district_series)
    holdout_size = holdout_years * weeks_per_year
    min_train_size = min_train_years * weeks_per_year
    usable_n = n - holdout_size

    if usable_n <= min_train_size:
        raise ValueError(
            f"Series too short ({n} weeks) to reserve a {holdout_size}-week "
            f"holdout AND a {min_train_size}-week minimum training window "
            f"(only {usable_n} weeks would remain)."
        )

    index = district_series.index
    train_end = min_train_size
    while train_end + weeks_per_year <= usable_n:
        train_index = index[:train_end]
        val_index = index[train_end: train_end + weeks_per_year]
        yield train_index, val_index
        train_end += weeks_per_year


def iter_walk_forward_windows(
    series: pd.Series,
    holdout_years: int = DEFAULT_HOLDOUT_YEARS,
    min_train_years: int = DEFAULT_MIN_TRAIN_YEARS,
    weeks_per_year: int = DEFAULT_WEEKS_PER_YEAR,
) -> Iterator[tuple[pd.Series, pd.Series]]:
    """Convenience wrapper combining `generate_walk_forward_folds` and
    `fit_window`: yields (train_series, val_series) pairs directly, so
    calling code never needs - and is never given - the raw series itself,
    only the appropriately-windowed data for its own fold.
    """
    for train_index, val_index in generate_walk_forward_folds(
        series,
        holdout_years=holdout_years,
        min_train_years=min_train_years,
        weeks_per_year=weeks_per_year,
    ):
        train_series = fit_window(series, train_index[-1])
        val_series = series.loc[val_index]
        yield train_series, val_series


def generate_walk_forward_folds_by_district(
    df: pd.DataFrame,
    districts: list[str] = DISTRICTS,
    value_col: str = "Number_of_Cases",
    **fold_kwargs,
) -> Iterator[tuple[str, pd.Index, pd.Index]]:
    """Convenience wrapper over `generate_walk_forward_folds` that iterates
    every district (Decision 002: SARIMA is fit per district, not pooled).
    Yields (district, train_index, val_index).
    """
    for district in districts:
        series = get_district_series(df, district, value_col=value_col)
        for train_index, val_index in generate_walk_forward_folds(series, **fold_kwargs):
            yield district, train_index, val_index
