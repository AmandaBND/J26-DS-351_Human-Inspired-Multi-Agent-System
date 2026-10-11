from src.agents.complaint_analysis import (
    analyze_complaint,
)


complaint = """
Our Canon printer has not worked for three days.
We contacted the service department several times,
but no technician has attended.
"""


result = analyze_complaint(complaint)


print("\nCOMPLAINT ANALYSIS RESULTS")
print("=" * 45)

print("Category:", result.category)
print("Issue Type:", result.issue_type)
print("Product:", result.product)
print("Duration:", result.duration)
print("Service Issue:", result.service_issue)
print("Summary:", result.summary)