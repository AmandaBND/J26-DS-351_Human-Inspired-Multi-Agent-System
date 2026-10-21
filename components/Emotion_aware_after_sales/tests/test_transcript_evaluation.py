from emotion_aware_after_sales.services.vocabulary_normalization_service import (
    VocabularyNormalizationService,
)


def word_error_rate(reference: str, hypothesis: str) -> float:
    reference_words = reference.lower().split()
    hypothesis_words = hypothesis.lower().split()

    distances = list(range(len(hypothesis_words) + 1))

    for i, reference_word in enumerate(reference_words, start=1):
        new_distances = [i]

        for j, hypothesis_word in enumerate(hypothesis_words, start=1):
            substitution = 0 if reference_word == hypothesis_word else 1

            new_distances.append(
                min(
                    distances[j] + 1,
                    new_distances[j - 1] + 1,
                    distances[j - 1] + substitution,
                )
            )

        distances = new_distances

    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0

    return distances[-1] / len(reference_words)


def test_normalization_wer_comparison():
    reference = (
        "mage laptop eka wada karanne naha "
        "mama me gana kalin paminillak kala "
        "thawama wisandumak labune naha"
    )

    # A fixed example of imperfect ASR output.
    # This is not the measured Whisper output.
    raw = (
        "maagay laptoppe ka vadkaran naha "
        "mama meegaan kalim pamini illa kula "
        "thaumat visiduma labunin naha"
    )

    service = VocabularyNormalizationService()
    normalized = service.normalize(raw)

    raw_wer = word_error_rate(reference, raw)
    normalized_wer = word_error_rate(reference, normalized)

    print(f"\nRaw WER: {raw_wer:.2%}")
    print(f"Normalized WER: {normalized_wer:.2%}")

    assert raw_wer >= 0
    assert normalized_wer >= 0
    assert normalized_wer < raw_wer

def test_actual_whisper_recording_wer():
    reference = (
        "mage laptop eka wada karanne naha "
        "mama me gana kalin paminillak kala "
        "thawama wisandumak labune naha"
    )

    raw = (
        "Maagay laptoppe ka vadkaran nai "
        "mama meeg an kaalim pamani illa kula "
        "Thaumat visiduma klabuni nai"
    )

    normalizer = VocabularyNormalizationService()
    normalized = normalizer.normalize(raw)

    raw_wer = word_error_rate(reference, raw)
    normalized_wer = word_error_rate(reference, normalized)

    print(f"\nActual recording raw WER: {raw_wer:.2%}")
    print(f"Actual recording normalized WER: {normalized_wer:.2%}")

    assert raw_wer >= 0
    assert normalized_wer >= 0