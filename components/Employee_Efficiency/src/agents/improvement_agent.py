from __future__ import annotations

from src.schemas.assessment import DeviationResult, Diagnosis
from src.services.diagnosis import diagnose
from src.services.recommendation import build_recommendations


def plan(dev: DeviationResult, ctx) -> tuple[Diagnosis, list]:
    diag = diagnose(dev, ctx)
    return diag, build_recommendations(dev, diag)
