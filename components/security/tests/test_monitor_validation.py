import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("monitor_validation", ROOT / "scripts/validate_monitor_execution.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def test_fault_records_are_identified_as_simulated():
    original = [{"event_id": "case-01", "source": "public", "monitor_id": "semantic-monitor", "decision": "BLOCK"}]
    rows = mod.fault_replay(original)
    assert len(rows) == 3
    assert all(item["fault_label"] == 1 for item in rows)
    assert all(item["measurement_origin"] == "controlled_replay_of_real_monitor_output" for item in rows)
    assert sum(row["observable_change"] for row in rows) == 2


def test_fields_require_review():
    with (ROOT / "data/evaluation/field_necessity_tasks.csv").open(encoding="utf-8") as f:
        tasks = list(csv.DictReader(f))
    assert len(tasks) >= 12
    assert all(task["label_status"] == "UNREVIEWED" for task in tasks)
    assert all(not task["reviewer"] for task in tasks)
    assert all(not task["expected_necessary_fields"] for task in tasks)


def test_all_four_monitors_have_distinct_ids(tmp_path):
    from security_framework.workspace import SecurityWorkspaceService
    service = SecurityWorkspaceService(ROOT, db_path=tmp_path / "empty.db")
    assert list(service.monitors) == [
        "semantic-monitor", "data-minimization-monitor", "policy-monitor", "behavior-monitor"
    ]


def test_actual_monitor_results_are_recorded_with_sqlite_projection(tmp_path):
    from security_framework.models import SecurityDecision
    from security_framework.monitors import DataMinimizationMonitor
    from security_framework.workspace import SecurityWorkspaceDatabase
    settings = ROOT / "config/data_minimization.json"
    policy = ROOT / "config/policies.json"
    monitor = DataMinimizationMonitor(settings, policy, selector=lambda *_: ["product", "service_status"])
    tasks = mod.load_tasks(ROOT / "data/evaluation/field_necessity_tasks.csv", 1)
    item = list(mod.events(ROOT, 0, 0, tasks))[0]
    db = SecurityWorkspaceDatabase(tmp_path / "test.db")
    rows = mod.monitor_observations([monitor], [item], database=db)
    assert len(rows) == 1
    assert rows[0]["sqlite_projection_verified"] == "True"
    assert rows[0]["sqlite_result_columns"] == '["product", "service_status"]'


def test_legacy_minimization_records_migrate_without_deleting_history(tmp_path):
    from security_framework.workspace import SecurityWorkspaceDatabase
    db = SecurityWorkspaceDatabase(tmp_path / "historical.db")
    with db._connect() as connection:
        connection.execute(
            "INSERT INTO security_events (event_id,created_at,scenario_id,source_agent_id,"
            "source_agent_role,event_type,content_summary,expected_decision,attack_type) "
            "VALUES ('case','now','demo','agent','Customer Complaint Agent',"
            "'RESOURCE_ACCESS','test','REVIEW','NONE')"
        )
        connection.execute(
            "INSERT INTO monitor_results (event_id,created_at,monitor_id,monitor_type,decision,"
            "risk_score,confidence,latency_ms,reason_codes_json,metadata_json) "
            "VALUES ('case','now','semantic-monitor','DATA_MINIMIZATION',"
            "'REVIEW',0.6,0.5,1,'[]','{}')"
        )
    assert db.migrate_monitor_history(0.85, "ACTIVE") == 1
    assert db.migrate_monitor_history(0.85, "ACTIVE") == 0
    with db._connect() as connection:
        row = connection.execute(
            "SELECT monitor_id FROM monitor_results WHERE event_id='case'"
        ).fetchone()
    assert row[0] == "data-minimization-monitor"


def test_minimization_has_known_answer_challenges():
    from security_framework.attestation import load_challenge_bank
    from security_framework.models import SecurityDecision
    from security_framework.monitors import DataMinimizationMonitor, MonitorType
    monitor = DataMinimizationMonitor(
        ROOT / "config/data_minimization.json", ROOT / "config/policies.json"
    )
    cases = [c for c in load_challenge_bank(ROOT / "config/challenge_bank.json")
             if c.target_monitor_type == MonitorType.DATA_MINIMIZATION]
    assert len(cases) >= 2
    assert all(monitor.evaluate(c.event).decision == c.event.expected_decision for c in cases)
