
from dataclasses import dataclass

import numpy as np


@dataclass
class TemporalAcousticEmotionPoint:
    start_seconds: float
    end_seconds: float
    activation_score: float
    trend: str
    uncertainty: float
    evidence: list[str]


class TemporalAcousticEmotionService:
    """Estimate relative vocal activation, not categorical emotion."""

    def analyze(self, acoustic_features):
        if not acoustic_features:
            return []

        # Use the call's customer segments as a relative baseline.
        energies = np.array(
            [item.rms_energy for item in acoustic_features],
            dtype=float,
        )

        energy_baseline = float(np.median(energies))
        energy_scale = max(
            float(np.std(energies)),
            0.01,
        )

        valid_pitches = [
            item.median_pitch_hz
            for item in acoustic_features
            if item.median_pitch_hz is not None
        ]

        pitch_baseline = (
            float(np.median(valid_pitches))
            if valid_pitches
            else None
        )

        pitch_scale = (
            max(float(np.std(valid_pitches)), 20.0)
            if valid_pitches
            else None
        )

        results = []
        previous_score = None

        for item in acoustic_features:
            evidence = []

            energy_z = (
                item.rms_energy - energy_baseline
            ) / energy_scale

            # Higher-than-baseline energy is one activation cue.
            energy_signal = float(
                np.clip(0.5 + 0.2 * energy_z, 0.0, 1.0)
            )

            signals = [energy_signal]

            if energy_z > 0.5:
                evidence.append(
                    "Energy above this call's customer baseline"
                )

            if (
                pitch_baseline is not None
                and pitch_scale is not None
                and item.median_pitch_hz is not None
            ):
                pitch_z = (
                    item.median_pitch_hz - pitch_baseline
                ) / pitch_scale

                pitch_signal = float(
                    np.clip(0.5 + 0.2 * pitch_z, 0.0, 1.0)
                )
                signals.append(pitch_signal)

                if pitch_z > 0.5:
                    evidence.append(
                        "Pitch above this call's customer baseline"
                    )

            score = float(np.mean(signals))

            if previous_score is None:
                trend = "baseline"
            elif score > previous_score + 0.10:
                trend = "increasing"
            elif score < previous_score - 0.10:
                trend = "decreasing"
            else:
                trend = "stable"

            duration = (
                item.end_seconds - item.start_seconds
            )

            # Heuristic uncertainty, not a calibrated probability.
            uncertainty = 0.35

            if item.median_pitch_hz is None:
                uncertainty += 0.25
                evidence.append("Pitch unavailable")

            if duration < 1.0:
                uncertainty += 0.20
                evidence.append("Short audio segment")

            if len(acoustic_features) < 5:
                uncertainty += 0.15
                evidence.append("Limited baseline data")

            uncertainty = min(uncertainty, 1.0)

            if not evidence:
                evidence.append(
                    "No strong above-baseline acoustic cues"
                )

            results.append(
                TemporalAcousticEmotionPoint(
                    start_seconds=item.start_seconds,
                    end_seconds=item.end_seconds,
                    activation_score=round(score, 3),
                    trend=trend,
                    uncertainty=round(uncertainty, 3),
                    evidence=evidence,
                )
            )

            previous_score = score

        return results
