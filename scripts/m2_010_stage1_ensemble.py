"""M2-010: Stage 1 ensemble - does blending RF+XGBoost+LR beat picking one
official model (Random Forest, Decision 025)?

Read-only diagnostic script. Does not modify any pipeline file or config,
and does not refit any model - it reuses the already-computed out-of-fold
probabilities in `MODULE2_BASELINE_PREDICTIONS_PATH` (all 3 benchmarked
models x all 13 walk-forward folds x holdout, from
`baseline_classifier.run_stage1_pipeline`), so there is zero leakage risk
introduced by this script itself.

Three ensemble variants, all built from those existing OOF probabilities:
    mean_all3     - simple unweighted average of RF + XGBoost + LR.
    mean_rf_xgb   - simple unweighted average of just RF + XGBoost (drops
                    the weakest of the three per Decision 025's own
                    validation-median PR-AUC ranking: LR 0.358 < XGB 0.373
                    < RF 0.377).
    logistic_blend - a genuine no-leakage stacked blend: for validation
                    fold k (k=2..13), fits a 3-feature (rf, xgb, lr
                    probability) LogisticRegression on the POOLED
                    out-of-fold rows from folds 1..k-1 only, predicts fold
                    k. Fold 1 has no prior fold to train on (mirrors Stage
                    2's own fold-1 no-op, `compensation_model.py`'s
                    `FIRST_TRAINABLE_STAGE2_FOLD` convention) so it is
                    excluded from this variant, not filled with a fallback.
                    For holdout, trains on all 13 folds' pooled OOF rows.

Selection rule (mirrors `baseline_classifier.select_official_model`):
compare median PR-AUC across the SAME fold population used for every
candidate. Because `logistic_blend` cannot score fold 1, the fair
head-to-head comparison uses folds 2-13 only for every candidate
(individual models included) - fold-1-inclusive numbers are also reported
for transparency but are not the selection criterion.

Holdout is looked at ONCE, only if the best variant beats the official
Random Forest model's own fold-2-13 median PR-AUC on validation - the same
"validation wins first, holdout checks once" discipline used everywhere
else in this project (Decisions 009/021/023/044).

Output: `outputs/metrics/module2/m2_010_ensemble_comparison.csv`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import MODULE2_BASELINE_PREDICTIONS_PATH, MODULE2_METRICS_DIR  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402

OUTPUT_PATH = MODULE2_METRICS_DIR / "m2_010_ensemble_comparison.csv"
BASE_MODELS = ["logistic_regression", "random_forest", "xgboost"]
OFFICIAL_MODEL = "random_forest"  # Decision 025
FIRST_COMPARABLE_FOLD = 2  # logistic_blend has no fold-1 counterpart
N_FOLDS = 13


def section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def load_wide() -> pd.DataFrame:
    """Pivot the long predictions file to one row per (District, Year, Week,
    split, fold_id) with one predicted_probability column per model."""
    df = pd.read_csv(MODULE2_BASELINE_PREDICTIONS_PATH, low_memory=False)
    idx_cols = ["District", "Year", "Week", "split", "fold_id", "label"]
    wide = df.pivot_table(
        index=idx_cols, columns="model", values="predicted_probability", aggfunc="first"
    ).reset_index()
    wide.columns.name = None
    return wide


def add_mean_variants(wide: pd.DataFrame) -> pd.DataFrame:
    wide = wide.copy()
    wide["mean_all3"] = wide[BASE_MODELS].mean(axis=1)
    wide["mean_rf_xgb"] = wide[["random_forest", "xgboost"]].mean(axis=1)
    return wide


def add_logistic_blend(wide: pd.DataFrame) -> pd.DataFrame:
    """No-leakage stacked blend: fold k's blend model trains only on folds
    1..k-1's pooled OOF rows (validation split); holdout's blend model
    trains on all 13 folds' pooled OOF rows. NaN for fold 1 (no prior data)."""
    wide = wide.copy()
    wide["logistic_blend"] = np.nan

    val = wide[wide["split"] == "validation"].copy()
    val["fold_id_numeric"] = pd.to_numeric(val["fold_id"], errors="coerce")

    for fold_num in range(FIRST_COMPARABLE_FOLD, N_FOLDS + 1):
        train_rows = val[val["fold_id_numeric"] < fold_num].dropna(subset=["label"])
        val_rows = val[val["fold_id_numeric"] == fold_num]
        if train_rows.empty or val_rows.empty:
            continue
        model = LogisticRegression(max_iter=2000, random_state=42)
        model.fit(train_rows[BASE_MODELS].to_numpy(), train_rows["label"].to_numpy(dtype=int))
        preds = model.predict_proba(val_rows[BASE_MODELS].to_numpy())[:, 1]
        wide.loc[val_rows.index, "logistic_blend"] = preds

    # Holdout: train on ALL 13 validation folds' pooled OOF rows.
    train_rows = val.dropna(subset=["label"])
    holdout_rows = wide[wide["split"] == "holdout"]
    if not train_rows.empty and not holdout_rows.empty:
        model = LogisticRegression(max_iter=2000, random_state=42)
        model.fit(train_rows[BASE_MODELS].to_numpy(), train_rows["label"].to_numpy(dtype=int))
        preds = model.predict_proba(holdout_rows[BASE_MODELS].to_numpy())[:, 1]
        wide.loc[holdout_rows.index, "logistic_blend"] = preds

    return wide


