
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class SpeechEmotionPrediction:
    start_seconds: float
    end_seconds: float
    emotion: str
    model_score: float | None
    uncertain: bool
    scores: dict[str, float]
    note: str


class SpeechEmotionRecognitionService:
    """Predict customer speech emotion using pretrained Wav2Vec2."""

    LABELS = {
        "neu": "neutral",
        "hap": "happy",
        "ang": "angry",
        "sad": "sad",
    }

    def __init__(self, model, feature_extractor):
        self.model = model
        self.feature_extractor = feature_extractor
        self.model.eval()

    def analyze(self, customer_segments):
        results = []

        for segment in customer_segments:
            samples = np.asarray(
                segment.samples, dtype=np.float32
            ).reshape(-1)

            sample_rate = int(segment.sample_rate)
            duration = len(samples) / sample_rate

            if duration < 1.0:
                results.append(
                    SpeechEmotionPrediction(
                        start_seconds=segment.start_seconds,
                        end_seconds=segment.end_seconds,
                        emotion="insufficient_audio",
                        model_score=None,
                        uncertain=True,
                        scores={},
                        note="Segment shorter than one second",
                    )
                )
                continue

            # Model expects 16 kHz mono audio.
            if sample_rate != 16000:
                import librosa

                samples = librosa.resample(
                    samples,
                    orig_sr=sample_rate,
                    target_sr=16000,
                )
                sample_rate = 16000

            # Limit inference duration for CPU performance.
            samples = samples[:15 * sample_rate]

            inputs = self.feature_extractor(
                samples,
                sampling_rate=sample_rate,
                return_tensors="pt",
                padding=True,
            )

            with torch.inference_mode():
                logits = self.model(
                    **inputs
                ).logits

                probabilities = torch.softmax(
                    logits, dim=-1
                )[0].cpu().numpy()

            scores = {
                self.LABELS.get(
                    self.model.config.id2label[index],
                    self.model.config.id2label[index],
                ): float(probability)
                for index, probability in enumerate(probabilities)
            }

            ranked = sorted(
                scores.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            top_emotion, top_score = ranked[0]
            second_score = ranked[1][1]

            # Heuristic review rule, not calibrated confidence.
            uncertain = (
                top_score < 0.55
                or top_score - second_score < 0.15
                or duration < 2.0
            )

            results.append(
                SpeechEmotionPrediction(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    emotion=top_emotion,
                    model_score=round(top_score, 3),
                    uncertain=uncertain,
                    scores={
                        key: round(value, 3)
                        for key, value in scores.items()
                    },
                    note=(
                        "Review prediction: uncertain or short segment"
                        if uncertain
                        else "Model prediction; not clinically validated"
                    ),
                )
            )

        return results
