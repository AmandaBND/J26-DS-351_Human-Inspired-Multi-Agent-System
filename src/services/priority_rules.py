from src.schemas.priority import (
    BusinessImpactAnalysis,
    PriorityResult,
)


# Prototype SLA values.
# Confirm these with Metropolitan before production use.
SLA_HOURS = {
    "High": 24,
    "Medium": 48,
    "Low": 72,
}


def calculate_priority(
    impact: BusinessImpactAnalysis,
    emotion_intensity: str,
) -> PriorityResult:

    score = 0
    reasons = []

    impact_scores = {
        "None": 0,
        "Low": 15,
        "Medium": 35,
        "High": 55,
    }

    score += impact_scores[impact.operational_impact]

    reasons.append(
        f"Operational impact: {impact.operational_impact}"
    )

    if impact.safety_risk:
        score = max(score, 90)
        reasons.append("Reported safety risk")

    if impact.service_delay_days is not None:
        if impact.service_delay_days >= 3:
            score += 20
            reasons.append("Service delay of 3 or more days")
        elif impact.service_delay_days >= 1:
            score += 10
            reasons.append("Service delay reported")

    if impact.repeated_contacts:
        score += 10
        reasons.append("Repeated customer contacts")

    if emotion_intensity == "High":
        score += 5
        reasons.append("Strong customer dissatisfaction")

    score = min(score, 100)

    if score >= 70:
        priority = "High"
    elif score >= 35:
        priority = "Medium"
    else:
        priority = "Low"

    return PriorityResult(
        priority=priority,
        priority_score=score,
        proposed_sla_hours=SLA_HOURS[priority],
        business_impact=impact.business_impact,
        reasons=reasons,
    )