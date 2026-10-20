from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from security_framework.models import AttackType, EventType, SecurityDecision, SecurityEvent
from security_framework.workspace import SecurityWorkspaceDatabase
from security_framework.monitors import (
    BehaviorAnomalyMonitor,
    DataMinimizationMonitor,
    PolicyToolMonitor,
    SemanticPromptMonitor,
)


NORMAL_ACTIVITY = {
    "tool_call_frequency": 3,
    "restricted_resource_attempts": 0,
    "failed_authorization_count": 0,
    "external_api_calls": 1,
    "database_query_count": 2,
    "sensitive_resource_attempts": 0,
}


def load_cases(path, limit):
    if limit <= 0:
        return []
    with path.open(encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    return rows[:limit]


def load_tasks(path, limit):
    if limit <= 0:
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))[:limit]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def events(project, attacks, benign, tasks):
    public = project / "data" / "public" / "injecagent"
    for name, expected, count in [
        ("test_cases_ds_base.jsonl", SecurityDecision.BLOCK, attacks),
        ("benign_user_cases.jsonl", SecurityDecision.ALLOW, benign),
    ]:
        for row in load_cases(public / name, count):
            event = SecurityEvent.model_validate(row)
            event.metadata.pop("behavior_features", None)
            event.metadata["behavior_features"] = dict(NORMAL_ACTIVITY)
            event.metadata["activity_origin"] = "controlled_context_not_enterprise_logs"
            yield event, {
                "source": "InjecAgent", "source_file": name,
                "reference_scope": "semantic_prompt_only",
                "reference_decision": expected.value,
                "field_labels_verified": False,
            }

    for row in tasks:
        event = SecurityEvent(
            event_id="FIELD-" + row["case_id"],
            scenario_id="FIELD-" + row["case_id"],
            source_agent_id="field-evaluation",
            source_agent_role=row["role"],
            event_type=EventType.RESOURCE_ACCESS,
            requested_resource=row["resource"],
            content_summary=row["prompt"],
            expected_decision=SecurityDecision.REVIEW,
            attack_type=AttackType.NONE,
            metadata={
                "prompt_text": row["prompt"],
                "behavior_features": dict(NORMAL_ACTIVITY),
                "activity_origin": "controlled_context_not_enterprise_logs",
            },
        )
        yield event, {
            "source": "authored_enterprise_task", "source_file": "field_necessity_tasks.csv",
            "reference_scope": "unreviewed_field_necessity",
            "reference_decision": "",
            "field_labels_verified": False,
        }


def make_monitors(project):
    settings = json.loads((project / "config" / "monitor_settings.json").read_text())[
        "semantic_prompt_monitor"
    ]
    return [
        SemanticPromptMonitor(
            model_id=settings["model_id"],
            review_threshold=float(settings["review_threshold"]),
            block_threshold=float(settings["block_threshold"]),
        ),
        DataMinimizationMonitor(
            project / "config" / "data_minimization.json",
            project / "config" / "policies.json",
        ),
        PolicyToolMonitor(project / "config" / "policies.json"),
        BehaviorAnomalyMonitor(
            project / "data" / "behavior_baseline" / "normal_agent_behavior.csv",
            project / "config" / "behavior_monitor.json",
        ),
    ]


