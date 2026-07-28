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
