"""Module 2 Stage 1 feature engineering.

Reads `data/processed/module2/weekly_modeling_table.csv` and builds Stage 1
(baseline classifier) features per
`research_context/FEATURE_ENGINEERING_SPEC.md`'s Module 2 section (finalized
2026-07-28 after a dedicated feature-engineering review), writing the
fold-agnostic portion to `data/features/module2/`.

## Feature groups implemented here

- **M2-1 Case-trend** (fold-agnostic): case lags, rolling mean/std, rate of
  change, and `momentum_vs_rolling_mean` (added after review - `rate_of_change`
  alone is noisy under this project's zero-inflation). `is_imputed` rows are
  masked to NaN before ANY of these are derived (revised 2026-07-28 - the
  first implementation pass only masked `case_anomaly_lag_1/2`, letting a
  fabricated seasonal-naive case count silently flow into a neighboring
  week's lag/rolling feature; same principle as M2-5 below, applied
  consistently now).
- **M2-2 Lagged climate** (fold-agnostic, NEW): `rainfall_lag_2..8`,
  `temperature_lag_1..4`, `humidity_lag_1..4` - same windows as Module 1
  Feature Group 2, added after review to capture dengue's ~2-8-week
  transmission delay (mosquito breeding cycle + extrinsic incubation period),
  which the anomaly-only feature set originally planned did not capture.
- **M2-3 Current-week climate** (fold-agnostic) + **climate anomaly**
  (fold-aware, reused unchanged from `src.module1_forecasting.feature_engineering
  .compute_fold_climate_anomalies` - already module-agnostic).
- **M2-4 Seasonal/contextual** (fold-agnostic): `sin_week`/`cos_week`,
  monsoon indicators.
- **M2-5 Case-level seasonal anomaly lags** (fold-agnostic - see the
  "leakage-guard architecture" note below): `case_anomaly_lag_1/2`.

Explicitly out of scope here (added once Stage 1 exists, same sequencing
Module 1 used for `sarima_prediction`/`residual_lag_1/2`):
- The outbreak label itself (`src/module2_classification/labels.py`).
- Baseline-probability and probability-error-lag features (Stage 1/2 model
  outputs).
- A "weeks currently above threshold" streak feature - deferred until Module
  2 Open Question #8 (single-week vs. consecutive-week trigger) is resolved.

## Leakage-guard architecture note (important, do not conflate the two)

Group M2-3's climate anomaly and Group M2-5's case-anomaly lag are BOTH
leakage-safe, but via genuinely different constructions:

- Climate anomaly: a single `(District, Week)` mean **frozen at each
  walk-forward fold's training-window cutoff** - MUST be recomputed per fold
  (`compute_fold_climate_anomalies`), never written to this global file.
- Case-anomaly lag: `historical_mean`/`historical_sd` computed using only
  years strictly before that row's own calendar year (reused directly from
  `labels.compute_historical_stats_harmonic`, the same construction the
  label itself uses as of Decision 025 - a per-district harmonic-regression
  seasonal curve, refit expanding per year; superseded the original exact-
  per-week `compute_historical_stats` estimator). Because any walk-forward
  fold's validation year `V` only ever needs years `< V` - exactly what the
  expanding-per-year construction already provides for any row whose year
  equals `V` - this one IS safe to compute once, globally, unlike the
  climate anomaly above.

`weather_code` is excluded from the output feature table - Module 2's own
independent choice (same reasoning as Module 1's Decision 008), not an
inherited default. It remains present upstream in
`data/processed/module2/weekly_modeling_table.csv`.

## Leakage/metadata exclusion (critical - read before using this table for modeling)

`Number_of_Cases` and `cases_per_100k` are KEPT in this table's output (for
merging in the label / for reporting) but must NEVER be used as model input
features - `Number_of_Cases` is exactly what the label is thresholded on, and
`cases_per_100k` is a population-rescaled copy of the same quantity for the
SAME week. Raw `Year` is also excluded from the feature list (monotonic with
the walk-forward split itself). Stage 1/2 modeling code must build its
feature matrix from the explicit `FOLD_AGNOSTIC_FEATURE_COLUMNS` list below,
never from "all columns minus a manually-remembered exclude list" - the more
error-prone pattern that let this exact leakage risk go unnoticed during the
first implementation pass of this module.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE2_FEATURES_DIR,
    MODULE2_STAGE1_FEATURE_TABLE_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    MONSOON_WEEKS_NE,
    MONSOON_WEEKS_SW,
)
from src.module1_forecasting.feature_engineering import (  # noqa: E402
    compute_fold_climate_anomalies,
)
from src.module2_classification.labels import compute_historical_stats_harmonic  # noqa: E402
from src.preprocessing.reporting_anomalies import mask_untrusted_cases  # noqa: E402

logger = logging.getLogger(__name__)

# Same rainfall-source choice as Module 1 (Decision 008's reasoning applies
# equally here: precipitation_sum includes convective showers, more complete
# for Sri Lanka's monsoon pattern) - re-affirmed independently for Module 2.
RAINFALL_COLUMN = "precipitation_sum (mm)"
TEMPERATURE_COLUMN = "temperature_2m_mean (\u00b0C)"
HUMIDITY_COLUMN = "relative_humidity_2m_mean (%)"
WEATHER_CODE_COLUMN = "weather_code (wmo code)"

CASE_LAGS = (1, 2, 3, 4)
RAINFALL_LAGS = range(2, 9)     # 2-8, same window as Module 1
TEMPERATURE_LAGS = range(1, 5)  # 1-4
HUMIDITY_LAGS = range(1, 5)     # 1-4
ROLLING_WINDOW = 4
WEEKS_PER_YEAR = 52

# Module-2-local monsoon override: `module2_preprocessing.py` (revised
# 2026-07-28) no longer merges epi-week 53 into week 52, so Week can be 53
# here - unlike Module 1, where MONSOON_WEEKS_NE (src/config.py) is defined
# over an already-merged 52-week structure and 53 never appears. Week 53
# falls in late December, squarely inside the NE monsoon window, so it must
# be added to a Module 2-specific copy rather than mutating the shared
# constant Module 1 depends on.
MODULE2_MONSOON_WEEKS_NE = list(MONSOON_WEEKS_NE) + [53]

# --- Explicit, enumerated feature-column groups (leakage/metadata guard) ---
CASE_TREND_FEATURES = [f"cases_lag_{lag}" for lag in CASE_LAGS] + [
    "rolling_mean_cases_4w",
    "rolling_std_cases_4w",
    "rate_of_change",
    "momentum_vs_rolling_mean",
]
CLIMATE_LAG_FEATURES = (
    [f"rainfall_lag_{lag}" for lag in RAINFALL_LAGS]
    + [f"temperature_lag_{lag}" for lag in TEMPERATURE_LAGS]
    + [f"humidity_lag_{lag}" for lag in HUMIDITY_LAGS]
)
CURRENT_WEEK_CLIMATE_FEATURES = ["current_rainfall", "current_temperature", "current_humidity"]
SEASONAL_FEATURES = ["sin_week", "cos_week", "monsoon_indicator_SW", "monsoon_indicator_NE"]
CASE_ANOMALY_LAG_FEATURES = ["case_anomaly_lag_1", "case_anomaly_lag_2"]

# Written to the global feature file, safe to use regardless of walk-forward
# fold (see module docstring's "leakage-guard architecture note").
FOLD_AGNOSTIC_FEATURE_COLUMNS = (
    CASE_TREND_FEATURES
    + CLIMATE_LAG_FEATURES
    + CURRENT_WEEK_CLIMATE_FEATURES
    + SEASONAL_FEATURES
    + CASE_ANOMALY_LAG_FEATURES
)

# M2-008 symmetric ablation (Module 1–style split): Stage 1 omits climate so Stage 2
# can learn climate-driven correction on top of a case-history baseline.
STAGE1_CLIMATE_FREE_FEATURE_COLUMNS = (
    CASE_TREND_FEATURES + SEASONAL_FEATURES + CASE_ANOMALY_LAG_FEATURES
)

# NOT written to the global file - must be recomputed per walk-forward fold.
FOLD_AWARE_FEATURE_COLUMNS = ["rainfall_anomaly", "temperature_anomaly", "humidity_anomaly"]

STAGE2_CLIMATE_COMPENSATION_FEATURE_COLUMNS = (
    CLIMATE_LAG_FEATURES + CURRENT_WEEK_CLIMATE_FEATURES + FOLD_AWARE_FEATURE_COLUMNS
)

# Categorical, handled separately by Stage 1 modeling code (Module 1 Feature
# Group 5b equivalent) - not part of the plain numeric feature lists above.
CATEGORICAL_FEATURE_COLUMNS = ["District"]

# Present in the feature table for merging/reporting, but MUST NEVER be used
# as a model input feature - see module docstring's leakage/metadata section.
NON_FEATURE_COLUMNS = [
    "Number_of_Cases",
    "cases_per_100k",
    "Year",
    "is_imputed",
    "is_reporting_anomaly",
    "Estimated_Population",
    "Source_Type",
    "Week_Start_Date",
    "Week_End_Date",
]


# ---------------------------------------------------------------------------
# Fold-agnostic features
# ---------------------------------------------------------------------------

def build_fold_agnostic_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build the Stage 1 features that are pure shifts/windows of
    already-observed values and are therefore safe to compute once, globally
    (Feature Groups M2-1, M2-2, M2-3's current-week part, M2-4).
    """
    df = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    out = df.copy()
    grouped = df.groupby("District")

    # --- M2-1: case-trend features ---
    # Mask is_imputed and reporting-anomaly rows to NaN BEFORE deriving any
    # case-lag/rolling feature from them (Decision 026 extends Decision 020).
    clean_cases = mask_untrusted_cases(df)
    clean_grouped = clean_cases.groupby(df["District"])

    for lag in CASE_LAGS:
        out[f"cases_lag_{lag}"] = clean_grouped.shift(lag)

    # Rolling stats use only the ROLLING_WINDOW weeks strictly BEFORE the
    # current row (shift(1) before rolling) - the current week's own case
    # count is what the label is derived from, so it must never leak into
    # its own feature row.
    out["rolling_mean_cases_4w"] = clean_grouped.transform(
        lambda s: s.shift(1).rolling(ROLLING_WINDOW).mean()
    )
    out["rolling_std_cases_4w"] = clean_grouped.transform(
        lambda s: s.shift(1).rolling(ROLLING_WINDOW).std()
    )

    out["rate_of_change"] = out["cases_lag_1"] - out["cases_lag_2"]
    # Added after feature-engineering review: recent value vs. short-term
    # baseline, less sensitive to a single noisy week-to-week jump than
    # rate_of_change alone under this project's zero-inflation.
    out["momentum_vs_rolling_mean"] = out["cases_lag_1"] - out["rolling_mean_cases_4w"]

    # --- M2-2: lagged climate features (new, added after review) ---
    for lag in RAINFALL_LAGS:
        out[f"rainfall_lag_{lag}"] = grouped[RAINFALL_COLUMN].shift(lag)
    for lag in TEMPERATURE_LAGS:
        out[f"temperature_lag_{lag}"] = grouped[TEMPERATURE_COLUMN].shift(lag)
    for lag in HUMIDITY_LAGS:
        out[f"humidity_lag_{lag}"] = grouped[HUMIDITY_COLUMN].shift(lag)

    # --- M2-3: current-week raw climate (deliberate divergence from Module
    # 1's Stage-1-purity rule - see FEATURE_ENGINEERING_SPEC.md Group M2-3) ---
    out["current_rainfall"] = out[RAINFALL_COLUMN]
    out["current_temperature"] = out[TEMPERATURE_COLUMN]
    out["current_humidity"] = out[HUMIDITY_COLUMN]

    # --- M2-4: seasonal / contextual indicators ---
    # Week can be 53 here (module2_preprocessing.py keeps it as its own week,
    # revised 2026-07-28 - see that module's docstring). sin/cos need no
    # special-casing: sin(2*pi*53/52) = sin(2*pi + 2*pi/52) = sin(2*pi*1/52)
    # by periodicity, i.e. week 53 naturally lands right next to week 1's
    # value - a reasonable approximation given week 53 IS chronologically
    # adjacent to the next year's week 1. Monsoon indicator uses a Module
    # 2-local override (MODULE2_MONSOON_WEEKS_NE) to correctly classify
    # week 53 (late December, NE monsoon) - see that constant's definition.
    out["sin_week"] = np.sin(2 * np.pi * out["Week"] / WEEKS_PER_YEAR)
    out["cos_week"] = np.cos(2 * np.pi * out["Week"] / WEEKS_PER_YEAR)
    out["monsoon_indicator_SW"] = out["Week"].isin(MONSOON_WEEKS_SW).astype(int)
    out["monsoon_indicator_NE"] = out["Week"].isin(MODULE2_MONSOON_WEEKS_NE).astype(int)

    return out


