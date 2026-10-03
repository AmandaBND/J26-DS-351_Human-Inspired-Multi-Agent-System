from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    NORMAL = "NORMAL"
    COMPROMISED = "COMPROMISED"
    UNAVAILABLE = "UNAVAILABLE"


class EventType(str, Enum):
    USER_INPUT = "USER_INPUT"
    AGENT_MESSAGE = "AGENT_MESSAGE"
    TOOL_REQUEST = "TOOL_REQUEST"
    RESOURCE_ACCESS = "RESOURCE_ACCESS"
    OUTPUT = "OUTPUT"


class AttackType(str, Enum):
    NONE = "NONE"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    MALICIOUS_INSTRUCTION = "MALICIOUS_INSTRUCTION"
    ABNORMAL_TOOL_USAGE = "ABNORMAL_TOOL_USAGE"
    FALSE_ALLOW = "FALSE_ALLOW"
    FALSE_BLOCK = "FALSE_BLOCK"
    MONITOR_COMPROMISE = "MONITOR_COMPROMISE"
    COLLUSION = "COLLUSION"


class SecurityDecision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REVIEW = "REVIEW"


class SecurityEvent(BaseModel):
    event_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    source_agent_id: str
    source_agent_role: str

    event_type: EventType

    content_summary: str

    requested_resource: str | None = None

    expected_decision: SecurityDecision

    attack_type: AttackType = AttackType.NONE

    source_agent_state: AgentState = AgentState.NORMAL

    metadata: dict[str, Any] = Field(default_factory=dict)


class MonitorDecision(BaseModel):
    decision_id: str
    event_id: str

    monitor_id: str

    monitor_state: AgentState = AgentState.NORMAL

    decision: SecurityDecision

    confidence: float = Field(ge=0.0, le=1.0)

    latency_ms: float = Field(ge=0.0)

    reason_codes: list[str] = Field(default_factory=list)