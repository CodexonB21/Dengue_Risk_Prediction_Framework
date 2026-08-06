"""M2-014: does a leakage-safe LAGGED Module 3 spatial-risk feature improve
Stage 1, where the earlier same-week version of this idea had a real
leakage bug (see `src/module2_classification/m3_risk_join.py`'s docstring)?

Benchmarks the official Random Forest (Decision 025, `RF_PARAMS` unchanged -
this experiment isolates the FEATURE SET question from the hyperparameter
question already covered by M2-013) with vs. without two new features,
`m3_risk_lag_1`/`m3_risk_lag_2` (Module 3's Hybrid Risk score from the prior
1-2 weeks, same district), across the same 13 walk-forward validation folds,
holdout-gated once for the winner - identical protocol to every other Stage
1 experiment in this log (M2-010, M2-013).

Does NOT modify `baseline_classifier.py`'s `fit_and_predict` (its numeric
column resolution is anchored to the fixed `NUMERIC_FEATURE_COLUMNS`
constant, so passing a genuinely new column name through its existing
`feature_columns` argument would be silently dropped) - this script builds
its own self-contained RF fit/predict step, reusing
`build_sklearn_preprocessor`'s existing `numeric_feature_columns` override
directly, so the comparison is still built from the exact same preprocessing
pipeline Stage 1 already uses.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import MODULE2_METRICS_DIR, MODULE3_HYBRID_RISK_MAP_PATH  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    CATEGORICAL_FEATURE_COLUMNS,
    N_FOLDS,
    NUMERIC_FEATURE_COLUMNS,
    RF_PARAMS,
    TARGET_COL,
    assemble_labeled_feature_table,
    attach_fold_anomalies,
    build_sklearn_preprocessor,
    compute_fold_boundaries,
)
from src.module2_classification.m3_risk_join import (  # noqa: E402
    M3_RISK_FEATURE_COLUMNS,
    build_m3_risk_lags,
    load_m3_risk_predictions,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COMPARISON_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_014_m3_risk_feature_comparison.csv"
HOLDOUT_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_014_m3_risk_feature_holdout.csv"

WITH_M3_NUMERIC_COLUMNS = NUMERIC_FEATURE_COLUMNS + M3_RISK_FEATURE_COLUMNS


def fit_rf_predict(train_df: pd.DataFrame, val_df: pd.DataFrame, numeric_cols: list[str]) -> np.ndarray:
    X_train = train_df[numeric_cols + CATEGORICAL_FEATURE_COLUMNS]
    X_val = val_df[numeric_cols + CATEGORICAL_FEATURE_COLUMNS]
    preprocessor = build_sklearn_preprocessor(include_scaler=False, numeric_feature_columns=numeric_cols)
    pipeline = Pipeline([("preprocess", preprocessor), ("clf", RandomForestClassifier(**RF_PARAMS))])
    pipeline.fit(X_train, train_df[TARGET_COL].to_numpy(dtype=int))
    return pipeline.predict_proba(X_val)[:, 1]


def _score_on_folds(df: pd.DataFrame, fold_train_keys: dict, fold_val_keys: dict, numeric_cols: list[str]) -> list[float]:
    pr_aucs = []
    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)
        trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
        val_rows_all = fold_df.loc[val_mask]
        proba = fit_rf_predict(trainable_train, val_rows_all, numeric_cols)
        pr_aucs.append(evaluate.pr_auc(val_rows_all[TARGET_COL].to_numpy(dtype=float), proba))
    return pr_aucs


def _score_on_holdout(df: pd.DataFrame, pre_holdout_keys: set, holdout_keys: set, numeric_cols: list[str]) -> dict:
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)
    trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = fold_df.loc[val_mask]
    proba = fit_rf_predict(trainable_train, val_rows_all, numeric_cols)
    y_true = val_rows_all[TARGET_COL].to_numpy(dtype=float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba),
        "roc_auc": evaluate.roc_auc(y_true, proba),
        "brier_score": evaluate.brier_score(y_true, proba),
    }


def main() -> None:
    print("\n" + "=" * 92)
    print("M2-014: LEAKAGE-SAFE LAGGED MODULE 3 RISK FEATURE - STAGE 1 COMPARISON")
    print("=" * 92)

    df = assemble_labeled_feature_table()
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(df)

    m3 = load_m3_risk_predictions(MODULE3_HYBRID_RISK_MAP_PATH)
    lags = build_m3_risk_lags(df, m3)
    df = df.merge(lags, on=["District", "Year", "Week"], how="left")
    coverage = df.loc[df["label"].notna(), "m3_risk_lag_1"].notna().mean()
    print(f"m3_risk_lag_1 coverage on defined-label rows: {coverage:.1%}")

    print("\nWithout Module 3 feature (current official feature set):")
    pr_aucs_without = _score_on_folds(df, fold_train_keys, fold_val_keys, NUMERIC_FEATURE_COLUMNS)
    median_without = float(np.nanmedian(pr_aucs_without))
    print(f"Median validation PR-AUC (13 folds): {median_without:.4f}")

    print("\nWith m3_risk_lag_1/2 added:")
    pr_aucs_with = _score_on_folds(df, fold_train_keys, fold_val_keys, WITH_M3_NUMERIC_COLUMNS)
    median_with = float(np.nanmedian(pr_aucs_with))
    print(f"Median validation PR-AUC (13 folds): {median_with:.4f}")

    comparison_df = pd.DataFrame(
        [
            {"candidate": "without_m3_risk", "median_pr_auc": median_without},
            {"candidate": "with_m3_risk_lag", "median_pr_auc": median_with},
        ]
    )
    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    comparison_df.to_csv(COMPARISON_OUTPUT_PATH, index=False)

    print("\n" + "=" * 92)
    print("VALIDATION VERDICT (all 13 folds)")
    print("=" * 92)
    print(comparison_df.to_string(index=False))

    if median_with <= median_without + 1e-9:
        print(
            f"\nRESULT: adding the lagged Module 3 risk feature does NOT beat the current feature set "
            f"({median_with:.4f} vs {median_without:.4f}). Holdout NOT checked. Negative result."
        )
        return

    print(
        f"\n'with_m3_risk_lag' beats the current feature set on validation "
        f"(+{median_with - median_without:.4f} median PR-AUC) - spending the one-time holdout check."
    )
    holdout_without = _score_on_holdout(df, pre_holdout_keys, holdout_keys, NUMERIC_FEATURE_COLUMNS)
    holdout_with = _score_on_holdout(df, pre_holdout_keys, holdout_keys, WITH_M3_NUMERIC_COLUMNS)

    print("\n" + "=" * 92)
    print("HOLDOUT CHECK (touched once)")
    print("=" * 92)
    holdout_df = pd.DataFrame(
        [{"candidate": "without_m3_risk", **holdout_without}, {"candidate": "with_m3_risk_lag", **holdout_with}]
    )
    print(holdout_df.to_string(index=False))
    holdout_df.to_csv(HOLDOUT_OUTPUT_PATH, index=False)

    if holdout_with["pr_auc"] > holdout_without["pr_auc"]:
        print("\nRESULT: the Module 3 risk feature beats the current feature set on BOTH validation AND holdout. Candidate for promotion.")
    else:
        print(
            f"\nRESULT: won on validation but did NOT beat the current feature set on holdout "
            f"({holdout_with['pr_auc']:.4f} vs {holdout_without['pr_auc']:.4f}). NOT promoted."
        )


if __name__ == "__main__":
    main()
