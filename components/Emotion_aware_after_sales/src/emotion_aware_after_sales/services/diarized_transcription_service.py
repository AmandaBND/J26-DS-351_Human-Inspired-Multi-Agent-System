
from dataclasses import dataclass

import numpy as np


@dataclass
class DiarizedTranscriptTurn:
    start_seconds: float
    end_seconds: float
    speaker_id: str
    role: str
    raw_text: str


class DiarizedTranscriptionService:
    def __init__(self, asr_service):
        self.asr_service = asr_service

    def transcribe(self, samples, sample_rate, speaker_turns):
        results = []

        for turn in speaker_turns:
            start_index = max(
                0, int(turn.start_seconds * sample_rate)
            )
            end_index = min(
                len(samples), int(turn.end_seconds * sample_rate)
            )

            if end_index <= start_index:
                continue

            segment_audio = np.asarray(
                samples[start_index:end_index],
                dtype=np.float32,
            )

            # Very short turns may be difficult to transcribe.
            if len(segment_audio) < int(0.5 * sample_rate):
                continue

            segments = self.asr_service.transcribe(
                samples=segment_audio,
                sample_rate=sample_rate,
                chunk_seconds=20,
            )

            text = " ".join(
                segment.raw_text
                for segment in segments
                if segment.raw_text.strip()
            ).strip()

            results.append(
                DiarizedTranscriptTurn(
                    start_seconds=turn.start_seconds,
                    end_seconds=turn.end_seconds,
                    speaker_id=turn.speaker_id,
                    role=turn.role or "unknown",
                    raw_text=text,
                )
            )

        return results
