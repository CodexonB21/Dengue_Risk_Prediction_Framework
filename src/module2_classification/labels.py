"""Module 2 outbreak label definition (Decision 019; mean/SD ESTIMATOR
superseded by Decision 025 - see below).

Implements the fold-aware epidemic-threshold label:

    threshold(District, Week, Year) = historical_mean + k * historical_SD
    outbreak = 1 if Number_of_Cases > threshold else 0

where `historical_mean`/`historical_SD` for a given row are computed using
STRICTLY-PRIOR years only (an expanding window, never the full series) - this
is a genuine LABEL-leakage guard, distinct in kind from Module 1's
feature-only climate-anomaly guard (`compute_fold_climate_anomalies`):
computing this once globally would let every walk-forward fold "see" whether
later years turned out to be outbreak years relative to a mean that includes
those same later years.

**Decision 025 (2026-07-28): the mean/SD ESTIMATOR changed, the threshold
FORMULA and leakage guard did not.** Decision 019's original estimator
(`compute_historical_stats`, kept below, superseded but not deleted) computed
an exact per-(District, Week) sample mean/SD - as few as 3-15 strictly-prior
years for a single week number, evidenced (Open Question #8; `scripts/
audit_label_stabilization.py`) to be noisy enough to drive a pooled
"outbreak" rate of 18-25% of weeks, well above WHO/CDC's typical
single-digit-percent epidemic-alert rate. The new official estimator,
`compute_historical_stats_harmonic`, instead fits a smooth per-district
seasonal curve (harmonic regression on week-of-year) expanding per year on
strictly-prior real data, and uses the fit's residual standard error as
`historical_sd`. This pools information across the whole season instead of
one exact week number, directly reducing the small-sample noise. `k` was
re-audited for the new estimator (not assumed to transfer) since the SD
quantity's meaning changed - `k=3.0` is now used (was `2.0`). See Decision
025 for the full audit results, including the important negative finding
that this change does NOT fix every individual under-flagged case (e.g.
Colombo 2025 Week 15 was already correctly labeled `1` under the OLD
estimator - that case turned out to be a Stage 2 calibration near-miss, not
a label defect).

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
    EPIDEMIC_THRESHOLD_N_HARMONICS,
)

WEEKS_PER_YEAR = 52


def compute_historical_stats(
    df: pd.DataFrame,
    min_prior_years: int = EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
) -> pd.DataFrame:
    """**Superseded by `compute_historical_stats_harmonic` (Decision 025) -
    kept, not deleted, for audit/comparison** (`scripts/
    audit_label_stabilization.py` uses this as the `exact_week` control).

    Return `df` with `historical_mean`/`historical_sd` columns added.

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


def _harmonic_design(weeks: np.ndarray, n_harmonics: int, weeks_per_year: int = WEEKS_PER_YEAR) -> np.ndarray:
    """Build an OLS design matrix `[1, sin(2*pi*h*w/52), cos(2*pi*h*w/52) for
    h in 1..n_harmonics]` for a per-district seasonal curve fit. Week 53
    (Decision 020's unmerged week) is not special-cased here - it naturally
    lands adjacent to week 1's harmonic value by periodicity, same as
    `sin_week`/`cos_week` elsewhere in this project.
    """
    cols = [np.ones_like(weeks, dtype=float)]
    for h in range(1, n_harmonics + 1):
        angle = 2 * np.pi * h * weeks / weeks_per_year
        cols.append(np.sin(angle))
        cols.append(np.cos(angle))
    return np.column_stack(cols)


