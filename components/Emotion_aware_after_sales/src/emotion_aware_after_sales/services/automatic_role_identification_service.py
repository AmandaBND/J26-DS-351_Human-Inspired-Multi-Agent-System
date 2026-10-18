
from __future__ import annotations

from collections import defaultdict

import numpy as np
import torch
from pyannote.audio import Model, Inference


class AutomaticRoleIdentificationService:
    """Identify an enrolled service agent by voice similarity."""

    def __init__(self, model: Model):
        self.inference = Inference(
            model,
            window="whole",
        )

    def _embedding(self, samples, sample_rate):
        waveform = torch.as_tensor(
            np.asarray(samples, dtype=np.float32)
        ).unsqueeze(0)

        embedding = self.inference({
            "waveform": waveform,
            "sample_rate": sample_rate,
        })

        vector = np.asarray(embedding).reshape(-1)

        norm = np.linalg.norm(vector)
        if norm == 0:
            raise ValueError("Invalid speaker embedding.")

        return vector / norm

    def identify(
        self,
        samples,
        sample_rate,
        speaker_turns,
        agent_reference_samples,
        agent_reference_sample_rate,
    ):
        reference = self._embedding(
            agent_reference_samples,
            agent_reference_sample_rate,
        )

        grouped = defaultdict(list)

        for turn in speaker_turns:
            start = int(turn.start_seconds * sample_rate)
            end = int(turn.end_seconds * sample_rate)

            if end - start < sample_rate:
                continue

            grouped[turn.speaker_id].append(
                np.asarray(samples[start:end])
            )

        scores = {}

        for speaker_id, segments in grouped.items():
            # Combine speech from the same diarized speaker.
            speaker_audio = np.concatenate(segments)

            embedding = self._embedding(
                speaker_audio,
                sample_rate,
            )

            scores[speaker_id] = float(
                np.dot(reference, embedding)
            )

        if len(scores) != 2:
            raise ValueError(
                "Expected two speakers with sufficient audio."
            )

        ranked = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )

        agent_id, customer_id = ranked

        role_mapping = {
            agent_id: "agent",
            customer_id: "customer",
        }

        # This is a score difference, not calibrated confidence.
        score_margin = scores[agent_id] - scores[customer_id]

        return role_mapping, scores, score_margin
