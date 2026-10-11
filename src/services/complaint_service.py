import json

from src.database.models import (
    Complaint,
    SessionLocal,
    create_database,
)

from src.workflow.graph import complaint_graph


def process_new_complaint(
    customer_name: str,
    product: str,
    complaint_text: str,
) -> dict:

    if not customer_name.strip():
        raise ValueError("Customer name is required.")

    if not product.strip():
        raise ValueError("Product is required.")

    if not complaint_text.strip():
        raise ValueError("Complaint text is required.")

    create_database()

    # Step 1: Save original complaint
    with SessionLocal() as db:
        complaint = Complaint(
            customer_name=customer_name,
            product=product,
            complaint_text=complaint_text,
            status="Pending Analysis",
        )

        db.add(complaint)
        db.commit()
        db.refresh(complaint)

        complaint_id = complaint.id

    # Step 2: Execute all four agents
    try:
        results = complaint_graph.invoke(
            {
                "complaint_text": complaint_text,
            }
        )

    except Exception:
        with SessionLocal() as db:
            complaint = db.get(Complaint, complaint_id)

            if complaint:
                complaint.status = "Analysis Failed"
                db.commit()

        raise

    analysis = results["complaint_analysis"]
    emotion = results["emotion_analysis"]
    priority = results["priority_analysis"]
    resolution = results["resolution_analysis"]

    # Step 3: Save agent results
    with SessionLocal() as db:
        complaint = db.get(Complaint, complaint_id)

        complaint.category = analysis["category"]
        complaint.issue_type = analysis["issue_type"]
        complaint.summary = analysis["summary"]

        complaint.emotion = emotion["primary_emotion"]
        complaint.sentiment = emotion["sentiment"]
        complaint.emotion_intensity = emotion[
            "emotion_intensity"
        ]
        complaint.emotion_score = emotion["emotion_score"]

        complaint.priority = priority["priority"]
        complaint.priority_score = priority[
            "priority_score"
        ]
        complaint.proposed_sla_hours = priority[
            "proposed_sla_hours"
        ]
        complaint.business_impact = priority[
            "business_impact"
        ]

        complaint.recommended_resolution = resolution[
            "recommended_action"
        ]

        complaint.resolution_details = json.dumps(
            resolution,
            ensure_ascii=False,
        )

        complaint.customer_response = resolution[
            "customer_response"
        ]

        complaint.status = "Pending Human Review"

        db.commit()

    return {
        "complaint_id": complaint_id,
        "status": "Pending Human Review",
        "results": results,
    }


def get_complaint_by_id(complaint_id: int):

    with SessionLocal() as db:
        complaint = db.get(Complaint, complaint_id)

        if complaint is None:
            return None

        return {
            column.name: getattr(complaint, column.name)
            for column in Complaint.__table__.columns
        }