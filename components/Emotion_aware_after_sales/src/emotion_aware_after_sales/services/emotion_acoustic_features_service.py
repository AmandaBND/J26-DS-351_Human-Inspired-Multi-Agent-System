
from dataclasses import dataclass

import numpy as np


@dataclass
class EmotionAcousticFeatures:
    start_seconds: float
    end_seconds: float
    rms_energy: float
    energy_variability: float
    silence_ratio: float
    median_pitch_hz: float | None
    pitch_variability_hz: float | None


class EmotionAcousticFeaturesService:
    """Extract acoustic signals from customer speech, not emotion labels."""

    def analyze(self, customer_segments):
        results = []

        for segment in customer_segments:
            samples = np.asarray(segment.samples, dtype=np.float32)
            sample_rate = segment.sample_rate

            if samples.size == 0:
                continue

            frame_length = max(1, int(0.025 * sample_rate))
            hop_length = max(1, int(0.010 * sample_rate))

            frame_energies = []

            for start in range(0, len(samples) - frame_length + 1, hop_length):
                frame = samples[start:start + frame_length]
                frame_energies.append(
                    float(np.sqrt(np.mean(frame ** 2)))
                )

            if not frame_energies:
                continue

            energies = np.asarray(frame_energies)

            silence_threshold = max(
                0.005,
                float(np.percentile(energies, 20)),
            )

            # Use librosa's pYIN only when enough audio is available.
            pitch_values = np.array([], dtype=np.float32)

            if len(samples) >= int(0.5 * sample_rate):
                try:
                    import librosa

                    f0 = librosa.yin(
                        samples,
                        fmin=75,
                        fmax=500,
                        sr=sample_rate,
                        frame_length=1024,
                        hop_length=256,
                    )

                    valid_pitch = f0[
                        np.isfinite(f0)
                        & (f0 >= 75)
                        & (f0 <= 500)
                    ]

                    pitch_values = valid_pitch

                except (ImportError, ValueError):
                    pass

            results.append(
                EmotionAcousticFeatures(
                    start_seconds=segment.start_seconds,
                    end_seconds=segment.end_seconds,
                    rms_energy=float(np.mean(energies)),
                    energy_variability=float(np.std(energies)),
                    silence_ratio=float(
                        np.mean(energies < silence_threshold)
                    ),
                    median_pitch_hz=(
                        float(np.median(pitch_values))
                        if pitch_values.size
                        else None
                    ),
                    pitch_variability_hz=(
                        float(np.std(pitch_values))
                        if pitch_values.size
                        else None
                    ),
                )
            )

        return results
