
from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np

from src.config import DATA_END, DATA_START, RANDOM_SEED
from src.database.models import (ContextRecord, Employee, Feedback, HROutcome, Intervention,
                                 KPIRecord, Recommendation, SessionLocal, reset_db)
from src.schemas.kpi import KPI_REGISTRY, ROLE_KPIS, Category, Role


def month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[5:])
    ey, em = int(end[:4]), int(end[5:])
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


def month_index(period: str) -> int:
    return int(period[:4]) * 12 + int(period[5:]) - 1


@dataclass
class Effect:
    start: str
    ramp: int = 3
    category_sev: dict = field(default_factory=dict)   # Category -> severity in KPI-sd units
    kpi_sev: dict = field(default_factory=dict)        # kpi code -> severity
    recover_start: str | None = None
    recover_len: int = 4

    def factor(self, period: str) -> float:
        i, s = month_index(period), month_index(self.start)
        if i < s:
            return 0.0
        f = min(1.0, (i - s + 1) / self.ramp)
        if self.recover_start and i >= month_index(self.recover_start):
            f *= max(0.0, 1 - (i - month_index(self.recover_start) + 1) / self.recover_len)
        return f


@dataclass
class Scenario:
    effects: list[Effect]
    cause_2026: str          # ground-truth root cause for the 2026 cycle ('none' if no deviation)
    cause_2025: str = "none"
    context: str = "normal"  # workload / skill / process / external / normal
    feedback: str = "neutral"


SCENARIOS: dict[str, Scenario] = {
    "stable": Scenario([], "none"),
    "improving": Scenario(
        [Effect("2025-03", 6, {Category.QUALITY: -1.2, Category.EFFICIENCY: -1.2})], "none", feedback="positive"),
    "workload": Scenario(
        [Effect("2026-04", 3, {Category.EFFICIENCY: 3.0, Category.COMPLIANCE: 2.2, Category.QUALITY: 1.0})],
        "workload", context="workload", feedback="workload"),
    "skill": Scenario(
        [Effect("2026-05", 3, {Category.QUALITY: 4.0, Category.CUSTOMER: 2.5})],
        "skill", context="skill", feedback="skill"),
    "recovered": Scenario(
        [Effect("2025-02", 3, {Category.QUALITY: 3.2, Category.CUSTOMER: 1.8}, recover_start="2025-06")],
        "none", cause_2025="skill", context="skill", feedback="skill"),
    "process": Scenario(
        [Effect("2026-06", 2, {Category.EFFICIENCY: 2.8, Category.QUALITY: 2.2})],
        "process", context="process", feedback="process"),
    "external": Scenario(
        [Effect("2026-05", 2, kpi_sev={"COORD_CONVERSION": 3.6, "COORD_CYCLE": 3.4})],
        "external", context="external", feedback="external"),
    "amc_skill": Scenario(
        [Effect("2026-03", 3, {Category.QUALITY: 4.5})], "skill", context="skill", feedback="skill"),
}

# (role, scenario) in order -> EMP-001 ... EMP-020
ROSTER: list[tuple[Role, str]] = (
    [(Role.TECHNICIAN, s) for s in
     ["stable", "stable", "workload", "skill", "improving", "recovered", "stable", "workload", "stable", "stable"]]
    + [(Role.TPO_SERVICE, "process")] * 4
    + [(Role.AMC_PROCESSING, s) for s in ["stable", "amc_skill", "stable"]]
    + [(Role.CONTRACTS_COORDINATOR, "external")] * 3
)

BASE_JOBS = {Role.TECHNICIAN: 55, Role.TPO_SERVICE: 220, Role.AMC_PROCESSING: 40, Role.CONTRACTS_COORDINATOR: 30}

FEEDBACK_BANK = {
    "neutral": ["Routine month, no major issues.", "Handled assigned jobs as usual.", "Team coordination was fine this month."],
    "positive": ["Feeling confident with the new workflow.", "Training helped, jobs are going smoothly.", "Good month, targets feel achievable."],
    "workload": ["Too many jobs assigned, working late most days.", "Backlog keeps growing and overtime is heavy.", "Struggling to keep up with the daily workload."],
    "skill": ["Unfamiliar with the new equipment model, needed repeat visits.", "Would benefit from training on the latest product line.", "Not confident handling the new systems."],
    "process": ["The job system was down again and delayed assignments.", "Slow approval process and system outages hold up closures."],
    "external": ["Customers say a competitor's offer is cheaper.", "Customer budget limits make AMC renewals hard.", "Price increase is putting customers off."],
}


