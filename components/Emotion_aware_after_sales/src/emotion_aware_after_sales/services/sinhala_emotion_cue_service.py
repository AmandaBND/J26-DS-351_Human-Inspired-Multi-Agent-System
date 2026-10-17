
from dataclasses import dataclass, field
import unicodedata

@dataclass
class EmotionCueResult:
    start_seconds: float
    end_seconds: float
    frustration_score: float
    satisfaction_score: float
    uncertainty_score: float
    matched_cues: list[str] = field(default_factory=list)


class SinhalaEmotionCueService:
    """Detect tentative emotional context from Sinhala-English service text."""

    FRUSTRATION_CUES = {
        "ප්‍රශ්න": 0.25,
        "කැඩුණ": 0.25,
        "වැඩ නෑ": 0.35,
        "වැඩ කළේ නෑ": 0.35,
        "විසඳුනේ නෑ": 0.40,
        "තාම": 0.15,
        "පරක්කු": 0.30,
        "ප්‍රමාද": 0.30,
        "complaint": 0.30,
        "not working": 0.35,
        "still broken": 0.40,
        "delay": 0.30,
        "unresolved": 0.40,
    }

    SATISFACTION_CUES = {
        "හොඳයි": 0.25,
        "ස්තූතියි": 0.15,
        "විසඳුණා": 0.40,
        "හරි ගියා": 0.35,
        "thank you": 0.15,
        "resolved": 0.40,
        "working now": 0.35,
        "satisfied": 0.40,
    }

    UNCERTAINTY_CUES = {
        "බලමු": 0.20,
        "දන්නේ නෑ": 0.30,
        "හිතන්නේ": 0.15,
        "maybe": 0.20,
        "not sure": 0.30,
        "perhaps": 0.20,
        "විසඳුනේ නෑ": 0.40,
        "විසඳුණේ නෑ": 0.40,
    }

    def analyze(self, transcript_turns):
        results = []

        for turn in transcript_turns:
            if turn["role"] != "customer":
                continue

            text = unicodedata.normalize(
                "NFC",
                turn.get("normalized_text", ""),
            ).casefold()

            frustration = 0.0
            satisfaction = 0.0
            uncertainty = 0.0
            matched = []

            for cue, weight in self.FRUSTRATION_CUES.items():
                if unicodedata.normalize("NFC", cue).casefold() in text:
                    frustration += weight
                    matched.append(f"frustration: {cue}")

            for cue, weight in self.SATISFACTION_CUES.items():
                if unicodedata.normalize("NFC", cue).casefold() in text:
                    satisfaction += weight
                    matched.append(f"satisfaction: {cue}")

            for cue, weight in self.UNCERTAINTY_CUES.items():
                if unicodedata.normalize("NFC", cue).casefold() in text:
                    uncertainty += weight
                    matched.append(f"uncertainty: {cue}")

            results.append(
                EmotionCueResult(
                    start_seconds=turn["start_seconds"],
                    end_seconds=turn["end_seconds"],
                    frustration_score=min(1.0, frustration),
                    satisfaction_score=min(1.0, satisfaction),
                    uncertainty_score=min(1.0, uncertainty),
                    matched_cues=matched,
                )
            )

        return results
