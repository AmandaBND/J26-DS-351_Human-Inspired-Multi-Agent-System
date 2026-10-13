
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from src.database.models import (
    Complaint,
    ComplaintEscalation,
    ManagerNotification,
    SessionLocal,
    create_database,
)

from src.services.escalation_service import (
    process_overdue_escalations,
)

from src.services.notification_service import (
    get_manager_notifications,
    mark_notification_read,
)


def main():
    create_database()

    now = datetime.now(timezone.utc)

    # ========================================================
    # CREATE SYNTHETIC OVERDUE COMPLAINT
    # ========================================================

    with SessionLocal() as db:
        complaint = Complaint(
            customer_name="Day 11 Test Customer",
            product="Test Printer",
            complaint_text=(
                "Synthetic overdue complaint for testing."
            ),
            category="Service Delay",
            priority="High",
            priority_score=90,
            proposed_sla_hours=24,
            status="Pending Human Review",
            created_at=now - timedelta(hours=30),
            sla_due_at=now - timedelta(hours=6),
            escalation_status="Not Escalated",
        )

        db.add(complaint)
        db.commit()

        complaint_id = complaint.id

    print(
        f"Created overdue test complaint #{complaint_id}"
    )

    # ========================================================
    # TEST 1: INITIAL ESCALATION
    # ========================================================

    first_run = process_overdue_escalations()

    matching = [
        item for item in first_run
        if item["complaint_id"] == complaint_id
    ]

    assert len(matching) == 1

    print("Initial escalation test passed.")

    # ========================================================
    # TEST 2: NO DUPLICATE ESCALATION
    # ========================================================

    second_run = process_overdue_escalations()

    duplicates = [
        item for item in second_run
        if item["complaint_id"] == complaint_id
    ]

    assert len(duplicates) == 0

    print("Duplicate prevention test passed.")

    # ========================================================
    # TEST 3: DATABASE RECORDS
    # ========================================================

    with SessionLocal() as db:
        saved_complaint = db.get(
            Complaint,
            complaint_id,
        )

        escalations = db.execute(
            select(ComplaintEscalation).where(
                ComplaintEscalation.complaint_id
                == complaint_id
            )
        ).scalars().all()

        notifications = db.execute(
            select(ManagerNotification).where(
                ManagerNotification.complaint_id
                == complaint_id
            )
        ).scalars().all()

        assert (
            saved_complaint.escalation_status
            == "Escalated"
        )

        assert len(escalations) == 1
        assert len(notifications) == 1

        notification_id = notifications[0].id

    print("Database persistence test passed.")

    # ========================================================
    # TEST 4: NOTIFICATION RETRIEVAL
    # ========================================================

    unread = get_manager_notifications(
        unread_only=True
    )

    assert any(
        item["id"] == notification_id
        for item in unread
    )

    print("Notification retrieval test passed.")

    # ========================================================
    # TEST 5: MARK NOTIFICATION AS READ
    # ========================================================

    assert mark_notification_read(
        notification_id
    ) is True

    assert mark_notification_read(
        notification_id
    ) is False

    print("Notification acknowledgement test passed.")

    print("\nAll Day 11 escalation tests passed!")


if __name__ == "__main__":
    main()
