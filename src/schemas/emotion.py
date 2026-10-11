from typing import Literal

from pydantic import BaseModel, Field


class EmotionAnalysis(BaseModel):

    sentiment: Literal[
        "Positive",
        "Neutral",
        "Negative",
        "Mixed",
    ] = Field(
        description="Overall sentiment of the complaint"
    )

    primary_emotion: Literal[
        "Anger",
        "Frustration",
        "Disappointment",
        "Concern",
        "Sadness",
        "Satisfaction",
        "Neutral",
        "Other",
    ] = Field(
        description="Main emotion expressed by the customer"
    )

    emotion_intensity: Literal[
        "Low",
        "Medium",
        "High",
    ] = Field(
        description="Intensity of the expressed emotion"
    )

    emotion_score: int = Field(
        ge=0,
        le=100,
        description=(
            "Estimated intensity score from 0 to 100. "
            "This is a heuristic model estimate, "
            "not a calibrated probability."
        ),
    )

    explanation: str = Field(
        description=(
            "Brief explanation based on the "
            "customer's actual words"
        )
    )