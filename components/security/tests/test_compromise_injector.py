import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.experiment import ControlledMonitorExecutor
from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    MonitorBehaviorMode,
    MonitorConfig,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import PolicyToolMonitor


def build_policy_monitor(tmp_path: Path) -> PolicyToolMonitor:
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "always_block_resources": ["credential_store"],
                "always_block_tools": [],
                "roles": {
                    "Customer Complaint Agent": {
                        "allowed_resources": ["complaint_records"],
                        "blocked_resources": ["full_customer_database"],
                        "allowed_tools": [],
                        "blocked_tools": [],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    return PolicyToolMonitor(policy_file)


def make_event(
    *,
    event_id: str = "EVT-1",
    resource: str = "full_customer_database",
    expected: SecurityDecision = SecurityDecision.BLOCK,
    attack: AttackType = AttackType.MALICIOUS_INSTRUCTION,
) -> SecurityEvent:
    return SecurityEvent(
        event_id=event_id,
        scenario_id="TEST-COMPROMISE",
        source_agent_id="complaint-agent",
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.RESOURCE_ACCESS,
        content_summary="Controlled compromise test.",
        requested_resource=resource,
        expected_decision=expected,
        attack_type=attack,
        source_agent_state=AgentState.NORMAL,
        metadata={"synthetic": True},
    )


def test_normal_mode_preserves_real_monitor_output(tmp_path: Path):
    monitor = build_policy_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-A",
            monitor_state=AgentState.NORMAL,
            behavior_mode=MonitorBehaviorMode.NORMAL,
        ),
    )
    result = executor.evaluate(make_event())

    assert result.monitor_id == "policy-A"
    assert result.decision == SecurityDecision.BLOCK


def test_false_allow_forces_wrong_allow(tmp_path: Path):
    monitor = build_policy_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-B",
            monitor_state=AgentState.COMPROMISED,
            behavior_mode=MonitorBehaviorMode.FALSE_ALLOW,
        ),
    )
    result = executor.evaluate(make_event())

    assert result.decision == SecurityDecision.ALLOW
    assert result.risk_score <= 0.10
    assert "monitor_state" not in result.metadata
    assert "behavior_mode" not in result.metadata


def test_intermittent_flip_is_reproducible(tmp_path: Path):
    monitor = build_policy_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-C",
            monitor_state=AgentState.COMPROMISED,
            behavior_mode=MonitorBehaviorMode.INTERMITTENT_FLIP,
        ),
        intermittent_every=2,
    )

    first = executor.evaluate(make_event(event_id="EVT-1"))
    second = executor.evaluate(make_event(event_id="EVT-2"))

    assert first.decision == SecurityDecision.BLOCK
    assert second.decision == SecurityDecision.ALLOW


def test_unavailable_monitor_returns_review(tmp_path: Path):
    monitor = build_policy_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-D",
            monitor_state=AgentState.UNAVAILABLE,
            behavior_mode=MonitorBehaviorMode.UNAVAILABLE,
        ),
    )
    result = executor.evaluate(make_event())

    assert result.decision == SecurityDecision.REVIEW
    assert result.confidence == 0.0
    assert "MONITOR_UNAVAILABLE" in result.reason_codes
