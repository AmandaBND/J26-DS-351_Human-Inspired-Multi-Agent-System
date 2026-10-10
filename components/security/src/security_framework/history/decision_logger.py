from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from security_framework.models import (
    AgentState,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import MonitorResult


class MonitorDecisionLogRecord(BaseModel):
    logged_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    episode_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    event_id: str = Field(min_length=1)

    monitor_id: str = Field(min_length=1)
    monitor_type: str

    monitor_decision: SecurityDecision
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)

    expected_event_decision: SecurityDecision
    attack_type: str

    experimental_monitor_state: AgentState | None = None
    experimental_behavior_mode: str | None = None

    reason_codes: list[str] = Field(
        default_factory=list
    )

    source_dataset: str = "synthetic"

    provenance: dict[str, Any] = Field(
        default_factory=dict
    )


class MonitorDecisionLogger:
    def __init__(
        self,
        output_file: str | Path,
    ) -> None:
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def _safe_provenance(
        event: SecurityEvent,
    ) -> dict[str, Any]:
        allowed_keys = {
            "synthetic",
            "dataset_source",
            "dataset_version",
            "dataset_record_id",
            "split",
            "attack_family",
            "surface",
        }

        return {
            key: event.metadata[key]
            for key in allowed_keys
            if key in event.metadata
        }

    def build_record(
        self,
        *,
        episode_id: str,
        event: SecurityEvent,
        result: MonitorResult,
        experimental_monitor_state: AgentState | None = None,
        experimental_behavior_mode: str | None = None,
    ) -> MonitorDecisionLogRecord:
        return MonitorDecisionLogRecord(
            episode_id=episode_id,
            scenario_id=event.scenario_id,
            event_id=event.event_id,
            monitor_id=result.monitor_id,
            monitor_type=result.monitor_type.value,
            monitor_decision=result.decision,
            risk_score=result.risk_score,
            confidence=result.confidence,
            latency_ms=result.latency_ms,
            expected_event_decision=event.expected_decision,
            attack_type=event.attack_type.value,
            experimental_monitor_state=(
                experimental_monitor_state
            ),
            experimental_behavior_mode=(
                experimental_behavior_mode
            ),
            reason_codes=result.reason_codes,
            source_dataset=str(
                event.metadata.get(
                    "dataset_source",
                    (
                        "synthetic"
                        if event.metadata.get("synthetic")
                        else "unspecified"
                    ),
                )
            ),
            provenance=self._safe_provenance(event),
        )

    def append(
        self,
        record: MonitorDecisionLogRecord,
    ) -> None:
        with self.output_file.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(record.model_dump_json())
            file.write("\n")

    def log(
        self,
        *,
        episode_id: str,
        event: SecurityEvent,
        result: MonitorResult,
        experimental_monitor_state: AgentState | None = None,
        experimental_behavior_mode: str | None = None,
    ) -> MonitorDecisionLogRecord:
        record = self.build_record(
            episode_id=episode_id,
            event=event,
            result=result,
            experimental_monitor_state=(
                experimental_monitor_state
            ),
            experimental_behavior_mode=(
                experimental_behavior_mode
            ),
        )

        self.append(record)
        return record

    def read_all(
        self,
    ) -> list[MonitorDecisionLogRecord]:
        if not self.output_file.exists():
            return []

        records: list[
            MonitorDecisionLogRecord
        ] = []

        with self.output_file.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line_number, line in enumerate(
                file,
                start=1,
            ):
                text = line.strip()

                if not text:
                    continue

                try:
                    records.append(
                        MonitorDecisionLogRecord
                        .model_validate_json(text)
                    )
                except Exception as exc:
                    raise ValueError(
                        "Invalid monitor decision log "
                        f"at line {line_number}."
                    ) from exc

        return records

    def export_csv(
        self,
        csv_file: str | Path,
    ) -> Path:
        csv_path = Path(csv_file)
        csv_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        records = self.read_all()

        fieldnames = list(
            MonitorDecisionLogRecord.model_fields.keys()
        )

        with csv_path.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
            writer.writeheader()

            for record in records:
                row = record.model_dump(
                    mode="json"
                )
                row["reason_codes"] = json.dumps(
                    row["reason_codes"],
                    ensure_ascii=False,
                )
                row["provenance"] = json.dumps(
                    row["provenance"],
                    ensure_ascii=False,
                    sort_keys=True,
                )
                writer.writerow(row)

        return csv_path
