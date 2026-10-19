import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.trust import (
    AdaptiveTrustEstimator,
    TrustStatus,
)


def test_trust_drops_under_sustained_bad_evidence():
    estimator = AdaptiveTrustEstimator(
        initial_trust=0.9,
        alpha=0.5,
    )

    first = estimator.update(
        monitor_id="monitor-A",
        p_compromised=0.1,
        challenge_accuracy=1.0,
        policy_violation_rate=0.0,
    )

    bad = None

    for _ in range(5):
        bad = estimator.update(
            monitor_id="monitor-A",
            p_compromised=0.95,
            challenge_accuracy=0.1,
            policy_violation_rate=0.9,
        )

    assert bad is not None
    assert (
        bad.current_trust
        < first.current_trust
    )


def test_trust_recovers_after_good_evidence_returns():
    estimator = AdaptiveTrustEstimator(
        initial_trust=0.9,
        alpha=0.5,
    )

    for _ in range(5):
        estimator.update(
            monitor_id="monitor-A",
            p_compromised=0.95,
            challenge_accuracy=0.1,
            policy_violation_rate=0.9,
        )

    low = estimator.get_trust(
        "monitor-A"
    )

    for _ in range(5):
        estimator.update(
            monitor_id="monitor-A",
            p_compromised=0.05,
            challenge_accuracy=0.95,
            policy_violation_rate=0.05,
        )

    recovered = estimator.get_trust(
        "monitor-A"
    )

    assert recovered > low


def test_severe_violation_can_force_isolation():
    estimator = AdaptiveTrustEstimator(
        severe_violation_cap=0.15,
        review_threshold=0.30,
    )

    update = estimator.update(
        monitor_id="monitor-A",
        p_compromised=0.1,
        challenge_accuracy=0.9,
        policy_violation_rate=0.0,
        severe_violation=True,
    )

    assert update.current_trust <= 0.15
    assert update.status == TrustStatus.ISOLATE
