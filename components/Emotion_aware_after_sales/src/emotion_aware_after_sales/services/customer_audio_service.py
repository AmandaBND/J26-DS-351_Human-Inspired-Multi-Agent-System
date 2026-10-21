
from dataclasses import dataclass

import numpy as np

from emotion_aware_after_sales.services.diarization_service import SpeakerTurn


@dataclass
class CustomerAudioSegment:
    start_seconds: float
    end_seconds: float
    samples: np.ndarray
    sample_rate: int


class CustomerAudioService:
    """Extract customer speech using verified diarization timestamps."""

    def extract_customer_segments(
        self,
        samples: np.ndarray,
        sample_rate: int,
        speaker_turns: list[SpeakerTurn],
    ) -> list[CustomerAudioSegment]:

        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")

        if samples.ndim != 1:
            raise ValueError("Expected mono audio samples")

        customer_segments = []

        for turn in speaker_turns:
            # Accept "Customer", "customer", or " CUSTOMER "
            if str(turn.role).strip().casefold() != "customer":
                continue

            start_index = max(
                0,
                int(turn.start_seconds * sample_rate),
            )
            end_index = min(
                len(samples),
                int(turn.end_seconds * sample_rate),
            )

            if end_index <= start_index:
                continue

            customer_segments.append(
                CustomerAudioSegment(
                    start_seconds=turn.start_seconds,
                    end_seconds=turn.end_seconds,
                    samples=samples[start_index:end_index].copy(),
                    sample_rate=sample_rate,
                )
            )

        return customer_segments
