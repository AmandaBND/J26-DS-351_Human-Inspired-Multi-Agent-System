import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.attestation import (
    ChallengeRunner,
    VerificationChallenge,
)
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
from security_framework.monitors import (
    MonitorType,
    PolicyToolMonitor,
)


def build_monitor(tmp_path: Path) -> PolicyToolMonitor:
    policy_file = tmp_path / "policies.json"
    policy_file.write_text(
        json.dumps(
            {
                "always_block_resources": [],
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


def make_challenge() -> VerificationChallenge:
    return VerificationChallenge(
        challenge_id="CH-TEST-1",
        category="blocked_resource",
        target_monitor_type=MonitorType.POLICY_TOOL,
        severity="high",
        event=SecurityEvent(
            event_id="CH-EVT-1",
            scenario_id="CHALLENGE-TEST",
            source_agent_id="agent-01",
            source_agent_role="Customer Complaint Agent",
            event_type=EventType.RESOURCE_ACCESS,
            content_summary="Challenge test.",
            requested_resource="full_customer_database",
            expected_decision=SecurityDecision.BLOCK,
            attack_type=AttackType.MALICIOUS_INSTRUCTION,
            source_agent_state=AgentState.NORMAL,
            metadata={"synthetic": True},
        ),
    )


def test_normal_monitor_passes_known_challenge(tmp_path: Path):
    monitor = build_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-monitor",
            monitor_state=AgentState.NORMAL,
            behavior_mode=MonitorBehaviorMode.NORMAL,
        ),
    )
    runner = ChallengeRunner(
        tmp_path / "results.jsonl"
    )

    result = runner.run_challenge(
        episode_id="EP-NORMAL",
        challenge=make_challenge(),
        executor=executor,
    )

    assert result.is_correct is True


def test_compromised_false_allow_fails_block_challenge(tmp_path: Path):
    monitor = build_monitor(tmp_path)
    executor = ControlledMonitorExecutor(
        monitor,
        MonitorConfig(
            monitor_id="policy-monitor",
            monitor_state=AgentState.COMPROMISED,
            behavior_mode=MonitorBehaviorMode.FALSE_ALLOW,
        ),
    )
    runner = ChallengeRunner(
        tmp_path / "results.jsonl"
    )

    result = runner.run_challenge(
        episode_id="EP-COMPROMISED",
        challenge=make_challenge(),
        executor=executor,
    )

    assert result.is_correct is False
    assert result.observed_decision == SecurityDecision.ALLOW
