import pandas as pd
from sqlalchemy import create_engine, inspect

from src.database.models import Base, init_db


def test_init_db_additively_migrates_existing_sqlite_schema():
    database_engine = create_engine("sqlite://")
    with database_engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE employees ("
            "id INTEGER PRIMARY KEY, code VARCHAR(20), role VARCHAR(40), "
            "team VARCHAR(40), hire_year INTEGER)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE kpi_records ("
            "id INTEGER PRIMARY KEY, employee_id INTEGER, kpi_code VARCHAR(30), "
            "period VARCHAR(7), value FLOAT, status VARCHAR(10))"
        )
        connection.exec_driver_sql(
            "CREATE TABLE context_records ("
            "id INTEGER PRIMARY KEY, employee_id INTEGER, period VARCHAR(7), "
            "jobs_assigned FLOAT, avg_complexity FLOAT, overtime_hours FLOAT, "
            "leave_days FLOAT, system_downtime_hours FLOAT, price_change_pct FLOAT, "
            "competitor_offers FLOAT, budget_constrained_share FLOAT, avg_equipment_age FLOAT)"
        )
        connection.exec_driver_sql(
            "CREATE TABLE recommendations ("
            "id INTEGER PRIMARY KEY, employee_id INTEGER, as_of VARCHAR(7), cause VARCHAR(20), "
            "headline VARCHAR(200), actions TEXT, priority VARCHAR(10), monitor_kpis TEXT, "
            "diagnosis_summary TEXT, status VARCHAR(12), reviewer_note TEXT, created_at DATETIME, "
            "decided_at DATETIME)"
        )
        connection.exec_driver_sql(
            "INSERT INTO employees VALUES (1, 'EMP-001', 'technician', 'Team A', 2020)"
        )
        connection.exec_driver_sql(
            "INSERT INTO kpi_records VALUES (1, 1, 'TECH_SLA', '2026-01', 90.0, 'confirmed')"
        )
        connection.exec_driver_sql(
            "INSERT INTO context_records VALUES (1, 1, '2026-01', 3, 2, 0, 0, 0, 0, 0, 0, 5)"
        )

    init_db(database_engine)

    employees = pd.read_sql(
        "SELECT id, code, role, team, hire_year, status FROM employees", database_engine
    )
    assert employees.to_dict("records") == [{
        "id": 1,
        "code": "EMP-001",
        "role": "technician",
        "team": "Team A",
        "hire_year": 2020,
        "status": "Active",
    }]
    assert pd.read_sql("SELECT n_obs FROM kpi_records", database_engine)["n_obs"].isna().all()
    context = pd.read_sql(
        "SELECT parts_wait_share, incomplete_input_share FROM context_records",
        database_engine,
    )
    assert context.iloc[0].tolist() == [0.0, 0.0]
    for table_name in ("employees", "kpi_records", "context_records", "recommendations"):
        actual = {column["name"] for column in inspect(database_engine).get_columns(table_name)}
        expected = {column.name for column in Base.metadata.tables[table_name].columns}
        assert expected <= actual
    recommendation_columns = {
        column["name"] for column in inspect(database_engine).get_columns("recommendations")
    }
    assert "assessment_context_factors" in recommendation_columns
    assert "assessment_context_note" in recommendation_columns
