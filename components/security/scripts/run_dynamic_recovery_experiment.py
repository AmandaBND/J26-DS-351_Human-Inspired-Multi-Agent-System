import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.evaluation.dynamic_recovery import (
    DynamicRecoveryExperiment,
)
from security_framework.trust import AdaptiveTrustEstimator


def best_supervised_model_name() -> str:
    metrics = pd.read_csv(
        PROJECT_ROOT
        / "results"
        / "reliability_models"
        / "model_metrics.csv"
    )

    supervised = metrics[
        metrics["model"] != "isolation_forest"
    ].sort_values(
        by=["f1", "auprc"],
        ascending=False,
    )

    if supervised.empty:
        raise ValueError("No supervised reliability model exists.")

    return str(supervised.iloc[0]["model"])


def build_trust_estimator() -> AdaptiveTrustEstimator:
    config = json.loads(
        (
            PROJECT_ROOT
            / "config"
            / "trust.json"
        ).read_text(encoding="utf-8")
    )

    return AdaptiveTrustEstimator(
        initial_trust=float(config["initial_trust"]),
        alpha=float(config["alpha"]),
        active_threshold=float(config["thresholds"]["active"]),
        reduced_threshold=float(config["thresholds"]["reduced"]),
        review_threshold=float(config["thresholds"]["review"]),
        severe_violation_cap=float(config["severe_violation_cap"]),
    )


def main() -> None:
    model_name = best_supervised_model_name()
    model_file = (
        PROJECT_ROOT
        / "models"
        / "reliability"
        / f"{model_name}.joblib"
    )

    feature_file = (
        PROJECT_ROOT
        / "data"
        / "benchmark"
        / "reliability"
        / "test_features.csv"
    )

    if not model_file.exists():
        raise FileNotFoundError(
            f"Missing trained model: {model_file}\n"
            "Run train_reliability_models.py first."
        )

    test_features = pd.read_csv(feature_file)

    experiment = DynamicRecoveryExperiment(
        model_file=model_file,
        trust_estimator=build_trust_estimator(),
    )

    frame, summary = experiment.run(
        test_features=test_features,
        monitor_id="policy-monitor",
        compromise_condition="FALSE_ALLOW",
        normal_windows=5,
        compromised_windows=7,
        recovery_windows=7,
    )

    output = PROJECT_ROOT / "results" / "dynamic_recovery"
    output.mkdir(parents=True, exist_ok=True)

    csv_file = output / "dynamic_recovery.csv"
    frame.to_csv(csv_file, index=False)

    summary_file = output / "dynamic_recovery_summary.json"
    summary_file.write_text(
        json.dumps(
            {
                "probability_model": model_name,
                "monitor_id": "policy-monitor",
                "compromise_condition": "FALSE_ALLOW",
                "detection_delay_windows": summary.detection_delay_windows,
                "recovery_delay_windows": summary.recovery_delay_windows,
                "minimum_trust": summary.minimum_trust,
                "final_trust": summary.final_trust,
                "warning": (
                    "Controlled PP1 temporal experiment using "
                    "representative held-out feature rows."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    figure, axis = plt.subplots()
    axis.plot(frame["window"], frame["trust"], marker="o")
    axis.set_title("Monitor Trust During Compromise and Recovery")
    axis.set_xlabel("Observation Window")
    axis.set_ylabel("Trust Score")
    axis.set_ylim(0, 1.05)
    figure.tight_layout()

    figure_file = output / "dynamic_recovery.png"
    figure.savefig(figure_file, dpi=180)
    plt.close(figure)

    print(
        frame[
            [
                "window",
                "phase",
                "p_compromised",
                "trust",
                "trust_status",
            ]
        ].to_string(index=False)
    )

    print(
        f"\nDetection delay (windows): {summary.detection_delay_windows}"
    )
    print(
        f"Recovery delay (windows): {summary.recovery_delay_windows}"
    )
    print(f"\nCSV: {csv_file}")
    print(f"Summary: {summary_file}")
    print(f"Figure: {figure_file}")


if __name__ == "__main__":
    main()
