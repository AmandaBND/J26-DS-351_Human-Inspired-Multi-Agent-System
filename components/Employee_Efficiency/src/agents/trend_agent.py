from __future__ import annotations

from src.services import trajectory
from src.services.data_access import DataBundle


def analyse(bundle: DataBundle, emp_id: int, declining_categories: list[str], declining_kpis: list[str]) -> dict:
    series = bundle.overall_series(emp_id)
    base = bundle.baseline_overall[emp_id]
    traj = trajectory.build_trajectory(series, base, bundle.as_of)
    dev = trajectory.detect_deviation(series, base)
    dev.declining_categories = declining_categories
    dev.declining_kpis = declining_kpis
    return {"trajectory": traj, "deviation": dev}
