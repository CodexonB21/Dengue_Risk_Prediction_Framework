"""Module 2 Stage 1 - post-hoc discrimination-vs-calibration diagnostic.

Read-only diagnostic script. Does not modify or rerun the Stage 1 pipeline -
reads the already-written `outputs/metrics/module2/baseline_classifier_metrics.csv`
and adds three derived comparisons against a "no-skill" / "climatology"
reference, none of which are in the raw metrics file:

1. `pr_auc_uplift_ratio` = pr_auc / prevalence - the correct no-skill
   reference for PR-AUC is the prevalence itself (a classifier that always
   predicts the base rate scores `PR-AUC = prevalence`), not 0.
2. `accuracy_uplift` = accuracy - (1 - prevalence) - compares against the
   majority-class ("always predict no outbreak") baseline, since raw
   accuracy under class imbalance is not a good verdict metric.
3. `brier_skill_score` = 1 - brier_score / (prevalence * (1 - prevalence)) -
   compares the model's calibration against a "climatology" forecast that
   always predicts the fold's own base rate. `reference_brier =
   prevalence * (1 - prevalence)` is exactly that climatology forecast's
   Brier score (the variance of a Bernoulli(prevalence) variable).

Purpose: PR-AUC alone confirms DISCRIMINATION (ranking ability) but says
nothing about CALIBRATION (whether the predicted probability VALUES are
trustworthy). A model can have strong discrimination and simultaneously
poor calibration - this is exactly what Decision 021's benchmark run
showed for the official XGBoost model (`scale_pos_weight`-based imbalance
correction is a common cause: it improves ranking under a reweighted loss
but distorts the output probability scale). This diagnostic makes that
decomposition explicit and persists it as a reusable artifact rather than
a one-off analysis, so numbers cited in documentation trace back to
something reproducible.
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT / "outputs" / "metrics" / "module2" / "baseline_classifier_metrics.csv"
OUTPUT_PATH = ROOT / "outputs" / "metrics" / "module2" / "baseline_classifier_calibration_diagnostic.csv"


def compute_calibration_diagnostic(metrics_df: pd.DataFrame) -> pd.DataFrame:
    official_model = metrics_df.loc[metrics_df["selected"], "model"].iloc[0]
    rows = metrics_df[
        (metrics_df["model"] == official_model) & (metrics_df["fold_id"] != "validation_aggregate")
    ].copy()

    rows["n_positive_scored"] = (rows["prevalence"] * rows["n_obs_scored"]).round().astype(int)
    rows["pr_auc_uplift_ratio"] = rows["pr_auc"] / rows["prevalence"]
    rows["majority_baseline_accuracy"] = 1 - rows["prevalence"]
    rows["accuracy_uplift"] = rows["accuracy"] - rows["majority_baseline_accuracy"]
    rows["reference_brier"] = rows["prevalence"] * (1 - rows["prevalence"])
    rows["brier_skill_score"] = 1 - rows["brier_score"] / rows["reference_brier"]

    columns = [
        "model", "fold_id", "split", "n_obs_scored", "n_positive_scored", "prevalence",
        "pr_auc", "pr_auc_uplift_ratio",
        "accuracy", "majority_baseline_accuracy", "accuracy_uplift",
        "brier_score", "reference_brier", "brier_skill_score",
    ]
    return rows[columns].reset_index(drop=True)


def main() -> None:
    metrics_df = pd.read_csv(METRICS_PATH)
    diagnostic_df = compute_calibration_diagnostic(metrics_df)

    n_folds_negative_bss = int((diagnostic_df["brier_skill_score"] < 0).sum())
    n_folds_total = len(diagnostic_df)
    n_validation_negative_acc = int(
        (diagnostic_df.loc[diagnostic_df["split"] == "validation", "accuracy_uplift"] < 0).sum()
    )
    n_validation_total = int((diagnostic_df["split"] == "validation").sum())

    print(diagnostic_df.round(4).to_string(index=False))
    print(
        f"\nFolds+holdout with negative Brier skill score (worse than climatology): "
        f"{n_folds_negative_bss}/{n_folds_total}"
    )
    print(
        f"Validation folds with negative accuracy uplift (worse than majority-class baseline): "
        f"{n_validation_negative_acc}/{n_validation_total}"
    )
    print(f"Median PR-AUC uplift ratio: {diagnostic_df['pr_auc_uplift_ratio'].median():.2f}x")
    print(f"Median Brier skill score: {diagnostic_df['brier_skill_score'].median():.4f}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    diagnostic_df.to_csv(OUTPUT_PATH, index=False)
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
