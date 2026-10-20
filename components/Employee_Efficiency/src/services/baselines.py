"""Rule-based KPI-threshold baseline (proposal Sec 3.3, baseline 2): flags, never explains."""
from __future__ import annotations

from src.services.data_access import DataBundle

THRESHOLD_Z = 1.0     # KPI recent mean worse than benchmark by > 1 std
MIN_KPIS_BREACHED = 2


def threshold_flag(bundle: DataBundle, emp_id: int) -> bool:
    k = bundle.kpi[bundle.kpi["employee_id"] == emp_id]
    recent = sorted(k["period"].unique())[-3:]
    rec = k[k["period"].isin(recent)].groupby("kpi_code")["index"].mean()
    # index 75 == benchmark, 12 points == 1 std
    breaches = int((rec < 75 - 12 * THRESHOLD_Z).sum())
    return breaches >= MIN_KPIS_BREACHED
