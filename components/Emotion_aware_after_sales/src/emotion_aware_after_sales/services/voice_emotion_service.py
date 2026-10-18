
from dataclasses import dataclass

import numpy as np
import torch
from transformers import (
    AutoFeatureExtractor,
    AutoModelForAudioClassification,
)


@dataclass
class VoiceEmotionResult:
    start_seconds: float
    end_seconds: float
    predicted_emotion: str
    model_score: float
    scores: dict[str, float]
    needs_review: bool


class VoiceEmotionService:
    MODEL_ID = "superb/wav2vec2-base-superb-er"

    def __init__(self, model_id=None):
        model_id = model_id or self.MODEL_ID

        self.extractor = AutoFeatureExtractor.from_pretrained(
            model_id
        )
        self.model = AutoModelForAudioClassification.from_pretrained(
            model_id
        )

        self.model.to("cpu")
        self.model.eval()

    def analyze(self, customer_segments):
        results = []

        for segment in customer_segments:
            samples = np.asarray(
                segment.samples,
                dtype=np.float32,
            )

            if segment.sample_rate != 16000:
                raise ValueError("Expected 16 kHz customer audio")

            duration = len(samples) / segment.sample_rate

            # Short utterances may not provide enough context.
            if duration < 1.0:
                continue

            inputs = self.extractor(
                samples,
                sampling_rate=16000,
                return_tensors="pt",
            )

            with torch.inference_mode():
                logits = self.model(
                    **inputs
                ).logits

                probabilities = torch.softmax(
                    logits,
                    dim=-1,
                )[0]

            scores = {
                str(self.model.config.id2label[index]).lower():
                    round(float(probability), 4)
                for index, probability in enumerate(
                    probabilities.tolist()
                )
            }

            predicted_emotion = max(
                scores,
                key=scores.get,
            )

            model_score = scores[predicted_emotion]

            # This threshold is a review heuristic,
            # not calibrated confidence.
            needs_review = (
                model_score < 0.60
                or duration < 2.0
            )

            results.append(
                VoiceEmotionResult(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    predicted_emotion=predicted_emotion,
                    model_score=model_score,
                    scores=scores,
                    needs_review=needs_review,
                )
            )

        return results
