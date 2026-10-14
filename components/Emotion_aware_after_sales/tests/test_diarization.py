
import pytest

from emotion_aware_after_sales.services.diarization_service import (
    DiarizationService,
    SpeakerTurn,
)


def test_assign_customer_and_agent_roles():
    service = DiarizationService()

    turns = [
        SpeakerTurn(0, 8, "SPEAKER_00"),
        SpeakerTurn(8, 24, "SPEAKER_01"),
        SpeakerTurn(24, 32, "SPEAKER_00"),
        SpeakerTurn(32, 51, "SPEAKER_01"),
    ]

    role_mapping = {
        "SPEAKER_00": "agent",
        "SPEAKER_01": "customer",
    }

    assigned = service.assign_roles(
        turns,
        role_mapping
    )

    assert assigned[0].role == "agent"
    assert assigned[1].role == "customer"

    customer_turns = service.get_customer_turns(
        assigned
    )

    assert len(customer_turns) == 2
    assert customer_turns[0].start_seconds == 8
    assert customer_turns[1].start_seconds == 32


def test_invalid_speaker_turn():
    service = DiarizationService()

    with pytest.raises(ValueError):
        service.validate_turns([
            SpeakerTurn(10, 5, "SPEAKER_00")
        ])


def test_missing_role_mapping():
    service = DiarizationService()

    with pytest.raises(ValueError):
        service.assign_roles(
            [SpeakerTurn(0, 5, "SPEAKER_00")],
            {}
        )


def test_turns_are_sorted():
    service = DiarizationService()

    turns = [
        SpeakerTurn(10, 15, "SPEAKER_01"),
        SpeakerTurn(0, 5, "SPEAKER_00"),
    ]

    sorted_turns = service.validate_turns(turns)

    assert sorted_turns[0].start_seconds == 0
    assert sorted_turns[1].start_seconds == 10
