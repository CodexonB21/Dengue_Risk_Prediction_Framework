"""Module 1 Stage 1 - seasonal-differencing test diagnostics (OCSB / Canova-Hansen).

Backfills a citation gap: `MODULE_CONTEXT.md`, `EXPERIMENT_LOG.md`, and
`CHANGELOG.md` all state that "both the OCSB and Canova-Hansen
seasonal-differencing tests independently selected D=0 for all 25
districts" (Open Question #1 / #12), but no per-district test result was
ever saved to disk - the claim was previously backed only by narrative,
not a reproducible artifact. This script reruns both tests explicitly, on
the same pre-holdout series and transforms `select_order()`
(`baseline_sarima.py`) already uses, and saves the per-district decisions.

`pmdarima.arima.nsdiffs(..., test="ocsb"|"ch")` is used rather than the
raw `OCSBTest`/`CHTest` classes because pmdarima 2.1.1 does not expose a
public numeric test statistic or p-value from either class - only the
final differencing decision (`estimate_seasonal_differencing_term`) via
`.estimate_seasonal_differencing_term(x)`, which is exactly what
`nsdiffs` wraps. The result recorded here is therefore the binary D
decision (0 or 1) per test, per district, per transform - matching
precisely what the existing documentation claims, not a stronger claim
than the library can support.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pmdarima.arima import nsdiffs

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    DISTRICTS,
    MODULE1_SEASONAL_DIFF_PLOT_PATH,
    MODULE1_SEASONAL_DIFF_TEST_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
)
from src.module1_forecasting.validation import (  # noqa: E402
    DEFAULT_HOLDOUT_YEARS,
    DEFAULT_WEEKS_PER_YEAR,
    get_district_series,
)

logger = logging.getLogger(__name__)

VALUE_COL = "Number_of_Cases"
WEEKS_PER_YEAR = DEFAULT_WEEKS_PER_YEAR
HOLDOUT_YEARS = DEFAULT_HOLDOUT_YEARS

# Same bound `select_order()` uses in baseline_sarima.py - D is never
# allowed above 1 there either, so testing higher D would answer a
# different question than "did auto_arima's D=0 choice have test support."
MAX_D = 1


def run_seasonal_diff_tests(series: np.ndarray) -> tuple[int, int]:
    """Return (ocsb_D, ch_D) for one pre-holdout series."""
    ocsb_d = int(nsdiffs(series, m=WEEKS_PER_YEAR, max_D=MAX_D, test="ocsb"))
    ch_d = int(nsdiffs(series, m=WEEKS_PER_YEAR, max_D=MAX_D, test="ch"))
    return ocsb_d, ch_d


def build_results_table(districts: list[str] = DISTRICTS) -> pd.DataFrame:
    df = pd.read_csv(MODULE1_WEEKLY_MODELING_TABLE_PATH, parse_dates=["Week_Start_Date", "Week_End_Date"])

    rows: list[dict] = []
    for district in districts:
        series = get_district_series(df, district, value_col=VALUE_COL)
        pre_holdout = series.iloc[: len(series) - HOLDOUT_YEARS * WEEKS_PER_YEAR]

        for transform, values in (
            ("raw", pre_holdout.to_numpy(dtype=float)),
            ("log1p", np.log1p(pre_holdout.to_numpy(dtype=float))),
        ):
            ocsb_d, ch_d = run_seasonal_diff_tests(values)
            rows.append(
                {
                    "District": district,
                    "transform": transform,
                    "n_weeks_tested": len(values),
                    "ocsb_D": ocsb_d,
                    "ch_D": ch_d,
                    "tests_agree": ocsb_d == ch_d,
                }
            )
            logger.info(
                "%s | %-5s | OCSB D=%d | Canova-Hansen D=%d | agree=%s",
                district,
                transform,
                ocsb_d,
                ch_d,
                ocsb_d == ch_d,
            )

    return pd.DataFrame(rows)


def plot_seasonal_diff_heatmap(results: pd.DataFrame, output_path: Path = MODULE1_SEASONAL_DIFF_PLOT_PATH) -> None:
    """Heatmap of D decisions: districts x (test, transform) cells, colored
    by D (0 = no seasonal differencing needed, 1 = needed). All-D=0 would
    render as a single flat color - itself the visual evidence for
    "unanimous agreement" that the narrative claim describes.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    districts = sorted(results["District"].unique())
    columns = [
        ("OCSB", "raw"), ("Canova-Hansen", "raw"),
        ("OCSB", "log1p"), ("Canova-Hansen", "log1p"),
    ]
    col_labels = [f"{test}\n({transform})" for test, transform in columns]

    matrix = np.zeros((len(districts), len(columns)), dtype=float)
    for i, district in enumerate(districts):
        for j, (test, transform) in enumerate(columns):
            key = "ocsb_D" if test == "OCSB" else "ch_D"
            value = results.loc[
                (results["District"] == district) & (results["transform"] == transform), key
            ].iloc[0]
            matrix[i, j] = value

    fig, ax = plt.subplots(figsize=(6, 0.32 * len(districts) + 1.5))
    im = ax.imshow(matrix, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(columns)))
    ax.set_xticklabels(col_labels, fontsize=8)
    ax.set_yticks(range(len(districts)))
    ax.set_yticklabels(districts, fontsize=7)
    ax.set_title("Seasonal differencing test decisions (D) per district\n0 = no seasonal differencing needed, 1 = needed")

    for i in range(len(districts)):
        for j in range(len(columns)):
            ax.text(j, i, int(matrix[i, j]), ha="center", va="center", fontsize=7,
                     color="white" if matrix[i, j] == 1 else "black")

    fig.colorbar(im, ax=ax, ticks=[0, 1], label="D")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    logger.info("Saved seasonal-differencing test heatmap to %s.", output_path)


def run_seasonal_diff_diagnostics() -> None:
    results = build_results_table()

    MODULE1_SEASONAL_DIFF_TEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(MODULE1_SEASONAL_DIFF_TEST_PATH, index=False)
    logger.info("Saved %d rows -> %s", len(results), MODULE1_SEASONAL_DIFF_TEST_PATH)

    plot_seasonal_diff_heatmap(results)

    n_disagree = int((~results["tests_agree"]).sum())
    n_nonzero = int((results["ocsb_D"] > 0).sum() + (results["ch_D"] > 0).sum())
    logger.info(
        "Summary: %d/%d (district, transform) rows where OCSB and Canova-Hansen disagree; "
        "%d total nonzero D decisions across both tests.",
        n_disagree,
        len(results),
        n_nonzero,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    run_seasonal_diff_diagnostics()