def monitor_observations(monitors, cases, database=None):
    observations = []
    for event, provenance in cases:
        for monitor in monitors:
            try:
                result = monitor.evaluate(event)
            except Exception as exc:
                raise RuntimeError(
                    f"{monitor.monitor_id} failed on {event.event_id}: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc
            if "FIELD_SELECTOR_UNAVAILABLE" in result.reason_codes:
                raise RuntimeError(
                    "Qwen selection could not complete. Start Ollama and install the configured model."
                )
            reference = (
                provenance["reference_decision"]
                if monitor.monitor_id == "semantic-monitor" and provenance["source"] == "InjecAgent"
                else ""
            )
            projected_fields = ""
            projection_verified = ""
            if (database is not None and provenance["source"] == "authored_enterprise_task"
                    and result.monitor_id == "data-minimization-monitor"
                    and result.decision == SecurityDecision.ALLOW):
                frame = database.fetch_selected_resource(
                    event.requested_resource, result.metadata["selected_fields"]
                )
                projected_fields = json.dumps(list(frame.columns))
                projection_verified = str(
                    list(frame.columns) == result.metadata["selected_fields"]
                )
            observations.append({
                "event_id": event.event_id,
                "source": provenance["source"],
                "source_file": provenance["source_file"],
                "monitor_id": result.monitor_id,
                "monitor_type": result.monitor_type.value,
                "event_type": event.event_type.value,
                "decision": result.decision.value,
                "risk_score": round(result.risk_score, 8),
                "confidence": round(result.confidence, 8),
                "latency_ms": round(result.latency_ms, 4),
                "reason_codes": json.dumps(result.reason_codes),
                "reference_decision": reference,
                "benchmark_match": (
                    str(result.decision.value == reference) if reference else ""
                ),
                "selected_fields": json.dumps(result.metadata.get("selected_fields", [])),
                "sqlite_result_columns": projected_fields,
                "sqlite_projection_verified": projection_verified,
                "removed_fields": json.dumps(result.metadata.get("removed_fields", [])),
                "selector": result.metadata.get("selector", ""),
                "reference_scope": provenance["reference_scope"],
                "field_labels_verified": False,
                "activity_origin": event.metadata.get("activity_origin", ""),
            })
    return observations


def fault_replay(observations):
    output = []
    for row in observations:
        current = row["decision"]
        for name, injected in [
            ("false_allow", "ALLOW"),
            ("false_block", "BLOCK"),
            ("unavailable", "REVIEW"),
        ]:
            output.append({
                "event_id": row["event_id"],
                "source": row["source"],
                "monitor_id": row["monitor_id"],
                "fault_mode": name,
                "original_observed_decision": current,
                "altered_decision": injected,
                "observable_change": injected != current,
                "fault_label": 1,
                "measurement_origin": "controlled_replay_of_real_monitor_output",
            })
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Record actual security-monitor executions")
    parser.add_argument("--attack-limit", type=int, default=10)
    parser.add_argument("--benign-limit", type=int, default=5)
    parser.add_argument("--task-limit", type=int, default=12)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    if min(args.attack_limit, args.benign_limit, args.task_limit) < 0:
        parser.error("Limits must not be negative")
    if sum((args.attack_limit, args.benign_limit, args.task_limit)) == 0:
        parser.error("Select at least one case")

    project = ROOT
    tasks_file = project / "data" / "evaluation" / "field_necessity_tasks.csv"
    source_files = [
        project / "data/public/injecagent/test_cases_ds_base.jsonl",
        project / "data/public/injecagent/benign_user_cases.jsonl",
        tasks_file,
        project / "config/data_minimization.json",
        project / "config/monitor_settings.json",
        project / "config/policies.json",
    ]
    monitors = make_monitors(project)
    cases = list(events(project, args.attack_limit, args.benign_limit,
                        load_tasks(tasks_file, args.task_limit)))
    with TemporaryDirectory() as directory:
        db = SecurityWorkspaceDatabase(Path(directory) / "local_test.db")
        rows = monitor_observations(monitors, cases, database=db)
    replay = fault_replay(rows)
    output = args.output or project / "results" / "monitor_validation" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
    )
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "monitor_observations.csv", rows)
    write_csv(output / "controlled_faults.csv", replay)
    semantic = [r for r in rows if r["monitor_id"] == "semantic-monitor" and r["reference_decision"]]
    summary = {
        "event_count": len(cases), "actual_monitor_observations": len(rows),
        "controlled_fault_records": len(replay),
        "semantic_benchmark_cases": len(semantic),
        "semantic_benchmark_exact_decision_matches": sum(r["benchmark_match"] == "True" for r in semantic),
        "independently_reviewed_field_labels": 0,
        "field_selection_accuracy": None,
        "successful_sqlite_projection_checks": sum(r["sqlite_projection_verified"] == "True" for r in rows),
        "sqlite_records_are_demonstration_data": True,
        "enterprise_behavior_log_cases": 0,
        "faults_are_simulated": True,
        "models_ran": ["Prompt Guard 2 86M"] + (
            ["Qwen2.5 via Ollama"] if any(r["selector"] == "ollama" for r in rows) else []
        ),
        "notes": "Benchmark decisions are proxies for injection presence; field-necessity labels remain unverified.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": {str(path.relative_to(project)): sha256(path) for path in source_files},
        "execution_script_sha256": sha256(Path(__file__)),
        "monitor_source_sha256": {
            str(path.relative_to(project)): sha256(path)
            for path in (project / "src/security_framework/monitors").glob("*_monitor.py")
        },
        "source_kind": {"InjecAgent": "public_research_benchmark",
                        "authored_enterprise_task": "author_defined_no_expert_review"},
        "runtime": {"ollama_model": json.loads((project / "config/data_minimization.json").read_text())["ollama_model"],
                    "semantic_model": monitors[0].model_id},
        "labels": "Only the semantic benchmark includes a reference attack/benign label; these do not independently certify monitor decisions.",
        "reproducibility_note": "Record exact installed Hugging Face model revision and Ollama model digest before publication.",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rows)} observed decisions and {len(replay)} controlled faults to {output}")
    print("Field-necessity precision/recall remain unreported until independent review.")
    return output


if __name__ == "__main__":
    main()
