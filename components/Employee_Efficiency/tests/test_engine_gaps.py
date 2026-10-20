import pandas as pd

from src.schemas.kpi import KPI_REGISTRY, Role, role_lag
from src.services.kpi_engine import monthly_scores
from src.services.trajectory import build_trajectory, detect_deviation


def test_maturity_lags_are_role_specific():
    assert role_lag(Role.TECHNICIAN) == 1
    assert role_lag(Role.CONTRACTS_COORDINATOR) == 2
    assert role_lag(Role.TPO_SERVICE) == 0


def test_monthly_composite_requires_coverage_and_each_weighted_category():
    rows = []
    technician_codes = [
        code for code, definition in KPI_REGISTRY.items()
        if definition.role == Role.TECHNICIAN
    ]
    for employee_id, omitted in ((1, None), (2, "TECH_RESPONSE"), (3, "TECH_CSAT")):
        for code in technician_codes:
            if code != omitted:
                rows.append({
                    "employee_id": employee_id,
                    "role": Role.TECHNICIAN.value,
                    "period": "2025-01",
                    "kpi_code": code,
                    "category": KPI_REGISTRY[code].category.value,
                    "index": 75.0,
                })
    scores = monthly_scores(pd.DataFrame(rows)).set_index("employee_id")
    assert scores.loc[1, "overall"] == 75.0
    assert scores.loc[2, "kpi_count"] == 7
    assert scores.loc[2, "overall"] == 75.0
    assert scores.loc[3, "kpi_count"] == 7
    assert pd.isna(scores.loc[3, "overall"])


def test_trajectory_projects_from_last_complete_month_not_as_of():
    series = pd.Series(
        [70.0, 72.0, 68.0],
        index=["2025-01", "2025-02", "2025-03"],
    )
    result = build_trajectory(series, baseline=75.0, as_of="2025-05")
    points = {point.period: point.status.value for point in result.points}
    assert points["2025-03"] == "confirmed"
    assert points["2025-04"] == "projected"
    assert points["2025-05"] == "projected"


def test_deviation_detection_rejects_sparse_recent_months():
    series = pd.Series(
        [60.0, 61.0, 62.0],
        index=["2025-01", "2025-03", "2025-06"],
    )
    assert not detect_deviation(series, baseline=75.0).is_deviating
