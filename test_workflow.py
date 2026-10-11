from pprint import pprint

from src.workflow.graph import complaint_graph


complaint = """
Our office Canon printer has not worked for
three days.

We have contacted the service department
several times, but no technician has attended.

We cannot print customer invoices, and our
daily business operations are affected.

This is extremely disappointing.
"""


print("\nStarting Multi-Agent Complaint Workflow")
print("=" * 55)

result = complaint_graph.invoke(
    {
        "complaint_text": complaint,
    }
)


print("\n" + "=" * 55)
print("FINAL MULTI-AGENT RESULTS")
print("=" * 55)

print("\n1. COMPLAINT ANALYSIS")
pprint(result["complaint_analysis"])

print("\n2. EMOTION ANALYSIS")
pprint(result["emotion_analysis"])

print("\n3. PRIORITY & BUSINESS IMPACT")
pprint(result["priority_analysis"])

print("\n4. RESOLUTION RECOMMENDATION")
pprint(result["resolution_analysis"])

assert result["complaint_analysis"]["category"]
assert result["emotion_analysis"]["primary_emotion"]
assert result["priority_analysis"]["priority"]
assert result["resolution_analysis"]["recommended_action"]

assert (
    result["resolution_analysis"]["approval_status"]
    == "Pending Human Review"
)

print("\nAll four agents executed successfully!")