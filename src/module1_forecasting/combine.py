"""Module 1 - combine Stage 1 (SARIMA) + Stage 2 (XGBoost) into the final
forecast and evaluate the compensation benefit.

Implements Decision 010's final-forecast formula and the evaluation
framework approved by the user before this file was written (see
`module_1_forecasting/MODULE_CONTEXT.md` "Stage 2 Implementation Status"):

```text
final_prediction = sarima_prediction + predicted_residual
```

Evaluation compares Stage-1-only vs Stage-1+Stage-2 using the same
RMSE/MAE/sMAPE/MASE (`evaluate.compute_all_metrics`, unchanged) at the same
per-fold + median-aggregate + holdout granularity Stage 1 already reports,
plus:

- A Diebold-Mariano test (`evaluate.dm_test`) per district, for both the
  full out-of-sample series (validation + holdout) and a holdout-only scope.
- Residual variance reduction per district.
- A final Ljung-Box sanity check (`evaluate.ljung_box_diagnostics`) on
  `actual - final_prediction`, mirroring Stage 1's own diagnostic, to
  confirm Stage 2 actually removed structure rather than moving it.

All of this is reported **per district, honestly** - including districts
where Stage 2 does not help - rather than only surfacing favorable results.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE1_COMBINED_METRICS_PATH,
    MODULE1_DM_TEST_PATH,
    MODULE1_FIGURES_DIR,
    MODULE1_FINAL_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE1_XGBOOST_PREDICTIONS_PATH,
)
from src.module1_forecasting.evaluate import compute_all_metrics, dm_test, ljung_box_diagnostics  # noqa: E402
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_MIN_TRAIN_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    fit_window,
    generate_walk_forward_folds,
    get_district_series,
    get_holdout_series,
)

logger = logging.getLogger(__name__)

WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS
MIN_TRAIN_YEARS = DEFAULT_MIN_TRAIN_YEARS

# Same representative subset used for Stage 1's ACF diagnostics
# (baseline_sarima.py) - one high-volume, one moderate, two sparse/
# zero-inflated districts.
ACF_DIAGNOSTIC_DISTRICTS = ("Colombo", "Kandy", "Mullaitivu", "Kilinochchi")
LJUNG_BOX_LAGS = (26, 52)
DM_MAX_LAG = 12


# ---------------------------------------------------------------------------
# Final forecast
# ---------------------------------------------------------------------------

def build_final_predictions() -> pd.DataFrame:
    """`final_prediction = sarima_prediction + predicted_residual`
    (Decision 010). Clipped to a 0 floor for the same reason Stage 1's own
    forecasts are (`baseline_sarima.py` design decision 2) - case counts
    cannot be negative, and adding a negative predicted residual can push an
    already-small SARIMA forecast below zero.
    """
    df = pd.read_csv(MODULE1_XGBOOST_PREDICTIONS_PATH)
    df["fold_id_numeric"] = pd.to_numeric(df["fold_id"], errors="coerce")
    df["final_prediction"] = (df["sarima_prediction"] + df["predicted_residual"]).clip(lower=0.0)
    df["final_residual"] = df["Number_of_Cases"] - df["final_prediction"]
    return df


# ---------------------------------------------------------------------------
# Per-district, per-fold metric comparison (Stage-1-only vs combined)
# ---------------------------------------------------------------------------

def _district_imputed_series(weekly_df: pd.DataFrame, district: str) -> pd.Series:
    return get_district_series(weekly_df, district, value_col="is_imputed")


def compute_district_fold_metrics(
    district: str, weekly_df: pd.DataFrame, predictions_df: pd.DataFrame
) -> list[dict]:
    """For one district, compute Stage-1-only and combined metrics for every
    walk-forward fold plus the holdout block, reusing `validation.py`
    (unchanged) to regenerate the exact same fold boundaries Stage 1 used.
    """
    series = get_district_series(weekly_df, district, value_col="Number_of_Cases")
    imputed = _district_imputed_series(weekly_df, district)
    district_preds = predictions_df[predictions_df["District"] == district]

    rows: list[dict] = []

    for fold_id, (train_index, val_index) in enumerate(
        generate_walk_forward_folds(
            series, holdout_years=HOLDOUT_YEARS, min_train_years=MIN_TRAIN_YEARS, weeks_per_year=WEEKS_PER_YEAR
        ),
        start=1,
    ):
        train_series = fit_window(series, train_index[-1])
        y_train = train_series.to_numpy(dtype=float)
        imputed_train = imputed.loc[train_series.index].to_numpy()

        val_rows = district_preds[district_preds["fold_id_numeric"] == fold_id].sort_values(["Year", "Week"])
        if len(val_rows) != len(val_index):
            logger.warning(
                "%s fold %d: expected %d validation rows, found %d - possible fold misalignment.",
                district, fold_id, len(val_index), len(val_rows),
            )
        mask = ~val_rows["is_imputed"].to_numpy()

        for model_name, y_pred_col in (("stage1_only", "sarima_prediction"), ("stage1_plus_stage2", "final_prediction")):
            metrics = compute_all_metrics(
                y_true=val_rows["Number_of_Cases"].to_numpy(),
                y_pred=val_rows[y_pred_col].to_numpy(),
                y_train=y_train,
                m=WEEKS_PER_YEAR,
                mask=mask,
                train_mask=~imputed_train,
            )
            rows.append({"District": district, "model": model_name, "fold_id": fold_id, **metrics})

    holdout = get_holdout_series(series, holdout_years=HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
    pre_holdout = series.iloc[: len(series) - len(holdout)]
    imputed_pre_holdout = imputed.loc[pre_holdout.index].to_numpy()

    holdout_rows = district_preds[district_preds["split"] == "holdout"].sort_values(["Year", "Week"])
    mask = ~holdout_rows["is_imputed"].to_numpy()
    for model_name, y_pred_col in (("stage1_only", "sarima_prediction"), ("stage1_plus_stage2", "final_prediction")):
        metrics = compute_all_metrics(
            y_true=holdout_rows["Number_of_Cases"].to_numpy(),
            y_pred=holdout_rows[y_pred_col].to_numpy(),
            y_train=pre_holdout.to_numpy(dtype=float),
            m=WEEKS_PER_YEAR,
            mask=mask,
            train_mask=~imputed_pre_holdout,
        )
        rows.append({"District": district, "model": model_name, "fold_id": "holdout", **metrics})

    return rows


def _aggregate_rows(fold_rows: list[dict], district: str, model_name: str) -> dict:
    """Per-district, per-model aggregate row: median of each metric across
    the 14 validation folds - consistent with Stage 1's own aggregation."""
    relevant = [r for r in fold_rows if r["District"] == district and r["model"] == model_name and r["fold_id"] != "holdout"]

    def _median(key: str) -> float:
        values = [r[key] for r in relevant if not np.isnan(r[key])]
        return float(np.median(values)) if values else float("nan")

    return {
        "District": district,
        "model": model_name,
        "fold_id": "validation_aggregate",
        "rmse": _median("rmse"),
        "mae": _median("mae"),
        "smape": _median("smape"),
        "mase": _median("mase"),
        "n_obs_scored": int(sum(r["n_obs_scored"] for r in relevant)),
        "n_obs_total": int(sum(r["n_obs_total"] for r in relevant)),
    }


