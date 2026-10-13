from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from security_framework.experiment import ControlledMonitorExecutor
from security_framework.models import (
    AgentState,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import MonitorType


class VerificationChallenge(BaseModel):
    challenge_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    target_monitor_type: MonitorType
    severity: str = "medium"
    event: SecurityEvent


class ChallengeResult(BaseModel):
    recorded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    episode_id: str = Field(min_length=1)
    challenge_id: str = Field(min_length=1)
    category: str
    monitor_id: str = Field(min_length=1)
    monitor_type: MonitorType
    expected_decision: SecurityDecision
    observed_decision: SecurityDecision
    is_correct: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    experimental_monitor_state: AgentState | None = None
    experimental_behavior_mode: str | None = None


def load_challenge_bank(
    file_path: str | Path,
) -> list[VerificationChallenge]:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Challenge bank does not exist: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "Challenge bank must contain a JSON list."
        )

    return [
        VerificationChallenge.model_validate(item)
        for item in data
    ]


class ChallengeRunner:
    def __init__(
        self,
        output_file: str | Path,
    ) -> None:
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def append(
        self,
        result: ChallengeResult,
    ) -> None:
        with self.output_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(result.model_dump_json())
            file.write("\\n")

    def run_challenge(
        self,
        *,
        episode_id: str,
        challenge: VerificationChallenge,
        executor: ControlledMonitorExecutor,
    ) -> ChallengeResult:
        if (
            executor.monitor.monitor_type
            != challenge.target_monitor_type
        ):
            raise ValueError(
                "Challenge target monitor type does not "
                "match executor monitor type."
            )

        observed = executor.evaluate(challenge.event)

        result = ChallengeResult(
            episode_id=episode_id,
            challenge_id=challenge.challenge_id,
            category=challenge.category,
            monitor_id=observed.monitor_id,
            monitor_type=observed.monitor_type,
            expected_decision=challenge.event.expected_decision,
            observed_decision=observed.decision,
            is_correct=(
                observed.decision
                == challenge.event.expected_decision
            ),
            risk_score=observed.risk_score,
            confidence=observed.confidence,
            latency_ms=observed.latency_ms,
            experimental_monitor_state=executor.config.monitor_state,
            experimental_behavior_mode=executor.config.behavior_mode.value,
        )

        self.append(result)
        return result

    def run_all(
        self,
        *,
        episode_id: str,
        challenges: list[VerificationChallenge],
        executor: ControlledMonitorExecutor,
    ) -> list[ChallengeResult]:
        applicable = [
            challenge
            for challenge in challenges
            if challenge.target_monitor_type
            == executor.monitor.monitor_type
        ]

        return [
            self.run_challenge(
                episode_id=episode_id,
                challenge=challenge,
                executor=executor,
            )
            for challenge in applicable
        ]


def read_challenge_results(
    file_path: str | Path,
) -> list[ChallengeResult]:
    path = Path(file_path)

    if not path.exists():
        return []

    results: list[ChallengeResult] = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            text = line.strip()
            if not text:
                continue

            try:
                results.append(
                    ChallengeResult.model_validate_json(text)
                )
            except Exception as exc:
                raise ValueError(
                    f"Invalid challenge result at line {line_number}."
                ) from exc

    return results
