from typing import Literal

from pydantic import BaseModel, Field


class ComplaintAnalysis(BaseModel):

    category: Literal[
        "Equipment Breakdown",
        "Service Delay",
        "Rejected Service Job",
        "AMC Issue",
        "Installation Issue",
        "Product Issue",
        "Other",
    ] = Field(
        description="Primary complaint category"
    )

    issue_type: str = Field(
        description="Specific issue reported by the customer"
    )

    product: str = Field(
        description="Product or equipment mentioned"
    )

    duration: str = Field(
        description="How long the issue has existed"
    )

    service_issue: str = Field(
        description="Any issue related to service delivery"
    )

    summary: str = Field(
        description="Concise factual summary of the complaint"
    )