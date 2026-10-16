
from dataclasses import dataclass
import numpy as np

from emotion_aware_after_sales.services.customer_audio_service import (
    CustomerAudioSegment,
)


@dataclass
class AcousticTimelinePoint:
    start_seconds: float
    end_seconds: float
    rms_energy: float


class TemporalAcousticService:
    """Extract time-ordered acoustic features from customer speech."""

    def analyze(
        self,
        segments: list[CustomerAudioSegment],
    ) -> list[AcousticTimelinePoint]:

        timeline = []

        for segment in segments:
            samples = np.asarray(segment.samples, dtype=np.float64)

            if samples.size == 0:
                continue

            rms = float(np.sqrt(np.mean(samples ** 2)))

            timeline.append(
                AcousticTimelinePoint(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    rms_energy=rms,
                )
            )

        return sorted(
            timeline,
            key=lambda point: point.start_seconds,
        )
