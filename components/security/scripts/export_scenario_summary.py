import sys
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from security_framework.simulator.scenario_loader import (
    load_scenarios,
)


def main() -> None:
    source_file = (
        PROJECT_ROOT
        / "data"
        / "raw_scenarios"
        / "normal_scenarios.json"
    )

    output_file = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "normal_scenario_summary.csv"
    )

    scenarios = load_scenarios(
        source_file
    )

    rows = []

    for event in scenarios:
        rows.append(
            {
                "event_id": event.event_id,
                "scenario_id": event.scenario_id,
                "source_agent_id": event.source_agent_id,
                "event_type": event.event_type.value,
                "expected_decision": (
                    event.expected_decision.value
                ),
                "attack_type": (
                    event.attack_type.value
                ),
                "agent_state": (
                    event.source_agent_state.value
                ),
            }
        )

    df = pd.DataFrame(rows)

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_file,
        index=False,
    )

    print(
        f"Saved {len(df)} scenarios "
        f"to {output_file}"
    )


if __name__ == "__main__":
    main()