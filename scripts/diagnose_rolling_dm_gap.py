"""M1-011: root-cause Open Question #17 (rolling-mode Stage 2 benefit gap).

M1-008 found that under the rolling one-step-ahead evaluation (SARIMA
refit weekly, frozen `xgboost_final_model.json` Stage 2), only 10/25
districts show Stage 2 helping at all, and only 2/25 reach DM significance
(both negative) - a much weaker picture than the validated walk-forward/
holdout backtest's 23/25-improve headline. This script distinguishes three
candidate explanations without any retraining:

(a) the frozen final model generalizes poorly to slightly different SARIMA
    inputs than it was trained on;
(b) weekly-refit SARIMA is itself noisier than fold-refit SARIMA (an input-
    distribution shift), independent of which Stage 2 model scores it;
(c) Stage 2 overfits fold-specific SARIMA error patterns rather than
    learning a genuinely general correction.

Method
------
1. **SARIMA drift**: merge the already-completed rolling run's
   `sarima_prediction` (weekly-refit) against the walk-forward fold-refit
   `sarima_prediction` for the same `(District, Year, Week)` rows. Large,
   systematic drift would support (b).
2. **Fold-matched-model rescoring**: re-score every already-rolling-scored
   week using the WALK-FORWARD FOLD MODEL that was actually responsible for
   that week under the original scheme (`models/module1/xgboost_folds/
   fold_{k}.json` / `holdout.json`, resolved via `compensation_model.
   compute_fold_boundaries()`), applied to the SAME feature row the rolling
   evaluator already computed - `rolling_one_step_district()`'s new
   `sarima_prediction_overrides`/`model_resolver` parameters make this a
   pure recombination (no SARIMAX refitting, no XGBoost retraining).
   Recovering most of the holdout-level improvement here would support
   (a)/(c) - the *frozen final model* is the problem, not weekly refitting
   itself. Not recovering it points to (b).
3. **Per-row correlation**: correlate per-row SARIMA drift magnitude against
   per-row rolling final-prediction error - a direct, independent check on
   (b).

This is evidence-gathering only. No model or feature is selected/promoted
here - any actionable finding becomes a separate, explicitly holdout-gated
follow-up decision.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    M1_STAGE2_RESIDUAL_MODE,
    MODULE1_METRICS_DIR,
    MODULE1_ROLLING_ONE_STEP_PATH,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE1_XGBOOST_MODELS_DIR,
    module1_stage2_paths,
)
from src.module1_forecasting.compensation_model import N_FOLDS, compute_fold_boundaries  # noqa: E402
from src.module1_forecasting.residual_transform import validate_residual_mode  # noqa: E402
from src.module1_forecasting.rolling_one_step import (  # noqa: E402
    _load_selected_configs,
    compute_dm_results_rolling,
    rolling_one_step_district,
)
from src.module1_forecasting.validation import DEFAULT_MIN_TRAIN_YEARS, DEFAULT_WEEKS_PER_YEAR  # noqa: E402

logger = logging.getLogger(__name__)

DIAGNOSIS_PATH = MODULE1_METRICS_DIR / "rolling_dm_gap_diagnosis.csv"
FOLD_MATCHED_DM_PATH = MODULE1_METRICS_DIR / "rolling_one_step_dm_test_fold_matched.csv"


class _ZeroModel:
    """Stand-in for fold 1's documented no-op (predicted_residual == 0)."""

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.zeros(len(X), dtype=float)


_ZERO_MODEL = _ZeroModel()


def _load_fold_model(label) -> xgb.XGBRegressor:
    m = xgb.XGBRegressor()
    filename = f"fold_{label}.json" if isinstance(label, int) else f"{label}.json"
    m.load_model(str(MODULE1_XGBOOST_MODELS_DIR / filename))
    return m


