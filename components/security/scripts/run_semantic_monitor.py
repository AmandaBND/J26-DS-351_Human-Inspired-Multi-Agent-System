import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from security_framework.models import SecurityEvent, SecurityDecision, EventType
from security_framework.monitors import DataMinimizationMonitor

monitor = DataMinimizationMonitor(ROOT / "config" / "data_minimization.json", ROOT / "config" / "policies.json")
event = SecurityEvent(event_id="DEMO-DATA-001", scenario_id="DATA-MINIMIZATION",
    source_agent_id="complaint-01", source_agent_role="Customer Complaint Agent",
    event_type=EventType.RESOURCE_ACCESS, requested_resource="customer_history",
    content_summary="Find delayed printer service status and product",
    expected_decision=SecurityDecision.ALLOW)
print(json.dumps(monitor.evaluate(event).model_dump(mode="json"), indent=2))
