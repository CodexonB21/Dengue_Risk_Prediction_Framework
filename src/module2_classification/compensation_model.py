"""Module 2 Stage 2 - probability/classification-error compensation model.

Implements the design confirmed with the user before this file was written
(see `module_2_classification/EXPERIMENT_LOG.md` M2-002 and
`research_context/RESEARCH_DECISIONS.md` Decision 022 for the permanent
record):

1. **Three numerically well-posed architectures, not a literal residual
   regression.** Module 1 Stage 2's `residual = actual - sarima_prediction`
   metaphor does not transfer to a binary target: `label -
   predicted_probability` for a single Bernoulli observation is a
   high-variance, low-information regression target, with no clean way to
   keep `predicted_probability + predicted_residual` inside `[0, 1]`.
   Benchmarked instead:
   - `isotonic`: pooled, feature-free `IsotonicRegression` on
     `predicted_probability` -> `label`.
   - `platt`: pooled, feature-free logistic regression on
     `logit(predicted_probability)` (the log-odds, NOT raw `p` - this is
     what makes it standard Platt scaling).
   - `stacked_xgboost`: a classifier on `[predicted_probability, contextual
     features, District, probability_residual_lag_1/2]` -> `label` directly
     - the resolved form of "residual/probability correction model" from
     `MODULE_CONTEXT.md`'s "Possible Stage 2 Models" list.
   Selected by median Brier Skill Score (Stage 2's primary metric, mirrors
   Stage 1's use of PR-AUC), gated by a logged (not silently ignored) check
   that PR-AUC/ROC-AUC don't regress vs. Stage 1's raw probability.
2. **No-leakage rule (Decision-010-style, adapted for classification)**:
   Stage 2 fold *k* (`k = 2..13`) trains only on the OFFICIAL Stage 1
   model's out-of-sample `predicted_probability`/`label` from folds
   `1..k-1` - never fold *k* itself. Fold 1 has no prior out-of-sample data
   and is a documented no-op passthrough (`calibrated_probability =
   predicted_probability`, `stage2_trained=False`), mirroring Module 1
   Stage 2's fold-1 no-op exactly.
3. **Pooled vs. per-district re-validated empirically** (not assumed from
   Decision 021's Stage-1 finding), using `stacked_xgboost` alone as the
   arbiter - mirrors `baseline_classifier.run_pooled_vs_per_district_comparison`.
4. **Fold-scoped contextual features are reused from Stage 1's own fold
   construction**, not recomputed independently: `compute_stage1_fold_boundaries`
   imports `baseline_classifier.compute_fold_boundaries` directly (a
   deliberate small improvement over Module 1's duplicated-logic pattern,
   since the function is already correct and exported - reduces drift risk).
   Climate anomalies attached to each historical row are the exact values
   Stage 1 saw when producing that row's probability (reusing a
   genuinely-already-known, correctly-scoped value as a later input is not
   leakage - same reasoning as `module1_forecasting/compensation_model.py`).
5. **`probability_residual_lag_1/2`** are built via the same
   full-calendar-reindex-then-shift construction as Module 1's
   `residual_lag_1/2` (Decision 015) - Module 2 Stage 1's fold structure has
   an analogous gap between the last walk-forward fold's validation end and
   the holdout block's start, so a naive shift over only the sparse
   out-of-sample rows would risk the same stale-value bug Decision 015 fixed.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import xgboost as xgb

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from sklearn.isotonic import IsotonicRegression  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE2_BASELINE_PREDICTIONS_PATH,
    MODULE2_FIGURES_DIR,
    MODULE2_STAGE1_FEATURE_TABLE_PATH,
    MODULE2_STAGE2_FINAL_MODEL_PATH,
    MODULE2_STAGE2_METRICS_PATH,
    MODULE2_STAGE2_MODELS_DIR,
    MODULE2_STAGE2_POOLED_VS_DISTRICT_PATH,
    MODULE2_STAGE2_PREDICTIONS_PATH,
)
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    compute_fold_climate_anomalies,
)
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    N_FOLDS as STAGE1_N_FOLDS,
)
from src.module2_classification.baseline_classifier import compute_fold_boundaries  # noqa: E402
from src.module2_classification.feature_engineering import (  # noqa: E402
    FOLD_AGNOSTIC_FEATURE_COLUMNS,
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
)

logger = logging.getLogger(__name__)

TARGET_COL = "label"
BASE_PROB_COL = "predicted_probability"

ARCHITECTURE_NAMES = ["isotonic", "platt", "stacked_xgboost"]
PRIMARY_METRIC = "brier_skill_score"
SECONDARY_THRESHOLD = 0.5

# Fold 1 has no prior out-of-sample Stage 1 data at all - documented no-op,
# mirrors Module 1 Stage 2's fold-1 no-op (see module docstring point 2).
FIRST_TRAINABLE_STAGE2_FOLD = 2

FOLD_AWARE_ANOMALY_COLUMNS = ["rainfall_anomaly", "temperature_anomaly", "humidity_anomaly"]
PROBABILITY_LAG_COLUMNS = ["probability_residual_lag_1", "probability_residual_lag_2"]

# Feature set for the `stacked_xgboost` architecture only - isotonic/platt
# are feature-free by design (see module docstring point 1).
STACKED_FEATURE_COLUMNS = (
    FOLD_AGNOSTIC_FEATURE_COLUMNS + FOLD_AWARE_ANOMALY_COLUMNS + [BASE_PROB_COL] + PROBABILITY_LAG_COLUMNS
)
CATEGORICAL_FEATURE_COLUMNS = ["District"]
STACKED_ALL_COLUMNS = STACKED_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS

# Fixed, conservative hyperparameters - not tuned per fold, same philosophy
# as Stage 1 (baseline_classifier.py) and Module 1 Stage 2.
XGB_STAGE2_PARAMS = dict(
    objective="binary:logistic",
    eval_metric="aucpr",
    tree_method="hist",
    enable_categorical=True,
    max_depth=4,
    learning_rate=0.05,
    n_estimators=300,
    subsample=0.8,
    colsample_bytree=0.8,
    reg_lambda=1.0,
    min_child_weight=5,
    random_state=42,
)

PREDICTION_OUTPUT_COLUMNS = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "label"]


# ---------------------------------------------------------------------------
# Logit helper (Platt scaling operates on the log-odds, not raw probability)
# ---------------------------------------------------------------------------

def _logit(p: np.ndarray, eps: float = 1e-6) -> np.ndarray:
    p_clipped = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    return np.log(p_clipped / (1 - p_clipped))


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def assemble_stage2_base_table(full_feature_df: pd.DataFrame) -> pd.DataFrame:
    """Read Stage 1's predictions, keep only the OFFICIAL model's rows (the
    one Stage 2 exists to correct), and attach Module 2's fold-agnostic
    contextual features (already present in `full_feature_df`, Stage 1's own
    feature table).
    """
    preds = pd.read_csv(MODULE2_BASELINE_PREDICTIONS_PATH)
    preds = preds[preds["is_selected_model"]].copy()
    preds["fold_id_numeric"] = pd.to_numeric(preds["fold_id"], errors="coerce")

    feature_cols = ["District", "Year", "Week"] + FOLD_AGNOSTIC_FEATURE_COLUMNS
    merged = preds.merge(full_feature_df[feature_cols], on=["District", "Year", "Week"], how="left")
    return merged


# ---------------------------------------------------------------------------
# Fold-scoped climate anomalies (reused from Stage 1's own fold-anomaly
# construction, not recomputed independently)
# ---------------------------------------------------------------------------

def build_fold_scoped_anomalies(
    full_feature_df: pd.DataFrame,
    fold_train_keys: dict[int, set],
    fold_val_keys: dict[int, set],
    pre_holdout_keys: set,
    holdout_keys: set,
) -> pd.DataFrame:
    """For each Stage-1 fold, recompute `compute_fold_climate_anomalies` on
    that fold's own training window and attach it to that fold's validation
    rows - reproduces the exact anomaly values Stage 1 saw when producing
    each row's `predicted_probability`. Mirrors
    `module1_forecasting/compensation_model.build_fold_scoped_anomalies`.
    """
    df = full_feature_df.copy()
    keys = list(zip(df["District"], df["Year"].astype(int), df["Week"].astype(int)))
    df["_key"] = keys

    anomaly_frames: list[pd.DataFrame] = []

    for fold_id in range(1, STAGE1_N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_id])
        if not train_mask.any():
            logger.warning("Fold %d has no training rows for anomaly computation - skipping.", fold_id)
            continue
        anomalies = compute_fold_climate_anomalies(
            df, train_mask, rainfall_col=RAINFALL_COLUMN, temperature_col=TEMPERATURE_COLUMN, humidity_col=HUMIDITY_COLUMN,
        )
        val_mask = df["_key"].isin(fold_val_keys[fold_id])
        sub = anomalies.loc[val_mask].copy()
        sub["District"] = df.loc[val_mask, "District"].to_numpy()
        sub["Year"] = df.loc[val_mask, "Year"].to_numpy()
        sub["Week"] = df.loc[val_mask, "Week"].to_numpy()
        anomaly_frames.append(sub)

    train_mask = df["_key"].isin(pre_holdout_keys)
    anomalies = compute_fold_climate_anomalies(
        df, train_mask, rainfall_col=RAINFALL_COLUMN, temperature_col=TEMPERATURE_COLUMN, humidity_col=HUMIDITY_COLUMN,
    )
    val_mask = df["_key"].isin(holdout_keys)
    sub = anomalies.loc[val_mask].copy()
    sub["District"] = df.loc[val_mask, "District"].to_numpy()
    sub["Year"] = df.loc[val_mask, "Year"].to_numpy()
    sub["Week"] = df.loc[val_mask, "Week"].to_numpy()
    anomaly_frames.append(sub)

    combined = pd.concat(anomaly_frames, ignore_index=True)
    return combined[["District", "Year", "Week"] + FOLD_AWARE_ANOMALY_COLUMNS]


# ---------------------------------------------------------------------------
# Probability-residual lags (Decision-015-style gap-safe construction)
# ---------------------------------------------------------------------------

def build_probability_residual_lags(full_feature_df: pd.DataFrame, stage2_base: pd.DataFrame) -> pd.DataFrame:
    """`probability_residual_lag_1/2`: reindex each district's out-of-sample
    `probability_residual = label - predicted_probability` onto the FULL
    weekly calendar (not just the sparse out-of-sample rows) before taking
    `shift(1)/shift(2)` - the same gap-safe construction Decision 015 used
    for Module 1's `residual_lag_1/2`. Module 2 Stage 1's fold structure has
    an analogous gap between the last walk-forward fold's validation end and
    the holdout block's start, so a naive shift over only the concatenated
    out-of-sample rows would risk pulling in a stale value across that gap.
    """
    calendar = full_feature_df[["District", "Year", "Week"]].drop_duplicates()

    oos = stage2_base[["District", "Year", "Week", TARGET_COL, BASE_PROB_COL]].copy()
    oos["probability_residual"] = oos[TARGET_COL] - oos[BASE_PROB_COL]
    oos.loc[oos[TARGET_COL].isna(), "probability_residual"] = np.nan

    merged = calendar.merge(oos[["District", "Year", "Week", "probability_residual"]], on=["District", "Year", "Week"], how="left")
    merged = merged.sort_values(["District", "Year", "Week"]).reset_index(drop=True)

    grouped = merged.groupby("District")["probability_residual"]
    merged["probability_residual_lag_1"] = grouped.shift(1)
    merged["probability_residual_lag_2"] = grouped.shift(2)

    return merged[["District", "Year", "Week"] + PROBABILITY_LAG_COLUMNS]


def assemble_stage2_table() -> tuple[pd.DataFrame, dict[int, set], dict[int, set], set, set]:
    full_feature_df = pd.read_csv(MODULE2_STAGE1_FEATURE_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])

    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(full_feature_df)

    base = assemble_stage2_base_table(full_feature_df)
    anomalies = build_fold_scoped_anomalies(full_feature_df, fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys)
    probability_lags = build_probability_residual_lags(full_feature_df, base)

    stage2_df = base.merge(anomalies, on=["District", "Year", "Week"], how="left")
    stage2_df = stage2_df.merge(probability_lags, on=["District", "Year", "Week"], how="left")

    return stage2_df, fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys


# ---------------------------------------------------------------------------
# Architecture fit/predict
# ---------------------------------------------------------------------------

def fit_and_calibrate(
    architecture: str, train_df: pd.DataFrame, val_df: pd.DataFrame, feature_columns: list[str] | None = None,
):
    """Fit `architecture` on `train_df` (already filtered to defined-label,
    out-of-sample prior-fold rows) and predict calibrated probabilities for
    `val_df`. Returns `(calibrated_probability: np.ndarray, fitted_model)`.

    `feature_columns` is only meaningful for `stacked_xgboost` (defaults to
    the full pooled feature set including `District`); the pooled-vs-
    per-district comparison passes the numeric-only subset for its
    per-district runs. Ignored by `isotonic`/`platt` (feature-free by design).
    """
    if architecture == "isotonic":
        model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        model.fit(train_df[BASE_PROB_COL].to_numpy(dtype=float), train_df[TARGET_COL].to_numpy(dtype=float))
        return model.predict(val_df[BASE_PROB_COL].to_numpy(dtype=float)), model

    if architecture == "platt":
        X_train = _logit(train_df[BASE_PROB_COL].to_numpy(dtype=float)).reshape(-1, 1)
        y_train = train_df[TARGET_COL].to_numpy(dtype=int)
        model = LogisticRegression(max_iter=2000, random_state=42)
        model.fit(X_train, y_train)
        X_val = _logit(val_df[BASE_PROB_COL].to_numpy(dtype=float)).reshape(-1, 1)
        return model.predict_proba(X_val)[:, 1], model

    if architecture == "stacked_xgboost":
        cols = feature_columns or STACKED_ALL_COLUMNS
        use_district = "District" in cols
        numeric_cols = [c for c in cols if c != "District"]
        select_cols = numeric_cols + (["District"] if use_district else [])

        X_train = train_df[select_cols].copy()
        X_val = val_df[select_cols].copy()
        if use_district:
            X_train["District"] = pd.Categorical(X_train["District"], categories=DISTRICTS)
            X_val["District"] = pd.Categorical(X_val["District"], categories=DISTRICTS)

        y_train = train_df[TARGET_COL].to_numpy(dtype=int)
        n_pos = int(y_train.sum())
        n_neg = len(y_train) - n_pos
        scale_pos_weight = (n_neg / n_pos) if n_pos > 0 else 1.0

        model = xgb.XGBClassifier(**XGB_STAGE2_PARAMS, scale_pos_weight=scale_pos_weight)
        model.fit(X_train, y_train)
        return model.predict_proba(X_val)[:, 1], model

    raise ValueError(f"Unknown architecture: {architecture!r}")


def _fit_and_predict_per_district_stacked(train_df: pd.DataFrame, val_df: pd.DataFrame) -> np.ndarray | None:
    """One `stacked_xgboost` model for a SINGLE district's fold slice (no
    `District` feature needed - it's constant). Returns `None` if the
    training slice doesn't have both classes present or is too small."""
    y_train = train_df[TARGET_COL].to_numpy(dtype=int)
    if len(y_train) < 4 or len(np.unique(y_train)) < 2 or val_df.empty:
        return None
    proba, _ = fit_and_calibrate("stacked_xgboost", train_df, val_df, feature_columns=STACKED_FEATURE_COLUMNS)
    return proba


