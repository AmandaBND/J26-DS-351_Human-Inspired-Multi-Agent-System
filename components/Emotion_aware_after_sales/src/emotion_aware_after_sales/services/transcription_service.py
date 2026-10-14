from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass
class TranscriptionResult:
    text: str
    language: str
    start_seconds: float
    end_seconds: float
    confidence: float | None = None


class SpeechToTextBackend(Protocol):
    def transcribe(
        self,
        samples: np.ndarray,
        sample_rate: int,
        language: str,
    ) -> str:
        ...


class TranscriptionService:
    def __init__(self, backend: SpeechToTextBackend):
        self.backend = backend

    def transcribe_segment(
        self,
        samples: np.ndarray,
        sample_rate: int,
        start_seconds: float,
        end_seconds: float,
        language: str = "si", #sinhala language
    ) -> TranscriptionResult:

        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive.")

        if end_seconds <= start_seconds:
            raise ValueError("Invalid segment timestamps.")

        if samples.size == 0:
            raise ValueError("Cannot transcribe an empty segment.")

        text = self.backend.transcribe(
            samples=samples,
            sample_rate=sample_rate,
            language=language,
        )

        return TranscriptionResult(
            text=text.strip(),
            language=language,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            confidence=None,
        )