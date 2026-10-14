
from dataclasses import dataclass

import numpy as np

from .audio_service import AudioData


@dataclass
class AudioSegment:
    segment_id: int
    start_seconds: float
    end_seconds: float
    samples: np.ndarray
    sample_rate: int


class AudioSegmentationService:

    def __init__(
        self,
        segment_duration=10.0,
        overlap_duration=2.0
    ):
        if segment_duration <= 0:
            raise ValueError(
                "Segment duration must be positive."
            )

        if not 0 <= overlap_duration < segment_duration:
            raise ValueError(
                "Overlap must be nonnegative and shorter "
                "than segment duration."
            )

        self.segment_duration = segment_duration
        self.overlap_duration = overlap_duration

    def segment_audio(self, audio: AudioData):
        sample_rate = audio.sample_rate

        if sample_rate <= 0:
            raise ValueError("Invalid sample rate.")

        window_size = round(
            self.segment_duration * sample_rate
        )
        overlap_size = round(
            self.overlap_duration * sample_rate
        )
        step_size = window_size - overlap_size

        if window_size <= 0 or step_size <= 0:
            raise ValueError(
                "Segment settings are too small for "
                "the audio sample rate."
            )

        total_samples = len(audio.samples)
        segments = []

        for start in range(0, total_samples, step_size):
            end = min(
                start + window_size,
                total_samples
            )

            segment_samples = audio.samples[start:end]

            segments.append(
                AudioSegment(
                    segment_id=len(segments) + 1,
                    start_seconds=start / sample_rate,
                    end_seconds=end / sample_rate,
                    samples=segment_samples,
                    sample_rate=sample_rate
                )
            )

            if end == total_samples:
                break

        return segments