# ---------------------------------------------------------------------------
# Per-fold scoring
# ---------------------------------------------------------------------------

def _score_predictions(label: pd.Series, proba: np.ndarray) -> dict:
    y_true = label.to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    pred_label = (np.asarray(proba, dtype=float) >= SECONDARY_THRESHOLD).astype(float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, proba, mask=mask),
        "accuracy": evaluate.accuracy(y_true, pred_label, mask=mask),
        "precision": evaluate.precision(y_true, pred_label, mask=mask),
        "recall": evaluate.recall(y_true, pred_label, mask=mask),
        "specificity": evaluate.specificity(y_true, pred_label, mask=mask),
        "f1": evaluate.f1(y_true, pred_label, mask=mask),
        "brier_score": evaluate.brier_score(y_true, proba, mask=mask),
        "brier_skill_score": evaluate.brier_skill_score(y_true, proba, mask=mask),
        "prevalence": evaluate.prevalence(y_true, mask=mask),
        "n_obs_scored": int(mask.sum()),
        "n_obs_total": int(len(y_true)),
    }


def _build_prediction_rows(
    val_rows: pd.DataFrame, calibrated_proba: np.ndarray, architecture: str, fold_id, split: str, stage2_trained: bool,
) -> pd.DataFrame:
    out = val_rows[PREDICTION_OUTPUT_COLUMNS].copy()
    out["split"] = split
    out["fold_id"] = fold_id
    out["stage1_predicted_probability"] = val_rows[BASE_PROB_COL].to_numpy()
    out["architecture"] = architecture
    out["calibrated_probability"] = np.asarray(calibrated_proba, dtype=float)
    out["predicted_label_at_0.5"] = (out["calibrated_probability"] >= SECONDARY_THRESHOLD).astype(int)
    out["stage2_trained"] = stage2_trained
    return out