def score_candidate(wide: pd.DataFrame, candidate: str, split: str, min_fold: int | None = None) -> dict:
    """Median PR-AUC/ROC-AUC/Brier across validation folds (>= min_fold if
    given), or a single-block score for holdout."""
    if split == "validation":
        rows = wide[wide["split"] == "validation"].copy()
        rows["fold_id_numeric"] = pd.to_numeric(rows["fold_id"], errors="coerce")
        if min_fold is not None:
            rows = rows[rows["fold_id_numeric"] >= min_fold]
        per_fold = []
        for _fold, g in rows.groupby("fold_id_numeric"):
            y = g["label"].to_numpy(dtype=float)
            p = g[candidate].to_numpy(dtype=float)
            mask = ~np.isnan(y) & ~np.isnan(p)
            per_fold.append(
                {
                    "pr_auc": evaluate.pr_auc(y, p, mask=mask),
                    "roc_auc": evaluate.roc_auc(y, p, mask=mask),
                    "brier_score": evaluate.brier_score(y, p, mask=mask),
                }
            )
        agg = pd.DataFrame(per_fold)
        return {
            "candidate": candidate,
            "split": f"validation_folds_{min_fold or 1}-{N_FOLDS}",
            "median_pr_auc": float(np.nanmedian(agg["pr_auc"])),
            "median_roc_auc": float(np.nanmedian(agg["roc_auc"])),
            "median_brier_score": float(np.nanmedian(agg["brier_score"])),
            "n_folds_scored": int(agg["pr_auc"].notna().sum()),
        }

    rows = wide[wide["split"] == "holdout"]
    y = rows["label"].to_numpy(dtype=float)
    p = rows[candidate].to_numpy(dtype=float)
    mask = ~np.isnan(y) & ~np.isnan(p)
    return {
        "candidate": candidate,
        "split": "holdout",
        "median_pr_auc": evaluate.pr_auc(y, p, mask=mask),
        "median_roc_auc": evaluate.roc_auc(y, p, mask=mask),
        "median_brier_score": evaluate.brier_score(y, p, mask=mask),
        "n_folds_scored": 1,
    }


