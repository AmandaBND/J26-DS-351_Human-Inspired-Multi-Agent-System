import numpy as np
import pytest
import soundfile as sf

from emotion_aware_after_sales.services.audio_service import AudioService


def test_load_audio(tmp_path):
    sample_rate = 16000
    samples = np.zeros(sample_rate, dtype=np.float32)

    audio_path = tmp_path / "test.wav"
    sf.write(audio_path, samples, sample_rate)

    service = AudioService()
    result = service.load_audio(str(audio_path))

    assert result.sample_rate == 16000
    assert result.duration_seconds == pytest.approx(1.0)
    assert len(result.samples) == 16000


def test_missing_audio():
    service = AudioService()

    with pytest.raises(FileNotFoundError):
        service.load_audio("nonexistent_audio.wav")