# ---------------------------------------------------------------------------
# Main benchmark (folds 2-13 x 3 architectures, plus fold-1 no-op passthrough)
# ---------------------------------------------------------------------------

def run_stage2_benchmark(stage2_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[int, object]]]:
    """Benchmark all `ARCHITECTURE_NAMES` across Stage 2's 12 trainable folds
    (2-13), plus a documented fold-1 no-op passthrough. Also computes
    `architecture="stage1_raw"` rows at every fold (Stage 1's own
    probability, unmodified) so before/after comparison lives in one file.

    Returns `(predictions_df, metrics_df, fitted_models)`.
    """
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict] = []
    fitted_models: dict[str, dict[int, object]] = {name: {} for name in ARCHITECTURE_NAMES}

    # --- Fold 1: no-op passthrough (Decision 022) ---
    fold1_val = stage2_df[(stage2_df["fold_id_numeric"] == 1) & (stage2_df["split"] == "validation")]
    prediction_frames.append(
        _build_prediction_rows(fold1_val, fold1_val[BASE_PROB_COL].to_numpy(), "none", 1, "validation", stage2_trained=False)
    )
    metric_rows.append(
        {"architecture": "stage1_raw", "fold_id": 1, "split": "validation", **_score_predictions(fold1_val[TARGET_COL], fold1_val[BASE_PROB_COL].to_numpy())}
    )
    logger.info("Stage 2 fold 1: no-op passthrough (no prior out-of-sample Stage 1 data) - %d rows.", len(fold1_val))

    # --- Folds 2-13: trained on prior folds' pooled out-of-sample rows ---
    for fold_num in range(FIRST_TRAINABLE_STAGE2_FOLD, STAGE1_N_FOLDS + 1):
        train_mask = (
            (stage2_df["fold_id_numeric"] >= 1)
            & (stage2_df["fold_id_numeric"] < fold_num)
            & (stage2_df["split"] == "validation")
        )
        val_mask = (stage2_df["fold_id_numeric"] == fold_num) & (stage2_df["split"] == "validation")

        train_rows_all = stage2_df.loc[train_mask]
        val_rows_all = stage2_df.loc[val_mask]
        trainable_train = train_rows_all.dropna(subset=[TARGET_COL])

        if trainable_train.empty:
            raise ValueError(f"Stage 2 fold {fold_num} has zero trainable (defined-label) rows from prior folds.")

        metric_rows.append(
            {"architecture": "stage1_raw", "fold_id": fold_num, "split": "validation", **_score_predictions(val_rows_all[TARGET_COL], val_rows_all[BASE_PROB_COL].to_numpy())}
        )

        for architecture in ARCHITECTURE_NAMES:
            proba, fitted = fit_and_calibrate(architecture, trainable_train, val_rows_all)
            prediction_frames.append(_build_prediction_rows(val_rows_all, proba, architecture, fold_num, "validation", stage2_trained=True))
            scores = _score_predictions(val_rows_all[TARGET_COL], proba)
            metric_rows.append({"architecture": architecture, "fold_id": fold_num, "split": "validation", **scores})
            fitted_models[architecture][fold_num] = fitted

        logger.info(
            "Stage 2 fold %d: trained on %d prior-fold rows, scored %d rows across %d architectures.",
            fold_num, len(trainable_train), len(val_rows_all), len(ARCHITECTURE_NAMES),
        )

    predictions_df = pd.concat(prediction_frames, ignore_index=True)
    fold_metrics_df = pd.DataFrame(metric_rows)

    # validation_aggregate: median across the TRAINABLE folds (2-13) only -
    # fold 1 has no Stage-2 counterpart, so it's excluded from both the
    # architectures' and stage1_raw's aggregate for a fair comparison.
    numeric_metric_cols = [
        "pr_auc", "roc_auc", "accuracy", "precision", "recall", "specificity", "f1",
        "brier_score", "brier_skill_score", "prevalence",
    ]
    comparable = fold_metrics_df[fold_metrics_df["fold_id"] >= FIRST_TRAINABLE_STAGE2_FOLD]
    aggregate_rows = []
    for architecture, group in comparable.groupby("architecture"):
        agg = {col: float(np.nanmedian(group[col])) for col in numeric_metric_cols}
        aggregate_rows.append(
            {
                "architecture": architecture, "fold_id": "validation_aggregate", "split": "validation", **agg,
                "n_obs_scored": int(group["n_obs_scored"].sum()), "n_obs_total": int(group["n_obs_total"].sum()),
            }
        )

    metrics_df = pd.concat([fold_metrics_df, pd.DataFrame(aggregate_rows)], ignore_index=True)
    return predictions_df, metrics_df, fitted_models


