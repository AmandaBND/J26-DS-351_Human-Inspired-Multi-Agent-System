
from src.services.escalation_service import (
    process_overdue_escalations,
)


def main():
    print("Checking overdue complaints...")

    created = process_overdue_escalations()

    if not created:
        print("No new escalations required.")
        return

    for item in created:
        print(
            f"Complaint #{item['complaint_id']} "
            f"escalated. Notification "
            f"#{item['notification_id']} created."
        )

    print(
        f"\nCreated {len(created)} escalation(s)."
    )


if __name__ == "__main__":
    main()
