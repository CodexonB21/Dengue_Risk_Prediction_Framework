"""Module 2 Stage 1 - baseline outbreak classifier.

Implements the design confirmed with the user before this file was written
(see `module_2_classification/EXPERIMENT_LOG.md` M2-001 and
`research_context/RESEARCH_DECISIONS.md` Decision 021 for the permanent
record):

1. **Pooled model, not per-district** (mirrors Module 1 Stage 2's Decision
   014 reasoning): one classifier per walk-forward fold, trained on all 25
   districts' rows together with `District` as a categorical feature - not
   25 separate per-district models. This is validated EMPIRICALLY, not
   assumed: `run_pooled_vs_per_district_comparison()` benchmarks pooled vs.
   per-district using XGBoost alone as the comparison arbiter (no
   imputation/encoding confound either way).
2. **New `MODULE2_MIN_TRAIN_YEARS = 4`** (`src/config.py`, Decision 021):
   `validation.py`'s SARIMA-tuned `DEFAULT_MIN_TRAIN_YEARS=3` was verified
   empirically to leave fold 1's ENTIRE training window with zero rows that
   have a defined label - the label's own 3-strictly-prior-years requirement
   (Decision 019) overlaps exactly with that window, for every district
   simultaneously (a calendar-driven effect pooling cannot rescue). Using 4
   years instead yields 13 walk-forward folds, each with genuinely trainable
   rows.
3. **Three benchmarked models per fold**: Logistic Regression, Random
   Forest, XGBoost. NaN/categorical handling differs by model (corrects the
   original premise that "tree-based models handle NaN natively" - only
   true for XGBoost among these three; `sklearn.ensemble.RandomForestClassifier`
   does NOT accept NaN):
   - XGBoost: raw features, `District` as a native pandas categorical
     (`enable_categorical=True`), NaNs left untouched - mirrors Module 1
     Stage 2's `compensation_model.py`.
   - Logistic Regression / Random Forest: identical `ColumnTransformer`
     pipeline (median-impute numeric features, one-hot encode `District`
     against the fixed `DISTRICTS` list; Logistic Regression additionally
     standard-scales). Imputer/scaler/encoder are fit on each fold's
     TRAINING rows only, applied to train+val - no leakage.
4. **Imbalance handling**: `class_weight="balanced"` (Logistic Regression,
   Random Forest); `scale_pos_weight = n_neg / n_pos` computed from that
   fold's OWN training labels (XGBoost). Not SMOTE - synthetic oversampling
   across a temporal walk-forward split would blur the fold boundary.
5. **Model selection**: one model type is chosen using the median PR-AUC
   (`evaluate.pr_auc`) across all 13 walk-forward folds; that same model
   type is used consistently as the "official" Stage 1 output (not a
   per-fold winner) - the artifact Stage 2 will eventually consume. All 3
   models' per-fold metrics are kept in the metrics CSV regardless.
6. **Held-out final block** (mirrors Decision 009): after the 13 folds, all
   3 models are also trained on the full pre-holdout window and scored
   against the untouched final `DEFAULT_HOLDOUT_YEARS` (2) years - genuinely
   never touched during fold-based model selection.
7. **Fixed, conservative hyperparameters** for every fold (not tuned per
   fold) - the small-data regime in early folds calls for deliberately
   shallow/regularized models rather than an expensive per-fold search.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH,
    MODULE2_BASELINE_FINAL_MODEL_PATH,
    MODULE2_BASELINE_METRICS_PATH,
    MODULE2_BASELINE_MODELS_DIR,
    MODULE2_BASELINE_PREDICTIONS_PATH,
    MODULE2_MIN_TRAIN_YEARS,
    MODULE2_POOLED_VS_DISTRICT_PATH,
    MODULE2_STAGE1_FEATURE_TABLE_PATH,
)
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    compute_fold_climate_anomalies,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    generate_walk_forward_folds,
    get_district_series,
    get_holdout_series,
)
from src.module2_classification import evaluate  # noqa: E402
from src.module2_classification.feature_engineering import (  # noqa: E402
    FOLD_AGNOSTIC_FEATURE_COLUMNS,
    HUMIDITY_COLUMN,
    RAINFALL_COLUMN,
    TEMPERATURE_COLUMN,
)
from src.module2_classification.labels import compute_epidemic_threshold_labels  # noqa: E402

logger = logging.getLogger(__name__)

TARGET_COL = "label"

# Feature Group M2-3's fold-aware anomalies (NOT in the fold-agnostic feature
# table - must be recomputed per fold, see feature_engineering.py docstring).
FOLD_AWARE_FEATURE_COLUMNS = ["rainfall_anomaly", "temperature_anomaly", "humidity_anomaly"]
NUMERIC_FEATURE_COLUMNS = FOLD_AGNOSTIC_FEATURE_COLUMNS + FOLD_AWARE_FEATURE_COLUMNS
CATEGORICAL_FEATURE_COLUMNS = ["District"]
ALL_FEATURE_COLUMNS = NUMERIC_FEATURE_COLUMNS + CATEGORICAL_FEATURE_COLUMNS

MODEL_NAMES = ["logistic_regression", "random_forest", "xgboost"]
PRIMARY_METRIC = "pr_auc"
SECONDARY_THRESHOLD = 0.5

WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS
MIN_TRAIN_YEARS = MODULE2_MIN_TRAIN_YEARS
N_FOLDS = 13  # Verified empirically (Decision 021) for MIN_TRAIN_YEARS=4.

# Fixed, conservative hyperparameters - not tuned per fold (see module docstring).
RF_PARAMS = dict(
    n_estimators=300, max_depth=8, min_samples_leaf=5,
    class_weight="balanced", random_state=42, n_jobs=-1,
)
LR_PARAMS = dict(class_weight="balanced", max_iter=2000, random_state=42)
# Tuned via Optuna (60 trials, 13-fold median PR-AUC objective) and
# holdout-gated in scripts/tune_stage1_xgboost.py (Decision 023). Adopted:
# holdout PR-AUC improved 0.5380 -> 0.5577 (+0.0198) and holdout ROC-AUC
# improved 0.8978 -> 0.9109 over the prior hand-picked defaults. Holdout
# Brier/BSS got worse under these params, but that is expected and does not
# block adoption - Stage 1 was never selected or tuned for calibration
# (Decision 021), and Stage 2's Platt scaling recalibrates whatever Stage 1
# produces regardless of its raw scale (Decision 022).
XGB_BASE_PARAMS = dict(
    objective="binary:logistic",
    eval_metric="aucpr",
    tree_method="hist",
    enable_categorical=True,
    max_depth=3,
    learning_rate=0.012372716856545026,
    n_estimators=217,
    subsample=0.6565207665644811,
    colsample_bytree=0.5962294998146025,
    reg_lambda=1.0757842716405472,
    min_child_weight=10,
    reg_alpha=4.11972811587084,
    gamma=2.4930165018747936,
    random_state=42,
)


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def assemble_labeled_feature_table(
    input_path: Path = MODULE2_STAGE1_FEATURE_TABLE_PATH,
) -> pd.DataFrame:
    """Read the Stage 1 fold-agnostic feature table and attach the
    fold-aware epidemic-threshold label (Decision 019). The feature table
    already carries `Number_of_Cases`/`is_imputed`/`District`/`Year`/`Week`,
    so no second read of `weekly_modeling_table.csv` is needed.
    """
    df = pd.read_csv(input_path, parse_dates=["Week_Start_Date", "Week_End_Date"])
    labeled = compute_epidemic_threshold_labels(df)
    labeled["_key"] = list(
        zip(labeled["District"], labeled["Year"].astype(int), labeled["Week"].astype(int))
    )
    return labeled


# ---------------------------------------------------------------------------
# Walk-forward fold boundaries (Decision 021's MIN_TRAIN_YEARS=4)
# ---------------------------------------------------------------------------

def compute_fold_boundaries(
    df: pd.DataFrame, districts: list[str] = DISTRICTS
) -> tuple[dict[int, set], dict[int, set], set, set]:
    """Reconstruct per-district fold + holdout boundaries via
    `validation.py`'s (unchanged) fold generator, using Decision 021's
    Module-2-specific `MIN_TRAIN_YEARS=4`.

    Returns `(fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys)`
    where each `fold_*_keys` value is a `set[(District, Year, Week)]`.
    """
    fold_train_keys: dict[int, set] = {i: set() for i in range(1, N_FOLDS + 1)}
    fold_val_keys: dict[int, set] = {i: set() for i in range(1, N_FOLDS + 1)}
    pre_holdout_keys: set = set()
    holdout_keys: set = set()

    for district in districts:
        series = get_district_series(df, district, value_col="Number_of_Cases")

        for fold_id, (train_index, val_index) in enumerate(
            generate_walk_forward_folds(
                series,
                holdout_years=HOLDOUT_YEARS,
                min_train_years=MIN_TRAIN_YEARS,
                weeks_per_year=WEEKS_PER_YEAR,
            ),
            start=1,
        ):
            fold_train_keys[fold_id].update((district, int(y), int(w)) for y, w in train_index)
            fold_val_keys[fold_id].update((district, int(y), int(w)) for y, w in val_index)

        holdout = get_holdout_series(series, holdout_years=HOLDOUT_YEARS, weeks_per_year=WEEKS_PER_YEAR)
        pre_holdout = series.iloc[: len(series) - len(holdout)]
        pre_holdout_keys.update((district, int(y), int(w)) for y, w in pre_holdout.index)
        holdout_keys.update((district, int(y), int(w)) for y, w in holdout.index)

    n_folds_found = sum(1 for k in fold_train_keys if fold_train_keys[k])
    if n_folds_found != N_FOLDS:
        raise ValueError(
            f"Expected {N_FOLDS} walk-forward folds (MIN_TRAIN_YEARS={MIN_TRAIN_YEARS}), "
            f"reconstructed {n_folds_found} - fold boundaries no longer match this module's assumptions."
        )

    return fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys


# ---------------------------------------------------------------------------
# Fold-scoped climate anomalies (Feature Group M2-3)
# ---------------------------------------------------------------------------

def attach_fold_anomalies(df: pd.DataFrame, train_mask: pd.Series) -> pd.DataFrame:
    """Return a copy of `df` with `rainfall_anomaly`/`temperature_anomaly`/
    `humidity_anomaly` columns attached, computed from `train_mask`'s rows
    only (reused unchanged from Module 1's `compute_fold_climate_anomalies`,
    already aligned to `df`'s row order/index - no merge needed). Applies to
    BOTH that fold's train and validation rows, since both need the same
    frozen training-window climate norm as a feature.
    """
    anomalies = compute_fold_climate_anomalies(
        df, train_mask,
        rainfall_col=RAINFALL_COLUMN, temperature_col=TEMPERATURE_COLUMN, humidity_col=HUMIDITY_COLUMN,
    )
    out = df.copy()
    out[FOLD_AWARE_FEATURE_COLUMNS] = anomalies[FOLD_AWARE_FEATURE_COLUMNS]
    return out


# ---------------------------------------------------------------------------
# Model fit/predict helpers
# ---------------------------------------------------------------------------

def build_sklearn_preprocessor(include_scaler: bool) -> ColumnTransformer:
    """Shared preprocessing for Logistic Regression / Random Forest - neither
    accepts NaN or raw categorical strings natively (Decision 021 correction:
    sklearn's RandomForestClassifier does NOT handle missing values, unlike
    XGBoost). Median-imputes numeric features; one-hot encodes `District`
    against the FIXED `DISTRICTS` list (not `df`'s own unique values) so
    column layout is stable even if a fold's slice happens to omit a
    district. Logistic Regression additionally standard-scales (RF doesn't
    need it, and skipping it avoids needlessly perturbing RF's splits).
    """
    numeric_steps = [("imputer", SimpleImputer(strategy="median"))]
    if include_scaler:
        numeric_steps.append(("scaler", StandardScaler()))
    numeric_pipeline = Pipeline(numeric_steps)
    categorical_pipeline = Pipeline(
        [("onehot", OneHotEncoder(categories=[DISTRICTS], handle_unknown="ignore"))]
    )
    return ColumnTransformer(
        [
            ("num", numeric_pipeline, NUMERIC_FEATURE_COLUMNS),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURE_COLUMNS),
        ]
    )


def fit_and_predict(
    model_name: str, train_df: pd.DataFrame, val_df: pd.DataFrame, feature_columns: list[str] | None = None,
    xgb_params: dict | None = None,
):
    """Fit `model_name` on `train_df` (must already be filtered to rows with
    a defined label) and predict probabilities for `val_df`.

    `feature_columns` defaults to the full pooled feature set
    (`ALL_FEATURE_COLUMNS`); the pooled-vs-per-district comparison passes
    `NUMERIC_FEATURE_COLUMNS` (no `District`) for its per-district XGBoost runs.

    `xgb_params` (XGBoost only) overrides `XGB_BASE_PARAMS` when given -
    added for `scripts/tune_stage1_xgboost.py`'s Optuna search (Decision
    023), so the walk-forward loop can be reused unchanged to score
    candidate hyperparameter sets. `scale_pos_weight` is still always
    computed fresh from the fold's own training labels, never overridable -
    it is a leakage-safety property of the fold, not a tunable hyperparameter.

    Returns `(predicted_probability: np.ndarray, fitted_model)`.
    """
    numeric_cols = [c for c in (feature_columns or ALL_FEATURE_COLUMNS) if c in NUMERIC_FEATURE_COLUMNS]
    use_categorical = "District" in (feature_columns or ALL_FEATURE_COLUMNS)
    y_train = train_df[TARGET_COL].to_numpy(dtype=int)

    if model_name == "xgboost":
        cols = numeric_cols + (["District"] if use_categorical else [])
        X_train = train_df[cols].copy()
        X_val = val_df[cols].copy()
        if use_categorical:
            X_train["District"] = pd.Categorical(X_train["District"], categories=DISTRICTS)
            X_val["District"] = pd.Categorical(X_val["District"], categories=DISTRICTS)
        n_pos = int(y_train.sum())
        n_neg = len(y_train) - n_pos
        scale_pos_weight = (n_neg / n_pos) if n_pos > 0 else 1.0
        model = xgb.XGBClassifier(**(xgb_params or XGB_BASE_PARAMS), scale_pos_weight=scale_pos_weight)
        model.fit(X_train, y_train)
        proba = model.predict_proba(X_val)[:, 1]
        return proba, model

    if not use_categorical:
        raise ValueError(f"model_name={model_name!r} requires the District column (sklearn per-district path unsupported).")

    X_train = train_df[numeric_cols + CATEGORICAL_FEATURE_COLUMNS]
    X_val = val_df[numeric_cols + CATEGORICAL_FEATURE_COLUMNS]
    preprocessor = build_sklearn_preprocessor(include_scaler=(model_name == "logistic_regression"))
    if model_name == "logistic_regression":
        clf = LogisticRegression(**LR_PARAMS)
    elif model_name == "random_forest":
        clf = RandomForestClassifier(**RF_PARAMS)
    else:
        raise ValueError(f"Unknown model_name: {model_name!r}")

    pipeline = Pipeline([("preprocess", preprocessor), ("clf", clf)])
    pipeline.fit(X_train, y_train)
    proba = pipeline.predict_proba(X_val)[:, 1]
    return proba, pipeline


def _fit_and_predict_per_district_xgb(train_df: pd.DataFrame, val_df: pd.DataFrame) -> np.ndarray | None:
    """One XGBoost model for a SINGLE district's fold slice (no `District`
    feature needed - it's constant). Returns `None` if the training slice
    doesn't have both classes present (too little history to fit)."""
    y_train = train_df[TARGET_COL].to_numpy(dtype=int)
    if len(y_train) < 4 or len(np.unique(y_train)) < 2:
        return None
    proba, _ = fit_and_predict("xgboost", train_df, val_df, feature_columns=NUMERIC_FEATURE_COLUMNS)
    return proba


# ---------------------------------------------------------------------------
# Per-fold metrics
# ---------------------------------------------------------------------------

def _score_predictions(label: pd.Series, proba: np.ndarray) -> dict:
    y_true = label.to_numpy(dtype=float)
    mask = ~np.isnan(y_true)
    pred_label = (proba >= SECONDARY_THRESHOLD).astype(float)
    return {
        "pr_auc": evaluate.pr_auc(y_true, proba, mask=mask),
        "roc_auc": evaluate.roc_auc(y_true, proba, mask=mask),
        "accuracy": evaluate.accuracy(y_true, pred_label, mask=mask),
        "precision": evaluate.precision(y_true, pred_label, mask=mask),
        "recall": evaluate.recall(y_true, pred_label, mask=mask),
        "specificity": evaluate.specificity(y_true, pred_label, mask=mask),
        "f1": evaluate.f1(y_true, pred_label, mask=mask),
        "brier_score": evaluate.brier_score(y_true, proba, mask=mask),
        "prevalence": evaluate.prevalence(y_true, mask=mask),
        "n_obs_scored": int(mask.sum()),
        "n_obs_total": int(len(y_true)),
    }


PREDICTION_OUTPUT_COLUMNS = ["District", "Year", "Week", "Number_of_Cases", "is_imputed", "label"]


def _build_prediction_rows(
    val_rows: pd.DataFrame, proba: np.ndarray, model_name: str, fold_id, split: str,
) -> pd.DataFrame:
    out = val_rows[PREDICTION_OUTPUT_COLUMNS].copy()
    out["split"] = split
    out["fold_id"] = fold_id
    out["model"] = model_name
    out["predicted_probability"] = proba
    out["predicted_label_at_0.5"] = (proba >= SECONDARY_THRESHOLD).astype(int)
    return out


# ---------------------------------------------------------------------------
# Main pooled benchmark (all 13 folds x 3 models)
# ---------------------------------------------------------------------------

def run_benchmark(
    df: pd.DataFrame, fold_train_keys: dict[int, set], fold_val_keys: dict[int, set],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[int, object]]]:
    """Benchmark all `MODEL_NAMES` across all `N_FOLDS` walk-forward folds,
    pooled across all 25 districts (`District` as a categorical feature).

    Returns `(predictions_df, metrics_df, fitted_models)`. `predictions_df`
    includes EVERY validation row (even undefined-label ones, so probability
    output is a complete audit trail); `metrics_df` scores only
    defined-label rows. `fitted_models[model_name][fold_num]` retains every
    fold's fitted model so the orchestrator can save the official model's
    fold artifacts without refitting.
    """
    prediction_frames: list[pd.DataFrame] = []
    metric_rows: list[dict] = []
    fitted_models: dict[str, dict[int, object]] = {name: {} for name in MODEL_NAMES}

    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        train_rows_all = fold_df.loc[train_mask]
        val_rows_all = fold_df.loc[val_mask]
        trainable_train = train_rows_all.dropna(subset=[TARGET_COL])

        if trainable_train.empty:
            raise ValueError(f"Fold {fold_num} has zero trainable (defined-label) rows - MIN_TRAIN_YEARS is too small.")

        for model_name in MODEL_NAMES:
            proba, fitted = fit_and_predict(model_name, trainable_train, val_rows_all)
            prediction_frames.append(_build_prediction_rows(val_rows_all, proba, model_name, fold_num, "validation"))

            scores = _score_predictions(val_rows_all[TARGET_COL], proba)
            metric_rows.append({"model": model_name, "fold_id": fold_num, "split": "validation", **scores})
            fitted_models[model_name][fold_num] = fitted

        logger.info(
            "Fold %d: trained on %d rows (%d districts), scored %d validation rows across %d models.",
            fold_num, len(trainable_train), trainable_train["District"].nunique(), len(val_rows_all), len(MODEL_NAMES),
        )

    predictions_df = pd.concat(prediction_frames, ignore_index=True)
    fold_metrics_df = pd.DataFrame(metric_rows)

    aggregate_rows = []
    numeric_metric_cols = [
        "pr_auc", "roc_auc", "accuracy", "precision", "recall", "specificity", "f1", "brier_score", "prevalence",
    ]
    for model_name, group in fold_metrics_df.groupby("model"):
        agg = {col: float(np.nanmedian(group[col])) for col in numeric_metric_cols}
        aggregate_rows.append(
            {
                "model": model_name, "fold_id": "validation_aggregate", "split": "validation", **agg,
                "n_obs_scored": int(group["n_obs_scored"].sum()), "n_obs_total": int(group["n_obs_total"].sum()),
            }
        )

    metrics_df = pd.concat([fold_metrics_df, pd.DataFrame(aggregate_rows)], ignore_index=True)
    return predictions_df, metrics_df, fitted_models


# ---------------------------------------------------------------------------
# Pooled vs. per-district comparison (point 1 - XGBoost arbiter only)
# ---------------------------------------------------------------------------

def run_pooled_vs_per_district_comparison(
    df: pd.DataFrame,
    fold_train_keys: dict[int, set],
    fold_val_keys: dict[int, set],
    pooled_pr_auc_by_fold: dict[int, float],
    districts: list[str] = DISTRICTS,
) -> pd.DataFrame:
    """Empirically validate pooled-vs-per-district (confirmed design
    decision) using XGBoost alone as the arbiter model - no
    imputation/encoding pipeline difference to confound the comparison
    either way. `pooled_pr_auc_by_fold` reuses the already-computed pooled
    XGBoost per-fold PR-AUC from `run_benchmark` rather than refitting.
    """
    rows: list[dict] = []

    for fold_num in range(1, N_FOLDS + 1):
        train_mask = df["_key"].isin(fold_train_keys[fold_num])
        val_mask = df["_key"].isin(fold_val_keys[fold_num])
        fold_df = attach_fold_anomalies(df, train_mask)

        per_district_pr_aucs = []
        for district in districts:
            district_train = fold_df.loc[train_mask & (fold_df["District"] == district)].dropna(subset=[TARGET_COL])
            district_val = fold_df.loc[val_mask & (fold_df["District"] == district)]
            proba = _fit_and_predict_per_district_xgb(district_train, district_val)
            if proba is None:
                continue
            score = evaluate.pr_auc(district_val[TARGET_COL].to_numpy(dtype=float), proba)
            if not np.isnan(score):
                per_district_pr_aucs.append(score)

        rows.append(
            {
                "fold_id": fold_num,
                "pooled_pr_auc": pooled_pr_auc_by_fold.get(fold_num, float("nan")),
                "per_district_median_pr_auc": float(np.nanmedian(per_district_pr_aucs)) if per_district_pr_aucs else float("nan"),
                "per_district_mean_pr_auc": float(np.nanmean(per_district_pr_aucs)) if per_district_pr_aucs else float("nan"),
                "n_districts_scored": len(per_district_pr_aucs),
            }
        )
        logger.info(
            "Pooled-vs-per-district fold %d: pooled=%.4f, per-district median=%.4f (n=%d districts scored)",
            fold_num, rows[-1]["pooled_pr_auc"], rows[-1]["per_district_median_pr_auc"], rows[-1]["n_districts_scored"],
        )

    comparison_df = pd.DataFrame(rows)
    summary = {
        "fold_id": "aggregate",
        "pooled_pr_auc": float(np.nanmedian(comparison_df["pooled_pr_auc"])),
        "per_district_median_pr_auc": float(np.nanmedian(comparison_df["per_district_median_pr_auc"])),
        "per_district_mean_pr_auc": float(np.nanmean(comparison_df["per_district_mean_pr_auc"])),
        "n_districts_scored": int(comparison_df["n_districts_scored"].sum()),
    }
    return pd.concat([comparison_df, pd.DataFrame([summary])], ignore_index=True)


# ---------------------------------------------------------------------------
# Model selection
# ---------------------------------------------------------------------------

def select_official_model(metrics_df: pd.DataFrame) -> str:
    """Pick the single model type with the highest median PR-AUC across all
    validation folds (confirmed design: one model type overall, not a
    per-fold winner)."""
    aggregate = metrics_df[metrics_df["fold_id"] == "validation_aggregate"]
    if aggregate.empty:
        raise ValueError("metrics_df has no 'validation_aggregate' rows to select from.")
    winner = aggregate.loc[aggregate[PRIMARY_METRIC].idxmax(), "model"]
    logger.info(
        "Official model selected: %s (median PR-AUC=%.4f). Full comparison:\n%s",
        winner, aggregate.set_index("model")[PRIMARY_METRIC].loc[winner],
        aggregate[["model", PRIMARY_METRIC]].to_string(index=False),
    )
    return str(winner)


# ---------------------------------------------------------------------------
# Held-out final block (mirrors Decision 009)
# ---------------------------------------------------------------------------

def run_holdout_evaluation(
    df: pd.DataFrame, official_model: str, pre_holdout_keys: set, holdout_keys: set,
) -> tuple[pd.DataFrame, pd.DataFrame, object]:
    """Train all 3 models on the full pre-holdout window, score against the
    untouched final holdout block. Returns `(predictions_df, metrics_df,
    official_fitted_model)` - only the official model's fitted object is
    returned for saving (Decision: save per-fold/holdout model files only
    for the official model)."""
    train_mask = df["_key"].isin(pre_holdout_keys)
    val_mask = df["_key"].isin(holdout_keys)
    fold_df = attach_fold_anomalies(df, train_mask)

    train_rows_all = fold_df.loc[train_mask]
    val_rows_all = fold_df.loc[val_mask]
    trainable_train = train_rows_all.dropna(subset=[TARGET_COL])

    prediction_frames = []
    metric_rows = []
    official_fitted = None

    for model_name in MODEL_NAMES:
        proba, fitted = fit_and_predict(model_name, trainable_train, val_rows_all)
        prediction_frames.append(_build_prediction_rows(val_rows_all, proba, model_name, "holdout", "holdout"))
        scores = _score_predictions(val_rows_all[TARGET_COL], proba)
        metric_rows.append({"model": model_name, "fold_id": "holdout", "split": "holdout", **scores})
        if model_name == official_model:
            official_fitted = fitted

    logger.info("Holdout: trained on %d rows, scored %d holdout rows across %d models.", len(trainable_train), len(val_rows_all), len(MODEL_NAMES))

    return pd.concat(prediction_frames, ignore_index=True), pd.DataFrame(metric_rows), official_fitted


# ---------------------------------------------------------------------------
# Final production model + feature importance
# ---------------------------------------------------------------------------

def train_final_production_model(df: pd.DataFrame, official_model: str):
    """Train one final model of `official_model`'s type on ALL available
    defined-label rows (folds + holdout), for potential future live scoring.
    Not used for any reported metric - holdout has already served its
    reporting purpose in `run_holdout_evaluation`. The climate-anomaly norm
    is frozen over the ENTIRE available history (this is a forward-looking
    production artifact with no future data left to leak from)."""
    train_mask = pd.Series(True, index=df.index)
    fold_df = attach_fold_anomalies(df, train_mask)
    trainable = fold_df.dropna(subset=[TARGET_COL])

    # fit_and_predict requires a val_df; reuse a single trainable row as a
    # throwaway prediction target (its prediction is discarded here).
    _, model = fit_and_predict(official_model, trainable, trainable.iloc[[0]])
    # Refit is unnecessary above (fit_and_predict already fits on `trainable`
    # in full) - `model` is already the desired final production model.
    return model


def _model_file_path(base_dir: Path, stem: str, model_name: str) -> Path:
    suffix = ".json" if model_name == "xgboost" else ".joblib"
    return base_dir / f"{stem}{suffix}"


def _save_model(model, path: Path, model_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if model_name == "xgboost":
        model.save_model(str(path))
    else:
        joblib.dump(model, path)


def _load_model(path: Path, model_name: str):
    if model_name == "xgboost":
        model = xgb.XGBClassifier()
        model.load_model(str(path))
        return model
    return joblib.load(path)


def compute_feature_importance(model, model_name: str) -> pd.DataFrame:
    """Feature importance for the OFFICIAL model only (Decision: benchmark
    metrics kept for all 3 models, but importance is only meaningful for the
    model actually selected)."""
    if model_name == "xgboost":
        importance = model.get_booster().get_score(importance_type="gain")
        importance_df = pd.DataFrame({"feature": list(importance.keys()), "importance": list(importance.values())})
        missing = set(ALL_FEATURE_COLUMNS) - set(importance_df["feature"])
        if missing:
            importance_df = pd.concat(
                [importance_df, pd.DataFrame({"feature": sorted(missing), "importance": 0.0})], ignore_index=True
            )
    elif model_name == "random_forest":
        clf: RandomForestClassifier = model.named_steps["clf"]
        feature_names = model.named_steps["preprocess"].get_feature_names_out()
        importance_df = pd.DataFrame({"feature": feature_names, "importance": clf.feature_importances_})
    elif model_name == "logistic_regression":
        clf: LogisticRegression = model.named_steps["clf"]
        feature_names = model.named_steps["preprocess"].get_feature_names_out()
        importance_df = pd.DataFrame({"feature": feature_names, "importance": np.abs(clf.coef_[0])})
    else:
        raise ValueError(f"Unknown model_name: {model_name!r}")

    return importance_df.sort_values("importance", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_stage1_pipeline() -> pd.DataFrame:
    logger.info("Assembling labeled Stage 1 feature table...")
    df = assemble_labeled_feature_table()

    logger.info("Computing walk-forward fold boundaries (MIN_TRAIN_YEARS=%d)...", MIN_TRAIN_YEARS)
    fold_train_keys, fold_val_keys, pre_holdout_keys, holdout_keys = compute_fold_boundaries(df)

    logger.info("Running %d-fold benchmark across models: %s", N_FOLDS, MODEL_NAMES)
    predictions_df, metrics_df, fitted_models = run_benchmark(df, fold_train_keys, fold_val_keys)

    official_model = select_official_model(metrics_df)

    pooled_pr_auc_by_fold = (
        metrics_df[(metrics_df["model"] == "xgboost") & (metrics_df["fold_id"] != "validation_aggregate")]
        .set_index("fold_id")["pr_auc"].to_dict()
    )
    logger.info("Running pooled-vs-per-district comparison (XGBoost arbiter)...")
    comparison_df = run_pooled_vs_per_district_comparison(df, fold_train_keys, fold_val_keys, pooled_pr_auc_by_fold)

    logger.info("Running held-out final-block evaluation...")
    holdout_predictions_df, holdout_metrics_df, official_holdout_model = run_holdout_evaluation(
        df, official_model, pre_holdout_keys, holdout_keys
    )

    predictions_df = pd.concat([predictions_df, holdout_predictions_df], ignore_index=True)
    predictions_df["is_selected_model"] = predictions_df["model"] == official_model
    metrics_df = pd.concat([metrics_df, holdout_metrics_df], ignore_index=True)
    metrics_df["selected"] = metrics_df["model"] == official_model

    MODULE2_BASELINE_METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions_df.to_csv(MODULE2_BASELINE_PREDICTIONS_PATH, index=False)
    metrics_df.to_csv(MODULE2_BASELINE_METRICS_PATH, index=False)
    comparison_df.to_csv(MODULE2_POOLED_VS_DISTRICT_PATH, index=False)

    # Per-fold model files - official model type only, reusing the already-
    # fitted models from run_benchmark rather than refitting.
    MODULE2_BASELINE_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    for fold_num in range(1, N_FOLDS + 1):
        fold_model = fitted_models[official_model][fold_num]
        _save_model(fold_model, _model_file_path(MODULE2_BASELINE_MODELS_DIR, f"fold_{fold_num}", official_model), official_model)
    _save_model(official_holdout_model, _model_file_path(MODULE2_BASELINE_MODELS_DIR, "holdout", official_model), official_model)

    logger.info("Training final production model (%s) on all available labeled data...", official_model)
    final_model = train_final_production_model(df, official_model)
    _save_model(final_model, MODULE2_BASELINE_FINAL_MODEL_PATH.with_suffix(".json" if official_model == "xgboost" else ".joblib"), official_model)

    importance_df = compute_feature_importance(final_model, official_model)
    importance_df.to_csv(MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH, index=False)

    logger.info(
        "Stage 1 complete: official_model=%s | predictions -> %s | metrics -> %s | "
        "pooled-vs-district -> %s | feature importance -> %s",
        official_model, MODULE2_BASELINE_PREDICTIONS_PATH, MODULE2_BASELINE_METRICS_PATH,
        MODULE2_POOLED_VS_DISTRICT_PATH, MODULE2_BASELINE_FEATURE_IMPORTANCE_PATH,
    )
    return predictions_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_stage1_pipeline()
