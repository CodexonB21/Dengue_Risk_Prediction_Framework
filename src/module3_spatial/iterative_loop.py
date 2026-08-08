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
    STAGE2_FEATURE_COLUMNS_V2,
    build_spatial_folds,
    prepare_training_table,
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

# UPDATED 2026-08-05 (EXPERIMENT_LOG.md M3-008): was 4. STAGE2_FEATURE_COLUMNS'
# residual lag features are computed ONCE, fixed relative to Risk_0 (see
# compensation_model.py's STAGE2_FEATURE_COLUMNS comment - they represent a
# historical fact about a district's own case trajectory, not a moving
# target). Retraining on iteration t's evolving residual_target while those
# lag features still describe "residual relative to Risk_0" is theoretically
# incoherent past iteration 1, and empirically confirmed unstable: running
# the old MAX_ITERATIONS=4 anyway (verified before capping this, not
# assumed) produced an OSCILLATING, non-converging max_delta
# (578.10 -> 240.05 -> 166.66 -> 189.57, all >> epsilon=12.98) that
# progressively degraded a result independently shown (stage2_experiments.py's
# single-pass ablation) to be excellent at iteration 1 alone
# (MAE=10.08 vs Stage 1 alone's 20.54, ~51% improvement). Capped at 1 -
# not because the strict numeric convergence criterion is met at iteration 1
# (it is NOT: max_delta=578.10 >> epsilon), but because further iteration is
# not well-founded for this feature set. The convergence check below is
# still run and logged every time (diagnostic value - confirms Moran's I
# stays non-significant, i.e. Stage 1 still captures spatial autocorrelation
# on its own, exactly as M3-004 found), it just never gets the chance to
# trigger a SECOND iteration.
MAX_ITERATIONS = 1
CONVERGENCE_EPSILON_FRACTION = 0.01
# UPDATED 2026-08-05 (EXPERIMENT_LOG.md M3-008): alpha=0.05 was chosen
# (M3-004) because the un-shrunk formula (alpha=1.0) diverged - root cause
# was that several features (population_density, Estimated_Population,
# elevation_m) are static per-district, so out-of-fold prediction for a
# held-out district was genuine extrapolation with real, non-cancelling
# error. Adding own-district residual lag features (STAGE2_FEATURE_COLUMNS,
# M3-008) gives the RF a genuine dynamic anchor even for a held-out
# district, which resolves that divergence: alpha=1.0 (no shrinkage) is now
# the best-performing choice, cutting out-of-fold MAE from ~34.7 to ~10.1
# and beating Stage 1 alone by ~51% (verified in stage2_experiments.py's
# ablation before promotion - not assumed).
SHRINKAGE_ALPHA = 1.0


# ---------------------------------------------------------------------------
# Out-of-fold RF prediction (same 5 spatial folds every iteration; only the
# training TARGET changes)
# ---------------------------------------------------------------------------

