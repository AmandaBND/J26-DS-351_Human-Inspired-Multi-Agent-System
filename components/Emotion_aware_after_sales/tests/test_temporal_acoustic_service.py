
import numpy as np

from emotion_aware_after_sales.services.customer_audio_service import (
    CustomerAudioSegment,
)
from emotion_aware_after_sales.services.temporal_acoustic_service import (
    TemporalAcousticService,
)


def test_temporal_acoustic_service_preserves_order():
    segments = [
        CustomerAudioSegment(
            start_seconds=10.0,
            end_seconds=11.0,
            samples=np.full(16000, 0.5, dtype=np.float32),
            sample_rate=16000,
        ),
        CustomerAudioSegment(
            start_seconds=2.0,
            end_seconds=3.0,
            samples=np.full(16000, 0.2, dtype=np.float32),
            sample_rate=16000,
        ),
    ]

    timeline = TemporalAcousticService().analyze(segments)

    assert len(timeline) == 2
    assert timeline[0].start_seconds == 2.0
    assert timeline[1].start_seconds == 10.0

    assert abs(timeline[0].rms_energy - 0.2) < 0.001
    assert abs(timeline[1].rms_energy - 0.5) < 0.001
