"""Module 2 - Live/production risk scoring for genuinely new incoming weeks.

Distinct from everything else in `module2_classification/`:
`baseline_classifier.py`/`compensation_model.py`/`risk_thresholds.py` all evaluate
the pipeline's model-selection/calibration/threshold CHOICES against data already
inside the dataset (walk-forward validation folds, the final 2-year holdout block)
- real ground truth to score against. This script instead asks "what does the
fully-trained pipeline predict for the MOST RECENT weeks in
`weekly_modeling_table.csv` right now" - the intended consumer is a dashboard,
which needs an up-to-date risk read without anyone manually rerunning the entire
walk-forward benchmark every time a new week's data arrives.

## Why this does NOT need Module 1's SARIMA-style recursive multi-step forecast

Every Stage 1 feature Module 2 uses is either a LAG of a PRIOR week's case
count/climate (`cases_lag_*`, `case_anomaly_lag_1/2`, `rainfall/temperature/
humidity_lag_*`) or that week's OWN already-reported climate (`current_rainfall/
temperature/humidity` - Module 2's deliberate divergence from Module 1's
Stage-1-purity rule, see `FEATURE_ENGINEERING_SPEC.md` Group M2-3) - NEVER that
week's own case count (excluded by Decision 019's leakage guard, since the case
count is exactly what the label is thresholded on). So unlike Module 1, no
feature here is EVER a recursively-fed prior prediction - every value, when
present, is a real observation. No `feature_completeness_pct`
degradation-WITH-HORIZON story applies the way it does in
`module1_forecasting/forecast_future.py`.

**Honest finding, verified empirically 2026-07-28 while building this script
(previously assumed otherwise): Module 2 has its OWN version of Module 1's Open
Question #16 climate-currency gap.** `weekly_modeling_table.csv`'s case counts and
climate columns do NOT actually share the same cutoff - case counts extend
through 2026 Wk25, but every climate column stops 4 weeks earlier, at 2026 Wk21,
for all 25 districts. Consequence: `current_rainfall/temperature/humidity`,
`rainfall/temperature/humidity_lag_1/2/3`, and `rainfall/temperature/
humidity_anomaly` are genuinely `NaN` (not a bug in this script) for the most
recent ~4 scored weeks - `feature_completeness_pct` drops from 100% to ~60% over
exactly that window (verified against `Ampara`: 100/100/100/100/82.9/77.1/68.6/60.0
across the last 8 weeks). The Random Forest final-production model copes
numerically via its pipeline's median imputer, but this is a real, flagged
degradation of the most recent weeks' inputs, not a modeling failure to hide.
Tracked as a new open item, mirroring Module 1's Open Question #16 (see
`MODULE_CONTEXT.md`).

## Method

1. Recompute Stage 1's fold-agnostic feature table
   (`feature_engineering.build_module2_feature_table`) FRESH from whatever
   `weekly_modeling_table.csv` currently contains - not the possibly-stale
   persisted `stage1_feature_table.csv` - so this script reflects newly
   preprocessed raw data without requiring a full Stage 1/2 retrain first.
   (Prerequisite, not automated here: `module2_preprocessing.py` must already
   have been rerun on the new raw data - this script only recomputes FEATURES,
   not the raw-to-weekly preprocessing layer.)
2. Attach fold-aware climate anomalies using the FULL available history as the
   training window (`baseline_classifier.attach_fold_anomalies` with an
   all-True mask) - the same maximal-data construction
   `baseline_classifier.train_final_production_model` already uses for its own
   final checkpoint, reused here for consistency rather than reinvented.
3. Score the most recent `n_recent_weeks` calendar weeks per district (default
   8) through the FROZEN Stage 1 final-production model
   (`models/module2/baseline_classifier/final_production_model.*`, whichever
   model type `baseline_classifier_metrics.csv` currently marks `selected`) ->
   `predicted_probability`.
4. Calibrate via the FROZEN Stage 2 final-production model
   (`models/module2/stage2_compensation/final_production_model.*`, whichever
   architecture `stage2_compensation_metrics.csv` currently marks `selected`)
   -> `calibrated_probability`. Model/architecture types are read from the
   metrics CSVs rather than hardcoded, so this script does not silently go
   stale if a future decision flips either choice again (as Decision 025 did).
5. Apply the SAME alert/high-confidence thresholds `risk_thresholds.py`
   already selected - re-derived deterministically from the persisted
   `risk_threshold_scan.csv` via `risk_thresholds.select_thresholds`, so no
   threshold logic or numeric value is duplicated/hardcoded here.

## Honest limitation (flagged, not hidden)

The Stage 1/2 final-production models are trained on ALL available data,
INCLUDING whatever portion of the scored weeks already fell inside the
walk-forward folds/holdout block - expected and desired for a live-scoring
checkpoint (more training data is strictly better once the goal is no longer
measuring honest out-of-sample skill), but it means this script's numbers for
already-evaluated weeks are NOT a repeat of `stage2_risk_tier_predictions.csv`'s
figures (a differently-trained checkpoint - trained on strictly less data) and
must never be quoted as additional validation/holdout evidence.
`EXPERIMENT_LOG.md`/`RESEARCH_DECISIONS.md`'s existing PR-AUC/BSS/recall numbers
remain the only honest skill estimates for this pipeline. Each output row is
flagged `already_scored_in_pipeline` so this distinction is visible, not silent.

Output: `data/processed/module2/live_risk_predictions.csv`.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_LIVE_RISK_PREDICTIONS_PATH,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
)
from src.module2_classification.scoring_utils import (  # noqa: E402
    apply_risk_tiers,
    build_scoring_feature_table,
    load_production_thresholds,
    load_stage1_model,
    load_stage2_model,
    official_stage1_model,
    official_stage2_architecture,
    score_feature_rows,
)

logger = logging.getLogger(__name__)

DEFAULT_N_RECENT_WEEKS = 8  # dashboard window - last 8 calendar weeks per district.

OUTPUT_COLUMNS = [
    "District", "Year", "Week", "Week_Start_Date", "Number_of_Cases", "is_imputed",
    "predicted_probability", "calibrated_probability", "alert_flag", "risk_tier",
    "feature_completeness_pct", "already_scored_in_pipeline",
]


def _already_scored_keys() -> set[tuple[str, int, int]]:
    """(District, Year, Week) keys already present in
    `stage2_risk_tier_predictions.csv` - i.e. already covered by an honest
    out-of-sample walk-forward fold or the holdout block. Weeks NOT in this
    set are genuinely new since the last full pipeline run."""
    if not MODULE2_RISK_TIER_PREDICTIONS_PATH.exists():
        return set()
    existing = pd.read_csv(MODULE2_RISK_TIER_PREDICTIONS_PATH, low_memory=False)
    return set(zip(existing["District"], existing["Year"].astype(int), existing["Week"].astype(int)))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def select_recent_weeks(df: pd.DataFrame, n_recent_weeks: int) -> pd.DataFrame:
    df = df.sort_values(["District", "Year", "Week"])
    return df.groupby("District", group_keys=False).tail(n_recent_weeks)


def run_live_scoring(n_recent_weeks: int = DEFAULT_N_RECENT_WEEKS) -> pd.DataFrame:
    logger.info("Recomputing Stage 1 feature table from the current weekly_modeling_table.csv...")
    feature_df = build_scoring_feature_table()

    logger.info("Selecting the most recent %d weeks per district to score...", n_recent_weeks)
    target_df = select_recent_weeks(feature_df, n_recent_weeks)

    stage1_model_name = official_stage1_model()
    stage2_architecture = official_stage2_architecture()
    logger.info(
        "Loading frozen final-production models: Stage 1=%s, Stage 2=%s...",
        stage1_model_name, stage2_architecture,
    )
    stage1_model = load_stage1_model(stage1_model_name)
    stage2_model = load_stage2_model(stage2_architecture)

    scored = score_feature_rows(target_df, stage1_model, stage1_model_name, stage2_model, stage2_architecture)
    scored = scored[
        ["District", "Year", "Week", "Week_Start_Date", "Number_of_Cases", "is_imputed",
         "predicted_probability", "calibrated_probability", "feature_completeness_pct"]
    ]

    alert_threshold, high_threshold = load_production_thresholds()
    logger.info("Applying persisted risk thresholds: alert=%.3f, high=%.3f", alert_threshold, high_threshold)
    scored = apply_risk_tiers(scored, alert_threshold, high_threshold)

    already_scored = _already_scored_keys()
    scored["already_scored_in_pipeline"] = [
        (d, int(y), int(w)) in already_scored
        for d, y, w in zip(scored["District"], scored["Year"], scored["Week"])
    ]

    result = scored[OUTPUT_COLUMNS].sort_values(["District", "Year", "Week"]).reset_index(drop=True)

    MODULE2_LIVE_RISK_PREDICTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(MODULE2_LIVE_RISK_PREDICTIONS_PATH, index=False)

    n_genuinely_new = int((~result["already_scored_in_pipeline"]).sum())
    latest = result.sort_values(["Year", "Week"]).groupby("District").tail(1)
    logger.info(
        "Live scoring complete: %d rows (%d districts x %d recent weeks, %d genuinely new since "
        "the last full pipeline run) -> %s. Latest-week risk_tier counts: %s",
        len(result), result["District"].nunique(), n_recent_weeks, n_genuinely_new,
        MODULE2_LIVE_RISK_PREDICTIONS_PATH, latest["risk_tier"].value_counts().to_dict(),
    )
    return result


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score the most recent weeks with Module 2's frozen final-production pipeline.")
    parser.add_argument(
        "--weeks", type=int, default=DEFAULT_N_RECENT_WEEKS,
        help=f"Number of most recent calendar weeks per district to score (default: {DEFAULT_N_RECENT_WEEKS}).",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_live_scoring(n_recent_weeks=args.weeks)
