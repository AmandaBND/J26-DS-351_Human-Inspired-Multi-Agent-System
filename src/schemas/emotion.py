
from typing import Literal

from pydantic import BaseModel, Field, model_validator


EmotionType = Literal[
    "Anger",
    "Frustration",
    "Disappointment",
    "Concern",
    "Sadness",
    "Satisfaction",
    "Neutral",
    "Other",
]


class EmotionAnalysis(BaseModel):

    # ============================================
    # EXISTING FIELDS - KEEP FOR COMPATIBILITY
    # ============================================

    sentiment: Literal[
        "Positive",
        "Neutral",
        "Negative",
        "Mixed",
    ] = Field(
        description="Overall sentiment of the complaint"
    )

    primary_emotion: EmotionType = Field(
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
            "Heuristic emotional intensity score "
            "from 0 to 100, not a confidence score."
        ),
    )

    explanation: str = Field(
        description=(
            "Brief explanation based on the "
            "customer's actual words"
        )
    )

    # ============================================
    # NEW RESEARCH FIELDS
    # ============================================

    secondary_emotions: list[EmotionType] = Field(
        default_factory=list,
        description=(
            "Additional emotions supported by "
            "the complaint text. Empty if none."
        ),
    )

    emotion_evidence: list[str] = Field(
        default_factory=list,
        description=(
            "Exact phrases copied from the "
            "complaint that support emotion predictions."
        ),
    )

    emotion_triggers: list[str] = Field(
        default_factory=list,
        description=(
            "Stated circumstances associated with "
            "the expressed emotions."
        ),
    )

    # ============================================
    # VALIDATE INTENSITY CONSISTENCY
    # ============================================

    @model_validator(mode="after")
    def validate_intensity(self):

        score = self.emotion_score
        intensity = self.emotion_intensity

        expected = (
            "Low" if score <= 33
            else "Medium" if score <= 66
            else "High"
        )

        if intensity != expected:
            raise ValueError(
                f"Emotion intensity '{intensity}' "
                f"does not match score {score}. "
                f"Expected '{expected}'."
            )

        return self
