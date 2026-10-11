from src.agents.complaint_analysis import (
    analyze_complaint,
)
from src.agents.emotion_analysis import (
    analyze_emotion,
)
from src.agents.priority_impact import (
    analyze_priority,
)


complaint = """
Our office Canon printer has not worked for
three days. We have contacted your service
department several times, but no technician
has attended.

We cannot print customer invoices, and
our daily business operations are affected.

This is extremely disappointing.
"""


print("Running Complaint Analysis Agent...")
analysis = analyze_complaint(complaint)

print("Running Emotion Analysis Agent...")
emotion = analyze_emotion(complaint)

print("Running Priority & Business Impact Agent...")
priority = analyze_priority(
    complaint_text=complaint,
    complaint_analysis=analysis.model_dump(),
    emotion_analysis=emotion.model_dump(),
)

print("\nPRIORITY ANALYSIS RESULTS")
print("=" * 50)

print("Priority:", priority.priority)
print("Priority Score:", priority.priority_score)
print("Proposed SLA:", priority.proposed_sla_hours, "hours")
print("Business Impact:", priority.business_impact)

print("\nReasons:")
for reason in priority.reasons:
    print("-", reason)