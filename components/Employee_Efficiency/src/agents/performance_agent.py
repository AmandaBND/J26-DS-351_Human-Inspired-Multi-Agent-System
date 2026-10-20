"""Performance Analysis sub-agent: role-specific KPIs -> indices, category scores, declining KPIs."""
from __future__ import annotations

from src.config import BASELINE_YEAR
from src.schemas.assessment import KPIStatus
from src.schemas.kpi import KPI_REGISTRY
from src.services.data_access import DataBundle
from src.services.kpi_engine import label_for

RECENT = 3
KPI_DECLINE = 10.0   # index points below own baseline
CAT_DECLINE = 6.0


def analyse(bundle: DataBundle, emp_id: int) -> dict:
    k = bundle.kpi[bundle.kpi["employee_id"] == emp_id]
    overall = bundle.overall_series(emp_id)
    recent_p = list(overall.index[-RECENT:])
    statuses: list[KPIStatus] = []
    declining_kpis: list[str] = []

    for code, g in k.groupby("kpi_code"):
        d = KPI_REGISTRY[code]
        rec = g[g["period"].isin(recent_p)]
        base = g[g["period"].str[:4] == str(BASELINE_YEAR)]
        idx_r = float(rec["index"].mean()) if not rec.empty else 75.0
        idx_b = float(base["index"].mean()) if not base.empty else idx_r
        statuses.append(KPIStatus(
            code=code, name=d.name, category=d.category.value, unit=d.unit,
            latest=round(float(g.sort_values("period")["value"].iloc[-1]), 2),
            recent_avg=round(float(rec["value"].mean()), 2) if not rec.empty else 0.0,
            baseline_avg=round(float(base["value"].mean()), 2) if not base.empty else None,
            benchmark_mean=round(float(g["bench_mean"].iloc[0]), 2),
            index_recent=round(idx_r, 1), index_baseline=round(idx_b, 1), delta=round(idx_r - idx_b, 1),
            label=label_for(idx_r)))
        if idx_b - idx_r >= KPI_DECLINE:
            declining_kpis.append(code)

    m = bundle.monthly[bundle.monthly["employee_id"] == emp_id].set_index("period").sort_index()
    cats = [c for c in ["Efficiency", "Quality", "Compliance", "Customer", "Productivity"] if c in m.columns and m[c].notna().any()]
    recent_cat = m.reindex(recent_p)[cats].mean()
    base_cat = m[m.index.str[:4] == str(BASELINE_YEAR)][cats].mean()
    declining_cats = [c for c in cats if base_cat[c] - recent_cat[c] >= CAT_DECLINE]
    declining_kpis.sort(key=lambda c: next(s.delta for s in statuses if s.code == c))
    return {
        "kpis": sorted(statuses, key=lambda s: s.delta),
        "category_scores": {c: round(float(recent_cat[c]), 1) for c in cats},
        "overall_score": round(float(m.reindex(recent_p)["overall"].mean()), 1),
        "declining_categories": declining_cats,
        "declining_kpis": declining_kpis,
    }
