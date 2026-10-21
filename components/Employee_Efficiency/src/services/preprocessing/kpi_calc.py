"""Deterministic monthly KPI derivation from cleaned service and AMC exports."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Callable

import numpy as np
import pandas as pd

from src.config import CONVERSION_WINDOW_DAYS, EXTRACT_DT, MIN_N, MIN_CSAT_RESPONSES, REPEAT_WINDOW_DAYS
from src.schemas.kpi import KPI_REGISTRY, ROLE_KPIS, Role
from src.services import working_time

MetricRows = list[dict[str, object]]
COMPLETED_STATUSES = {"Closed", "Completed"}
PRIORITIES = {"P1", "P2", "P3"}


def _period(value: object) -> str | None:
    if pd.isna(value):
        return None
    return pd.Timestamp(value).strftime("%Y-%m")


def _valid_time(value: object) -> datetime | None:
    return None if pd.isna(value) else pd.Timestamp(value).to_pydatetime()


def _minutes(start: object, end: object) -> float:
    a, b = _valid_time(start), _valid_time(end)
    return float("nan") if a is None or b is None or b < a else working_time.working_minutes_between(a, b)


def _hours(start: object, end: object) -> float:
    return _minutes(start, end) / 60


def _emit(
    rows: MetricRows,
    code: str,
    employee_code: str,
    period: str,
    values: pd.Series | list[float] | np.ndarray,
    calculate: Callable[[pd.Series], float],
    minimum: int,
) -> None:
    """Append one finite KPI only when its observed denominator meets the rule."""
    if isinstance(values, pd.DataFrame):
        source = pd.Series(dtype="float64")
    elif isinstance(values, pd.Series):
        source = values
    else:
        source = pd.Series(values)
    observed = pd.to_numeric(source, errors="coerce").dropna()
    if len(observed) < minimum:
        return
    value = float(calculate(observed))
    if np.isfinite(value):
        rows.append({
            "employee_code": employee_code,
            "kpi_code": code,
            "period": period,
            "value": value,
            "n_obs": int(len(observed)),
        })


def _mean(values: pd.Series) -> float:
    return float(values.mean())


def _median(values: pd.Series) -> float:
    return float(values.median())


def _completed_jobs(jobs: pd.DataFrame) -> pd.DataFrame:
    return jobs[jobs["completion_dt"].notna() & jobs["status"].isin(COMPLETED_STATUSES)]


def _mature_jobs(jobs: pd.DataFrame, days: int) -> pd.DataFrame:
    cutoff = pd.Timestamp(EXTRACT_DT) - pd.Timedelta(days=days)
    return jobs[jobs["completion_dt"].notna() & (jobs["completion_dt"] <= cutoff)]


def _followup_counts(
    due_dates: list[pd.Timestamp], done_dates: list[pd.Timestamp]
) -> tuple[int, int, int]:
    """Greedily match each due date to the earliest unused completion within seven days."""
    due_count = on_time = matched_count = 0
    unused = sorted(done_dates)
    for due in sorted(due_dates):
        if due > pd.Timestamp(EXTRACT_DT).normalize():
            continue
        due_count += 1
        match = next((index for index, done in enumerate(unused)
                      if due <= done <= due + pd.Timedelta(days=7)), None)
        if match is not None:
            done = unused.pop(match)
            matched_count += 1
            on_time += int(done <= due)
    return on_time, matched_count, due_count


def calculate_kpis(data: dict[str, pd.DataFrame]) -> MetricRows:
    """Derive all role KPIs, enforcing sample sizes and reporting month attribution."""
    rows: MetricRows = []
    employees = data["employees"]
    jobs = data["jobs"]
    proposals = data["proposals"]
    contracts = data["contracts"]
    repeat_parent_ids = set(jobs["parent_job_id"].dropna().astype(str).str.strip()) - {""}

    for employee in employees.itertuples(index=False):
        code = str(employee.code)
        role = str(employee.role)
        min_obs = MIN_N[role]

        if role in {Role.TECHNICIAN.value, Role.TPO_SERVICE.value}:
            attribution = "technician_no" if role == Role.TECHNICIAN.value else "assigned_by"
            person_jobs = jobs[jobs[attribution] == code].copy()
            person_jobs["period"] = person_jobs["request_dt"].map(_period)
            for period, group in person_jobs.dropna(subset=["period"]).groupby("period"):
                completed = _completed_jobs(group)
                if role == Role.TECHNICIAN.value:
                    sla = completed[completed["sla_due_dt"].notna()]
                    _emit(rows, "TECH_SLA", code, period,
                          (sla["completion_dt"] <= sla["sla_due_dt"]).astype(float) * 100,
                          _mean, min_obs)

                    eligible_ftfr = _mature_jobs(group, REPEAT_WINDOW_DAYS)
                    eligible_ftfr = eligible_ftfr[
                        eligible_ftfr["parent_job_id"].fillna("").astype(str).str.strip().eq("")
                        & eligible_ftfr["job_type"].isin({"Breakdown repair", "Installation"})
                    ]
                    if len(eligible_ftfr) >= min_obs:
                        resolved = ~eligible_ftfr["job_id"].astype(str).isin(repeat_parent_ids)
                        _emit(rows, "TECH_FTFR", code, period, resolved.astype(float) * 100, _mean, min_obs)

                    breakdown = completed[completed["job_type"].eq("Breakdown repair")]
                    _emit(rows, "TECH_MTTR", code, period, breakdown["repair_time_hrs"], _mean, min_obs)
                    response = group[
                        group["priority"].isin(PRIORITIES) & group["arrival_dt"].notna()
                        & ~group["ts_error_arrival"]
                    ].copy()
                    response_values = response.apply(
                        lambda row: _hours(row["request_dt"], row["arrival_dt"]), axis=1)
                    _emit(rows, "TECH_RESPONSE", code, period, response_values, _mean, min_obs)

                    mature_completed = _mature_jobs(group, REPEAT_WINDOW_DAYS)
                    mature_original = mature_completed[
                        mature_completed["parent_job_id"].fillna("").astype(str).str.strip().eq("")
                    ]
                    if len(mature_original) >= min_obs:
                        repeats = mature_original["job_id"].astype(str).isin(repeat_parent_ids)
                        _emit(rows, "TECH_REPEAT", code, period, repeats.astype(float) * 100, _mean, min_obs)

                    report = completed[completed["report_complete"].notna()]
                    _emit(rows, "TECH_REPORT", code, period,
                          report["report_complete"].astype(float) * 100, _mean, min_obs)
                    _emit(rows, "TECH_CSAT", code, period, completed["csat"], _mean, MIN_CSAT_RESPONSES)

                    assigned = group[group["assigned_dt"].notna() & ~group["ts_error_assign"]
                                     & ~group["status"].eq("Cancelled")].copy()
                    assignment_mature = assigned["assigned_dt"].map(
                        lambda value: working_time.add_working_minutes(
                            pd.Timestamp(value).to_pydatetime(), 5 * working_time.WEEKDAY_MINUTES
                        ) <= EXTRACT_DT
                    )
                    assigned = assigned[assignment_mature]
                    within = assigned.apply(
                        lambda row: row["completion_dt"] is not pd.NaT
                        and not pd.isna(row["completion_dt"])
                        and _minutes(row["assigned_dt"], row["completion_dt"])
                        <= 5 * working_time.WEEKDAY_MINUTES,
                        axis=1,
                    )
                    _emit(rows, "TECH_COMPLETION", code, period, within.astype(float) * 100, _mean, min_obs)
                else:
                    assignable = group[group["priority"].isin(PRIORITIES) & group["assigned_dt"].notna()
                                       & ~group["ts_error_assign"]]
                    assign_times = assignable.apply(
                        lambda row: _minutes(row["request_dt"], row["assigned_dt"]), axis=1)
                    _emit(rows, "TPO_ASSIGN_TIME", code, period, assign_times, _median, min_obs)

                    assigned_jobs = group[group["assigned_dt"].notna() & group["reassigned_flag"].notna()]
                    _emit(rows, "TPO_ASSIGN_ACC", code, period,
                          (~assigned_jobs["reassigned_flag"].astype(bool)).astype(float) * 100, _mean, min_obs)

                    priority_jobs = group[group["priority"].isin(PRIORITIES)
                                          & ~group["status"].eq("Cancelled")]
                    unassigned_values = priority_jobs.apply(
                        lambda row: (
                            _minutes(row["request_dt"], row["assigned_dt"]) > 240
                            if not pd.isna(row["assigned_dt"]) and not row["ts_error_assign"]
                            else _minutes(row["request_dt"], EXTRACT_DT) > 240
                        ), axis=1)
                    _emit(rows, "TPO_UNASSIGNED", code, period,
                          unassigned_values.astype(float) * 100, _mean, min_obs)

                    monitored = priority_jobs[priority_jobs["sla_due_dt"].notna()]
                    _emit(rows, "TPO_SLA_MONITOR", code, period,
                          (monitored["sla_alert_dt"].notna()
                           & (monitored["sla_alert_dt"] < monitored["sla_due_dt"])).astype(float) * 100,
                          _mean, min_obs)

                    closed = group[group["status"].eq("Closed")]
                    accurate = closed[closed["admin_error_flag"].notna()]
                    _emit(rows, "TPO_PROC_ACC", code, period,
                      (~accurate["admin_error_flag"].astype(bool)).astype(float) * 100, _mean, min_obs)

                    if role == Role.TPO_SERVICE.value:
                        closure = closed[closed["closure_dt"].notna() & closed["completion_dt"].notna()]
                        closure_values = closure.apply(
                            lambda row: _hours(row["completion_dt"], row["closure_dt"]), axis=1)
                        _emit(rows, "TPO_CLOSURE_TIME", code, period, closure_values, _mean, min_obs)

                        pending = completed.copy()
                        pending_flag = pending.apply(
                            lambda row: (
                                pd.isna(row["closure_dt"])
                                or _minutes(row["completion_dt"], row["closure_dt"]) > 2 * 510
                            ), axis=1)
                        _emit(rows, "TPO_PENDING", code, period,
                              pending_flag.astype(float) * 100, _mean, min_obs)
                        documented = closed[closed["record_complete_flag"].notna()]
                        _emit(rows, "TPO_DOC_COMPLETE", code, period,
                              documented["record_complete_flag"].astype(float) * 100, _mean, min_obs)

        elif role == Role.AMC_PROCESSING.value:
            person_contracts = contracts[contracts["processor_no"] == code].copy()
            person_contracts["created_period"] = person_contracts["contract_created_dt"].map(_period)
            person_contracts["approval_period"] = person_contracts["approval_dt"].map(_period)
            person_contracts["renewal_period"] = person_contracts["renewal_due_date"].map(_period)
            for period, group in person_contracts.dropna(subset=["created_period"]).groupby("created_period"):
                created = group[group["contract_created_dt"].notna()]
                new_created = created[created["contract_type"].eq("New")]
                processing = new_created[new_created["approval_dt"].notna()]
                process_days = processing.apply(
                    lambda row: working_time.working_days_between(
                        _valid_time(row["approval_dt"]), _valid_time(row["contract_created_dt"])
                    ), axis=1)
                _emit(rows, "AMC_PROC_TIME", code, period, process_days, _median, min_obs)
                correction = created[created["correction_required_flag"].notna()]
                _emit(rows, "AMC_ACCURACY", code, period,
                      (~correction["correction_required_flag"].astype(bool)).astype(float) * 100,
                      _mean, min_obs)
                complete = created[created["data_complete_flag"].notna()]
                _emit(rows, "AMC_DATA_COMPLETE", code, period,
                      complete["data_complete_flag"].astype(float) * 100, _mean, min_obs)

            for period, group in person_contracts.dropna(subset=["approval_period"]).groupby("approval_period"):
                new_approved = group[group["contract_type"].eq("New")]
                matured = new_approved[new_approved["approval_dt"].map(
                    lambda value: working_time.add_working_minutes(
                        _valid_time(value), 3 * working_time.WEEKDAY_MINUTES
                    ) <= EXTRACT_DT
                )]
                completion_values = matured.apply(
                    lambda row: not pd.isna(row["contract_created_dt"])
                    and working_time.working_minutes_between(
                        _valid_time(row["approval_dt"]), _valid_time(row["contract_created_dt"])
                    ) <= 3 * working_time.WEEKDAY_MINUTES,
                    axis=1)
                _emit(rows, "AMC_COMPLETION", code, period, completion_values.astype(float) * 100,
                      _mean, min_obs)

                pending_mature = new_approved[new_approved["approval_dt"].map(
                    lambda value: working_time.add_working_minutes(
                        _valid_time(value), 5 * working_time.WEEKDAY_MINUTES
                    ) <= EXTRACT_DT
                )]
                pending_values = pending_mature.apply(
                    lambda row: pd.isna(row["contract_created_dt"])
                    or working_time.working_minutes_between(
                        _valid_time(row["approval_dt"]), _valid_time(row["contract_created_dt"])
                    ) > 5 * working_time.WEEKDAY_MINUTES,
                    axis=1)
                _emit(rows, "AMC_PENDING", code, period, pending_values.astype(float) * 100,
                      _mean, min_obs)

            for period, group in person_contracts.dropna(subset=["renewal_period"]).groupby("renewal_period"):
                renewal = group[group["renewal_due_date"] <= pd.Timestamp(EXTRACT_DT).normalize()]
                values = renewal.apply(
                    lambda row: not pd.isna(row["renewal_followup_date"])
                    and row["renewal_followup_date"]
                    <= row["renewal_due_date"] - pd.Timedelta(days=30),
                    axis=1)
                _emit(rows, "AMC_RENEWAL", code, period, values.astype(float) * 100, _mean, min_obs)

            for period, group in person_contracts.dropna(subset=["created_period"]).groupby("created_period"):
                scheduled = group[group["contract_created_dt"].notna()]
                values = scheduled.apply(
                    lambda row: not pd.isna(row["pm_schedule_created_date"])
                    and row["pm_schedule_created_date"]
                    <= row["contract_created_dt"] + pd.Timedelta(days=7),
                    axis=1)
                _emit(rows, "AMC_PM_SCHED", code, period, values.astype(float) * 100, _mean, min_obs)

        elif role == Role.CONTRACTS_COORDINATOR.value:
            person_proposals = proposals[proposals["coordinator_no"] == code].copy()
            person_proposals["period"] = person_proposals["proposal_dt"].map(_period)
            for period, group in person_proposals.dropna(subset=["period"]).groupby("period"):
                contact = group[group["first_contact_dt"].notna()]
                contact_values = contact.apply(
                    lambda row: _hours(row["proposal_dt"], row["first_contact_dt"]), axis=1)
                _emit(rows, "COORD_CONTACT", code, period, contact_values, _mean, min_obs)

                followups = group.apply(
                    lambda row: _followup_counts(row["followup_due_dates"], row["followup_done_dates"]),
                    axis=1)
                on_time = sum(item[0] for item in followups)
                done_total = sum(item[1] for item in followups)
                due_total = sum(item[2] for item in followups)
                if due_total >= min_obs:
                    rows.append({"employee_code": code, "kpi_code": "COORD_FOLLOWUP", "period": period,
                                 "value": on_time / due_total * 100, "n_obs": due_total})
                    rows.append({"employee_code": code, "kpi_code": "COORD_FOLLOWUP_DONE", "period": period,
                                 "value": done_total / due_total * 100, "n_obs": due_total})

                mature = (pd.Period(period, freq="M").end_time + pd.Timedelta(days=CONVERSION_WINDOW_DAYS)
                          <= pd.Timestamp(EXTRACT_DT))
                if mature:
                    accepted = group[group["status"].eq("Accepted")]
                    conversions = accepted[
                        accepted["approval_dt"].notna()
                        & (accepted["approval_dt"] >= accepted["proposal_dt"])
                        & ((accepted["approval_dt"] - accepted["proposal_dt"]).dt.days
                           <= CONVERSION_WINDOW_DAYS)
                    ]
                    if len(group) >= min_obs:
                        rows.append({"employee_code": code, "kpi_code": "COORD_CONVERSION", "period": period,
                                     "value": len(conversions) / len(group) * 100, "n_obs": len(group)})
                accepted = group[group["status"].eq("Accepted") & group["approval_dt"].notna()]
                cycle = accepted.apply(
                    lambda row: (row["approval_dt"] - row["proposal_dt"]).total_seconds() / 86400,
                    axis=1)
                _emit(rows, "COORD_CYCLE", code, period, cycle, _median, min_obs)
                rejected = group[group["status"].eq("Rejected")]
                if len(rejected) >= min_obs:
                    _emit(rows, "COORD_REJECT_REASON", code, period,
                          rejected["reason_recorded"].astype(float) * 100, _mean, min_obs)

    _validate_registry(rows)
    return rows


def _validate_registry(rows: MetricRows) -> None:
    """Raise when computed KPI codes do not exactly cover the registered role definitions."""
    computed_codes = {
        "TECH_SLA", "TECH_FTFR", "TECH_MTTR", "TECH_RESPONSE", "TECH_REPEAT", "TECH_REPORT",
        "TECH_CSAT", "TECH_COMPLETION", "TPO_ASSIGN_TIME", "TPO_ASSIGN_ACC", "TPO_UNASSIGNED",
        "TPO_SLA_MONITOR", "TPO_PROC_ACC", "TPO_CLOSURE_TIME", "TPO_PENDING", "TPO_DOC_COMPLETE",
        "AMC_PROC_TIME", "AMC_ACCURACY", "AMC_COMPLETION", "AMC_RENEWAL", "AMC_PM_SCHED",
        "AMC_PENDING", "AMC_DATA_COMPLETE", "COORD_CONTACT", "COORD_FOLLOWUP", "COORD_CONVERSION",
        "COORD_CYCLE", "COORD_FOLLOWUP_DONE", "COORD_REJECT_REASON",
    }
    registered_codes = {code for codes in ROLE_KPIS.values() for code in codes}
    if computed_codes != registered_codes:
        raise ValueError(
            f"Computed KPI definitions do not match the registry: "
            f"missing={sorted(registered_codes - computed_codes)}, extra={sorted(computed_codes - registered_codes)}"
        )
    if any(str(row["kpi_code"]) not in KPI_REGISTRY for row in rows):
        raise ValueError("A computed KPI record has no registry entry.")
