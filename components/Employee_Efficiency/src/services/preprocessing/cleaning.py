"""Explicit, auditable cleaning rules for the source CSV exports."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

from src.services.preprocessing.utils import (
    QualityLogger,
    log_value_changes,
    norm_emp_no,
    parse_date,
    parse_datetime,
    parse_period,
    read_raw,
    to_bool,
)


EMPLOYEE_COLUMNS = ("assigned_by", "technician_no", "closed_by", "coordinator_no", "processor_no", "employee_no")
FLAG_COLUMNS = ("repeat_visit_flag", "report_complete", "reassigned_flag", "admin_error_flag",
                "record_complete_flag", "data_complete_flag", "correction_required_flag")


def _count_changed(before: pd.Series, after: pd.Series) -> int:
    """Count rows whose normalized values differ from their original values."""
    return int((before.astype(str).str.strip() != after.astype(str)).sum())


def _normalize_employee_column(
    df: pd.DataFrame, column: str, valid_employees: set[str], logger: QualityLogger, filename: str
) -> None:
    before = len(df)
    original = df[column].copy()
    normalized = original.map(norm_emp_no)
    unknown = normalized.notna() & ~normalized.isin(valid_employees)
    invalid = normalized.isna() | unknown
    if bool(invalid.any()):
        logger.record("cleaning", filename, f"{column}_invalid_or_unknown", before, before,
                      int(invalid.sum()), "set_missing", "Employee references not present in employees.csv.")
    df[column] = normalized.mask(unknown, pd.NA)
    changed = _count_changed(original, df[column])
    log_value_changes(logger, filename, f"{column}_normalized", before, changed)


def _map_labels(
    series: pd.Series, mapper: dict[str, str], default: str
) -> pd.Series:
    return series.astype(str).str.strip().str.casefold().map(mapper).fillna(default)


def _canonical_priority(value: Any) -> str | Any:
    text = str(value).strip().casefold()
    if not text:
        return pd.NA
    if text == "p1" or re.match(r"^1(?:\D|$)", text) or "critical" in text:
        return "P1"
    if text == "p2" or re.match(r"^2(?:\D|$)", text) or text == "high":
        return "P2"
    if text == "p3" or re.match(r"^3(?:\D|$)", text) or text == "normal":
        return "P3"
    if text == "p4" or re.match(r"^4(?:\D|$)", text) or text == "planned":
        return "P4"
    return pd.NA


def _canonical_status(value: Any) -> str:
    text = str(value).strip().casefold()
    aliases = {
        "closed": "Closed", "complete": "Completed", "completed": "Completed",
        "in progress": "In Progress", "in-progress": "In Progress",
        "assigned": "Assigned", "open": "Open", "cancelled": "Cancelled",
        "canceled": "Cancelled",
    }
    return aliases.get(text, "Unknown")


def _canonical_job_type(value: Any) -> str:
    text = str(value).strip().casefold()
    if "breakdown" in text or text in {"repair", "breakdown"}:
        return "Breakdown repair"
    if "preventive" in text or text in {"pm", "maintenance"}:
        return "Preventive maintenance"
    if "install" in text:
        return "Installation"
    if "repeat" in text:
        return "Repeat visit"
    return "Other service"


def _canonical_role(value: Any) -> str:
    text = str(value).strip().casefold()
    if "technician" in text:
        return "technician"
    if "tpo" in text or "transaction processing" in text:
        return "tpo_service"
    if "amc" in text or "contract processing" in text:
        return "amc_processing"
    if "coordinator" in text or "co-ordinator" in text:
        return "contracts_coordinator"
    return "unknown"


def _canonical_proposal_status(value: Any) -> str:
    text = str(value).strip().casefold()
    if text in {"accepted", "won"}:
        return "Accepted"
    if text in {"rejected", "declined"}:
        return "Rejected"
    if text in {"no response", "no_response", "lapsed"}:
        return "No Response"
    if text in {"pending", "open", "in progress"}:
        return "Pending"
    return "Pending"


def _parse_date_list(value: Any) -> list[pd.Timestamp]:
    """Parse a semicolon-separated list of supported date formats."""
    values = [part.strip() for part in str(value).split(";") if part.strip()]
    parsed = parse_date(pd.Series(values, dtype="string"))
    return sorted(item for item in parsed.tolist() if not pd.isna(item))


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")


def clean_employees(df: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Normalize employee roles, dates, territories, and employment state."""
    name = "employees.csv"
    before = len(df)
    out = df.copy()
    out["employee_no"] = out["employee_no"].map(norm_emp_no)
    out["role"] = out["designation"].map(_canonical_role)
    out["join_date"] = parse_date(out["join_date"])
    out["employment_status"] = out["employment_status"].astype(str).str.strip()
    out["status"] = out["employment_status"].str.casefold().map(
        lambda text: "On Leave" if "leave" in text else ("Active" if text else "Active"))
    out["team"] = out["base_territory"].astype(str).str.strip()
    out["hire_year"] = out["join_date"].map(lambda value: value.year if not pd.isna(value) else pd.NA)
    out = out.drop_duplicates(subset=["employee_no"], keep="first").reset_index(drop=True)
    logger.record("cleaning", name, "duplicate_employee_number", before, len(out), before - len(out), "drop")
    logger.note_file_counts(name, before, len(out))
    return out


