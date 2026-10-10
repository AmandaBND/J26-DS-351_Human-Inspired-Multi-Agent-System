import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.models import AgentState, AttackType, EventType, SecurityDecision, SecurityEvent
from security_framework.monitors import PolicyToolMonitor

POLICY_FILE = PROJECT_ROOT / "config" / "policies.json"


def make_event(event_id: str, event_type: EventType, resource: str) -> SecurityEvent:
    return SecurityEvent(event_id=event_id, scenario_id="TEST-POLICY", source_agent_id="complaint-agent-01", source_agent_role="Customer Complaint Agent", event_type=event_type, content_summary="Synthetic policy-monitor test event.", requested_resource=resource, expected_decision=SecurityDecision.REVIEW, attack_type=AttackType.NONE, source_agent_state=AgentState.NORMAL, metadata={"synthetic": True})


def test_policy_monitor_blocks_role_blocked_resource():
    monitor = PolicyToolMonitor(POLICY_FILE)
    result = monitor.evaluate(make_event("EVT-POLICY-1", EventType.RESOURCE_ACCESS, "full_customer_database"))
    assert result.decision == SecurityDecision.BLOCK
    assert result.risk_score >= 0.90
    assert "ROLE_BLOCKED_RESOURCE" in result.reason_codes


def test_policy_monitor_allows_role_allowed_resource():
    monitor = PolicyToolMonitor(POLICY_FILE)
    result = monitor.evaluate(make_event("EVT-POLICY-2", EventType.RESOURCE_ACCESS, "complaint_records"))
    assert result.decision == SecurityDecision.ALLOW
    assert result.risk_score <= 0.10


def test_policy_monitor_reviews_unknown_resource():
    monitor = PolicyToolMonitor(POLICY_FILE)
    result = monitor.evaluate(make_event("EVT-POLICY-3", EventType.RESOURCE_ACCESS, "new_unregistered_resource"))
    assert result.decision == SecurityDecision.REVIEW
