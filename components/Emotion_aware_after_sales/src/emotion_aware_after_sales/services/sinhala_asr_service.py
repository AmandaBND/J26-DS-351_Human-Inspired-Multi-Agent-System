
from dataclasses import dataclass

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor


@dataclass
class SinhalaASRSegment:
    start_seconds: float
    end_seconds: float
    raw_text: str


class SinhalaASRService:
    MODEL_ID = (
        "SinhaSpeech/whisper-small-sinhala-v6-e6-run11-best"
    )

    def __init__(self, model_id: str | None = None):
        model_id = model_id or self.MODEL_ID

        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id
        )
        self.model.to("cpu")
        self.model.eval()

    def transcribe(
        self,
        samples,
        sample_rate: int,
        chunk_seconds: int = 20,
    ) -> list[SinhalaASRSegment]:
        if sample_rate != 16000:
            raise ValueError("Expected 16 kHz audio")

        if chunk_seconds <= 0:
            raise ValueError("chunk_seconds must be positive")

        chunk_size = chunk_seconds * sample_rate
        results = []

        for start_index in range(
            0, len(samples), chunk_size
        ):
            end_index = min(
                start_index + chunk_size,
                len(samples),
            )

            inputs = self.processor(
                samples[start_index:end_index],
                sampling_rate=sample_rate,
                return_tensors="pt",
            )

            with torch.inference_mode():
                predicted_ids = self.model.generate(
                    inputs.input_features,
                    max_new_tokens=224,
                    num_beams=3,
                    do_sample=False,
                )

            text = self.processor.batch_decode(
                predicted_ids,
                skip_special_tokens=True,
            )[0].strip()

            results.append(
                SinhalaASRSegment(
                    start_seconds=start_index / sample_rate,
                    end_seconds=end_index / sample_rate,
                    raw_text=text,
                )
            )

        return results
