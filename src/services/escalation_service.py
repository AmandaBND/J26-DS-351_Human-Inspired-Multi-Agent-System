from datetime import datetime, timezone

from sqlalchemy import select

from src.database.models import (
    Complaint,
    SessionLocal,
)

from src.services.sla_service import get_sla_status


def check_overdue_complaints() -> list[dict]:

    overdue_complaints = []

    now = datetime.now(timezone.utc)

    with SessionLocal() as db:

        complaints = db.execute(
            select(Complaint).where(
                Complaint.sla_due_at.is_not(None),
                Complaint.sla_completed_at.is_(None),
            )
        ).scalars().all()

        for complaint in complaints:

            status = get_sla_status(
                due_at=complaint.sla_due_at,
                completed_at=complaint.sla_completed_at,
                now=now,
            )

            if status == "Overdue":

                overdue_complaints.append(
                    {
                        "complaint_id": complaint.id,
                        "customer_name": complaint.customer_name,
                        "priority": complaint.priority,
                        "sla_due_at": complaint.sla_due_at,
                        "sla_status": status,
                    }
                )

    return overdue_complaints