import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import (
    BehaviorAnomalyMonitor,
)


FEATURES = [
    "tool_call_frequency",
    "restricted_resource_attempts",
    "failed_authorization_count",
    "external_api_calls",
    "database_query_count",
    "sensitive_resource_attempts",
]


def build_monitor(tmp_path: Path) -> BehaviorAnomalyMonitor:
    baseline = tmp_path / "baseline.csv"
    config = tmp_path / "config.json"

    with baseline.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=FEATURES,
        )
        writer.writeheader()

        for index in range(40):
            writer.writerow(
                {
                    "tool_call_frequency": 2 + (index % 4),
                    "restricted_resource_attempts": 0,
                    "failed_authorization_count": (
                        1 if index % 13 == 0 else 0
                    ),
                    "external_api_calls": index % 3,
                    "database_query_count": 1 + (index % 4),
                    "sensitive_resource_attempts": 0,
                }
            )

    config.write_text(
        json.dumps(
            {
                "feature_order": FEATURES,
                "n_estimators": 100,
                "contamination": "auto",
                "random_state": 42,
                "minimum_baseline_rows": 30,
                "review_threshold": 0.90,
                "block_threshold": 0.98,
            }
        ),
        encoding="utf-8",
    )

    return BehaviorAnomalyMonitor(
        baseline_file=baseline,
        config_file=config,
    )


def make_event(
    features: dict | None,
) -> SecurityEvent:
    metadata = {"synthetic": True}

    if features is not None:
        metadata["behavior_features"] = features

    return SecurityEvent(
        event_id="TEST-BEHAVIOR-001",
        scenario_id="TEST-BEHAVIOR",
        source_agent_id="agent-01",
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.TOOL_REQUEST,
        content_summary="Behavior monitor unit test.",
        requested_resource="customer_history",
        expected_decision=SecurityDecision.REVIEW,
        attack_type=AttackType.NONE,
        source_agent_state=AgentState.NORMAL,
        metadata=metadata,
    )


def test_behavior_monitor_accepts_normal_behavior(
    tmp_path: Path,
):
    monitor = build_monitor(tmp_path)

    event = make_event(
        {
            "tool_call_frequency": 3,
            "restricted_resource_attempts": 0,
            "failed_authorization_count": 0,
            "external_api_calls": 1,
            "database_query_count": 2,
            "sensitive_resource_attempts": 0,
        }
    )

    result = monitor.evaluate(event)

    assert result.risk_score < 0.98


def test_behavior_monitor_blocks_extreme_behavior(
    tmp_path: Path,
):
    monitor = build_monitor(tmp_path)

    event = make_event(
        {
            "tool_call_frequency": 50,
            "restricted_resource_attempts": 10,
            "failed_authorization_count": 8,
            "external_api_calls": 15,
            "database_query_count": 35,
            "sensitive_resource_attempts": 7,
        }
    )

    result = monitor.evaluate(event)

    assert result.decision == SecurityDecision.BLOCK
    assert result.risk_score >= 0.98


def test_behavior_monitor_reviews_missing_features(
    tmp_path: Path,
):
    monitor = build_monitor(tmp_path)

    event = make_event(None)

    result = monitor.evaluate(event)

    assert result.decision == SecurityDecision.REVIEW
    assert "MISSING_BEHAVIOR_FEATURES" in result.reason_codes
