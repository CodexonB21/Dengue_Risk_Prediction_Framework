"""Stage 2 - Random Forest residual compensation model (single-pass only;
the iterative convergence loop is NOT built here - future work).

IMPORTANT: KDE_baseline / Residual scale fix (Stage-2-scoped only)
-------------------------------------------------------------------
`stage2_feature_table.csv`'s `Residual` column (= `Number_of_Cases -
KDE_baseline`, as literally specified in `MODULE_CONTEXT.md`) is NOT used
as the RF training target. Verified numerically before writing this file:
`KDE_baseline`'s max value across the whole dataset is ~4.48e-7, while
`Number_of_Cases` reaches 2,631 - `corr(Residual, Number_of_Cases) =
0.9999999999999991`. Stage 1's committed `KDE_baseline` is a properly-
normalized 2D Gaussian density with a bandwidth on the order of tens/
hundreds of km, so its peak value is astronomically small; Global Moran's
I is scale-invariant, so this never surfaced during Stage 1's validation
(which remains a correct result on its own terms - only the ABSOLUTE
magnitude is unusable for a subtraction against real case counts, not the
relative spatial pattern Moran's I checked).

Fix (explicitly scoped to THIS file, per user decision - Stage 1's
`kde_baseline.py`, `baseline_risk.csv`, and the committed Moran's I = 0.70
result are untouched): `rescale_kde_baseline()` mass-conserves
`KDE_baseline` per (Year, Week) so it sums to that week's actual total
case count across districts - preserving the KDE surface's spatial
redistribution SHAPE while making it comparable in scale to
`Number_of_Cases`. `residual_rescaled = Number_of_Cases -
kde_baseline_rescaled` is the actual RF target. Verified this produces a
genuine residual: mean ~0, `corr(residual_rescaled, Number_of_Cases)`
drops from 0.9999999 to 0.678 (KDE now explains real variance instead of
being numerically invisible).

Whoever builds the iterative loop next needs to use THIS rescaled
KDE_baseline as `Risk_0`, not the raw one, for the loop's arithmetic
(`Risk_t = Risk_(t-1) + predicted_residual_t`) to stay on a consistent
scale across iterations.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_METRICS_DIR,
    MODULE3_MODELS_DIR,
    MODULE3_RF_FEATURE_IMPORTANCE_PATH,
    MODULE3_RF_FINAL_MODEL_PATH,
    MODULE3_RF_FOLDS_DIR,
    MODULE3_RF_METRICS_PATH,
    MODULE3_SPATIAL_CV_FOLDS_PATH,
    MODULE3_STAGE2_FEATURE_TABLE_PATH,
)
from src.module3_spatial.kde_baseline import district_centroid_coords, load_district_boundaries

logger = logging.getLogger(__name__)

TARGET_COL = "relative_residual"
# UPDATED 2026-08-08 (EXPERIMENT_LOG.md M3-015): was "residual_rescaled". A
# direct diagnostic of the raw absolute residual found it strongly
# heteroscedastic (corr(Risk_0, |residual|) = 0.78; corr(log(Risk_0),
# log(|residual|+1)) = 0.81) - every absolute-residual model let the
# handful of huge outbreak weeks dominate the learning signal. Modeling the
# RELATIVE residual instead fixes this and produces a genuine, bootstrap-
# confirmed improvement over both naive persistence and the previous
# absolute-residual RF on every reported metric (M3-015). Reconstruction
# back to an absolute Risk value is exact, not approximate:
# Risk_t = Risk_(t-1) + predicted_relative_residual * (Risk_(t-1) + 1).

FEATURE_COLUMNS = [
    "rain_sum (mm)", "temperature_2m_mean (°C)",
    "rainfall_lag_2", "rainfall_lag_3", "rainfall_lag_4",
    "temperature_lag_2", "temperature_lag_3", "temperature_lag_4",
    "rainfall_anomaly", "temperature_anomaly",
    "monsoon_indicator_SW", "monsoon_indicator_NE",
    "elevation_m", "Estimated_Population", "population_density",
    "mahalanobis_anomaly_score",
]
# NOTE: FEATURE_COLUMNS is kept exactly as originally specified (16 columns)
# so that outdated/frozen exploratory scripts that import it directly
# (`alpha_sweep.py`, M3-006; `stage2_experiments.py`, the ablation this
# promotion came from) remain byte-for-byte reproducible if ever rerun -
# their reported numbers are tied to this exact 16-column set. The
# OFFICIAL Stage 2 model (this file's own `run_compensation_model()`,
# `iterative_loop.py`, `evaluate.py`, `forecast_future.py`) uses
# STAGE2_FEATURE_COLUMNS below instead.

# Own-district lags of residual_rescaled (1-4 weeks) - promoted from the
# stage2_experiments.py ablation (2026-08-05, EXPERIMENT_LOG.md M3-008):
# this single addition drops out-of-fold residual MAE from ~34.7 to ~10.1
# and lets alpha=1.0 (no shrinkage) become the best-performing choice - a
# ~51% MAE improvement over Stage 1 alone. Every other feature in
# FEATURE_COLUMNS is either static per-district or current-week climate;
# nothing previously gave the RF any memory of a district's own recent
# burden trend, despite dengue outbreaks having real week-to-week
# persistence (verified: corr(residual_rescaled, its own lag_1) = 0.84,
# and this is NOT a computational artifact - kde_baseline_rescaled[t] only
# ever uses week t's own case counts, never t-1's, so any lag-1
# correlation reflects genuine epidemic persistence, not shared lineage).
RESIDUAL_LAG_WEEKS = [1, 2, 3, 4]
RESIDUAL_LAG_COLUMNS = [f"residual_rescaled_lag_{lag}" for lag in RESIDUAL_LAG_WEEKS]
STAGE2_FEATURE_COLUMNS = FEATURE_COLUMNS + RESIDUAL_LAG_COLUMNS
# NOTE: STAGE2_FEATURE_COLUMNS (20 columns) is kept exactly as it was after
# M3-008 - NOT extended further in place - so that
# `stacked_persistence_experiment.py` (M3-011, frozen) stays byte-for-byte
# reproducible if ever rerun, the same reasoning that already keeps
# FEATURE_COLUMNS itself frozen for `alpha_sweep.py`/`stage2_experiments.py`.
# The OFFICIAL Stage 2 model (this file's own `run_compensation_model()`,
# `iterative_loop.py`, `evaluate.py`, `forecast_future.py`) uses
# STAGE2_FEATURE_COLUMNS_V2 below instead.

# Own-district lags of the RELATIVE residual (1-4 weeks) - promoted from the
# `relative_residual_compensation.py` experiment (2026-08-08, M3-015): fixes
# the heteroscedasticity of the absolute residual (see TARGET_COL comment
# above) and, combined with the relative target, beats both naive
# persistence and the previous absolute-residual RF on every metric.
RELATIVE_LAG_COLUMNS = [f"relative_residual_lag_{lag}" for lag in RESIDUAL_LAG_WEEKS]
STAGE2_FEATURE_COLUMNS_V2 = STAGE2_FEATURE_COLUMNS + RELATIVE_LAG_COLUMNS

N_SPATIAL_FOLDS = 5
SPATIAL_CV_SEED = 42

# Fixed, conservative hyperparameters (not tuned) - consistent with Module
# 1/2's convention of a documented, un-tuned baseline before any grid search.
RF_PARAMS = dict(
    n_estimators=300,
    min_samples_leaf=5,
    random_state=42,
    n_jobs=-1,
)


# ---------------------------------------------------------------------------
# Step 1: load feature table, drop lag_4 NaN rows
# ---------------------------------------------------------------------------

def load_training_table(path: Path = MODULE3_STAGE2_FEATURE_TABLE_PATH) -> pd.DataFrame:
    """Drop rows with NaN in either lag_4 column (rainfall_lag_4,
    temperature_lag_4) - the deepest lag - so every training row has a
    complete 2/3/4-week lag history. Because lag_4 is NaN only for each
    district's first 4 rows (a strict superset of lag_2's first-2-rows and
    lag_3's first-3-rows), this single drop leaves zero NaN anywhere in
    FEATURE_COLUMNS, not just in the lag_4 columns themselves.
    """
    df = pd.read_csv(path, parse_dates=["Week_Start_Date"])
    before = len(df)
    df = df.dropna(subset=["rainfall_lag_4", "temperature_lag_4"]).reset_index(drop=True)
    dropped = before - len(df)

    remaining_nan = df[FEATURE_COLUMNS].isna().sum()
    remaining_nan = remaining_nan[remaining_nan > 0]
    if not remaining_nan.empty:
        raise ValueError(f"Unexpected NaN remains in FEATURE_COLUMNS after the lag_4 drop:\n{remaining_nan}")

    logger.info(
        "Loaded stage2_feature_table.csv: %d rows (dropped %d series-start "
        "rows lacking a full lag_4 history).", len(df), dropped,
    )
    return df


# ---------------------------------------------------------------------------
# Step 2: Stage-2-scoped KDE_baseline rescale + residual target (see module
# docstring's IMPORTANT section for why this exists)
# ---------------------------------------------------------------------------

def rescale_kde_baseline(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    weekly = (
        df.groupby(["Year", "Week"])
        .agg(total_cases=("Number_of_Cases", "sum"), total_kde=("KDE_baseline", "sum"))
        .reset_index()
    )
    df = df.merge(weekly, on=["Year", "Week"], how="left")

    # Guards the 0/0 case (a week with zero cases everywhere has
    # total_kde == 0 too, since KDE_baseline is itself case-count-weighted) -
    # not observed in this dataset (checked: no week has total_cases == 0),
    # but kept as a documented safeguard rather than an assumption.
    scale_factor = np.where(df["total_kde"] > 0, df["total_cases"] / df["total_kde"], 0.0)
    df["kde_baseline_rescaled"] = df["KDE_baseline"] * scale_factor
    df["residual_rescaled"] = df["Number_of_Cases"] - df["kde_baseline_rescaled"]

    return df.drop(columns=["total_cases", "total_kde"])


# ---------------------------------------------------------------------------
# Step 2b: own-district residual lag features (promoted 2026-08-05,
# EXPERIMENT_LOG.md M3-008 - see STAGE2_FEATURE_COLUMNS above)
# ---------------------------------------------------------------------------

def add_residual_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """Adds RESIDUAL_LAG_COLUMNS and RELATIVE_LAG_COLUMNS via `.shift()` on
    each district's own time-ordered rows (same pattern
    `feature_engineering.py::compute_lag_features` already uses for
    climate) - requires `residual_rescaled` and `kde_baseline_rescaled` to
    already exist (call AFTER `rescale_kde_baseline`).

    `relative_residual` (added 2026-08-08, M3-015) divides the absolute
    residual by (kde_baseline_rescaled + 1) - the same "+1" denominator
    guard `rescale_kde_baseline` itself uses - fixing the heteroscedasticity
    a direct diagnostic found in the absolute residual (see TARGET_COL
    comment above).
    """
    df = df.sort_values(["District", "Week_Start_Date"]).reset_index(drop=True)
    df["relative_residual"] = df["residual_rescaled"] / (df["kde_baseline_rescaled"] + 1)
    grouped = df.groupby("District")
    for lag, col in zip(RESIDUAL_LAG_WEEKS, RESIDUAL_LAG_COLUMNS):
        df[col] = grouped["residual_rescaled"].shift(lag)
    for lag, col in zip(RESIDUAL_LAG_WEEKS, RELATIVE_LAG_COLUMNS):
        df[col] = grouped["relative_residual"].shift(lag)
    return df


def drop_residual_lag_nan(df: pd.DataFrame) -> pd.DataFrame:
    """Drops the (same-sized, per-district-start) NaN rows
    `add_residual_lag_features` introduces - a SEPARATE 100-row drop from
    `load_training_table`'s own climate lag_4 drop (both remove each
    district's first 4 remaining rows, but at different pipeline stages),
    leaving 25,123 -> 25,023 rows. Validates STAGE2_FEATURE_COLUMNS_V2 (a
    strict superset of STAGE2_FEATURE_COLUMNS) is NaN-free afterward -
    RELATIVE_LAG_COLUMNS shares the identical shift pattern and underlying
    non-null condition as RESIDUAL_LAG_COLUMNS (relative_residual is defined
    wherever residual_rescaled is), so this single drop clears both, checked
    directly here rather than assumed.
    """
    before = len(df)
    df = df.dropna(subset=RESIDUAL_LAG_COLUMNS).reset_index(drop=True)
    dropped = before - len(df)

    remaining_nan = df[STAGE2_FEATURE_COLUMNS_V2].isna().sum()
    remaining_nan = remaining_nan[remaining_nan > 0]
    if not remaining_nan.empty:
        raise ValueError(f"Unexpected NaN remains in STAGE2_FEATURE_COLUMNS_V2 after the residual-lag drop:\n{remaining_nan}")

    logger.info("Dropped %d additional rows lacking residual_lag_4 history (%d remain).", dropped, len(df))
    return df


def prepare_training_table(path: Path = MODULE3_STAGE2_FEATURE_TABLE_PATH) -> pd.DataFrame:
    """Canonical Stage 2 training table (load -> rescale -> add residual
    lags -> drop remaining NaN) - the single entry point every OFFICIAL
    Stage 2 consumer (this file, `iterative_loop.py`, `evaluate.py`,
    `forecast_future.py`) should use, so the M3-008 promotion is applied
    consistently rather than duplicated ad hoc in each file.
    """
    df = load_training_table(path)
    df = rescale_kde_baseline(df)
    df = add_residual_lag_features(df)
    df = drop_residual_lag_nan(df)
    return df


# ---------------------------------------------------------------------------
# Step 3: spatial K-means CV (5 folds, whole districts, never split weeks)
# ---------------------------------------------------------------------------

def build_spatial_folds() -> pd.DataFrame:
    """Cluster the 25 district centroids (same reprojected GADM geometry
    kde_baseline.py uses) into N_SPATIAL_FOLDS groups. A district's cluster
    assignment is fixed - every one of its weekly rows falls in the same
    fold, satisfying "never split a district's weeks across folds" trivially
    by construction (whole districts move together, not individual weeks).
    """
    boundaries = load_district_boundaries()
    coords = district_centroid_coords(boundaries)
    kmeans = KMeans(n_clusters=N_SPATIAL_FOLDS, random_state=SPATIAL_CV_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(coords)
    return pd.DataFrame({"District": boundaries["District"], "spatial_fold": cluster_labels})


# ---------------------------------------------------------------------------
# Step 4: train/evaluate per spatial fold
# ---------------------------------------------------------------------------

def run_spatial_cv(
    df: pd.DataFrame, folds_df: pd.DataFrame, feature_cols: list[str] = FEATURE_COLUMNS,
) -> tuple[pd.DataFrame, dict[int, RandomForestRegressor]]:
    df = df.merge(folds_df, on="District", how="left")
    if df["spatial_fold"].isna().any():
        raise ValueError("Some districts have no spatial_fold assignment after merge.")

    fold_rows = []
    fold_models: dict[int, RandomForestRegressor] = {}

    for fold_id in sorted(df["spatial_fold"].unique()):
        test_mask = df["spatial_fold"] == fold_id
        train_mask = ~test_mask

        X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, TARGET_COL]
        X_test, y_test = df.loc[test_mask, feature_cols], df.loc[test_mask, TARGET_COL]

        model = RandomForestRegressor(**RF_PARAMS)
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)

        mae = mean_absolute_error(y_test, predicted)
        rmse = float(np.sqrt(mean_squared_error(y_test, predicted)))
        test_districts = sorted(df.loc[test_mask, "District"].unique())

        fold_rows.append(
            {
                "fold": int(fold_id),
                "n_districts": len(test_districts),
                "districts": ", ".join(test_districts),
                "n_train_rows": int(train_mask.sum()),
                "n_test_rows": int(test_mask.sum()),
                "mae": mae,
                "rmse": rmse,
            }
        )
        fold_models[int(fold_id)] = model
        logger.info(
            "Spatial fold %d (%s): %d test rows, MAE=%.3f, RMSE=%.3f.",
            fold_id, ", ".join(test_districts), int(test_mask.sum()), mae, rmse,
        )

    return pd.DataFrame(fold_rows), fold_models


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_compensation_model() -> pd.DataFrame:
    MODULE3_RF_FOLDS_DIR.mkdir(parents=True, exist_ok=True)
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)

    df = prepare_training_table()

    folds_df = build_spatial_folds()
    folds_df.to_csv(MODULE3_SPATIAL_CV_FOLDS_PATH, index=False)
    logger.info(
        "Spatial CV folds (%d clusters over 25 districts):\n%s",
        N_SPATIAL_FOLDS,
        folds_df.groupby("spatial_fold")["District"].apply(list).to_string(),
    )

    fold_metrics, fold_models = run_spatial_cv(df, folds_df, feature_cols=STAGE2_FEATURE_COLUMNS_V2)
    for fold_id, model in fold_models.items():
        joblib.dump(model, MODULE3_RF_FOLDS_DIR / f"fold_{fold_id}.joblib")

    agg_row = pd.DataFrame(
        [
            {
                "fold": "mean_std",
                "n_districts": None,
                "districts": None,
                "n_train_rows": None,
                "n_test_rows": None,
                "mae": fold_metrics["mae"].mean(),
                "rmse": fold_metrics["rmse"].mean(),
                "mae_std": fold_metrics["mae"].std(),
                "rmse_std": fold_metrics["rmse"].std(),
            }
        ]
    )
    metrics_df = pd.concat([fold_metrics, agg_row], ignore_index=True)
    metrics_df.to_csv(MODULE3_RF_METRICS_PATH, index=False)

    logger.info(
        "Aggregate (RELATIVE-residual scale, since TARGET_COL=%r as of M3-015 - "
        "not directly comparable to the pre-2026-08-08 absolute-scale figures): "
        "MAE = %.3f +/- %.3f, RMSE = %.3f +/- %.3f (mean +/- std across %d folds).",
        TARGET_COL, fold_metrics["mae"].mean(), fold_metrics["mae"].std(),
        fold_metrics["rmse"].mean(), fold_metrics["rmse"].std(),
        N_SPATIAL_FOLDS,
    )

    logger.info("Training final production model on all %d districts...", 25)
    final_model = RandomForestRegressor(**RF_PARAMS)
    final_model.fit(df[STAGE2_FEATURE_COLUMNS_V2], df[TARGET_COL])
    joblib.dump(final_model, MODULE3_RF_FINAL_MODEL_PATH)

    importance_df = (
        pd.DataFrame({"feature": STAGE2_FEATURE_COLUMNS_V2, "importance": final_model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    importance_df.to_csv(MODULE3_RF_FEATURE_IMPORTANCE_PATH, index=False)

    logger.info(
        "Top 10 features by importance:\n%s", importance_df.head(10).to_string(index=False),
    )
    logger.info(
        "Stage 2 RF (single-pass) complete: fold models -> %s | final model -> %s | "
        "metrics -> %s | feature importance -> %s | spatial folds -> %s",
        MODULE3_RF_FOLDS_DIR, MODULE3_RF_FINAL_MODEL_PATH, MODULE3_RF_METRICS_PATH,
        MODULE3_RF_FEATURE_IMPORTANCE_PATH, MODULE3_SPATIAL_CV_FOLDS_PATH,
    )
    return metrics_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_compensation_model()
