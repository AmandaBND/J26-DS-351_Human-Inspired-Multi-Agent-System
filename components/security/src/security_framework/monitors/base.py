from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from security_framework.models import SecurityDecision, SecurityEvent


class MonitorType(str, Enum):
    """Specialized role performed by a security monitor."""

    SEMANTIC_PROMPT = "SEMANTIC_PROMPT"
    POLICY_TOOL = "POLICY_TOOL"
    BEHAVIOR_ANOMALY = "BEHAVIOR_ANOMALY"


class MonitorResult(BaseModel):
    """Normalized output returned by every security monitor."""

    monitor_id: str = Field(min_length=1)
    monitor_type: MonitorType
    event_id: str = Field(min_length=1)
    decision: SecurityDecision
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    reason_codes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityMonitor(ABC):
    """Common interface for all security monitors."""

    def __init__(self, monitor_id: str, monitor_type: MonitorType) -> None:
        if not monitor_id.strip():
            raise ValueError("monitor_id must not be empty.")
        self.monitor_id = monitor_id
        self.monitor_type = monitor_type

    @abstractmethod
    def evaluate(self, event: SecurityEvent) -> MonitorResult:
        """Evaluate one security event."""

    def _build_result(
        self,
        *,
        event: SecurityEvent,
        decision: SecurityDecision,
        risk_score: float,
        confidence: float,
        started_at: float,
        reason_codes: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MonitorResult:
        latency_ms = (perf_counter() - started_at) * 1000.0
        return MonitorResult(
            monitor_id=self.monitor_id,
            monitor_type=self.monitor_type,
            event_id=event.event_id,
            decision=decision,
            risk_score=risk_score,
            confidence=confidence,
            latency_ms=latency_ms,
            reason_codes=reason_codes or [],
            metadata=metadata or {},
        )
