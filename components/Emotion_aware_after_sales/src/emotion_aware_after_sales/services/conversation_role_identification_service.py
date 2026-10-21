
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RoleIdentificationResult:
    agent_speaker_id: str | None
    customer_speaker_id: str | None
    agent_score: float
    customer_score: float
    uncertain: bool
    evidence: List[str]


class ConversationRoleIdentificationService:
    """
    Infer agent/customer roles from Sinhala-English
    conversation content, without voice enrollment.

    This is a rule-based baseline, not a trained
    speaker-role classifier.
    """

    AGENT_PHRASES = {
        "how can i help": 3,
        "how may i help": 3,
        "customer service": 3,
        "service center": 2,
        "ticket number": 2,
        "serial number": 2,
        "may i have": 2,
        "please provide": 2,
        "මම කොහොමද උදව්": 3,
        "කොහොමද උදව් කරන්න": 3,
        "සේවා මධ්‍යස්ථානය": 2,
        "විස්තර ලබා දෙන්න": 2,
        "අංකය කියන්න": 2,
        "පරීක්ෂා කරලා": 2,
        "දැනුම් දෙන්නම්": 2,
    }

    CUSTOMER_PHRASES = {
        "my laptop": 3,
        "my device": 3,
        "i called": 2,
        "not working": 2,
        "still waiting": 2,
        "i have a problem": 3,
        "repair delay": 2,
        "මගේ ලැප්ටොප්": 3,
        "මගේ laptop": 3,
        "මගේ ප්‍රශ්න": 3,
        "තාම හදලා": 2,
        "වැඩ කරන්නේ නැහැ": 2,
        "මම කතා කළා": 2,
        "මට ප්‍රශ්නයක්": 3,
        "මගේ device": 3,
    }

    def _score(self, text, phrase_weights):
        text = (text or "").lower()
        total = 0
        matched = []

        for phrase, weight in phrase_weights.items():
            if phrase.lower() in text:
                total += weight
                matched.append(phrase)

        return total, matched

    def identify(
        self,
        speaker_turns,
        speaker_transcripts: Dict[str, str],
    ) -> RoleIdentificationResult:

        speakers = sorted({
            turn.speaker_id
            for turn in speaker_turns
        })

        if len(speakers) != 2:
            return RoleIdentificationResult(
                agent_speaker_id=None,
                customer_speaker_id=None,
                agent_score=0,
                customer_score=0,
                uncertain=True,
                evidence=[
                    "Expected two speakers; "
                    f"found {len(speakers)}."
                ],
            )

        scores = {}
        evidence = []

        for speaker in speakers:
            text = speaker_transcripts.get(speaker, "")

            agent_score, agent_matches = self._score(
                text, self.AGENT_PHRASES
            )

            customer_score, customer_matches = self._score(
                text, self.CUSTOMER_PHRASES
            )

            scores[speaker] = {
                "agent": agent_score,
                "customer": customer_score,
            }

            if agent_matches:
                evidence.append(
                    f"{speaker}: agent-like phrases: "
                    + ", ".join(agent_matches)
                )

            if customer_matches:
                evidence.append(
                    f"{speaker}: customer-like phrases: "
                    + ", ".join(customer_matches)
                )

        first, second = speakers

        first_agent_margin = (
            scores[first]["agent"]
            + scores[second]["customer"]
            - scores[first]["customer"]
            - scores[second]["agent"]
        )

        if first_agent_margin >= 2:
            agent = first
            customer = second
            uncertain = False

        elif first_agent_margin <= -2:
            agent = second
            customer = first
            uncertain = False

        else:
            agent = None
            customer = None
            uncertain = True

        return RoleIdentificationResult(
            agent_speaker_id=agent,
            customer_speaker_id=customer,
            agent_score=max(
                scores[s]["agent"] for s in speakers
            ),
            customer_score=max(
                scores[s]["customer"] for s in speakers
            ),
            uncertain=uncertain,
            evidence=evidence or [
                "No distinctive role phrases detected."
            ],
        )
