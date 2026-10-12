from datetime import datetime, timedelta, timezone


def normalize_utc(value: datetime) -> datetime:
    """
    SQLite may return timezone-naive datetimes.
    Our application stores all timestamps as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def calculate_sla_due_at(
    created_at: datetime,
    sla_hours: int,
) -> datetime:

    if sla_hours <= 0:
        raise ValueError("SLA hours must be positive.")

    return normalize_utc(created_at) + timedelta(
        hours=sla_hours
    )


def get_sla_status(
    due_at: datetime | None,
    completed_at: datetime | None = None,
    now: datetime | None = None,
) -> str:

    if due_at is None:
        return "Not Configured"

    due_at = normalize_utc(due_at)
    now = normalize_utc(
        now or datetime.now(timezone.utc)
    )

    if completed_at is not None:
        completed_at = normalize_utc(completed_at)

        if completed_at <= due_at:
            return "Completed Within SLA"

        return "Completed Late"

    if now > due_at:
        return "Overdue"

    if due_at - now <= timedelta(hours=4):
        return "Due Soon"

    return "Within SLA"