def main() -> None:
    section("M2-010: STAGE 1 ENSEMBLE - VALIDATION COMPARISON")
    wide = load_wide()
    wide = add_mean_variants(wide)
    wide = add_logistic_blend(wide)

    # PRIMARY comparison: all 13 folds, median PR-AUC - this is EXACTLY
    # `baseline_classifier.select_official_model`'s own protocol (the
    # decision point that picked Random Forest, Decision 025), so it is the
    # only apples-to-apples test of "would an ensemble have won Stage 1
    # model selection instead of RF." mean_all3/mean_rf_xgb are computable
    # on every fold, same as the 3 base models.
    print("\nPRIMARY comparison - all 13 folds, median PR-AUC (matches Decision 025's own selection protocol):")
    primary_rows = [
        score_candidate(wide, c, "validation", min_fold=1)
        for c in BASE_MODELS + ["mean_all3", "mean_rf_xgb"]
    ]
    primary_df = pd.DataFrame(primary_rows).sort_values("median_pr_auc", ascending=False).reset_index(drop=True)
    print(primary_df.to_string(index=False))

    # SECONDARY/exploratory: logistic_blend cannot score fold 1 (no prior
    # fold to train on), so it is reported on its own valid window (folds
    # 2-13) against the same candidates restricted to that window - NOT
    # used to pick the primary winner, since that would silently swap in a
    # different fold population than the one Decision 025 actually used.
    print(f"\nSECONDARY/exploratory - folds {FIRST_COMPARABLE_FOLD}-{N_FOLDS} only, includes logistic_blend:")
    secondary_rows = [
        score_candidate(wide, c, "validation", min_fold=FIRST_COMPARABLE_FOLD)
        for c in BASE_MODELS + ["mean_all3", "mean_rf_xgb", "logistic_blend"]
    ]
    secondary_df = pd.DataFrame(secondary_rows).sort_values("median_pr_auc", ascending=False).reset_index(drop=True)
    print(secondary_df.to_string(index=False))

    official_pr_auc = primary_df.loc[primary_df["candidate"] == OFFICIAL_MODEL, "median_pr_auc"].iloc[0]
    best_row = primary_df.iloc[0]
    best_candidate = str(best_row["candidate"])
    best_pr_auc = float(best_row["median_pr_auc"])

    section("VERDICT (validation, all 13 folds - the actual selection protocol)")
    print(f"Official Stage 1 model ({OFFICIAL_MODEL}) median PR-AUC: {official_pr_auc:.4f}")
    print(f"Best candidate overall: {best_candidate} (median PR-AUC: {best_pr_auc:.4f})")
    print(
        "\n(logistic_blend is excluded from this verdict by construction - it has no fold-1 value, so it "
        "was never a like-for-like alternative to a single-model Stage 1 selection. Its folds-2-13 number "
        "above is reported for interest only.)"
    )

    all_rows = (
        primary_df.assign(stage="primary_validation_comparison").to_dict("records")
        + secondary_df.assign(stage="secondary_folds_2_13_comparison").to_dict("records")
    )

    if best_candidate != OFFICIAL_MODEL and best_pr_auc > official_pr_auc + 1e-9:
        print(
            f"\n'{best_candidate}' beats the official model on validation "
            f"(+{best_pr_auc - official_pr_auc:.4f} median PR-AUC) - per the project's "
            "'validation wins first, holdout checks once' rule, checking holdout now."
        )
        holdout_row = score_candidate(wide, best_candidate, "holdout")
        official_holdout_row = score_candidate(wide, OFFICIAL_MODEL, "holdout")
        print("\nHOLDOUT CHECK (touched once, for this candidate only):")
        print(pd.DataFrame([official_holdout_row, holdout_row]).to_string(index=False))
        all_rows.append({**holdout_row, "stage": "holdout_check"})
        all_rows.append({**official_holdout_row, "stage": "holdout_check"})

        if holdout_row["median_pr_auc"] > official_holdout_row["median_pr_auc"]:
            print(
                f"\nRESULT: '{best_candidate}' beats official Random Forest on BOTH validation AND holdout. "
                "Candidate for promotion - but note holdout is a single 2,600-row/40-positive block, so this "
                "is a directional signal, not a large-sample confirmation."
            )
        else:
            print(
                f"\nRESULT: '{best_candidate}' won on validation but did NOT beat official Random Forest on "
                f"holdout ({holdout_row['median_pr_auc']:.4f} vs {official_holdout_row['median_pr_auc']:.4f}). "
                "NOT promoted - this is exactly the validation-improves/holdout-regresses pattern the "
                "holdout-once discipline exists to catch (cf. Decision 044)."
            )
    else:
        print(
            f"\nRESULT: no ensemble variant beats the official '{OFFICIAL_MODEL}' model's validation median "
            "PR-AUC. Holdout is NOT checked (per the pre-registered rule: holdout is only spent on a "
            "candidate that already won on validation). Negative result - reported, not discarded."
        )

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_rows).to_csv(OUTPUT_PATH, index=False)
    section("DONE")
    print(f"Full comparison written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
