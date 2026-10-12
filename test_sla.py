from datetime import datetime, timedelta, timezone

from src.services.sla_service import (
    calculate_sla_due_at,
    get_sla_status,
)


now = datetime.now(timezone.utc)


# Test 1: Deadline calculation
due = calculate_sla_due_at(now, 24)

assert due == now + timedelta(hours=24)

print("SLA deadline calculation passed.")


# Test 2: Within SLA
assert get_sla_status(
    due_at=now + timedelta(hours=10),
    now=now,
) == "Within SLA"

print("Within SLA test passed.")


# Test 3: Due soon
assert get_sla_status(
    due_at=now + timedelta(hours=2),
    now=now,
) == "Due Soon"

print("Due Soon test passed.")


# Test 4: Overdue
assert get_sla_status(
    due_at=now - timedelta(hours=2),
    now=now,
) == "Overdue"

print("Overdue detection test passed.")


# Test 5: Completed within SLA
assert get_sla_status(
    due_at=now,
    completed_at=now - timedelta(hours=1),
    now=now,
) == "Completed Within SLA"

print("Completed Within SLA test passed.")


# Test 6: Completed late
assert get_sla_status(
    due_at=now,
    completed_at=now + timedelta(hours=1),
    now=now + timedelta(hours=2),
) == "Completed Late"

print("Completed Late test passed.")


print("\nAll SLA tests passed!")