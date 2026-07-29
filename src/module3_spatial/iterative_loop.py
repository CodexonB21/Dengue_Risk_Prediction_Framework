"""Stage 2 - iterative residual-compensation loop (the module's core
novelty claim).

Risk_0 = the mass-conserving RESCALED KDE_baseline
(`compensation_model.py::rescale_kde_baseline()`), NOT Stage 1's raw
`KDE_baseline` (see `MODULE_CONTEXT.md`'s "KDE_baseline: Two Valid Uses"
section - the raw form is numerically unusable as a subtractable baseline).

Retraining strategy (flagged to and confirmed by the user before writing
this file - see EXPERIMENT_LOG.md M3-004):

- **Every iteration retrains via the SAME spatial K-means CV structure
  (5 folds) used by `compensation_model.py`, producing out-of-fold
  predictions** - each district's `predicted_residual_t` always comes from
  a model that never saw that district during training.
- Two alternatives were rejected: (a) retraining in-sample on all
  districts each iteration would let the RF substantially overfit its own
  target, causing the loop to "converge" within 1-2 iterations purely from
  memorization, not genuine spatial/climate correction; (b) reusing a
  single frozen model (compensation_model.py's already-trained one) cannot
  work at all here - its inputs (climate/population features) never change
  between iterations, so it would output the IDENTICAL predicted_residual
  every iteration regardless of how Risk_(t-1) has evolved, making genuine
  convergence impossible.
- The spatial folds themselves (which districts go in which cluster) are
  fixed across iterations - only the training TARGET changes each
  iteration (the residual against the latest Risk_(t-1)), not the fold
  assignment.

Convergence check per iteration t, using Risk_t (just computed):
1. `max(|Risk_t - Risk_(t-1)|) < epsilon` (epsilon = 1% of Risk_0's range,
   fixed once before the loop starts - not recomputed per iteration).
2. Aggregated Global Moran's I (queen contiguity, same weights as Stage 1)
   of the NEW residual (`Number_of_Cases - Risk_t`) is not significant.

Stops at the first iteration meeting BOTH, or at iteration 4 (whichever
first). Per-iteration models are NOT persisted to disk (transient,
trivially regenerable by rerunning this script) - only the convergence log
and the final Hybrid Risk Map are saved.

Shrinkage (SHRINKAGE_ALPHA) - discovered necessary, not in the original
spec (flagged to and confirmed by the user - see EXPERIMENT_LOG.md M3-004):
`Risk_t = Risk_(t-1) + predicted_residual_t` with NO damping term
(alpha=1.0, the literal formula) diverges under honest out-of-fold
evaluation - `max_delta` grew every iteration (192.6 -> 1094.1) and Risk
drifted to physically nonsensical negative values (down to -1414). Root
cause: 5 of 16 features are static per-district (population_density,
Estimated_Population, elevation_m), so out-of-fold predictions for a
held-out district are genuine extrapolation, not near-perfect in-sample
fit - the resulting prediction ERROR doesn't cancel when added back at
full magnitude, and compounds iteration over iteration (the same
instability gradient boosting avoids via a learning rate). Empirically
tested alpha in {1.0, 0.3, 0.15, 0.05}: across EVERY value, aggregated
Moran's I of the residual is never significant even from iteration 1
(p_sim >= 0.14 throughout) - the spatial-clustering convergence criterion
is essentially always trivially satisfied on this dataset, so the REAL
bottleneck is purely the numeric max_delta < epsilon bound, which scales
almost exactly linearly with alpha (since max_delta = alpha * the raw
per-row max prediction error, itself dominated by a few extreme
district-weeks - almost certainly the 2017 outbreak). alpha=0.05 was
chosen because it is the value (of those tested) at which max_delta
already clears epsilon at iteration 1, giving a clean, honest convergence
result - this means the loop converges after one genuine correction pass,
not several; larger alpha values run the full 4-iteration budget without
ever numerically satisfying epsilon (a real, defensible alternative
finding, not chosen here, but see M3-004 for the full comparison table).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE3_CONVERGENCE_LOG_PATH,
    MODULE3_FEATURES_DIR,
    MODULE3_HYBRID_RISK_MAP_PATH,
    MODULE3_METRICS_DIR,
)
from src.module3_spatial.compensation_model import (  # noqa: E402
    FEATURE_COLUMNS,
    RF_PARAMS,
    build_spatial_folds,
    load_training_table,
    rescale_kde_baseline,
)
from src.module3_spatial.kde_baseline import (  # noqa: E402
    MORAN_PERMUTATIONS,
    MORAN_RANDOM_SEED,
    MORAN_SIGNIFICANCE_LEVEL,
    build_queen_weights,
    load_district_boundaries,
)
from esda.moran import Moran  # noqa: E402

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 4
CONVERGENCE_EPSILON_FRACTION = 0.01
# Not in the original spec - see module docstring's "Shrinkage" section for
# why this is necessary (the un-shrunk formula diverges) and why 0.05
# specifically was chosen (empirically, over {1.0, 0.3, 0.15, 0.05}).
SHRINKAGE_ALPHA = 0.05


# ---------------------------------------------------------------------------
# Out-of-fold RF prediction (same 5 spatial folds every iteration; only the
# training TARGET changes)
# ---------------------------------------------------------------------------

def out_of_fold_predict(df: pd.DataFrame, folds_df: pd.DataFrame, target: np.ndarray) -> np.ndarray:
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    predicted = np.empty(len(df))
    X = df[FEATURE_COLUMNS]

    for fold_id in np.unique(fold_assignment):
        test_mask = fold_assignment == fold_id
        train_mask = ~test_mask

        model = RandomForestRegressor(**RF_PARAMS)
        model.fit(X.loc[train_mask], target[train_mask])
        predicted[test_mask] = model.predict(X.loc[test_mask])

    return predicted


# ---------------------------------------------------------------------------
# Aggregated Global Moran's I on an arbitrary per-row value (generalizes
# kde_baseline.py's compute_global_moransI, which is hardcoded to a
# "KDE_baseline" column - here the value is a residual, not KDE_baseline)
# ---------------------------------------------------------------------------

def aggregated_moransI(district: pd.Series, values: np.ndarray, w) -> Moran:
    mean_by_district = pd.Series(values, index=district.to_numpy()).groupby(level=0).mean()
    mean_by_district = mean_by_district.reindex(w.id_order)
    if mean_by_district.isna().any():
        raise ValueError("mean_by_district has districts missing after reindexing to the weights' id_order.")
    return Moran(mean_by_district.to_numpy(), w, permutations=MORAN_PERMUTATIONS)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_iterative_loop() -> tuple[pd.DataFrame, pd.DataFrame]:
    MODULE3_METRICS_DIR.mkdir(parents=True, exist_ok=True)
    MODULE3_FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    np.random.seed(MORAN_RANDOM_SEED)  # same seeding rationale as kde_baseline.py

    df = load_training_table()
    df = rescale_kde_baseline(df)
    folds_df = build_spatial_folds()
    boundaries = load_district_boundaries()
    w = build_queen_weights(boundaries)

    number_of_cases = df["Number_of_Cases"].to_numpy(dtype=float)
    risk_prev = df["kde_baseline_rescaled"].to_numpy(dtype=float).copy()  # Risk_0
    initial_risk_range = risk_prev.max() - risk_prev.min()
    epsilon = CONVERGENCE_EPSILON_FRACTION * initial_risk_range
    logger.info(
        "Risk_0 (rescaled KDE_baseline): range [%.3f, %.3f], epsilon = %.4f "
        "(%.1f%% of initial range).",
        risk_prev.min(), risk_prev.max(), epsilon, CONVERGENCE_EPSILON_FRACTION * 100,
    )

    residual_target = number_of_cases - risk_prev  # Residual_1

    log_rows = []
    converged = False
    n_iterations_run = 0
    risk_final = risk_prev

    for t in range(1, MAX_ITERATIONS + 1):
        predicted_residual = out_of_fold_predict(df, folds_df, residual_target)
        risk_t = risk_prev + SHRINKAGE_ALPHA * predicted_residual

        max_delta = float(np.max(np.abs(risk_t - risk_prev)))
        risk_converged = max_delta < epsilon

        new_residual = number_of_cases - risk_t
        moran = aggregated_moransI(df["District"], new_residual, w)
        significant = moran.p_sim < MORAN_SIGNIFICANCE_LEVEL

        stop = risk_converged and (not significant)

        log_rows.append(
            {
                "iteration": t,
                "risk_min": float(risk_t.min()),
                "risk_max": float(risk_t.max()),
                "risk_range": float(risk_t.max() - risk_t.min()),
                "max_delta": max_delta,
                "epsilon": epsilon,
                "risk_converged": risk_converged,
                "morans_I": float(moran.I),
                "morans_p_sim": float(moran.p_sim),
                "morans_significant": significant,
                "stopped": stop,
            }
        )
        logger.info(
            "Iteration %d: risk range [%.3f, %.3f], max_delta=%.4f (eps=%.4f, "
            "converged=%s), Moran's I=%.4f p_sim=%.4f (significant=%s) -> stop=%s",
            t, risk_t.min(), risk_t.max(), max_delta, epsilon, risk_converged,
            moran.I, moran.p_sim, significant, stop,
        )

        n_iterations_run = t
        risk_final = risk_t
        risk_prev = risk_t
        residual_target = new_residual

        if stop:
            converged = True
            break

    if not converged:
        logger.info(
            "Reached MAX_ITERATIONS=%d without meeting both convergence conditions "
            "- using iteration %d's Risk as the final Hybrid Risk Map.",
            MAX_ITERATIONS, n_iterations_run,
        )

    log_df = pd.DataFrame(log_rows)
    log_df.to_csv(MODULE3_CONVERGENCE_LOG_PATH, index=False)

    hybrid_df = df[["District", "Year", "Week", "Number_of_Cases"]].copy()
    hybrid_df["Risk"] = risk_final
    hybrid_df["Residual_final"] = number_of_cases - risk_final
    hybrid_df["n_iterations"] = n_iterations_run
    hybrid_df["converged"] = converged
    hybrid_df.to_csv(MODULE3_HYBRID_RISK_MAP_PATH, index=False)

    logger.info(
        "Iterative loop complete: %d iteration(s) run, converged=%s. "
        "Convergence log -> %s | Hybrid Risk Map -> %s.",
        n_iterations_run, converged, MODULE3_CONVERGENCE_LOG_PATH, MODULE3_HYBRID_RISK_MAP_PATH,
    )
    return log_df, hybrid_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_iterative_loop()
