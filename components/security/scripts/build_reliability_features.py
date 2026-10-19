import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.features import (
    MODEL_FEATURE_COLUMNS,
    MonitorReliabilityFeatureExtractor,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Build one monitor-reliability feature row "
            "per experiment episode and monitor."
        )
    )

    parser.add_argument(
        "--decisions",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "monitor_logs"
            / "compromise_demo.jsonl"
        ),
    )

    parser.add_argument(
        "--challenges",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "attestation"
            / "challenge_demo.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=(
            PROJECT_ROOT
            / "data"
            / "processed"
            / "monitor_reliability_features_demo.csv"
        ),
    )

    args = parser.parse_args()

    if not args.decisions.exists():
        raise FileNotFoundError(
            f"Decision log not found: {args.decisions}\\n"
            "Run: python scripts\\\\run_compromise_demo.py"
        )

    if not args.challenges.exists():
        raise FileNotFoundError(
            f"Challenge log not found: {args.challenges}\\n"
            "Run: python scripts\\\\run_challenge_demo.py"
        )

    extractor = (
        MonitorReliabilityFeatureExtractor
        .from_files(
            decision_log=args.decisions,
            challenge_log=args.challenges,
        )
    )

    rows = extractor.extract()
    output = extractor.write_csv(
        rows,
        args.output,
    )

    print("Model input feature columns:")
    for feature in MODEL_FEATURE_COLUMNS:
        print(f"  - {feature}")

    print(
        f"\\nCreated {len(rows)} feature rows at: {output}"
    )

    for row in rows:
        print(
            f"\\n{row.episode_id} / {row.monitor_id}"
        )
        print(
            f"  challenge_accuracy={row.challenge_accuracy}"
        )
        print(
            "  verified_decision_accuracy="
            f"{row.verified_decision_accuracy:.2f}"
        )
        print(
            f"  false_allow_rate={row.false_allow_rate:.2f}"
        )
        print(
            "  policy_violation_rate="
            f"{row.policy_violation_rate}"
        )
        print(
            f"  label={row.label_state}"
        )


if __name__ == "__main__":
    main()
