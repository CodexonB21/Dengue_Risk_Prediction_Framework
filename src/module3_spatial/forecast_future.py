"""Stage 1+2 - Forward operational hotspot forecast beyond the last reported
case-count week.

**Cross-module, operational tier - see RESEARCH_DECISIONS.md Decision 052.**
(UPDATED 2026-08-10: this module's docstring and `MODULE_CONTEXT.md`
previously mis-cited "Decision 031" here, which is actually an unrelated
Module 1 decision - Decision 052 is the correct, backfilled entry.) This
reverses `MODULE_CONTEXT.md`'s 2026-07-30 "deliberately out of scope" note,
which correctly identified that a future-week map needs Module 1's
forecasts fed in as a hypothetical input. That is exactly what this script
does - it does NOT retrain, refit, or reconverge anything; it applies the
already-committed Stage 1 kernel/Stage 2 final model once to a new,
synthesized week.

Only READS `data/processed/module1/future_forecast.csv` - never edits
anything under `module_1_forecasting/`/`src/module1_forecasting/`, per
Module 3's own scope rule.

## Why this differs from Module 1/2's forward-forecast scripts in one
## important way: climate is NOT actually a forecast here

Module 1/2's forward scores genuinely need Open-Meteo's Forecast API for
future weeks, because their forward horizon reaches into calendar dates
that have not happened yet. Module 3's case-count reporting lags the real
calendar by several weeks (the last real case week, 2026 Wk25, maps to
calendar dates 2026-06-15 to 2026-06-21 - a date range that has already
passed in real time by the time this script runs). Verified directly:
every raw daily Open-Meteo row for the next epi-week's date range
(2026-06-22 to 2026-06-28) is tagged `climate_data_source="observed"`, not
"forecast". So the forecast week's CLIMATE is real, already-observed data -
only the CASE COUNT (this week hasn't been reported yet) is a genuine
forecast, sourced from Module 1's `future_forecast.csv`. Both facts are
recorded per-row (`climate_source`, `cases_source`) rather than assumed.

## Why the shared weekly climate table can't be read directly for this week

`data/processed/shared/climate_weekly.csv` is aggregated using
`src/preprocessing/shared.py::aggregate_climate_weekly`, which buckets raw
daily weather into epi-weeks via the epi-week CALENDAR
(`epi_week_calendar.csv`) - itself built only from weeks that have a real
case-count row (`build_epi_week_calendar`). The calendar has no entry yet
for the forecast week (no case row exists for it yet), so the shared
weekly table has no row for it either, even though the raw daily weather
underlying it already exists. Rather than editing `shared.py` (a shared
file - out of scope to edit without confirmation, and the fix would need
to reason about calendar rollover for weeks with no case data at all,
which is a bigger change than this forecast needs), this script computes
ONLY the forecast week's raw current-value aggregate directly from the
already-committed `sum`/`mean` convention (`aggregate_climate_weekly`'s own
statistic choice for `rain_sum (mm)`/`temperature_2m_mean (°C)`) - the
lag_2/3/4 features reach back into weeks already present in the refreshed
`climate_weekly.csv` and need no special handling.

## Method, per forecast step (horizon defaults to 1 - "next week")

1. Determine the forecast week's (Year, Week, Week_Start_Date) as exactly
   7 days beyond the last calendar week (no week-53 handling, consistent
   with Module 3's existing stance of not inheriting Module 1's week-53
   logic).
2. Aggregate that week's raw daily weather per district (sum/mean, same
   statistic `shared.py` uses) directly from `data/raw/weather/`.
3. Extend the historical feature table with the forecast row(s) and reuse
   `feature_engineering.py`'s existing, already-tested
   `compute_lag_features`/`compute_monsoon_dummies`/
   `compute_population_density` unchanged. Climate anomaly is computed
   separately (not via `compute_climate_anomaly` directly) so the
   historical per-(District, Week) mean is fit on historical rows ONLY -
   including the forecast row in that mean would shift it slightly,
   mirroring the same historical-norms-only precaution Module 1's own
   `forecast_future.py::_compute_climate_norms` already takes.
4. Mahalanobis score reuses the PERSISTED training-time mean/covariance
   (`MODULE3_MAHALANOBIS_STATS_PATH`, written by
   `feature_engineering.py::run_feature_engineering`) rather than
   refitting on a historical-plus-one-new-row sample.
5. Stage 1: the forecast week's KDE_baseline is computed via the SAME
   fixed 25x25 Silverman kernel (`kde_baseline.py`, geography-only, not
   refit) applied to Module 1's forecasted per-district case counts as the
   weight vector, then mass-conserved to sum to the forecast week's total
   forecast case count - the direct forecast-week analogue of
   `compensation_model.py::rescale_kde_baseline`.
6. Stage 2: the already-trained final production RF
   (`MODULE3_RF_FINAL_MODEL_PATH`, all 25 districts, not a fold model)
   scores `predicted_residual` for the forecast row(s).
7. Combine once: `Risk_forecast = Risk_0_forecast + SHRINKAGE_ALPHA *
   predicted_residual` - the same already-decided formula
   (`iterative_loop.py`), applied a single time. Not a new multi-iteration
   loop: M3-004 already established this dataset converges at iteration 1,
   so one application is the honest operational equivalent of that already
   -validated result, not a new convergence claim.

Any remaining NaN in a required feature after all of the above raises an
explicit error naming the field/district rather than silently guessing -
unlike Module 1's XGBoost, Module 3's Stage 2 model is a bare
`sklearn.RandomForestRegressor` with no native NaN tolerance.

Outputs `data/processed/module3/future_hotspot_forecast.csv`, every row
tagged `evidence_tier="operational"` (never to be cited alongside the
Moran's I / spatial-CV holdout figures in `results_summary.txt`).

## Prospective accuracy tracking (added 2026-08-10, Decision 052/M3-016)

Every call also appends its forecast row(s) to a permanent log via
`hotspot_tracking.append_to_hotspot_log()` (pass `log_prediction=False` to
suppress this for ad hoc/exploratory runs). `hotspot_tracking.py`'s own
module docstring explains how the log is later reconciled against real
outcomes, mirroring Module 1's nowcast tracker (Decision 041/M1-017) and
Module 2's forward-risk tracker (Decision 048/M2-015) - this closes the
same gap for Module 3.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE1_FUTURE_FORECAST_PATH,
    MODULE3_BASELINE_RISK_PATH,
    MODULE3_FIGURES_DIR,
    MODULE3_FUTURE_HOTSPOT_FORECAST_PATH,
    MODULE3_MAHALANOBIS_STATS_PATH,
    MODULE3_MASTER_TABLE_PATH,
    MODULE3_PROCESSED_DIR,
    MODULE3_RF_FINAL_MODEL_PATH,
    RAW_WEATHER_DIR,
    SHARED_EPI_WEEK_CALENDAR_PATH,
)
from src.module3_spatial.compensation_model import (
    RELATIVE_LAG_COLUMNS,
    RESIDUAL_LAG_COLUMNS,
    STAGE2_FEATURE_COLUMNS_V2,
    add_residual_lag_features,
    rescale_kde_baseline,
)
from src.module3_spatial.feature_engineering import (
    LAG_SOURCE_COLUMNS,
    LAG_WEEKS,
    apply_mahalanobis_scores,
    compute_lag_features,
    compute_monsoon_dummies,
    compute_population_density,
)
from src.module3_spatial.hotspot_tracking import append_to_hotspot_log
from src.module3_spatial.iterative_loop import SHRINKAGE_ALPHA
from src.module3_spatial.kde_baseline import (
    build_kernel_matrix,
    district_centroid_coords,
    load_district_boundaries,
    silverman_covariance,
)
from src.module3_spatial.risk_surface import (
    DEFAULT_RESOLUTION_M,
    build_evaluation_grid,
    evaluate_risk_surface,
    plot_risk_surface,
)
from src.preprocessing.shared import district_from_weather_filename, load_weather_file

logger = logging.getLogger(__name__)

DEFAULT_HORIZON_WEEKS = 1
WEEKS_PER_YEAR = 52  # Module 3 does not handle week-53, per existing precedent.

RAIN_COL = "rain_sum (mm)"
TEMP_COL = "temperature_2m_mean (°C)"
EVIDENCE_TIER = "operational"


# ---------------------------------------------------------------------------
# Step 1: forecast-week calendar (7 days beyond the last known epi-week)
# ---------------------------------------------------------------------------

def _next_epi_week(year: int, week: int) -> tuple[int, int]:
    if week >= WEEKS_PER_YEAR:
        return year + 1, 1
    return year, week + 1


def forecast_week_calendar(horizon: int = DEFAULT_HORIZON_WEEKS) -> pd.DataFrame:
    """(Year, Week, Week_Start_Date, Week_End_Date) for each of the next
    `horizon` weeks beyond the last row of the shared epi-week calendar -
    NOT the last row of `master_table.csv`, since that table already drops
    rows outside climate coverage and could under-count how far the real
    case-count series extends."""
    calendar = pd.read_csv(
        SHARED_EPI_WEEK_CALENDAR_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    ).sort_values(["Year", "Week"])
    last = calendar.iloc[-1]
    year, week = int(last["Year"]), int(last["Week"])
    week_end = last["Week_End_Date"]

    rows = []
    for step in range(1, horizon + 1):
        year, week = _next_epi_week(year, week)
        week_start = week_end + pd.Timedelta(days=1)
        week_end = week_start + pd.Timedelta(days=6)
        rows.append(
            {"horizon_step": step, "Year": year, "Week": week, "Week_Start_Date": week_start, "Week_End_Date": week_end}
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Step 2: forecast-week raw climate (real observed data - see module
# docstring for why this is not a meteorological forecast at all)
# ---------------------------------------------------------------------------

def aggregate_forecast_week_climate(week_start: pd.Timestamp, week_end: pd.Timestamp) -> pd.DataFrame:
    """Sum `rain_sum (mm)` / mean `temperature_2m_mean (°C)` per district over
    [week_start, week_end] directly from the raw daily Open-Meteo CSVs - the
    same two statistics `shared.py::aggregate_climate_weekly` uses for these
    columns, just computed for one week the shared calendar doesn't have an
    entry for yet."""
    files = sorted(RAW_WEATHER_DIR.glob("open-meteo-*.csv"))
    if len(files) != len(DISTRICTS):
        raise ValueError(f"Expected {len(DISTRICTS)} weather files, found {len(files)}")

    records = []
    for f in files:
        district = district_from_weather_filename(f)
        daily = load_weather_file(f)
        window = daily[(daily["time"] >= week_start) & (daily["time"] <= week_end)]
        if window.empty:
            raise ValueError(
                f"No raw daily weather rows for {district} in [{week_start.date()}, "
                f"{week_end.date()}] - the raw Open-Meteo CSVs may need refreshing "
                f"(scripts/fetch_open_meteo_weather.py) before this forecast can run."
            )
        source = (
            window["climate_data_source"].mode().iloc[0]
            if "climate_data_source" in window.columns and not window["climate_data_source"].mode().empty
            else "observed"
        )
        records.append(
            {
                "District": district,
                RAIN_COL: window[RAIN_COL].sum(),
                TEMP_COL: window[TEMP_COL].mean(),
                "climate_source": source,
            }
        )
    return pd.DataFrame(records)


# ---------------------------------------------------------------------------
# Step 3: assemble the forecast row(s)' 16 Stage 2 features
# ---------------------------------------------------------------------------

def build_forecast_feature_table(calendar_row: pd.Series) -> pd.DataFrame:
    """One row per district for a single forecast week, with every
    `STAGE2_FEATURE_COLUMNS` column populated (the original 16 plus the
    M3-008 residual lags).

    NOTE: each call reads `historical` fresh from `master_table.csv` and
    does not chain in any OTHER forecast week's own output as pseudo-history
    - correct for `DEFAULT_HORIZON_WEEKS=1` ("next week"). If `horizon` is
    ever raised above 1, a horizon_step>=2 row's lag_2/3/4 features would be
    missing the intervening forecast week(s) as history (a real, not-yet-
    implemented gap, unlike Module 1's `forecast_future.py` which explicitly
    recurses its own prior predictions forward) - not a silent bug, but
    flagged here since only the horizon=1 case has been exercised/verified.
    """
    year, week = int(calendar_row["Year"]), int(calendar_row["Week"])
    week_start, week_end = calendar_row["Week_Start_Date"], calendar_row["Week_End_Date"]

    historical = pd.read_csv(MODULE3_MASTER_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    historical = historical.dropna(subset=[RAIN_COL]).reset_index(drop=True)

    climate_now = aggregate_forecast_week_climate(week_start, week_end)

    static_cols = historical.sort_values(["District", "Year"]).groupby("District").tail(1)
    static_cols = static_cols[["District", "elevation_m"]]

    pop_this_year = (
        historical.loc[historical["Year"] == year, ["District", "Estimated_Population"]]
        .drop_duplicates(subset="District")
    )
    if len(pop_this_year) < len(DISTRICTS):
        pop_this_year = (
            historical.sort_values(["District", "Year"]).groupby("District").tail(1)[["District", "Estimated_Population"]]
        )

    forecast_row = climate_now.merge(static_cols, on="District", how="left").merge(
        pop_this_year, on="District", how="left"
    )
    forecast_row["Year"] = year
    forecast_row["Week"] = week
    forecast_row["Week_Start_Date"] = week_start
    forecast_row["Number_of_Cases"] = np.nan

    missing = forecast_row[["elevation_m", "Estimated_Population"]].isna().any(axis=1)
    if missing.any():
        raise ValueError(
            f"Missing static elevation/population for districts: "
            f"{forecast_row.loc[missing, 'District'].tolist()}"
        )

    # --- Lags: reuse compute_lag_features unchanged on history + this row ---
    work_cols = ["District", "Year", "Week", "Week_Start_Date", RAIN_COL, TEMP_COL]
    combined = pd.concat([historical[work_cols], forecast_row[work_cols]], ignore_index=True)
    combined = compute_lag_features(combined)
    lag_cols = [f"{label}_lag_{lag}" for label in LAG_SOURCE_COLUMNS.values() for lag in LAG_WEEKS]
    forecast_lags = combined.loc[combined["Week_Start_Date"] == week_start, ["District"] + lag_cols]

    result = forecast_row.merge(forecast_lags, on="District", how="left")

    # --- Residual lags (STAGE2_FEATURE_COLUMNS, M3-008): real historical
    # residual_rescaled, computed from real reported Number_of_Cases and
    # Stage 1's already-committed KDE_baseline (baseline_risk.csv) - NOT
    # recomputed relative to any forecast value. Lag_1..4 always look
    # strictly backward into already-reported weeks, even at horizon_step=1.
    baseline_hist = pd.read_csv(MODULE3_BASELINE_RISK_PATH)[["District", "Year", "Week", "KDE_baseline"]]
    residual_hist = historical[["District", "Year", "Week", "Week_Start_Date", "Number_of_Cases"]].merge(
        baseline_hist, on=["District", "Year", "Week"], how="inner"
    )
    residual_hist = rescale_kde_baseline(residual_hist)[
        ["District", "Year", "Week", "Week_Start_Date", "residual_rescaled", "kde_baseline_rescaled"]
    ]

    forecast_resid_row = forecast_row[["District", "Year", "Week", "Week_Start_Date"]].copy()
    forecast_resid_row["residual_rescaled"] = np.nan
    forecast_resid_row["kde_baseline_rescaled"] = np.nan
    combined_resid = pd.concat([residual_hist, forecast_resid_row], ignore_index=True)
    combined_resid = add_residual_lag_features(combined_resid)
    forecast_resid_lags = combined_resid.loc[
        combined_resid["Week_Start_Date"] == week_start,
        ["District"] + RESIDUAL_LAG_COLUMNS + RELATIVE_LAG_COLUMNS,
    ]
    result = result.merge(forecast_resid_lags, on="District", how="left")

    # --- Climate anomaly: historical-only per-(District, Week) mean, NOT
    # recomputed with the forecast row included (see module docstring) ---
    historical_norms = historical.groupby(["District", "Week"])[[RAIN_COL, TEMP_COL]].mean()
    for source_col, label in LAG_SOURCE_COLUMNS.items():
        norm = historical_norms[source_col].reindex(
            pd.MultiIndex.from_arrays([result["District"], [week] * len(result)])
        ).to_numpy()
        result[f"{label}_anomaly"] = result[source_col].to_numpy() - norm

    result = compute_monsoon_dummies(result)
    result = compute_population_density(result)

    mahalanobis_stats = joblib.load(MODULE3_MAHALANOBIS_STATS_PATH)
    result = apply_mahalanobis_scores(result, mahalanobis_stats["mean"], mahalanobis_stats["cov"])

    nan_features = result[STAGE2_FEATURE_COLUMNS_V2].isna().any(axis=0)
    if nan_features.any():
        bad_cols = nan_features[nan_features].index.tolist()
        raise ValueError(
            f"Forecast feature table has NaN in required columns {bad_cols} for "
            f"Year={year} Week={week} - refresh the raw weather "
            f"(scripts/fetch_open_meteo_weather.py) and rerun "
            f"src.preprocessing.module3_preprocessing before retrying."
        )

    result["feature_completeness_pct"] = 100.0
    return result


# ---------------------------------------------------------------------------
# Step 4: Stage 1 forecast-week KDE (Module 1's forecast cases as weights)
# ---------------------------------------------------------------------------

def forecast_week_kde(case_count_weights: pd.Series) -> pd.Series:
    """Raw KDE_baseline for one forecast week, using the SAME fixed 25x25
    Silverman kernel `kde_baseline.py` already validated (not refit) applied
    to `case_count_weights` (Module 1's forecasted per-district case counts,
    in DISTRICTS order) instead of a real, reported Number_of_Cases vector -
    the forecast-week analogue of `compute_kde_baseline`'s per-week matrix
    multiply."""
    boundaries = load_district_boundaries()
    coords = district_centroid_coords(boundaries)
    covariance = silverman_covariance(coords)
    kernel = build_kernel_matrix(coords, covariance)

    weights = case_count_weights.reindex(DISTRICTS).to_numpy(dtype=float)
    if np.isnan(weights).any():
        raise ValueError("case_count_weights missing districts after reindexing to DISTRICTS order.")

    kde_vector = weights @ kernel
    return pd.Series(kde_vector, index=DISTRICTS)


def rescale_forecast_kde(kde_vector: pd.Series, forecast_total_cases: float) -> pd.Series:
    """Mass-conserve `kde_vector` to sum to `forecast_total_cases` - the
    forecast-week analogue of `compensation_model.py::rescale_kde_baseline`,
    using the forecast week's FORECASTED total (sum of Module 1's
    per-district predictions) in place of an actual reported total."""
    total_kde = kde_vector.sum()
    if total_kde <= 0:
        return pd.Series(0.0, index=kde_vector.index)
    return kde_vector * (forecast_total_cases / total_kde)


# ---------------------------------------------------------------------------
# Step 5: static figure - reuses risk_surface.py's grid/IDW functions
# unchanged (they already take a plain district_values array, decoupled
# from hybrid_risk_map.csv), so no changes to that file are needed.
# ---------------------------------------------------------------------------

def plot_forecast_risk_surface(forecast_row: pd.DataFrame, year: int, week: int) -> Path:
    """Saves to `risk_surface_forecast_{year}_wk{week}.png` - never
    `risk_surface_peak_week.png`, so this can never overwrite the canonical
    historical figure `risk_surface.py::run_risk_surface` produces."""
    MODULE3_FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    boundaries = load_district_boundaries()
    district_coords = district_centroid_coords(boundaries)
    xx, yy, mask, grid_coords = build_evaluation_grid(boundaries, DEFAULT_RESOLUTION_M)

    district_values = forecast_row.set_index("District")["Risk_forecast"].reindex(DISTRICTS).to_numpy(dtype=float)
    surface = evaluate_risk_surface(grid_coords, district_coords, district_values)

    out_path = MODULE3_FIGURES_DIR / f"risk_surface_forecast_{year}_wk{week}.png"
    plot_risk_surface(xx, yy, mask, surface, boundaries, year, week, out_path)
    logger.info("Forecast risk surface figure saved to %s.", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_forecast_future(
    horizon: int = DEFAULT_HORIZON_WEEKS, *, log_prediction: bool = True
) -> pd.DataFrame:
    """`log_prediction=True` (default, Decision 052/M3-016) appends this
    run's forecast row(s) to the permanent prospective-accuracy log
    (`hotspot_tracking.append_to_hotspot_log()`) - the only source of
    genuinely forward-checkable evidence for this forecast, mirroring
    Module 1's nowcast (Decision 041) and Module 2's forward risk
    (Decision 048). Pass `False` for ad hoc/exploratory runs that
    shouldn't pollute that record.
    """
    calendar = forecast_week_calendar(horizon)
    m1_forecast = pd.read_csv(MODULE1_FUTURE_FORECAST_PATH)
    rf_model = joblib.load(MODULE3_RF_FINAL_MODEL_PATH)

    frames = []
    for _, calendar_row in calendar.iterrows():
        step = int(calendar_row["horizon_step"])
        year, week = int(calendar_row["Year"]), int(calendar_row["Week"])

        m1_step = m1_forecast.loc[m1_forecast["horizon_step"] == step].set_index("District")
        if len(m1_step) != len(DISTRICTS):
            raise ValueError(
                f"Module 1's future_forecast.csv has no horizon_step={step} rows for all "
                f"{len(DISTRICTS)} districts - regenerate it via "
                f"src.module1_forecasting.forecast_future before retrying."
            )
        case_count_weights = m1_step["final_prediction"].reindex(DISTRICTS)

        features = build_forecast_feature_table(calendar_row)
        features = features.set_index("District").reindex(DISTRICTS).reset_index()

        X = features[STAGE2_FEATURE_COLUMNS_V2]
        # UPDATED 2026-08-08 (EXPERIMENT_LOG.md M3-015): the frozen final RF
        # now predicts the RELATIVE residual, not the absolute one -
        # reconstruction back to Risk is exact, not approximate.
        predicted_relative_residual = rf_model.predict(X)

        kde_vector = forecast_week_kde(case_count_weights)
        risk_0 = rescale_forecast_kde(kde_vector, case_count_weights.sum())

        # Clipped at 0 (case counts cannot be negative) - matches
        # iterative_loop.py's M3-008 clipping decision; alpha=1.0's
        # unshrunk correction can otherwise overshoot below 0 for
        # near-zero-risk districts.
        risk_0_values = risk_0.to_numpy()
        risk_forecast = np.clip(
            risk_0_values + SHRINKAGE_ALPHA * predicted_relative_residual * (risk_0_values + 1), 0.0, None,
        )

        out = pd.DataFrame(
            {
                "District": DISTRICTS,
                "Year": year,
                "Week": week,
                "Week_Start_Date": calendar_row["Week_Start_Date"],
                "horizon_step": step,
                "Risk_0_forecast": risk_0.to_numpy(),
                "predicted_relative_residual": predicted_relative_residual,
                "Risk_forecast": risk_forecast,
                "cases_forecast": case_count_weights.to_numpy(),
                "cases_source": "module1_forecast",
                "climate_source": features["climate_source"].to_numpy(),
                "feature_completeness_pct": features["feature_completeness_pct"].to_numpy(),
                "evidence_tier": EVIDENCE_TIER,
            }
        )
        frames.append(out)
        logger.info(
            "Forecast Year=%d Week=%d (horizon_step=%d): Risk_forecast range [%.2f, %.2f], "
            "total forecast cases=%.1f.",
            year, week, step, risk_forecast.min(), risk_forecast.max(), case_count_weights.sum(),
        )
        plot_forecast_risk_surface(out, year, week)

    result = pd.concat(frames, ignore_index=True)
    MODULE3_PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE3_FUTURE_HOTSPOT_FORECAST_PATH, index=False)
    logger.info(
        "Wrote %d forward-hotspot-forecast rows to %s.", len(result), MODULE3_FUTURE_HOTSPOT_FORECAST_PATH,
    )
    if log_prediction:
        append_to_hotspot_log(result)
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Module 3 forward hotspot forecast.")
    parser.add_argument(
        "--horizon", type=int, default=DEFAULT_HORIZON_WEEKS,
        help=f"Forward weeks to forecast. Default: {DEFAULT_HORIZON_WEEKS} (only this value is "
             "exercised/verified - see the module docstring's DEFAULT_HORIZON_WEEKS note).",
    )
    parser.add_argument(
        "--no-log", action="store_true",
        help="Skip appending to the permanent hotspot prediction log - use for ad hoc/exploratory "
             "runs that shouldn't pollute the prospective-accuracy record.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_forecast_future(horizon=args.horizon, log_prediction=not args.no_log)