# ---------------------------------------------------------------------------
# Pooled vs. per-district comparison (stacked_xgboost arbiter only)
# ---------------------------------------------------------------------------

def run_pooled_vs_per_district_comparison(
    stage2_df: pd.DataFrame, pooled_bss_by_fold: dict[int, float], districts: list[str] = DISTRICTS,
) -> pd.DataFrame:
    """Empirically validate pooled-vs-per-district for Stage 2 (Decision
    022) using `stacked_xgboost` alone as the arbiter - mirrors
    `baseline_classifier.run_pooled_vs_per_district_comparison` exactly, but
    scored by Brier Skill Score (Stage 2's primary metric) rather than PR-AUC.
    """
    rows: list[dict] = []

    for fold_num in range(FIRST_TRAINABLE_STAGE2_FOLD, STAGE1_N_FOLDS + 1):
        train_mask = (
            (stage2_df["fold_id_numeric"] >= 1)
            & (stage2_df["fold_id_numeric"] < fold_num)
            & (stage2_df["split"] == "validation")
        )
        val_mask = (stage2_df["fold_id_numeric"] == fold_num) & (stage2_df["split"] == "validation")

        per_district_bss = []
        for district in districts:
            d_train = stage2_df.loc[train_mask & (stage2_df["District"] == district)].dropna(subset=[TARGET_COL])
            d_val = stage2_df.loc[val_mask & (stage2_df["District"] == district)]
            proba = _fit_and_predict_per_district_stacked(d_train, d_val)
            if proba is None:
                continue
            score = evaluate.brier_skill_score(d_val[TARGET_COL].to_numpy(dtype=float), proba)
            if not np.isnan(score):
                per_district_bss.append(score)

        rows.append(
            {
                "fold_id": fold_num,
                "pooled_brier_skill_score": pooled_bss_by_fold.get(fold_num, float("nan")),
                "per_district_median_brier_skill_score": float(np.nanmedian(per_district_bss)) if per_district_bss else float("nan"),
                "per_district_mean_brier_skill_score": float(np.nanmean(per_district_bss)) if per_district_bss else float("nan"),
                "n_districts_scored": len(per_district_bss),
            }
        )
        logger.info(
            "Stage 2 pooled-vs-per-district fold %d: pooled BSS=%.4f, per-district median BSS=%.4f (n=%d districts scored)",
            fold_num, rows[-1]["pooled_brier_skill_score"], rows[-1]["per_district_median_brier_skill_score"], rows[-1]["n_districts_scored"],
        )

    comparison_df = pd.DataFrame(rows)
    summary = {
        "fold_id": "aggregate",
        "pooled_brier_skill_score": float(np.nanmedian(comparison_df["pooled_brier_skill_score"])),
        "per_district_median_brier_skill_score": float(np.nanmedian(comparison_df["per_district_median_brier_skill_score"])),
        "per_district_mean_brier_skill_score": float(np.nanmean(comparison_df["per_district_mean_brier_skill_score"])),
        "n_districts_scored": int(comparison_df["n_districts_scored"].sum()),
    }
    return pd.concat([comparison_df, pd.DataFrame([summary])], ignore_index=True)


