"""M1-023/M1-024 pilot - walk-forward train/evaluate the direct h=2/3/4
models built from `direct_horizon_pilot.py`'s output, and compare each
against SARIMA-h-alone and the current recursive approach's output at the
same horizon, on the SAME held-out rows.

Reuses `compensation_model.py`'s exact fold boundaries
(`compute_fold_boundaries`), hyperparameters (`XGB_BASE_PARAMS`), and
training/early-stopping recipe (`train_and_predict_fold`/
`train_and_predict_holdout`) - the ONLY thing that differs from the
production h=1 model is which rows/target feed it (this pilot's origin-
anchored, h-shifted table instead of the production h=1 table), run
separately for each horizon 2, 3, 4.

Run standalone: `python -m src.module1_forecasting.direct_horizon_pilot_eval`
(after `direct_horizon_pilot.py`/`scripts/run_direct_horizon_pilot_parallel.py`
has produced `MODULE1_DIRECT_HORIZON_PILOT_PATH`).
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
    MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH,
    MODULE1_DIRECT_HORIZON_PILOT_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
)
from src.module1_forecasting.compensation_model import (  # noqa: E402
    FEATURE_COLUMNS,
    IMPUTED_COL,
    N_FOLDS,
    TARGET_COL,
    compute_fold_boundaries,
    train_and_predict_fold,
    train_and_predict_holdout,
)
from src.module1_forecasting.evaluate import dm_test, mase, smape  # noqa: E402

logger = logging.getLogger(__name__)

HORIZONS = (2, 3, 4)


def _load_pilot_table_for_horizon(raw: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Build a `FEATURE_COLUMNS`-shaped, `stage2_df`-compatible table for one
    horizon: origin-anchored `feat__*` columns (shared across all horizons)
    plus that horizon's own `sarima_h{H}` value substituted in as
    `sarima_prediction`, and `stage2_target_h{H}` as the training target."""
    df = raw.rename(columns={"origin_Year": "Year", "origin_Week": "Week"}).copy()
    feat_cols = [c for c in df.columns if c.startswith("feat__")]
    for c in feat_cols:
        df[c.removeprefix("feat__")] = df[c]
    df["sarima_prediction"] = df[f"sarima_h{horizon}"]
    df[TARGET_COL] = df[f"stage2_target_h{horizon}"]
    df[IMPUTED_COL] = df[f"is_imputed_h{horizon}"].astype(bool)
    df["actual_target"] = df[f"actual_h{horizon}"]
    df["final_prediction_recursive"] = df[f"final_prediction_recursive_h{horizon}"]
    df["sarima_alone"] = df[f"sarima_h{horizon}"]
    keep = ["Year", "Week", TARGET_COL, IMPUTED_COL, "actual_target",
            "final_prediction_recursive", "sarima_alone"] + FEATURE_COLUMNS
    seen: set[str] = set()
    ordered_unique = [c for c in keep if c in df.columns and not (c in seen or seen.add(c))]
    return df[ordered_unique].copy()


def _assign_folds(df: pd.DataFrame, weekly_df: pd.DataFrame) -> pd.DataFrame:
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(weekly_df)
    key = list(zip(df["District"], df["Year"].astype(int), df["Week"].astype(int)))

    fold_id_numeric = np.full(len(df), np.nan)
    for fold_id, val_keys in fold_val_keys.items():
        mask = [k in val_keys for k in key]
        fold_id_numeric[mask] = fold_id
    df["fold_id_numeric"] = fold_id_numeric

    split = np.where([k in holdout_keys for k in key], "holdout", "pre_holdout")
    df["split"] = split
    return df


