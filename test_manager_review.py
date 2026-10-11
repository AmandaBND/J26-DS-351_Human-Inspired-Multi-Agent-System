from src.database.models import (
    Complaint,
    SessionLocal,
)

from src.services.review_service import (
    submit_manager_review,
)


def create_test_complaint():
    with SessionLocal() as db:
        complaint = Complaint(
            customer_name="Review Test Customer",
            product="Test Printer",
            complaint_text="Manager review workflow test",
            status="Pending Human Review",
        )
        db.add(complaint)
        db.commit()
        return complaint.id


# Test 1: Approval
approved_id = create_test_complaint()

approved = submit_manager_review(
    complaint_id=approved_id,
    reviewer_name="Test Manager",
    decision="Approve",
    comments="Recommendation reviewed and approved.",
)

assert approved["status"] == "Resolution Approved"

print("Approval test passed:", approved)


# Test 2: Rejection
rejected_id = create_test_complaint()

rejected = submit_manager_review(
    complaint_id=rejected_id,
    reviewer_name="Test Manager",
    decision="Reject",
    comments="Additional technical verification required.",
)

assert rejected["status"] == "Resolution Rejected"

print("Rejection test passed:", rejected)


# Test 3: Duplicate decision must fail
try:
    submit_manager_review(
        complaint_id=approved_id,
        reviewer_name="Another Manager",
        decision="Reject",
        comments="Attempting duplicate review.",
    )

    raise AssertionError(
        "Duplicate review was incorrectly allowed."
    )

except ValueError:
    print("Duplicate review prevention test passed.")


# Test 4: Verify database persistence
with SessionLocal() as db:

    approved_record = db.get(Complaint, approved_id)
    rejected_record = db.get(Complaint, rejected_id)

    assert approved_record.status == "Resolution Approved"
    assert approved_record.reviewed_by == "Test Manager"
    assert approved_record.reviewed_at is not None

    assert rejected_record.status == "Resolution Rejected"
    assert rejected_record.review_comments is not None
    assert rejected_record.reviewed_at is not None

print("\nAll manager review tests passed!")