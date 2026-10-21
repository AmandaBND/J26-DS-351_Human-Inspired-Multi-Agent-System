"""Apply structured manager-reported context to assessment diagnosis and recommendations."""
from __future__ import annotations

from src.schemas.assessment import DeviationResult, Diagnosis, RecommendationItem
from src.services.manager_context import (
    MANAGER_CONTEXT_FACTORS,
    apply_manager_context,
    data_quality_recommendation,
    validate_manager_factors,
)
from src.services.recommendation import build_recommendations


def apply_assessment_context(
    deviation: DeviationResult,
    diagnosis: Diagnosis,
    factors: list[str],
) -> tuple[Diagnosis, list[RecommendationItem]]:
    factors = validate_manager_factors(factors)
    diagnosis = apply_manager_context(diagnosis, factors)
    if "data_quality" in factors:
        return diagnosis, [data_quality_recommendation(deviation.declining_kpis)]
    return diagnosis, build_recommendations(deviation, diagnosis)

__all__ = [
    "apply_assessment_context",
    "MANAGER_CONTEXT_FACTORS",
    "apply_manager_context",
    "data_quality_recommendation",
    "validate_manager_factors",
]
