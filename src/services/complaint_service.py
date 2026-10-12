
import json

from src.database.models import (
    Complaint,
    SessionLocal,
    create_database,
)

from src.workflow.graph import complaint_graph

from src.services.sla_service import (
    calculate_sla_due_at,
)


# ============================================================
# PROCESS NEW CUSTOMER COMPLAINT
# ============================================================

def process_new_complaint(
    customer_name: str,
    product: str,
    complaint_text: str,
) -> dict:

    # ========================================================
    # STEP 1: VALIDATE CUSTOMER INPUT
    # ========================================================

    if not customer_name.strip():
        raise ValueError("Customer name is required.")

    if not product.strip():
        raise ValueError("Product is required.")

    if not complaint_text.strip():
        raise ValueError("Complaint text is required.")

    # Ensure database tables exist
    create_database()

    # ========================================================
    # STEP 2: SAVE ORIGINAL COMPLAINT
    # ========================================================

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

    # ========================================================
    # STEP 3: EXECUTE FOUR AI AGENTS
    # ========================================================

    try:

        results = complaint_graph.invoke(
            {
                "complaint_text": complaint_text,
            }
        )

    except Exception:

        with SessionLocal() as db:

            complaint = db.get(
                Complaint,
                complaint_id,
            )

            if complaint:

                complaint.status = "Analysis Failed"

                db.commit()

        raise

    # ========================================================
    # STEP 4: EXTRACT AGENT RESULTS
    # ========================================================

    analysis = results["complaint_analysis"]

    emotion = results["emotion_analysis"]

    priority = results["priority_analysis"]

    resolution = results["resolution_analysis"]

    # ========================================================
    # STEP 5: SAVE AI ANALYSIS RESULTS
    # ========================================================

    with SessionLocal() as db:

        complaint = db.get(
            Complaint,
            complaint_id,
        )

        if complaint is None:
            raise ValueError(
                f"Complaint {complaint_id} not found."
            )

        # ----------------------------------------------------
        # AGENT 1: COMPLAINT ANALYSIS
        # ----------------------------------------------------

        complaint.category = analysis["category"]

        complaint.issue_type = analysis["issue_type"]

        complaint.summary = analysis["summary"]

        # ----------------------------------------------------
        # AGENT 2: CUSTOMER EMOTION ANALYSIS
        # ----------------------------------------------------

        complaint.emotion = emotion["primary_emotion"]

        complaint.sentiment = emotion["sentiment"]

        complaint.emotion_intensity = emotion[
            "emotion_intensity"
        ]

        complaint.emotion_score = emotion[
            "emotion_score"
        ]

        # ----------------------------------------------------
        # AGENT 3: PRIORITY AND BUSINESS IMPACT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SLA DEADLINE CALCULATION
        # ----------------------------------------------------

        complaint.sla_due_at = calculate_sla_due_at(
            complaint.created_at,
            priority["proposed_sla_hours"],
        )

        # Initialize escalation status
        complaint.escalation_status = "Not Escalated"

        # ----------------------------------------------------
        # AGENT 4: RESOLUTION RECOMMENDATION
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # HUMAN APPROVAL WORKFLOW
        # ----------------------------------------------------

        complaint.status = "Pending Human Review"

        # Save all results
        db.commit()

    # ========================================================
    # STEP 6: RETURN PROCESSING RESULT
    # ========================================================

    return {
        "complaint_id": complaint_id,
        "status": "Pending Human Review",
        "results": results,
    }


# ============================================================
# GET COMPLAINT BY ID
# ============================================================

def get_complaint_by_id(
    complaint_id: int,
):

    with SessionLocal() as db:

        complaint = db.get(
            Complaint,
            complaint_id,
        )

        if complaint is None:
            return None

        return {
            column.name: getattr(
                complaint,
                column.name,
            )
            for column in Complaint.__table__.columns
        }
