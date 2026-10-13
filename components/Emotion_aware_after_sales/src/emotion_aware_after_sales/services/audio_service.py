from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class AudioData:
    samples: np.ndarray
    sample_rate: int
    duration_seconds: float


class AudioService:

    def load_audio(self, file_path: str) -> AudioData:
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Audio file not found: {file_path}"
            )

        samples, sample_rate = sf.read(
            str(path),
            dtype="float32"
        )

        if samples.size == 0:
            raise ValueError("Audio file is empty.")

        if sample_rate <= 0:
            raise ValueError("Invalid sample rate.")

        # Convert stereo/multichannel audio to mono
        if samples.ndim == 2:
            samples = np.mean(samples, axis=1)

        duration = len(samples) / sample_rate

        return AudioData(
            samples=samples,
            sample_rate=sample_rate,
            duration_seconds=duration
        )