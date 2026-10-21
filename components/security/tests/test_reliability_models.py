import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.features import (
    MODEL_FEATURE_COLUMNS,
)
from security_framework.ml import (
    ReliabilityModelTrainer,
)


def make_frame(
    rows: int = 30,
) -> pd.DataFrame:
    records = []

    for index in range(rows):
        compromised = (
            1 if index >= rows // 2 else 0
        )

        base = (
            0.8 if compromised else 0.1
        )

        record = {
            feature: (
                base
                + ((index % 3) * 0.01)
            )
            for feature in MODEL_FEATURE_COLUMNS
        }

        record.update(
            {
                "episode_id": f"EP-{index}",
                "monitor_id": "policy-monitor",
                "monitor_type": "POLICY_TOOL",
                "split": "train",
                "experiment_condition": (
                    "FALSE_ALLOW"
                    if compromised
                    else "NORMAL"
                ),
                "compromised_label": (
                    compromised
                ),
            }
        )

        records.append(record)

    return pd.DataFrame(records)


def test_threshold_selection_returns_valid_value():
    trainer = ReliabilityModelTrainer()

    y = np.array(
        [0, 0, 1, 1]
    )

    scores = np.array(
        [0.1, 0.2, 0.8, 0.9]
    )

    threshold = (
        trainer._select_threshold(
            y,
            scores,
        )
    )

    assert 0.1 <= threshold <= 0.9


def test_feature_loader_restricts_expected_columns(
    tmp_path: Path,
):
    frame = make_frame()
    path = tmp_path / "features.csv"
    frame.to_csv(
        path,
        index=False,
    )

    loaded = (
        ReliabilityModelTrainer
        .load_feature_csv(path)
    )

    assert set(
        MODEL_FEATURE_COLUMNS
    ).issubset(
        loaded.columns
    )