def clean_service_jobs(
    df: pd.DataFrame,
    employees: pd.DataFrame,
    branch_map: pd.DataFrame,
    logger: QualityLogger,
) -> pd.DataFrame:
    """Clean service jobs and preserve invalid timestamps with explicit exclusion flags."""
    name = "service_jobs.csv"
    initial = len(df)
    out = df.copy()
    test_mask = (
        out["job_id"].astype(str).str.upper().str.startswith("TEST")
        | out["customer_ref"].astype(str).str.strip().str.upper().eq("TEST")
        | out["product_type"].astype(str).str.strip().str.casefold().eq("test printer")
    )
    out = out.loc[~test_mask].copy()
    logger.record("cleaning", name, "test_records", initial, len(out), int(test_mask.sum()), "drop")

    before = len(out)
    out = out.drop_duplicates(keep="first")
    logger.record("cleaning", name, "exact_duplicates", before, len(out), before - len(out), "drop")
    before = len(out)
    out = out.drop_duplicates(subset=["job_id"], keep="first")
    logger.record("cleaning", name, "duplicate_job_id", before, len(out), before - len(out), "drop")

    valid_employees = set(employees["employee_no"].dropna().astype(str))
    for column in ("assigned_by", "technician_no", "closed_by"):
        _normalize_employee_column(out, column, valid_employees, logger, name)
    for column in [column for column in out if column.endswith("_dt")]:
        original = out[column].copy()
        out[column] = parse_datetime(out[column])
        invalid = original.astype(str).str.strip().ne("") & out[column].isna()
        if bool(invalid.any()):
            logger.record("cleaning", name, f"invalid_{column}", len(out), len(out), int(invalid.sum()),
                          "set_missing", "Timestamp failed the supported explicit formats.")

    original_priority = out["priority"].copy()
    out["priority"] = out["priority"].map(_canonical_priority)
    invalid_priority = out["priority"].isna() & original_priority.astype(str).str.strip().ne("")
    logger.record("cleaning", name, "priority_variants", len(out), len(out),
                  _count_changed(original_priority, out["priority"]), "normalize")
    if bool(invalid_priority.any()):
        logger.record("cleaning", name, "unknown_priority", len(out), len(out), int(invalid_priority.sum()),
                      "set_missing")
    out["job_type"] = out["job_type"].map(_canonical_job_type)
    out["status"] = out["status"].map(_canonical_status)
    unknown_status = out["status"].eq("Unknown")
    if bool(unknown_status.any()):
        logger.record("cleaning", name, "unknown_service_status", len(out), len(out),
                      int(unknown_status.sum()), "map_to_open")
        out.loc[unknown_status, "status"] = "Open"

    for column in ("repeat_visit_flag", "report_complete", "reassigned_flag", "admin_error_flag",
                   "record_complete_flag"):
        original = out[column].copy()
        out[column] = out[column].map(to_bool).astype("boolean")
        changed = _count_changed(original, out[column])
        log_value_changes(logger, name, f"{column}_boolean", len(out), changed)

    branch_map_clean = branch_map.copy()
    branch_map_clean["branch_key"] = branch_map_clean["branch"].astype(str).str.strip().str.casefold()
    territory_by_branch = branch_map_clean.set_index("branch_key")["service_territory"].to_dict()
    branch_key = out["branch"].astype(str).str.strip().str.casefold()
    out["territory"] = branch_key.map(territory_by_branch).fillna("Unknown")
    unknown_branch = out["territory"].eq("Unknown")
    if bool(unknown_branch.any()):
        logger.record("cleaning", name, "unknown_branch", len(out), len(out), int(unknown_branch.sum()),
                      "map_unknown")

    product = out["product_type"].astype(str).str.casefold()
    out["product_category"] = "Unknown"
    out.loc[product.str.contains(r"york|btu|split|central ac", regex=True), "product_category"] = "York AC"
    out.loc[product.str.contains(r"\bir\b|imagerunner", regex=True), "product_category"] = "Copier/MFP"
    out.loc[product.str.contains(r"imageclass|pixma|imageformula|\blbp\b|dr-c", regex=True),
            "product_category"] = "Printer/Scanner"
    out.loc[product.str.contains(r"ups|switch|cctv|telephone", regex=True), "product_category"] = "Other"
    unknown_product = out["product_category"].eq("Unknown")
    logger.record("cleaning", name, "product_category_unknown", len(out), len(out), int(unknown_product.sum()),
                  "classify_unknown")
    out["new_model"] = product.str.contains("c3835i", regex=False)
    out["fault_type"] = out["fault_type"].astype(str).str.strip().replace("", "Unknown")
    original_complexity = out["fault_complexity"].copy()
    out["fault_complexity"] = original_complexity.astype(str).str.strip().str.casefold().map(
        {"low": "Low", "medium": "Medium", "high": "High"}).fillna("Medium")
    invalid_complexity = out["fault_complexity"].eq("Medium") & ~original_complexity.astype(
        str).str.strip().str.casefold().eq("medium")
    if bool(invalid_complexity.any()):
        logger.record("cleaning", name, "unknown_fault_complexity", len(out), len(out),
                      int(invalid_complexity.sum()), "default_to_medium")
    out["complexity_score"] = out["fault_complexity"].map({"Low": 1.0, "Medium": 3.0, "High": 5.0})

    repair_text = out["repair_time_hrs"].astype(str).str.strip()
    hhmm = repair_text.str.fullmatch(r"\d{1,3}:\d{2}")
    repair = pd.to_numeric(repair_text.where(~hhmm), errors="coerce")
    repair.loc[hhmm] = repair_text.loc[hhmm].map(
        lambda value: int(value.split(":")[0]) + int(value.split(":")[1]) / 60)
    out["repair_time_hrs"] = repair
    x10_count = 0
    for job_type, indices in out.groupby("job_type").groups.items():
        values = out.loc[indices, "repair_time_hrs"]
        median = float(values.median()) if values.notna().any() else float("nan")
        if median <= 0 or pd.isna(median):
            continue
        outlier = values > 5 * median
        candidate = values / 10
        plausible = candidate.between(0.25, 3 * median)
        corrected = outlier & plausible
        nulled = outlier & ~plausible
        x10_count += int(corrected.sum())
        out.loc[values.index[corrected], "repair_time_hrs"] = candidate[corrected]
        out.loc[values.index[nulled], "repair_time_hrs"] = pd.NA
    logger.record("cleaning", name, "probable_x10_repair_typos", len(out), len(out), x10_count,
                  "divide_by_10", "Outliers corrected only when the scaled value was plausible.")
    numeric_repair = repair.notna().sum()
    final_repair = out["repair_time_hrs"].notna().sum()
    logger.record("cleaning", name, "implausible_repair_time", len(out), len(out),
                  int(numeric_repair - final_repair), "set_missing")
    out["parts_wait_hrs"] = _numeric(out["parts_wait_hrs"])
    out["csat"] = _numeric(out["csat"]).where(_numeric(out["csat"]).between(1, 5))

    out["ts_error_assign"] = out["assigned_dt"].notna() & out["request_dt"].notna() & (
        out["assigned_dt"] < out["request_dt"])
    out["assigned_dt"] = out["assigned_dt"].mask(out["ts_error_assign"])
    out["ts_error_arrival"] = out["arrival_dt"].notna() & out["assigned_dt"].notna() & (
        out["arrival_dt"] < out["assigned_dt"])
    out["arrival_dt"] = out["arrival_dt"].mask(out["ts_error_arrival"])
    logger.record("cleaning", name, "timestamp_order", len(out), len(out),
                  int(out["ts_error_assign"].sum() + out["ts_error_arrival"].sum()), "set_invalid_timestamp_missing")
    missing_arrival = out["completion_dt"].notna() & out["arrival_dt"].isna()
    if bool(missing_arrival.any()):
        logger.record("cleaning", name, "completed_without_arrival", len(out), len(out),
                      int(missing_arrival.sum()), "retain_missing", "Excluded from response-time calculations.")
    logger.note_file_counts(name, initial, len(out))
    return out.reset_index(drop=True)


