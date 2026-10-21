from emotion_aware_after_sales.services.hybrid_normalization_service import (
    HybridNormalizationService,
)


def test_existing_rule_normalization():
    service = HybridNormalizationService()

    result = service.normalize("Maagay laptoppe ka vadkaran naha")

    assert result.normalized_text == "mage laptop eka wada karanne naha"
    assert result.raw_text == "Maagay laptoppe ka vadkaran naha"


def test_fuzzy_auto_correction():
    service = HybridNormalizationService()

    result = service.normalize("laptopp battery")

    assert result.normalized_text == "laptop battery"
    assert any(
        correction.original == "laptopp"
        and correction.status == "auto"
        for correction in result.corrections
    )


def test_uncertain_word_preserved():
    service = HybridNormalizationService()

    result = service.normalize("warrenty")

    assert result.normalized_text == "warrenty"
    assert any(
        correction.status == "review"
        for correction in result.corrections
    )


def test_negation_preserved():
    service = HybridNormalizationService()

    result = service.normalize("nai naha")

    assert result.normalized_text == "nai naha"


def test_unknown_word_preserved():
    service = HybridNormalizationService()

    result = service.normalize("unknownword")

    assert result.normalized_text == "unknownword"

def test_phrase_suggestion():
    service = HybridNormalizationService()

    result = service.normalize("mama pamani illa kula")

    assert result.normalized_text == "mama pamani illa kula"
    assert any(
        correction.original == "pamani illa"
        and correction.suggested == "paminillak"
        and correction.status == "review"
        for correction in result.corrections
    )


def test_phrase_suggestion_does_not_modify_text():
    service = HybridNormalizationService()

    result = service.normalize("mama meeg an kaalim")

    assert result.normalized_text == "mama meeg an kaalim"
    assert any(
        correction.original == "meeg an"
        and correction.suggested == "me gana"
        and correction.status == "review"
        for correction in result.corrections
    )