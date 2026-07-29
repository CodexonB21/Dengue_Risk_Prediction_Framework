"""Entry point for Module 1 (Hybrid Time-Series Case Forecasting).

Orchestrates the full pipeline end to end:

```text
shared preprocessing -> module1 preprocessing -> feature engineering
    -> Stage 1 (SARIMA) -> Stage 2 (XGBoost) -> combine
```

Idempotent by default: each stage is SKIPPED if its main output file already
exists, since Stage 1 alone takes ~82 minutes (dominated by `auto_arima`
order search) - rerunning it on every invocation would make iterating on
Stage 2/combine impractically slow. Pass `--force` to rerun every stage
regardless, or `--stages` to run a specific subset by name.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import (  # noqa: E402
    MODULE1_FINAL_PREDICTIONS_PATH,
    MODULE1_SARIMA_PREDICTIONS_PATH,
    MODULE1_STAGE2_FEATURE_TABLE_PATH,
    MODULE1_WEEKLY_MODELING_TABLE_PATH,
    MODULE1_XGBOOST_PREDICTIONS_PATH,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
)

logger = logging.getLogger(__name__)


def _run_shared_preprocessing() -> None:
    from src.preprocessing.shared import run_shared_preprocessing

    run_shared_preprocessing()


def _run_module1_preprocessing() -> None:
    from src.preprocessing.module1_preprocessing import run_module1_preprocessing

    run_module1_preprocessing()


def _run_feature_engineering() -> None:
    from src.module1_forecasting.feature_engineering import run_feature_engineering

    run_feature_engineering()


def _run_stage1() -> None:
    from src.module1_forecasting.baseline_sarima import run_stage1_pipeline

    run_stage1_pipeline()


def _run_stage2() -> None:
    from src.module1_forecasting.compensation_model import run_stage2_pipeline

    run_stage2_pipeline()


def _run_combine() -> None:
    from src.module1_forecasting.combine import run_combine_pipeline

    run_combine_pipeline()


# Ordered (name, output-file-to-check, run-function) - each stage's output is
# what the NEXT stage reads, so running a later stage without an earlier
# stage's output already on disk will simply fail naturally with a clear
# FileNotFoundError rather than silently using stale data.
PIPELINE_STAGES: list[tuple[str, Path, callable]] = [
    ("shared_preprocessing", SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH, _run_shared_preprocessing),
    ("module1_preprocessing", MODULE1_WEEKLY_MODELING_TABLE_PATH, _run_module1_preprocessing),
    ("feature_engineering", MODULE1_STAGE2_FEATURE_TABLE_PATH, _run_feature_engineering),
    ("stage1_sarima", MODULE1_SARIMA_PREDICTIONS_PATH, _run_stage1),
    ("stage2_xgboost", MODULE1_XGBOOST_PREDICTIONS_PATH, _run_stage2),
    ("combine", MODULE1_FINAL_PREDICTIONS_PATH, _run_combine),
]

STAGE_NAMES = [name for name, _, _ in PIPELINE_STAGES]


def run_pipeline(force: bool = False, stages: list[str] | None = None) -> None:
    selected = set(stages) if stages else set(STAGE_NAMES)
    unknown = selected - set(STAGE_NAMES)
    if unknown:
        raise ValueError(f"Unknown stage(s): {sorted(unknown)}. Valid stages: {STAGE_NAMES}")

    for name, output_path, run_fn in PIPELINE_STAGES:
        if name not in selected:
            continue
        if not force and output_path.exists():
            logger.info("Skipping '%s' - output already exists at %s (use --force to rerun).", name, output_path)
            continue
        logger.info("Running '%s'...", name)
        run_fn()
        logger.info("Finished '%s'.", name)

    logger.info("Module 1 pipeline complete.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Module 1 forecasting pipeline end to end.")
    parser.add_argument(
        "--force", action="store_true",
        help="Rerun every selected stage even if its output file already exists.",
    )
    parser.add_argument(
        "--stages", nargs="+", choices=STAGE_NAMES, default=None,
        help=f"Run only these stages (default: all). Choices: {STAGE_NAMES}.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = _parse_args()
    run_pipeline(force=args.force, stages=args.stages)
