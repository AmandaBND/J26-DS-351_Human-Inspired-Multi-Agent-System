from src.database.models import (
    Complaint,
    SessionLocal,
    create_database,
)

create_database()

db = SessionLocal()

try:
    complaint = Complaint(
        customer_name="Test Customer",
        product="Canon Printer",
        complaint_text=(
            "Our Canon printer has not worked for "
            "three days. We contacted the service "
            "department, but no technician attended."
        ),
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    print("Complaint saved successfully!")
    print("Complaint ID:", complaint.id)
    print("Customer:", complaint.customer_name)
    print("Product:", complaint.product)
    print("Complaint:", complaint.complaint_text)
    print("Status:", complaint.status)

finally:
    db.close()