# ---------------------------------------------------------------------------
# Architecture selection
# ---------------------------------------------------------------------------

def select_official_architecture(metrics_df: pd.DataFrame) -> str:
    """Pick the architecture with the highest median Brier Skill Score
    across the 12 trainable validation folds (Decision 022). Logs - does not
    silently drop - any PR-AUC/ROC-AUC regression vs. Stage 1's raw
    probability, since only isotonic/Platt provably cannot hurt ranking;
    `stacked_xgboost` in principle could.
    """
    aggregate = metrics_df[(metrics_df["fold_id"] == "validation_aggregate") & (metrics_df["architecture"] != "stage1_raw")]
    if aggregate.empty:
        raise ValueError("metrics_df has no candidate 'validation_aggregate' rows to select from.")

    winner = str(aggregate.loc[aggregate[PRIMARY_METRIC].idxmax(), "architecture"])
    winner_row = aggregate.set_index("architecture").loc[winner]

    stage1_raw_agg = metrics_df[(metrics_df["fold_id"] == "validation_aggregate") & (metrics_df["architecture"] == "stage1_raw")]
    if not stage1_raw_agg.empty:
        for metric in ("pr_auc", "roc_auc"):
            stage1_value = float(stage1_raw_agg[metric].iloc[0])
            winner_value = float(winner_row[metric])
            if winner_value < stage1_value - 1e-9:
                logger.warning(
                    "Selected architecture '%s' regresses on %s vs. Stage 1 raw (%.4f -> %.4f) - "
                    "flagged per Decision 022's gating check, not blocked.",
                    winner, metric, stage1_value, winner_value,
                )

    logger.info(
        "Official Stage 2 architecture selected: %s (median BSS=%.4f). Full comparison:\n%s",
        winner, winner_row[PRIMARY_METRIC],
        aggregate[["architecture", PRIMARY_METRIC, "pr_auc", "roc_auc"]].to_string(index=False),
    )
    return winner