def clean_amc_proposals(
    df: pd.DataFrame, employees: pd.DataFrame, logger: QualityLogger
) -> pd.DataFrame:
    """Normalize AMC proposal records, dates, follow-ups, flags, and statuses."""
    name = "amc_proposals.csv"
    initial = len(df)
    out = df.copy()
    before = len(out)
    out = out.drop_duplicates(keep="first").drop_duplicates(subset=["proposal_id"], keep="first")
    logger.record("cleaning", name, "duplicate_proposals", before, len(out), before - len(out), "drop")
    valid = set(employees["employee_no"].dropna().astype(str))
    for column in ("coordinator_no", "processor_no"):
        _normalize_employee_column(out, column, valid, logger, name)
    for column in ("proposal_dt", "first_contact_dt", "approval_dt"):
        raw = out[column].copy()
        out[column] = parse_datetime(raw)
        bad = raw.astype(str).str.strip().ne("") & out[column].isna()
        if bool(bad.any()):
            logger.record("cleaning", name, f"invalid_{column}", len(out), len(out), int(bad.sum()), "set_missing")
    original_status = out["status"].copy()
    out["status"] = original_status.map(_canonical_proposal_status)
    recognized = {"accepted", "won", "rejected", "declined", "no response", "no_response",
                  "lapsed", "pending", "open", "in progress"}
    unknown_status = ~original_status.astype(str).str.strip().str.casefold().isin(recognized)
    if bool(unknown_status.any()):
        logger.record("cleaning", name, "unknown_proposal_status", len(out), len(out),
                      int(unknown_status.sum()), "map_to_pending")
    out["quoted_price"] = _numeric(out["quoted_price"].str.replace("LKR", "", case=False, regex=False))
    for column in ("followup_due_dates", "followup_done_dates"):
        out[column] = out[column].map(_parse_date_list)
    reason = out["rejection_reason"].astype(str).str.strip()
    out["reason_recorded"] = ~reason.str.casefold().isin({"", "-", "n/a", "na", "none"})
    out["rejection_reason"] = reason.mask(~out["reason_recorded"])
    out["data_complete_flag"] = out["data_complete_flag"].map(to_bool).astype("boolean")
    logger.note_file_counts(name, initial, len(out))
    return out.reset_index(drop=True)


