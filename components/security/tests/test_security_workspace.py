import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.models import (
    AttackType,
    EventType,
    MonitorBehaviorMode,
    SecurityDecision,
)
from security_framework.workspace import (
    SecurityWorkspaceDatabase,
    SecurityWorkspaceService,
)


def normal_behavior() -> dict[str, float]:
    return {
        "tool_call_frequency": 3,
        "restricted_resource_attempts": 0,
        "failed_authorization_count": 0,
        "external_api_calls": 1,
        "database_query_count": 2,
        "sensitive_resource_attempts": 0,
    }


def test_workspace_database_seeds_business_tables(tmp_path: Path):
    database = SecurityWorkspaceDatabase(tmp_path / "workspace.db")

    tables = database.list_tables()
    assert "complaint_records" in tables
    assert "credential_store" in tables

    complaints = database.fetch_resource("complaint_records")
    assert len(complaints) >= 1


def test_incoming_resource_request_uses_deterministic_policy_reference(tmp_path: Path):
    service = SecurityWorkspaceService(
        PROJECT_ROOT,
        db_path=tmp_path / "workspace.db",
    )

    event, verification_source = service.create_incoming_event(
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.RESOURCE_ACCESS,
        content_summary="Request complete customer database.",
        requested_resource="full_customer_database",
        tool_name=None,
        behavior_features=normal_behavior(),
        sample_attack_type=AttackType.NONE,
        sample_expected_decision=None,
    )

    assert event.expected_decision == SecurityDecision.BLOCK
    assert verification_source == "deterministic_policy"


def test_normal_integrity_check_passes_known_policy_cases(tmp_path: Path):
    service = SecurityWorkspaceService(
        PROJECT_ROOT,
        db_path=tmp_path / "workspace.db",
    )

    results = service.run_policy_challenge_suite(
        MonitorBehaviorMode.NORMAL
    )

    assert len(results) == 4
    assert int(results["correct"].sum()) == 4
    assert "trust" in results.columns
