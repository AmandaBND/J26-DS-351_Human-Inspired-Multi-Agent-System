
import numpy as np

from emotion_aware_after_sales.services.customer_audio_service import (
    CustomerAudioService,
)
from emotion_aware_after_sales.services.diarization_service import SpeakerTurn


def test_extracts_only_customer_audio():
    sample_rate = 16000
    samples = np.arange(48000, dtype=np.float32)

    turns = [
        SpeakerTurn(
            start_seconds=0.0,
            end_seconds=1.0,
            speaker_id="SPEAKER_00",
            role="agent",
        ),
        SpeakerTurn(
            start_seconds=1.0,
            end_seconds=2.0,
            speaker_id="SPEAKER_01",
            role="customer",
        ),
        SpeakerTurn(
            start_seconds=2.0,
            end_seconds=3.0,
            speaker_id="SPEAKER_00",
            role="agent",
        ),
    ]

    service = CustomerAudioService()

    result = service.extract_customer_segments(
        samples=samples,
        sample_rate=sample_rate,
        speaker_turns=turns,
    )

    assert len(result) == 1
    assert result[0].start_seconds == 1.0
    assert result[0].end_seconds == 2.0
    assert len(result[0].samples) == 16000
    np.testing.assert_array_equal(
        result[0].samples,
        samples[16000:32000],
    )
