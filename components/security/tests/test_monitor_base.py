import sys
from pathlib import Path
import pytest
from pydantic import ValidationError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from security_framework.models import SecurityDecision
from security_framework.monitors import MonitorResult, MonitorType


def test_monitor_result_accepts_valid_risk_score():
    result = MonitorResult(monitor_id="monitor-A", monitor_type=MonitorType.POLICY_TOOL, event_id="EVT-1", decision=SecurityDecision.BLOCK, risk_score=0.95, confidence=0.98, latency_ms=1.2, reason_codes=["TEST"])
    assert result.risk_score == 0.95


def test_monitor_result_rejects_invalid_risk_score():
    with pytest.raises(ValidationError):
        MonitorResult(monitor_id="monitor-A", monitor_type=MonitorType.POLICY_TOOL, event_id="EVT-1", decision=SecurityDecision.BLOCK, risk_score=1.50, confidence=0.98, latency_ms=1.2)
