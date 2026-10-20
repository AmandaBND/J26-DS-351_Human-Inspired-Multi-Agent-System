import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from security_framework.models import SecurityEvent, SecurityDecision, EventType
from security_framework.monitors import DataMinimizationMonitor, SemanticPromptMonitor


def monitor(selector=None):
    return DataMinimizationMonitor(
        ROOT / "config" / "data_minimization.json",
        ROOT / "config" / "policies.json",
        selector=selector,
    )


def event(role="Customer Complaint Agent", resource="customer_history", task="Find delayed printer service status"):
    return SecurityEvent(event_id="MINIM-TEST", scenario_id="MINIM",
        source_agent_id="agent-01", source_agent_role=role,
        event_type=EventType.RESOURCE_ACCESS, content_summary=task,
        requested_resource=resource, expected_decision=SecurityDecision.REVIEW)


def test_selected_fields_exclude_unnecessary_personal_data():
    result = monitor(lambda task, columns: ["product", "service_status"]).evaluate(event())
    assert result.decision == SecurityDecision.ALLOW
    assert result.monitor_id == "data-minimization-monitor"
    assert "product" in result.metadata["selected_fields"]
    assert "customer_name" not in result.metadata["selected_fields"]


def test_denies_out_of_role_table():
    result = monitor(lambda *_: []).evaluate(event(resource="employee_payroll"))
    assert result.decision == SecurityDecision.BLOCK
    assert result.metadata["selected_fields"] == []


def test_empty_selection_stays_in_review():
    result = monitor(lambda *_: []).evaluate(event(task="Please help."))
    assert result.decision == SecurityDecision.REVIEW


def test_column_projection_returns_no_customer_identifiers(tmp_path):
    from security_framework.workspace import SecurityWorkspaceDatabase
    db = SecurityWorkspaceDatabase(tmp_path / "test.db")
    fields = monitor(lambda *_: ["product", "service_status"]).evaluate(event()).metadata["selected_fields"]
    result = db.fetch_selected_resource("customer_history", fields)
    assert list(result.columns) == fields
    assert "customer_name" not in result.columns


def test_fake_llm_cannot_expand_selection():
    forged = monitor(lambda task, fields: ["customer_name", "admin_password"])
    result = forged.evaluate(event())
    assert result.decision == SecurityDecision.REVIEW
    assert result.metadata["selected_fields"] == []


def test_semantic_monitor_runs_independently():
    semantic = SemanticPromptMonitor(classifier=lambda *args, **kwargs: [{"label": "MALICIOUS", "score": 0.99}])
    result = semantic.evaluate(event())
    assert result.monitor_id == "semantic-monitor"
    assert result.decision == SecurityDecision.BLOCK


def test_ollama_unavailable_holds_data(monkeypatch):
    from security_framework.monitors import data_minimization_monitor as module
    def unavailable(*args, **kwargs):
        raise OSError("Local model unavailable")
    monkeypatch.setattr(module, "urlopen", unavailable)
    result = monitor().evaluate(event())
    assert result.decision == SecurityDecision.REVIEW
    assert "FIELD_SELECTOR_UNAVAILABLE" in result.reason_codes


def test_only_ollama_is_allowed(tmp_path):
    import json, pytest
    conf = json.loads((ROOT / "config/data_minimization.json").read_text())
    conf["selector"] = "rules"
    setting = tmp_path / "selector.json"
    setting.write_text(json.dumps(conf))
    with pytest.raises(ValueError, match="Ollama"):
        DataMinimizationMonitor(setting, ROOT / "config/policies.json")
