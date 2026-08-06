"""M2-013: three untried Stage 1 levers, benchmarked together -

1. `rf_balanced_subsample` - one-line change: `class_weight="balanced_subsample"`
   instead of the production `"balanced"` (RF-specific per-bootstrap
   reweighting, distinct in kind from the already-rejected SMOTE, Decision 026).
2. `rf_tuned` - Optuna search over Random Forest's OWN hyperparameters
   (`n_estimators`, `max_depth`, `min_samples_leaf`, `min_samples_split`,
   `max_features`), `class_weight="balanced"` held fixed (isolates this from
   lever #1). Random Forest became the official model only after Decision
   025's label re-estimation and has never itself been tuned - only
   XGBoost went through this treatment (Decision 023), for a Stage 1
   architecture that is no longer selected.
3. `gradient_boosting` - listed as a "possible Stage 1 model" in
   `MODULE_CONTEXT.md` but never benchmarked (Decision 021 only ran
   Logistic Regression/Random Forest/XGBoost). Conservative, untuned
   defaults (`GB_PARAMS`); imbalance handled via a fold-fresh sample_weight
   (no `class_weight` param exists on `GradientBoostingClassifier`).

Methodology mirrors `scripts/tune_stage1_xgboost.py` exactly: the 13-fold
median PR-AUC (Stage 1's own primary selection metric, Decision 021) is used
to find each candidate; the untouched holdout block is spent EXACTLY ONCE,
on whichever single candidate is best on validation - only if that
candidate actually beats the official Random Forest's own validation
median PR-AUC. Losing candidates are reported on validation only.

Usage:
    python scripts/m2_013_stage1_rf_refresh.py [--trials N]
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

from src.config import MODULE2_METRICS_DIR  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    GB_PARAMS,
    N_FOLDS,
    RF_PARAMS,
    TARGET_COL,
    assemble_labeled_feature_table,
    attach_fold_anomalies,
    compute_fold_boundaries,
    fit_and_predict,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
optuna.logging.set_verbosity(optuna.logging.WARNING)

TRIALS_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_013_rf_tuning_trials.csv"
COMPARISON_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_013_stage1_refresh_comparison.csv"
HOLDOUT_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_013_stage1_refresh_holdout.csv"

OFFICIAL_MODEL_NAME = "random_forest"
RF_BALANCED_SUBSAMPLE_PARAMS = {**RF_PARAMS, "class_weight": "balanced_subsample"}


def section(title: str) -> None:
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)


def _score_on_folds(
    df: pd.DataFrame, fold_train_keys: dict, fold_val_keys: dict, model_name: str, model_params: dict | None,
) -> list[float]:
    """Same 13-fold walk-forward loop `baseline_classifier.run_benchmark`
    uses, one model/param-set at a time."""
    pr_aucs = []
    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
        val_rows_all = fold_df.loc[val_mask]

        proba, _ = fit_and_predict(model_name, trainable_train, val_rows_all, model_params=model_params)
        pr_aucs.append(evaluate.pr_auc(val_rows_all[TARGET_COL].to_numpy(dtype=float), proba))
    return pr_aucs


def _score_on_holdout(
    df: pd.DataFrame, pre_holdout_keys: set, holdout_keys: set, model_name: str, model_params: dict | None,
) -> dict:
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)

    trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = fold_df.loc[val_mask]

    proba, _ = fit_and_predict(model_name, trainable_train, val_rows_all, model_params=model_params)
    y_true = val_rows_all[TARGET_COL].to_numpy(dtype=float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba),
        "roc_auc": evaluate.roc_auc(y_true, proba),
        "brier_score": evaluate.brier_score(y_true, proba),
    }


def rf_optuna_objective(trial: "optuna.Trial", df: pd.DataFrame, fold_train_keys: dict, fold_val_keys: dict) -> float:
    params = dict(
        n_estimators=trial.suggest_int("n_estimators", 100, 600),
        max_depth=trial.suggest_int("max_depth", 3, 20),
        min_samples_leaf=trial.suggest_int("min_samples_leaf", 1, 20),
        min_samples_split=trial.suggest_int("min_samples_split", 2, 30),
        max_features=trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
        class_weight="balanced",  # fixed - isolates this search from lever #1 (balanced_subsample)
        random_state=42,
        n_jobs=-1,
    )
    pr_aucs = _score_on_folds(df, fold_train_keys, fold_val_keys, "random_forest", params)
    return float(np.nanmedian(pr_aucs))


def main(n_trials: int) -> None:
    section("M2-013: STAGE 1 REFRESH - balanced_subsample / RF tuning / Gradient Boosting")
    logger.info("Assembling labeled Stage 1 feature table and fold boundaries...")
    df = assemble_labeled_feature_table()
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(df)

    results = []

    section("Lever #1: random_forest with class_weight='balanced_subsample'")
    pr_aucs_1 = _score_on_folds(df, fold_train_keys, fold_val_keys, "random_forest", RF_BALANCED_SUBSAMPLE_PARAMS)
    median_1 = float(np.nanmedian(pr_aucs_1))
    print(f"Median validation PR-AUC (13 folds): {median_1:.4f}")
    results.append({"candidate": "rf_balanced_subsample", "median_pr_auc": median_1, "params": RF_BALANCED_SUBSAMPLE_PARAMS})

    section(f"Lever #2: random_forest tuned via Optuna ({n_trials} trials, class_weight='balanced' fixed)")
    sampler = optuna.samplers.TPESampler(seed=42)
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name="m2_013_rf_tuning")
    study.optimize(lambda t: rf_optuna_objective(t, df, fold_train_keys, fold_val_keys), n_trials=n_trials)
    logger.info("RF tuning complete. Best median fold PR-AUC = %.4f. Best params: %s", study.best_value, study.best_params)
    tuned_params = {**study.best_params, "class_weight": "balanced", "random_state": 42, "n_jobs": -1}
    results.append({"candidate": "rf_tuned", "median_pr_auc": float(study.best_value), "params": tuned_params})
    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    study.trials_dataframe().sort_values("value", ascending=False).to_csv(TRIALS_OUTPUT_PATH, index=False)

    section("Lever #3: gradient_boosting (untuned, GB_PARAMS + fold-fresh sample_weight)")
    pr_aucs_3 = _score_on_folds(df, fold_train_keys, fold_val_keys, "gradient_boosting", GB_PARAMS)
    median_3 = float(np.nanmedian(pr_aucs_3))
    print(f"Median validation PR-AUC (13 folds): {median_3:.4f}")
    results.append({"candidate": "gradient_boosting", "median_pr_auc": median_3, "params": GB_PARAMS})

    section("Reference: official random_forest (production RF_PARAMS)")
    pr_aucs_official = _score_on_folds(df, fold_train_keys, fold_val_keys, "random_forest", RF_PARAMS)
    median_official = float(np.nanmedian(pr_aucs_official))
    print(f"Median validation PR-AUC (13 folds): {median_official:.4f}")
    results.append({"candidate": "random_forest_official", "median_pr_auc": median_official, "params": RF_PARAMS})

    comparison_df = pd.DataFrame(results).sort_values("median_pr_auc", ascending=False).reset_index(drop=True)

    section("VALIDATION VERDICT (all 13 folds - matches Decision 021/025's own selection protocol)")
    print(comparison_df[["candidate", "median_pr_auc"]].to_string(index=False))
    comparison_df.to_csv(COMPARISON_OUTPUT_PATH, index=False)

    best = comparison_df.iloc[0]
    if best["candidate"] == "random_forest_official" or best["median_pr_auc"] <= median_official + 1e-9:
        print(
            f"\nRESULT: none of the three new levers beat the official model's own validation median PR-AUC "
            f"({median_official:.4f}). Holdout is NOT checked (per the pre-registered rule). Negative result."
        )
        return

    winner_name = str(best["candidate"])
    winner_model = "random_forest" if winner_name in ("rf_balanced_subsample", "rf_tuned") else "gradient_boosting"
    winner_params = best["params"]

    print(
        f"\n'{winner_name}' beats the official model on validation "
        f"(+{best['median_pr_auc'] - median_official:.4f} median PR-AUC) - spending the one-time holdout check on it."
    )
    holdout_scores = _score_on_holdout(df, pre_holdout_keys, holdout_keys, winner_model, winner_params)
    official_holdout_scores = _score_on_holdout(df, pre_holdout_keys, holdout_keys, "random_forest", RF_PARAMS)

    section("HOLDOUT CHECK (touched once, for this candidate only)")
    holdout_df = pd.DataFrame(
        [{"candidate": "random_forest_official", **official_holdout_scores}, {"candidate": winner_name, **holdout_scores}]
    )
    print(holdout_df.to_string(index=False))
    holdout_df.to_csv(HOLDOUT_OUTPUT_PATH, index=False)

    if holdout_scores["pr_auc"] > official_holdout_scores["pr_auc"]:
        print(
            f"\nRESULT: '{winner_name}' beats official Random Forest on BOTH validation AND holdout. "
            f"Candidate for promotion. Params: {winner_params}"
        )
    else:
        print(
            f"\nRESULT: '{winner_name}' won on validation but did NOT beat official Random Forest on holdout "
            f"({holdout_scores['pr_auc']:.4f} vs {official_holdout_scores['pr_auc']:.4f}). NOT promoted - the same "
            "validation-improves/holdout-regresses pattern already documented for M2-010/Decision 044."
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="M2-013: RF balanced_subsample / RF tuning / Gradient Boosting.")
    parser.add_argument("--trials", type=int, default=50, help="Optuna trials for RF tuning (default: 50).")
    args = parser.parse_args()
    main(n_trials=args.trials)
