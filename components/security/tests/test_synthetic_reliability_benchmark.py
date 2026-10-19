import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.experiment.synthetic_reliability_benchmark import (
    SyntheticReliabilityBenchmark,
)


def test_synthetic_benchmark_creates_balanced_labels(
    tmp_path: Path,
):
    benchmark = SyntheticReliabilityBenchmark(
        random_seed=7,
        events_per_episode=12,
        challenges_per_monitor=4,
    )

    summary = benchmark.generate_split(
        split="train",
        episode_count=8,
        output_dir=tmp_path,
        seed_offset=0,
    )

    frame = pd.read_csv(
        tmp_path / "train_features.csv"
    )

    assert summary["episodes"] == 8
    assert len(frame) == 24
    assert set(
        frame["compromised_label"].unique()
    ) == {0, 1}
    assert "experiment_condition" in frame.columns