def build_fold_resolver_factory(weekly_df: pd.DataFrame):
    """Returns (`resolver_factory(district) -> resolver(year, week)`,
    `fallback_counter` dict) - `resolver_factory` closes over one shared
    model cache so each fold's pooled model is loaded from disk only once
    across all 25 districts."""
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(weekly_df)
    model_cache: dict = {}
    fallback_counts: dict[str, int] = {}

    def _cached(label):
        if label not in model_cache:
            model_cache[label] = _load_fold_model(label)
        return model_cache[label]

    def resolver_factory(district: str):
        fallback_counts.setdefault(district, 0)

        def resolver(year: int, week: int):
            key = (district, int(year), int(week))
            for fold_id in range(2, N_FOLDS + 1):
                if key in fold_val_keys[fold_id]:
                    return _cached(fold_id)
            if key in fold_val_keys[1]:
                return _ZERO_MODEL
            if key in holdout_keys:
                return _cached("holdout")
            # Structural ~26-week gap between fold N_FOLDS's validation end
            # and the holdout block's start (Decision 015) - no fold "owns"
            # these weeks under the original scheme. Fall back to the most
            # recent fold's model (closest in time) and count it, rather
            # than silently pretending it's unambiguous.
            fallback_counts[district] += 1
            return _cached(N_FOLDS)

        return resolver

    return resolver_factory, fallback_counts


def compare_sarima_drift(rolling_df: pd.DataFrame, fold_refit_df: pd.DataFrame) -> pd.DataFrame:
    fold_refit = fold_refit_df[["District", "Year", "Week", "sarima_prediction"]].rename(
        columns={"sarima_prediction": "sarima_prediction_fold_refit"}
    )
    merged = rolling_df[["District", "Year", "Week", "sarima_prediction", "Number_of_Cases", "final_prediction"]].rename(
        columns={"sarima_prediction": "sarima_prediction_weekly_refit"}
    ).merge(fold_refit, on=["District", "Year", "Week"], how="inner")
    merged["sarima_drift"] = merged["sarima_prediction_weekly_refit"] - merged["sarima_prediction_fold_refit"]
    merged["abs_drift"] = merged["sarima_drift"].abs()
    merged["rolling_abs_error"] = (merged["Number_of_Cases"] - merged["final_prediction"]).abs()

    rows = []
    for district, g in merged.groupby("District"):
        g = g.dropna(subset=["sarima_drift", "rolling_abs_error"])
        corr = float(g["abs_drift"].corr(g["rolling_abs_error"])) if len(g) > 2 else float("nan")
        rows.append({
            "District": district,
            "n_matched_weeks": len(g),
            "mean_abs_drift": float(g["abs_drift"].mean()) if len(g) else float("nan"),
            "median_abs_drift": float(g["abs_drift"].median()) if len(g) else float("nan"),
            "corr_sarima_pred": float(g["sarima_prediction_weekly_refit"].corr(g["sarima_prediction_fold_refit"])) if len(g) > 2 else float("nan"),
            "corr_drift_vs_rolling_error": corr,
        })
    return pd.DataFrame(rows)


