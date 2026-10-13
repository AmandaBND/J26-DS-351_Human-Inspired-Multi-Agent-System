
from datetime import datetime, timezone

from sqlalchemy import select, func, update

from src.database.models import (
    ManagerNotification,
    SessionLocal,
)


# ============================================================
# GET MANAGER NOTIFICATIONS
# ============================================================

def get_manager_notifications(
    unread_only: bool = False,
) -> list[dict]:

    with SessionLocal() as db:
        statement = select(
            ManagerNotification
        ).order_by(
            ManagerNotification.created_at.desc(),
            ManagerNotification.id.desc(),
        )

        if unread_only:
            statement = statement.where(
                ManagerNotification.is_read == 0
            )

        records = db.execute(
            statement
        ).scalars().all()

        return [
            {
                "id": item.id,
                "complaint_id": item.complaint_id,
                "title": item.title,
                "message": item.message,
                "recipient_role": item.recipient_role,
                "is_read": bool(item.is_read),
                "created_at": item.created_at,
                "read_at": item.read_at,
            }
            for item in records
        ]


# ============================================================
# COUNT UNREAD NOTIFICATIONS
# ============================================================

def count_unread_notifications() -> int:

    with SessionLocal() as db:
        count = db.scalar(
            select(func.count())
            .select_from(ManagerNotification)
            .where(
                ManagerNotification.is_read == 0
            )
        )

        return count or 0


# ============================================================
# ACKNOWLEDGE NOTIFICATION
# ============================================================

def mark_notification_read(
    notification_id: int,
) -> bool:

    with SessionLocal() as db:
        result = db.execute(
            update(ManagerNotification)
            .where(
                ManagerNotification.id == notification_id,
                ManagerNotification.is_read == 0,
            )
            .values(
                is_read=1,
                read_at=datetime.now(timezone.utc),
            )
        )

        db.commit()

        return result.rowcount == 1
