import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from security_framework.simulator.scenario_loader import (
    load_scenarios,
    summarize_scenarios,
)


def main() -> None:
    scenario_file = (
        PROJECT_ROOT
        / "data"
        / "raw_scenarios"
        / "normal_scenarios.json"
    )

    scenarios = load_scenarios(
        scenario_file
    )

    summary = summarize_scenarios(
        scenarios
    )

    print("=" * 60)
    print("NORMAL SCENARIO VALIDATION")
    print("=" * 60)

    print(
        f"Loaded scenarios: "
        f"{summary['total_scenarios']}"
    )

    print("\nExpected Decisions:")

    for decision, count in (
        summary["expected_decisions"].items()
    ):
        print(
            f"  {decision}: {count}"
        )

    print("\nEvent Types:")

    for event_type, count in (
        summary["event_types"].items()
    ):
        print(
            f"  {event_type}: {count}"
        )

    print(
        "\nAll scenarios passed "
        "schema validation."
    )


if __name__ == "__main__":
    main()