def clean_amc_contracts(
    df: pd.DataFrame, employees: pd.DataFrame, logger: QualityLogger
) -> pd.DataFrame:
    """Normalize AMC contract identifiers, dates, numeric values, and flags."""
    name = "amc_contracts.csv"
    initial = len(df)
    out = df.copy()
    before = len(out)
    out = out.drop_duplicates(keep="first").drop_duplicates(subset=["contract_id"], keep="first")
    logger.record("cleaning", name, "duplicate_contracts", before, len(out), before - len(out), "drop")
    _normalize_employee_column(out, "processor_no", set(employees["employee_no"].dropna().astype(str)),
                               logger, name)
    date_columns = ("approval_dt", "contract_created_dt", "contract_start_date", "renewal_due_date",
                    "renewal_followup_date", "pm_schedule_created_date")
    for column in date_columns:
        raw = out[column].copy()
        parsed_datetime = parse_datetime(raw)
        parsed_date = parse_date(raw)
        out[column] = parsed_datetime.fillna(parsed_date)
        bad = raw.astype(str).str.strip().ne("") & out[column].isna()
        if bool(bad.any()):
            logger.record("cleaning", name, f"invalid_{column}", len(out), len(out), int(bad.sum()), "set_missing")
    for column in ("data_complete_flag", "correction_required_flag"):
        out[column] = out[column].map(to_bool).astype("boolean")
    out["contract_value_lkr"] = _numeric(out["contract_value_lkr"].str.replace("LKR", "", case=False, regex=False))
    out["contract_type"] = out["contract_type"].astype(str).str.strip().str.title()
    out["status"] = out["status"].astype(str).str.strip().str.title()
    logger.note_file_counts(name, initial, len(out))
    return out.reset_index(drop=True)


