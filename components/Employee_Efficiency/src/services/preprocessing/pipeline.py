"""Run the full source-export preprocessing pipeline and rebuild SQLite."""
from __future__ import annotations

import re
import uuid

import pandas as pd

from src.config import DATA_DIR, DATA_END, DATA_START
from src.database.models import (
    ContextRecord,
    Employee,
    Feedback,
    HRReview,
    KPIRecord,
    SessionLocal,
    reset_db,
)
from src.schemas.kpi import ROLE_LABELS, Role
from src.services import working_time
from src.services.preprocessing.cleaning import load_and_clean
from src.services.preprocessing.context_calc import calculate_context
from src.services.preprocessing.kpi_calc import calculate_kpis
from src.services.preprocessing.pseudonymise import apply_map, build_map
from src.services.preprocessing.utils import QualityLogger


def _install_holidays(holidays: pd.DataFrame) -> None:
    """Add exported public holidays to the shared working-time calendar."""
    exported = {
        pd.Timestamp(value).date()
        for value in holidays["date"].dropna()
    }
    working_time.HOLIDAYS = working_time.HOLIDAYS | exported


def _pseudonymise(data: dict[str, pd.DataFrame], mapping: dict[str, str]) -> None:
    """Replace every employee-number field before data reaches persistence."""
    data["employees"] = apply_map(data["employees"], ["employee_no"], mapping)
    data["employees"]["code"] = data["employees"]["employee_no"]
    data["employees"] = data["employees"].sort_values("code").reset_index(drop=True)
    data["jobs"] = apply_map(data["jobs"], ["assigned_by", "technician_no", "closed_by"], mapping)
    data["proposals"] = apply_map(data["proposals"], ["coordinator_no", "processor_no"], mapping)
    data["contracts"] = apply_map(data["contracts"], ["processor_no"], mapping)
    data["attendance"] = apply_map(data["attendance"], ["employee_no"], mapping)
    data["reviews"] = apply_map(data["reviews"], ["employee_no"], mapping)
    data["feedback"] = apply_map(data["feedback"], ["employee_no"], mapping)
    for frame, columns in (
        (data["reviews"], ["manager_comment", "action_taken"]),
        (data["feedback"], ["comment_text"]),
    ):
        for column in columns:
            frame[column] = frame[column].map(
                lambda value: re.sub(r"(?<!\d)\d{6}(?!\d)", "[redacted]", str(value))
            )


def _persist(data: dict[str, pd.DataFrame], logger: QualityLogger, run_id: str) -> dict[str, int]:
    """Persist pseudonymized employees and derived facts to the SQLAlchemy database."""
    employees = data["employees"]
    kpis = calculate_kpis(data)
    contexts = calculate_context(data)
    before_kpis = len(kpis)
    before_contexts = len(contexts)
    kpis = [row for row in kpis if DATA_START <= str(row["period"]) <= DATA_END]
    contexts = [row for row in contexts if DATA_START <= str(row["period"]) <= DATA_END]
    logger.record("aggregation", "all source files", "outside_configured_period",
                  before_kpis + before_contexts, len(kpis) + len(contexts),
                  before_kpis - len(kpis) + before_contexts - len(contexts), "exclude",
                  f"Retained periods {DATA_START} through {DATA_END}.")
    id_by_code: dict[str, int] = {}

    with SessionLocal() as session:
        for row in employees.itertuples(index=False):
            employee = Employee(
                code=str(row.code),
                role=str(row.role),
                team=str(row.team),
                hire_year=int(row.hire_year) if not pd.isna(row.hire_year) else 0,
                status=str(row.status),
            )
            session.add(employee)
            session.flush()
            id_by_code[str(row.code)] = int(employee.id)

        session.add_all([
            KPIRecord(
                employee_id=id_by_code[str(row["employee_code"])],
                kpi_code=str(row["kpi_code"]),
                period=str(row["period"]),
                value=float(row["value"]),
                status="confirmed",
                n_obs=int(row["n_obs"]),
            )
            for row in kpis
        ])
        session.add_all([
            ContextRecord(employee_id=id_by_code[str(row["employee_code"])], **{
                key: value for key, value in row.items() if key != "employee_code"
            })
            for row in contexts
        ])

        feedback = data["feedback"]
        session.add_all([
            Feedback(
                employee_id=id_by_code[str(row.employee_no)],
                period=str(row.period),
                text=str(row.comment_text),
            )
            for row in feedback.itertuples(index=False)
            if not pd.isna(row.employee_no) and not pd.isna(row.period) and str(row.comment_text).strip()
        ])
        reviews = data["reviews"]
        session.add_all([
            HRReview(
                employee_id=id_by_code[str(row.employee_no)],
                review_cycle=str(row.review_cycle),
                rating=None if pd.isna(row.rating) else int(row.rating),
                manager_comment=str(row.manager_comment),
                action_taken=str(row.action_taken),
            )
            for row in reviews.itertuples(index=False)
            if not pd.isna(row.employee_no)
        ])
        session.commit()
        counts = {
            "employees": len(employees),
            "kpi_records": len(kpis),
            "context_records": len(contexts),
            "feedback": int(session.query(Feedback).count()),
            "hr_reviews": int(session.query(HRReview).count()),
            "quality_log": len(logger.entries),
        }
    logger.write_db(run_id)
    return counts


