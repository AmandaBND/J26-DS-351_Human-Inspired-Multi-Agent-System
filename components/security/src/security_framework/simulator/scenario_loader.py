import json
from pathlib import Path

from security_framework.models import SecurityEvent


def load_scenarios(file_path: str | Path) -> list[SecurityEvent]:
    """
    Load controlled experimental scenarios from a JSON file.

    Every scenario is validated using the SecurityEvent model.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Scenario file does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, list):
        raise ValueError(
            "Scenario JSON must contain a list of events."
        )

    scenarios = [
        SecurityEvent.model_validate(item)
        for item in raw_data
    ]

    return scenarios


def summarize_scenarios(
    scenarios: list[SecurityEvent],
) -> dict:
    total = len(scenarios)

    decisions: dict[str, int] = {}
    event_types: dict[str, int] = {}

    for scenario in scenarios:
        decision = scenario.expected_decision.value
        event_type = scenario.event_type.value

        decisions[decision] = (
            decisions.get(decision, 0) + 1
        )

        event_types[event_type] = (
            event_types.get(event_type, 0) + 1
        )

    return {
        "total_scenarios": total,
        "expected_decisions": decisions,
        "event_types": event_types,
    }