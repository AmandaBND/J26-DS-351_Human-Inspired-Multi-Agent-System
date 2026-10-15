
from __future__ import annotations

from typing import Any

from emotion_aware_after_sales.services.diarization_service import (
    DiarizationService,
    SpeakerTurn,
)


class AutomaticDiarizationService:
    """Convert pretrained diarization output into validated speaker turns."""

    def __init__(self, pipeline: Any):
        self.pipeline = pipeline
        self.diarization_service = DiarizationService()

    def diarize(
        self,
        samples,
        sample_rate: int,
        num_speakers: int | None = None,
        role_mapping: dict[str, str] | None = None,
    ) -> list[SpeakerTurn]:
        import torch

        waveform = torch.as_tensor(samples, dtype=torch.float32)

        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)

        audio_input = {
            "waveform": waveform,
            "sample_rate": sample_rate,
        }

        kwargs = {}
        if num_speakers is not None:
            kwargs["num_speakers"] = num_speakers

        result = self.pipeline(audio_input, **kwargs)

        turns = [
            SpeakerTurn(
                start_seconds=float(segment.start),
                end_seconds=float(segment.end),
                speaker_id=speaker,
            )
            for segment, speaker in result.exclusive_speaker_diarization
        ]

        turns = self.diarization_service.validate_turns(turns)

        if role_mapping is not None:
            turns = self.diarization_service.assign_roles(
                turns,
                role_mapping,
            )

        return turns
