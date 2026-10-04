import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from security_framework.simulator.scenario_loader import (
    load_experiment_scenarios,
    summarize_experiment_scenarios,
)


def main() -> None:
    scenario_file = (
        PROJECT_ROOT
        / "data"
        / "raw_scenarios"
        / "compromised_monitor_scenarios.json"
    )

    scenarios = load_experiment_scenarios(
        scenario_file
    )

    summary = summarize_experiment_scenarios(
        scenarios
    )

    print("=" * 70)
    print("COMPROMISED SECURITY-MONITOR SCENARIO VALIDATION")
    print("=" * 70)

    print(
        f"Loaded scenarios: "
        f"{summary['total_scenarios']}"
    )

    print(
        f"Normal monitor instances: "
        f"{summary['normal_monitors']}"
    )

    print(
        f"Compromised monitor instances: "
        f"{summary['compromised_monitors']}"
    )

    print(
        f"Unavailable monitor instances: "
        f"{summary['unavailable_monitors']}"
    )

    print("\nExpected Final Decisions:")

    for decision, count in (
        summary[
            "expected_final_decisions"
        ].items()
    ):
        print(
            f"  {decision}: {count}"
        )

    print("\nScenario Details:")

    for scenario in scenarios:
        print(
            f"\n{scenario.scenario_id}"
        )

        print(
            f"  Ground truth: "
            f"{scenario.expected_final_decision.value}"
        )

        for monitor in scenario.monitors:
            print(
                f"  {monitor.monitor_id}: "
                f"{monitor.monitor_state.value} / "
                f"{monitor.behavior_mode.value}"
            )

    print(
        "\nAll compromised-monitor scenarios "
        "passed schema validation."
    )


if __name__ == "__main__":
    main()