
from pathlib import Path
import torch
from pyannote.audio import Pipeline

from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)

# CHANGE THIS to your actual recording filename.
AUDIO_FILENAME = "test_amc_call.mp4"

BASE_DIR = Path(__file__).resolve().parent
AUDIO_PATH = BASE_DIR / AUDIO_FILENAME

if not AUDIO_PATH.exists():
    raise FileNotFoundError(f"Recording not found: {AUDIO_PATH}")

print("Preparing audio...")
preprocessor = AudioPreprocessingPipeline()
audio = preprocessor.process(AUDIO_PATH)

print(f"Audio duration: {audio.duration_seconds:.2f} seconds")

print("Loading diarization model...")
pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-community-1"
)
pipeline.to(torch.device("cpu"))

print("Detecting speakers...")

waveform = torch.from_numpy(audio.samples).float().unsqueeze(0)

result = pipeline(
    {"waveform": waveform, "sample_rate": audio.sample_rate},
    num_speakers=2,
)

from emotion_aware_after_sales.services.diarization_service import (
    DiarizationService,
    SpeakerTurn,
)

speaker_turns = []

for turn, speaker in result.exclusive_speaker_diarization:
    speaker_turns.append(
        SpeakerTurn(
            start_seconds=turn.start,
            end_seconds=turn.end,
            speaker_id=speaker,
        )
    )

diarization_service = DiarizationService()

validated_turns = diarization_service.validate_turns(speaker_turns)

role_mapping = {
    "SPEAKER_00": "agent",
    "SPEAKER_01": "customer",
}

labeled_turns = diarization_service.assign_roles(
    validated_turns,
    role_mapping,
)

print("\nDetected speaker turns with roles:")

for turn in labeled_turns:
    print(
        f"{turn.start_seconds:.2f}s - "
        f"{turn.end_seconds:.2f}s | "
        f"{turn.speaker_id} | {turn.role}"
    )

customer_turns = diarization_service.get_customer_turns(labeled_turns)

print(f"\nCustomer turns detected: {len(customer_turns)}")