def generate_and_seed(reset: bool = True, seed: int = RANDOM_SEED) -> dict:
    rng = np.random.default_rng(seed)
    if reset:
        reset_db()
    periods = month_range(DATA_START, DATA_END)
    n_kpi = n_ctx = 0

    with SessionLocal() as s:
        emp_rows = []
        for i, (role, scen) in enumerate(ROSTER, start=1):
            e = Employee(code=f"EMP-{i:03d}", role=role.value,
                         team=rng.choice(["Service North", "Service South"]),
                         hire_year=int(rng.integers(2018, 2025)))
            s.add(e)
            emp_rows.append((e, role, scen))
        s.flush()

        for e, role, scen_name in emp_rows:
            scen = SCENARIOS[scen_name]
            offsets = {c: rng.normal(0, 0.5) * KPI_REGISTRY[c].sd for c in ROLE_KPIS[role]}
            for p in periods:
                # ---- KPIs --------------------------------------------------
                for code in ROLE_KPIS[role]:
                    k = KPI_REGISTRY[code]
                    sev = 0.0
                    for ef in scen.effects:
                        sev += ef.factor(p) * (ef.category_sev.get(k.category, 0.0) + ef.kpi_sev.get(code, 0.0))
                    direction = -1 if k.higher_is_better else 1   # +sev worsens the KPI
                    v = k.base + offsets[code] + rng.normal(0, k.sd) + direction * k.sd * sev
                    v = float(np.clip(v, k.lo, k.hi))
                    s.add(KPIRecord(employee_id=e.id, kpi_code=code, period=p, value=round(v, 3)))
                    n_kpi += 1
                # ---- context -----------------------------------------------
                f = max([ef.factor(p) for ef in scen.effects] or [0.0])
                jobs = BASE_JOBS[role] * (1 + rng.normal(0, 0.05))
                overtime = max(0, rng.normal(6, 3))
                complexity = float(np.clip(rng.normal(2.8, 0.2), 1, 5))
                downtime = max(0, rng.normal(2, 1))
                price = rng.normal(0, 1.0)
                offers = max(0, rng.normal(1, 0.5))
                budget = float(np.clip(rng.normal(0.2, 0.05), 0, 1))
                if scen.context == "workload":
                    jobs *= 1 + 0.45 * f
                    overtime += 28 * f
                elif scen.context == "skill":
                    complexity += 1.0 * f
                elif scen.context == "process":
                    downtime += 16 * f
                elif scen.context == "external":
                    price += 12 * f
                    offers += 3 * f
                    budget = float(np.clip(budget + 0.45 * f, 0, 1))
                s.add(ContextRecord(
                    employee_id=e.id, period=p, jobs_assigned=round(jobs, 1), avg_complexity=round(complexity, 2),
                    overtime_hours=round(overtime, 1), leave_days=float(rng.choice([0, 0, 1, 1, 2, 3])),
                    system_downtime_hours=round(downtime, 1), price_change_pct=round(price, 1),
                    competitor_offers=round(offers, 1), budget_constrained_share=round(budget, 2),
                    avg_equipment_age=round(float(rng.normal(4.5, 0.3)), 1)))
                n_ctx += 1
                # ---- feedback ----------------------------------------------
                if f > 0.3 and rng.random() < 0.85:
                    key = scen.feedback
                elif scen_name == "recovered" and p >= "2025-08":
                    key = "positive"
                elif scen_name == "improving" and p >= "2025-06":
                    key = "positive"
                else:
                    key = "neutral"
                s.add(Feedback(employee_id=e.id, period=p, text=str(rng.choice(FEEDBACK_BANK[key]))))

            # ---- ground truth labels for evaluation ------------------------
            s.add(HROutcome(employee_id=e.id, cycle_year=2026, has_deviation=scen.cause_2026 != "none",
                            root_cause=scen.cause_2026))
            s.add(HROutcome(employee_id=e.id, cycle_year=2025, has_deviation=scen.cause_2025 != "none",
                            root_cause=scen.cause_2025))

        # ---- one historical intervention (closed-loop demo): 'recovered' technician ----
        rec_emp = next(e for e, _, sc in emp_rows if sc == "recovered")
        rec = Recommendation(
            employee_id=rec_emp.id, as_of="2025-05", cause="skill",
            headline="Targeted technical training and mentoring",
            actions=json.dumps(["Product-specific refresher on the new equipment line",
                                "Pair with a senior technician for 4 weeks"]),
            priority="high", monitor_kpis=json.dumps(["TECH_FTFR", "TECH_REPEAT", "TECH_CSAT"]),
            diagnosis_summary="Seeded historical case: quality KPIs declined with higher job complexity.",
            status="approved", reviewer_note="Approved by manager (seed data).")
        s.add(rec)
        s.flush()
        s.add(Intervention(recommendation_id=rec.id, employee_id=rec_emp.id, start_period="2025-05",
                           baseline_score=0.0))   # baseline recomputed by the tracking service
        s.commit()
    return {"employees": len(ROSTER), "kpi_records": n_kpi, "context_records": n_ctx, "months": len(periods)}


if __name__ == "__main__":
    print(generate_and_seed())
