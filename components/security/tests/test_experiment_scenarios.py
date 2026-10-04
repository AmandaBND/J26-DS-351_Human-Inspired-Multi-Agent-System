import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from security_framework.models import (
    AgentState,
    MonitorBehaviorMode,
    SecurityDecision,
)

from security_framework.simulator.scenario_loader import (
    load_experiment_scenarios,
    summarize_experiment_scenarios,
)


SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw_scenarios"
    / "compromised_monitor_scenarios.json"
)


def test_load_compromised_scenarios():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    assert len(scenarios) == 5


def test_each_scenario_has_three_monitors():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    for scenario in scenarios:
        assert len(scenario.monitors) == 3


def test_dataset_contains_compromised_monitor():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    compromised_found = False

    for scenario in scenarios:
        for monitor in scenario.monitors:
            if (
                monitor.monitor_state
                == AgentState.COMPROMISED
            ):
                compromised_found = True

    assert compromised_found is True


def test_false_allow_condition_exists():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    found = any(
        monitor.behavior_mode
        == MonitorBehaviorMode.FALSE_ALLOW
        for scenario in scenarios
        for monitor in scenario.monitors
    )

    assert found is True


def test_false_block_condition_exists():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    found = any(
        monitor.behavior_mode
        == MonitorBehaviorMode.FALSE_BLOCK
        for scenario in scenarios
        for monitor in scenario.monitors
    )

    assert found is True


def test_majority_failure_scenario_exists():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    scenario = next(
        item
        for item in scenarios
        if item.scenario_id
        == "EXP-COMP-004"
    )

    compromised_count = sum(
        monitor.monitor_state
        == AgentState.COMPROMISED
        for monitor in scenario.monitors
    )

    assert compromised_count == 2

    assert (
        scenario.expected_final_decision
        == SecurityDecision.BLOCK
    )


def test_experiment_summary():
    scenarios = load_experiment_scenarios(
        SCENARIO_FILE
    )

    summary = summarize_experiment_scenarios(
        scenarios
    )

    assert summary["total_scenarios"] == 5

    assert (
        summary["compromised_monitors"]
        == 5
    )

    assert (
        summary["unavailable_monitors"]
        == 1
    )