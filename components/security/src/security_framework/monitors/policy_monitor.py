from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Any

from security_framework.models import EventType, SecurityDecision, SecurityEvent
from security_framework.monitors.base import MonitorResult, MonitorType, SecurityMonitor


class PolicyToolMonitor(SecurityMonitor):
    """Deterministic policy and tool-access monitor."""

    def __init__(self, policy_file: str | Path, monitor_id: str = "policy-monitor") -> None:
        super().__init__(monitor_id=monitor_id, monitor_type=MonitorType.POLICY_TOOL)
        self.policy_file = Path(policy_file)
        self.policy = self._load_policy(self.policy_file)

    @staticmethod
    def _load_policy(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Policy file does not exist: {path}")
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if not isinstance(data, dict):
            raise ValueError("Policy configuration must be a JSON object.")
        return data

    @staticmethod
    def _normalize(value: str | None) -> str:
        return (value or "").strip().lower()

    def evaluate(self, event: SecurityEvent) -> MonitorResult:
        started_at = perf_counter()
        role_policy = self.policy.get("roles", {}).get(event.source_agent_role, {})

        if event.event_type == EventType.RESOURCE_ACCESS:
            return self._evaluate_resource_access(event, role_policy, started_at)

        if event.event_type == EventType.TOOL_REQUEST:
            return self._evaluate_tool_request(event, role_policy, started_at)

        return self._build_result(
            event=event,
            decision=SecurityDecision.ALLOW,
            risk_score=0.10,
            confidence=0.75,
            started_at=started_at,
            reason_codes=["NO_APPLICABLE_HARD_POLICY_VIOLATION"],
            metadata={"policy_file": str(self.policy_file)},
        )

    def _evaluate_resource_access(self, event: SecurityEvent, role_policy: dict[str, Any], started_at: float) -> MonitorResult:
        resource = self._normalize(event.requested_resource)
        if not resource:
            return self._build_result(event=event, decision=SecurityDecision.REVIEW, risk_score=0.60, confidence=0.90, started_at=started_at, reason_codes=["MISSING_RESOURCE_NAME"])

        always_block = {self._normalize(x) for x in self.policy.get("always_block_resources", [])}
        blocked = {self._normalize(x) for x in role_policy.get("blocked_resources", [])}
        allowed = {self._normalize(x) for x in role_policy.get("allowed_resources", [])}

        if resource in always_block:
            return self._build_result(event=event, decision=SecurityDecision.BLOCK, risk_score=1.00, confidence=1.00, started_at=started_at, reason_codes=["GLOBAL_BLOCKED_RESOURCE"], metadata={"resource": resource})
        if resource in blocked:
            return self._build_result(event=event, decision=SecurityDecision.BLOCK, risk_score=0.95, confidence=0.98, started_at=started_at, reason_codes=["ROLE_BLOCKED_RESOURCE"], metadata={"resource": resource})
        if resource in allowed:
            return self._build_result(event=event, decision=SecurityDecision.ALLOW, risk_score=0.05, confidence=0.98, started_at=started_at, reason_codes=["ROLE_ALLOWED_RESOURCE"], metadata={"resource": resource})

        return self._build_result(event=event, decision=SecurityDecision.REVIEW, risk_score=0.55, confidence=0.80, started_at=started_at, reason_codes=["RESOURCE_NOT_EXPLICITLY_LISTED"], metadata={"resource": resource})

    def _evaluate_tool_request(self, event: SecurityEvent, role_policy: dict[str, Any], started_at: float) -> MonitorResult:
        tool_name = self._normalize(event.metadata.get("tool_name") or event.requested_resource)
        if not tool_name:
            return self._build_result(event=event, decision=SecurityDecision.REVIEW, risk_score=0.60, confidence=0.90, started_at=started_at, reason_codes=["MISSING_TOOL_NAME"])

        always_block = {self._normalize(x) for x in self.policy.get("always_block_tools", [])}
        blocked = {self._normalize(x) for x in role_policy.get("blocked_tools", [])}
        allowed = {self._normalize(x) for x in role_policy.get("allowed_tools", [])}

        if tool_name in always_block:
            return self._build_result(event=event, decision=SecurityDecision.BLOCK, risk_score=1.00, confidence=1.00, started_at=started_at, reason_codes=["GLOBAL_BLOCKED_TOOL"], metadata={"tool_name": tool_name})
        if tool_name in blocked:
            return self._build_result(event=event, decision=SecurityDecision.BLOCK, risk_score=0.95, confidence=0.98, started_at=started_at, reason_codes=["ROLE_BLOCKED_TOOL"], metadata={"tool_name": tool_name})
        if tool_name in allowed:
            return self._build_result(event=event, decision=SecurityDecision.ALLOW, risk_score=0.05, confidence=0.98, started_at=started_at, reason_codes=["ROLE_ALLOWED_TOOL"], metadata={"tool_name": tool_name})

        return self._build_result(event=event, decision=SecurityDecision.REVIEW, risk_score=0.55, confidence=0.80, started_at=started_at, reason_codes=["TOOL_NOT_EXPLICITLY_LISTED"], metadata={"tool_name": tool_name})
