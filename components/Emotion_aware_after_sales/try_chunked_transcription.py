
from pathlib import Path

from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)
from emotion_aware_after_sales.services.whisper_backend import (
    WhisperBackend,
)
from emotion_aware_after_sales.services.transcription_service import (
    TranscriptionService,
)

AUDIO_PATH = Path(__file__).resolve().parent / "test_amc_call.mp4"

audio = AudioPreprocessingPipeline().process(AUDIO_PATH)

backend = WhisperBackend(model_size="base")
service = TranscriptionService(backend=backend)

chunk_seconds = 20
sample_rate = audio.sample_rate
chunk_samples = chunk_seconds * sample_rate

print(f"Audio duration: {audio.duration_seconds:.2f} seconds")

for start_index in range(0, len(audio.samples), chunk_samples):
    end_index = min(
        start_index + chunk_samples,
        len(audio.samples),
    )

    start_seconds = start_index / sample_rate
    end_seconds = end_index / sample_rate

    result = service.transcribe_segment(
        samples=audio.samples[start_index:end_index],
        sample_rate=sample_rate,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        language="si",
    )

    print(f"\n[{start_seconds:.1f}s - {end_seconds:.1f}s]")
    print(result.text)
