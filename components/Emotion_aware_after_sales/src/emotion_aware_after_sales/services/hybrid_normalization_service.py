from dataclasses import dataclass, field
from difflib import SequenceMatcher
from rapidfuzz import fuzz
# from streamlit import text

from emotion_aware_after_sales.services.vocabulary_normalization_service import (
    VocabularyNormalizationService,
)


@dataclass
class Correction:
    original: str
    suggested: str
    similarity: float
    status: str


@dataclass
class HybridNormalizationResult:
    raw_text: str
    normalized_text: str
    corrections: list[Correction] = field(default_factory=list)


class HybridNormalizationService:
    """Combine existing rules with conservative fuzzy matching."""

    VOCABULARY = (
        "laptop",
        "battery",
        "warranty",
        "repair",
        "charger",
        "keyboard",
        "screen",
        "paminillak",
        "wisanduma",
        "thawama",
        "kalin",
        "mage",
    )

    # Short or meaning-sensitive words are not fuzzy-corrected.
    PROTECTED_WORDS = {
        "nai",
        "naha",
        "na",
        "ne",
        "ow",
        "epa",
    }

    # Canonical phrases for fuzzy phrase matching.
    PHRASE_VOCABULARY = (
        "paminillak",
        "me gana",
        "wada karanne",
        "wisandumak",
    )

    def suggest_phrase_corrections(self, text: str) -> list[Correction]:
        """Suggest phrase corrections without modifying the transcript."""
        words = text.lower().split()
        suggestions = []

        for window_size in (2, 3):
            for i in range(len(words) - window_size + 1):
                phrase = " ".join(words[i:i + window_size])

                best_candidate = None
                best_score = 0.0

                for candidate in self.PHRASE_VOCABULARY:
                    if phrase == candidate:
                        continue

                    score = fuzz.ratio(phrase, candidate) / 100.0

                    if score > best_score:
                        best_candidate = candidate
                        best_score = score

                if best_candidate and best_score >= 0.75:
                    suggestions.append(
                        Correction(
                            original=phrase,
                            suggested=best_candidate,
                            similarity=best_score,
                            status="review",
                        )
                    )

        return suggestions

    def __init__(self, auto_threshold: float = 0.92,
                 review_threshold: float = 0.78):
        self.rule_normalizer = VocabularyNormalizationService()
        self.auto_threshold = auto_threshold
        self.review_threshold = review_threshold

    def normalize(self, text: str) -> HybridNormalizationResult:
        rule_normalized = self.rule_normalizer.normalize(text)

        # Track changes made by the rule-based normalizer.
        if rule_normalized != text.lower().strip():
            corrections = [
                Correction(
                    original=text,
                    suggested=rule_normalized,
                    similarity=1.0,
                    status="rule",
                )
            ]
        else:
            corrections = []

        # Prepare words for fuzzy matching.
        words = rule_normalized.split()
        output = []
        

        for word in words:
            if word in self.PROTECTED_WORDS or word in self.VOCABULARY:
                output.append(word)
                continue

            candidates = [
                (
                    candidate,
                    SequenceMatcher(None, word, candidate).ratio(),
                )
                for candidate in self.VOCABULARY
            ]

            best_word, score = max(
                candidates,
                key=lambda item: item[1],
            )

            if score >= self.auto_threshold:
                output.append(best_word)
                corrections.append(
                    Correction(word, best_word, score, "auto")
                )

            elif score >= self.review_threshold:
                output.append(word)
                corrections.append(
                    Correction(word, best_word, score, "review")
                )

            else:
                output.append(word)

        normalized_text = " ".join(output)
        corrections.extend(
            self.suggest_phrase_corrections(normalized_text)
        )

        # Identify possible phrase-level transcription errors.
        # Suggestions do not change the normalized transcript.
        phrase_suggestions = {
            "pamani illa": "paminillak",
            "meeg an": "me gana",
        }

        for original_phrase, suggested_phrase in phrase_suggestions.items():
            if original_phrase in normalized_text:
                corrections.append(
                    Correction(
                        original=original_phrase,
                        suggested=suggested_phrase,
                        similarity=0.0,
                        status="review",
                    )
                )

        return HybridNormalizationResult(
            raw_text=text,
            normalized_text=normalized_text,
            corrections=corrections,
        )