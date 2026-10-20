"""KPI registry: the 4 roles, 29 KPIs and 5 categories from the KPI Evaluation Framework.

`base` / `sd` specify nominal operational parameters (typical monthly value and
month-to-month variation). Historical benchmarks are recomputed directly from baseline records.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    TECHNICIAN = "technician"
    TPO_SERVICE = "tpo_service"
    AMC_PROCESSING = "amc_processing"
    CONTRACTS_COORDINATOR = "contracts_coordinator"


ROLE_LABELS = {
    Role.TECHNICIAN: "Technician",
    Role.TPO_SERVICE: "TPO - Service",
    Role.AMC_PROCESSING: "AMC / Contract Processing",
    Role.CONTRACTS_COORDINATOR: "Contracts Coordinator",
}


class Category(str, Enum):
    EFFICIENCY = "Efficiency"
    QUALITY = "Quality"
    COMPLIANCE = "Compliance"
    CUSTOMER = "Customer"
    PRODUCTIVITY = "Productivity"


class Phase(str, Enum):
    PRE_MID_YEAR = "pre_mid_year"
    POST_MID_YEAR = "post_mid_year"
    POST_FULL_YEAR = "post_full_year"


class DataStatus(str, Enum):
    CONFIRMED = "confirmed"
    PROJECTED = "projected"


@dataclass(frozen=True)
class KPIDef:
    code: str
    name: str
    role: Role
    category: Category
    unit: str
    higher_is_better: bool
    base: float
    sd: float
    lo: float
    hi: float
    description: str
    external_sensitive: bool = False  # strongly influenced by market conditions, not only the employee
    maturity_lag_months: int = 0


E, Q, C, CU, P = (Category.EFFICIENCY, Category.QUALITY, Category.COMPLIANCE,
                  Category.CUSTOMER, Category.PRODUCTIVITY)
T, TPO, AMC, CO = (Role.TECHNICIAN, Role.TPO_SERVICE, Role.AMC_PROCESSING,
                   Role.CONTRACTS_COORDINATOR)

_KPIS = [
    # ---- Technician -------------------------------------------------------
    KPIDef("TECH_SLA", "SLA Compliance Rate", T, C, "%", True, 91, 2.5, 0, 100, "% of jobs completed within required SLA"),
    KPIDef("TECH_FTFR", "First-Time Fix Rate", T, Q, "%", True, 82, 3.0, 0, 100, "% of jobs resolved without a repeat visit", maturity_lag_months=1),
    KPIDef("TECH_MTTR", "Mean Time to Repair", T, E, "hrs", False, 4.5, 0.6, 0.5, 48, "Average time required to restore service"),
    KPIDef("TECH_RESPONSE", "Response Time", T, E, "hrs", False, 2.2, 0.4, 0.2, 24, "Service request to technician arrival"),
    KPIDef("TECH_REPEAT", "Repeat Service Rate", T, Q, "%", False, 9, 2.0, 0, 100, "% of jobs needing another visit for same issue", maturity_lag_months=1),
    KPIDef("TECH_REPORT", "Service Report Completion", T, Q, "%", True, 94, 2.5, 0, 100, "% of jobs with complete documentation"),
    KPIDef("TECH_CSAT", "Customer Satisfaction (CSAT)", T, CU, "/5", True, 4.3, 0.15, 1, 5, "Customer rating after service"),
    KPIDef("TECH_COMPLETION", "Job Completion Rate", T, P, "%", True, 93, 2.5, 0, 100, "% of assigned jobs completed in expected period"),
    # ---- TPO - Service ----------------------------------------------------
    KPIDef("TPO_ASSIGN_TIME", "Job Assignment Time", TPO, E, "min", False, 25, 6.0, 1, 300, "Request received to technician assigned"),
    KPIDef("TPO_ASSIGN_ACC", "Assignment Accuracy", TPO, Q, "%", True, 95, 2.0, 0, 100, "Jobs assigned correctly without reassignment"),
    KPIDef("TPO_UNASSIGNED", "Unassigned Job Rate", TPO, C, "%", False, 4, 1.5, 0, 100, "Jobs unassigned beyond target"),
    KPIDef("TPO_SLA_MONITOR", "SLA Monitoring Compliance", TPO, C, "%", True, 92, 3.0, 0, 100, "Jobs monitored properly before SLA breach"),
    KPIDef("TPO_PROC_ACC", "Processing Accuracy", TPO, Q, "%", True, 96, 1.8, 0, 100, "% transactions without administrative errors"),
    KPIDef("TPO_CLOSURE_TIME", "Job Closure Processing Time", TPO, E, "hrs", False, 6, 1.5, 0.5, 100, "Technician completion to administrative closure"),
    KPIDef("TPO_PENDING", "Pending Case Rate", TPO, P, "%", False, 6, 2.0, 0, 100, "Cases pending beyond target"),
    KPIDef("TPO_DOC_COMPLETE", "Documentation Completeness", TPO, Q, "%", True, 94, 2.5, 0, 100, "Completeness of service records"),
    # ---- AMC / Contract Processing ---------------------------------------
    KPIDef("AMC_PROC_TIME", "Contract Processing Time", AMC, E, "days", False, 3.5, 0.8, 0.2, 60, "Request/approval to contract creation"),
    KPIDef("AMC_ACCURACY", "Contract Accuracy Rate", AMC, Q, "%", True, 96, 1.8, 0, 100, "Contracts created without errors"),
    KPIDef("AMC_COMPLETION", "Contract Completion Rate", AMC, P, "%", True, 90, 3.0, 0, 100, "Contracts completed within target"),
    KPIDef("AMC_RENEWAL", "Renewal Follow-up Rate", AMC, C, "%", True, 88, 4.0, 0, 100, "Expiring contracts followed up on time"),
    KPIDef("AMC_PM_SCHED", "Preventive Maintenance Scheduling", AMC, C, "%", True, 90, 3.0, 0, 100, "AMC services scheduled on time"),
    KPIDef("AMC_PENDING", "Pending Contract Rate", AMC, P, "%", False, 7, 2.0, 0, 100, "Contracts stuck beyond target"),
    KPIDef("AMC_DATA_COMPLETE", "Contract Data Completeness", AMC, Q, "%", True, 95, 2.0, 0, 100, "Required contract info completed"),
    # ---- Contracts Coordinator -------------------------------------------
    KPIDef("COORD_CONTACT", "Customer Contact Response Time", CO, CU, "hrs", False, 5, 1.5, 0.2, 72, "Time to first customer contact"),
    KPIDef("COORD_FOLLOWUP", "Follow-up Compliance Rate", CO, C, "%", True, 90, 3.0, 0, 100, "Required follow-ups completed on time"),
    KPIDef("COORD_CONVERSION", "AMC Conversion Rate", CO, P, "%", True, 38, 5.0, 0, 100, "Accepted AMC proposals / eligible proposals", True, 2),
    KPIDef("COORD_CYCLE", "Proposal-to-Contract Cycle Time", CO, E, "days", False, 12, 3.0, 1, 120, "Proposal to accepted contract", True, 2),
    KPIDef("COORD_FOLLOWUP_DONE", "Customer Follow-up Completion", CO, C, "%", True, 89, 3.0, 0, 100, "Follow-ups completed per process"),
    KPIDef("COORD_REJECT_REASON", "Rejection Reason Recording Rate", CO, Q, "%", True, 85, 5.0, 0, 100, "Rejected proposals with recorded reason"),
]

KPI_REGISTRY: dict[str, KPIDef] = {k.code: k for k in _KPIS}
ROLE_KPIS: dict[Role, list[str]] = {r: [k.code for k in _KPIS if k.role == r] for r in Role}

# Category weights per role (must be validated with Metropolitan management).
ROLE_CATEGORY_WEIGHTS: dict[Role, dict[Category, float]] = {
    Role.TECHNICIAN: {C: .25, Q: .25, E: .20, CU: .15, P: .15},
    Role.TPO_SERVICE: {E: .30, Q: .30, C: .25, P: .15},
    Role.AMC_PROCESSING: {Q: .30, C: .30, E: .20, P: .20},
    Role.CONTRACTS_COORDINATOR: {P: .30, C: .25, E: .15, CU: .15, Q: .15},
}


def role_lag(role: Role | str) -> int:
    """Return the maximum maturity lag for a role's KPIs."""
    resolved = role if isinstance(role, Role) else Role(role)
    return max(KPI_REGISTRY[code].maturity_lag_months for code in ROLE_KPIS[resolved])
