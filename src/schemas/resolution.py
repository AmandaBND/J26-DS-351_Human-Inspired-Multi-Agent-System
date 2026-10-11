from typing import Literal

from pydantic import BaseModel, Field


class ResolutionRecommendation(BaseModel):

    recommended_action: str = Field(
        description="Main recommended resolution action"
    )

    action_steps: list[str] = Field(
        min_length=1,
        description="Ordered steps for handling the complaint"
    )

    responsible_team: str = Field(
        description="Suggested responsible department or team"
    )

    escalation_required: bool = Field(
        description="Whether human escalation is recommended"
    )

    escalation_reason: str = Field(
        description="Reason for escalation, if applicable"
    )

    customer_response: str = Field(
        description="Professional draft response to the customer"
    )

    resolution_reasoning: str = Field(
        description="Explanation supporting the recommendation"
    )

    policy_references: list[str] = Field(
        description="Relevant knowledge-base section headings"
    )

    approval_status: Literal[
        "Pending Human Review"
    ] = "Pending Human Review"