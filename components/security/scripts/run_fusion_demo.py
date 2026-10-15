import json
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


def main() -> None:
    config = json.loads(
        (
            PROJECT_ROOT
            / "config"
            / "fusion.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    fusion = SecurityDecisionFusion(
        review_threshold=(
            config["review_threshold"]
        ),
        block_threshold=(
            config["block_threshold"]
        ),
    )

    # Demonstration:
    # two low-trust compromised monitors say ALLOW,
    # one high-trust policy monitor says BLOCK.
    inputs = [
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

    results = [
        fusion.single_guard(
            inputs,
            guard_id=config[
                "single_guard_id"
            ],
        ),
        fusion.equal_majority(
            inputs
        ),
        fusion.static_weighting(
            inputs,
            static_weights=config[
                "static_weights"
            ],
        ),
        fusion.adaptive_trust_weighting(
            inputs
        ),
    ]

    print(
        "Scenario: two low-trust monitors "
        "ALLOW, one high-trust monitor BLOCKS.\n"
    )

    for result in results:
        print(
            f"{result.strategy:28s} "
            f"decision={result.decision.value:6s} "
            f"risk={result.final_risk:.3f}"
        )

        print(
            f"  contributions="
            f"{result.contributions}"
        )


if __name__ == "__main__":
    main()