def out_of_fold_predict(
    df: pd.DataFrame, folds_df: pd.DataFrame, target: np.ndarray,
    feature_cols: list[str] = FEATURE_COLUMNS,
) -> np.ndarray:
    """`feature_cols` defaults to the ORIGINAL 16-column `FEATURE_COLUMNS`
    (not `STAGE2_FEATURE_COLUMNS_V2`) so that `alpha_sweep.py` (M3-006),
    which imports this function directly relying on this default, stays
    byte-for-byte reproducible if ever rerun. `stacked_persistence_
    experiment.py` (M3-011) explicitly overrides this default with the
    frozen `STAGE2_FEATURE_COLUMNS` (20-column, still unchanged) every call,
    so it is unaffected either way. `run_iterative_loop()` below explicitly
    passes `feature_cols=STAGE2_FEATURE_COLUMNS_V2` for the OFFICIAL,
    post-M3-015 model.
    """
    fold_assignment = df[["District"]].merge(folds_df, on="District", how="left")["spatial_fold"]
    if fold_assignment.isna().any():
        raise ValueError("Some districts missing spatial_fold assignment.")
    fold_assignment = fold_assignment.to_numpy()

    predicted = np.empty(len(df))
    X = df[feature_cols]

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

    df = prepare_training_table()
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

    # UPDATED 2026-08-08 (EXPERIMENT_LOG.md M3-015): the RF's target is now
    # the RELATIVE residual (Residual_1 / (Risk_0 + 1)), not the absolute
    # one - fixes a directly-diagnosed heteroscedasticity in the absolute
    # residual. Reconstruction back to Risk is exact, not approximate:
    # Risk_t = Risk_(t-1) + alpha * predicted_relative_residual * (Risk_(t-1) + 1).
    relative_residual_target = (number_of_cases - risk_prev) / (risk_prev + 1)  # relative Residual_1

    log_rows = []
    converged = False
    n_iterations_run = 0
    risk_final = risk_prev

    for t in range(1, MAX_ITERATIONS + 1):
        predicted_relative_residual = out_of_fold_predict(
            df, folds_df, relative_residual_target, feature_cols=STAGE2_FEATURE_COLUMNS_V2,
        )
        risk_t = risk_prev + SHRINKAGE_ALPHA * predicted_relative_residual * (risk_prev + 1)

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
        relative_residual_target = new_residual / (risk_t + 1)

        if stop:
            converged = True
            break

    if not converged:
        logger.info(
            "Stopped at MAX_ITERATIONS=%d (iteration %d's Risk is the final Hybrid Risk Map) "
            "WITHOUT meeting the strict numeric convergence criterion - this is a deliberate "
            "design cap for STAGE2_FEATURE_COLUMNS (see MAX_ITERATIONS comment above), not a "
            "failed search for convergence: iteration %d's own fit to actual case counts has "
            "already been independently verified as the excellent, official result "
            "(see EXPERIMENT_LOG.md M3-008).",
            MAX_ITERATIONS, n_iterations_run, n_iterations_run,
        )

    log_df = pd.DataFrame(log_rows)
    log_df.to_csv(MODULE3_CONVERGENCE_LOG_PATH, index=False)

    # UPDATED 2026-08-05 (M3-008): clipped at 0 (case counts cannot be
    # negative), superseding the earlier "not clipped" decision (M3-004),
    # which was made when the largest overshoot was a "minor" -2.32.
    # alpha=1.0's full, unshrunk correction (vs. the old alpha=0.05) widens
    # this to 1,211 rows (4.82%, median still small at -0.94, but a real
    # tail down to -112.87) - large enough to be a physically nonsensical
    # "negative case count" rather than a rounding-scale overshoot. Verified
    # before clipping (not assumed): clipping is a strict, if small,
    # improvement on every metric (MAE 10.08 -> 9.96, corr 0.9551 -> 0.9554,
    # RMSE 25.12 -> 25.06), not a trade-off.
    risk_clipped = np.clip(risk_final, 0.0, None)
    n_clipped = int((risk_final < 0).sum())

    hybrid_df = df[["District", "Year", "Week", "Number_of_Cases"]].copy()
    hybrid_df["Risk"] = risk_clipped
    hybrid_df["Residual_final"] = number_of_cases - risk_clipped
    hybrid_df["n_iterations"] = n_iterations_run
    hybrid_df["converged"] = converged
    hybrid_df.to_csv(MODULE3_HYBRID_RISK_MAP_PATH, index=False)
    logger.info(
        "Clipped %d rows (%.2f%%) with negative unclipped Risk (min %.2f) to 0.",
        n_clipped, 100 * n_clipped / len(df), float(risk_final.min()),
    )

    logger.info(
        "Iterative loop complete: %d iteration(s) run, converged=%s. "
        "Convergence log -> %s | Hybrid Risk Map -> %s.",
        n_iterations_run, converged, MODULE3_CONVERGENCE_LOG_PATH, MODULE3_HYBRID_RISK_MAP_PATH,
    )
    return log_df, hybrid_df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_iterative_loop()
