"""Build monthly operating context from attendance, service, outage, and AMC data."""
from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd

from src.config import EXTRACT_DT
from src.services.preprocessing.kpi_calc import _period


COMPETITOR_TERMS = ("lower", "cheaper", "price match", "higher than market")


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _outage_hours(row: pd.Series) -> float:
    if pd.isna(row["start_dt"]):
        return 0.0
    end = EXTRACT_DT if pd.isna(row["end_dt"]) else pd.Timestamp(row["end_dt"]).to_pydatetime()
    return max(0.0, (end - pd.Timestamp(row["start_dt"]).to_pydatetime()).total_seconds() / 3600)


def _compounded_price_change(prices: pd.DataFrame, period: str) -> float:
    end = pd.Period(period, freq="M").end_time
    start = end - pd.DateOffset(months=12)
    relevant = prices[
        prices["effective_date"].notna()
        & (prices["effective_date"] > start)
        & (prices["effective_date"] <= end)
    ]
    if relevant.empty:
        return 0.0
    factors = 1 + pd.to_numeric(relevant["change_pct"], errors="coerce").dropna() / 100
    return (float(math.prod(factors)) - 1) * 100


def calculate_context(data: dict[str, pd.DataFrame]) -> list[dict[str, object]]:
    """Return pseudonymous employee-month context records for all observed activity."""
    employees = data["employees"]
    jobs = data["jobs"].copy()
    proposals = data["proposals"].copy()
    contracts = data["contracts"].copy()
    attendance = data["attendance"]
    downtime = data["downtime"]
    competitors = data["competitors"]
    prices = data["prices"]

    jobs["period"] = jobs["request_dt"].map(_period)
    contracts["period"] = contracts["contract_created_dt"].map(_period)
    proposals["period"] = proposals["proposal_dt"].map(_period)
    downtime["period"] = downtime["start_dt"].map(_period)
    competitors["period"] = competitors["note_date"].map(_period)
    prices["effective_period"] = prices["effective_date"].map(_period)

    attendance_by = attendance.set_index(["employee_no", "period"]) if not attendance.empty else None
    records: list[dict[str, object]] = []

    for employee in employees.itertuples(index=False):
        code = str(employee.code)
        role = str(employee.role)
        if role == "technician":
            assigned = jobs[jobs["technician_no"] == code]
            job_count_column = "technician_no"
        elif role == "tpo_service":
            assigned = jobs[jobs["assigned_by"] == code]
            job_count_column = "assigned_by"
        elif role == "amc_processing":
            assigned = contracts[contracts["processor_no"] == code]
            job_count_column = "processor_no"
        else:
            assigned = proposals[proposals["coordinator_no"] == code]
            job_count_column = "coordinator_no"

        activity_months = set(assigned["period"].dropna().astype(str))
        if attendance_by is not None:
            activity_months.update(
                attendance.loc[attendance["employee_no"].eq(code), "period"].dropna().astype(str)
            )
        for month in sorted(activity_months):
            month_att = pd.DataFrame()
            if attendance_by is not None and (employee.employee_no, month) in attendance_by.index:
                month_att = attendance_by.loc[[(employee.employee_no, month)]]

            if role in {"technician", "tpo_service"}:
                month_jobs = assigned[assigned["period"].eq(month) & ~assigned["status"].eq("Cancelled")]
                jobs_assigned = int(len(month_jobs))
                complexity = float(month_jobs["complexity_score"].mean()) if not month_jobs.empty else 3.0
            elif role == "amc_processing":
                month_rows = assigned[assigned["period"].eq(month)]
                jobs_assigned = int(len(month_rows))
                complexity = 3.0
            else:
                month_rows = assigned[assigned["period"].eq(month)]
                jobs_assigned = int(len(month_rows))
                complexity = 3.0

            outage_rows = downtime[downtime["period"].eq(month)]
            downtime_hours = float(outage_rows.apply(_outage_hours, axis=1).sum())
            if role == "contracts_coordinator":
                price_pct = _compounded_price_change(prices, month)
                competitor_rows = competitors[competitors["period"].eq(month)]
                offers = int(competitor_rows["note_text"].astype(str).str.casefold().str.contains(
                    "|".join(COMPETITOR_TERMS), regex=True).sum())
                proposal_rows = proposals[
                    proposals["coordinator_no"].eq(code) & proposals["period"].eq(month)
                    & proposals["status"].eq("Rejected") & proposals["reason_recorded"]
                ]
                budget_share = _ratio(
                    int(proposal_rows["rejection_reason"].astype(str).str.casefold().str.contains("budget").sum()),
                    len(proposal_rows),
                )
            else:
                price_pct = 0.0
                offers = 0
                budget_share = 0.0

            if role == "technician":
                completed = assigned[
                    assigned["period"].eq(month)
                    & assigned["completion_dt"].notna()
                    & assigned["status"].isin({"Closed", "Completed"})
                    & assigned["job_type"].isin({"Breakdown repair", "Repeat visit"})
                ]
                parts_share = _ratio(int(completed["parts_wait_hrs"].fillna(0).gt(0).sum()), len(completed))
            else:
                parts_share = 0.0

            if role == "amc_processing":
                incomplete_contracts = assigned[
                    assigned["period"].eq(month) & assigned["contract_created_dt"].notna()
                    & assigned["data_complete_flag"].notna()
                ]
                incomplete_share = _ratio(
                    int((~incomplete_contracts["data_complete_flag"].astype(bool)).sum()),
                    len(incomplete_contracts),
                )
            else:
                incomplete_share = 0.0

            records.append({
                "employee_code": code,
                "period": month,
                "jobs_assigned": jobs_assigned,
                "avg_complexity": complexity,
                "overtime_hours": float(month_att["overtime_hours"].mean()) if not month_att.empty else 0.0,
                "leave_days": float(month_att["leave_days"].mean()) if not month_att.empty else 0.0,
                "system_downtime_hours": downtime_hours,
                "price_change_pct": price_pct,
                "competitor_offers": float(offers),
                "budget_constrained_share": budget_share,
                "avg_equipment_age": 0.0,
                "parts_wait_share": parts_share,
                "incomplete_input_share": incomplete_share,
            })
    return records
