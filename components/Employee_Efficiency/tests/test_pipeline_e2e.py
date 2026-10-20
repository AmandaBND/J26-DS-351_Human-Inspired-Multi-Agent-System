import re

import pandas as pd
import pytest
from sqlalchemy import inspect

from src.database.models import engine
from src.services.data_access import load_bundle
from src.services.preprocessing.pipeline import run_preprocessing
from src.workflow.graph import run_team


@pytest.fixture(scope="module")
def company_bundle():
    run_preprocessing()
    return load_bundle("2026-09")


@pytest.mark.slow
def test_pipeline_loads_company_employees_and_monthly_records(company_bundle):
    assert len(company_bundle.employees) == 34
    assert company_bundle.employees["code"].tolist() == [
        f"EMP-{index:03d}" for index in range(1, 35)
    ]
    assert company_bundle.kpi["period"].min() == "2024-01"
    assert company_bundle.kpi["period"].max() == "2026-09"
    assert not company_bundle.monthly.empty


@pytest.mark.slow
def test_database_text_columns_do_not_contain_six_digit_employee_numbers(company_bundle):
    inspector = inspect(engine)
    violations = []
    for table in inspector.get_table_names():
        text_columns = [
            column["name"] for column in inspector.get_columns(table)
            if "CHAR" in str(column["type"]).upper() or "TEXT" in str(column["type"]).upper()
        ]
        if not text_columns:
            continue
        frame = pd.read_sql_table(table, engine, columns=text_columns)
        for column in text_columns:
            if frame[column].astype(str).str.contains(r"(?<!\d)\d{6}(?!\d)", regex=True).any():
                violations.append(f"{table}.{column}")
    assert violations == []


@pytest.mark.slow
def test_lag_and_extended_leave_status_are_visible(company_bundle):
    coordinator = company_bundle.employees["role"].eq("contracts_coordinator")
    coordinator_months = company_bundle.employees.loc[coordinator, "id"].map(
        company_bundle.data_through
    )
    assert coordinator_months.max() <= "2026-07"

    tpo_on_leave = company_bundle.employees[
        company_bundle.employees["role"].eq("tpo_service")
        & company_bundle.employees["status"].eq("On Leave")
    ]
    assert not tpo_on_leave.empty
    report = run_team(company_bundle)
    by_code = {assessment.employee_code: assessment for assessment in report}
    assert any(
        by_code[row["code"]].insufficient_data
        and "extended leave" in by_code[row["code"]].insufficient_reason
        for _, row in tpo_on_leave.iterrows()
    )
