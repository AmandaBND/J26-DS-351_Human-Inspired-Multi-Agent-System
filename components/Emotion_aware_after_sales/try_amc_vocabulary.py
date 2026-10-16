
from pathlib import Path

from emotion_aware_after_sales.services.amc_vocabulary_normalizer import (
    AMCVocabularyNormalizer,
)

BASE_DIR = Path(__file__).resolve().parent

VOCABULARY_PATH = BASE_DIR / "config" / "amc_vocabulary.json"
TRANSCRIPT_PATH = BASE_DIR / "sinhala_transcript_beam5.txt"
OUTPUT_PATH = BASE_DIR / "sinhala_transcript_beam5_normalized.txt"

normalizer = AMCVocabularyNormalizer(VOCABULARY_PATH)

raw_text = TRANSCRIPT_PATH.read_text(encoding="utf-8")
result = normalizer.normalize(raw_text)

OUTPUT_PATH.write_text(
    result.normalized_text,
    encoding="utf-8",
)

print("Normalization completed!")
print(f"Corrections found: {len(result.corrections)}")

print("\nCORRECTIONS:")
for correction in result.corrections:
    print(
        f"{correction.original} -> {correction.replacement}"
    )

print(f"\nSaved to: {OUTPUT_PATH}")


print("\nREVIEW SUGGESTIONS:")
for suggestion in result.suggestions:
    print(
        f"{suggestion.original} "
        f"-> {suggestion.suggested_replacement} "
        f"(review required)"
    )
