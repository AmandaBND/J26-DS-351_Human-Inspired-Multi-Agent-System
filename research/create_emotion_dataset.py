
import csv
from pathlib import Path


# ============================================================
# DAY 3 - SYNTHETIC CUSTOMER EMOTION RESEARCH DATASET
# ============================================================

COMPLAINTS = [
    # Neutral / factual service requests
    ("Printer Breakdown", "My Canon printer displays error code E03. Please arrange a technician."),
    ("Printer Breakdown", "The printer is not switching on. I would like to request a service visit."),
    ("Service Request", "Please confirm the scheduled date for our copier maintenance."),
    ("Service Request", "I need information about the annual maintenance contract renewal."),
    ("Technical Support", "Our scanner is producing blank pages. Please check the equipment."),
    ("Service Request", "Could you provide the status of service request SR1024?"),
    ("Equipment Maintenance", "The copier requires a toner replacement. Please advise the procedure."),
    ("Service Request", "Please schedule a technician to inspect our office printer."),
    ("Technical Support", "The machine displays a paper jam message after startup."),
    ("Service Request", "We would like to request preventive maintenance for our air conditioner."),

    # Frustration
    ("Service Delay", "I am frustrated because I have called your service team three times without receiving an update."),
    ("Printer Breakdown", "Our printer has been down for four days and I am extremely frustrated with the delay."),
    ("Service Delay", "I am tired of repeatedly contacting your office about the same unresolved issue."),
    ("Technical Support", "It is very frustrating that the same printer problem keeps happening after repairs."),
    ("Service Delay", "I cannot understand why nobody has responded despite my repeated requests."),
    ("Equipment Breakdown", "I am extremely frustrated that our copier is still not working after several technician visits."),
    ("Service Delay", "I have followed up every day and I am getting increasingly frustrated."),
    ("Technical Support", "This recurring scanner issue is becoming very frustrating for our team."),

    # Disappointment
    ("Service Delay", "I am disappointed that nobody informed us about the technician's delay."),
    ("Customer Service", "I expected better communication from your service department."),
    ("Service Delay", "It is disappointing that our service appointment was cancelled without notice."),
    ("Technical Support", "I am disappointed because the repaired printer stopped working again."),
    ("Customer Service", "The support experience has been disappointing compared with our previous service visits."),
    ("Service Delay", "I am very disappointed that our complaint has remained unresolved."),
    ("Customer Service", "We are disappointed by the lack of updates about our maintenance request."),

    # Concern
    ("Business Disruption", "I am worried that the printer breakdown will delay our customer invoices."),
    ("Equipment Breakdown", "I am concerned that the air conditioner may stop working during business hours."),
    ("Technical Support", "We are worried about losing important documents because the scanner keeps failing."),
    ("Service Delay", "I am concerned that the technician may not arrive before our scheduled meeting."),
    ("Business Disruption", "I am worried that this unresolved copier issue could interrupt our operations."),
    ("Equipment Breakdown", "The unusual noise from our air conditioner is concerning because we do not know whether it is safe to operate."),

    # Anger
    ("Service Delay", "I am angry that your team repeatedly promised a technician but nobody arrived."),
    ("Customer Service", "This is unacceptable! I am furious about the way our complaint has been handled."),
    ("Service Delay", "I am extremely angry that we have been ignored for an entire week."),
    ("Technical Support", "Your repeated failure to fix this problem makes me furious."),
    ("Customer Service", "I am angry about the broken promises and lack of accountability."),

    # Satisfaction / positive feedback
    ("Positive Feedback", "Thank you for repairing our printer quickly. I am very satisfied with the service."),
    ("Positive Feedback", "Your technician arrived on time and resolved the issue. Excellent service."),
    ("Positive Feedback", "I am happy with the professional support provided by your technical team."),
    ("Positive Feedback", "We are very satisfied with how efficiently the copier problem was resolved."),
    ("Positive Feedback", "Thank you for keeping us informed throughout the repair process."),

    # Mixed / multi-label emotions
    ("Service Delay", "I am frustrated by the repeated delays and disappointed that nobody has updated me."),
    ("Business Disruption", "I am worried about our pending invoices and frustrated by the slow technician response."),
    ("Customer Service", "I am angry about the missed appointment and disappointed with the lack of communication."),
    ("Technical Support", "I am concerned about the recurring fault and frustrated that it has not been fixed."),
    ("Customer Service", "I appreciate the technician's effort, but I am disappointed by the long waiting time."),
    ("Service Delay", "I am extremely frustrated with the delay and worried about the effect on our daily operations."),
    ("Technical Support", "I am disappointed that the repair failed and concerned about further equipment damage."),
    ("Positive Feedback", "I was worried about the breakdown, but I am now satisfied with the quick resolution."),
    ("Customer Service", "I am angry about the repeated delays, frustrated by the lack of progress, and disappointed with the service."),
    ("Service Delay", "Although I am satisfied with the final repair, I am disappointed that the process took so long."),
]


# ============================================================
# SAVE DATASET
# ============================================================

OUTPUT_PATH = Path("research/emotion_dataset.csv")

OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

FIELDNAMES = [
    "complaint_id",
    "complaint_text",
    "scenario",
    "sentiment_label",
    "primary_emotion_label",
    "secondary_emotions_label",
    "intensity_label",
    "evidence_label",
    "annotation_status",
]

rows = []

for index, (scenario, text) in enumerate(
    COMPLAINTS,
    start=1,
):
    rows.append({
        "complaint_id": f"EMO{index:03d}",
        "complaint_text": text,
        "scenario": scenario,
        "sentiment_label": "",
        "primary_emotion_label": "",
        "secondary_emotions_label": "",
        "intensity_label": "",
        "evidence_label": "",
        "annotation_status": "Pending",
    })


with OUTPUT_PATH.open(
    "w",
    newline="",
    encoding="utf-8-sig",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=FIELDNAMES,
    )

    writer.writeheader()
    writer.writerows(rows)


print("=" * 55)
print("DAY 3 - CUSTOMER EMOTION RESEARCH DATASET")
print("=" * 55)

print("Total Complaints:", len(rows))
print("Annotation Status: Pending")
print("Dataset Location:", OUTPUT_PATH)
print("Dataset Created Successfully!")
