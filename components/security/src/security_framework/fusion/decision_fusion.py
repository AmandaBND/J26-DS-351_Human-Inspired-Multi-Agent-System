from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from security_framework.models import (
    SecurityDecision,
)


class FusionInput(BaseModel):
    monitor_id: str
    decision: SecurityDecision
    risk_score: float = Field(
        ge=0.0,
        le=1.0,
    )
    trust_score: float = Field(
        ge=0.0,
        le=1.0,
    )


class FusionResult(BaseModel):
    strategy: str
    decision: SecurityDecision
    final_risk: float = Field(
        ge=0.0,
        le=1.0,
    )
    contributions: dict[str, float] = Field(
        default_factory=dict
    )


class SecurityDecisionFusion:
    def __init__(
        self,
        *,
        review_threshold: float = 0.35,
        block_threshold: float = 0.70,
    ) -> None:
        if not (
            0.0
            <= review_threshold
            <= block_threshold
            <= 1.0
        ):
            raise ValueError(
                "Fusion thresholds must satisfy "
                "0 <= review <= block <= 1."
            )

        self.review_threshold = (
            review_threshold
        )
        self.block_threshold = (
            block_threshold
        )

    def _decision_from_risk(
        self,
        risk: float,
    ) -> SecurityDecision:
        if risk >= self.block_threshold:
            return SecurityDecision.BLOCK

        if risk >= self.review_threshold:
            return SecurityDecision.REVIEW

        return SecurityDecision.ALLOW

    def single_guard(
        self,
        inputs: list[FusionInput],
        *,
        guard_id: str,
    ) -> FusionResult:
        guard = next(
            (
                item
                for item in inputs
                if item.monitor_id == guard_id
            ),
            None,
        )

        if guard is None:
            return FusionResult(
                strategy="single_guard",
                decision=SecurityDecision.REVIEW,
                final_risk=0.50,
                contributions={},
            )

        return FusionResult(
            strategy="single_guard",
            decision=guard.decision,
            final_risk=guard.risk_score,
            contributions={
                guard.monitor_id: 1.0
            },
        )

    def equal_majority(
        self,
        inputs: list[FusionInput],
    ) -> FusionResult:
        if not inputs:
            return FusionResult(
                strategy="equal_majority",
                decision=SecurityDecision.REVIEW,
                final_risk=0.50,
                contributions={},
            )

        counts = Counter(
            item.decision
            for item in inputs
        )

        ranked = counts.most_common()

        if (
            len(ranked) > 1
            and ranked[0][1]
            == ranked[1][1]
        ):
            decision = (
                SecurityDecision.REVIEW
            )
        else:
            decision = ranked[0][0]

        final_risk = sum(
            item.risk_score
            for item in inputs
        ) / len(inputs)

        equal_weight = 1.0 / len(inputs)

        return FusionResult(
            strategy="equal_majority",
            decision=decision,
            final_risk=final_risk,
            contributions={
                item.monitor_id: (
                    equal_weight
                )
                for item in inputs
            },
        )

    def _weighted_risk(
        self,
        inputs: list[FusionInput],
        weights: dict[str, float],
        *,
        strategy: str,
    ) -> FusionResult:
        if not inputs:
            return FusionResult(
                strategy=strategy,
                decision=SecurityDecision.REVIEW,
                final_risk=0.50,
                contributions={},
            )

        raw_weights = {
            item.monitor_id: max(
                0.0,
                float(
                    weights.get(
                        item.monitor_id,
                        0.0,
                    )
                ),
            )
            for item in inputs
        }

        total = sum(
            raw_weights.values()
        )

        if total <= 0:
            return FusionResult(
                strategy=strategy,
                decision=SecurityDecision.REVIEW,
                final_risk=0.50,
                contributions={},
            )

        normalized = {
            monitor_id: weight / total
            for monitor_id, weight
            in raw_weights.items()
        }

        final_risk = sum(
            item.risk_score
            * normalized[
                item.monitor_id
            ]
            for item in inputs
        )

        return FusionResult(
            strategy=strategy,
            decision=(
                self._decision_from_risk(
                    final_risk
                )
            ),
            final_risk=final_risk,
            contributions=normalized,
        )

    def static_weighting(
        self,
        inputs: list[FusionInput],
        *,
        static_weights: dict[str, float],
    ) -> FusionResult:
        return self._weighted_risk(
            inputs,
            static_weights,
            strategy="static_weighting",
        )

    def adaptive_trust_weighting(
        self,
        inputs: list[FusionInput],
    ) -> FusionResult:
        trust_weights = {
            item.monitor_id: (
                item.trust_score
            )
            for item in inputs
        }

        return self._weighted_risk(
            inputs,
            trust_weights,
            strategy="adaptive_trust_weighting",
        )
