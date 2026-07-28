"""Module 2 outbreak-label STABILIZATION audit (Open Question #8, Decision 025).

Read-only diagnostic script. Does not modify any pipeline file or config.
Compares the current label estimator (`labels.compute_historical_stats`,
exact per-(District, Week), Decision 019) against two stabilized candidates
that pool more strictly-prior information to reduce small-sample noise in
the historical mean/SD estimate:

    exact_week   - CONTROL. Unchanged from Decision 019/`labels.py`.
    windowed(W)  - pool weeks in a circular [Week-W, Week+W] window (mod 52,
                   week 53 treated as adjacent to week 1) across
                   strictly-prior years.
    harmonic(H)  - per-district OLS fit of Number_of_Cases on H harmonics of
                   week-of-year (sin/cos(2*pi*Week/52), plus sin/cos(4*pi*Week/52)
                   if H=2), refit expanding per year using only that
                   district's strictly-prior-year real rows. historical_mean
                   = fitted curve; historical_sd = the fit's residual
                   standard error.

Motivation (see `module_2_classification/MODULE_CONTEXT.md` Open Question #8
and `research_context/RESEARCH_DECISIONS.md` Decision 019's methodological
caveat): the current exact-week estimator draws its mean/SD from as few as
3-15 strictly-prior years for a single week number. This is evidenced to be
noisy in BOTH directions:
  - too loose in some district-weeks: Colombo's 2025 Week 15 (277 actual
    cases, a large absolute spike) was labeled/predicted "low risk" because
    Colombo's own baseline variance is large enough that 277 isn't a big
    enough RELATIVE deviation under the noisy small-sample SD estimate.
  - too tight in others: the pooled "outbreak" rate is 18-25% of weeks,
    considerably higher than WHO/CDC-style single-digit-percent epidemic
    alert rates - consistent with the per-week SD being underestimated for
    many district-weeks and ordinary monsoon variation tripping the
    threshold.

This script does NOT change `k` selection methodology (Decision 019's
k in {1.5, 2.0, 2.5} grid is reused unchanged) - it isolates the effect of
stabilizing the mean/SD estimate itself, holding k fixed across candidates
for a fair comparison, exactly mirroring how `scripts/data_audit_module2.py`
isolated k while holding the (then-only) exact-week estimator fixed.

Output: `outputs/metrics/module2/label_stabilization_audit.csv` (long format:
candidate, parameter, k, district, prevalence, n_defined, n_undefined) plus
an explicit printed Colombo 2025 Week 15 spot-check for every
candidate/parameter/k combination.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import MODULE2_METRICS_DIR, MODULE2_WEEKLY_MODELING_TABLE_PATH  # noqa: E402
from src.module2_classification.labels import compute_historical_stats  # noqa: E402

OUTPUT_PATH = MODULE2_METRICS_DIR / "label_stabilization_audit.csv"

CANDIDATE_K_VALUES = [1.5, 2.0, 2.5]
MIN_PRIOR_YEARS = 3
WINDOW_SIZES = [1, 2, 3]
HARMONIC_ORDERS = [1, 2]
WEEKS_PER_YEAR = 52

SPOT_CHECK = {"District": "Colombo", "Year": 2025, "Week": 15}

# Same diagnostic band as scripts/data_audit_module2.py, but Open Question #8
# explicitly argues the pooled rate should end up much closer to WHO/CDC's
# single-digit-percent norm than the current 18-25% - reported alongside the
# per-district band, not used to silently reject a candidate.
DEGENERATE_LOW_PCT = 2.0
DEGENERATE_HIGH_PCT = 40.0
TARGET_POOLED_PCT_HIGH = 10.0  # informational: Open Question #8's WHO-style aspiration


def section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def load_table() -> pd.DataFrame:
    df = pd.read_csv(
        MODULE2_WEEKLY_MODELING_TABLE_PATH,
        parse_dates=["Week_Start_Date", "Week_End_Date"],
    )
    return df.sort_values(["District", "Week", "Year"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Candidate 1: exact_week (control) - reuse labels.py's official function
# ---------------------------------------------------------------------------

def stats_exact_week(df: pd.DataFrame, min_prior_years: int = MIN_PRIOR_YEARS) -> pd.DataFrame:
    return compute_historical_stats(df, min_prior_years=min_prior_years)


# ---------------------------------------------------------------------------
# Candidate 2: windowed - circular week-window pooling across strictly-prior
# years. Implemented per-district via an explicit prior-years loop (not a
# vectorized expanding/shift trick like the exact-week estimator) because the
# pooling set for row i is no longer just "the same group's earlier rows" -
# it is "rows from OTHER week groups too, but still only earlier years" -
# expanding().shift() cannot express this directly.
# ---------------------------------------------------------------------------

def _circular_week_distance(week_a: np.ndarray, week_b: int, weeks_per_year: int = WEEKS_PER_YEAR) -> np.ndarray:
    """Circular distance between `week_a` (array, may include 53) and a
    single reference `week_b`, on a `weeks_per_year`-week ring. Week 53 is
    mapped to week 1's position (consistent with sin_week/cos_week's
    existing periodicity treatment, Decision 020) before computing distance.
    """
    a = np.where(week_a == weeks_per_year + 1, 1, week_a).astype(float)
    b = weeks_per_year + 1 if week_b == weeks_per_year + 1 else week_b
    raw = np.abs(a - b)
    return np.minimum(raw, weeks_per_year - raw)


def stats_windowed(df: pd.DataFrame, window: int, min_prior_years: int = MIN_PRIOR_YEARS) -> pd.DataFrame:
    """Return `df` with `historical_mean`/`historical_sd` computed by pooling
    real (non-`is_imputed`) case counts from weeks within a circular
    `+/- window` band of each row's own Week, drawn from strictly-prior years
    only for that row's District.
    """
    df = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    clean_cases = df["Number_of_Cases"].where(~df["is_imputed"])
    working = df[["District", "Year", "Week"]].copy()
    working["_clean_cases"] = clean_cases

    means = np.full(len(df), np.nan)
    sds = np.full(len(df), np.nan)

    for district, dist_idx in df.groupby("District").groups.items():
        dist_idx = np.asarray(dist_idx)
        dist_years = df.loc[dist_idx, "Year"].to_numpy()
        dist_weeks = df.loc[dist_idx, "Week"].to_numpy()
        dist_cases = clean_cases.loc[dist_idx].to_numpy()

        for pos in range(len(dist_idx)):
            row_year = dist_years[pos]
            row_week = dist_weeks[pos]
            prior_mask = dist_years < row_year
            if not prior_mask.any():
                continue
            week_mask = _circular_week_distance(dist_weeks, row_week) <= window
            pool_mask = prior_mask & week_mask
            pooled_years = np.unique(dist_years[pool_mask & ~np.isnan(dist_cases)])
            if len(pooled_years) < min_prior_years:
                continue
            pooled_values = dist_cases[pool_mask]
            pooled_values = pooled_values[~np.isnan(pooled_values)]
            if len(pooled_values) < min_prior_years:
                continue
            means[dist_idx[pos]] = np.mean(pooled_values)
            sds[dist_idx[pos]] = np.std(pooled_values, ddof=1) if len(pooled_values) > 1 else np.nan

    out = df.copy()
    out["historical_mean"] = means
    out["historical_sd"] = sds
    return out


# ---------------------------------------------------------------------------
# Candidate 3: harmonic - per-district, per-year expanding OLS fit of
# Number_of_Cases on `n_harmonics` sin/cos harmonics of week-of-year, using
# only that district's strictly-prior-year real rows. historical_mean = the
# fitted curve evaluated at the row's own Week; historical_sd = the fit's
# residual standard error (same value applied to every week of that
# district-year, unlike windowed/exact_week's per-week SD).
# ---------------------------------------------------------------------------

def _harmonic_design(weeks: np.ndarray, n_harmonics: int, weeks_per_year: int = WEEKS_PER_YEAR) -> np.ndarray:
    cols = [np.ones_like(weeks, dtype=float)]
    for h in range(1, n_harmonics + 1):
        angle = 2 * np.pi * h * weeks / weeks_per_year
        cols.append(np.sin(angle))
        cols.append(np.cos(angle))
    return np.column_stack(cols)


def stats_harmonic(df: pd.DataFrame, n_harmonics: int, min_prior_years: int = MIN_PRIOR_YEARS) -> pd.DataFrame:
    df = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    clean_cases = df["Number_of_Cases"].where(~df["is_imputed"])

    means = np.full(len(df), np.nan)
    sds = np.full(len(df), np.nan)
    n_params = 2 * n_harmonics + 1

    for district, dist_idx in df.groupby("District").groups.items():
        dist_idx = np.asarray(dist_idx)
        dist_years = df.loc[dist_idx, "Year"].to_numpy()
        dist_weeks = df.loc[dist_idx, "Week"].to_numpy()
        dist_cases = clean_cases.loc[dist_idx].to_numpy()

        distinct_years = np.unique(dist_years)
        for row_year in distinct_years:
            prior_mask = (dist_years < row_year) & ~np.isnan(dist_cases)
            prior_years_available = np.unique(dist_years[(dist_years < row_year)])
            if len(prior_years_available) < min_prior_years or prior_mask.sum() < n_params + 1:
                continue

            X_train = _harmonic_design(dist_weeks[prior_mask], n_harmonics)
            y_train = dist_cases[prior_mask]
            coeffs, _, _, _ = np.linalg.lstsq(X_train, y_train, rcond=None)
            fitted = X_train @ coeffs
            residuals = y_train - fitted
            dof = max(len(y_train) - n_params, 1)
            residual_sd = float(np.sqrt(np.sum(residuals ** 2) / dof))

            target_mask = dist_years == row_year
            X_target = _harmonic_design(dist_weeks[target_mask], n_harmonics)
            predicted = X_target @ coeffs
            target_idx = dist_idx[target_mask]
            means[target_idx] = predicted
            sds[target_idx] = residual_sd

    out = df.copy()
    out["historical_mean"] = means
    out["historical_sd"] = sds
    return out


# ---------------------------------------------------------------------------
# Shared: threshold + label + summary, given a stats dataframe and k
# ---------------------------------------------------------------------------

def apply_threshold(stats_df: pd.DataFrame, k: float) -> pd.DataFrame:
    out = stats_df.copy()
    out["threshold"] = out["historical_mean"] + k * out["historical_sd"]
    out["label"] = np.nan
    defined = out["threshold"].notna() & ~out["is_imputed"]
    out.loc[defined, "label"] = (out.loc[defined, "Number_of_Cases"] > out.loc[defined, "threshold"]).astype(float)
    return out


def summarize(labeled: pd.DataFrame, candidate: str, parameter, k: float) -> pd.DataFrame:
    total_rows = len(labeled)
    defined_mask = labeled["label"].notna()
    n_defined = int(defined_mask.sum())
    n_undefined = total_rows - n_defined
    pooled_pct = labeled.loc[defined_mask, "label"].mean() * 100 if n_defined else float("nan")

    per_district = (
        labeled.groupby("District")
        .apply(
            lambda g: pd.Series(
                {
                    "n_rows": len(g),
                    "n_defined": int(g["label"].notna().sum()),
                    "outbreak_pct": (
                        g.loc[g["label"].notna(), "label"].mean() * 100
                        if g["label"].notna().any()
                        else float("nan")
                    ),
                }
            ),
            include_groups=False,
        )
        .reset_index()
    )
    per_district["candidate"] = candidate
    per_district["parameter"] = parameter
    per_district["k"] = k
    per_district["pooled_outbreak_pct"] = pooled_pct
    per_district["pooled_n_defined"] = n_defined
    per_district["pooled_n_undefined"] = n_undefined
    per_district["pooled_pct_undefined"] = n_undefined / total_rows * 100

    degenerate = per_district[
        (per_district["outbreak_pct"] < DEGENERATE_LOW_PCT) | (per_district["outbreak_pct"] > DEGENERATE_HIGH_PCT)
    ]
    print(
        f"[{candidate:<10} param={str(parameter):<4} k={k}] pooled={pooled_pct:5.2f}%  "
        f"undefined={n_undefined / total_rows * 100:5.2f}%  "
        f"degenerate_districts={len(degenerate)}"
        + (f" ({', '.join(degenerate['District'])})" if len(degenerate) else "")
    )
    return per_district


def spot_check(labeled: pd.DataFrame, candidate: str, parameter, k: float) -> dict:
    row = labeled[
        (labeled["District"] == SPOT_CHECK["District"])
        & (labeled["Year"] == SPOT_CHECK["Year"])
        & (labeled["Week"] == SPOT_CHECK["Week"])
    ]
    if row.empty:
        return {}
    row = row.iloc[0]
    result = {
        "candidate": candidate,
        "parameter": parameter,
        "k": k,
        "Number_of_Cases": row["Number_of_Cases"],
        "historical_mean": row["historical_mean"],
        "historical_sd": row["historical_sd"],
        "threshold": row["threshold"],
        "label": row["label"],
    }
    flag = "OUTBREAK (fixed!)" if result["label"] == 1.0 else ("still MISSED" if result["label"] == 0.0 else "UNDEFINED")
    print(
        f"  Colombo 2025 Wk15 [{candidate:<10} param={str(parameter):<4} k={k}]: "
        f"cases=277, mean={result['historical_mean']:.1f}, sd={result['historical_sd']:.1f}, "
        f"threshold={result['threshold']:.1f} -> {flag}"
    )
    return result


def main() -> None:
    df = load_table()
    section("MODULE 2 LABEL STABILIZATION AUDIT (Open Question #8, Decision 025)")
    print(f"Source: {MODULE2_WEEKLY_MODELING_TABLE_PATH}")
    print(f"Rows: {len(df)}, Districts: {df['District'].nunique()}")
    print(f"Candidate k values: {CANDIDATE_K_VALUES}")
    print(f"Window sizes tested: {WINDOW_SIZES}; harmonic orders tested: {HARMONIC_ORDERS}")

    candidates: list[tuple[str, object, pd.DataFrame]] = []

    section("Computing candidate historical-stats estimators (k-independent)")
    print("exact_week (control)...")
    candidates.append(("exact_week", "-", stats_exact_week(df)))
    for w in WINDOW_SIZES:
        print(f"windowed(window={w})...")
        candidates.append((f"windowed", w, stats_windowed(df, window=w)))
    for h in HARMONIC_ORDERS:
        print(f"harmonic(n_harmonics={h})...")
        candidates.append((f"harmonic", h, stats_harmonic(df, n_harmonics=h)))

    section("PER-CANDIDATE / PER-k SUMMARY")
    all_summaries = []
    for candidate, parameter, stats_df in candidates:
        for k in CANDIDATE_K_VALUES:
            labeled = apply_threshold(stats_df, k)
            all_summaries.append(summarize(labeled, candidate, parameter, k))

    section(f"COLOMBO {SPOT_CHECK['Year']} WEEK {SPOT_CHECK['Week']} SPOT-CHECK (actual = 277 cases)")
    spot_rows = []
    for candidate, parameter, stats_df in candidates:
        for k in CANDIDATE_K_VALUES:
            labeled = apply_threshold(stats_df, k)
            result = spot_check(labeled, candidate, parameter, k)
            if result:
                spot_rows.append(result)

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(all_summaries, ignore_index=True)
    combined.to_csv(OUTPUT_PATH, index=False)

    spot_check_path = MODULE2_METRICS_DIR / "label_stabilization_spot_check.csv"
    pd.DataFrame(spot_rows).to_csv(spot_check_path, index=False)

    section("DONE")
    print(f"Per-candidate/parameter/k/district summary written to {OUTPUT_PATH}")
    print(f"Colombo 2025 Wk15 spot-check written to {spot_check_path}")


if __name__ == "__main__":
    main()
