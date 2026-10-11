from typing import Literal

from pydantic import BaseModel, Field


class BusinessImpactAnalysis(BaseModel):
    operational_impact: Literal[
        "None",
        "Low",
        "Medium",
        "High",
    ]

    service_delay_days: int | None = Field(
        description="Reported service delay in days, if known",
        ge=0,
    )

    repeated_contacts: bool = Field(
        description="Whether repeated contacts are explicitly reported"
    )

    safety_risk: bool = Field(
        description="Whether the complaint reports a safety concern"
    )

    business_impact: str = Field(
        description="Factual explanation of business impact"
    )


class PriorityResult(BaseModel):
    priority: Literal["Low", "Medium", "High"]
    priority_score: int = Field(ge=0, le=100)
    proposed_sla_hours: int
    business_impact: str
    reasons: list[str]