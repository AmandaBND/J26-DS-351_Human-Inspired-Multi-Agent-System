import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.attestation import ChallengeResult
from security_framework.features import (
    MonitorReliabilityFeatureExtractor,
)
from security_framework.history import (
    MonitorDecisionLogRecord,
)
from security_framework.models import (
    AgentState,
    SecurityDecision,
)
from security_framework.monitors import MonitorType


def record(
    *,
    event_id: str,
    decision: SecurityDecision,
    expected: SecurityDecision,
    state: AgentState,
    risk: float,
) -> MonitorDecisionLogRecord:
    return MonitorDecisionLogRecord(
        logged_at=datetime.now(timezone.utc),
        episode_id="EP-TEST",
        scenario_id="SCN-TEST",
        event_id=event_id,
        monitor_id="policy-monitor",
        monitor_type="POLICY_TOOL",
        monitor_decision=decision,
        risk_score=risk,
        confidence=0.95,
        latency_ms=1.0,
        expected_event_decision=expected,
        attack_type="MALICIOUS_INSTRUCTION",
        experimental_monitor_state=state,
        experimental_behavior_mode="FALSE_ALLOW",
        reason_codes=[],
        source_dataset="unit_test",
        provenance={
            "verification_source": "deterministic_policy"
        },
    )


def test_extracts_expected_reliability_features():
    decisions = [
        record(
            event_id="E1",
            decision=SecurityDecision.ALLOW,
            expected=SecurityDecision.BLOCK,
            state=AgentState.COMPROMISED,
            risk=0.05,
        ),
        record(
            event_id="E2",
            decision=SecurityDecision.ALLOW,
            expected=SecurityDecision.BLOCK,
            state=AgentState.COMPROMISED,
            risk=0.05,
        ),
        record(
            event_id="E3",
            decision=SecurityDecision.ALLOW,
            expected=SecurityDecision.ALLOW,
            state=AgentState.COMPROMISED,
            risk=0.05,
        ),
    ]

    challenges = [
        ChallengeResult(
            episode_id="EP-TEST",
            challenge_id="CH1",
            category="blocked_resource",
            monitor_id="policy-monitor",
            monitor_type=MonitorType.POLICY_TOOL,
            expected_decision=SecurityDecision.BLOCK,
            observed_decision=SecurityDecision.ALLOW,
            is_correct=False,
            risk_score=0.05,
            confidence=0.95,
            latency_ms=1.0,
            experimental_monitor_state=AgentState.COMPROMISED,
            experimental_behavior_mode="FALSE_ALLOW",
        ),
        ChallengeResult(
            episode_id="EP-TEST",
            challenge_id="CH2",
            category="allowed_resource",
            monitor_id="policy-monitor",
            monitor_type=MonitorType.POLICY_TOOL,
            expected_decision=SecurityDecision.ALLOW,
            observed_decision=SecurityDecision.ALLOW,
            is_correct=True,
            risk_score=0.05,
            confidence=0.95,
            latency_ms=1.0,
            experimental_monitor_state=AgentState.COMPROMISED,
            experimental_behavior_mode="FALSE_ALLOW",
        ),
    ]

    extractor = MonitorReliabilityFeatureExtractor(
        decisions,
        challenges,
    )

    rows = extractor.extract()

    assert len(rows) == 1

    row = rows[0]

    assert row.challenge_accuracy == 0.5
    assert row.verified_decision_accuracy == (1 / 3)
    assert row.false_allow_rate == 1.0
    assert row.policy_violation_rate == (2 / 3)
    assert row.compromised_label == 1
    assert row.label_state == "COMPROMISED"
