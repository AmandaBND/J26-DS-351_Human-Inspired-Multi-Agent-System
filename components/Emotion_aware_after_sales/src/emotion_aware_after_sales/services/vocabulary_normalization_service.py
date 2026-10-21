import re


class VocabularyNormalizationService:
    """Normalize known Romanized Sinhala transcription variants."""

    REPLACEMENTS = {
        "maagay": "mage",
        "mageel": "mage",
        "laptoppe": "laptop",
        "laptoppe ka": "laptop eka",
        "vadkaran": "wada karanne",
        "vadkaran naha": "wada karanne naha",
        "meegaan": "me gana",
        "kalim": "kalin",
        "pamini illa": "paminilla",
        "paminillak": "paminillak",
        "thaumat": "thawama",
        "visiduma": "wisanduma",
        "labunin": "labune",
    }

    def normalize(self, text: str) -> str:
        normalized = text.lower().strip()

        for original, replacement in sorted(
            self.REPLACEMENTS.items(),
            key=lambda item: len(item[0]),
            reverse=True,
        ):
            pattern = rf"\b{re.escape(original)}\b"
            normalized = re.sub(pattern, replacement, normalized)

        normalized = re.sub(r"\s+", " ", normalized)

        return normalized