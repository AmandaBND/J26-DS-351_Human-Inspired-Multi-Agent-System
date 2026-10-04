from enum import Enum

from pydantic import BaseModel, Field, model_validator

from security_framework.models.security_event import (
    AgentState,
    SecurityDecision,
    SecurityEvent,
)


class MonitorBehaviorMode(str, Enum):
    """
    Controlled behaviour assigned to a security monitor
    during an experiment.
    """

    NORMAL = "NORMAL"
    FALSE_ALLOW = "FALSE_ALLOW"
    FALSE_BLOCK = "FALSE_BLOCK"
    UNAVAILABLE = "UNAVAILABLE"


class MonitorConfig(BaseModel):
    """
    Ground-truth configuration of one security monitor
    inside a controlled experiment.
    """

    monitor_id: str = Field(min_length=1)

    monitor_state: AgentState = AgentState.NORMAL

    behavior_mode: MonitorBehaviorMode = (
        MonitorBehaviorMode.NORMAL
    )

    description: str = ""


class ExperimentScenario(BaseModel):
    """
    Complete controlled experiment.

    Contains:
    - one security-relevant event;
    - known monitor states;
    - known expected final decision.
    """

    scenario_id: str = Field(min_length=1)

    description: str

    security_event: SecurityEvent

    monitors: list[MonitorConfig]

    expected_final_decision: SecurityDecision

    @model_validator(mode="after")
    def validate_monitors(self):
        if len(self.monitors) == 0:
            raise ValueError(
                "An experiment must contain at least one security monitor."
            )

        monitor_ids = [
            monitor.monitor_id
            for monitor in self.monitors
        ]

        if len(monitor_ids) != len(set(monitor_ids)):
            raise ValueError(
                "Monitor IDs must be unique within an experiment."
            )

        return self