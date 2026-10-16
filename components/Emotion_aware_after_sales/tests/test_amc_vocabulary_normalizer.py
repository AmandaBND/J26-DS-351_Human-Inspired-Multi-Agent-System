
import json

from emotion_aware_after_sales.services.amc_vocabulary_normalizer import (
    AMCVocabularyNormalizer,
)


def make_normalizer(tmp_path):
    vocabulary = {
        "company_names": {
            "Metropolitan Technologies": [
                "මෙට්‍රපල්ටන් ටෙක්නාවේ ජේසිකයෙන්"
            ]
        },
        "service_terms": {
            "AMC": ["ඒම්සි"],
            "Miss": ["මිස්"],
        },
    }

    path = tmp_path / "vocabulary.json"
    path.write_text(
        json.dumps(vocabulary, ensure_ascii=False),
        encoding="utf-8",
    )

    return AMCVocabularyNormalizer(path)


def test_verified_amc_variant_is_corrected(tmp_path):
    normalizer = make_normalizer(tmp_path)

    result = normalizer.normalize(
        "මම ඒම්සි අලුත් කරන්න කැමති නැහැ"
    )

    assert result.normalized_text == (
        "මම AMC අලුත් කරන්න කැමති නැහැ"
    )
    assert len(result.corrections) == 1
    assert result.corrections[0].replacement == "AMC"


def test_uncertain_company_name_requires_review(tmp_path):
    normalizer = make_normalizer(tmp_path)

    raw = "මෙට්‍රපල්ටන් ටෙක්නාවේ ජේසිකයෙන් කතා කරන්නේ"
    result = normalizer.normalize(raw)

    assert result.normalized_text == raw
    assert len(result.suggestions) == 1
    assert (
        result.suggestions[0].suggested_replacement
        == "Metropolitan Technologies"
    )


def test_customer_negation_is_preserved(tmp_path):
    normalizer = make_normalizer(tmp_path)

    result = normalizer.normalize(
        "මට ඒම්සි renew කරන්න ඕන නැහැ"
    )

    assert "නැහැ" in result.normalized_text
    assert "AMC" in result.normalized_text


def test_existing_english_terms_are_unchanged(tmp_path):
    normalizer = make_normalizer(tmp_path)

    raw = "manager service records"
    result = normalizer.normalize(raw)

    assert result.normalized_text == raw
    assert len(result.corrections) == 0
