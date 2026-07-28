"""Module 2 Stage 1 imbalance-handling audit: leakage-safe SMOTENC vs. the
current `class_weight`/`scale_pos_weight`-only approach (Decision 021).

Read-only diagnostic script. Does not modify `baseline_classifier.py` or any
production artifact. Reuses `baseline_classifier.py`'s exact data assembly,
walk-forward fold boundaries, and fold-aware climate anomalies so every
variant here is scored on IDENTICAL folds/rows to the current production
benchmark - only the training-time resampling/weighting differs.

## Why this audit exists

Decision 021 rejected SMOTE with the reasoning "synthetic oversampling across
a temporal walk-forward split would blur the fold boundary." That reasoning
is revisited here rather than assumed: SMOTE fit strictly on a fold's own
TRAINING rows (never seeing that fold's validation/holdout rows) does not
actually leak future information across the walk-forward boundary - the real,
distinct risk is that SMOTE/SMOTENC linearly interpolates feature vectors
between two random minority-class TRAINING rows, which can synthesize
physically-implausible combinations of the lag/rolling-stat features that
dominate this model's importance (`case_anomaly_lag_1/2` alone account for
>60%, per `MODULE_CONTEXT.md`'s Stage 1 Implementation Status) - e.g.
interpolating between a Colombo monsoon-peak week and a Puttalam post-drought
week. This audit measures whether that risk actually materializes as worse
discrimination, or whether SMOTENC's rebalancing benefit dominates.

## Leakage guards (identical discipline to `audit_label_stabilization.py`)

- SMOTENC is `fit_resample`'d on each fold's own TRAINING rows ONLY, after
  that fold's own median-imputation (imputer `fit` on train, applied to
  train+val) - it never sees that fold's validation or holdout rows.
- `District` is passed to SMOTENC as a categorical column (`categorical_features`)
  so synthetic rows get a real, existing district label (nearest-neighbor
  majority vote), never an invented category value.
- Reuses `baseline_classifier.py`'s own fold-boundary reconstruction
  (`compute_fold_boundaries`) and fold-aware climate anomalies
  (`attach_fold_anomalies`) verbatim - zero risk of the two scripts silently
  drifting apart on what counts as "this fold's training window."

## Models and variants compared

Random Forest (current official Stage 1 model, Decision 025) and XGBoost
(the close runner-up) are both benchmarked, across:

    baseline_class_weight     - CONTROL. Exactly today's production approach:
                                `class_weight="balanced"` (RF) /
                                `scale_pos_weight` from the fold's own labels
                                (XGBoost). No resampling.
    smotenc_full_no_weight    - SMOTENC to `sampling_strategy=1.0` (full 1:1
                                balance), class weighting DISABLED (avoids
                                double-correcting).
    smotenc_half_no_weight    - SMOTENC to `sampling_strategy=0.5` (minority
                                reaches half the majority count), class
                                weighting DISABLED - a gentler resampling
                                ablation against the full-balance variant.
    smotenc_half_plus_weight - SMOTENC to `sampling_strategy=0.5` PLUS class
                                weighting still applied on the resampled
                                (now less imbalanced) labels - tests whether
                                combining both helps or over-corrects.

Caveat for XGBoost specifically: the PRODUCTION XGBoost path leaves NaNs
untouched (native handling, Decision 021). SMOTENC requires no missing
values, so this audit's XGBoost rows are median-imputed first, unlike
production XGBoost - this is flagged as a soft/indicative comparison for
XGBoost only, not an apples-to-apples one; Random Forest's comparison IS
apples-to-apples since RF is already median-imputed in production.

Output: `outputs/metrics/module2/smote_imbalance_audit.csv` (per-fold +
holdout, per-model, per-variant metrics) and a printed aggregate summary.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from imblearn.over_sampling import SMOTENC
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import DISTRICTS, MODULE2_METRICS_DIR  # noqa: E402
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    NUMERIC_FEATURE_COLUMNS,
    RF_PARAMS,
    TARGET_COL,
    XGB_BASE_PARAMS,
    assemble_labeled_feature_table,
    attach_fold_anomalies,
    compute_fold_boundaries,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_PATH = MODULE2_METRICS_DIR / "smote_imbalance_audit.csv"

MODEL_NAMES = ["random_forest", "xgboost"]
SECONDARY_THRESHOLD = 0.5

VARIANTS: list[tuple[str, dict | None]] = [
    ("baseline_class_weight", None),
    ("smotenc_full_no_weight", {"sampling_strategy": 1.0, "use_class_weight": False}),
    ("smotenc_half_no_weight", {"sampling_strategy": 0.5, "use_class_weight": False}),
    ("smotenc_half_plus_weight", {"sampling_strategy": 0.5, "use_class_weight": True}),
]


# ---------------------------------------------------------------------------
# Leakage-safe SMOTENC resampling of a fold's TRAINING rows only
# ---------------------------------------------------------------------------

def resample_with_smotenc(
    X_train_df: pd.DataFrame, y_train: np.ndarray, sampling_strategy: float, random_state: int = 42,
) -> tuple[pd.DataFrame, np.ndarray, bool]:
    """Apply SMOTENC to `X_train_df` (numeric columns already median-imputed,
    plus a raw `District` string column) / `y_train`. Returns
    `(X_resampled, y_resampled, applied)` - `applied=False` (unchanged input)
    if the minority class is too small to support even `k_neighbors=1`.
    """
    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    minority_count = min(n_pos, n_neg)
    if minority_count < 2 or n_pos == 0 or n_neg == 0:
        return X_train_df, y_train, False

    k_neighbors = min(5, minority_count - 1)
    cat_idx = [X_train_df.columns.get_loc("District")]
    smote = SMOTENC(
        categorical_features=cat_idx, sampling_strategy=sampling_strategy,
        k_neighbors=k_neighbors, random_state=random_state,
    )
    X_res, y_res = smote.fit_resample(X_train_df, y_train)
    return X_res, np.asarray(y_res), True


# ---------------------------------------------------------------------------
# Fit/predict per model, with optional SMOTENC variant config
# ---------------------------------------------------------------------------

def _prep_numeric_and_district(train_df: pd.DataFrame, val_df: pd.DataFrame):
    imputer = SimpleImputer(strategy="median")
    X_train_num = imputer.fit_transform(train_df[NUMERIC_FEATURE_COLUMNS])
    X_val_num = imputer.transform(val_df[NUMERIC_FEATURE_COLUMNS])

    X_train_df = pd.DataFrame(X_train_num, columns=NUMERIC_FEATURE_COLUMNS)
    X_train_df["District"] = train_df["District"].to_numpy()
    X_val_df = pd.DataFrame(X_val_num, columns=NUMERIC_FEATURE_COLUMNS)
    X_val_df["District"] = val_df["District"].to_numpy()
    return X_train_df, X_val_df


def fit_predict_random_forest(
    train_df: pd.DataFrame, val_df: pd.DataFrame, smote_cfg: dict | None,
) -> tuple[np.ndarray, bool]:
    y_train = train_df[TARGET_COL].to_numpy(dtype=int)
    X_train_df, X_val_df = _prep_numeric_and_district(train_df, val_df)

    applied = False
    use_class_weight = True
    if smote_cfg is not None:
        X_train_df, y_train, applied = resample_with_smotenc(
            X_train_df, y_train, smote_cfg["sampling_strategy"]
        )
        use_class_weight = smote_cfg["use_class_weight"]

    encoder = OneHotEncoder(categories=[DISTRICTS], handle_unknown="ignore", sparse_output=False)
    X_train_cat = encoder.fit_transform(X_train_df[["District"]])
    X_val_cat = encoder.transform(X_val_df[["District"]])

    X_train_all = np.hstack([X_train_df[NUMERIC_FEATURE_COLUMNS].to_numpy(dtype=float), X_train_cat])
    X_val_all = np.hstack([X_val_df[NUMERIC_FEATURE_COLUMNS].to_numpy(dtype=float), X_val_cat])

    params = dict(RF_PARAMS)
    params["class_weight"] = "balanced" if use_class_weight else None
    clf = RandomForestClassifier(**params)
    clf.fit(X_train_all, y_train)
    proba = clf.predict_proba(X_val_all)[:, 1]
    return proba, applied


def fit_predict_xgboost(
    train_df: pd.DataFrame, val_df: pd.DataFrame, smote_cfg: dict | None,
) -> tuple[np.ndarray, bool]:
    y_train = train_df[TARGET_COL].to_numpy(dtype=int)
    X_train_df, X_val_df = _prep_numeric_and_district(train_df, val_df)

    applied = False
    use_class_weight = True
    if smote_cfg is not None:
        X_train_df, y_train, applied = resample_with_smotenc(
            X_train_df, y_train, smote_cfg["sampling_strategy"]
        )
        use_class_weight = smote_cfg["use_class_weight"]

    X_train_df["District"] = pd.Categorical(X_train_df["District"], categories=DISTRICTS)
    X_val_df["District"] = pd.Categorical(X_val_df["District"], categories=DISTRICTS)
    cols = NUMERIC_FEATURE_COLUMNS + ["District"]

    n_pos = int(y_train.sum())
    n_neg = len(y_train) - n_pos
    scale_pos_weight = (n_neg / n_pos) if (use_class_weight and n_pos > 0) else 1.0

    model = xgb.XGBClassifier(**XGB_BASE_PARAMS, scale_pos_weight=scale_pos_weight)
    model.fit(X_train_df[cols], y_train)
    proba = model.predict_proba(X_val_df[cols])[:, 1]
    return proba, applied


FIT_PREDICT_FN = {"random_forest": fit_predict_random_forest, "xgboost": fit_predict_xgboost}


# ---------------------------------------------------------------------------
# Scoring (mirrors baseline_classifier._score_predictions)
# ---------------------------------------------------------------------------

def score_predictions(label: pd.Series, proba: np.ndarray) -> dict:
    y_true = label.to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    pred_label = (proba >= SECONDARY_THRESHOLD).astype(float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, proba, mask=mask),
        "precision": evaluate.precision(y_true, pred_label, mask=mask),
        "recall": evaluate.recall(y_true, pred_label, mask=mask),
        "f1": evaluate.f1(y_true, pred_label, mask=mask),
        "f2": evaluate.fbeta_score(y_true, pred_label, beta=2.0, mask=mask),
        "brier_score": evaluate.brier_score(y_true, proba, mask=mask),
        "prevalence": evaluate.prevalence(y_true, mask=mask),
        "n_obs_scored": int(mask.sum()),
    }


# ---------------------------------------------------------------------------
# Main loop: every fold x model x variant, plus a holdout check for each
# ---------------------------------------------------------------------------

def run_audit() -> pd.DataFrame:
    logger.info("Assembling labeled Stage 1 feature table (identical to production)...")
    df = assemble_labeled_feature_table()
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(df)
    n_folds = len(fold_train_keys)

    rows: list[dict] = []

    for fold_num in range(1, n_folds + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        train_rows_all = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
        val_rows_all = fold_df.loc[val_mask]

        for model_name in MODEL_NAMES:
            for variant_name, smote_cfg in VARIANTS:
                proba, applied = FIT_PREDICT_FN[model_name](train_rows_all, val_rows_all, smote_cfg)
                scores = score_predictions(val_rows_all[TARGET_COL], proba)
                rows.append(
                    {
                        "split": "validation", "fold_id": fold_num, "model": model_name,
                        "variant": variant_name, "smote_applied": applied,
                        "n_train": len(train_rows_all), "n_train_pos": int(train_rows_all[TARGET_COL].sum()),
                        **scores,
                    }
                )
        logger.info("Fold %d scored across %d models x %d variants.", fold_num, len(MODEL_NAMES), len(VARIANTS))

    # Holdout check (pre_holdout -> holdout), same variants, for the winner to be re-confirmed on.
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)
    train_rows_all = fold_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = fold_df.loc[val_mask]

    for model_name in MODEL_NAMES:
        for variant_name, smote_cfg in VARIANTS:
            proba, applied = FIT_PREDICT_FN[model_name](train_rows_all, val_rows_all, smote_cfg)
            scores = score_predictions(val_rows_all[TARGET_COL], proba)
            rows.append(
                {
                    "split": "holdout", "fold_id": "holdout", "model": model_name,
                    "variant": variant_name, "smote_applied": applied,
                    "n_train": len(train_rows_all), "n_train_pos": int(train_rows_all[TARGET_COL].sum()),
                    **scores,
                }
            )
    logger.info("Holdout scored across %d models x %d variants.", len(MODEL_NAMES), len(VARIANTS))

    results_df = pd.DataFrame(rows)

    MODULE2_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(results_df), OUTPUT_PATH)

    print("\n" + "=" * 100)
    print("AGGREGATE (median across 13 validation folds) BY MODEL x VARIANT")
    print("=" * 100)
    val_only = results_df[results_df["split"] == "validation"]
    agg = val_only.groupby(["model", "variant"])[["pr_auc", "roc_auc", "recall", "precision", "f2", "brier_score"]].median()
    print(agg.to_string())

    print("\n" + "=" * 100)
    print("HOLDOUT BY MODEL x VARIANT")
    print("=" * 100)
    holdout_only = results_df[results_df["split"] == "holdout"]
    print(
        holdout_only.set_index(["model", "variant"])[
            ["pr_auc", "roc_auc", "recall", "precision", "f2", "brier_score", "n_train_pos"]
        ].to_string()
    )

    return results_df


if __name__ == "__main__":
    run_audit()
