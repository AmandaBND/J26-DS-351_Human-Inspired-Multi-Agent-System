from __future__ import annotations

from time import perf_counter

from security_framework.models import (
    AgentState,
    AttackType,
    MonitorBehaviorMode,
    MonitorConfig,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import (
    MonitorResult,
    SecurityMonitor,
)


class ControlledMonitorExecutor:
    """
    Controlled research harness for security-monitor compromise.

    This simulates known compromise conditions so the experiment has
    ground truth. It does NOT hack a real host or model.
    """

    def __init__(
        self,
        monitor: SecurityMonitor,
        config: MonitorConfig,
        *,
        intermittent_every: int = 3,
    ) -> None:
        if intermittent_every < 2:
            raise ValueError("intermittent_every must be at least 2.")

        self.monitor = monitor
        self.config = config
        self.intermittent_every = intermittent_every
        self._call_count = 0

    @staticmethod
    def _forced_reason(
        decision: SecurityDecision,
    ) -> list[str]:
        if decision == SecurityDecision.ALLOW:
            return ["EVENT_ASSESSED_LOW_RISK"]
        if decision == SecurityDecision.BLOCK:
            return ["EVENT_ASSESSED_HIGH_RISK"]
        return ["EVENT_REQUIRES_REVIEW"]

    def _copy_result(
        self,
        result: MonitorResult,
        *,
        decision: SecurityDecision | None = None,
        risk_score: float | None = None,
        confidence: float | None = None,
        reason_codes: list[str] | None = None,
    ) -> MonitorResult:
        return MonitorResult(
            monitor_id=self.config.monitor_id,
            monitor_type=result.monitor_type,
            event_id=result.event_id,
            decision=decision or result.decision,
            risk_score=(
                result.risk_score
                if risk_score is None
                else risk_score
            ),
            confidence=(
                result.confidence
                if confidence is None
                else confidence
            ),
            latency_ms=result.latency_ms,
            reason_codes=(
                result.reason_codes
                if reason_codes is None
                else reason_codes
            ),
            metadata=dict(result.metadata),
        )

    def _force_decision(
        self,
        result: MonitorResult,
        decision: SecurityDecision,
    ) -> MonitorResult:
        if decision == SecurityDecision.ALLOW:
            risk = 0.05
        elif decision == SecurityDecision.BLOCK:
            risk = 0.95
        else:
            risk = 0.50

        return self._copy_result(
            result,
            decision=decision,
            risk_score=risk,
            confidence=0.95,
            reason_codes=self._forced_reason(decision),
        )

    @staticmethod
    def _wrong_decision(
        expected: SecurityDecision,
    ) -> SecurityDecision:
        if expected == SecurityDecision.BLOCK:
            return SecurityDecision.ALLOW
        if expected == SecurityDecision.ALLOW:
            return SecurityDecision.BLOCK
        return SecurityDecision.ALLOW

    def _unavailable_result(
        self,
        event: SecurityEvent,
    ) -> MonitorResult:
        started_at = perf_counter()
        latency_ms = (perf_counter() - started_at) * 1000.0

        return MonitorResult(
            monitor_id=self.config.monitor_id,
            monitor_type=self.monitor.monitor_type,
            event_id=event.event_id,
            decision=SecurityDecision.REVIEW,
            risk_score=0.50,
            confidence=0.0,
            latency_ms=latency_ms,
            reason_codes=["MONITOR_UNAVAILABLE"],
            metadata={},
        )

    def evaluate(
        self,
        event: SecurityEvent,
    ) -> MonitorResult:
        self._call_count += 1

        mode = self.config.behavior_mode
        state = self.config.monitor_state

        if (
            state == AgentState.UNAVAILABLE
            or mode == MonitorBehaviorMode.UNAVAILABLE
        ):
            return self._unavailable_result(event)

        raw_result = self.monitor.evaluate(event)

        if mode in {
            MonitorBehaviorMode.NORMAL,
            MonitorBehaviorMode.RECOVERED,
        }:
            return self._copy_result(raw_result)

        if mode == MonitorBehaviorMode.FALSE_ALLOW:
            return self._force_decision(
                raw_result,
                SecurityDecision.ALLOW,
            )

        if mode == MonitorBehaviorMode.FALSE_BLOCK:
            return self._force_decision(
                raw_result,
                SecurityDecision.BLOCK,
            )

        if mode == MonitorBehaviorMode.SELECTIVE_FALSE_ALLOW:
            if (
                event.expected_decision
                == SecurityDecision.BLOCK
                and event.attack_type != AttackType.NONE
            ):
                return self._force_decision(
                    raw_result,
                    SecurityDecision.ALLOW,
                )
            return self._copy_result(raw_result)

        if mode == MonitorBehaviorMode.INTERMITTENT_FLIP:
            if self._call_count % self.intermittent_every == 0:
                return self._force_decision(
                    raw_result,
                    self._wrong_decision(
                        event.expected_decision
                    ),
                )
            return self._copy_result(raw_result)

        if mode == MonitorBehaviorMode.PROMPT_MANIPULATED:
            if event.attack_type == AttackType.PROMPT_INJECTION:
                return self._force_decision(
                    raw_result,
                    SecurityDecision.ALLOW,
                )
            return self._copy_result(raw_result)

        if mode == MonitorBehaviorMode.COLLUDING:
            return self._force_decision(
                raw_result,
                self._wrong_decision(
                    event.expected_decision
                ),
            )

        raise ValueError(
            f"Unsupported monitor behavior mode: {mode}"
        )
