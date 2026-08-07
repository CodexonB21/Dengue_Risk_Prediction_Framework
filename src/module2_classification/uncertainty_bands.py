"""Module 2 Stage 2 companion output - Venn-Abers uncertainty bands.

Purely ADDITIVE diagnostic: wraps Stage 1's raw `predicted_probability`
(the same input the official isotonic Stage 2 calibrator already consumes)
with a valid probability INTERVAL instead of a single point estimate, using
the Inductive Venn-Abers Predictor (IVAP - Vovk & Petej, 2012). Does not
retrain, replace, or modify the official Stage 2 isotonic model, Stage 1,
or `risk_thresholds.py` - this is a new, separate companion CSV, not a
production pipeline stage.

Why Venn-Abers, not a generic split-conformal residual band: Venn-Abers is
built from the exact same primitive Stage 2 already uses officially
(`sklearn.isotonic.IsotonicRegression`) and is specifically designed to
interval-bound a BINARY classifier's probability output - the natural
"how much should I trust this calibrated probability" companion to an
isotonic calibrator, not an unrelated bolt-on technique.

Method (IVAP, per test point `s`):
    p0 = isotonic_fit(calibration_scores + [s], calibration_labels + [0])(s)
    p1 = isotonic_fit(calibration_scores + [s], calibration_labels + [1])(s)
    merged point estimate: p = p1 / (1 - p0 + p1)          (Vovk's formula)

`[p0, p1]` is the valid probability interval; `p1 - p0` (the "width") is the
uncertainty measure itself - no separate alpha/coverage parameter is needed,
unlike quantile-based conformal intervals.

No-leakage rule (mirrors `compensation_model.py`'s own Stage 2 fold design
exactly): fold *k* (2-13)'s calibration set is the POOLED out-of-sample
Stage 1 rows from folds `1..k-1` only. Fold 1 is excluded (no prior
out-of-sample data, same as Stage 2's own fold-1 no-op). Holdout's
calibration set is all 13 folds' pooled out-of-sample rows.
"""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import MODULE2_BASELINE_PREDICTIONS_PATH, MODULE2_PROCESSED_DIR  # noqa: E402
from src.module2_classification.baseline_classifier import (  # noqa: E402
    N_FOLDS as STAGE1_N_FOLDS,
)

logger = logging.getLogger(__name__)

TARGET_COL = "label"
SCORE_COL = "predicted_probability"
FIRST_TRAINABLE_FOLD = 2  # mirrors compensation_model.FIRST_TRAINABLE_STAGE2_FOLD

OUTPUT_PATH = MODULE2_PROCESSED_DIR / "stage2_uncertainty_bands.csv"


def _ivap_point(calib_scores: np.ndarray, calib_labels: np.ndarray, test_score: float) -> tuple[float, float]:
    """Single-point IVAP core: two augmented isotonic fits, evaluated at
    `test_score`. `calib_scores`/`calib_labels` are 1-D arrays already
    restricted to defined (non-NaN) labels."""
    aug_scores = np.append(calib_scores, test_score)

    iso0 = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso0.fit(aug_scores, np.append(calib_labels, 0.0))
    p0 = float(iso0.predict([test_score])[0])

    iso1 = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso1.fit(aug_scores, np.append(calib_labels, 1.0))
    p1 = float(iso1.predict([test_score])[0])

    return p0, p1


def ivap_batch(calib_scores: np.ndarray, calib_labels: np.ndarray, test_scores: np.ndarray) -> pd.DataFrame:
    """IVAP for every value in `test_scores` against one fixed calibration
    set. De-duplicates identical test scores (common with tree-model
    probabilities rounded to float precision) so each DISTINCT score is only
    fit twice, not once per row - a real cost saving at zero correctness
    cost, since IVAP's output depends only on the score value, not row
    identity.
    """
    unique_scores, inverse = np.unique(test_scores, return_inverse=True)
    p0_unique = np.empty(len(unique_scores))
    p1_unique = np.empty(len(unique_scores))
    for i, s in enumerate(unique_scores):
        p0_unique[i], p1_unique[i] = _ivap_point(calib_scores, calib_labels, float(s))
    p0 = p0_unique[inverse]
    p1 = p1_unique[inverse]
    merged = p1 / (1.0 - p0 + p1)
    return pd.DataFrame({"venn_abers_p0": p0, "venn_abers_p1": p1, "venn_abers_point": merged})


def compute_fold_aware_uncertainty_bands(predictions_path: Path | None = None) -> pd.DataFrame:
    """Reuses Stage 1's already-computed OOF probabilities (official model
    only) - same input, same fold structure Stage 2's isotonic calibrator
    already uses - to compute Venn-Abers bands for every validation fold
    (2-13) and holdout, no-leakage."""
    preds = pd.read_csv(predictions_path or MODULE2_BASELINE_PREDICTIONS_PATH, low_memory=False)
    preds = preds[preds["is_selected_model"]].copy()
    preds["fold_id_numeric"] = pd.to_numeric(preds["fold_id"], errors="coerce")

    val = preds[preds["split"] == "validation"].copy()
    holdout = preds[preds["split"] == "holdout"].copy()

    output_frames: list[pd.DataFrame] = []
    total_start = time.time()

    for fold_num in range(FIRST_TRAINABLE_FOLD, STAGE1_N_FOLDS + 1):
        calib = val[(val["fold_id_numeric"] < fold_num)].dropna(subset=[TARGET_COL])
        test = val[val["fold_id_numeric"] == fold_num].copy()
        if calib.empty or test.empty:
            continue

        t0 = time.time()
        bands = ivap_batch(
            calib[SCORE_COL].to_numpy(dtype=float), calib[TARGET_COL].to_numpy(dtype=float),
            test[SCORE_COL].to_numpy(dtype=float),
        )
        elapsed = time.time() - t0
        test = test.reset_index(drop=True)
        test = pd.concat([test, bands], axis=1)
        output_frames.append(test)
        logger.info(
            "Fold %d: calibration=%d rows, test=%d rows (%d unique scores), %.1fs.",
            fold_num, len(calib), len(test), test["predicted_probability"].nunique(), elapsed,
        )

    # Holdout: calibration = all 13 validation folds' pooled OOF rows.
    calib_all = val.dropna(subset=[TARGET_COL])
    if not holdout.empty:
        t0 = time.time()
        bands = ivap_batch(
            calib_all[SCORE_COL].to_numpy(dtype=float), calib_all[TARGET_COL].to_numpy(dtype=float),
            holdout[SCORE_COL].to_numpy(dtype=float),
        )
        elapsed = time.time() - t0
        holdout = holdout.reset_index(drop=True)
        holdout = pd.concat([holdout, bands], axis=1)
        output_frames.append(holdout)
        logger.info(
            "Holdout: calibration=%d rows, test=%d rows (%d unique scores), %.1fs.",
            len(calib_all), len(holdout), holdout["predicted_probability"].nunique(), elapsed,
        )

    logger.info("Total IVAP compute time: %.1fs.", time.time() - total_start)

    out = pd.concat(output_frames, ignore_index=True)
    out["venn_abers_width"] = out["venn_abers_p1"] - out["venn_abers_p0"]
    return out


def run_uncertainty_bands_pipeline() -> pd.DataFrame:
    logger.info("Computing fold-aware Venn-Abers uncertainty bands (folds %d-%d + holdout)...", FIRST_TRAINABLE_FOLD, STAGE1_N_FOLDS)
    out = compute_fold_aware_uncertainty_bands()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows -> %s", len(out), OUTPUT_PATH)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_uncertainty_bands_pipeline()
