from emotion_aware_after_sales.services.vocabulary_normalization_service import (
    VocabularyNormalizationService,
)


def test_normalizes_known_variants():
    service = VocabularyNormalizationService()

    text = "Maagay laptoppe ka vadkaran naha"

    result = service.normalize(text)

    assert result == "mage laptop eka wada karanne naha"


def test_normalizes_complaint_terms():
    service = VocabularyNormalizationService()

    text = "mama meegaan kalim pamini illa kula"

    result = service.normalize(text)

    assert "me gana" in result
    assert "kalin" in result
    assert "paminilla" in result


def test_preserves_unknown_words():
    service = VocabularyNormalizationService()

    result = service.normalize("battery issue unknownword")

    assert result == "battery issue unknownword"