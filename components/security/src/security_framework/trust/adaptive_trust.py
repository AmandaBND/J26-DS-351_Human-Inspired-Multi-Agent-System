from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class TrustStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REDUCED = "REDUCED"
    REVIEW = "REVIEW"
    ISOLATE = "ISOLATE"


class TrustUpdate(BaseModel):
    monitor_id: str
    previous_trust: float = Field(ge=0, le=1)
    raw_reliability: float = Field(ge=0, le=1)
    current_trust: float = Field(ge=0, le=1)
    status: TrustStatus
    severe_violation: bool = False


class AdaptiveTrustEstimator:
    def __init__(self, *, initial_trust=0.85, alpha=0.7,
                 active_threshold=0.7, reduced_threshold=0.5,
                 review_threshold=0.3, severe_violation_cap=0.15):
        for name, value in locals().copy().items():
            if name not in {"self", "__class__"} and not 0 <= value <= 1:
                raise ValueError(f"{name} must be in [0, 1]")
        if not active_threshold >= reduced_threshold >= review_threshold:
            raise ValueError("Trust thresholds are inconsistent")
        self.initial_trust = initial_trust
        self.alpha = alpha
        self.active_threshold = active_threshold
        self.reduced_threshold = reduced_threshold
        self.review_threshold = review_threshold
        self.severe_violation_cap = severe_violation_cap
        self._trust = {}

    def get_trust(self, monitor_id):
        return self._trust.get(monitor_id, self.initial_trust)

    def _status(self, trust):
        if trust >= self.active_threshold:
            return TrustStatus.ACTIVE
        if trust >= self.reduced_threshold:
            return TrustStatus.REDUCED
        if trust >= self.review_threshold:
            return TrustStatus.REVIEW
        return TrustStatus.ISOLATE

    def _raw_reliability(self, *, p_compromised=None, challenge_accuracy=None,
                         policy_violation_rate=None):
        signals = []
        for value in (p_compromised, challenge_accuracy, policy_violation_rate):
            if value is not None and not 0 <= value <= 1:
                raise ValueError("Evidence values must be in [0, 1]")
        if p_compromised is not None:
            signals.append(1 - p_compromised)
        if challenge_accuracy is not None:
            signals.append(challenge_accuracy)
        if policy_violation_rate is not None:
            signals.append(1 - policy_violation_rate)
        return min(signals) if signals else None

    def update(self, *, monitor_id, p_compromised=None, challenge_accuracy=None,
               policy_violation_rate=None, severe_violation=False):
        previous = self.get_trust(monitor_id)
        raw = self._raw_reliability(p_compromised=p_compromised,
            challenge_accuracy=challenge_accuracy,
            policy_violation_rate=policy_violation_rate)
        current = previous if raw is None else self.alpha * previous + (1-self.alpha) * raw
        if severe_violation:
            current = min(current, self.severe_violation_cap)
        self._trust[monitor_id] = current
        return TrustUpdate(monitor_id=monitor_id, previous_trust=previous,
            raw_reliability=previous if raw is None else raw,
            current_trust=current, status=self._status(current),
            severe_violation=severe_violation)
