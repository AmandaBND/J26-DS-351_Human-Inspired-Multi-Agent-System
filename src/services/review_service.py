from datetime import datetime, timezone

from sqlalchemy import update

from src.database.models import (
    Complaint,
    SessionLocal,
)


ALLOWED_DECISIONS = {
    "Approve": "Resolution Approved",
    "Reject": "Resolution Rejected",
}


def submit_manager_review(
    complaint_id: int,
    reviewer_name: str,
    decision: str,
    comments: str,
) -> dict:

    reviewer_name = reviewer_name.strip()
    comments = comments.strip()

    if not reviewer_name:
        raise ValueError("Reviewer name is required.")

    if decision not in ALLOWED_DECISIONS:
        raise ValueError("Invalid review decision.")

    if decision == "Reject" and not comments:
        raise ValueError(
            "A rejection reason is required."
        )

    new_status = ALLOWED_DECISIONS[decision]

    with SessionLocal() as db:

        # Atomic conditional update prevents
        # reviewing the same complaint twice.
        statement = (
            update(Complaint)
            .where(
                Complaint.id == complaint_id,
                Complaint.status == "Pending Human Review",
            )
            .values(
                status=new_status,
                reviewed_by=reviewer_name,
                review_comments=comments,
                reviewed_at=datetime.now(timezone.utc),
            )
        )

        result = db.execute(statement)

        if result.rowcount != 1:
            db.rollback()
            raise ValueError(
                "Complaint not found or already reviewed. "
                "Refresh the page."
            )

        db.commit()

    return {
        "complaint_id": complaint_id,
        "status": new_status,
        "reviewed_by": reviewer_name,
        "review_comments": comments,
    }