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


def main() -> None:
    monitor = BehaviorAnomalyMonitor(
        baseline_file=(
            PROJECT_ROOT
            / "data"
            / "behavior_baseline"
            / "normal_agent_behavior.csv"
        ),
        config_file=(
            PROJECT_ROOT
            / "config"
            / "behavior_monitor.json"
        ),
    )

    event = SecurityEvent(
        event_id="DEMO-BEHAVIOR-001",
        scenario_id="DEMO-BEHAVIOR",
        source_agent_id="complaint-agent-01",
        source_agent_role="Customer Complaint Agent",
        event_type=EventType.TOOL_REQUEST,
        content_summary=(
            "Application agent shows unusually high "
            "sensitive tool and database activity."
        ),
        requested_resource="customer_history",
        expected_decision=SecurityDecision.BLOCK,
        attack_type=AttackType.ABNORMAL_TOOL_USAGE,
        source_agent_state=AgentState.NORMAL,
        metadata={
            "synthetic": True,
            "behavior_features": {
                "tool_call_frequency": 45,
                "restricted_resource_attempts": 8,
                "failed_authorization_count": 7,
                "external_api_calls": 12,
                "database_query_count": 30,
                "sensitive_resource_attempts": 6,
            },
        },
    )

    result = monitor.evaluate(event)

    print(
        json.dumps(
            result.model_dump(mode="json"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
