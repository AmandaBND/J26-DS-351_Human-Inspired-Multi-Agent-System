import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.fusion import (
    FusionInput,
    SecurityDecisionFusion,
)
from security_framework.models import (
    SecurityDecision,
)


def compromised_majority_inputs():
    return [
        FusionInput(
            monitor_id="semantic-monitor",
            decision=SecurityDecision.ALLOW,
            risk_score=0.08,
            trust_score=0.18,
        ),
        FusionInput(
            monitor_id="policy-monitor",
            decision=SecurityDecision.BLOCK,
            risk_score=0.96,
            trust_score=0.95,
        ),
        FusionInput(
            monitor_id="behavior-monitor",
            decision=SecurityDecision.ALLOW,
            risk_score=0.12,
            trust_score=0.20,
        ),
    ]


def test_equal_majority_can_allow_two_bad_votes():
    fusion = SecurityDecisionFusion(
        review_threshold=0.35,
        block_threshold=0.70,
    )

    result = fusion.equal_majority(
        compromised_majority_inputs()
    )

    assert result.decision == SecurityDecision.ALLOW


def test_adaptive_trust_can_reduce_bad_monitor_influence():
    fusion = SecurityDecisionFusion(
        review_threshold=0.35,
        block_threshold=0.70,
    )

    result = (
        fusion.adaptive_trust_weighting(
            compromised_majority_inputs()
        )
    )

    assert result.decision == SecurityDecision.BLOCK
    assert result.final_risk >= 0.70


def test_zero_weight_fails_to_review():
    fusion = SecurityDecisionFusion()

    inputs = [
        FusionInput(
            monitor_id="A",
            decision=SecurityDecision.ALLOW,
            risk_score=0.1,
            trust_score=0.0,
        )
    ]

    result = (
        fusion.adaptive_trust_weighting(
            inputs
        )
    )

    assert result.decision == SecurityDecision.REVIEW
