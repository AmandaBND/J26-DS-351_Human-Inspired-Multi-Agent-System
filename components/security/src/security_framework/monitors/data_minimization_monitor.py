from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from time import perf_counter
from urllib.request import Request, urlopen

from security_framework.models import SecurityDecision, SecurityEvent
from .base import MonitorType, SecurityMonitor


class DataMinimizationMonitor(SecurityMonitor):
    def __init__(self, settings_file, policy_file, selector=None):
        super().__init__("semantic-monitor", MonitorType.DATA_MINIMIZATION)
        self.settings = json.loads(Path(settings_file).read_text(encoding="utf-8"))
        self.policy = json.loads(Path(policy_file).read_text(encoding="utf-8"))
        self.selector = selector or self._select

    def _select(self, task, columns):
        if self.settings["selector"] == "ollama":
            instruction = (
                "Select only necessary columns for this task. Return a JSON object "
                "with a fields array using only supplied column names. "
                "Do not invent or expand permissions. "
                f"Task: {task[:800]}\nAvailable columns and purposes: "
                f"{json.dumps(columns)}"
            )
            payload = json.dumps({
                "model": self.settings["ollama_model"],
                "prompt": instruction, "stream": False,
                "format": "json",
            }).encode("utf-8")
            request = Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload, headers={"Content-Type": "application/json"},
            )
            with urlopen(request, timeout=20) as response:
                answer = json.loads(response.read().decode("utf-8"))
            chosen = json.loads(answer["response"])["fields"]
            if not isinstance(chosen, list):
                raise ValueError("Column selection must be a list")
            if any(not isinstance(item, str) or item not in columns for item in chosen):
                raise ValueError("Selection contains unknown columns")
            return chosen
        tokens = set(re.findall(r"[a-z0-9]+", task.lower()))
        return [name for name, terms in columns.items()
                if tokens.intersection(name.split("_")) or tokens.intersection(terms)]

    def evaluate(self, event: SecurityEvent):
        started = perf_counter()
        resource = event.requested_resource
        if not resource:
            resource = self.settings["tool_resources"].get(event.metadata.get("tool_name", ""))
        if not resource:
            return self._build_result(event=event, decision=SecurityDecision.ALLOW,
                risk_score=0.0, confidence=1.0, started_at=started,
                reason_codes=["NO_DATA_REQUEST"], metadata={"selected_fields": [], "removed_fields": []})

        role = self.policy.get("roles", {}).get(event.source_agent_role)
        globally_blocked = resource in self.policy.get("always_block_resources", [])
        allowed = bool(role and resource in role.get("allowed_resources", []) and
                       resource not in role.get("blocked_resources", []) and not globally_blocked)
        if not allowed:
            return self._build_result(event=event, decision=SecurityDecision.BLOCK,
                risk_score=1.0, confidence=1.0, started_at=started,
                reason_codes=["RESOURCE_NOT_AUTHORIZED"], metadata={"selected_fields": [], "removed_fields": []})

        columns = self.settings["columns"].get(resource)
        if not columns:
            return self._build_result(event=event, decision=SecurityDecision.REVIEW,
                risk_score=0.6, confidence=1.0, started_at=started,
                reason_codes=["RESOURCE_SCHEMA_UNKNOWN"], metadata={"selected_fields": [], "removed_fields": []})

        task = event.metadata.get("prompt_text") or event.content_summary
        try:
            selected = list(dict.fromkeys(self.selector(task, columns)))
            if any(column not in columns for column in selected):
                raise ValueError("Unknown selected column")
        except (KeyError, ValueError, OSError, TimeoutError):
            selected = []

        personal = set(self.settings["personal_fields"])
        transformed = {}
        secret_available = bool(os.getenv("DATA_PSEUDONYM_KEY"))
        for column in selected:
            if column in personal:
                transformed[column] = "PSEUDONYMIZE" if secret_available else "REMOVE"
            else:
                transformed[column] = "ALLOW"
        disclosed = [field for field, action in transformed.items() if action != "REMOVE"]
        if not disclosed:
            decision, risk, reason = SecurityDecision.REVIEW, 0.6, "INSUFFICIENT_SAFE_FIELDS"
        else:
            decision, risk, reason = SecurityDecision.ALLOW, 0.1, "MINIMIZED_DATA_READY"
        return self._build_result(event=event, decision=decision,
            risk_score=risk, confidence=1.0, started_at=started,
            reason_codes=[reason], metadata={
                "resource": resource, "selected_fields": disclosed,
                "removed_fields": [name for name in columns if name not in disclosed],
                "field_actions": transformed, "selector": self.settings["selector"],
            })

    @staticmethod
    def pseudonymize(value: object) -> str:
        secret = os.environ["DATA_PSEUDONYM_KEY"].encode("utf-8")
        digest = hmac.new(secret, str(value).encode("utf-8"), hashlib.sha256).hexdigest()
        return "Person-" + digest[:10]