def run_fold_matched_rescoring(
    weekly_df: pd.DataFrame,
    rolling_df: pd.DataFrame,
    districts: list[str] = DISTRICTS,
    *,
    residual_mode: str | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    mode = validate_residual_mode(residual_mode or M1_STAGE2_RESIDUAL_MODE)
    paths = module1_stage2_paths(mode)
    sarima_configs = _load_selected_configs()

    frozen_model = xgb.XGBRegressor()
    frozen_model.load_model(str(paths["xgboost_final_model"]))  # unused fallback arg, required by signature

    resolver_factory, fallback_counts = build_fold_resolver_factory(weekly_df)
    min_train_weeks = DEFAULT_MIN_TRAIN_YEARS * DEFAULT_WEEKS_PER_YEAR

    frames = []
    for district in districts:
        dist_rolling = rolling_df.loc[rolling_df["District"] == district]
        overrides = {
            (int(y), int(w)): float(s)
            for y, w, s in zip(dist_rolling["Year"], dist_rolling["Week"], dist_rolling["sarima_prediction"])
        }
        result = rolling_one_step_district(
            district, weekly_df, sarima_configs[district], frozen_model,
            min_train_weeks=min_train_weeks, target_keys=None, residual_mode=mode,
            sarima_prediction_overrides=overrides,
            model_resolver=resolver_factory(district),
        )
        logger.info("Fold-matched rescoring done: %s (%d rows, %d structural-gap fallbacks).",
                     district, len(result), fallback_counts[district])
        frames.append(result)

    return pd.concat(frames, ignore_index=True), fallback_counts


def main() -> None:
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])
    rolling_df = pd.read_csv(MODULE1_ROLLING_ONE_STEP_PATH)
    fold_refit_df = pd.read_csv(MODULE1_SARIMA_PREDICTIONS_PATH)

    logger.info("Step 1/3: comparing weekly-refit vs fold-refit SARIMA predictions...")
    drift = compare_sarima_drift(rolling_df, fold_refit_df)

    logger.info("Step 2/3: fold-matched-model rescoring (no SARIMA refit, no retraining)...")
    fold_matched_df, fallback_counts = run_fold_matched_rescoring(weekly_df, rolling_df)
    fold_matched_df.to_csv(
        MODULE1_ROLLING_ONE_STEP_PATH.with_name("rolling_one_step_predictions_fold_matched.csv"), index=False
    )
    dm_fold_matched = compute_dm_results_rolling(fold_matched_df, scope="all_fold_matched")
    dm_fold_matched.to_csv(FOLD_MATCHED_DM_PATH, index=False)

    dm_original_path = MODULE1_METRICS_DIR / "rolling_one_step_dm_test.csv"
    dm_original = pd.read_csv(dm_original_path)

    logger.info("Step 3/3: assembling comparison + verdict...")
    comparison = drift.merge(
        dm_original[["District", "p_value", "mean_loss_diff"]].rename(
            columns={"p_value": "p_value_frozen_model", "mean_loss_diff": "mean_loss_diff_frozen_model"}
        ),
        on="District", how="left",
    ).merge(
        dm_fold_matched[["District", "p_value", "mean_loss_diff"]].rename(
            columns={"p_value": "p_value_fold_matched", "mean_loss_diff": "mean_loss_diff_fold_matched"}
        ),
        on="District", how="left",
    )
    comparison["n_structural_gap_fallbacks"] = comparison["District"].map(fallback_counts)
    MODULE1_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(DIAGNOSIS_PATH, index=False)

    n_helps_frozen = int((dm_original["mean_loss_diff"] > 0).sum())
    n_helps_fold_matched = int((dm_fold_matched["mean_loss_diff"] > 0).sum())
    n_sig_frozen = int((dm_original["p_value"] < 0.05).sum())
    n_sig_fold_matched = int((dm_fold_matched["p_value"] < 0.05).sum())
    mean_drift = comparison["mean_abs_drift"].mean()
    mean_corr_pred = comparison["corr_sarima_pred"].mean()
    mean_corr_drift_error = comparison["corr_drift_vs_rolling_error"].mean()

    logger.info("=" * 70)
    logger.info("SARIMA drift (weekly-refit vs fold-refit): mean |drift| across districts = %.2f cases", mean_drift)
    logger.info("Mean correlation(weekly-refit, fold-refit) sarima_prediction = %.4f", mean_corr_pred)
    logger.info("Mean correlation(|drift|, rolling final-prediction error) = %.4f", mean_corr_drift_error)
    logger.info("-" * 70)
    logger.info("Districts with Stage 2 helping (mean_loss_diff>0): frozen model = %d/25, fold-matched = %d/25",
                n_helps_frozen, n_helps_fold_matched)
    logger.info("Districts DM-significant (p<0.05): frozen model = %d/25, fold-matched = %d/25",
                n_sig_frozen, n_sig_fold_matched)
    logger.info("=" * 70)
    logger.info("Wrote diagnosis to %s and fold-matched DM results to %s.", DIAGNOSIS_PATH, FOLD_MATCHED_DM_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    main()