# ---------------------------------------------------------------------------
# M2-5: case-level seasonal anomaly lags (fold-agnostic - see module docstring)
# ---------------------------------------------------------------------------

def compute_case_anomaly_lags(
    df: pd.DataFrame, *, carry_forward_masked_lag1: bool = False,
) -> pd.DataFrame:
    """Return a `(District, Year, Week, case_anomaly_lag_1, case_anomaly_lag_2)`
    DataFrame, safe to merge onto the main feature table.

    `case_zscore` for a row's OWN week is deliberately not exposed - at
    `k=EPIDEMIC_THRESHOLD_K` it is nearly identical to the label itself
    (`zscore > k`). Only the shifted (1-2 weeks prior) values are safe and
    useful features. Rows whose lagged week was itself `is_imputed` get
    `NaN` (a fabricated case count is not a real anomaly observation).

    `carry_forward_masked_lag1` (experimental, default off - mirrors Module
    1's Decision 030/M1-006B `cases_lag_1` nowcast substitution, but is NOT
    itself validated/adopted yet): when True, and week *t-1* is itself
    `is_reporting_anomaly` (so `case_anomaly_lag_1` at row *t* would
    otherwise be `NaN`), substitute `case_anomaly_lag_2` (the last
    known-good anomaly reading, from *t-2*) instead of leaving it missing.
    `case_anomaly_lag_1` is this model's single most important feature
    (~35% of RF feature importance) - leaving it `NaN` right after a
    flagged week means the model's preprocessing median-imputes it to
    approximately "no anomaly", which is the wrong default during a real
    accelerating outbreak (see the 2026 Wk25 Colombo/Gampaha false-negative
    investigation). Does NOT touch `is_imputed`-driven masking (a
    fabricated case count is a different kind of unknown than a merely
    mis-timed real one) - scoped identically to M1-006B's own precedent.
    """
    stats = compute_historical_stats_harmonic(df)
    stats = stats.sort_values(["District", "Year", "Week"]).reset_index(drop=True)

    case_zscore = (stats["Number_of_Cases"] - stats["historical_mean"]) / stats["historical_sd"]
    case_zscore = case_zscore.replace([np.inf, -np.inf], np.nan)
    case_zscore = case_zscore.where(~stats["is_imputed"].fillna(False).astype(bool))
    if "is_reporting_anomaly" in stats.columns:
        # `.fillna(False)` guards against a NaN-contaminated boolean column
        # (e.g. synthetic forward-week rows lacking this field, which
        # upcasts the whole column to object/float and breaks `~`) - found
        # via forecast_future_risk.py's forward scoring (M2-013 follow-up).
        case_zscore = case_zscore.where(~stats["is_reporting_anomaly"].fillna(False).astype(bool))

    stats["case_zscore"] = case_zscore
    grouped = stats.groupby("District")
    grouped_zscore = grouped["case_zscore"]
    stats["case_anomaly_lag_1"] = grouped_zscore.shift(1)
    stats["case_anomaly_lag_2"] = grouped_zscore.shift(2)

    if carry_forward_masked_lag1 and "is_reporting_anomaly" in stats.columns:
        prior_flagged = grouped["is_reporting_anomaly"].shift(1).fillna(False).astype(bool)
        stats["case_anomaly_lag_1"] = stats["case_anomaly_lag_1"].where(
            ~prior_flagged, stats["case_anomaly_lag_2"]
        )

    return stats[["District", "Year", "Week", "case_anomaly_lag_1", "case_anomaly_lag_2"]]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def build_module2_feature_table(
    input_path: Path = MODULE2_WEEKLY_MODELING_TABLE_PATH,
    *,
    carry_forward_masked_lag1: bool = False,
) -> pd.DataFrame:
    df = pd.read_csv(input_path, parse_dates=["Week_Start_Date", "Week_End_Date"])

    features = build_fold_agnostic_features(df)
    case_anomaly_lags = compute_case_anomaly_lags(
        df, carry_forward_masked_lag1=carry_forward_masked_lag1,
    )
    features = features.merge(case_anomaly_lags, on=["District", "Year", "Week"], how="left")

    return features.drop(columns=[WEATHER_CODE_COLUMN], errors="ignore")


def run_feature_engineering() -> pd.DataFrame:
    MODULE2_FEATURES_DIR.mkdir(parents=True, exist_ok=True)

    features = build_module2_feature_table()
    features.to_csv(MODULE2_STAGE1_FEATURE_TABLE_PATH, index=False)

    logger.info(
        "Wrote %d feature rows (%d columns) to %s. %d fold-agnostic model "
        "features enumerated in FOLD_AGNOSTIC_FEATURE_COLUMNS. Fold-aware "
        "climate anomalies (%s) and the outbreak label are NOT included "
        "here - compute them per walk-forward fold instead "
        "(compute_fold_climate_anomalies / labels.compute_epidemic_threshold_labels).",
        len(features), features.shape[1], MODULE2_STAGE1_FEATURE_TABLE_PATH,
        len(FOLD_AGNOSTIC_FEATURE_COLUMNS), FOLD_AWARE_FEATURE_COLUMNS,
    )
    return features


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_feature_engineering()