# ---------------------------------------------------------------------------
# Held-out final block
# ---------------------------------------------------------------------------

def run_holdout_evaluation(stage2_df: pd.DataFrame, official_architecture: str) -> tuple[pd.DataFrame, pd.DataFrame, object]:
    """Train all 3 architectures on ALL 13 folds' pooled out-of-sample rows,
    score against the untouched holdout block. Returns `(predictions_df,
    metrics_df, official_fitted_model)`."""
    train_mask = (stage2_df["split"] == "validation") & (stage2_df["fold_id_numeric"].between(1, STAGE1_N_FOLDS))
    val_mask = stage2_df["split"] == "holdout"

    trainable_train = stage2_df.loc[train_mask].dropna(subset=[TARGET_COL])
    val_rows_all = stage2_df.loc[val_mask]

    prediction_frames = []
    metric_rows = [
        {"architecture": "stage1_raw", "fold_id": "holdout", "split": "holdout", **_score_predictions(val_rows_all[TARGET_COL], val_rows_all[BASE_PROB_COL].to_numpy())}
    ]
    official_fitted = None

    for architecture in ARCHITECTURE_NAMES:
        proba, fitted = fit_and_calibrate(architecture, trainable_train, val_rows_all)
        prediction_frames.append(_build_prediction_rows(val_rows_all, proba, architecture, "holdout", "holdout", stage2_trained=True))
        scores = _score_predictions(val_rows_all[TARGET_COL], proba)
        metric_rows.append({"architecture": architecture, "fold_id": "holdout", "split": "holdout", **scores})
        if architecture == official_architecture:
            official_fitted = fitted

    logger.info(
        "Stage 2 holdout: trained on %d rows (all 13 folds pooled), scored %d holdout rows across %d architectures.",
        len(trainable_train), len(val_rows_all), len(ARCHITECTURE_NAMES),
    )
    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(metric_rows), official_fitted


