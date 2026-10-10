import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.history import (
    MonitorDecisionLogger,
)
from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import (
    MonitorResult,
    MonitorType,
)


def test_decision_logger_writes_and_reads_jsonl(
    tmp_path: Path,
):
    output = tmp_path / "decisions.jsonl"
    logger = MonitorDecisionLogger(output)

    event = SecurityEvent(
        event_id="EVT-LOG-1",
        scenario_id="SCN-LOG",
        source_agent_id="agent-01",
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.RESOURCE_ACCESS,
        content_summary="Logger test event.",
        requested_resource="credential_store",
        expected_decision=SecurityDecision.BLOCK,
        attack_type=AttackType.MALICIOUS_INSTRUCTION,
        source_agent_state=AgentState.NORMAL,
        metadata={
            "synthetic": True,
            "dataset_source": "unit_test",
        },
    )

    result = MonitorResult(
        monitor_id="policy-monitor",
        monitor_type=MonitorType.POLICY_TOOL,
        event_id=event.event_id,
        decision=SecurityDecision.BLOCK,
        risk_score=1.0,
        confidence=1.0,
        latency_ms=0.5,
        reason_codes=["GLOBAL_BLOCKED_RESOURCE"],
    )

    logger.log(
        episode_id="EP-001",
        event=event,
        result=result,
        experimental_monitor_state=AgentState.NORMAL,
        experimental_behavior_mode="NORMAL",
    )

    records = logger.read_all()

    assert len(records) == 1
    assert records[0].event_id == "EVT-LOG-1"
    assert records[0].monitor_id == "policy-monitor"
    assert records[0].source_dataset == "unit_test"


def test_decision_logger_exports_csv(
    tmp_path: Path,
):
    output = tmp_path / "decisions.jsonl"
    csv_output = tmp_path / "decisions.csv"

    logger = MonitorDecisionLogger(output)

    event = SecurityEvent(
        event_id="EVT-LOG-2",
        scenario_id="SCN-LOG",
        source_agent_id="agent-01",
        source_agent_role="Employee Performance Agent",
        event_type=EventType.OUTPUT,
        content_summary="Logger CSV test.",
        expected_decision=SecurityDecision.ALLOW,
        attack_type=AttackType.NONE,
        source_agent_state=AgentState.NORMAL,
        metadata={"synthetic": True},
    )

    result = MonitorResult(
        monitor_id="semantic-monitor",
        monitor_type=MonitorType.SEMANTIC_PROMPT,
        event_id=event.event_id,
        decision=SecurityDecision.ALLOW,
        risk_score=0.03,
        confidence=0.97,
        latency_ms=4.0,
    )

    logger.log(
        episode_id="EP-002",
        event=event,
        result=result,
    )

    exported = logger.export_csv(csv_output)

    assert exported.exists()
    assert "EVT-LOG-2" in exported.read_text(
        encoding="utf-8"
    )
