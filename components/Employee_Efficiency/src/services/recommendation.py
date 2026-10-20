"""Scenario-based intervention templates. Output always requires human review."""
from __future__ import annotations

from src.schemas.assessment import Diagnosis, DeviationResult, RecommendationItem
from src.schemas.kpi import KPI_REGISTRY


def build_recommendations(dev: DeviationResult, diag: Diagnosis) -> list[RecommendationItem]:
    priority = {"high": "high", "medium": "medium", "low": "low", "none": "low"}[dev.severity]
    kpis = dev.declining_kpis[:4]
    names = ", ".join(KPI_REGISTRY[k].name for k in kpis) or "the declining KPIs"
    cause = diag.primary_cause

    if cause == "skill":
        return [RecommendationItem(
            cause=cause, headline="Offer focused training and mentoring", priority=priority, monitor_kpis=kpis,
            actions=[f"Agree a short refresher on the areas behind {names}.",
                     "Arrange four weeks of supported work with an experienced colleague.",
                     f"Afterwards, watch {names} and re-check after two closed months."])]
    if cause == "workload":
        return [RecommendationItem(
            cause=cause, headline="Review workload and overtime", priority=priority, monitor_kpis=kpis,
            actions=["Review assigned work and move some jobs to colleagues who have capacity.",
                     "Discuss overtime and leave with the employee; agree a manageable plan."])]
    if cause == "process":
        return [RecommendationItem(
            cause=cause, headline="Fix the system or process issue (no individual action)", priority="medium",
            monitor_kpis=kpis,
            actions=["Send the role-wide decline and any system downtime to the operations or IT team.",
                     "Record that this review period should not be treated as an individual shortfall.",
                     "Check whether the same decline remains after the issue is fixed."])]
    if cause == "external":
        return [RecommendationItem(
            cause=cause, headline="Record market conditions and review customer offers (no individual action)",
            priority="medium", monitor_kpis=kpis,
            actions=["Record pricing, competitor and customer budget information before any appraisal discussion.",
                     "Ask management to review service pricing, packages and renewal offers.",
                     "Do not treat market-driven results as an individual concern."])]
    return [RecommendationItem(
        cause="undetermined", headline="Manager review needed", priority="medium", monitor_kpis=kpis,
        actions=["Speak with the employee to understand the change.",
                 "Check the job mix, work conditions and customer feedback before choosing support."])]
