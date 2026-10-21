import json
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No results available._"
    try:
        return frame.to_markdown(index=False)
    except ImportError:
        return "```\n" + frame.to_string(index=False) + "\n```"


def main() -> None:
    model_file = (
        PROJECT_ROOT
        / "results"
        / "reliability_models"
        / "model_metrics.csv"
    )
    resilience_file = (
        PROJECT_ROOT
        / "results"
        / "system_resilience"
        / "overall_metrics.csv"
    )
    by_count_file = (
        PROJECT_ROOT
        / "results"
        / "system_resilience"
        / "metrics_by_compromised_count.csv"
    )
    ablation_file = (
        PROJECT_ROOT
        / "results"
        / "ablation"
        / "evidence_ablation.csv"
    )
    recovery_file = (
        PROJECT_ROOT
        / "results"
        / "dynamic_recovery"
        / "dynamic_recovery_summary.json"
    )

    required = [
        model_file,
        resilience_file,
        by_count_file,
        ablation_file,
        recovery_file,
    ]

    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing PP1 result files:\n"
            + "\n".join(str(path) for path in missing)
        )

    model_metrics = pd.read_csv(model_file)
    resilience = pd.read_csv(resilience_file)
    by_count = pd.read_csv(by_count_file)
    ablation = pd.read_csv(ablation_file)
    recovery = json.loads(
        recovery_file.read_text(encoding="utf-8")
    )

    model_view = model_metrics[
        ["model", "precision", "recall", "f1", "auprc", "fpr"]
    ]

    resilience_view = resilience[
        [
            "strategy",
            "final_decision_accuracy",
            "attack_success_rate",
            "false_block_rate",
            "review_rate",
        ]
    ]

    adaptive_by_count = by_count[
        (by_count["strategy"] == "adaptive_trust_weighting")
        & (by_count["compromised_count"] != "ALL")
    ][
        [
            "compromised_count",
            "final_decision_accuracy",
            "attack_success_rate",
            "false_block_rate",
        ]
    ]

    content = f"""# PP1 Preliminary Research Evidence

## 1. Monitor-Reliability Model Comparison

{table(model_view)}

## 2. Final Security Decision Strategy Comparison

{table(resilience_view)}

## 3. Proposed Adaptive Method by Compromised-Monitor Count

{table(adaptive_by_count)}

## 4. Evidence Ablation

{table(ablation)}

## 5. Dynamic Compromise / Recovery

- Probability model: `{recovery["probability_model"]}`
- Monitor: `{recovery["monitor_id"]}`
- Compromise condition: `{recovery["compromise_condition"]}`
- Detection delay: `{recovery["detection_delay_windows"]}` windows
- Recovery delay: `{recovery["recovery_delay_windows"]}` windows
- Minimum trust: `{recovery["minimum_trust"]:.4f}`
- Final trust: `{recovery["final_trust"]:.4f}`

## Interpretation Boundary

These are preliminary PP1 results from a controlled research benchmark. They demonstrate the implemented experimental pipeline and support baseline comparison, but they must not be reported as production enterprise performance.
"""

    output_dir = PROJECT_ROOT / "results" / "pp1"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "PP1_PRELIMINARY_EVIDENCE.md"
    output_file.write_text(content, encoding="utf-8")

    print(content)
    print(f"\nSaved to: {output_file}")


if __name__ == "__main__":
    main()
