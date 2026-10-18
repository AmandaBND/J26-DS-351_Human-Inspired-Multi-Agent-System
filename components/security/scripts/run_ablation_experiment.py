import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.evaluation import SystemResilienceEvaluator


def evaluator(mode: str) -> SystemResilienceEvaluator:
    benchmark = (
        PROJECT_ROOT
        / "data"
        / "benchmark"
        / "reliability"
    )

    return SystemResilienceEvaluator(
        feature_file=benchmark / "test_features.csv",
        decision_log=benchmark / "test_decisions.jsonl",
        model_metrics_file=(
            PROJECT_ROOT
            / "results"
            / "reliability_models"
            / "model_metrics.csv"
        ),
        model_dir=PROJECT_ROOT / "models" / "reliability",
        trust_config_file=PROJECT_ROOT / "config" / "trust.json",
        fusion_config_file=PROJECT_ROOT / "config" / "fusion.json",
        evidence_mode=mode,
    )


def main() -> None:
    rows = []

    for mode in [
        "full",
        "model_only",
        "no_challenge",
        "no_policy",
    ]:
        _, metrics, _, metadata = evaluator(mode).evaluate()

        adaptive = metrics[
            (metrics["strategy"] == "adaptive_trust_weighting")
            & (metrics["compromised_count"] == "ALL")
        ]

        if adaptive.empty:
            continue

        row = adaptive.iloc[0]

        rows.append(
            {
                "evidence_mode": mode,
                "probability_model": metadata["probability_model"],
                "final_decision_accuracy": row["final_decision_accuracy"],
                "attack_success_rate": row["attack_success_rate"],
                "false_block_rate": row["false_block_rate"],
                "review_rate": row["review_rate"],
            }
        )

    frame = pd.DataFrame(rows)
    output = PROJECT_ROOT / "results" / "ablation"
    output.mkdir(parents=True, exist_ok=True)

    csv_file = output / "evidence_ablation.csv"
    frame.to_csv(csv_file, index=False)

    axis = frame.set_index("evidence_mode")[
        ["final_decision_accuracy", "attack_success_rate"]
    ].plot(kind="bar")

    axis.set_title("Ablation of Monitor-Reliability Evidence")
    axis.set_ylabel("Score / Rate")
    axis.set_ylim(0, 1.05)
    axis.figure.tight_layout()

    figure_file = output / "evidence_ablation.png"
    axis.figure.savefig(figure_file, dpi=180)
    plt.close(axis.figure)

    print("\nEvidence ablation:")
    print(frame.to_string(index=False))
    print(f"\nCSV: {csv_file}")
    print(f"Figure: {figure_file}")


if __name__ == "__main__":
    main()
