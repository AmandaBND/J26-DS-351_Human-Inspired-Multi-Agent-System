from __future__ import annotations

import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from pydantic import BaseModel, Field

from security_framework.attestation.challenge_runner import (
    ChallengeResult,
    read_challenge_results,
)
from security_framework.history import (
    MonitorDecisionLogRecord,
    MonitorDecisionLogger,
)
from security_framework.models import (
    AgentState,
    SecurityDecision,
)


MODEL_FEATURE_COLUMNS = [
    "challenge_accuracy",
    "verified_decision_accuracy",
    "false_allow_rate",
    "false_block_rate",
    "disagreement_rate",
    "policy_violation_rate",
    "decision_flip_rate",
    "risk_score_drift",
    "missing_response_rate",
    "response_latency_zscore",
]


class MonitorReliabilityFeatureRow(BaseModel):
    episode_id: str
    monitor_id: str
    monitor_type: str

    challenge_accuracy: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    verified_decision_accuracy: float = Field(ge=0.0, le=1.0)
    false_allow_rate: float = Field(ge=0.0, le=1.0)
    false_block_rate: float = Field(ge=0.0, le=1.0)
    disagreement_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    policy_violation_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    decision_flip_rate: float = Field(ge=0.0, le=1.0)
    risk_score_drift: float = Field(ge=0.0, le=1.0)
    missing_response_rate: float = Field(ge=0.0, le=1.0)
    response_latency_zscore: float = Field(ge=0.0)

    decision_count: int = Field(ge=1)
    challenge_count: int = Field(ge=0)

    label_state: str
    compromised_label: int = Field(ge=0, le=1)


