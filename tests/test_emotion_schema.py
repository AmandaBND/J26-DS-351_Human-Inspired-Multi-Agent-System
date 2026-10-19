
import pytest
from pydantic import ValidationError

from src.schemas.emotion import EmotionAnalysis


def make_emotion(**overrides):
    data = {
        "sentiment": "Negative",
        "primary_emotion": "Frustration",
        "emotion_intensity": "High",
        "emotion_score": 80,
        "explanation": "Customer explicitly expresses frustration.",
        "secondary_emotions": ["Disappointment"],
        "emotion_evidence": ["I am frustrated"],
        "emotion_triggers": ["Delayed service"],
    }

    data.update(overrides)
    return EmotionAnalysis(**data)


def test_valid_emotion_schema():
    result = make_emotion()

    assert result.primary_emotion == "Frustration"
    assert result.emotion_score == 80


def test_secondary_emotions():
    result = make_emotion()

    assert "Disappointment" in result.secondary_emotions


def test_optional_research_fields():
    result = make_emotion(
        secondary_emotions=[],
        emotion_evidence=[],
        emotion_triggers=[],
    )

    assert result.secondary_emotions == []
    assert result.emotion_evidence == []
    assert result.emotion_triggers == []


def test_invalid_score():
    with pytest.raises(ValidationError):
        make_emotion(emotion_score=120)


def test_inconsistent_intensity():
    with pytest.raises(ValidationError):
        make_emotion(
            emotion_score=80,
            emotion_intensity="Low",
        )


def test_medium_intensity():
    result = make_emotion(
        emotion_score=55,
        emotion_intensity="Medium",
    )

    assert result.emotion_intensity == "Medium"


def test_low_intensity():
    result = make_emotion(
        emotion_score=20,
        emotion_intensity="Low",
    )

    assert result.emotion_intensity == "Low"
