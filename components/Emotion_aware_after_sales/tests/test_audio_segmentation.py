
import numpy as np
import pytest

from emotion_aware_after_sales.services.audio_service import AudioData
from emotion_aware_after_sales.services.audio_segmentation_service import (
    AudioSegmentationService,
)
import soundfile as sf

from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)


def make_audio(duration_seconds, sample_rate=16000):
    samples = np.zeros(
        int(duration_seconds * sample_rate),
        dtype=np.float32
    )

    return AudioData(
        samples=samples,
        sample_rate=sample_rate,
        duration_seconds=duration_seconds
    )


def test_26_second_recording():
    audio = make_audio(26)

    service = AudioSegmentationService(
        segment_duration=10,
        overlap_duration=2
    )

    segments = service.segment_audio(audio)

    assert len(segments) == 3
    assert [
        (s.start_seconds, s.end_seconds)
        for s in segments
    ] == [
        (0, 10),
        (8, 18),
        (16, 26)
    ]


def test_short_recording():
    audio = make_audio(5)

    segments = AudioSegmentationService().segment_audio(audio)

    assert len(segments) == 1
    assert segments[0].start_seconds == 0
    assert segments[0].end_seconds == 5


def test_empty_recording():
    audio = make_audio(0)

    segments = AudioSegmentationService().segment_audio(audio)

    assert segments == []


def test_invalid_overlap():
    with pytest.raises(ValueError):
        AudioSegmentationService(
            segment_duration=10,
            overlap_duration=10
        )


def test_preprocessing_and_segmentation_integration(tmp_path):
    sample_rate = 8000
    duration_seconds = 26

    samples = np.zeros(
        sample_rate * duration_seconds,
        dtype=np.float32
    )

    input_path = tmp_path / "test_call.wav"
    sf.write(input_path, samples, sample_rate)

    pipeline = AudioPreprocessingPipeline()

    segments = pipeline.process_and_segment(
        str(input_path),
        segment_duration=10,
        overlap_duration=2
    )

    assert len(segments) == 3
    assert segments[0].start_seconds == 0
    assert segments[0].end_seconds == 10
    assert segments[1].start_seconds == 8
    assert segments[1].end_seconds == 18
    assert segments[2].start_seconds == 16
    assert segments[2].end_seconds == 26

    assert all(
        segment.sample_rate == 16000
        for segment in segments
    )
