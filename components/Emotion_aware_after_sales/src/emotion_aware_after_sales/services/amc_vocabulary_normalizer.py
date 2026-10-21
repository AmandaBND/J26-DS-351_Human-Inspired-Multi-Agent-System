
import json
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VocabularyCorrection:
    original: str
    replacement: str
    start: int
    end: int


@dataclass
class VocabularySuggestion:
    original: str
    suggested_replacement: str
    start: int
    end: int
    reason: str = "Requires human verification"


@dataclass
class VocabularyNormalizationResult:
    raw_text: str
    normalized_text: str
    corrections: list[VocabularyCorrection] = field(
        default_factory=list
    )
    suggestions: list[VocabularySuggestion] = field(
        default_factory=list
    )


class AMCVocabularyNormalizer:
    # Only explicitly verified variants are corrected automatically.
    AUTO_CORRECTIONS = {
        "ඒම්සි": "AMC",
        "ඒ එම් සී": "AMC",
        "ඒඑම්සී": "AMC",
        "a m c": "AMC",
    }

    # These may be ASR errors, but must be confirmed against audio.
    REVIEW_VARIANTS = {
        "මෙට්‍රපල්ටන් ටෙක්නාවේ ජේසිකයෙන්",
    }

    def __init__(self, vocabulary_path: str | Path):
        with Path(vocabulary_path).open(
            "r", encoding="utf-8"
        ) as file:
            vocabulary = json.load(file)

        self.candidates = {}

        for category in vocabulary.values():
            for canonical, variations in category.items():
                for variation in variations:
                    if variation.strip():
                        self.candidates[variation.casefold()] = canonical

        for variant, canonical in self.AUTO_CORRECTIONS.items():
            self.candidates[variant.casefold()] = canonical

        self.pattern = self._compile_pattern(
            self.candidates.keys()
        )

    @staticmethod
    def _compile_pattern(variants):
        variants = sorted(
            variants,
            key=len,
            reverse=True,
        )

        if not variants:
            return None

        alternatives = "|".join(
            re.escape(variant) for variant in variants
        )

        return re.compile(
            rf"(?<!\w)(?:{alternatives})(?!\w)",
            flags=re.IGNORECASE,
        )

    def normalize(self, text: str) -> VocabularyNormalizationResult:
        corrections = []
        suggestions = []

        if self.pattern is None:
            return VocabularyNormalizationResult(text, text)

        output_parts = []
        cursor = 0

        for match in self.pattern.finditer(text):
            original = match.group(0)
            variant = original.casefold()
            canonical = self.candidates[variant]

            output_parts.append(text[cursor:match.start()])

            if variant in self.AUTO_CORRECTIONS:
                replacement = self.AUTO_CORRECTIONS[variant]
                output_parts.append(replacement)

                corrections.append(
                    VocabularyCorrection(
                        original=original,
                        replacement=replacement,
                        start=match.start(),
                        end=match.end(),
                    )
                )

            else:
                output_parts.append(original)

                suggestions.append(
                    VocabularySuggestion(
                        original=original,
                        suggested_replacement=canonical,
                        start=match.start(),
                        end=match.end(),
                    )
                )

            cursor = match.end()

        output_parts.append(text[cursor:])

        return VocabularyNormalizationResult(
            raw_text=text,
            normalized_text="".join(output_parts),
            corrections=corrections,
            suggestions=suggestions,
        )
