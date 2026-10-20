"""Typed outputs of the agent. Every number here is computed deterministically in Python."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.schemas.kpi import DataStatus, Phase


class KPIStatus(BaseModel):
    code: str
    name: str
    category: str
    unit: str
    latest: float
    recent_avg: float            # mean of last 3 confirmed months
    baseline_avg: Optional[float] = None  # employee's own mean during the baseline year
    benchmark_mean: float        # historical benchmark (baseline year, role-wide)
    index_recent: float          # 0-100 performance index (75 = historical benchmark)
    index_baseline: float        # employee's own baseline-year index
    delta: float                 # index_recent - index_baseline
    label: str                   # Strong / On target / Watch / Concern


class TrajectoryPoint(BaseModel):
    period: str
    score: float
    status: DataStatus


class Checkpoint(BaseModel):
    name: str
    score: Optional[float]
    status: str                  # confirmed / partly projected / projected
    n_confirmed: int
    n_projected: int


class Trajectory(BaseModel):
    phase: Phase
    cycle_year: int
    points: list[TrajectoryPoint]
    mid_year: Checkpoint
    full_year: Checkpoint
    baseline_score: float
    delta_vs_baseline: float      # recent 3 confirmed months minus own baseline-year score
    previous_checkpoint_name: Optional[str] = None
    delta_vs_previous: Optional[float] = None


class DeviationResult(BaseModel):
    is_deviating: bool
    severity: str                # none / low / medium / high
    drop: float                  # baseline - recent 3-month mean (index points)
    slope_per_month: float
    months_below: int            # of last 3 months materially below baseline
    declining_categories: list[str] = Field(default_factory=list)
    declining_kpis: list[str] = Field(default_factory=list)


class ContextFindings(BaseModel):
    workload_ratio: float
    complexity_delta: float
    overtime_hours: float
    downtime_delta: float
    price_change_pct: float
    competitor_offers: float
    budget_share: float
    sentiment: float             # -1 .. +1
    feedback_tags: dict[str, int]
    peer_deviation_share: float  # share of same-role peers also deviating
    parts_wait_share_delta: float = 0.0
    incomplete_input_delta: float = 0.0
    notes: list[str] = Field(default_factory=list)


class CauseScore(BaseModel):
    cause: str                   # workload / skill / process / external / undetermined
    score: float
    evidence: list[str]


class Diagnosis(BaseModel):
    primary_cause: str
    confidence: float
    ranked: list[CauseScore]
    employee_controllable: str   # yes / partly / no / unknown
    verdict: str


class RecommendationItem(BaseModel):
    cause: str
    headline: str
    actions: list[str]
    priority: str                # high / medium / low
    monitor_kpis: list[str]
    review_after_months: int = 2
    requires_human_review: bool = True


class AssessmentReport(BaseModel):
    employee_code: str
    role: str
    as_of: str
    phase: Phase
    overall_score: float
    category_scores: dict[str, float]
    kpis: list[KPIStatus]
    trajectory: Trajectory
    deviation: DeviationResult
    context: ContextFindings
    diagnosis: Optional[Diagnosis] = None
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    narrative: str = ""
    data_note: str = ""
    data_through: str = ""
    insufficient_data: bool = False
    insufficient_reason: str = ""
