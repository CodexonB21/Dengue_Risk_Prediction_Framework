"""Detect and flag suspected delayed-reporting weeks in weekly case counts.

A recurring data-quality pattern in this project's Sri Lanka dengue series:
a sharp week-over-week *drop* in reported cases immediately followed by a
large *rebound* the next week — consistent with reporting lag / catch-up
rather than a true epidemiological collapse (see Module 1 Open Question #16,
Colombo/Gampaha 2026 Wk24→Wk25).

Flagged weeks are stored as `is_reporting_anomaly=True` on the module
weekly modeling tables. Downstream feature engineering treats them like
`is_imputed` rows: the raw `Number_of_Cases` remains in the table for
labels and evaluation, but case-derived LAG/rolling features must not
consume the suspect value (Decision 026).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Flag week t when cases[t] / cases[t-1] <= DROP_RATIO (>= ~75% drop) AND
# cases[t+1] / max(cases[t], 1) >= REBOUND_RATIO. Prior week must exceed
# MIN_PRIOR_CASES so tiny noisy districts are not over-flagged.
DEFAULT_DROP_RATIO = 0.25
DEFAULT_REBOUND_RATIO = 2.5
DEFAULT_MIN_PRIOR_CASES = 100.0


def flag_reporting_anomalies(
    df: pd.DataFrame,
    *,
    drop_ratio: float = DEFAULT_DROP_RATIO,
    rebound_ratio: float = DEFAULT_REBOUND_RATIO,
    min_prior_cases: float = DEFAULT_MIN_PRIOR_CASES,
) -> pd.DataFrame:
    """Return a copy of `df` with boolean column `is_reporting_anomaly`.

    Expects columns: District, Year, Week, Number_of_Cases. If
    `is_reporting_anomaly` already exists it is recomputed.
    """
    out = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True).copy()
    out["is_reporting_anomaly"] = False

    for district, group in out.groupby("District", sort=False):
        idx = group.index.to_numpy()
        cases = group["Number_of_Cases"].to_numpy(dtype=float)
        flags = np.zeros(len(cases), dtype=bool)

        for i in range(1, len(cases) - 1):
            prior = cases[i - 1]
            current = cases[i]
            nxt = cases[i + 1]
            if np.isnan(prior) or np.isnan(current) or np.isnan(nxt):
                continue
            if prior < min_prior_cases:
                continue
            if prior <= 0:
                continue
            if current / prior > drop_ratio:
                continue
            rebound = nxt / max(current, 1.0)
            if rebound >= rebound_ratio or nxt >= prior:
                flags[i] = True

        out.loc[idx, "is_reporting_anomaly"] = flags

    n_flagged = int(out["is_reporting_anomaly"].sum())
    if n_flagged:
        sample = out.loc[out["is_reporting_anomaly"], ["District", "Year", "Week", "Number_of_Cases"]].head(10)
        logger.info(
            "Flagged %d suspected reporting-anomaly weeks (drop>=%.0f%%, rebound>=%.1fx, min_prior=%.0f). "
            "Sample:\n%s",
            n_flagged,
            (1.0 - drop_ratio) * 100,
            rebound_ratio,
            min_prior_cases,
            sample.to_string(index=False),
        )
    else:
        logger.info("No reporting-anomaly weeks flagged with current thresholds.")

    return out


def mask_untrusted_cases(df: pd.DataFrame) -> pd.Series:
    """Case counts nulled for feature derivation (imputed + reporting anomaly)."""
    cases = df["Number_of_Cases"]
    untrusted = pd.Series(False, index=df.index)
    if "is_imputed" in df.columns:
        untrusted = untrusted | df["is_imputed"].astype(bool)
    if "is_reporting_anomaly" in df.columns:
        untrusted = untrusted | df["is_reporting_anomaly"].astype(bool)
    return cases.where(~untrusted)


WEEKS_SINCE_REPORTING_ANOMALY_CAP = 4

REPORTING_DELAY_FEATURE_COLUMNS = [
    "weeks_since_reporting_anomaly",
    "reporting_rebound_ratio_lag1",
    "suspected_backfill_week",
]


def compute_reporting_delay_features(df: pd.DataFrame) -> pd.DataFrame:
    """M1-006B reporting-state features (fold-agnostic, leakage-safe).

    - ``weeks_since_reporting_anomaly``: calendar weeks since the most recent
      ``is_reporting_anomaly`` week in the same district (0 if current week
      flagged; capped at 4; NaN if no prior anomaly in history).
    - ``reporting_rebound_ratio_lag1``: at week *t*, when week *t−1* was
      flagged, ``cases[t−1] / max(cases[t−2], 1)`` using raw counts (captures
      the dip magnitude that motivated the flag — not masked).
    - ``suspected_backfill_week``: ``int(is_reporting_anomaly)`` at week *t*.
    """
    ordered = df.sort_values(["District", "Year", "Week"]).reset_index(drop=True)
    out = pd.DataFrame(index=ordered.index)

    if "is_reporting_anomaly" not in ordered.columns:
        out["weeks_since_reporting_anomaly"] = np.nan
        out["reporting_rebound_ratio_lag1"] = np.nan
        out["suspected_backfill_week"] = 0
        return out

    flags = ordered["is_reporting_anomaly"].astype(bool)
    cases = ordered["Number_of_Cases"].to_numpy(dtype=float)
    out["suspected_backfill_week"] = flags.astype(int)

    weeks_since = np.full(len(ordered), np.nan, dtype=float)
    rebound = np.full(len(ordered), np.nan, dtype=float)

    for _, group in ordered.groupby("District", sort=False):
        idx = group.index.to_numpy()
        g_flags = flags.loc[idx].to_numpy()
        g_cases = cases[idx]

        for pos, i in enumerate(idx):
            if g_flags[pos]:
                weeks_since[i] = 0.0
            else:
                for back in range(1, pos + 1):
                    if g_flags[pos - back]:
                        weeks_since[i] = float(min(back, WEEKS_SINCE_REPORTING_ANOMALY_CAP))
                        break

            if pos >= 2 and g_flags[pos - 1]:
                rebound[i] = g_cases[pos - 1] / max(g_cases[pos - 2], 1.0)

    out["weeks_since_reporting_anomaly"] = weeks_since
    out["reporting_rebound_ratio_lag1"] = rebound
    return out