def run_preprocessing() -> dict[str, object]:
    """Clean, pseudonymize, aggregate, and persist the latest available CSV exports."""
    logger = QualityLogger()
    run_id = "RUN-" + "-".join(uuid.uuid4().hex)
    if not (DATA_DIR / "raw").is_dir():
        raise FileNotFoundError(f"Required raw data directory is missing: {DATA_DIR / 'raw'}")
    reset_db()
    data = load_and_clean(logger)
    if data["employees"]["role"].eq("unknown").any():
        raise ValueError("One or more employee designations could not be mapped to a supported role.")
    _install_holidays(data["holidays"])
    mapping = build_map(data["employees"])
    _pseudonymise(data, mapping)
    if data["employees"]["code"].isna().any():
        raise ValueError("Employee pseudonymization produced an unmapped employee.")
    counts = _persist(data, logger, run_id)
    logger.render_markdown(DATA_DIR.parent / "docs" / "DATA_QUALITY_REPORT.md")
    summary = {
        "run_id": run_id,
        "counts": counts,
        "quality": logger,
        "employees": data["employees"],
    }
    print_summary(summary)
    return summary


def print_summary(summary: dict[str, object]) -> None:
    """Print aggregate table counts, KPI coverage by role, and observed data months."""
    counts = summary["counts"]
    quality = summary["quality"]
    assert isinstance(counts, dict) and isinstance(quality, QualityLogger)
    print("Preprocessing complete")
    print(f"Run ID: {summary['run_id']}")
    print("\nTable rows")
    for table, count in counts.items():
        print(f"  {table:<18} {count:>8}")
    with SessionLocal() as session:
        rows = session.query(KPIRecord).all()
        employee_roles = {employee.id: employee.role for employee in session.query(Employee).all()}
        records = [{"role": employee_roles[row.employee_id], "period": row.period, "kpi_code": row.kpi_code}
                   for row in rows]
    frame = pd.DataFrame(records)
    print("\nKPI records by role")
    if frame.empty:
        print("  No KPI records met the minimum sample-size requirements.")
    else:
        for role, group in frame.groupby("role"):
            print(f"  {ROLE_LABELS[Role(role)]:<30} {len(group):>8}")
        print(f"\nMonths covered: {frame['period'].min()} through {frame['period'].max()}")
        coverage = frame.groupby(["role", "period"])["kpi_code"].nunique()
        print(f"Role-month KPI cells: {len(coverage)}")
    print(f"Quality rules recorded: {len(quality.entries)}")


def main() -> None:
    """CLI entry point for a complete deterministic preprocessing run."""
    run_preprocessing()


if __name__ == "__main__":
    main()
