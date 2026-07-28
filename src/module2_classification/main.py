"""Entry point for Module 2 (Hybrid Outbreak Risk Classification).

Orchestrates the pipeline end to end:

```text
shared preprocessing -> module2 preprocessing -> feature engineering
    -> Stage 1 (baseline classifier) -> Stage 2 (compensation model)
    -> Stage 2 risk thresholds (alert flag + low/medium/high tiers)
```

Idempotent by default, mirroring `src/module1_forecasting/main.py`: each
stage is SKIPPED if its main output file already exists. Pass `--force` to
rerun every stage regardless, or `--stages` to run a specific subset by name.
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
    MODULE2_BASELINE_PREDICTIONS_PATH,
    MODULE2_RISK_TIER_PREDICTIONS_PATH,
    MODULE2_STAGE1_FEATURE_TABLE_PATH,
    MODULE2_STAGE2_PREDICTIONS_PATH,
    MODULE2_WEEKLY_MODELING_TABLE_PATH,
    SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH,
)

logger = logging.getLogger(__name__)


def _run_shared_preprocessing() -> None:
    from src.preprocessing.shared import run_shared_preprocessing

    run_shared_preprocessing()


def _run_module2_preprocessing() -> None:
    from src.preprocessing.module2_preprocessing import run_module2_preprocessing

    run_module2_preprocessing()


def _run_feature_engineering() -> None:
    from src.module2_classification.feature_engineering import run_feature_engineering

    run_feature_engineering()


def _run_stage1_baseline_classifier() -> None:
    from src.module2_classification.baseline_classifier import run_stage1_pipeline

    run_stage1_pipeline()


def _run_stage2_compensation() -> None:
    from src.module2_classification.compensation_model import run_stage2_pipeline

    run_stage2_pipeline()


def _run_stage2_risk_thresholds() -> None:
    from src.module2_classification.risk_thresholds import run_risk_threshold_pipeline

    run_risk_threshold_pipeline()


# Ordered (name, output-file-to-check, run-function) - each stage's output is
# what the NEXT stage reads, so running a later stage without an earlier
# stage's output already on disk will simply fail naturally with a clear
# FileNotFoundError rather than silently using stale data.
PIPELINE_STAGES: list[tuple[str, Path, callable]] = [
    ("shared_preprocessing", SHARED_EPIDEMIOLOGICAL_WEEKLY_PATH, _run_shared_preprocessing),
    ("module2_preprocessing", MODULE2_WEEKLY_MODELING_TABLE_PATH, _run_module2_preprocessing),
    ("feature_engineering", MODULE2_STAGE1_FEATURE_TABLE_PATH, _run_feature_engineering),
    ("stage1_baseline_classifier", MODULE2_BASELINE_PREDICTIONS_PATH, _run_stage1_baseline_classifier),
    ("stage2_compensation", MODULE2_STAGE2_PREDICTIONS_PATH, _run_stage2_compensation),
    ("stage2_risk_thresholds", MODULE2_RISK_TIER_PREDICTIONS_PATH, _run_stage2_risk_thresholds),
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

    logger.info("Module 2 pipeline complete.")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Module 2 classification pipeline end to end.")
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
