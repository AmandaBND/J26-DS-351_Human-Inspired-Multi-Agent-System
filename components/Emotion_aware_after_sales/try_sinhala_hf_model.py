
from pathlib import Path

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)

# Paths and model configuration
MODEL_ID = "SinhaSpeech/whisper-small-sinhala-v6-e6-run11-best"

BASE_DIR = Path(__file__).resolve().parent
AUDIO_PATH = BASE_DIR / "test_amc_call.mp4"
OUTPUT_PATH = BASE_DIR / "sinhala_transcript_beam5.txt"

print("Loading audio...", flush=True)
audio = AudioPreprocessingPipeline().process(AUDIO_PATH)

print("Loading Sinhala speech model...", flush=True)
processor = AutoProcessor.from_pretrained(MODEL_ID)
model = AutoModelForSpeechSeq2Seq.from_pretrained(MODEL_ID)

model.to("cpu")
model.eval()

# Audio chunk settings
chunk_seconds = 20
sample_rate = audio.sample_rate
chunk_samples = chunk_seconds * sample_rate

print(f"Audio duration: {audio.duration_seconds:.2f} seconds")

# Clear the output file ONCE before processing
OUTPUT_PATH.write_text("", encoding="utf-8")

# Transcribe each audio chunk
for start_index in range(0, len(audio.samples), chunk_samples):
    end_index = min(
        start_index + chunk_samples,
        len(audio.samples),
    )

    start_seconds = start_index / sample_rate
    end_seconds = end_index / sample_rate

    chunk = audio.samples[start_index:end_index]

    inputs = processor(
        chunk,
        sampling_rate=sample_rate,
        return_tensors="pt",
    )

    with torch.inference_mode():
        predicted_ids = model.generate(
            inputs.input_features,
            max_new_tokens=224,
            num_beams=5,
            do_sample=False,
    )
    transcription = processor.batch_decode(
        predicted_ids,
        skip_special_tokens=True,
    )[0]

    # Display this chunk in the terminal
    print(
        f"\n[{start_seconds:.1f}s - {end_seconds:.1f}s]",
        flush=True,
    )
    print(transcription, flush=True)

    # Append this chunk to the UTF-8 text file
    with OUTPUT_PATH.open("a", encoding="utf-8") as file:
        file.write(
            f"\n[{start_seconds:.1f}s - {end_seconds:.1f}s]\n"
        )
        file.write(transcription + "\n")

print("\nFinished!", flush=True)
print(f"Transcript saved to: {OUTPUT_PATH}", flush=True)
