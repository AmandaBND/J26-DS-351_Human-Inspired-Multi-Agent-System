from src.services.complaint_service import (
    process_new_complaint,
    get_complaint_by_id,
)


complaint_text = """
Our Canon printer has not worked for three days.
We have contacted your service department
several times, but no technician has attended.

We cannot print customer invoices and our
daily business operations are affected.

This is extremely disappointing.
"""


print("\nSubmitting new complaint...")
print("=" * 50)

result = process_new_complaint(
    customer_name="Test Customer",
    product="Canon Printer",
    complaint_text=complaint_text,
)

complaint_id = result["complaint_id"]

print("\nComplaint ID:", complaint_id)
print("Processing Status:", result["status"])

print("\nRetrieving complaint from database...")

saved = get_complaint_by_id(complaint_id)

assert saved is not None
assert saved["status"] == "Pending Human Review"
assert saved["category"] is not None
assert saved["priority"] is not None
assert saved["recommended_resolution"] is not None

print("\nSAVED COMPLAINT DETAILS")
print("=" * 50)

print("Customer:", saved["customer_name"])
print("Product:", saved["product"])
print("Category:", saved["category"])
print("Emotion:", saved["emotion"])
print("Priority:", saved["priority"])
print("Priority Score:", saved["priority_score"])
print("Business Impact:", saved["business_impact"])
print("Recommended Resolution:", saved["recommended_resolution"])
print("Status:", saved["status"])

print("\nFull system database integration successful!")