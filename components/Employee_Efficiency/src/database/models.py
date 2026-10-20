from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        create_engine, inspect)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)      # pseudonym
    role: Mapped[str] = mapped_column(String(40))
    team: Mapped[str] = mapped_column(String(40))
    hire_year: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="Active")


class KPIRecord(Base):
    """One KPI value for one employee for one closed month. Stored data is always confirmed."""
    __tablename__ = "kpi_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    kpi_code: Mapped[str] = mapped_column(String(30))
    period: Mapped[str] = mapped_column(String(7))                   # 'YYYY-MM'
    value: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(10), default="confirmed")
    n_obs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    __table_args__ = (Index("ix_kpi_emp_period", "employee_id", "period"),)


class ContextRecord(Base):
    """Operational context per employee-month (workload, complexity, system and market conditions)."""
    __tablename__ = "context_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period: Mapped[str] = mapped_column(String(7))
    jobs_assigned: Mapped[float] = mapped_column(Float)
    avg_complexity: Mapped[float] = mapped_column(Float)             # 1 (simple) - 5 (complex)
    overtime_hours: Mapped[float] = mapped_column(Float)
    leave_days: Mapped[float] = mapped_column(Float)
    system_downtime_hours: Mapped[float] = mapped_column(Float)
    price_change_pct: Mapped[float] = mapped_column(Float)           # market/price change vs last year
    competitor_offers: Mapped[float] = mapped_column(Float)          # competing offers seen by customers
    budget_constrained_share: Mapped[float] = mapped_column(Float)   # share of customers citing budget
    avg_equipment_age: Mapped[float] = mapped_column(Float)
    parts_wait_share: Mapped[float] = mapped_column(Float, default=0.0)
    incomplete_input_share: Mapped[float] = mapped_column(Float, default=0.0)


class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    period: Mapped[str] = mapped_column(String(7))
    text: Mapped[str] = mapped_column(Text)


class Recommendation(Base):
    """A recommendation produced by the agent. Nothing is 'taken' until a human approves it."""
    __tablename__ = "recommendations"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    as_of: Mapped[str] = mapped_column(String(7))
    cause: Mapped[str] = mapped_column(String(20))
    headline: Mapped[str] = mapped_column(String(200))
    actions: Mapped[str] = mapped_column(Text)                        # JSON list
    priority: Mapped[str] = mapped_column(String(10))
    monitor_kpis: Mapped[str] = mapped_column(Text)                   # JSON list
    diagnosis_summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(12), default="pending")  # pending/approved/modified/rejected
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    intervention: Mapped[Optional["Intervention"]] = relationship(back_populates="recommendation", uselist=False)


class Intervention(Base):
    """Created when a manager approves a recommendation; tracked at later checkpoints (closed loop)."""
    __tablename__ = "interventions"
    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    start_period: Mapped[str] = mapped_column(String(7))
    baseline_score: Mapped[float] = mapped_column(Float)              # recent-3-month score at approval
    followup_period: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    followup_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # improved/no_change/worsened
    recommendation: Mapped[Recommendation] = relationship(back_populates="intervention")


class HROutcome(Base):
    """Ground-truth historical review labels used for benchmark evaluation."""
    __tablename__ = "hr_outcomes"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    cycle_year: Mapped[int] = mapped_column(Integer)
    has_deviation: Mapped[bool] = mapped_column(Boolean)
    root_cause: Mapped[str] = mapped_column(String(20))               # workload/skill/process/external/none


class HRReview(Base):
    __tablename__ = "hr_reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    review_cycle: Mapped[str] = mapped_column(String(20))
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    manager_comment: Mapped[str] = mapped_column(Text, default="")
    action_taken: Mapped[str] = mapped_column(String(200), default="")


class DataQualityLog(Base):
    __tablename__ = "data_quality_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(36))
    stage: Mapped[str] = mapped_column(String(40))
    source_file: Mapped[str] = mapped_column(String(120))
    rule: Mapped[str] = mapped_column(String(120))
    rows_before: Mapped[int] = mapped_column(Integer)
    rows_after: Mapped[int] = mapped_column(Integer)
    rows_affected: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(40))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))


_SQLITE_COLUMN_MIGRATIONS = {
    "employees": {
        "status": "VARCHAR(20) NOT NULL DEFAULT 'Active'",
    },
    "kpi_records": {
        "n_obs": "INTEGER",
    },
    "context_records": {
        "parts_wait_share": "FLOAT NOT NULL DEFAULT 0.0",
        "incomplete_input_share": "FLOAT NOT NULL DEFAULT 0.0",
    },
}


def init_db(database_engine: Engine = engine) -> None:
    """Create missing tables and add new columns without replacing existing data."""
    Base.metadata.create_all(database_engine)
    if database_engine.dialect.name != "sqlite":
        return

    with database_engine.begin() as connection:
        for table_name, columns in _SQLITE_COLUMN_MIGRATIONS.items():
            for column_name, definition in columns.items():
                inspector = inspect(connection)
                if table_name not in inspector.get_table_names():
                    continue
                existing = {column["name"] for column in inspector.get_columns(table_name)}
                if column_name not in existing:
                    connection.exec_driver_sql(
                        f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}'
                    )


def reset_db() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    print(f"Database ready: {DATABASE_URL}")
