"""Module 2 Stage 1 - XGBoost hyperparameter tuning (Decision 023).

Standalone research script (mirrors `stage1_calibration_diagnostic.py`'s
pattern) - NOT wired into `main.py`'s pipeline, since it makes a one-off
recommendation for a human/agent to review, not a repeatable production step.

Methodology, and why it is deliberately NOT the same as Stage 1's own model
selection:

Stage 1's official model (Decision 021) was already chosen by picking
whichever of 3 model TYPES had the highest median PR-AUC across the same 13
walk-forward validation folds it is then reported against - a mild, accepted
form of the test folds influencing the choice, tolerable because the search
space was tiny (3 candidates). Hyperparameter tuning searches a much larger
space (~100 Optuna trials here) against that exact same 13-fold median
PR-AUC. If we let the reported "did tuning help" number be MEASURED on the
same folds it was SEARCHED against, that number is an optimistic, overfit
estimate almost by construction - not a genuine claim of accuracy
improvement.

The fix: the 13-fold median PR-AUC is used ONLY to propose a candidate
(Optuna's optimization target). The untouched holdout block - genuinely
never seen during this search, exactly as it is never seen during Stage 1's
own model-type selection - is the ONLY number this script treats as honest
evidence for whether tuning actually improved generalization. The adopt/
reject recommendation printed at the end is based on the HOLDOUT comparison,
never the fold-median search value.

Usage:
    python scripts/tune_stage1_xgboost.py [--trials N]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import optuna
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    N_FOLDS,
    TARGET_COL,
    XGB_BASE_PARAMS,
    assemble_labeled_feature_table,
    attach_fold_anomalies,
    compute_fold_boundaries,
    fit_and_predict,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

TRIALS_OUTPUT_PATH = ROOT / "outputs" / "metrics" / "module2" / "xgboost_tuning_trials.csv"
HOLDOUT_COMPARISON_OUTPUT_PATH = ROOT / "outputs" / "metrics" / "module2" / "xgboost_tuning_holdout_comparison.csv"

# Kept fixed across every trial - these are not being tuned, they are
# structural choices (objective/tree method) or leakage-safety properties
# (scale_pos_weight is always recomputed per fold inside fit_and_predict,
# regardless of what's passed here).
FIXED_XGB_KEYS = dict(
    objective="binary:logistic",
    eval_metric="aucpr",
    tree_method="hist",
    enable_categorical=True,
    random_state=42,
)


def build_full_params(tunable_params: dict) -> dict:
    return {**FIXED_XGB_KEYS, **tunable_params}


def _score_xgboost_on_folds(
    df: pd.DataFrame, fold_train_keys: dict[int, set], fold_val_keys: dict[int, set], xgb_params: dict,
) -> list[float]:
    """Run the same 13-fold walk-forward loop as `baseline_classifier.run_benchmark`,
    XGBoost only, with `xgb_params` substituted for `XGB_BASE_PARAMS`. Returns
    one PR-AUC per fold."""
    pr_aucs = []
    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
        val_rows_all = fold_df.loc[val_mask]

        proba, _ = fit_and_predict("xgboost", trainable_train, val_rows_all, xgb_params=xgb_params)
        pr_aucs.append(evaluate.pr_auc(val_rows_all[TARGET_COL].to_numpy(dtype=float), proba))
    return pr_aucs


def _score_xgboost_on_holdout(
    df: pd.DataFrame, pre_holdout_keys: set, holdout_keys: set, xgb_params: dict,
) -> dict:
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)

    trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = fold_df.loc[val_mask]

    proba, _ = fit_and_predict("xgboost", trainable_train, val_rows_all, xgb_params=xgb_params)
    y_true = val_rows_all[TARGET_COL].to_numpy(dtype=float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba),
        "roc_auc": evaluate.roc_auc(y_true, proba),
        "brier_score": evaluate.brier_score(y_true, proba),
        "brier_skill_score": evaluate.brier_skill_score(y_true, proba),
    }


def objective(trial: "optuna.Trial", df: pd.DataFrame, fold_train_keys: dict, fold_val_keys: dict) -> float:
    tunable = dict(
        max_depth=trial.suggest_int("max_depth", 3, 8),
        learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        n_estimators=trial.suggest_int("n_estimators", 100, 600),
        subsample=trial.suggest_float("subsample", 0.5, 1.0),
        colsample_bytree=trial.suggest_float("colsample_bytree", 0.5, 1.0),
        reg_lambda=trial.suggest_float("reg_lambda", 0.1, 10.0, log=True),
        min_child_weight=trial.suggest_int("min_child_weight", 1, 15),
        reg_alpha=trial.suggest_float("reg_alpha", 0.0, 5.0),
        gamma=trial.suggest_float("gamma", 0.0, 5.0),
    )
    params = build_full_params(tunable)
    pr_aucs = _score_xgboost_on_folds(df, fold_train_keys, fold_val_keys, params)
    return float(np.nanmedian(pr_aucs))


def _progress_callback(study: "optuna.Study", trial: "optuna.trial.FrozenTrial") -> None:
    if trial.number % 10 == 0 or trial.number == study.user_attrs.get("n_trials", 0) - 1:
        logger.info(
            "Trial %d done: median fold PR-AUC=%.4f (best so far=%.4f)",
            trial.number, trial.value, study.best_value,
        )


def run_search(n_trials: int, seed: int = 42):
    logger.info("Assembling labeled Stage 1 feature table and fold boundaries...")
    df = assemble_labeled_feature_table()
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(df)

    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name="stage1_xgboost_tuning")
    study.set_user_attr("n_trials", n_trials)

    logger.info("Starting Optuna search: %d trials, objective = median PR-AUC across %d walk-forward folds.", n_trials, N_FOLDS)
    study.optimize(
        lambda trial: objective(trial, df, fold_train_keys, fold_val_keys),
        n_trials=n_trials, callbacks=[_progress_callback],
    )
    return study, df, pre_holdout_keys, holdout_keys


def main(n_trials: int = 100) -> None:
    study, df, pre_holdout_keys, holdout_keys = run_search(n_trials=n_trials)

    logger.info("Search complete. Best median fold PR-AUC = %.4f. Best params: %s", study.best_value, study.best_params)

    TRIALS_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    trials_df = study.trials_dataframe().sort_values("value", ascending=False)
    trials_df.to_csv(TRIALS_OUTPUT_PATH, index=False)
    logger.info("Wrote full trial history -> %s", TRIALS_OUTPUT_PATH)

    logger.info("Scoring default vs. tuned hyperparameters on the untouched holdout block (the honest evidence)...")
    default_scores = _score_xgboost_on_holdout(df, pre_holdout_keys, holdout_keys, XGB_BASE_PARAMS)
    tuned_full_params = build_full_params(study.best_params)
    tuned_scores = _score_xgboost_on_holdout(df, pre_holdout_keys, holdout_keys, tuned_full_params)

    comparison_df = pd.DataFrame(
        [
            {"variant": "default (current XGB_BASE_PARAMS)", **default_scores, "params": XGB_BASE_PARAMS},
            {"variant": "tuned (optuna best trial)", **tuned_scores, "params": tuned_full_params},
        ]
    )
    comparison_df.to_csv(HOLDOUT_COMPARISON_OUTPUT_PATH, index=False)
    logger.info("Wrote holdout comparison -> %s", HOLDOUT_COMPARISON_OUTPUT_PATH)

    print("\n" + comparison_df[["variant", "pr_auc", "roc_auc", "brier_score", "brier_skill_score"]].to_string(index=False))

    pr_auc_delta = tuned_scores["pr_auc"] - default_scores["pr_auc"]
    print(f"\nHoldout PR-AUC: default={default_scores['pr_auc']:.4f} -> tuned={tuned_scores['pr_auc']:.4f} (delta {pr_auc_delta:+.4f})")
    if pr_auc_delta > 0:
        print(
            "RECOMMENDATION: ADOPT tuned hyperparameters - holdout PR-AUC (never touched during the search) genuinely "
            "improved. Update XGB_BASE_PARAMS in baseline_classifier.py with:\n"
            f"  {tuned_full_params}"
        )
    else:
        print(
            "RECOMMENDATION: REJECT tuned hyperparameters - holdout PR-AUC did not improve despite the search "
            "improving the (searched-against) fold-median PR-AUC. This is exactly the overfitting-to-validation-folds "
            "risk this script's holdout gate exists to catch. Keep the existing, deliberately conservative "
            "XGB_BASE_PARAMS (Decision 021)."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tune Stage 1's XGBoost hyperparameters via Optuna (Decision 023).")
    parser.add_argument("--trials", type=int, default=100, help="Number of Optuna trials (default: 100).")
    args = parser.parse_args()
    main(n_trials=args.trials)
