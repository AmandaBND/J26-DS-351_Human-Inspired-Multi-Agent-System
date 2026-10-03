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
    AttackType,
    SecurityDecision,
)

from security_framework.simulator.scenario_loader import (
    load_scenarios,
    summarize_scenarios,
)


SCENARIO_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw_scenarios"
    / "normal_scenarios.json"
)


def test_load_normal_scenarios():
    scenarios = load_scenarios(
        SCENARIO_FILE
    )

    assert len(scenarios) == 8


def test_normal_scenarios_have_no_attack():
    scenarios = load_scenarios(
        SCENARIO_FILE
    )

    for scenario in scenarios:
        assert (
            scenario.attack_type
            == AttackType.NONE
        )

        assert (
            scenario.source_agent_state
            == AgentState.NORMAL
        )


def test_normal_scenarios_expected_allow():
    scenarios = load_scenarios(
        SCENARIO_FILE
    )

    for scenario in scenarios:
        assert (
            scenario.expected_decision
            == SecurityDecision.ALLOW
        )


def test_scenario_summary():
    scenarios = load_scenarios(
        SCENARIO_FILE
    )

    summary = summarize_scenarios(
        scenarios
    )

    assert (
        summary["total_scenarios"]
        == 8
    )

    assert (
        summary["expected_decisions"]["ALLOW"]
        == 8
    )