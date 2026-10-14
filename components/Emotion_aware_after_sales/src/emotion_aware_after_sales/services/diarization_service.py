
from dataclasses import dataclass
from typing import Optional


@dataclass
class SpeakerTurn:
    start_seconds: float
    end_seconds: float
    speaker_id: str
    role: Optional[str] = None


class DiarizationService:
    """Manage speaker turns and customer/agent roles."""

    VALID_ROLES = {"customer", "agent"}

    def validate_turns(self, turns):
        validated = []

        for turn in turns:
            if turn.start_seconds < 0:
                raise ValueError(
                    "Speaker turn cannot start before zero."
                )

            if turn.end_seconds <= turn.start_seconds:
                raise ValueError(
                    "Speaker turn end must be after start."
                )

            if not turn.speaker_id:
                raise ValueError(
                    "Speaker ID cannot be empty."
                )

            if (
                turn.role is not None
                and turn.role not in self.VALID_ROLES
            ):
                raise ValueError(
                    f"Invalid speaker role: {turn.role}"
                )

            validated.append(turn)

        return sorted(
            validated,
            key=lambda turn: turn.start_seconds
        )

    def assign_roles(self, turns, role_mapping):
        """Assign human-confirmed roles to speaker IDs."""

        assigned = []

        for turn in self.validate_turns(turns):
            role = role_mapping.get(turn.speaker_id)

            if role not in self.VALID_ROLES:
                raise ValueError(
                    f"Missing or invalid role for "
                    f"{turn.speaker_id}"
                )

            assigned.append(
                SpeakerTurn(
                    start_seconds=turn.start_seconds,
                    end_seconds=turn.end_seconds,
                    speaker_id=turn.speaker_id,
                    role=role
                )
            )

        return assigned

    def get_customer_turns(self, turns):
        """Return only customer speech intervals."""

        return [
            turn
            for turn in self.validate_turns(turns)
            if turn.role == "customer"
        ]
