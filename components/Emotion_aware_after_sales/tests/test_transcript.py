import numpy as np
import pytest

from emotion_aware_after_sales.services.transcription_service import (
    TranscriptionService,
)


class FakeSinhalaBackend:
    def transcribe(self, samples, sample_rate, language):
        assert sample_rate == 16000
        assert language == "si"
        return "මගේ ලැප්ටොප් එක වැඩ කරන්නේ නැහැ."


def test_sinhala_transcription():
    service = TranscriptionService(FakeSinhalaBackend())

    samples = np.zeros(16000, dtype=np.float32)

    result = service.transcribe_segment(
        samples=samples,
        sample_rate=16000,
        start_seconds=0.0,
        end_seconds=1.0,
    )

    assert result.text == "මගේ ලැප්ටොප් එක වැඩ කරන්නේ නැහැ."
    assert result.language == "si"
    assert result.start_seconds == 0.0
    assert result.end_seconds == 1.0
    assert result.confidence is None


def test_empty_audio_rejected():
    service = TranscriptionService(FakeSinhalaBackend())

    with pytest.raises(ValueError, match="empty segment"):
        service.transcribe_segment(
            samples=np.array([], dtype=np.float32),
            sample_rate=16000,
            start_seconds=0.0,
            end_seconds=1.0,
        )