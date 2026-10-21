
from types import SimpleNamespace

import numpy as np

from emotion_aware_after_sales.services.automatic_diarization_service import (
    AutomaticDiarizationService,
)


class FakePipeline:
    def __call__(self, audio_input, num_speakers=None):
        assert audio_input["sample_rate"] == 16000
        assert audio_input["waveform"].shape == (1, 16000)
        assert num_speakers == 2

        return SimpleNamespace(
            exclusive_speaker_diarization=[
                (
                    SimpleNamespace(start=0.0, end=0.4),
                    "SPEAKER_00",
                ),
                (
                    SimpleNamespace(start=0.5, end=0.9),
                    "SPEAKER_01",
                ),
            ]
        )


def test_automatic_diarization_assigns_roles():
    service = AutomaticDiarizationService(
        pipeline=FakePipeline()
    )

    samples = np.zeros(16000, dtype=np.float32)

    turns = service.diarize(
        samples=samples,
        sample_rate=16000,
        num_speakers=2,
        role_mapping={
            "SPEAKER_00": "agent",
            "SPEAKER_01": "customer",
        },
    )

    assert len(turns) == 2
    assert turns[0].speaker_id == "SPEAKER_00"
    assert turns[0].role == "agent"
    assert turns[1].speaker_id == "SPEAKER_01"
    assert turns[1].role == "customer"
    assert turns[1].start_seconds == 0.5
