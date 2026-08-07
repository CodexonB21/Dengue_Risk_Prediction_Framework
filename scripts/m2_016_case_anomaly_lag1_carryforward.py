"""M2-016: does substituting a carried-forward `case_anomaly_lag_2` for a
masked `case_anomaly_lag_1` help Stage 1 (Random Forest) discrimination?

Motivated by the 2026 Wk25 Colombo/Gampaha false-negative investigation
(user-facing chat, 2026-08-07): both districts' single most important
feature (`case_anomaly_lag_1`, ~35% of RF feature importance) went `NaN`
that week because the immediately preceding week (Wk24) was flagged
`is_reporting_anomaly` - a real reporting-delay artifact, not a genuine
case-count collapse. `RandomForestClassifier`'s median-imputer then fills
that gap with roughly "no anomaly", the wrong default during a genuine
accelerating outbreak.

Mirrors Module 1's Decision 030/M1-006B precedent (`cases_lag_1 =
max(cases_lag_2, rolling_mean_cases_4w)` when the prior week is flagged),
but scoped to Module 2's own dominant feature:
`case_anomaly_lag_1 = case_anomaly_lag_2` when the prior week is flagged
(`feature_engineering.compute_case_anomaly_lags(..., carry_forward_masked_lag1=True)`).

Methodology mirrors `scripts/m2_013_stage1_rf_refresh.py` exactly: 13-fold
walk-forward median PR-AUC (Stage 1's own selection metric, Decision 021) on
the CURRENT PRODUCTION Random Forest hyperparameters (`RF_PARAMS`, Decision
047) - this isolates the feature-engineering change as the only variable.
Holdout is spent exactly once, only if validation improves - the same
"validation wins first, holdout checks once" discipline used everywhere
else in this project (Decisions 009/021/023/044).

Does NOT modify the production feature table
(`MODULE2_STAGE1_FEATURE_TABLE_PATH`) or any production artifact - the
carry-forward variant is built fresh to a separate path.

Usage:
    python scripts/m2_016_case_anomaly_lag1_carryforward.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import MODULE2_FEATURES_DIR, MODULE2_METRICS_DIR, MODULE2_STAGE1_FEATURE_TABLE_PATH  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    N_FOLDS,
    RF_PARAMS,
    TARGET_COL,
    assemble_labeled_feature_table,
    attach_fold_anomalies,
    compute_fold_boundaries,
    fit_and_predict,
)
from src.module2_classification.feature_engineering import build_module2_feature_table  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CARRYFORWARD_FEATURE_TABLE_PATH = MODULE2_FEATURES_DIR / "stage1_feature_table_m2_016_carryforward.csv"
COMPARISON_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_016_case_anomaly_carryforward_comparison.csv"
HOLDOUT_OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_016_case_anomaly_carryforward_holdout.csv"

MODEL_NAME = "random_forest"  # Decision 025/047's official Stage 1 model
SPOTLIGHT_ROWS = [("Colombo", 2026, 25), ("Gampaha", 2026, 25)]


def section(title: str) -> None:
    print("\n" + "=" * 92)
    print(title)
    print("=" * 92)


def build_carryforward_feature_table() -> Path:
    MODULE2_FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    features = build_module2_feature_table(carry_forward_masked_lag1=True)
    features.to_csv(CARRYFORWARD_FEATURE_TABLE_PATH, index=False)
    logger.info("Wrote carry-forward variant feature table to %s (%d rows).", CARRYFORWARD_FEATURE_TABLE_PATH, len(features))
    return CARRYFORWARD_FEATURE_TABLE_PATH


def score_validation_folds(df: pd.DataFrame, fold_train_keys: dict, fold_val_keys: dict) -> list[float]:
    """Same 13-fold walk-forward loop `baseline_classifier.run_benchmark` uses, RF only."""
    pr_aucs = []
    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
        val_rows_all = fold_df.loc[val_mask]

        proba, _ = fit_and_predict(MODEL_NAME, trainable_train, val_rows_all, model_params=RF_PARAMS)
        y = val_rows_all[TARGET_COL].to_numpy(dtype=float)
        mask = ~np.isnan(y)
        pr_aucs.append(evaluate.pr_auc(y, proba, mask=mask))
        logger.info("Fold %d: PR-AUC=%.4f (n_scored=%d)", fold_num, pr_aucs[-1], int(mask.sum()))
    return pr_aucs


def score_holdout(df: pd.DataFrame, pre_holdout_keys: set, holdout_keys: set) -> tuple[dict, pd.DataFrame]:
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)

    trainable_train = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = fold_df.loc[val_mask]

    proba, _ = fit_and_predict(MODEL_NAME, trainable_train, val_rows_all, model_params=RF_PARAMS)
    y = val_rows_all[TARGET_COL].to_numpy(dtype=float)
    mask = ~np.isnan(y)

    scores = {
        "pr_auc": evaluate.pr_auc(y, proba, mask=mask),
        "roc_auc": evaluate.roc_auc(y, proba, mask=mask),
        "brier_score": evaluate.brier_score(y, proba, mask=mask),
        "n_obs_scored": int(mask.sum()),
    }
    spotlight = val_rows_all[["District", "Year", "Week", "Number_of_Cases", TARGET_COL]].copy()
    spotlight["predicted_probability"] = proba
    return scores, spotlight


def main() -> None:
    section("M2-016: CASE_ANOMALY_LAG_1 CARRY-FORWARD SUBSTITUTION - VALIDATION COMPARISON")

    baseline_df = assemble_labeled_feature_table(input_path=MODULE2_STAGE1_FEATURE_TABLE_PATH)
    carryforward_path = build_carryforward_feature_table()
    carryforward_df = assemble_labeled_feature_table(input_path=carryforward_path)

    base_fold_train, base_fold_val, base_pre_holdout, base_holdout = compute_fold_boundaries(baseline_df)
    cf_fold_train, cf_fold_val, cf_pre_holdout, cf_holdout = compute_fold_boundaries(carryforward_df)

    print("\nBaseline (production feature table, case_anomaly_lag_1 left NaN after a flagged week):")
    baseline_pr_aucs = score_validation_folds(baseline_df, base_fold_train, base_fold_val)
    print("\nCarry-forward variant (case_anomaly_lag_1 = case_anomaly_lag_2 after a flagged week):")
    carryforward_pr_aucs = score_validation_folds(carryforward_df, cf_fold_train, cf_fold_val)

    comparison = pd.DataFrame({
        "fold_id": list(range(1, N_FOLDS + 1)),
        "baseline_pr_auc": baseline_pr_aucs,
        "carryforward_pr_auc": carryforward_pr_aucs,
    })
    baseline_median = float(np.nanmedian(baseline_pr_aucs))
    carryforward_median = float(np.nanmedian(carryforward_pr_aucs))

    section("VALIDATION VERDICT (13-fold median PR-AUC - Decision 021's own selection protocol)")
    print(comparison.to_string(index=False))
    print(f"\nBaseline median PR-AUC:      {baseline_median:.4f}")
    print(f"Carry-forward median PR-AUC: {carryforward_median:.4f}")

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    comparison.assign(baseline_median=baseline_median, carryforward_median=carryforward_median).to_csv(
        COMPARISON_OUTPUT_PATH, index=False
    )

    if carryforward_median > baseline_median + 1e-9:
        print(
            f"\nCarry-forward beats baseline on validation (+{carryforward_median - baseline_median:.4f} "
            "median PR-AUC) - per the project's 'validation wins first, holdout checks once' rule, "
            "checking holdout now."
        )
        base_holdout_scores, base_spotlight = score_holdout(baseline_df, base_pre_holdout, base_holdout)
        cf_holdout_scores, cf_spotlight = score_holdout(carryforward_df, cf_pre_holdout, cf_holdout)

        section("HOLDOUT CHECK (touched once)")
        holdout_df = pd.DataFrame([
            {"candidate": "baseline", **base_holdout_scores},
            {"candidate": "carryforward", **cf_holdout_scores},
        ])
        print(holdout_df.to_string(index=False))
        holdout_df.to_csv(HOLDOUT_OUTPUT_PATH, index=False)

        if cf_holdout_scores["pr_auc"] > base_holdout_scores["pr_auc"]:
            print(
                "\nRESULT: carry-forward beats baseline on BOTH validation AND holdout. "
                "Candidate for promotion (would require a Decision record + production rerun)."
            )
        else:
            print(
                "\nRESULT: carry-forward won on validation but did NOT beat baseline on holdout "
                f"({cf_holdout_scores['pr_auc']:.4f} vs {base_holdout_scores['pr_auc']:.4f}). "
                "NOT promoted - the validation-improves/holdout-regresses pattern the holdout-once "
                "discipline exists to catch (cf. Decision 044)."
            )

        section("SPOTLIGHT: raw Stage 1 (Random Forest) probability, Colombo/Gampaha 2026 Wk25 (holdout)")
        for district, year, week in SPOTLIGHT_ROWS:
            b = base_spotlight[(base_spotlight.District == district) & (base_spotlight.Year == year) & (base_spotlight.Week == week)]
            c = cf_spotlight[(cf_spotlight.District == district) & (cf_spotlight.Year == year) & (cf_spotlight.Week == week)]
            b_p = float(b["predicted_probability"].iloc[0]) if not b.empty else float("nan")
            c_p = float(c["predicted_probability"].iloc[0]) if not c.empty else float("nan")
            cases = float(b["Number_of_Cases"].iloc[0]) if not b.empty else float("nan")
            print(f"{district} {year} Wk{week} (actual cases={cases:.0f}): baseline p={b_p:.4f} -> carryforward p={c_p:.4f}")
    else:
        print(
            f"\nRESULT: carry-forward does NOT beat baseline's validation median PR-AUC "
            f"({carryforward_median:.4f} vs {baseline_median:.4f}). Holdout is NOT checked (pre-registered "
            "rule: holdout is only spent on a candidate that already won on validation). Negative result - "
            "reported, not discarded. NOT promoted."
        )
        print(
            "\n(Diagnostic only, NOT holdout evidence - the specific Colombo/Gampaha 2026 Wk25 row this "
            "experiment was motivated by sits inside the untouched holdout block, which this run has NOT "
            "earned the right to look at under the project's own discipline.)"
        )

    section("DONE")
    print(f"Validation comparison written to {COMPARISON_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
