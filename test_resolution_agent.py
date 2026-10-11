from src.agents.complaint_analysis import (
    analyze_complaint,
)
from src.agents.emotion_analysis import (
    analyze_emotion,
)
from src.agents.priority_impact import (
    analyze_priority,
)
from src.agents.resolution_agent import (
    recommend_resolution,
)


complaint = """
Our office Canon printer has not worked for
three days. We contacted the service department
several times, but no technician has attended.

We cannot print customer invoices and our daily
business operations are affected.

This is extremely disappointing.
"""


print("Running Agent 1: Complaint Analysis...")
analysis = analyze_complaint(complaint)

print("Running Agent 2: Emotion Analysis...")
emotion = analyze_emotion(complaint)

print("Running Agent 3: Priority & Impact...")
priority = analyze_priority(
    complaint_text=complaint,
    complaint_analysis=analysis.model_dump(),
    emotion_analysis=emotion.model_dump(),
)

print("Running Agent 4: Resolution Recommendation...")
resolution = recommend_resolution(
    complaint_text=complaint,
    complaint_analysis=analysis.model_dump(),
    emotion_analysis=emotion.model_dump(),
    priority_analysis=priority.model_dump(),
)


print("\n" + "=" * 55)
print("MULTI-AGENT COMPLAINT PROCESSING RESULTS")
print("=" * 55)

print("\nCATEGORY:", analysis.category)
print("EMOTION:", emotion.primary_emotion)
print("PRIORITY:", priority.priority)

print("\nRECOMMENDED ACTION:")
print(resolution.recommended_action)

print("\nACTION STEPS:")
for index, step in enumerate(
    resolution.action_steps,
    start=1,
):
    print(f"{index}. {step}")

print("\nRESPONSIBLE TEAM:")
print(resolution.responsible_team)

print("\nESCALATION REQUIRED:")
print(resolution.escalation_required)

print("\nESCALATION REASON:")
print(resolution.escalation_reason)

print("\nRESOLUTION REASONING:")
print(resolution.resolution_reasoning)

print("\nPOLICY REFERENCES:")
for reference in resolution.policy_references:
    print("-", reference)

print("\nCUSTOMER RESPONSE DRAFT:")
print(resolution.customer_response)

print("\nAPPROVAL STATUS:")
print(resolution.approval_status)