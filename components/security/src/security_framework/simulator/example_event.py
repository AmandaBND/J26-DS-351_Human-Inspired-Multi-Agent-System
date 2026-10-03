from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    SecurityDecision,
    SecurityEvent,
)


def create_example_event() -> SecurityEvent:
    return SecurityEvent(
        event_id="EVT-DEMO-001",
        scenario_id="SCN-DEMO-001",
        source_agent_id="employee-agent-01",
        source_agent_role="Employee Performance Agent",
        event_type=EventType.RESOURCE_ACCESS,
        content_summary=(
            "Request authorized employee KPI records "
            "for performance analysis."
        ),
        requested_resource="employee_kpi_database",
        expected_decision=SecurityDecision.ALLOW,
        attack_type=AttackType.NONE,
        source_agent_state=AgentState.NORMAL,
        metadata={
            "department": "after_sales",
            "environment": "controlled_experiment",
        },
    )


if __name__ == "__main__":
    event = create_example_event()

    print(event.model_dump_json(indent=2))