class MonitorReliabilityFeatureExtractor:
    def __init__(
        self,
        decision_records: list[MonitorDecisionLogRecord],
        challenge_results: list[ChallengeResult],
    ) -> None:
        self.decision_records = decision_records
        self.challenge_results = challenge_results

    @classmethod
    def from_files(
        cls,
        *,
        decision_log: str | Path,
        challenge_log: str | Path,
    ) -> "MonitorReliabilityFeatureExtractor":
        decisions = MonitorDecisionLogger(
            decision_log
        ).read_all()

        challenges = read_challenge_results(
            challenge_log
        )

        return cls(decisions, challenges)

    @staticmethod
    def _safe_rate(
        numerator: int,
        denominator: int,
    ) -> float:
        if denominator == 0:
            return 0.0
        return numerator / denominator

    @staticmethod
    def _challenge_accuracy(
        results: list[ChallengeResult],
    ) -> float | None:
        if not results:
            return None

        correct = sum(
            result.is_correct
            for result in results
        )
        return correct / len(results)

    @staticmethod
    def _verified_accuracy(
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        correct = sum(
            record.monitor_decision
            == record.expected_event_decision
            for record in records
        )
        return correct / len(records)

    @classmethod
    def _false_allow_rate(
        cls,
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        expected_block = [
            record
            for record in records
            if record.expected_event_decision
            == SecurityDecision.BLOCK
        ]

        false_allows = sum(
            record.monitor_decision
            == SecurityDecision.ALLOW
            for record in expected_block
        )

        return cls._safe_rate(
            false_allows,
            len(expected_block),
        )

    @classmethod
    def _false_block_rate(
        cls,
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        expected_allow = [
            record
            for record in records
            if record.expected_event_decision
            == SecurityDecision.ALLOW
        ]

        false_blocks = sum(
            record.monitor_decision
            == SecurityDecision.BLOCK
            for record in expected_allow
        )

        return cls._safe_rate(
            false_blocks,
            len(expected_allow),
        )

    def _disagreement_rate(
        self,
        episode_id: str,
        monitor_id: str,
    ) -> float | None:
        by_event: dict[
            str,
            list[MonitorDecisionLogRecord],
        ] = defaultdict(list)

        for record in self.decision_records:
            if record.episode_id == episode_id:
                by_event[record.event_id].append(record)

        comparable = 0
        disagreements = 0

        for records in by_event.values():
            if len(records) < 2:
                continue

            counts = Counter(
                record.monitor_decision
                for record in records
            )
            most_common = counts.most_common()

            if (
                len(most_common) > 1
                and most_common[0][1]
                == most_common[1][1]
            ):
                continue

            peer_reference = most_common[0][0]

            target = next(
                (
                    record
                    for record in records
                    if record.monitor_id == monitor_id
                ),
                None,
            )

            if target is None:
                continue

            comparable += 1

            if target.monitor_decision != peer_reference:
                disagreements += 1

        if comparable == 0:
            return None

        return disagreements / comparable

    @classmethod
    def _policy_violation_rate(
        cls,
        records: list[MonitorDecisionLogRecord],
    ) -> float | None:
        policy_records = [
            record
            for record in records
            if record.provenance.get(
                "verification_source"
            )
            == "deterministic_policy"
        ]

        if not policy_records:
            return None

        violations = sum(
            record.monitor_decision
            != record.expected_event_decision
            for record in policy_records
        )

        return cls._safe_rate(
            violations,
            len(policy_records),
        )

    @classmethod
    def _decision_flip_rate(
        cls,
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        comparable_pairs = 0
        flips = 0

        for previous, current in zip(
            records,
            records[1:],
        ):
            same_condition = (
                previous.expected_event_decision
                == current.expected_event_decision
                and previous.attack_type
                == current.attack_type
            )

            if not same_condition:
                continue

            comparable_pairs += 1

            if (
                previous.monitor_decision
                != current.monitor_decision
            ):
                flips += 1

        return cls._safe_rate(
            flips,
            comparable_pairs,
        )

    @staticmethod
    def _risk_score_drift(
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        scores = [
            record.risk_score
            for record in records
        ]

        if len(scores) < 2:
            return 0.0

        midpoint = max(
            1,
            len(scores) // 2,
        )

        first_half = scores[:midpoint]
        second_half = scores[midpoint:]

        if not second_half:
            return 0.0

        first_mean = statistics.mean(first_half)
        second_mean = statistics.mean(second_half)

        return min(
            1.0,
            abs(second_mean - first_mean),
        )

    @staticmethod
    def _missing_response_rate(
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        missing = sum(
            "MONITOR_UNAVAILABLE"
            in record.reason_codes
            for record in records
        )
        return missing / len(records)

    @staticmethod
    def _latency_zscore(
        records: list[MonitorDecisionLogRecord],
    ) -> float:
        latencies = [
            record.latency_ms
            for record in records
        ]

        if len(latencies) < 3:
            return 0.0

        history = latencies[:-1]
        latest = latencies[-1]

        if len(history) < 2:
            return 0.0

        std = statistics.stdev(history)

        if std == 0:
            return 0.0

        mean = statistics.mean(history)

        return abs(
            (latest - mean) / std
        )

    @staticmethod
    def _label(
        records: list[MonitorDecisionLogRecord],
    ) -> tuple[str, int]:
        states = {
            record.experimental_monitor_state
            for record in records
            if record.experimental_monitor_state
            is not None
        }

        if not states:
            return "UNKNOWN", 0

        if len(states) == 1:
            state = next(iter(states))

            if state == AgentState.COMPROMISED:
                return "COMPROMISED", 1

            if state == AgentState.UNAVAILABLE:
                return "UNAVAILABLE", 1

            return "NORMAL", 0

        compromised = (
            AgentState.COMPROMISED in states
            or AgentState.UNAVAILABLE in states
        )

        return (
            "MIXED",
            1 if compromised else 0,
        )

    def extract(
        self,
    ) -> list[MonitorReliabilityFeatureRow]:
        grouped: dict[
            tuple[str, str],
            list[MonitorDecisionLogRecord],
        ] = defaultdict(list)

        for record in self.decision_records:
            grouped[
                (
                    record.episode_id,
                    record.monitor_id,
                )
            ].append(record)

        challenge_grouped: dict[
            tuple[str, str],
            list[ChallengeResult],
        ] = defaultdict(list)

        for result in self.challenge_results:
            challenge_grouped[
                (
                    result.episode_id,
                    result.monitor_id,
                )
            ].append(result)

        rows: list[
            MonitorReliabilityFeatureRow
        ] = []

        for (
            episode_id,
            monitor_id,
        ), records in grouped.items():
            challenge_results = challenge_grouped.get(
                (episode_id, monitor_id),
                [],
            )

            label_state, compromised_label = (
                self._label(records)
            )

            rows.append(
                MonitorReliabilityFeatureRow(
                    episode_id=episode_id,
                    monitor_id=monitor_id,
                    monitor_type=records[0].monitor_type,
                    challenge_accuracy=(
                        self._challenge_accuracy(
                            challenge_results
                        )
                    ),
                    verified_decision_accuracy=(
                        self._verified_accuracy(
                            records
                        )
                    ),
                    false_allow_rate=(
                        self._false_allow_rate(
                            records
                        )
                    ),
                    false_block_rate=(
                        self._false_block_rate(
                            records
                        )
                    ),
                    disagreement_rate=(
                        self._disagreement_rate(
                            episode_id,
                            monitor_id,
                        )
                    ),
                    policy_violation_rate=(
                        self._policy_violation_rate(
                            records
                        )
                    ),
                    decision_flip_rate=(
                        self._decision_flip_rate(
                            records
                        )
                    ),
                    risk_score_drift=(
                        self._risk_score_drift(
                            records
                        )
                    ),
                    missing_response_rate=(
                        self._missing_response_rate(
                            records
                        )
                    ),
                    response_latency_zscore=(
                        self._latency_zscore(
                            records
                        )
                    ),
                    decision_count=len(records),
                    challenge_count=len(
                        challenge_results
                    ),
                    label_state=label_state,
                    compromised_label=(
                        compromised_label
                    ),
                )
            )

        return sorted(
            rows,
            key=lambda row: (
                row.episode_id,
                row.monitor_id,
            ),
        )

    @staticmethod
    def write_csv(
        rows: list[MonitorReliabilityFeatureRow],
        output_file: str | Path,
    ) -> Path:
        path = Path(output_file)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        fieldnames = list(
            MonitorReliabilityFeatureRow.model_fields.keys()
        )

        with path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
            writer.writeheader()

            for row in rows:
                writer.writerow(
                    row.model_dump(
                        mode="json"
                    )
                )

        return path
