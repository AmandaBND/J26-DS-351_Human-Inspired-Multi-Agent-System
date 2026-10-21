import pandas as pd

from src.services.preprocessing.cleaning import _canonical_priority, clean_service_jobs
from src.services.preprocessing.utils import QualityLogger, norm_emp_no, parse_datetime, to_bool


def test_employee_number_boolean_and_mixed_timestamp_parsing():
    assert norm_emp_no(" 1363 ") == "001363"
    assert pd.isna(norm_emp_no("employee"))
    assert to_bool("YES") is True
    assert to_bool("0") is False
    assert pd.isna(to_bool("unknown"))

    parsed = parse_datetime(pd.Series(["2024-01-02 08:30:00", "03/02/2024 09:15", "bad", ""]))
    assert parsed.iloc[0] == pd.Timestamp("2024-01-02 08:30:00")
    assert parsed.iloc[1] == pd.Timestamp("2024-02-03 09:15:00")
    assert pd.isna(parsed.iloc[2]) and pd.isna(parsed.iloc[3])
    assert [_canonical_priority(value) for value in ("P1", "p2", "3 - Normal", "Planned")] == [
        "P1", "P2", "P3", "P4",
    ]


def test_service_cleaner_deduplicates_normalizes_and_repairs_repair_time():
    row = {
        "job_id": "SR-1", "request_dt": "2024-01-02 09:00:00",
        "assigned_dt": "2024-01-02 10:00:00", "assigned_by": "1363",
        "technician_no": "001363", "arrival_dt": "2024-01-02 10:30:00",
        "completion_dt": "2024-01-02 12:00:00", "closure_dt": "2024-01-02 13:00:00",
        "sla_due_dt": "2024-01-03 17:00:00", "sla_alert_dt": "",
        "job_type": "Breakdown repair", "product_type": "ImageRunner",
        "fault_type": "", "fault_complexity": "Low", "priority": "1 - Critical",
        "branch": "Main", "customer_ref": "CUST", "contract_status": "AMC",
        "repeat_visit_flag": "N", "parent_job_id": "", "repair_time_hrs": "02:30",
        "parts_wait_hrs": "0", "report_complete": "Yes", "csat": "5",
        "status": "closed", "closed_by": "1363", "reassigned_flag": "N",
        "admin_error_flag": "false", "record_complete_flag": "Y",
    }
    rows = [
        row.copy(),
        row.copy(),
        {**row, "job_id": "TEST-1"},
    ]
    logger = QualityLogger()
    clean = clean_service_jobs(
        pd.DataFrame(rows),
        pd.DataFrame({"employee_no": ["001363"]}),
        pd.DataFrame({"branch": ["Main"], "service_territory": ["Colombo"]}),
        logger,
    )

    assert len(clean) == 1
    assert clean.iloc[0]["priority"] == "P1"
    assert clean.iloc[0]["status"] == "Closed"
    assert clean.iloc[0]["assigned_by"] == "001363"
    assert clean.iloc[0]["repair_time_hrs"] == 2.5
    assert clean.iloc[0]["product_category"] == "Copier/MFP"
    assert clean.iloc[0]["fault_type"] == "Unknown"
    assert {entry["rule"] for entry in logger.entries} >= {
        "test_records", "exact_duplicates", "duplicate_job_id",
    }
