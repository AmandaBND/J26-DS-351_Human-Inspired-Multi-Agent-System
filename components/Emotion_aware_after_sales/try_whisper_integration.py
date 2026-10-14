from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)
from emotion_aware_after_sales.services.transcription_service import (
    TranscriptionService,
)
from emotion_aware_after_sales.services.whisper_backend import (
    WhisperBackend,
)
from emotion_aware_after_sales.services.vocabulary_normalization_service import (
    VocabularyNormalizationService,
)


def main():
    audio = AudioPreprocessingPipeline().process("test_sinhala.wav")

    print(f"Audio duration: {audio.duration_seconds:.2f} seconds")
    print(f"Sample rate: {audio.sample_rate} Hz")

    backend = WhisperBackend(model_size="base")
    transcription_service = TranscriptionService(backend)

    result = transcription_service.transcribe_segment(
        samples=audio.samples,
        sample_rate=audio.sample_rate,
        start_seconds=0.0,
        end_seconds=audio.duration_seconds,
        language="si",
    )

    normalizer = VocabularyNormalizationService()
    normalized_text = normalizer.normalize(result.text)

    print("\nRaw transcript:")
    print(result.text)

    print("\nNormalized transcript:")
    print(normalized_text)


if __name__ == "__main__":
    main()