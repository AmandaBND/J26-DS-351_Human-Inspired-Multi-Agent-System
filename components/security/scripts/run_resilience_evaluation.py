import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.evaluation import SystemResilienceEvaluator


def save_plot(
    metrics: pd.DataFrame,
    *,
    metric: str,
    title: str,
    ylabel: str,
    output_file: Path,
) -> None:
    numeric = metrics[
        metrics["compromised_count"] != "ALL"
    ].copy()

    numeric["compromised_count"] = numeric[
        "compromised_count"
    ].astype(int)

    pivot = numeric.pivot(
        index="compromised_count",
        columns="strategy",
        values=metric,
    ).sort_index()

    axis = pivot.plot(marker="o")
    axis.set_title(title)
    axis.set_xlabel("Number of Compromised / Unavailable Monitors")
    axis.set_ylabel(ylabel)
    axis.set_ylim(0, 1.05)
    axis.figure.tight_layout()
    axis.figure.savefig(output_file, dpi=180)
    plt.close(axis.figure)


def main() -> None:
    benchmark = (
        PROJECT_ROOT
        / "data"
        / "benchmark"
        / "reliability"
    )

    evaluator = SystemResilienceEvaluator(
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
        evidence_mode="full",
    )

    event_results, metrics, trust_history, metadata = (
        evaluator.evaluate()
    )

    output = PROJECT_ROOT / "results" / "system_resilience"
    output.mkdir(parents=True, exist_ok=True)

    event_results.to_csv(
        output / "event_level_results.csv",
        index=False,
    )
    metrics.to_csv(
        output / "metrics_by_compromised_count.csv",
        index=False,
    )
    trust_history.to_csv(
        output / "monitor_trust_history.csv",
        index=False,
    )
    (output / "evaluation_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    overall = metrics[
        metrics["compromised_count"] == "ALL"
    ].copy()
    overall.to_csv(
        output / "overall_metrics.csv",
        index=False,
    )

    save_plot(
        metrics,
        metric="final_decision_accuracy",
        title="Final Security Decision Accuracy vs Compromised Monitors",
        ylabel="Final Decision Accuracy",
        output_file=output / "accuracy_vs_compromise.png",
    )

    save_plot(
        metrics,
        metric="attack_success_rate",
        title="Attack Success Rate vs Compromised Monitors",
        ylabel="Attack Success Rate",
        output_file=output / "attack_success_vs_compromise.png",
    )

    print("\nOverall system-level comparison:")
    print(
        overall[
            [
                "strategy",
                "events",
                "final_decision_accuracy",
                "attack_success_rate",
                "false_block_rate",
                "review_rate",
            ]
        ].to_string(index=False)
    )

    print(
        "\nUse only the values produced here in your report. "
        "Do not invent a better result."
    )
    print(f"\nResults saved to: {output}")


if __name__ == "__main__":
    main()
