import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.experiment.synthetic_reliability_benchmark import (
    SyntheticReliabilityBenchmark,
)


def main() -> None:
    config_file = (
        PROJECT_ROOT
        / "config"
        / "reliability_experiment.json"
    )

    config = json.loads(
        config_file.read_text(
            encoding="utf-8"
        )
    )

    benchmark = SyntheticReliabilityBenchmark(
        random_seed=config["random_seed"],
        events_per_episode=(
            config["events_per_episode"]
        ),
        challenges_per_monitor=(
            config["challenges_per_monitor"]
        ),
    )

    output_dir = (
        PROJECT_ROOT
        / "data"
        / "benchmark"
        / "reliability"
    )

    manifest = benchmark.generate_all(
        output_dir=output_dir,
        split_counts={
            "train": config["splits"]["train"],
            "validation": (
                config["splits"]["validation"]
            ),
            "test": config["splits"]["test"],
        },
    )

    print(
        json.dumps(
            manifest,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
