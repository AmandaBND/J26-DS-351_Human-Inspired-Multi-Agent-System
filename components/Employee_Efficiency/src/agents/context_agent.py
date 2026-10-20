"""Context & Gap Analysis sub-agent: workload, complexity, system/market conditions, feedback, peers."""
from __future__ import annotations

from src.services.context import analyse_context
from src.services.data_access import DataBundle


def analyse(bundle: DataBundle, emp_id: int, role: str) -> object:
    peers = bundle.employees[
        (bundle.employees["role"] == role)
        & (bundle.employees["id"] != emp_id)
        & ~bundle.employees["id"].map(bundle.insufficient_data).fillna(True)
    ]["id"]
    share = float(sum(bundle.deviations[p].is_deviating for p in peers) / len(peers)) if len(peers) else 0.0
    valid_periods = list(bundle.overall_series(emp_id).index[-3:])
    role_employee_ids = bundle.employees.loc[bundle.employees["role"] == role, "id"].tolist()
    return analyse_context(
        bundle.context, bundle.feedback, emp_id, share, valid_periods, role_employee_ids
    )