def _train_direct_model(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    predicted_residual = np.full(len(df), np.nan)
    fold_trained = np.zeros(len(df), dtype=bool)

    for fold_num in range(1, N_FOLDS + 1):
        mask = df["fold_id_numeric"] == fold_num
        if not mask.any():
            continue
        preds, trained, _ = train_and_predict_fold(df, fold_num, feature_columns=FEATURE_COLUMNS)
        predicted_residual[mask.to_numpy()] = preds
        fold_trained[mask.to_numpy()] = trained

    holdout_mask = df["split"] == "holdout"
    if holdout_mask.any():
        holdout_preds, _ = train_and_predict_holdout(df, feature_columns=FEATURE_COLUMNS)
        predicted_residual[holdout_mask.to_numpy()] = holdout_preds
        fold_trained[holdout_mask.to_numpy()] = True

    return predicted_residual, fold_trained


def run_eval() -> pd.DataFrame:
    raw = pd.read_csv(MODULE1_DIRECT_HORIZON_PILOT_PATH)
    weekly_df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])

    all_comparison = []
    all_dm = []

    for horizon in HORIZONS:
        df = _load_pilot_table_for_horizon(raw, horizon)
        df = _assign_folds(df, weekly_df)
        predicted_residual, fold_trained = _train_direct_model(df)

        df["final_prediction_direct"] = np.clip(df["sarima_alone"] + predicted_residual, 0.0, None)
        scored = df.loc[fold_trained & ~df[IMPUTED_COL]].copy()
        logger.info("Horizon h=%d: scored %d/%d rows across %d districts.",
                    horizon, len(scored), len(df), scored["District"].nunique())

        for district in sorted(scored["District"].unique()):
            d = scored.loc[scored["District"] == district]
            y_train = weekly_df.loc[weekly_df["District"] == district, "Number_of_Cases"].to_numpy(dtype=float)
            for split_name, sub in [("pre_holdout", d.loc[d["split"] == "pre_holdout"]), ("holdout", d.loc[d["split"] == "holdout"]), ("all", d)]:
                if sub.empty:
                    continue
                actual = sub["actual_target"].to_numpy(dtype=float)
                for approach, pred_col in [
                    ("sarima_alone", "sarima_alone"),
                    ("recursive", "final_prediction_recursive"),
                    ("direct", "final_prediction_direct"),
                ]:
                    pred = sub[pred_col].to_numpy(dtype=float)
                    all_comparison.append({
                        "horizon": horizon, "District": district, "split": split_name, "approach": approach, "n": len(sub),
                        "mae": float(np.nanmean(np.abs(actual - pred))),
                        "mase": mase(actual, pred, y_train, m=52),
                        "smape_pct": smape(actual, pred),
                    })

        for district in sorted(scored["District"].unique()):
            d = scored.loc[scored["District"] == district]
            actual = d["actual_target"].to_numpy(dtype=float)
            e_sarima = actual - d["sarima_alone"].to_numpy(dtype=float)
            e_recursive = actual - d["final_prediction_recursive"].to_numpy(dtype=float)
            e_direct = actual - d["final_prediction_direct"].to_numpy(dtype=float)
            row = {"horizon": horizon, "District": district}
            row.update({f"vs_recursive_{k}": v for k, v in dm_test(e_recursive, e_direct, loss="squared").items()})
            row.update({f"vs_sarima_{k}": v for k, v in dm_test(e_sarima, e_direct, loss="squared").items()})
            all_dm.append(row)

    comparison = pd.DataFrame(all_comparison)
    dm_results = pd.DataFrame(all_dm)

    MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_csv(MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH, index=False)
    dm_out = MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH.with_name(
        MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH.stem + "_dm.csv"
    )
    dm_results.to_csv(dm_out, index=False)
    logger.info("Wrote %d comparison rows -> %s, %d DM rows -> %s.",
                len(comparison), MODULE1_DIRECT_HORIZON_PILOT_COMPARISON_PATH, len(dm_results), dm_out)

    pooled = comparison.loc[comparison["split"] == "holdout"].groupby(["horizon", "approach"])[["mase", "smape_pct"]].median()
    logger.info("Median-across-districts, holdout only:\n%s", pooled.to_string())

    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_eval()