# ---------------------------------------------------------------------------
# Final production model
# ---------------------------------------------------------------------------

def train_final_production_model(stage2_df: pd.DataFrame, official_architecture: str):
    """Train one final `official_architecture` model on ALL available
    out-of-sample rows (13 folds + holdout, defined-label only), for
    potential future live scoring. Not used for any reported metric."""
    all_mask = (
        (stage2_df["split"] == "validation") & (stage2_df["fold_id_numeric"].between(1, STAGE1_N_FOLDS))
    ) | (stage2_df["split"] == "holdout")
    trainable = stage2_df.loc[all_mask].dropna(subset=[TARGET_COL])

    # fit_and_calibrate requires a val_df; reuse a throwaway trainable row
    # as a discarded prediction target (mirrors baseline_classifier.py).
    _, model = fit_and_calibrate(official_architecture, trainable, trainable.iloc[[0]])
    return model


def _model_file_path(base_dir: Path, stem: str, architecture: str) -> Path:
    suffix = ".json" if architecture == "stacked_xgboost" else ".joblib"
    return base_dir / f"{stem}{suffix}"


def _save_model(model, path: Path, architecture: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if architecture == "stacked_xgboost":
        model.save_model(str(path))
    else:
        joblib.dump(model, path)


# ---------------------------------------------------------------------------
# Reliability diagrams
# ---------------------------------------------------------------------------

def plot_reliability_diagrams(
    predictions_df: pd.DataFrame, official_architecture: str, output_dir: Path = MODULE2_FIGURES_DIR,
) -> None:
    """Stage-1-raw vs. Stage-2-calibrated reliability diagrams for the
    pooled validation folds (2-13) and the holdout block separately - the
    `MODULE_CONTEXT.md` "calibration plots" evaluation item never
    implemented before Stage 2 (Decision 022)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for split_name in ("validation", "holdout"):
        rows = predictions_df[(predictions_df["split"] == split_name) & (predictions_df["architecture"] == official_architecture)]
        if rows.empty:
            logger.warning("No '%s' rows for the official architecture - skipping its reliability diagram.", split_name)
            continue

        label = rows["label"].to_numpy(dtype=float)
        mask = ~np.isnan(label)
        if mask.sum() == 0:
            logger.warning("No defined-label rows for the %s reliability diagram - skipping.", split_name)
            continue

        raw_curve = evaluate.reliability_curve(label, rows["stage1_predicted_probability"].to_numpy(), mask=mask)
        calibrated_curve = evaluate.reliability_curve(label, rows["calibrated_probability"].to_numpy(), mask=mask)

        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Perfect calibration")
        if not raw_curve.empty:
            ax.plot(raw_curve["mean_predicted"], raw_curve["mean_observed"], marker="o", label="Stage 1 raw")
        if not calibrated_curve.empty:
            ax.plot(calibrated_curve["mean_predicted"], calibrated_curve["mean_observed"], marker="o", label=f"Stage 2 ({official_architecture})")
        ax.set_xlabel("Mean predicted probability")
        ax.set_ylabel("Mean observed outcome")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"Reliability diagram - {split_name} (official architecture: {official_architecture})")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / f"reliability_diagram_{split_name}.png", dpi=150)
        plt.close(fig)
        logger.info("Saved reliability diagram for %s split -> %s", split_name, output_dir / f"reliability_diagram_{split_name}.png")


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_stage2_pipeline() -> pd.DataFrame:
    logger.info("Assembling Stage 2 table (Stage 1 probabilities + contextual features + fold-scoped anomalies + probability-residual lags)...")
    stage2_df, _, _, _, _ = assemble_stage2_table()

    logger.info(
        "Running Stage 2 benchmark across architectures: %s (folds %d-%d trainable, fold 1 is a no-op passthrough)...",
        ARCHITECTURE_NAMES, FIRST_TRAINABLE_STAGE2_FOLD, STAGE1_N_FOLDS,
    )
    predictions_df, metrics_df, fitted_models = run_stage2_benchmark(stage2_df)

    official_architecture = select_official_architecture(metrics_df)

    pooled_bss_by_fold = (
        metrics_df[(metrics_df["architecture"] == "stacked_xgboost") & (metrics_df["fold_id"] != "validation_aggregate")]
        .set_index("fold_id")["brier_skill_score"].to_dict()
    )
    logger.info("Running Stage 2 pooled-vs-per-district comparison (stacked_xgboost arbiter)...")
    comparison_df = run_pooled_vs_per_district_comparison(stage2_df, pooled_bss_by_fold)

    logger.info("Running Stage 2 held-out final-block evaluation...")
    holdout_predictions_df, holdout_metrics_df, official_holdout_model = run_holdout_evaluation(stage2_df, official_architecture)

    predictions_df = pd.concat([predictions_df, holdout_predictions_df], ignore_index=True)
    predictions_df["is_selected_architecture"] = predictions_df["architecture"] == official_architecture
    metrics_df = pd.concat([metrics_df, holdout_metrics_df], ignore_index=True)
    metrics_df["selected"] = metrics_df["architecture"] == official_architecture

    MODULE2_STAGE2_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(MODULE2_STAGE2_PREDICTIONS_PATH, index=False)
    metrics_df.to_csv(MODULE2_STAGE2_METRICS_PATH, index=False)
    comparison_df.to_csv(MODULE2_STAGE2_POOLED_VS_DISTRICT_PATH, index=False)

    # Per-fold model files - official architecture only, reusing the
    # already-fitted models from run_stage2_benchmark rather than refitting.
    MODULE2_STAGE2_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for fold_num in range(FIRST_TRAINABLE_STAGE2_FOLD, STAGE1_N_FOLDS + 1):
        fold_model = fitted_models[official_architecture][fold_num]
        _save_model(fold_model, _model_file_path(MODULE2_STAGE2_MODELS_DIR, f"fold_{fold_num}", official_architecture), official_architecture)
    _save_model(official_holdout_model, _model_file_path(MODULE2_STAGE2_MODELS_DIR, "holdout", official_architecture), official_architecture)

    logger.info("Training final Stage 2 production model (%s) on all available out-of-sample data...", official_architecture)
    final_model = train_final_production_model(stage2_df, official_architecture)
    _save_model(
        final_model, MODULE2_STAGE2_FINAL_MODEL_PATH.with_suffix(".json" if official_architecture == "stacked_xgboost" else ".joblib"), official_architecture,
    )

    logger.info("Plotting reliability diagrams (Stage 1 raw vs. Stage 2 %s)...", official_architecture)
    plot_reliability_diagrams(predictions_df, official_architecture)

    logger.info(
        "Stage 2 complete: official_architecture=%s | predictions -> %s | metrics -> %s | "
        "pooled-vs-district -> %s | reliability diagrams -> %s",
        official_architecture, MODULE2_STAGE2_PREDICTIONS_PATH, MODULE2_STAGE2_METRICS_PATH,
        MODULE2_STAGE2_POOLED_VS_DISTRICT_PATH, MODULE2_FIGURES_DIR,
    )
    return predictions_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stage2_pipeline()
