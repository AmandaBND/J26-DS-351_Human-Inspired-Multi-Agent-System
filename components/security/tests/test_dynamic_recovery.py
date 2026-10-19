import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.evaluation.dynamic_recovery import (
    first_active_delay,
    first_non_active_delay,
)


def test_detection_delay_finds_first_non_active_window():
    frame = pd.DataFrame(
        [
            {"phase": "COMPROMISED", "trust_status": "ACTIVE"},
            {"phase": "COMPROMISED", "trust_status": "REDUCED"},
            {"phase": "COMPROMISED", "trust_status": "REVIEW"},
        ]
    )

    assert first_non_active_delay(
        frame,
        phase="COMPROMISED",
    ) == 2


def test_recovery_delay_finds_first_active_window():
    frame = pd.DataFrame(
        [
            {"phase": "RECOVERY", "trust_status": "REVIEW"},
            {"phase": "RECOVERY", "trust_status": "REDUCED"},
            {"phase": "RECOVERY", "trust_status": "ACTIVE"},
        ]
    )

    assert first_active_delay(
        frame,
        phase="RECOVERY",
    ) == 3
