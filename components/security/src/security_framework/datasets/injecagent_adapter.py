from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    SecurityDecision,
    SecurityEvent,
)


class InjecAgentAdapter:
    DATASET_NAME = "InjecAgent"
    DATASET_REPOSITORY = (
        "https://github.com/uiuc-kang-lab/InjecAgent"
    )

    @staticmethod
    def _load_json_array(
        path: Path,
    ) -> list[dict[str, Any]]:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array in {path}"
            )

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    @staticmethod
    def _load_jsonl(
        path: Path,
    ) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []

        with path.open(
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
                    item = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at {path}:{line_number}"
                    ) from exc

                if isinstance(item, dict):
                    records.append(item)

        return records

    @staticmethod
    def _safe_string(value: Any) -> str:
        if isinstance(value, str):
            return value

        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _normalize_tool_response(
        value: Any,
    ) -> str:
        return InjecAgentAdapter._safe_string(
            value
        ).strip()

    @staticmethod
    def _remove_injection_placeholder(
        template: Any,
    ) -> str:
        text = InjecAgentAdapter._safe_string(
            template
        )

        placeholders = [
            "<Attacker Instruction>",
            "<Attacker Instruction >",
            "{Attacker Instruction}",
        ]

        for placeholder in placeholders:
            text = text.replace(
                placeholder,
                "",
            )

        return text.strip()

    def convert_attack_records(
        self,
        input_file: str | Path,
        *,
        attack_family: str,
        setting: str,
    ) -> list[SecurityEvent]:
        path = Path(input_file)
        records = self._load_json_array(path)

        events: list[SecurityEvent] = []

        for index, record in enumerate(records):
            tool_response = (
                record.get("Tool Response")
                or record.get("Tool response")
                or record.get("tool_response")
            )

            if tool_response is None:
                raise ValueError(
                    f"Record {index} in {path} "
                    "does not contain Tool Response."
                )

            record_id = (
                f"{attack_family}-{setting}-{index:04d}"
            )

            events.append(
                SecurityEvent(
                    event_id=f"INJECAGENT-{record_id}",
                    scenario_id=f"INJECAGENT-{record_id}",
                    source_agent_id=(
                        "injecagent-tool-environment"
                    ),
                    source_agent_role=(
                        "Public Benchmark Tool Environment"
                    ),
                    event_type=EventType.TOOL_RESPONSE,
                    content_summary=(
                        self._normalize_tool_response(
                            tool_response
                        )
                    ),
                    expected_decision=(
                        SecurityDecision.BLOCK
                    ),
                    attack_type=(
                        AttackType.PROMPT_INJECTION
                    ),
                    source_agent_state=AgentState.NORMAL,
                    metadata={
                        "synthetic": False,
                        "dataset_source": self.DATASET_NAME,
                        "dataset_record_id": record_id,
                        "attack_family": attack_family,
                        "setting": setting,
                        "surface": "tool_response",
                        "user_instruction": self._safe_string(
                            record.get(
                                "User Instruction",
                                "",
                            )
                        ),
                        "user_tool": self._safe_string(
                            record.get(
                                "User Tool",
                                "",
                            )
                        ),
                        "attacker_tools": record.get(
                            "Attacker Tools",
                            [],
                        ),
                        "evaluation_only_attacker_instruction": (
                            self._safe_string(
                                record.get(
                                    "Attacker Instruction",
                                    "",
                                )
                            )
                        ),
                    },
                )
            )

        return events

    def convert_benign_user_cases(
        self,
        input_file: str | Path,
    ) -> list[SecurityEvent]:
        path = Path(input_file)
        records = self._load_jsonl(path)

        events: list[SecurityEvent] = []

        for index, record in enumerate(records):
            template = record.get(
                "Tool Response Template"
            )

            if template is None:
                continue

            record_id = f"benign-{index:04d}"

            events.append(
                SecurityEvent(
                    event_id=f"INJECAGENT-{record_id}",
                    scenario_id=f"INJECAGENT-{record_id}",
                    source_agent_id=(
                        "injecagent-tool-environment"
                    ),
                    source_agent_role=(
                        "Public Benchmark Tool Environment"
                    ),
                    event_type=EventType.TOOL_RESPONSE,
                    content_summary=(
                        self._remove_injection_placeholder(
                            template
                        )
                    ),
                    expected_decision=(
                        SecurityDecision.ALLOW
                    ),
                    attack_type=AttackType.NONE,
                    source_agent_state=AgentState.NORMAL,
                    metadata={
                        "synthetic": False,
                        "dataset_source": self.DATASET_NAME,
                        "dataset_record_id": record_id,
                        "attack_family": "benign",
                        "surface": (
                            "tool_response_template"
                        ),
                        "user_instruction": self._safe_string(
                            record.get(
                                "User Instruction",
                                "",
                            )
                        ),
                        "user_tool": self._safe_string(
                            record.get(
                                "User Tool",
                                "",
                            )
                        ),
                    },
                )
            )

        return events

    @staticmethod
    def write_jsonl(
        events: Iterable[SecurityEvent],
        output_file: str | Path,
    ) -> Path:
        path = Path(output_file)
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:
            for event in events:
                file.write(
                    event.model_dump_json()
                )
                file.write("\n")

        return path
