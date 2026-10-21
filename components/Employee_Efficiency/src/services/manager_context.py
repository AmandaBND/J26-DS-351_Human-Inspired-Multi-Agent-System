"""Apply structured, manager-reported context to diagnosis without changing KPI scores."""
from __future__ import annotations

from src.schemas.assessment import CauseScore, Diagnosis
from src.schemas.kpi import KPI_REGISTRY

MANAGER_CONTEXT_FACTORS = {
    "workload": "High workload or overtime",
    "leave": "Approved leave or time away",
    "system_process": "System or process disruption",
    "market_conditions": "External market conditions",
    "training_support": "Training or mentoring support needed",
    "data_quality": "Data completeness or quality concern",
}

FACTOR_CAUSES = {
    "workload": "workload",
    "leave": "workload",
    "system_process": "process",
    "market_conditions": "external",
    "training_support": "skill",
}

RESPONSIBILITY = {
    "skill": "yes",
    "workload": "partly",
    "process": "no",
    "external": "no",
}

VERDICTS = {
    "skill": (
        "Manager-reported context supports a possible skills or training gap. "
        "Offer support before drawing conclusions about individual performance."
    ),
    "workload": (
        "Manager-reported context supports a possible workload-related explanation. "
        "Work volume and leave are partly management decisions, so this should not be "
        "treated as solely the employee's responsibility."
    ),
    "process": (
        "Manager-reported context supports a possible system or process explanation. "
        "This is not an individual performance concern and should not be used against the employee."
    ),
    "external": (
        "Manager-reported context supports a possible market-related explanation. "
        "This is not an individual performance concern and should not be used against the employee."
    ),
}


def validate_manager_factors(factors: list[str]) -> list[str]:
    unique_factors = list(dict.fromkeys(factors))
    unknown = set(unique_factors) - MANAGER_CONTEXT_FACTORS.keys()
    if unknown:
        raise ValueError(f"Unsupported manager context factor(s): {', '.join(sorted(unknown))}")
    return unique_factors


def apply_manager_context(diagnosis: Diagnosis, factors: list[str]) -> Diagnosis:
    """Use manager-reported factors as explicit evidence, not as verified operational facts."""
    factors = validate_manager_factors(factors)
    if not factors:
        return diagnosis

    if "data_quality" in factors:
        return Diagnosis(
            primary_cause="undetermined",
            confidence=0.0,
            ranked=diagnosis.ranked,
            employee_controllable="unknown",
            verdict=(
                "The manager reported a data completeness or quality concern. "
                "Validate the source data and rerun the assessment before drawing any "
                "individual or root-cause conclusion."
            ),
        )

    scores = {
        item.cause: CauseScore(
            cause=item.cause, score=item.score, evidence=list(item.evidence)
        )
        for item in diagnosis.ranked
    }
    for factor in factors:
        cause = FACTOR_CAUSES[factor]
        score = scores.setdefault(cause, CauseScore(cause=cause, score=0.0, evidence=[]))
        score.score = round(min(1.0, score.score + 0.25), 2)
        score.evidence.append(
            f"Manager-reported context (not independently verified): "
            f"{MANAGER_CONTEXT_FACTORS[factor]}."
        )
    ranked = sorted(scores.values(), key=lambda item: item.score, reverse=True)
    top = ranked[0]
    if top.score < 0.35:
        return diagnosis
    manager_supported_causes = {FACTOR_CAUSES[factor] for factor in factors}
    verdict = (
        VERDICTS[top.cause]
        if top.cause in manager_supported_causes
        else diagnosis.verdict
    )
    return Diagnosis(
        primary_cause=top.cause,
        confidence=top.score,
        ranked=ranked,
        employee_controllable=RESPONSIBILITY[top.cause],
        verdict=verdict,
    )


def data_quality_recommendation(declining_kpis: list[str]):
    """Return a cautious recommendation when manager reports unreliable assessment data."""
    from src.schemas.assessment import RecommendationItem

    kpis = declining_kpis[:4]
    names = ", ".join(KPI_REGISTRY[k].name for k in kpis if k in KPI_REGISTRY)
    return RecommendationItem(
        cause="undetermined",
        headline="Verify source data before drawing conclusions",
        priority="medium",
        monitor_kpis=kpis,
        actions=[
            "Check the source records and correct any missing, delayed, or inaccurate entries.",
            "Do not make an individual performance conclusion while the data-quality concern is unresolved.",
            "Rerun the assessment after the records are verified"
            + (f", including {names}." if names else "."),
        ],
    )


def adjust_recommendation(
    headline: str,
    actions: list[str],
    factors: list[str],
) -> tuple[str, list[str]]:
    """Tailor the review-stage action plan using the same validated context factors."""
    factors = validate_manager_factors(factors)
    if not factors:
        return headline, list(actions)

    contextual_actions = {
        "workload": (
            "Review assigned workload and overtime; rebalance work where feasible before assessing individual performance."
        ),
        "leave": (
            "Confirm approved time away is reflected in the comparison period and adjust the assessment window if appropriate."
        ),
        "system_process": (
            "Refer the disruption to the responsible operations or IT owner and record when it is resolved."
        ),
        "market_conditions": (
            "Review relevant pricing, competitor, and customer-budget conditions at the service or team level."
        ),
        "data_quality": (
            "Validate source records and correct missing or incomplete data before interpreting the results."
        ),
    }
    non_individual_factors = [factor for factor in factors if factor in contextual_actions]
    if non_individual_factors:
        adjusted_actions = [contextual_actions[factor] for factor in non_individual_factors]
        if "data_quality" in non_individual_factors:
            adjusted_actions.append(
                "Defer individual conclusions or action until the data has been verified and the assessment rerun."
            )
        else:
            adjusted_actions.append(
                "Do not treat this period's result as an individual shortfall until the selected context has been reviewed."
            )
        if "training_support" in factors:
            adjusted_actions.append(
                "Offer targeted training or mentoring as developmental support, not as a disciplinary action."
            )
        return "Reassess using manager-confirmed context", adjusted_actions

    adjusted_actions = list(actions)
    adjusted_actions.append(
        "Offer targeted training or mentoring as developmental support, not as a disciplinary action."
    )
    return headline, adjusted_actions
