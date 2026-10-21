import json
from pathlib import Path

from security_framework.models import (
    ExperimentScenario,
    SecurityEvent,
)



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

def load_experiment_scenarios(
    file_path: str | Path,
) -> list[ExperimentScenario]:
    """
    Load controlled multi-monitor experiment scenarios.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Experiment scenario file does not exist: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    if not isinstance(raw_data, list):
        raise ValueError(
            "Experiment scenario JSON must contain a list."
        )

    scenarios = [
        ExperimentScenario.model_validate(item)
        for item in raw_data
    ]

    return scenarios


def summarize_experiment_scenarios(
    scenarios: list[ExperimentScenario],
) -> dict:
    total = len(scenarios)

    compromised_monitors = 0
    unavailable_monitors = 0
    normal_monitors = 0

    expected_decisions: dict[str, int] = {}

    for scenario in scenarios:
        decision = scenario.expected_final_decision.value

        expected_decisions[decision] = (
            expected_decisions.get(
                decision,
                0,
            )
            + 1
        )

        for monitor in scenario.monitors:
            if monitor.monitor_state.value == "COMPROMISED":
                compromised_monitors += 1

            elif monitor.monitor_state.value == "UNAVAILABLE":
                unavailable_monitors += 1

            else:
                normal_monitors += 1

    return {
        "total_scenarios": total,
        "normal_monitors": normal_monitors,
        "compromised_monitors": compromised_monitors,
        "unavailable_monitors": unavailable_monitors,
        "expected_final_decisions": expected_decisions,
    }