# ---------------------------------------------------------------------------
# Pooled error series (for DM test, variance reduction, Ljung-Box)
# ---------------------------------------------------------------------------

def pooled_district_errors(district_preds: pd.DataFrame, include_holdout: bool) -> pd.DataFrame:
    """Chronologically ordered, non-imputed rows for one district. Folds are
    non-overlapping and generated in ascending order, so sorting by
    (fold_id_numeric, Year, Week) already yields chronological order for the
    validation block; holdout follows (with the known ~26-week gap - see
    `compensation_model.py`'s `build_residual_lags` docstring - which is
    irrelevant here since we're pooling errors, not taking lags)."""
    validation_rows = district_preds[district_preds["split"] == "validation"].sort_values(
        ["fold_id_numeric", "Year", "Week"]
    )
    frames = [validation_rows]
    if include_holdout:
        holdout_rows = district_preds[district_preds["split"] == "holdout"].sort_values(["Year", "Week"])
        frames.append(holdout_rows)
    pooled = pd.concat(frames, ignore_index=True)
    return pooled[~pooled["is_imputed"]]


def residual_variance_reduction(pooled: pd.DataFrame) -> float:
    """`1 - var(final_residual) / var(stage1_residual)` on pooled,
    non-imputed out-of-sample rows. Positive means Stage 2 reduced the
    spread of unexplained error; negative means it made it worse.

    Uses `nanvar` (rather than plain `var`) because a fold whose Stage 1 fit
    is now correctly flagged as explosive/non-stationary (`baseline_sarima.
    _has_explosive_ar_root`) contributes `NaN` `residual`/`final_residual`
    rows here - those should be excluded from the variance calculation, not
    poison the whole district's result to `NaN`.
    """
    var_stage1 = np.nanvar(pooled["residual"].to_numpy(dtype=float), ddof=1)
    var_final = np.nanvar(pooled["final_residual"].to_numpy(dtype=float), ddof=1)
    if not np.isfinite(var_stage1) or var_stage1 == 0:
        return float("nan")
    return float(1 - var_final / var_stage1)


def compute_dm_results(predictions_df: pd.DataFrame, districts: list[str] = DISTRICTS) -> pd.DataFrame:
    rows = []
    for district in districts:
        district_preds = predictions_df[predictions_df["District"] == district]
        pooled_all = pooled_district_errors(district_preds, include_holdout=True)

        for scope in ("validation_and_holdout", "holdout_only"):
            pooled = pooled_all if scope == "validation_and_holdout" else pooled_all[pooled_all["split"] == "holdout"]
            result = dm_test(pooled["residual"], pooled["final_residual"], max_lag=DM_MAX_LAG, loss="squared")
            rows.append({"District": district, "scope": scope, **result})

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Final Ljung-Box + ACF diagnostics
# ---------------------------------------------------------------------------

