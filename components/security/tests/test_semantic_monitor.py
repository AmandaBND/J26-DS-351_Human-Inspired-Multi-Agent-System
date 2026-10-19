import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from security_framework.models import SecurityEvent, SecurityDecision, EventType
from security_framework.monitors import DataMinimizationMonitor


def monitor():
    return DataMinimizationMonitor(ROOT / "config" / "data_minimization.json", ROOT / "config" / "policies.json")


def event(role="Customer Complaint Agent", resource="customer_history", task="Find delayed printer service status"):
    return SecurityEvent(event_id="MINIM-TEST", scenario_id="MINIM",
        source_agent_id="agent-01", source_agent_role=role,
        event_type=EventType.RESOURCE_ACCESS, content_summary=task,
        requested_resource=resource, expected_decision=SecurityDecision.REVIEW)


def test_selected_fields_exclude_unnecessary_personal_data():
    result = monitor().evaluate(event())
    assert result.decision == SecurityDecision.ALLOW
    assert "product" in result.metadata["selected_fields"]
    assert "customer_name" not in result.metadata["selected_fields"]


def test_denies_out_of_role_table():
    result = monitor().evaluate(event(resource="employee_payroll"))
    assert result.decision == SecurityDecision.BLOCK
    assert result.metadata["selected_fields"] == []


def test_unknown_task_stays_in_review():
    result = monitor().evaluate(event(task="Please help."))
    assert result.decision == SecurityDecision.REVIEW


def test_column_projection_returns_no_customer_identifiers(tmp_path):
    from security_framework.workspace import SecurityWorkspaceDatabase
    db = SecurityWorkspaceDatabase(tmp_path / "test.db")
    fields = monitor().evaluate(event()).metadata["selected_fields"]
    result = db.fetch_selected_resource("customer_history", fields)
    assert list(result.columns) == fields
    assert "customer_name" not in result.columns


def test_fake_llm_cannot_expand_selection():
    forged = DataMinimizationMonitor(
        ROOT / "config" / "data_minimization.json",
        ROOT / "config" / "policies.json",
        selector=lambda task, fields: ["customer_name", "admin_password"],
    )
    result = forged.evaluate(event())
    assert result.decision == SecurityDecision.REVIEW
    assert result.metadata["selected_fields"] == []
