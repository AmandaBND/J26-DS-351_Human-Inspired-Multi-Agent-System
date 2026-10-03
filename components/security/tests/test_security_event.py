import sys
from pathlib import Path

import pytest
from pydantic import ValidationError


PROJECT_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(PROJECT_SRC))


from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    MonitorDecision,
    SecurityDecision,
    SecurityEvent,
)


def test_create_normal_security_event():
    event = SecurityEvent(
        event_id="EVT-001",
        scenario_id="SCN-001",
        source_agent_id="complaint-agent-01",
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.RESOURCE_ACCESS,
        content_summary="Retrieve complaint history for an authorized case.",
        requested_resource="internal_complaint_history",
        expected_decision=SecurityDecision.ALLOW,
        attack_type=AttackType.NONE,
        source_agent_state=AgentState.NORMAL,
    )

    assert event.event_id == "EVT-001"
    assert event.expected_decision == SecurityDecision.ALLOW
    assert event.attack_type == AttackType.NONE
    assert event.source_agent_state == AgentState.NORMAL


def test_monitor_decision_confidence_validation():
    with pytest.raises(ValidationError):
        MonitorDecision(
            decision_id="DEC-001",
            event_id="EVT-001",
            monitor_id="monitor-A",
            monitor_state=AgentState.NORMAL,
            decision=SecurityDecision.ALLOW,
            confidence=1.5,
            latency_ms=10.0,
        )


def test_create_valid_monitor_decision():
    decision = MonitorDecision(
        decision_id="DEC-002",
        event_id="EVT-001",
        monitor_id="monitor-A",
        monitor_state=AgentState.NORMAL,
        decision=SecurityDecision.ALLOW,
        confidence=0.94,
        latency_ms=18.5,
        reason_codes=["AUTHORIZED_INTERNAL_ACCESS"],
    )

    assert decision.monitor_id == "monitor-A"
    assert decision.confidence == 0.94