def plot_final_acf_diagnostics(
    residuals_by_district: dict[str, np.ndarray],
    districts: tuple[str, ...] = ACF_DIAGNOSTIC_DISTRICTS,
    output_dir: Path = MODULE1_FIGURES_DIR,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for district in districts:
        residuals = residuals_by_district.get(district)
        if residuals is None or residuals.size < 3:
            logger.warning("Not enough pooled final residuals for an ACF plot: %s", district)
            continue

        fig, ax = plt.subplots(figsize=(10, 4))
        max_lags = min(60, residuals.size - 1)
        plot_acf(residuals, lags=max_lags, ax=ax, title=f"Final combined residual ACF (post Stage 2) - {district}")
        fig.tight_layout()
        safe_name = district.replace(" ", "_")
        fig.savefig(output_dir / f"acf_residuals_final_{safe_name}.png", dpi=150)
        plt.close(fig)
        logger.info("Saved final-residual ACF diagnostic plot for %s.", district)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_combine_pipeline(districts: list[str] = DISTRICTS) -> None:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    predictions_df = build_final_predictions()

    MODULE1_FINAL_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    MODULE1_COMBINED_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

    final_output = predictions_df[
        [
            "District", "Year", "Week", "split", "fold_id", "Number_of_Cases", "is_imputed",
            "sarima_prediction", "residual", "predicted_residual", "stage2_trained",
            "final_prediction", "final_residual",
        ]
    ]
    final_output.to_csv(MODULE1_FINAL_PREDICTIONS_PATH, index=False)
    logger.info("Wrote %d final combined prediction rows to %s.", len(final_output), MODULE1_FINAL_PREDICTIONS_PATH)

    all_fold_rows: list[dict] = []
    final_ljung_box_by_district: dict[str, dict] = {}
    final_residuals_by_district: dict[str, np.ndarray] = {}

    for district in districts:
        logger.info("=== %s ===", district)
        fold_rows = compute_district_fold_metrics(district, weekly_df, predictions_df)
        all_fold_rows.extend(fold_rows)

        for model_name in ("stage1_only", "stage1_plus_stage2"):
            all_fold_rows.append(_aggregate_rows(fold_rows, district, model_name))

        district_preds = predictions_df[predictions_df["District"] == district]
        pooled_validation = pooled_district_errors(district_preds, include_holdout=False)

        var_reduction = residual_variance_reduction(
            pooled_district_errors(district_preds, include_holdout=True)
        )
        ljung_box = ljung_box_diagnostics(pooled_validation["final_residual"].to_numpy(), lags=LJUNG_BOX_LAGS)
        final_ljung_box_by_district[district] = {"residual_variance_reduction": var_reduction, **ljung_box}
        final_residuals_by_district[district] = pooled_validation["final_residual"].to_numpy()

    metrics_df = pd.DataFrame(all_fold_rows)

    # Attach variance-reduction/Ljung-Box diagnostics to each district's
    # "stage1_plus_stage2" validation_aggregate row only (they describe the
    # combined model's residual, not a per-fold quantity).
    for district, diag in final_ljung_box_by_district.items():
        row_mask = (
            (metrics_df["District"] == district)
            & (metrics_df["model"] == "stage1_plus_stage2")
            & (metrics_df["fold_id"] == "validation_aggregate")
        )
        for key, value in diag.items():
            metrics_df.loc[row_mask, key] = value

    metrics_df.to_csv(MODULE1_COMBINED_METRICS_PATH, index=False)
    logger.info("Wrote %d combined-vs-baseline metric rows to %s.", len(metrics_df), MODULE1_COMBINED_METRICS_PATH)

    dm_results = compute_dm_results(predictions_df, districts=districts)
    dm_results.to_csv(MODULE1_DM_TEST_PATH, index=False)
    logger.info("Wrote %d Diebold-Mariano test rows to %s.", len(dm_results), MODULE1_DM_TEST_PATH)

    plot_final_acf_diagnostics(final_residuals_by_district)

    n_improved = (
        metrics_df[(metrics_df["fold_id"] == "validation_aggregate") & (metrics_df["model"] == "stage1_plus_stage2")]
        .merge(
            metrics_df[(metrics_df["fold_id"] == "validation_aggregate") & (metrics_df["model"] == "stage1_only")],
            on="District", suffixes=("_combined", "_stage1"),
        )
        .assign(improved=lambda d: d["mase_combined"] < d["mase_stage1"])["improved"]
        .sum()
    )
    logger.info(
        "Combine complete: %d/%d districts show a lower validation-aggregate MASE with Stage 2 than without.",
        int(n_improved), len(districts),
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_combine_pipeline()
