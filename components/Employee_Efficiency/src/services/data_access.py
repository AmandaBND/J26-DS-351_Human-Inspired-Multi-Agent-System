"""Loads everything the agent needs for a given `as_of` month into one in-memory bundle.

Only months <= as_of are loaded, so the agent can never 'see the future'.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.config import BASELINE_YEAR
from src.database.models import DataQualityLog, Employee, HRReview, SessionLocal, engine, init_db
from src.schemas.assessment import DeviationResult
from src.schemas.kpi import KPI_REGISTRY, Role, role_lag
from src.services import kpi_engine, trajectory


@dataclass
class DataBundle:
    as_of: str
    employees: pd.DataFrame
    kpi: pd.DataFrame               # with benchmark + index columns
    monthly: pd.DataFrame
    context: pd.DataFrame
    feedback: pd.DataFrame
    benchmarks: pd.DataFrame
    attendance: pd.DataFrame
    hr_reviews: pd.DataFrame
    baseline_overall: dict = field(default_factory=dict)
    deviations: dict = field(default_factory=dict)   # employee_id -> DeviationResult
    data_through: dict = field(default_factory=dict)
    stale_months: dict = field(default_factory=dict)
    insufficient_data: dict = field(default_factory=dict)
    insufficient_reason: dict = field(default_factory=dict)
    quality_log: pd.DataFrame = field(default_factory=pd.DataFrame)

    def emp(self, code: str):
        row = self.employees[self.employees["code"] == code]
        if row.empty:
            raise KeyError(f"Unknown employee code: {code}")
        return row.iloc[0]

    def overall_series(self, emp_id: int) -> pd.Series:
        m = self.monthly[self.monthly["employee_id"] == emp_id]
        series = m.set_index("period")["overall"].dropna()
        series.index = series.index.astype(str)
        return series


def available_periods() -> list[str]:
    init_db()
    return pd.read_sql(
        "SELECT DISTINCT period FROM kpi_records ORDER BY period", engine
    )["period"].tolist()


def load_bundle(as_of: str) -> DataBundle:
    employees = pd.read_sql("SELECT id, code, role, team, hire_year, status FROM employees", engine)
    kpi = pd.read_sql(
        "SELECT employee_id, kpi_code, period, value FROM kpi_records WHERE period <= ?", engine, params=(as_of,))
    with SessionLocal() as session:
        has_import_quality_log = session.query(DataQualityLog).count() > 0
    legacy_demo = len(employees) == 20 and not has_import_quality_log
    if not legacy_demo and not kpi.empty:
        maturity_cutoff = {
            code: (pd.Period(as_of, freq="M") - definition.maturity_lag_months).strftime("%Y-%m")
            for code, definition in KPI_REGISTRY.items()
        }
        kpi = kpi[kpi.apply(lambda row: row["period"] <= maturity_cutoff[row["kpi_code"]], axis=1)]
    kpi = kpi.merge(employees[["id", "role"]].rename(columns={"id": "employee_id"}), on="employee_id")
    bench = kpi_engine.compute_benchmarks(kpi)
    kpi = kpi_engine.add_indices(kpi, bench)
    monthly = kpi_engine.monthly_scores(kpi)
    context = pd.read_sql("SELECT * FROM context_records WHERE period <= ?", engine, params=(as_of,))
    feedback = pd.read_sql("SELECT * FROM feedback WHERE period <= ?", engine, params=(as_of,))
    attendance = context[["employee_id", "period", "leave_days", "overtime_hours"]].copy()
    with SessionLocal() as session:
        reviews = session.query(HRReview).all()
        hr_reviews = pd.DataFrame([{
            "employee_id": review.employee_id,
            "review_cycle": review.review_cycle,
            "rating": review.rating,
            "manager_comment": review.manager_comment,
            "action_taken": review.action_taken,
        } for review in reviews])
        quality_entries = session.query(DataQualityLog).all()
        quality_log = pd.DataFrame([{
            "stage": entry.stage,
            "source_file": entry.source_file,
            "rule": entry.rule,
            "rows_before": entry.rows_before,
            "rows_after": entry.rows_after,
            "rows_affected": entry.rows_affected,
            "action": entry.action,
            "detail": entry.detail,
        } for entry in quality_entries])

    bundle = DataBundle(
        as_of=as_of,
        employees=employees,
        kpi=kpi,
        monthly=monthly,
        context=context,
        feedback=feedback,
        benchmarks=bench,
        attendance=attendance,
        hr_reviews=hr_reviews,
        quality_log=quality_log,
    )
    for emp_id in employees["id"]:
        s = bundle.overall_series(emp_id)
        base = s[s.index.str[:4] == str(BASELINE_YEAR)]
        bundle.baseline_overall[emp_id] = (
            float(base.mean()) if len(base) else float(s.iloc[:12].mean()) if len(s) else np.nan
        )
        through = str(s.index[-1]) if len(s) else ""
        stale = (
            int((pd.Period(as_of, freq="M") - pd.Period(through, freq="M")).n)
            if through else int((pd.Period(as_of, freq="M") - pd.Period("1900-01", freq="M")).n)
        )
        bundle.data_through[emp_id] = through
        bundle.stale_months[emp_id] = stale
        role = Role(employees.loc[employees["id"] == emp_id, "role"].iloc[0])
        recent = s.iloc[-3:]
        has_recent_gap = (
            len(recent) == 3
            and int((pd.Period(str(recent.index[-1]), freq="M")
                     - pd.Period(str(recent.index[0]), freq="M")).n) > 3
        )
        latest_attendance = attendance[
            (attendance["employee_id"] == emp_id) & (attendance["period"] <= as_of)
        ].sort_values("period")
        extended_leave = bool(
            not latest_attendance.empty and latest_attendance.iloc[-1]["leave_days"] >= 15
        )
        reasons = []
        if stale > role_lag(role) + 1:
            reasons.append("extended leave" if extended_leave else "recent performance data is too old")
        if len(s) < 6:
            reasons.append("fewer than six complete months of performance data")
        if has_recent_gap:
            reasons.append("the three most recent complete months span more than four calendar months")
        bundle.insufficient_data[emp_id] = bool(reasons)
        bundle.insufficient_reason[emp_id] = "; ".join(dict.fromkeys(reasons))
        if bundle.insufficient_data[emp_id] or not np.isfinite(bundle.baseline_overall[emp_id]):
            bundle.deviations[emp_id] = DeviationResult(
                is_deviating=False, severity="none", drop=0.0, slope_per_month=0.0, months_below=0,
            )
        else:
            bundle.deviations[emp_id] = trajectory.detect_deviation(s, bundle.baseline_overall[emp_id])
    return bundle