def compute_historical_stats_harmonic(
    df: pd.DataFrame,
    n_harmonics: int = EPIDEMIC_THRESHOLD_N_HARMONICS,
    min_prior_years: int = EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
    weeks_per_year: int = WEEKS_PER_YEAR,
) -> pd.DataFrame:
    """**Official estimator as of Decision 025.** Return `df` with
    `historical_mean`/`historical_sd` columns added, computed from a
    per-district, per-year harmonic-regression fit instead of
    `compute_historical_stats`'s exact-week sample mean/SD.

    For each `(District, Year)`, an OLS regression of `Number_of_Cases` on
    `n_harmonics` sin/cos harmonics of week-of-year is fit using ONLY that
    district's REAL (non-`is_imputed`) rows from years strictly before
    `Year` (expanding, refit each year - the same "strictly-prior-years-only"
    leakage guard as `compute_historical_stats`, just applied at an annual
    grain instead of per-row). `historical_mean` is the fitted curve
    evaluated at each row's own `Week`; `historical_sd` is the fit's
    residual standard error (`sqrt(sum(residuals**2) / dof)`) - a single
    value shared by every week of that district-year, unlike
    `compute_historical_stats`'s per-exact-week SD.

    A `(District, Year)` is left undefined (NaN mean/sd for every week of
    that year) if fewer than `min_prior_years` distinct strictly-prior real
    years exist, or if there are fewer prior observations than free
    parameters (`2 * n_harmonics + 1`) plus one degree of freedom - mirrors
    `compute_historical_stats`'s own insufficient-history guard.

    Rationale for pooling across weeks instead of one exact week number:
    Open Question #8 (`module_2_classification/MODULE_CONTEXT.md`) found the
    exact-week estimator's small per-week sample size (3-15 strictly-prior
    years) noisy enough to produce an 18-25% pooled "outbreak" rate, well
    above WHO/CDC's typical single-digit-percent epidemic-alert norm. Fitting
    one smooth seasonal curve per district-year uses ALL of that district's
    strictly-prior weeks to estimate the curve and its residual spread,
    directly addressing the small-sample-noise root cause (Decision 025).
    """
    if "is_imputed" not in df.columns:
        raise ValueError("df must have an is_imputed column (from module2_preprocessing.py).")

    df = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    clean_cases = df["Number_of_Cases"].where(~df["is_imputed"])

    means = np.full(len(df), np.nan)
    sds = np.full(len(df), np.nan)
    n_params = 2 * n_harmonics + 1

    for _district, dist_idx in df.groupby("District", sort=False).groups.items():
        dist_idx = np.asarray(dist_idx)
        dist_years = df.loc[dist_idx, "Year"].to_numpy()
        dist_weeks = df.loc[dist_idx, "Week"].to_numpy()
        dist_cases = clean_cases.loc[dist_idx].to_numpy()

        for row_year in np.unique(dist_years):
            prior_mask = (dist_years < row_year) & ~np.isnan(dist_cases)
            prior_years_available = np.unique(dist_years[dist_years < row_year])
            if len(prior_years_available) < min_prior_years or prior_mask.sum() < n_params + 1:
                continue

            X_train = _harmonic_design(dist_weeks[prior_mask], n_harmonics, weeks_per_year)
            y_train = dist_cases[prior_mask]
            coeffs, _, _, _ = np.linalg.lstsq(X_train, y_train, rcond=None)
            residuals = y_train - X_train @ coeffs
            dof = max(len(y_train) - n_params, 1)
            residual_sd = float(np.sqrt(np.sum(residuals ** 2) / dof))

            target_mask = dist_years == row_year
            X_target = _harmonic_design(dist_weeks[target_mask], n_harmonics, weeks_per_year)
            target_idx = dist_idx[target_mask]
            means[target_idx] = X_target @ coeffs
            sds[target_idx] = residual_sd

    out = df.copy()
    out["historical_mean"] = means
    out["historical_sd"] = sds
    return out


def compute_epidemic_threshold_labels(
    df: pd.DataFrame,
    k: float = EPIDEMIC_THRESHOLD_K,
    min_prior_years: int = EPIDEMIC_THRESHOLD_MIN_PRIOR_YEARS,
    n_harmonics: int = EPIDEMIC_THRESHOLD_N_HARMONICS,
) -> pd.DataFrame:
    """Return `df` with `historical_mean`, `historical_sd`, `threshold`,
    `label` columns added (threshold formula: Decision 019; mean/SD estimator:
    Decision 025).

    Uses `compute_historical_stats_harmonic` (the official estimator as of
    Decision 025) by default - NOT `compute_historical_stats` (Decision 019's
    original exact-per-week estimator, kept for audit/comparison only). The
    threshold formula and NaN-handling rules below are unchanged from
    Decision 019.

    `label` is a nullable float in {0.0, 1.0, NaN} - NaN means "undefined"
    (insufficient prior history, or the row itself is `is_imputed`), never a
    silent default to 0. Callers (Stage 1 training/scoring code) must drop or
    explicitly handle NaN labels rather than treating them as negatives.
    """
    df = compute_historical_stats_harmonic(df, n_harmonics=n_harmonics, min_prior_years=min_prior_years)
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