def clean_attendance(df: pd.DataFrame, employees: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Normalize employee-month attendance and numeric hours."""
    name = "hr_attendance_monthly.csv"
    out = df.copy()
    _normalize_employee_column(out, "employee_no", set(employees["employee_no"].dropna().astype(str)), logger, name)
    out["period"] = out["month"].map(parse_period)
    out["leave_days"] = _numeric(out["leave_days"])
    out["overtime_hours"] = _numeric(out["overtime_hours"])
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_downtime(df: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Parse system outage timestamps and preserve rows with invalid dates."""
    name = "system_downtime_log.csv"
    out = df.copy()
    for column in ("start_dt", "end_dt"):
        raw = out[column].copy()
        out[column] = parse_datetime(raw)
        bad = raw.astype(str).str.strip().ne("") & out[column].isna()
        if bool(bad.any()):
            logger.record("cleaning", name, f"invalid_{column}", len(out), len(out), int(bad.sum()), "set_missing")
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_price_changes(df: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Parse price change dates and percentages."""
    name = "price_list_changes.csv"
    out = df.copy()
    out["effective_date"] = parse_date(out["effective_date"])
    out["change_pct"] = _numeric(out["change_pct"].astype(str).str.replace("%", "", regex=False))
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_competitor_notes(df: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Parse competitor note dates without logging note contents."""
    name = "competitor_notes.csv"
    out = df.copy()
    out["note_date"] = parse_date(out["note_date"])
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_reviews(df: pd.DataFrame, employees: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Normalize pseudonymizable review data and nullable ratings."""
    name = "hr_reviews.csv"
    out = df.copy()
    _normalize_employee_column(out, "employee_no", set(employees["employee_no"].dropna().astype(str)), logger, name)
    out["rating"] = _numeric(out["rating"]).where(_numeric(out["rating"]).between(1, 5)).astype("Int64")
    out["review_cycle"] = out["review_cycle"].astype(str).str.strip()
    out["manager_comment"] = out["manager_comment"].astype(str).str.strip()
    out["action_taken"] = out["action_taken"].astype(str).str.strip()
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_feedback(df: pd.DataFrame, employees: pd.DataFrame, logger: QualityLogger) -> pd.DataFrame:
    """Normalize employee-month feedback while keeping text local to SQLite."""
    name = "employee_feedback.csv"
    out = df.copy()
    _normalize_employee_column(out, "employee_no", set(employees["employee_no"].dropna().astype(str)), logger, name)
    out["period"] = out["period"].map(parse_period)
    out["comment_text"] = out["comment_text"].astype(str).str.strip()
    logger.note_file_counts(name, len(df), len(out))
    return out


def clean_reference_data(
    branch_map: pd.DataFrame, holidays: pd.DataFrame, logger: QualityLogger
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Normalize territory and holiday reference tables."""
    branch_map = branch_map.copy()
    branch_map["branch"] = branch_map["branch"].astype(str).str.strip()
    branch_map["service_territory"] = branch_map["service_territory"].astype(str).str.strip()
    holidays = holidays.copy()
    holidays["date"] = parse_date(holidays["date"])
    logger.note_file_counts("branch_territory_map.csv", len(branch_map), len(branch_map))
    logger.note_file_counts("public_holidays.csv", len(holidays), len(holidays))
    return branch_map, holidays


def load_and_clean(logger: QualityLogger) -> dict[str, pd.DataFrame]:
    """Read and clean all required CSVs using the shared quality log."""
    employees = clean_employees(read_raw("employees.csv"), logger)
    branch_map, holidays = clean_reference_data(
        read_raw("branch_territory_map.csv"), read_raw("public_holidays.csv"), logger)
    jobs = clean_service_jobs(read_raw("service_jobs.csv"), employees, branch_map, logger)
    proposals = clean_amc_proposals(read_raw("amc_proposals.csv"), employees, logger)
    contracts = clean_amc_contracts(read_raw("amc_contracts.csv"), employees, logger)
    attendance = clean_attendance(read_raw("hr_attendance_monthly.csv"), employees, logger)
    downtime = clean_downtime(read_raw("system_downtime_log.csv"), logger)
    prices = clean_price_changes(read_raw("price_list_changes.csv"), logger)
    competitors = clean_competitor_notes(read_raw("competitor_notes.csv"), logger)
    reviews = clean_reviews(read_raw("hr_reviews.csv"), employees, logger)
    feedback = clean_feedback(read_raw("employee_feedback.csv"), employees, logger)
    return {
        "employees": employees, "branch_map": branch_map, "holidays": holidays, "jobs": jobs,
        "proposals": proposals, "contracts": contracts, "attendance": attendance, "downtime": downtime,
        "prices": prices, "competitors": competitors, "reviews": reviews, "feedback": feedback,
    }
