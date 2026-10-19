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
    previous_trust: float = Field(
        ge=0.0,
        le=1.0,
    )
    raw_reliability: float = Field(
        ge=0.0,
        le=1.0,
    )
    current_trust: float = Field(
        ge=0.0,
        le=1.0,
    )
    status: TrustStatus
    severe_violation: bool = False


class AdaptiveTrustEstimator:
    """
    Temporal trust estimator for security monitors.

    Inputs:
    - ML model estimate P(compromised)
    - known-answer challenge accuracy
    - deterministic policy integrity

    The hidden experiment ground-truth monitor state is never used here.
    """

    def __init__(
        self,
        *,
        initial_trust: float = 0.85,
        alpha: float = 0.70,
        model_weight: float = 0.50,
        challenge_weight: float = 0.30,
        policy_weight: float = 0.20,
        active_threshold: float = 0.70,
        reduced_threshold: float = 0.50,
        review_threshold: float = 0.30,
        severe_violation_cap: float = 0.15,
    ) -> None:
        for value, name in [
            (initial_trust, "initial_trust"),
            (alpha, "alpha"),
            (model_weight, "model_weight"),
            (challenge_weight, "challenge_weight"),
            (policy_weight, "policy_weight"),
            (active_threshold, "active_threshold"),
            (reduced_threshold, "reduced_threshold"),
            (review_threshold, "review_threshold"),
            (
                severe_violation_cap,
                "severe_violation_cap",
            ),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{name} must be between 0 and 1."
                )

        if not (
            active_threshold
            >= reduced_threshold
            >= review_threshold
        ):
            raise ValueError(
                "Trust thresholds must satisfy "
                "active >= reduced >= review."
            )

        self.initial_trust = initial_trust
        self.alpha = alpha

        self.weights = {
            "model_reliability": model_weight,
            "challenge_accuracy": challenge_weight,
            "policy_integrity": policy_weight,
        }

        self.active_threshold = active_threshold
        self.reduced_threshold = reduced_threshold
        self.review_threshold = review_threshold
        self.severe_violation_cap = (
            severe_violation_cap
        )

        self._trust: dict[str, float] = {}

    def get_trust(
        self,
        monitor_id: str,
    ) -> float:
        return self._trust.get(
            monitor_id,
            self.initial_trust,
        )

    def _status(
        self,
        trust: float,
    ) -> TrustStatus:
        if trust >= self.active_threshold:
            return TrustStatus.ACTIVE

        if trust >= self.reduced_threshold:
            return TrustStatus.REDUCED

        if trust >= self.review_threshold:
            return TrustStatus.REVIEW

        return TrustStatus.ISOLATE

    def _raw_reliability(
        self,
        *,
        p_compromised: float,
        challenge_accuracy: float | None,
        policy_violation_rate: float | None,
    ) -> float:
        if not 0.0 <= p_compromised <= 1.0:
            raise ValueError(
                "p_compromised must be between 0 and 1."
            )

        evidence: list[
            tuple[float, float]
        ] = [
            (
                1.0 - p_compromised,
                self.weights[
                    "model_reliability"
                ],
            )
        ]

        if challenge_accuracy is not None:
            if not 0.0 <= challenge_accuracy <= 1.0:
                raise ValueError(
                    "challenge_accuracy must be "
                    "between 0 and 1."
                )

            evidence.append(
                (
                    challenge_accuracy,
                    self.weights[
                        "challenge_accuracy"
                    ],
                )
            )

        if policy_violation_rate is not None:
            if not 0.0 <= policy_violation_rate <= 1.0:
                raise ValueError(
                    "policy_violation_rate must be "
                    "between 0 and 1."
                )

            evidence.append(
                (
                    1.0 - policy_violation_rate,
                    self.weights[
                        "policy_integrity"
                    ],
                )
            )

        total_weight = sum(
            weight
            for _, weight in evidence
        )

        if total_weight == 0:
            return 1.0 - p_compromised

        raw = sum(
            value * weight
            for value, weight in evidence
        ) / total_weight

        return max(
            0.0,
            min(1.0, raw),
        )

    def update(
        self,
        *,
        monitor_id: str,
        p_compromised: float,
        challenge_accuracy: float | None = None,
        policy_violation_rate: float | None = None,
        severe_violation: bool = False,
    ) -> TrustUpdate:
        previous = self.get_trust(
            monitor_id
        )

        raw = self._raw_reliability(
            p_compromised=p_compromised,
            challenge_accuracy=challenge_accuracy,
            policy_violation_rate=(
                policy_violation_rate
            ),
        )

        current = (
            self.alpha * previous
            + (1.0 - self.alpha) * raw
        )

        if severe_violation:
            current = min(
                current,
                self.severe_violation_cap,
            )

        current = max(
            0.0,
            min(1.0, current),
        )

        self._trust[
            monitor_id
        ] = current

        return TrustUpdate(
            monitor_id=monitor_id,
            previous_trust=previous,
            raw_reliability=raw,
            current_trust=current,
            status=self._status(current),
            severe_violation=severe_violation,
        )
