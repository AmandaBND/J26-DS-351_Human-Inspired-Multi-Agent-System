
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from src.database.models import (
    Complaint,
    ComplaintEscalation,
    ManagerNotification,
    SessionLocal,
    create_database,
)

from src.services.sla_service import (
    get_sla_status,
    normalize_utc,
)


# ============================================================
# SQLITE UTC DATETIME HELPER
# ============================================================

def sqlite_utc_now() -> datetime:
    """
    Return current UTC time without timezone information.

    SQLite commonly stores datetime values as naive
    timestamps even when SQLAlchemy specifies
    DateTime(timezone=True).

    All stored naive timestamps are assumed to be UTC.
    """

    return datetime.now(timezone.utc).replace(
        tzinfo=None
    )


# ============================================================
# IDENTIFY OVERDUE COMPLAINTS
# ============================================================

def check_overdue_complaints() -> list[dict]:
    """
    Identify complaints that have exceeded their SLA.

    Only complaints with:
    - An SLA deadline
    - No SLA completion timestamp
    - An overdue SLA status

    are returned.
    """

    now = datetime.now(timezone.utc)

    overdue = []

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

            if status != "Overdue":
                continue

            due_at = normalize_utc(
                complaint.sla_due_at
            )

            overdue.append(
                {
                    "complaint_id": complaint.id,
                    "customer_name": (
                        complaint.customer_name
                    ),
                    "priority": complaint.priority,
                    "sla_due_at": due_at,
                    "sla_status": status,
                    "escalation_status": (
                        complaint.escalation_status
                    ),
                }
            )

    return overdue


# ============================================================
# CREATE INITIAL ESCALATION AND MANAGER NOTIFICATION
# ============================================================

def process_overdue_escalations() -> list[dict]:
    """
    Find overdue complaints and create one initial
    escalation and manager notification per complaint.

    Features:
    - Checks SLA deadlines
    - Prevents duplicate escalations
    - Creates escalation audit records
    - Creates manager notifications
    - Uses atomic database transactions
    - Handles SQLite datetime comparisons
    """

    # Ensure required database tables exist.
    create_database()

    # Identify overdue complaints.
    overdue_complaints = check_overdue_complaints()

    created_events = []

    for item in overdue_complaints:

        complaint_id = item["complaint_id"]

        # Timezone-aware UTC for application logic.
        now = datetime.now(timezone.utc)

        # SQLite-compatible naive UTC for SQL comparison.
        sqlite_now = sqlite_utc_now()

        with SessionLocal() as db:

            try:

                # ============================================
                # STEP 1: RECHECK COMPLAINT
                # ============================================

                complaint = db.get(
                    Complaint,
                    complaint_id,
                )

                if complaint is None:
                    continue

                # Normalize deadline to UTC.
                due_at = normalize_utc(
                    complaint.sla_due_at
                )

                # Verify SLA status again.
                sla_status = get_sla_status(
                    due_at=complaint.sla_due_at,
                    completed_at=complaint.sla_completed_at,
                    now=now,
                )

                if sla_status != "Overdue":
                    continue

                # ============================================
                # STEP 2: ATOMIC ESCALATION CLAIM
                # ============================================

                result = db.execute(
                    update(Complaint)
                    .where(
                        Complaint.id == complaint_id,
                        Complaint.sla_due_at.is_not(None),
                        Complaint.sla_completed_at.is_(None),
                        Complaint.escalation_status
                        == "Not Escalated",
                        Complaint.sla_due_at < sqlite_now,
                    )
                    .values(
                        escalation_status="Escalated"
                    )
                    .execution_options(
                        synchronize_session=False
                    )
                )

                # If another process has already escalated
                # the complaint, do not create duplicates.

                if result.rowcount != 1:

                    db.rollback()
                    continue

                # ============================================
                # STEP 3: CREATE ESCALATION AUDIT RECORD
                # ============================================

                reason = (
                    f"Complaint #{complaint_id} exceeded "
                    f"its proposed SLA deadline of "
                    f"{due_at.isoformat()}."
                )

                escalation = ComplaintEscalation(
                    complaint_id=complaint_id,
                    escalation_type="SLA Overdue",
                    reason=reason,
                    escalated_to="Service Manager",
                    created_at=now,
                )

                db.add(escalation)

                # Flush to obtain escalation ID.
                db.flush()

                escalation_id = escalation.id

                # ============================================
                # STEP 4: CREATE MANAGER NOTIFICATION
                # ============================================

                priority = (
                    complaint.priority or "Unknown"
                )

                notification = ManagerNotification(
                    complaint_id=complaint_id,
                    escalation_id=escalation_id,
                    title=(
                        f"SLA Overdue: Complaint "
                        f"#{complaint_id}"
                    ),
                    message=(
                        f"Complaint #{complaint_id} "
                        f"({priority} priority) "
                        f"has exceeded its proposed "
                        f"SLA deadline. "
                        f"Manager action is required."
                    ),
                    recipient_role="Service Manager",
                    is_read=0,
                    created_at=now,
                )

                db.add(notification)

                # Flush to obtain notification ID.
                db.flush()

                notification_id = notification.id

                # ============================================
                # STEP 5: COMMIT TRANSACTION
                # ============================================

                db.commit()

                # ============================================
                # STEP 6: RECORD SUCCESSFUL ESCALATION
                # ============================================

                created_events.append(
                    {
                        "complaint_id": complaint_id,
                        "escalation_id": escalation_id,
                        "notification_id": notification_id,
                        "status": "Escalated",
                    }
                )

            # ================================================
            # HANDLE DUPLICATE ESCALATIONS
            # ================================================

            except IntegrityError:

                db.rollback()

                # Unique constraints prevent duplicate
                # escalation records and notifications.
                continue

            # ================================================
            # HANDLE UNEXPECTED DATABASE ERRORS
            # ================================================

            except Exception:

                db.rollback()
                raise

    return created_events
