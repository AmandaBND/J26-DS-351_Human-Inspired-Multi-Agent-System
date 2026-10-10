import csv
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "behavior_baseline"
    / "normal_agent_behavior.csv"
)

RANDOM_SEED = 42
ROWS = 60


def main() -> None:
    random.seed(RANDOM_SEED)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    fieldnames = [
        "baseline_id",
        "baseline_type",
        "tool_call_frequency",
        "restricted_resource_attempts",
        "failed_authorization_count",
        "external_api_calls",
        "database_query_count",
        "sensitive_resource_attempts",
    ]

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for index in range(1, ROWS + 1):
            writer.writerow(
                {
                    "baseline_id": f"NORMAL-{index:03d}",
                    "baseline_type": "synthetic_normal",
                    "tool_call_frequency": random.randint(1, 6),
                    "restricted_resource_attempts": (
                        1 if random.random() < 0.05 else 0
                    ),
                    "failed_authorization_count": (
                        1 if random.random() < 0.08 else 0
                    ),
                    "external_api_calls": random.randint(0, 3),
                    "database_query_count": random.randint(0, 5),
                    "sensitive_resource_attempts": (
                        1 if random.random() < 0.03 else 0
                    ),
                }
            )

    print(
        f"Created {ROWS} reproducible synthetic "
        f"normal behavior rows at: {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
