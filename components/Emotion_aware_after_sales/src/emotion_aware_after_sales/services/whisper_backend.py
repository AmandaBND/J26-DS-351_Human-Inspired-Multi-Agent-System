import numpy as np
from faster_whisper import WhisperModel


class WhisperBackend:
    """Real speech-to-text backend using Faster-Whisper."""

    def __init__(self, model_size: str = "base"):
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )

    def transcribe(
        self,
        samples: np.ndarray,
        sample_rate: int,
        language: str,
    ) -> str:
        if sample_rate != 16000:
            raise ValueError("WhisperBackend expects 16 kHz audio.")

        audio = np.asarray(samples, dtype=np.float32)

        segments, _ = self.model.transcribe(
            audio,
            language=language,
            task="transcribe",
            beam_size=5,
            vad_filter=False,
            condition_on_previous_text=False,
            no_speech_threshold=None,
        )

        return " ".join(segment.text.strip() for segment in segments)