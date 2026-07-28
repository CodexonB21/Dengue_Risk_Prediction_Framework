"""Module 2 Stage 1 classification evaluation metrics.

Mirrors `src/module1_forecasting/evaluate.py`'s style: small, pure functions
that all accept an optional boolean `mask` (True = keep the row), so callers
can exclude rows with an undefined (`NaN`) label - Decision 019's rule that
undefined labels "must be excluded from training/scoring, never defaulted to
0" - from any metric computation, the same `_apply_mask` pattern Module 1
uses for `is_imputed` exclusion.

Two families of metrics:
- Threshold-dependent (`accuracy`, `precision`, `recall`, `specificity`,
  `f1`, `confusion_counts`): operate on a binarized prediction
  (`y_pred_label`). Per the confirmed Stage 1 design, these are only ever
  computed at a FIXED 0.5 cutoff, reported as an untuned diagnostic - not a
  decision policy. Real threshold/calibration tuning is deferred to Stage 2
  (`compensation_model.py`).
- Threshold-free (`roc_auc`, `pr_auc`, `brier_score`): operate directly on
  predicted probabilities (`y_prob`). `pr_auc` (average precision) is the
  PRIMARY Stage 1 selection metric (confirmed design decision) given the
  ~18.4% pooled outbreak rate - PR-AUC is far more informative than ROC-AUC
  under moderate class imbalance.
"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


def _apply_mask(*arrays: np.ndarray, mask: np.ndarray | None) -> list[np.ndarray]:
    """Coerce inputs to float ndarrays and apply a boolean keep-mask.

    Rows that are NaN in any of `arrays` are also dropped - an undefined
    label or a missing prediction must never silently count as a scored
    observation.
    """
    coerced = [np.asarray(a, dtype=float) for a in arrays]
    if mask is None:
        keep = np.ones_like(coerced[0], dtype=bool)
    else:
        keep = np.asarray(mask, dtype=bool)

    for arr in coerced:
        keep = keep & ~np.isnan(arr)

    return [arr[keep] for arr in coerced]


def confusion_counts(
    y_true, y_pred_label, mask: np.ndarray | None = None
) -> tuple[int, int, int, int]:
    """Return `(tn, fp, fn, tp)` at whatever binarization the caller already
    applied to `y_pred_label` (Stage 1 always uses a fixed 0.5 cutoff)."""
    yt, yp = _apply_mask(y_true, y_pred_label, mask=mask)
    if yt.size == 0:
        return 0, 0, 0, 0

    tp = int(np.sum((yt == 1) & (yp == 1)))
    tn = int(np.sum((yt == 0) & (yp == 0)))
    fp = int(np.sum((yt == 0) & (yp == 1)))
    fn = int(np.sum((yt == 1) & (yp == 0)))
    return tn, fp, fn, tp


def accuracy(y_true, y_pred_label, mask: np.ndarray | None = None) -> float:
    yt, yp = _apply_mask(y_true, y_pred_label, mask=mask)
    if yt.size == 0:
        return float("nan")
    return float(np.mean(yt == yp))


def precision(y_true, y_pred_label, mask: np.ndarray | None = None) -> float:
    tn, fp, fn, tp = confusion_counts(y_true, y_pred_label, mask=mask)
    denom = tp + fp
    return float(tp / denom) if denom > 0 else float("nan")


def recall(y_true, y_pred_label, mask: np.ndarray | None = None) -> float:
    """Recall / sensitivity: of the actual outbreak weeks, how many were flagged."""
    tn, fp, fn, tp = confusion_counts(y_true, y_pred_label, mask=mask)
    denom = tp + fn
    return float(tp / denom) if denom > 0 else float("nan")


def specificity(y_true, y_pred_label, mask: np.ndarray | None = None) -> float:
    """Of the actual non-outbreak weeks, how many were correctly left unflagged."""
    tn, fp, fn, tp = confusion_counts(y_true, y_pred_label, mask=mask)
    denom = tn + fp
    return float(tn / denom) if denom > 0 else float("nan")


def f1(y_true, y_pred_label, mask: np.ndarray | None = None) -> float:
    p = precision(y_true, y_pred_label, mask=mask)
    r = recall(y_true, y_pred_label, mask=mask)
    if np.isnan(p) or np.isnan(r) or (p + r) == 0:
        return float("nan")
    return float(2 * p * r / (p + r))


def fbeta_score(y_true, y_pred_label, beta: float, mask: np.ndarray | None = None) -> float:
    """F-beta score - generalizes `f1` (`beta=1`) to weight recall `beta`
    times as heavily as precision. `beta > 1` (e.g. F2) favors recall, the
    natural choice for an outbreak EARLY-WARNING alert threshold where
    missing a real outbreak is costlier than a false alarm; `beta < 1` (e.g.
    F0.5) favors precision, the natural choice for a "high confidence" risk
    tier (Decision 024) where a false positive at the top tier is more
    costly to credibility than at the alert tier.

        F_beta = (1 + beta^2) * P * R / (beta^2 * P + R)
    """
    p = precision(y_true, y_pred_label, mask=mask)
    r = recall(y_true, y_pred_label, mask=mask)
    if np.isnan(p) or np.isnan(r):
        return float("nan")
    denom = (beta**2 * p) + r
    if denom == 0:
        return float("nan")
    return float((1 + beta**2) * p * r / denom)


def threshold_scan(
    y_true, y_prob, thresholds: np.ndarray | None = None, mask: np.ndarray | None = None,
) -> "pd.DataFrame":
    """Score `y_prob` at every cutoff in `thresholds` (default: 99 cutoffs
    from 0.01 to 0.99), returning `precision`/`recall`/`f1`/`f2`/`f0_5`/
    `accuracy` per threshold.

    Used by `risk_thresholds.py` (Decision 024) to pick a real decision
    threshold for the calibrated probability Stage 2 now produces, instead
    of the fixed, explicitly-untuned 0.5 cutoff used as a diagnostic
    throughout Stage 1/2's own benchmarking (`SECONDARY_THRESHOLD` in
    `baseline_classifier.py`/`compensation_model.py`).
    """
    import pandas as pd

    if thresholds is None:
        thresholds = np.linspace(0.01, 0.99, 99)

    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0:
        return pd.DataFrame(columns=["threshold", "precision", "recall", "f1", "f2", "f0_5", "accuracy"])

    rows = []
    for t in thresholds:
        pred_label = (yp >= t).astype(float)
        rows.append(
            {
                "threshold": float(t),
                "precision": precision(yt, pred_label),
                "recall": recall(yt, pred_label),
                "f1": f1(yt, pred_label),
                "f2": fbeta_score(yt, pred_label, beta=2.0),
                "f0_5": fbeta_score(yt, pred_label, beta=0.5),
                "accuracy": accuracy(yt, pred_label),
            }
        )
    return pd.DataFrame(rows)


def roc_auc(y_true, y_prob, mask: np.ndarray | None = None) -> float:
    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0 or len(np.unique(yt)) < 2:
        # roc_auc_score is undefined with a single class present (can happen
        # in a thin early fold) - report NaN rather than raising.
        return float("nan")
    return float(roc_auc_score(yt, yp))


def pr_auc(y_true, y_prob, mask: np.ndarray | None = None) -> float:
    """Average precision (area under the precision-recall curve) - the
    PRIMARY Stage 1 model-selection metric (confirmed design decision)."""
    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0 or len(np.unique(yt)) < 2:
        return float("nan")
    return float(average_precision_score(yt, yp))


def brier_score(y_true, y_prob, mask: np.ndarray | None = None) -> float:
    """Brier score (mean squared error of the predicted probability against
    the binary outcome) - a simple scalar calibration proxy. Full
    calibration curves/plots are not built here (out of scope for the
    baseline benchmark); calibration recalibration itself is planned for
    Stage 2 (`compensation_model.py`, per MODULE_CONTEXT.md Open Question #5)."""
    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0:
        return float("nan")
    return float(brier_score_loss(yt, yp))


def prevalence(y_true, mask: np.ndarray | None = None) -> float:
    """Share of positive (outbreak) rows among scored rows - reported
    alongside pr_auc so a raw PR-AUC value is never read without the base
    rate it should be compared against (raw PR-AUC is not comparable across
    folds/districts with different prevalence)."""
    (yt,) = _apply_mask(y_true, mask=mask)
    if yt.size == 0:
        return float("nan")
    return float(np.mean(yt))


def brier_skill_score(y_true, y_prob, mask: np.ndarray | None = None) -> float:
    """Brier Skill Score relative to a climatology forecast - "always predict
    this fold's own base rate (prevalence)". `reference_brier = prevalence *
    (1 - prevalence)` is exactly that climatology forecast's Brier score (the
    variance of a Bernoulli(prevalence) variable). Positive means the model's
    probabilities are better calibrated than climatology; negative means
    worse - despite potentially strong discrimination (PR-AUC/ROC-AUC), since
    those measure ranking, not calibration.

    Promoted here (Decision 022) from the one-off
    `scripts/stage1_calibration_diagnostic.py` into a first-class, reusable
    metric - this is Stage 2's PRIMARY architecture-selection metric, the
    same role `pr_auc` played for Stage 1 (Decision 021).
    """
    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0:
        return float("nan")
    p = float(np.mean(yt))
    reference_brier = p * (1 - p)
    if reference_brier == 0:
        # Degenerate fold (all-one-class after masking) - climatology itself
        # would be a perfect (zero-Brier) forecast, so skill is undefined
        # rather than a spurious +-inf.
        return float("nan")
    model_brier = float(np.mean((yp - yt) ** 2))
    return float(1 - model_brier / reference_brier)


def reliability_curve(
    y_true, y_prob, n_bins: int = 10, mask: np.ndarray | None = None
) -> "pd.DataFrame":
    """Bin predicted probabilities into `n_bins` equal-width bins over
    `[0, 1]` and return, per non-empty bin, the mean predicted probability
    vs. the mean observed outcome (the two curves a reliability diagram
    plots against each other) plus the bin's observation count.

    A perfectly calibrated model has `mean_observed == mean_predicted` in
    every bin. Used by `compensation_model.plot_reliability_diagrams` for
    Stage 1-raw vs. Stage 2-calibrated comparison plots (Decision 022) - the
    one `MODULE_CONTEXT.md` Evaluation Metrics item ("calibration plots")
    never implemented before Stage 2.
    """
    import pandas as pd  # local import - keeps this module's other pure
    # functions dependency-light (numpy/sklearn only) for anything that
    # doesn't need a DataFrame return type.

    yt, yp = _apply_mask(y_true, y_prob, mask=mask)
    if yt.size == 0:
        return pd.DataFrame(columns=["bin_lower", "bin_upper", "mean_predicted", "mean_observed", "n"])

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    # Rightmost edge inclusive, matching np.digitize's default half-open
    # bins [edges[i], edges[i+1]) except the last bin which includes 1.0.
    bin_idx = np.clip(np.digitize(yp, edges[1:-1], right=False), 0, n_bins - 1)

    rows = []
    for b in range(n_bins):
        in_bin = bin_idx == b
        n = int(np.sum(in_bin))
        if n == 0:
            continue
        rows.append(
            {
                "bin_lower": float(edges[b]),
                "bin_upper": float(edges[b + 1]),
                "mean_predicted": float(np.mean(yp[in_bin])),
                "mean_observed": float(np.mean(yt[in_bin])),
                "n": n,
            }
        )
    return pd.DataFrame(rows)
