
from types import SimpleNamespace

from emotion_aware_after_sales.services.temporal_emotion_fusion_service import (
    TemporalEmotionFusionService,
)


def test_temporal_fusion_tracks_customer_evidence():
    text_cues = [
        SimpleNamespace(
            start_seconds=10.0,
            end_seconds=15.0,
            frustration_score=0.0,
            satisfaction_score=0.0,
            matched_cues=[],
        ),
        SimpleNamespace(
            start_seconds=20.0,
            end_seconds=25.0,
            frustration_score=0.25,
            satisfaction_score=0.0,
            matched_cues=["frustration: කැඩුණ"],
        ),
        SimpleNamespace(
            start_seconds=30.0,
            end_seconds=35.0,
            frustration_score=0.0,
            satisfaction_score=0.0,
            matched_cues=[],
        ),
    ]

    acoustic_features = [
        SimpleNamespace(
            start_seconds=10.0,
            end_seconds=15.0,
            rms_energy=0.02,
        ),
        SimpleNamespace(
            start_seconds=20.0,
            end_seconds=25.0,
            rms_energy=0.05,
        ),
        SimpleNamespace(
            start_seconds=30.0,
            end_seconds=35.0,
            rms_energy=0.02,
        ),
    ]

    results = TemporalEmotionFusionService().analyze(
        text_cues,
        acoustic_features,
    )

    assert len(results) == 3

    assert results[0].trend == "initial"
    assert results[1].trend == "increasing"
    assert results[2].trend == "decreasing"

    assert results[1].frustration_evidence > 0.25
    assert results[1].uncertainty < results[2].uncertainty

    assert results[2].frustration_evidence == 0.0
    assert results[2].uncertainty >= 0.65
