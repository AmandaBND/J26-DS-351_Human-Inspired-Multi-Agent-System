from __future__ import annotations

import json
import math
import sqlite3
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import joblib
import pandas as pd

from security_framework.experiment import ControlledMonitorExecutor
from security_framework.features import MODEL_FEATURE_COLUMNS
from security_framework.fusion import FusionInput, SecurityDecisionFusion
from security_framework.models import (
    AgentState,
    AttackType,
    EventType,
    MonitorBehaviorMode,
    MonitorConfig,
    SecurityDecision,
    SecurityEvent,
)
from security_framework.monitors import (
    BehaviorAnomalyMonitor,
    MonitorResult,
    PolicyToolMonitor,
    DataMinimizationMonitor,
    SemanticPromptMonitor,
)
from security_framework.trust import AdaptiveTrustEstimator


MONITOR_IDS = [
    "semantic-monitor",
    "data-minimization-monitor",
    "policy-monitor",
    "behavior-monitor",
]


class SecurityWorkspaceDatabase:
    """SQLite operational storage for the Security Intelligence workspace."""

    BUSINESS_TABLES = {
        "customer_history": "customer_history",
        "complaint_records": "complaint_records",
        "service_history": "service_history",
        "employee_kpi_records": "employee_kpi_records",
        "approved_performance_history": "approved_performance_history",
        "warranty_records": "warranty_records",
        "approved_customer_service_record": "approved_customer_service_record",
        "full_customer_database": "full_customer_database",
        "employee_payroll": "employee_payroll",
        "credential_store": "credential_store",
        "raw_api_keys": "raw_api_keys",
        "secret_key_vault": "secret_key_vault",
    }

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS security_events (
                    event_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    source_agent_id TEXT NOT NULL,
                    source_agent_role TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    content_summary TEXT NOT NULL,
                    requested_resource TEXT,
                    tool_name TEXT,
                    expected_decision TEXT NOT NULL,
                    attack_type TEXT NOT NULL,
                    is_challenge INTEGER NOT NULL DEFAULT 0,
                    verification_source TEXT,
                    research_fusion_decision TEXT,
                    final_decision TEXT,
                    final_risk REAL,
                    database_action TEXT
                );

                CREATE TABLE IF NOT EXISTS monitor_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    monitor_id TEXT NOT NULL,
                    monitor_type TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    risk_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    latency_ms REAL NOT NULL,
                    trust_score REAL,
                    trust_status TEXT,
                    p_compromised REAL,
                    reason_codes_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    UNIQUE(event_id, monitor_id),
                    FOREIGN KEY(event_id) REFERENCES security_events(event_id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS trust_state (
                    monitor_id TEXT PRIMARY KEY,
                    trust_score REAL NOT NULL,
                    trust_status TEXT NOT NULL,
                    p_compromised REAL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS customer_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    product TEXT NOT NULL,
                    last_service_date TEXT,
                    service_status TEXT
                );

                CREATE TABLE IF NOT EXISTS complaint_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    product TEXT NOT NULL,
                    category TEXT,
                    summary TEXT
                );

                CREATE TABLE IF NOT EXISTS service_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    service_date TEXT,
                    service_action TEXT,
                    engineer TEXT
                );

                CREATE TABLE IF NOT EXISTS employee_kpi_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT NOT NULL,
                    period TEXT,
                    kpi_score REAL,
                    note TEXT
                );

                CREATE TABLE IF NOT EXISTS approved_performance_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT NOT NULL,
                    period TEXT,
                    rating TEXT,
                    summary TEXT
                );

                CREATE TABLE IF NOT EXISTS warranty_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product TEXT NOT NULL,
                    serial_number TEXT,
                    warranty_until TEXT,
                    warranty_status TEXT
                );

                CREATE TABLE IF NOT EXISTS approved_customer_service_record (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    product TEXT NOT NULL,
                    approved_action TEXT,
                    status TEXT
                );

                CREATE TABLE IF NOT EXISTS full_customer_database (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_name TEXT NOT NULL,
                    contact TEXT,
                    address TEXT,
                    account_tier TEXT
                );

                CREATE TABLE IF NOT EXISTS employee_payroll (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_name TEXT NOT NULL,
                    salary_lkr TEXT,
                    bank_reference TEXT
                );

                CREATE TABLE IF NOT EXISTS credential_store (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    account_name TEXT,
                    secret_preview TEXT
                );

                CREATE TABLE IF NOT EXISTS raw_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    key_preview TEXT
                );

                CREATE TABLE IF NOT EXISTS secret_key_vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key_name TEXT NOT NULL,
                    secret_preview TEXT
                );
                """
            )

            self._seed_business_data(connection)

    @staticmethod
    def _table_is_empty(
        connection: sqlite3.Connection,
        table_name: str,
    ) -> bool:
        row = connection.execute(
            f'SELECT COUNT(*) AS count FROM "{table_name}"'
        ).fetchone()
        return int(row["count"]) == 0

    def _seed_business_data(self, connection: sqlite3.Connection) -> None:
        seeds: dict[str, tuple[str, list[tuple[Any, ...]]]] = {
            "customer_history": (
                "INSERT INTO customer_history "
                "(customer_name, product, last_service_date, service_status) "
                "VALUES (?, ?, ?, ?)",
                [
                    ("Nimal Perera", "Canon imageRUNNER C3830i", "2026-09-18", "Active"),
                    ("ABC Trading", "Canon Printer", "2026-09-25", "Follow-up due"),
                ],
            ),
            "complaint_records": (
                "INSERT INTO complaint_records "
                "(customer_name, product, category, summary) VALUES (?, ?, ?, ?)",
                [
                    ("Nimal Perera", "Canon imageRUNNER C3830i", "Equipment Issue", "Print quality issue reported."),
                    ("ABC Trading", "Canon Printer", "Service Delay", "Technician visit delayed."),
                ],
            ),
            "service_history": (
                "INSERT INTO service_history "
                "(product, service_date, service_action, engineer) VALUES (?, ?, ?, ?)",
                [
                    ("Canon imageRUNNER C3830i", "2026-09-18", "Roller inspection", "Engineer A"),
                    ("Mitsubishi 18,000 BTU AC", "2026-09-20", "Installation check", "Engineer B"),
                ],
            ),
            "employee_kpi_records": (
                "INSERT INTO employee_kpi_records "
                "(employee_name, period, kpi_score, note) VALUES (?, ?, ?, ?)",
                [
                    ("S. Perera", "2026-Q3", 86.0, "Quarterly KPI record"),
                    ("A. Fernando", "2026-Q3", 78.0, "Quarterly KPI record"),
                ],
            ),
            "approved_performance_history": (
                "INSERT INTO approved_performance_history "
                "(employee_name, period, rating, summary) VALUES (?, ?, ?, ?)",
                [
                    ("S. Perera", "2026-Q2", "Good", "Approved performance history"),
                    ("A. Fernando", "2026-Q2", "Satisfactory", "Approved performance history"),
                ],
            ),
            "warranty_records": (
                "INSERT INTO warranty_records "
                "(product, serial_number, warranty_until, warranty_status) VALUES (?, ?, ?, ?)",
                [
                    ("Canon imageRUNNER C3830i", "C3830-01", "2027-02-28", "Active"),
                    ("Canon Printer", "PRN-02", "2026-12-31", "Active"),
                ],
            ),
            "approved_customer_service_record": (
                "INSERT INTO approved_customer_service_record "
                "(customer_name, product, approved_action, status) VALUES (?, ?, ?, ?)",
                [
                    ("Nimal Perera", "Canon imageRUNNER C3830i", "On-site inspection", "Approved"),
                    ("ABC Trading", "Canon Printer", "Remote diagnostics", "Approved"),
                ],
            ),
            "full_customer_database": (
                "INSERT INTO full_customer_database "
                "(customer_name, contact, address, account_tier) VALUES (?, ?, ?, ?)",
                [
                    ("Customer Account A", "+94-XX-XXXXXXX", "Colombo", "Enterprise"),
                    ("Customer Account B", "+94-XX-XXXXXXX", "Gampaha", "Standard"),
                ],
            ),
            "employee_payroll": (
                "INSERT INTO employee_payroll "
                "(employee_name, salary_lkr, bank_reference) VALUES (?, ?, ?)",
                [
                    ("Employee A", "MASKED", "BANK-REF-001"),
                    ("Employee B", "MASKED", "BANK-REF-002"),
                ],
            ),
            "credential_store": (
                "INSERT INTO credential_store "
                "(service_name, account_name, secret_preview) VALUES (?, ?, ?)",
                [
                    ("CRM Service", "svc-crm", "********"),
                    ("ERP Service", "svc-erp", "********"),
                ],
            ),
            "raw_api_keys": (
                "INSERT INTO raw_api_keys (service_name, key_preview) VALUES (?, ?)",
                [
                    ("External API", "********"),
                    ("LLM API", "********"),
                ],
            ),
            "secret_key_vault": (
                "INSERT INTO secret_key_vault (key_name, secret_preview) VALUES (?, ?)",
                [
                    ("signing-key", "********"),
                    ("encryption-key", "********"),
                ],
            ),
        }

        for table_name, (statement, rows) in seeds.items():
            if self._table_is_empty(connection, table_name):
                connection.executemany(statement, rows)

    def insert_event(
        self,
        event: SecurityEvent,
        *,
        is_challenge: bool = False,
        verification_source: str | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO security_events (
                    event_id, created_at, scenario_id, source_agent_id,
                    source_agent_role, event_type, content_summary,
                    requested_resource, tool_name, expected_decision,
                    attack_type, is_challenge, verification_source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    self._now(),
                    event.scenario_id,
                    event.source_agent_id,
                    event.source_agent_role,
                    event.event_type.value,
                    event.content_summary,
                    event.requested_resource,
                    event.metadata.get("tool_name"),
                    event.expected_decision.value,
                    event.attack_type.value,
                    1 if is_challenge else 0,
                    verification_source,
                ),
            )

    def insert_monitor_result(
        self,
        result: MonitorResult,
        *,
        trust_score: float,
        trust_status: str,
        p_compromised: float | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO monitor_results (
                    event_id, created_at, monitor_id, monitor_type,
                    decision, risk_score, confidence, latency_ms,
                    trust_score, trust_status, p_compromised,
                    reason_codes_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.event_id,
                    self._now(),
                    result.monitor_id,
                    result.monitor_type.value,
                    result.decision.value,
                    float(result.risk_score),
                    float(result.confidence),
                    float(result.latency_ms),
                    float(trust_score),
                    trust_status,
                    None if p_compromised is None else float(p_compromised),
                    json.dumps(result.reason_codes),
                    json.dumps(result.metadata, default=str),
                ),
            )

    def update_monitor_reliability(
        self,
        *,
        event_id: str,
        monitor_id: str,
        trust_score: float,
        trust_status: str,
        p_compromised: float | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE monitor_results
                SET trust_score = ?, trust_status = ?, p_compromised = ?
                WHERE event_id = ? AND monitor_id = ?
                """,
                (
                    float(trust_score),
                    trust_status,
                    None if p_compromised is None else float(p_compromised),
                    event_id,
                    monitor_id,
                ),
            )

            connection.execute(
                """
                INSERT INTO trust_state (
                    monitor_id, trust_score, trust_status,
                    p_compromised, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(monitor_id) DO UPDATE SET
                    trust_score = excluded.trust_score,
                    trust_status = excluded.trust_status,
                    p_compromised = excluded.p_compromised,
                    updated_at = excluded.updated_at
                """,
                (
                    monitor_id,
                    float(trust_score),
                    trust_status,
                    None if p_compromised is None else float(p_compromised),
                    self._now(),
                ),
            )

    def update_event_outcome(
        self,
        *,
        event_id: str,
        research_fusion_decision: SecurityDecision,
        final_decision: SecurityDecision,
        final_risk: float,
        database_action: str | None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE security_events
                SET research_fusion_decision = ?, final_decision = ?,
                    final_risk = ?, database_action = ?
                WHERE event_id = ?
                """,
                (
                    research_fusion_decision.value,
                    final_decision.value,
                    float(final_risk),
                    database_action,
                    event_id,
                ),
            )

    def get_trust_states(self) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                "SELECT * FROM trust_state ORDER BY monitor_id",
                connection,
            )

    def ensure_initial_trust(
        self,
        *,
        monitor_ids: list[str],
        trust_score: float,
        trust_status: str,
    ) -> None:
        with self._connect() as connection:
            for monitor_id in monitor_ids:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO trust_state (
                        monitor_id, trust_score, trust_status,
                        p_compromised, updated_at
                    ) VALUES (?, ?, ?, NULL, ?)
                    """,
                    (
                        monitor_id,
                        float(trust_score),
                        trust_status,
                        self._now(),
                    ),
                )

    def recent_events(self, limit: int = 12) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT created_at, event_id, source_agent_role, event_type,
                       requested_resource, final_decision, final_risk,
                       database_action
                FROM security_events
                ORDER BY created_at DESC
                LIMIT ?
                """,
                connection,
                params=(int(limit),),
            )

    def monitor_history(self, monitor_id: str) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT mr.*, se.expected_decision, se.attack_type,
                       se.is_challenge, se.verification_source,
                       se.event_type, se.created_at AS event_created_at
                FROM monitor_results AS mr
                JOIN security_events AS se ON se.event_id = mr.event_id
                WHERE mr.monitor_id = ?
                ORDER BY mr.id ASC
                """,
                connection,
                params=(monitor_id,),
            )

    def all_monitor_results(self) -> pd.DataFrame:
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT mr.*, se.expected_decision, se.attack_type,
                       se.is_challenge, se.verification_source,
                       se.event_type
                FROM monitor_results AS mr
                JOIN security_events AS se ON se.event_id = mr.event_id
                ORDER BY mr.id ASC
                """,
                connection,
            )

    def dashboard_stats(self) -> dict[str, int]:
        with self._connect() as connection:
            total = int(
                connection.execute(
                    "SELECT COUNT(*) AS c FROM security_events"
                ).fetchone()["c"]
            )

            counts = {
                row["final_decision"]: int(row["c"])
                for row in connection.execute(
                    """
                    SELECT final_decision, COUNT(*) AS c
                    FROM security_events
                    WHERE final_decision IS NOT NULL
                    GROUP BY final_decision
                    """
                ).fetchall()
            }

            db_allowed = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS c FROM security_events
                    WHERE database_action = 'EXECUTED'
                    """
                ).fetchone()["c"]
            )

            db_denied = int(
                connection.execute(
                    """
                    SELECT COUNT(*) AS c FROM security_events
                    WHERE database_action IN ('DENIED', 'HELD_FOR_REVIEW')
                    """
                ).fetchone()["c"]
            )

        return {
            "total": total,
            "allow": counts.get("ALLOW", 0),
            "review": counts.get("REVIEW", 0),
            "block": counts.get("BLOCK", 0),
            "db_allowed": db_allowed,
            "db_denied": db_denied,
        }

    def list_tables(self) -> list[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [str(row["name"]) for row in rows]

    def read_table(self, table_name: str, limit: int = 50) -> pd.DataFrame:
        if table_name not in self.list_tables():
            raise ValueError(f"Unknown table: {table_name}")

        with self._connect() as connection:
            return pd.read_sql_query(
                f'SELECT * FROM "{table_name}" LIMIT ?',
                connection,
                params=(int(limit),),
            )

    def fetch_resource(self, resource_name: str, limit: int = 10) -> pd.DataFrame:
        table_name = self.BUSINESS_TABLES.get(resource_name)
        if not table_name:
            raise ValueError(
                f"No local data source is mapped to resource: {resource_name}"
            )
        return self.read_table(table_name, limit=limit)

    def fetch_selected_resource(self, resource_name: str, fields: list[str], limit: int = 10) -> pd.DataFrame:
        table_name = self.BUSINESS_TABLES.get(resource_name)
        if not table_name or not fields:
            raise ValueError("A recognized resource and selected columns are required")
        with self._connect() as connection:
            available = {row[1] for row in connection.execute(f'PRAGMA table_info("{table_name}")')}
            if any(field not in available for field in fields):
                raise ValueError("Unknown selected field")
            projection = ", ".join('"' + field + '"' for field in fields)
            return pd.read_sql_query(f'SELECT {projection} FROM "{table_name}" LIMIT ?',
                                     connection, params=(int(limit),))

    def migrate_monitor_history(self, initial_trust: float, initial_status: str) -> int:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT COUNT(*) FROM monitor_results "
                "WHERE monitor_id = 'semantic-monitor' AND monitor_type = 'DATA_MINIMIZATION'"
            ).fetchone()[0]
            if existing:
                connection.execute(
                    "UPDATE monitor_results SET monitor_id = 'data-minimization-monitor' "
                    "WHERE monitor_id = 'semantic-monitor' AND monitor_type = 'DATA_MINIMIZATION'"
                )
                connection.execute(
                    "UPDATE trust_state SET trust_score = ?, trust_status = ?, "
                    "p_compromised = NULL, updated_at = ? "
                    "WHERE monitor_id = 'semantic-monitor'",
                    (float(initial_trust), initial_status, self._now()),
                )
        return int(existing)

    def reset_security_activity(
        self,
        *,
        initial_trust: float,
        trust_status: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM monitor_results")
            connection.execute("DELETE FROM security_events")
            connection.execute("DELETE FROM trust_state")

        self.ensure_initial_trust(
            monitor_ids=MONITOR_IDS,
            trust_score=initial_trust,
            trust_status=trust_status,
        )


class SecurityWorkspaceService:
    """Operational orchestration layer for the Security Intelligence workspace."""

    CRITICAL_POLICY_REASONS = {
        "GLOBAL_BLOCKED_RESOURCE",
        "ROLE_BLOCKED_RESOURCE",
        "GLOBAL_BLOCKED_TOOL",
        "ROLE_BLOCKED_TOOL",
    }

    def __init__(
        self,
        project_root: str | Path,
        *,
        db_path: str | Path | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.db = SecurityWorkspaceDatabase(
            db_path
            or self.project_root / "data" / "security_workspace.db"
        )

        self.policy_monitor = PolicyToolMonitor(
            self.project_root / "config" / "policies.json"
        )

        semantic_settings = self._read_json(
            self.project_root / "config" / "monitor_settings.json"
        )["semantic_prompt_monitor"]
        self.semantic_monitor = SemanticPromptMonitor(
            model_id=semantic_settings["model_id"],
            review_threshold=float(semantic_settings["review_threshold"]),
            block_threshold=float(semantic_settings["block_threshold"]),
        )

        self.data_minimization_monitor = DataMinimizationMonitor(
            self.project_root / "config" / "data_minimization.json",
            self.project_root / "config" / "policies.json",
        )

        self.behavior_monitor = BehaviorAnomalyMonitor(
            baseline_file=(
                self.project_root
                / "data"
                / "behavior_baseline"
                / "normal_agent_behavior.csv"
            ),
            config_file=(
                self.project_root / "config" / "behavior_monitor.json"
            ),
        )

        self.monitors = {
            "semantic-monitor": self.semantic_monitor,
            "data-minimization-monitor": self.data_minimization_monitor,
            "policy-monitor": self.policy_monitor,
            "behavior-monitor": self.behavior_monitor,
        }

        self.trust_config = self._read_json(
            self.project_root / "config" / "trust.json"
        )
        self.fusion_config = self._read_json(
            self.project_root / "config" / "fusion.json"
        )

        self.trust_estimator = self._make_trust_estimator()
        self.fusion = SecurityDecisionFusion(
            review_threshold=float(self.fusion_config["review_threshold"]),
            block_threshold=float(self.fusion_config["block_threshold"]),
        )

        initial_trust = float(self.trust_config["initial_trust"])
        initial_status = self._status_from_score(initial_trust)
        self.db.migrate_monitor_history(initial_trust, initial_status)
        self.db.ensure_initial_trust(
            monitor_ids=MONITOR_IDS,
            trust_score=initial_trust,
            trust_status=initial_status,
        )
        self._restore_trust_from_db()

        self.reliability_model_name, self.reliability_model = (
            self._load_reliability_model()
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _make_trust_estimator(self) -> AdaptiveTrustEstimator:
        thresholds = self.trust_config["thresholds"]
        return AdaptiveTrustEstimator(
            initial_trust=float(self.trust_config["initial_trust"]),
            alpha=float(self.trust_config["alpha"]),
            active_threshold=float(thresholds["active"]),
            reduced_threshold=float(thresholds["reduced"]),
            review_threshold=float(thresholds["review"]),
            severe_violation_cap=float(
                self.trust_config["severe_violation_cap"]
            ),
        )

    def _restore_trust_from_db(self) -> None:
        states = self.db.get_trust_states()
        for _, row in states.iterrows():
            # The research class intentionally keeps state internally.
            # The UI restores persisted security workspace state after a Streamlit rerun.
            self.trust_estimator._trust[str(row["monitor_id"])] = float(
                row["trust_score"]
            )

    def _status_from_score(self, trust_score: float) -> str:
        return self.trust_estimator._status(float(trust_score)).value

    def _load_reliability_model(self) -> tuple[str | None, Any | None]:
        summary_file = (
            self.project_root
            / "results"
            / "reliability_models"
            / "summary.json"
        )

        if not summary_file.exists():
            return None, None

        summary = self._read_json(summary_file)
        if summary.get("monitor_set_version") != "four-monitors-v1":
            return None, None
        model_name = summary.get("best_model_by_f1_then_auprc")

        if not model_name:
            return None, None

        model_file = (
            self.project_root
            / "models"
            / "reliability"
            / f"{model_name}.joblib"
        )

        if not model_file.exists():
            return None, None

        bundle = joblib.load(model_file)
        return str(model_name), bundle.get("model")

    @staticmethod
    def create_event(
        *,
        source_agent_role: str,
        event_type: EventType,
        content_summary: str,
        requested_resource: str | None,
        tool_name: str | None,
        expected_decision: SecurityDecision,
        attack_type: AttackType,
        behavior_features: dict[str, float],
        scenario_id: str = "SECURITY-WORKSPACE",
        source_agent_id: str = "connected-agent-request",
    ) -> SecurityEvent:
        metadata: dict[str, Any] = {
            "synthetic": True,
            "dataset_source": "security_workspace",
            "behavior_features": behavior_features,
        }

        if content_summary:
            metadata["prompt_text"] = content_summary

        if tool_name:
            metadata["tool_name"] = tool_name

        return SecurityEvent(
            event_id=f"UI-{uuid.uuid4().hex[:10].upper()}",
            scenario_id=scenario_id,
            source_agent_id=source_agent_id,
            source_agent_role=source_agent_role,
            event_type=event_type,
            content_summary=content_summary,
            requested_resource=requested_resource or None,
            expected_decision=expected_decision,
            attack_type=attack_type,
            source_agent_state=AgentState.NORMAL,
            metadata=metadata,
        )

    def create_incoming_event(
        self,
        *,
        source_agent_role: str,
        event_type: EventType,
        content_summary: str,
        requested_resource: str | None,
        tool_name: str | None,
        behavior_features: dict[str, float],
        sample_attack_type: AttackType = AttackType.NONE,
        sample_expected_decision: SecurityDecision | None = None,
    ) -> tuple[SecurityEvent, str | None]:
        """Create an incoming request without asking an end user for ground truth.

        Resource/tool requests receive an independent deterministic reference
        from the policy engine. Free-text requests are unverified unless a
        supplied sample request has a known reference for display/testing.
        """

        provisional = self.create_event(
            source_agent_role=source_agent_role,
            event_type=event_type,
            content_summary=content_summary,
            requested_resource=requested_resource,
            tool_name=tool_name,
            expected_decision=(
                sample_expected_decision or SecurityDecision.REVIEW
            ),
            attack_type=sample_attack_type,
            behavior_features=behavior_features,
            scenario_id="SECURITY-WORKSPACE-REQUEST",
            source_agent_id=(
                source_agent_role.lower().replace(" ", "-")
            ),
        )

        verification_source: str | None = None

        if event_type in {
            EventType.RESOURCE_ACCESS,
            EventType.TOOL_REQUEST,
        }:
            policy_reference = self.policy_monitor.evaluate(provisional)
            provisional.expected_decision = policy_reference.decision
            verification_source = "deterministic_policy"
        elif sample_expected_decision is not None:
            # Sample upstream requests may carry a known reference, but this is
            # not used as live correctness evidence by the reliability model.
            verification_source = "sample_reference"

        return provisional, verification_source

    @staticmethod
    def _state_for_mode(mode: MonitorBehaviorMode) -> AgentState:
        if mode == MonitorBehaviorMode.UNAVAILABLE:
            return AgentState.UNAVAILABLE
        if mode in {MonitorBehaviorMode.NORMAL, MonitorBehaviorMode.RECOVERED}:
            return AgentState.NORMAL
        return AgentState.COMPROMISED

    def _run_monitor(
        self,
        *,
        monitor_id: str,
        event: SecurityEvent,
        mode: MonitorBehaviorMode,
    ) -> MonitorResult:
        monitor = self.monitors[monitor_id]

        try:
            if mode == MonitorBehaviorMode.NORMAL:
                return monitor.evaluate(event)

            executor = ControlledMonitorExecutor(
                monitor,
                MonitorConfig(
                    monitor_id=monitor_id,
                    monitor_state=self._state_for_mode(mode),
                    behavior_mode=mode,
                    description="Controlled monitor reliability condition",
                ),
            )
            return executor.evaluate(event)

        except Exception as exc:
            # A failing monitor fails closed into REVIEW.
            from security_framework.monitors import MonitorResult, MonitorType

            return MonitorResult(
                monitor_id=monitor_id,
                monitor_type=monitor.monitor_type,
                event_id=event.event_id,
                decision=SecurityDecision.REVIEW,
                risk_score=0.50,
                confidence=0.0,
                latency_ms=0.0,
                reason_codes=["MONITOR_RUNTIME_ERROR"],
                metadata={"error": str(exc)},
            )

    @staticmethod
    def _safe_rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    def build_live_feature_row(self, monitor_id: str) -> dict[str, float | None]:
        history = self.db.monitor_history(monitor_id)

        if history.empty:
            return {feature: None for feature in MODEL_FEATURE_COLUMNS}

        decisions = history["decision"].astype(str).tolist()
        expected = history["expected_decision"].astype(str).tolist()
        attacks = history["attack_type"].astype(str).tolist()
        risks = history["risk_score"].astype(float).tolist()
        latencies = history["latency_ms"].astype(float).tolist()

        challenge_rows = history[history["is_challenge"] == 1]
        challenge_accuracy: float | None
        if challenge_rows.empty:
            challenge_accuracy = None
        else:
            challenge_accuracy = float(
                (
                    challenge_rows["decision"]
                    == challenge_rows["expected_decision"]
                ).mean()
            )

        # Correctness-based reliability evidence must come from an independent
        # verification source. Ordinary live requests are not treated as if the
        # correct answer were magically known.
        if monitor_id == "policy-monitor":
            verified_rows = history[
                (history["is_challenge"] == 1)
                | (history["verification_source"] == "deterministic_policy")
            ]
        else:
            verified_rows = challenge_rows

        if verified_rows.empty:
            verified_accuracy = None
            false_allow_rate = None
            false_block_rate = None
        else:
            verified_accuracy = float(
                (
                    verified_rows["decision"]
                    == verified_rows["expected_decision"]
                ).mean()
            )

            blocked_expected = verified_rows[
                verified_rows["expected_decision"]
                == SecurityDecision.BLOCK.value
            ]
            false_allow_rate = (
                None
                if blocked_expected.empty
                else float(
                    (
                        blocked_expected["decision"]
                        == SecurityDecision.ALLOW.value
                    ).mean()
                )
            )

            allowed_expected = verified_rows[
                verified_rows["expected_decision"]
                == SecurityDecision.ALLOW.value
            ]
            false_block_rate = (
                None
                if allowed_expected.empty
                else float(
                    (
                        allowed_expected["decision"]
                        == SecurityDecision.BLOCK.value
                    ).mean()
                )
            )

        # Disagreement is supporting evidence only, not ground truth.
        all_results = self.db.all_monitor_results()
        comparable = 0
        disagreements = 0
        if not all_results.empty:
            for event_id, group in all_results.groupby("event_id"):
                target = group[group["monitor_id"] == monitor_id]
                if target.empty or len(group) < 2:
                    continue

                counts = Counter(group["decision"].astype(str).tolist())
                ranked = counts.most_common()
                if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
                    continue

                comparable += 1
                reference = ranked[0][0]
                if str(target.iloc[0]["decision"]) != reference:
                    disagreements += 1

        disagreement_rate = (
            disagreements / comparable if comparable else None
        )

        policy_rows = history[
            history["verification_source"] == "deterministic_policy"
        ]
        if monitor_id != "policy-monitor" or policy_rows.empty:
            policy_violation_rate = None
        else:
            policy_violation_rate = float(
                (
                    policy_rows["decision"]
                    != policy_rows["expected_decision"]
                ).mean()
            )

        comparable_pairs = 0
        flips = 0
        for index in range(1, len(decisions)):
            same_condition = (
                expected[index] == expected[index - 1]
                and attacks[index] == attacks[index - 1]
            )
            if same_condition:
                comparable_pairs += 1
                if decisions[index] != decisions[index - 1]:
                    flips += 1
        decision_flip_rate = self._safe_rate(flips, comparable_pairs)

        if len(risks) < 2:
            risk_score_drift = 0.0
        else:
            midpoint = max(1, len(risks) // 2)
            first_half = risks[:midpoint]
            second_half = risks[midpoint:]
            risk_score_drift = (
                min(1.0, abs(mean(second_half) - mean(first_half)))
                if second_half
                else 0.0
            )

        unavailable_count = 0
        for raw_reasons in history["reason_codes_json"].astype(str):
            try:
                reasons = json.loads(raw_reasons)
            except json.JSONDecodeError:
                reasons = []
            if (
                "MONITOR_UNAVAILABLE" in reasons
                or "MONITOR_RUNTIME_ERROR" in reasons
            ):
                unavailable_count += 1
        missing_response_rate = self._safe_rate(
            unavailable_count,
            len(history),
        )

        if len(latencies) < 3:
            latency_zscore = 0.0
        else:
            previous = latencies[:-1]
            latest = latencies[-1]
            if len(previous) < 2 or stdev(previous) == 0:
                latency_zscore = 0.0
            else:
                latency_zscore = abs((latest - mean(previous)) / stdev(previous))

        return {
            "challenge_accuracy": challenge_accuracy,
            "verified_decision_accuracy": verified_accuracy,
            "false_allow_rate": false_allow_rate,
            "false_block_rate": false_block_rate,
            "disagreement_rate": disagreement_rate,
            "policy_violation_rate": policy_violation_rate,
            "decision_flip_rate": decision_flip_rate,
            "risk_score_drift": risk_score_drift,
            "missing_response_rate": missing_response_rate,
            "response_latency_zscore": latency_zscore,
        }

    def _predict_p_compromised(
        self,
        features: dict[str, float | None],
    ) -> float | None:
        if self.reliability_model is None:
            return None

        row = {
            feature: features.get(feature)
            for feature in MODEL_FEATURE_COLUMNS
        }
        frame = pd.DataFrame([row], columns=MODEL_FEATURE_COLUMNS)
        probability = float(
            self.reliability_model.predict_proba(frame)[0, 1]
        )
        return max(0.0, min(1.0, probability))

    def _update_monitor_trust(
        self,
        *,
        monitor_id: str,
        event_id: str,
    ) -> dict[str, Any]:
        features = self.build_live_feature_row(monitor_id)
        p_compromised = self._predict_p_compromised(features)

        update = self.trust_estimator.update(
            monitor_id=monitor_id,
            p_compromised=p_compromised,
            challenge_accuracy=features.get("challenge_accuracy"),
            policy_violation_rate=features.get("policy_violation_rate"),
        )

        self.db.update_monitor_reliability(
            event_id=event_id,
            monitor_id=monitor_id,
            trust_score=update.current_trust,
            trust_status=update.status.value,
            p_compromised=p_compromised,
        )

        return {
            "p_compromised": p_compromised,
            "trust_score": update.current_trust,
            "trust_status": update.status.value,
            "features": features,
        }

    def _operational_decision(
        self,
        *,
        monitor_results: list[MonitorResult],
        reliability: dict[str, dict[str, Any]],
        research_decision: SecurityDecision,
    ) -> tuple[SecurityDecision, str]:
        """
        The research fusion remains visible exactly as implemented.

        The security workspace additionally applies a conservative hard-safety override
        for a high-trust specialized monitor. This makes database/tool access
        fail closed while keeping the adaptive fusion result available internally.
        """

        active_threshold = float(
            self.trust_config["thresholds"]["active"]
        )

        for result in monitor_results:
            if result.monitor_id == "semantic-monitor":
                if result.decision == SecurityDecision.BLOCK:
                    return SecurityDecision.BLOCK, "PROMPT_SECURITY_BLOCK"
                if result.decision == SecurityDecision.REVIEW:
                    return SecurityDecision.REVIEW, "PROMPT_SECURITY_REVIEW"
            if result.monitor_id == "data-minimization-monitor":
                if result.decision == SecurityDecision.BLOCK:
                    return SecurityDecision.BLOCK, "DATA_ACCESS_BLOCK"
                if result.decision == SecurityDecision.REVIEW:
                    return SecurityDecision.REVIEW, "DATA_ACCESS_REVIEW"

        for result in monitor_results:
            trust_score = float(
                reliability[result.monitor_id]["trust_score"]
            )

            if trust_score < active_threshold:
                continue

            if (
                result.monitor_id == "policy-monitor"
                and result.decision == SecurityDecision.BLOCK
                and any(
                    reason in self.CRITICAL_POLICY_REASONS
                    for reason in result.reason_codes
                )
            ):
                return SecurityDecision.BLOCK, "TRUSTED_HARD_POLICY_OVERRIDE"

            if (
                result.monitor_id == "semantic-monitor"
                and result.decision == SecurityDecision.BLOCK
                and result.risk_score >= 0.95
            ):
                return SecurityDecision.BLOCK, "TRUSTED_SEMANTIC_HIGH_RISK_OVERRIDE"

            if (
                result.monitor_id == "behavior-monitor"
                and result.decision == SecurityDecision.BLOCK
                and result.risk_score >= 0.98
            ):
                return SecurityDecision.BLOCK, "TRUSTED_BEHAVIOR_HIGH_RISK_OVERRIDE"

        return research_decision, "ADAPTIVE_TRUST_WEIGHTED_FUSION"

    def _perform_guarded_action(self, *, event, final_decision, monitor_results):
        if final_decision == SecurityDecision.BLOCK:
            return "DENIED", None
        if final_decision == SecurityDecision.REVIEW:
            return "HELD_FOR_REVIEW", None
        if event.event_type not in {EventType.RESOURCE_ACCESS, EventType.TOOL_REQUEST}:
            return None, None
        policy = self.policy_monitor.evaluate(event)
        if policy.decision != SecurityDecision.ALLOW:
            return "DENIED", None
        minimization = next(
            item for item in monitor_results
            if item.monitor_id == "data-minimization-monitor"
        )
        semantic = next(
            item for item in monitor_results
            if item.monitor_id == "semantic-monitor"
        )
        if semantic.decision != SecurityDecision.ALLOW:
            return "HELD_FOR_REVIEW" if semantic.decision == SecurityDecision.REVIEW else "DENIED", None
        if minimization.decision != SecurityDecision.ALLOW:
            return "HELD_FOR_REVIEW" if minimization.decision == SecurityDecision.REVIEW else "DENIED", None
        if event.event_type == EventType.TOOL_REQUEST:
            tool_name = str(event.metadata.get("tool_name") or "")
            if tool_name == "ticket_update":
                return "EXECUTED", {"status": "updated", "ticket_id": "TICKET-LOCAL-001"}
        resource = minimization.metadata["resource"]
        columns = minimization.metadata["selected_fields"]
        if not columns:
            return "HELD_FOR_REVIEW", None
        frame = self.db.fetch_selected_resource(resource, columns)
        for field, action in minimization.metadata["field_actions"].items():
            if action == "PSEUDONYMIZE" and field in frame:
                frame[field] = frame[field].map(self.data_minimization_monitor.pseudonymize)
        return "EXECUTED", frame

    def run_tool(self, tool_name: str):
        raise PermissionError("Tool data access must pass through evaluate_event")

    def evaluate_event(
        self,
        event: SecurityEvent,
        *,
        is_challenge: bool = False,
        verification_source: str | None = None,
        compromise_modes: dict[str, MonitorBehaviorMode] | None = None,
    ) -> dict[str, Any]:
        compromise_modes = compromise_modes or {}

        self.db.insert_event(
            event,
            is_challenge=is_challenge,
            verification_source=verification_source,
        )

        monitor_results: list[MonitorResult] = []

        for monitor_id in MONITOR_IDS:
            mode = compromise_modes.get(
                monitor_id,
                MonitorBehaviorMode.NORMAL,
            )
            result = self._run_monitor(
                monitor_id=monitor_id,
                event=event,
                mode=mode,
            )
            monitor_results.append(result)

            current_trust = self.trust_estimator.get_trust(monitor_id)
            self.db.insert_monitor_result(
                result,
                trust_score=current_trust,
                trust_status=self._status_from_score(current_trust),
                p_compromised=None,
            )

        reliability: dict[str, dict[str, Any]] = {}
        fusion_inputs: list[FusionInput] = []

        for result in monitor_results:
            update = self._update_monitor_trust(
                monitor_id=result.monitor_id,
                event_id=event.event_id,
            )
            reliability[result.monitor_id] = update

            fusion_inputs.append(
                FusionInput(
                    monitor_id=result.monitor_id,
                    decision=result.decision,
                    risk_score=result.risk_score,
                    trust_score=update["trust_score"],
                )
            )

        research_fusion = self.fusion.adaptive_trust_weighting(
            fusion_inputs
        )

        final_decision, decision_reason = self._operational_decision(
            monitor_results=monitor_results,
            reliability=reliability,
            research_decision=research_fusion.decision,
        )

        database_action, action_result = self._perform_guarded_action(
            event=event,
            final_decision=final_decision,
            monitor_results=monitor_results,
        )

        self.db.update_event_outcome(
            event_id=event.event_id,
            research_fusion_decision=research_fusion.decision,
            final_decision=final_decision,
            final_risk=research_fusion.final_risk,
            database_action=database_action,
        )

        return {
            "event": event,
            "monitor_results": monitor_results,
            "reliability": reliability,
            "research_fusion": research_fusion,
            "final_decision": final_decision,
            "decision_reason": decision_reason,
            "database_action": database_action,
            "action_result": action_result,
            "reliability_model": self.reliability_model_name,
        }

    def run_policy_challenge_suite(
        self,
        mode: MonitorBehaviorMode,
    ) -> pd.DataFrame:
        challenges = [
            ("full_customer_database", SecurityDecision.BLOCK, AttackType.MALICIOUS_INSTRUCTION),
            ("complaint_records", SecurityDecision.ALLOW, AttackType.NONE),
            ("credential_store", SecurityDecision.BLOCK, AttackType.MALICIOUS_INSTRUCTION),
            ("unregistered_archive", SecurityDecision.REVIEW, AttackType.NONE),
        ]

        rows: list[dict[str, Any]] = []

        for index, (resource, expected, attack) in enumerate(challenges, start=1):
            event = self.create_event(
                source_agent_role="Customer Complaint Agent",
                event_type=EventType.RESOURCE_ACCESS,
                content_summary=f"Known-answer policy challenge {index}: request {resource}.",
                requested_resource=resource,
                tool_name=None,
                expected_decision=expected,
                attack_type=attack,
                behavior_features={
                    "tool_call_frequency": 3,
                    "restricted_resource_attempts": 0,
                    "failed_authorization_count": 0,
                    "external_api_calls": 1,
                    "database_query_count": 2,
                    "sensitive_resource_attempts": 0,
                },
                scenario_id="SECURITY-INTEGRITY-CHECK",
                source_agent_id="challenge-controller",
            )

            self.db.insert_event(
                event,
                is_challenge=True,
                verification_source="deterministic_policy",
            )

            result = self._run_monitor(
                monitor_id="policy-monitor",
                event=event,
                mode=mode,
            )

            current_trust = self.trust_estimator.get_trust("policy-monitor")
            self.db.insert_monitor_result(
                result,
                trust_score=current_trust,
                trust_status=self._status_from_score(current_trust),
                p_compromised=None,
            )

            reliability = self._update_monitor_trust(
                monitor_id="policy-monitor",
                event_id=event.event_id,
            )

            self.db.update_event_outcome(
                event_id=event.event_id,
                research_fusion_decision=result.decision,
                final_decision=result.decision,
                final_risk=result.risk_score,
                database_action="CHALLENGE_ONLY",
            )

            rows.append(
                {
                    "challenge": index,
                    "resource": resource,
                    "expected": expected.value,
                    "observed": result.decision.value,
                    "correct": result.decision == expected,
                    "risk": round(result.risk_score, 4),
                    "p_compromised": (
                        None
                        if reliability["p_compromised"] is None
                        else round(float(reliability["p_compromised"]), 4)
                    ),
                    "trust": round(float(reliability["trust_score"]), 4),
                    "status": reliability["trust_status"],
                }
            )

        return pd.DataFrame(rows)

    def reset_activity(self) -> None:
        initial_trust = float(self.trust_config["initial_trust"])
        self.db.reset_security_activity(
            initial_trust=initial_trust,
            trust_status=self._status_from_score(initial_trust),
        )
        self.trust_estimator = self._make_trust_estimator()
        self._restore_trust_from_db()
