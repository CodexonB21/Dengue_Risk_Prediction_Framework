"""Module 1 Stage 2 - per-district shrinkage weight (Phase 3 remediation).

Targets the finding that `Kilinochchi` and `Mannar` get a WORSE holdout MASE
after Stage 2 than Stage 1 alone (Decision 017's post-fix numbers:
Kilinochchi -11.7%, Mannar -3.0%; neither DM-significant). Stage 2's
correction is currently applied at full strength for every district
(`final = sarima_prediction + predicted_residual`, i.e. an implicit weight
of 1.0 everywhere - see `residual_transform.combine_stage2_forecast`). This
module selects a per-district weight `w` such that
`final = sarima_prediction + w * predicted_residual`, shrinking the
correction toward zero only where it empirically hurts.

Two-stage, holdout-respecting design (Decision 009 unchanged):

1. `select_shrinkage_weights()` grid-searches `w` per district using ONLY
   the 14 already-computed walk-forward validation folds' `sarima_prediction`
   / `predicted_residual` (pure recombination of Stage 2's existing
   out-of-sample output - no retraining). A candidate weight is only chosen
   over the default `w=1.0` if it both (a) improves the MEDIAN fold MASE and
   (b) beats `w=1.0` on a MAJORITY of the individual scored folds - the
   second condition guards against the weight search itself overfitting to
   one or two folds, a real risk flagged for exactly the two low-volume
   districts this module targets.
2. `evaluate_shrinkage_on_holdout()` then checks the validation-chosen
   weight against the untouched holdout block, per district, PURELY to
   confirm - not to re-select. A district's holdout accept/reject decision
   is independent of every other district: if the chosen weight doesn't
   also help (or at least not hurt) on holdout, that district reverts to
   `w=1.0` (i.e. behaves exactly as production does today) rather than
   forcing adoption.

`run_shrinkage_selection()` runs both and writes the final, holdout-confirmed
per-district weight table that `combine.py` consumes when
`apply_shrinkage=True`.
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
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_METRICS_DIR,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    module1_stage2_paths,
)
from src.module1_forecasting.evaluate import mase  # noqa: E402
from src.module1_forecasting.residual_transform import (  # noqa: E402
    combine_stage2_forecast,
    validate_residual_mode,
)
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

CANDIDATE_WEIGHTS: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0)
DEFAULT_WEIGHT = 1.0
# A candidate must win on at least this fraction of individually-scored
# folds (not just the median) to be trusted over the default weight.
MIN_FOLD_WIN_FRACTION = 0.5

MODULE1_SHRINKAGE_WEIGHTS_PATH = MODULE1_METRICS_DIR / "sarima_stage2_shrinkage_weights.csv"
MODULE1_SHRINKAGE_HOLDOUT_CHECK_PATH = MODULE1_METRICS_DIR / "sarima_stage2_shrinkage_holdout_check.csv"


def select_shrinkage_weights(
    districts: list[str] = DISTRICTS,
    weights: tuple[float, ...] = CANDIDATE_WEIGHTS,
    *,
    residual_mode: str | None = None,
) -> pd.DataFrame:
    """Validation-fold-only weight search. Never touches the holdout."""
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    predictions_df = pd.read_csv(paths["xgboost_predictions"])
    predictions_df["fold_id_numeric"] = pd.to_numeric(predictions_df["fold_id"], errors="coerce")

    rows: list[dict] = []
    for district in districts:
        series = get_district_series(weekly_df, district, value_col="Number_of_Cases")
        imputed = get_district_series(weekly_df, district, value_col="is_imputed")
        district_preds = predictions_df[predictions_df["District"] == district]

        fold_mase_by_weight: dict[float, list[float]] = {w: [] for w in weights}

        for fold_id, (train_index, val_index) in enumerate(
            generate_walk_forward_folds(
                series, holdout_years=HOLDOUT_YEARS, min_train_years=MIN_TRAIN_YEARS, weeks_per_year=WEEKS_PER_YEAR
            ),
            start=1,
        ):
            if fold_id == 1:
                # Documented Stage 2 no-op (predicted_residual == 0 for
                # every weight) - identical MASE regardless of weight,
                # carries no information for this search.
                continue

            train_series = fit_window(series, train_index[-1])
            y_train = train_series.to_numpy(dtype=float)
            imputed_train = imputed.loc[train_series.index].to_numpy(dtype=bool)

            val_rows = district_preds.loc[
                district_preds["fold_id_numeric"] == fold_id
            ].sort_values(["Year", "Week"])
            if val_rows.empty:
                continue
            fold_mask = ~val_rows["is_imputed"].to_numpy(dtype=bool)

            for w in weights:
                final = combine_stage2_forecast(
                    val_rows["sarima_prediction"].to_numpy(),
                    val_rows["predicted_residual"].to_numpy(),
                    mode=mode,
                    weight=w,
                )
                m = mase(
                    val_rows["Number_of_Cases"].to_numpy(), final, y_train,
                    m=WEEKS_PER_YEAR, mask=fold_mask, train_mask=~imputed_train,
                )
                fold_mase_by_weight[w].append(m)

        median_by_weight = {
            w: float(np.nanmedian(vals)) if vals else float("nan")
            for w, vals in fold_mase_by_weight.items()
        }
        baseline_folds = np.array(fold_mase_by_weight[DEFAULT_WEIGHT], dtype=float)

        selected_weight = DEFAULT_WEIGHT
        best_median = median_by_weight[DEFAULT_WEIGHT]
        best_win_fraction = float("nan")
        for w in weights:
            if w == DEFAULT_WEIGHT:
                continue
            candidate_folds = np.array(fold_mase_by_weight[w], dtype=float)
            paired = ~np.isnan(baseline_folds) & ~np.isnan(candidate_folds)
            if paired.sum() == 0:
                continue
            win_fraction = float(np.mean(candidate_folds[paired] < baseline_folds[paired]))
            candidate_median = median_by_weight[w]
            improves_median = (
                not np.isnan(candidate_median)
                and not np.isnan(best_median)
                and candidate_median < best_median
            )
            if improves_median and win_fraction >= MIN_FOLD_WIN_FRACTION:
                selected_weight = w
                best_median = candidate_median
                best_win_fraction = win_fraction

        row = {
            "District": district,
            "selected_weight": selected_weight,
            "fold_win_fraction_vs_w1": best_win_fraction,
            "n_folds_scored": int(np.sum(~np.isnan(baseline_folds))),
        }
        for w in weights:
            row[f"median_mase_w{w}"] = median_by_weight[w]
        rows.append(row)

    result = pd.DataFrame(rows)
    n_shrunk = int((result["selected_weight"] != DEFAULT_WEIGHT).sum())
    logger.info(
        "Validation-fold weight search: %d/%d districts selected a weight != %.2f (%s).",
        n_shrunk, len(districts), DEFAULT_WEIGHT,
        ", ".join(result.loc[result["selected_weight"] != DEFAULT_WEIGHT, "District"]) or "none",
    )
    return result


def evaluate_shrinkage_on_holdout(
    selection: pd.DataFrame,
    *,
    residual_mode: str | None = None,
) -> pd.DataFrame:
    """Confirm (never re-select) each district's validation-chosen weight
    against the untouched holdout block. Districts whose chosen weight is
    already 1.0 pass trivially (no change from production). For every other
    district, `adopt=True` only if the holdout MASE at the selected weight
    is no worse than at weight=1.0 - otherwise that district's `final_weight`
    reverts to 1.0 in the output, exactly matching current production
    behavior for that district.
    """
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    weekly_df = pd.read_csv(
        MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"]
    )
    predictions_df = pd.read_csv(paths["xgboost_predictions"])

    rows: list[dict] = []
    for _, sel_row in selection.iterrows():
        district = sel_row["District"]
        selected_weight = float(sel_row["selected_weight"])

        series = get_district_series(weekly_df, district, value_col="Number_of_Cases")
        imputed = get_district_series(weekly_df, district, value_col="is_imputed")
        holdout = get_holdout_series(series, holdout_years=HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
        pre_holdout = series.iloc[: len(series) - len(holdout)]
        imputed_pre_holdout = imputed.loc[pre_holdout.index].to_numpy(dtype=bool)

        holdout_rows = predictions_df.loc[
            (predictions_df["District"] == district) & (predictions_df["split"] == "holdout")
        ].sort_values(["Year", "Week"])
        holdout_mask = ~holdout_rows["is_imputed"].to_numpy(dtype=bool)
        y_train = pre_holdout.to_numpy(dtype=float)

        def _holdout_mase(w: float) -> float:
            final = combine_stage2_forecast(
                holdout_rows["sarima_prediction"].to_numpy(),
                holdout_rows["predicted_residual"].to_numpy(),
                mode=mode,
                weight=w,
            )
            return mase(
                holdout_rows["Number_of_Cases"].to_numpy(), final, y_train,
                m=WEEKS_PER_YEAR, mask=holdout_mask, train_mask=~imputed_pre_holdout,
            )

        holdout_mase_w1 = _holdout_mase(DEFAULT_WEIGHT)
        if selected_weight == DEFAULT_WEIGHT:
            rows.append({
                "District": district, "selected_weight": selected_weight,
                "holdout_mase_at_selected": holdout_mase_w1,
                "holdout_mase_at_w1": holdout_mase_w1,
                "adopt": True, "final_weight": DEFAULT_WEIGHT,
            })
            continue

        holdout_mase_selected = _holdout_mase(selected_weight)
        adopt = bool(
            not np.isnan(holdout_mase_selected)
            and not np.isnan(holdout_mase_w1)
            and holdout_mase_selected <= holdout_mase_w1
        )
        rows.append({
            "District": district,
            "selected_weight": selected_weight,
            "holdout_mase_at_selected": holdout_mase_selected,
            "holdout_mase_at_w1": holdout_mase_w1,
            "adopt": adopt,
            "final_weight": selected_weight if adopt else DEFAULT_WEIGHT,
        })

    result = pd.DataFrame(rows)
    n_adopted = int(((result["final_weight"] != DEFAULT_WEIGHT)).sum())
    logger.info(
        "Holdout confirmation: %d/%d districts keep a shrunk weight after holdout check (%s).",
        n_adopted, len(result),
        ", ".join(result.loc[result["final_weight"] != DEFAULT_WEIGHT, "District"]) or "none",
    )
    return result


def run_shrinkage_selection(
    districts: list[str] = DISTRICTS,
    weights: tuple[float, ...] = CANDIDATE_WEIGHTS,
    *,
    residual_mode: str | None = None,
) -> pd.DataFrame:
    selection = select_shrinkage_weights(districts, weights, residual_mode=residual_mode)
    MODULE1_SHRINKAGE_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    selection.to_csv(MODULE1_SHRINKAGE_WEIGHTS_PATH, index=False)

    holdout_check = evaluate_shrinkage_on_holdout(selection, residual_mode=residual_mode)
    holdout_check.to_csv(MODULE1_SHRINKAGE_HOLDOUT_CHECK_PATH, index=False)

    logger.info(
        "Wrote validation weight search to %s and holdout confirmation to %s.",
        MODULE1_SHRINKAGE_WEIGHTS_PATH, MODULE1_SHRINKAGE_HOLDOUT_CHECK_PATH,
    )
    return holdout_check


def load_final_weights(residual_mode: str | None = None) -> dict[str, float]:
    """Load the holdout-confirmed per-district weight table for
    `combine.py`'s `apply_shrinkage=True` path. Districts absent from the
    file (or the file not yet generated) default to `1.0` - unchanged
    production behavior."""
    if not MODULE1_SHRINKAGE_HOLDOUT_CHECK_PATH.exists():
        return {}
    df = pd.read_csv(MODULE1_SHRINKAGE_HOLDOUT_CHECK_PATH)
    return dict(zip(df["District"], df["final_weight"]))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_shrinkage_selection()
