import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.evaluation import calculate_system_metrics


def test_system_metrics_are_calculated_correctly():
    frame = pd.DataFrame(
        [
            {"expected_decision": "BLOCK", "final_decision": "BLOCK"},
            {"expected_decision": "BLOCK", "final_decision": "ALLOW"},
            {"expected_decision": "ALLOW", "final_decision": "BLOCK"},
            {"expected_decision": "ALLOW", "final_decision": "ALLOW"},
        ]
    )

    metrics = calculate_system_metrics(frame)

    assert metrics["final_decision_accuracy"] == 0.5
    assert metrics["attack_success_rate"] == 0.5
    assert metrics["false_block_rate"] == 0.5
