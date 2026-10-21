"""Narration ONLY. All numbers and diagnoses are computed deterministically before this step.

Only aggregated, pseudonymous facts are sent to the optional LLM. Raw feedback text and
row-level KPI data are never sent. A deterministic template keeps the system usable offline.
"""
from __future__ import annotations

import pandas as pd

from src.config import LLM_MODEL, OPENROUTER_API_KEY, OPENROUTER_BASE_URL, USE_LLM
from src.schemas.assessment import AssessmentReport
from src.schemas.kpi import KPI_REGISTRY

CAUSE_LABELS = {
    "workload": "heavy workload",
    "skill": "a skills or training gap",
    "process": "a system or process problem, including parts delays or incomplete incoming records",
    "external": "market conditions such as pricing or competitor offers",
    "undetermined": "no clear cause in the available information",
}
CATEGORY_LABELS = {
    "Efficiency": "efficiency of service work",
    "Quality": "service quality",
    "Compliance": "meeting service commitments",
    "Customer": "customer experience",
    "Productivity": "completed work",
}


def evidence_strength(score: float) -> str:
    if score >= 0.7:
        return "Strong"
    if score >= 0.45:
        return "Moderate"
    return "Weak"


def _cause_name(cause: str | None) -> str:
    return CAUSE_LABELS.get(cause or "undetermined", "no clear cause in the available information")


def _kpi_value(value: float, unit: str) -> str:
    formatted = f"{value:.0f}" if value.is_integer() else f"{value:.1f}"
    if unit == "%":
        return f"about {formatted}%"
    return f"about {formatted} {unit}"


def _checkpoint_text(name: str, checkpoint) -> str:
    if checkpoint.score is None:
        return f"{name}: no figure is available yet."
    score = f"{checkpoint.score:.1f}"
    if checkpoint.status == "confirmed":
        return f"{name}: {score} (confirmed)."
    estimate = "estimated from the recent trend (not yet confirmed)"
    if checkpoint.status == "partly projected":
        return (
            f"{name}: {score} (partly confirmed; the remaining months are "
            f"{estimate})."
        )
    return f"{name}: {score} ({estimate})."


def _recommendation_lines(r: AssessmentReport) -> list[str]:
    lines: list[str] = []
    for recommendation in r.recommendations:
        lines.append(f"**{recommendation.headline}:**")
        lines.append("")
        lines.extend(f"- {action}" for action in recommendation.actions)
        watch = [
            KPI_REGISTRY[code].name
            for code in recommendation.monitor_kpis
            if code in KPI_REGISTRY
        ]
        if watch:
            lines.append(f"- Afterwards, watch: {', '.join(watch)}.")
        lines.append(
            f"- Re-check after {recommendation.review_after_months} closed months."
        )
    return lines


def facts_for_llm(r: AssessmentReport) -> dict:
    diagnosis = r.diagnosis
    top_kpis = []
    by_code = {item.code: item for item in r.kpis}
    for code in r.deviation.declining_kpis[:3]:
        item = by_code.get(code)
        if item is None:
            continue
        top_kpis.append({
            "name": item.name,
            "usual_level_in_2024": item.baseline_avg,
            "recent_value": item.recent_avg,
            "unit": item.unit,
        })

    has_cause = bool(diagnosis and diagnosis.primary_cause != "undetermined")
    second = (
        diagnosis.ranked[1]
        if has_cause and len(diagnosis.ranked) > 1 and diagnosis.ranked[1].evidence
        else None
    )
    return {
        "employee_code": r.employee_code,
        "role": r.role,
        "reporting_month": r.as_of,
        "overall_performance_score": r.overall_score,
        "usual_performance_score_in_2024": r.trajectory.baseline_score,
        "change_from_usual_score": r.trajectory.delta_vs_baseline,
        "clear_drop": r.deviation.is_deviating,
        "insufficient_data": r.insufficient_data,
        "insufficient_reason": r.insufficient_reason,
        "data_through": r.data_through,
        "areas_that_dropped": [
            CATEGORY_LABELS.get(category, category)
            for category in r.deviation.declining_categories
        ],
        "most_affected_kpis": top_kpis,
        "main_cause": _cause_name(diagnosis.primary_cause) if diagnosis else None,
        "main_cause_evidence_strength": (
            evidence_strength(diagnosis.confidence) if diagnosis else None
        ),
        "main_cause_evidence": (
            diagnosis.ranked[0].evidence if has_cause and diagnosis and diagnosis.ranked else []
        ),
        "second_possible_cause": (
            {
                "cause": _cause_name(second.cause),
                "evidence_strength": evidence_strength(second.score),
                "evidence": second.evidence,
            }
            if second
            else None
        ),
        "employee_responsibility": (
            diagnosis.employee_controllable if diagnosis else "no clear concern identified"
        ),
        "context_facts": r.context.notes,
        "mid_year_checkpoint": {
            "score": r.trajectory.mid_year.score,
            "status": r.trajectory.mid_year.status,
            "confirmed_months": r.trajectory.mid_year.n_confirmed,
            "estimated_months": r.trajectory.mid_year.n_projected,
        },
        "full_year_checkpoint": {
            "score": r.trajectory.full_year.score,
            "status": r.trajectory.full_year.status,
            "confirmed_months": r.trajectory.full_year.n_confirmed,
            "estimated_months": r.trajectory.full_year.n_projected,
        },
        "recommendations": [
            {
                "headline": recommendation.headline,
                "steps": recommendation.actions,
                "watch_kpis": [
                    KPI_REGISTRY[code].name
                    for code in recommendation.monitor_kpis
                    if code in KPI_REGISTRY
                ],
                "recheck_after_closed_months": recommendation.review_after_months,
            }
            for recommendation in r.recommendations
        ],
        "strongest_kpi": max(r.kpis, key=lambda item: item.index_recent).name if r.kpis else None,
        "weakest_kpi": min(r.kpis, key=lambda item: item.index_recent).name if r.kpis else None,
        "data_limit": "The records may be incomplete; diagnosis is rule-based and should be reviewed by a manager.",
    }


def template_narrative(r: AssessmentReport) -> str:
    t = r.trajectory
    if r.insufficient_data:
        through = r.data_through or "no complete month"
        reason = r.insufficient_reason or "there are not enough complete monthly records"
        return "\n\n".join([
            f"**What happened:**\nThere is not enough complete performance data to assess {r.employee_code}. "
            f"The latest complete data is through {through}.",
            f"**Why it probably happened:**\nThe system cannot identify a cause because {reason}.",
            "**Is this the employee's responsibility?:**\nNo conclusion about individual responsibility can be drawn.",
            f"**What the data does and does not show:**\nThe records currently available end at {through}. "
            "No performance conclusion is made from incomplete data; diagnosis is rule-based.",
            "**What we recommend:**\n- Wait for complete reporting data before drawing conclusions or proposing action.",
            "This is a recommendation only. A manager must review and approve it before any action is taken.",
        ])
    delta = f"{t.delta_vs_baseline:+.1f} points"
    categories = [
        CATEGORY_LABELS.get(category, category)
        for category in r.deviation.declining_categories
    ]
    area_text = ", ".join(categories) if categories else "no specific service area"

    if not r.deviation.is_deviating:
        strongest = max(r.kpis, key=lambda item: item.index_recent) if r.kpis else None
        weakest = min(r.kpis, key=lambda item: item.index_recent) if r.kpis else None
        happened = (
            f"{r.employee_code} has a performance score of {r.overall_score:.1f} out of 100. "
            f"That is {delta} compared with this employee's own usual level in 2024 "
            f"({t.baseline_score:.1f}). There is no clear drop in the recent results. "
            f"The strongest KPI is {strongest.name if strongest else 'not available'}"
            f"{f' ({strongest.label.lower()})' if strongest else ''}; "
            f"the weakest is {weakest.name if weakest else 'not available'}"
            f"{f' ({weakest.label.lower()})' if weakest else ''}."
        )
        why = "No main cause is suggested because the results do not show a clear drop."
        responsibility = (
            "This is not an individual performance concern based on the available results."
        )
        recommendations = [
            "Continue routine monitoring of the employee's usual service measures.",
            "Re-check after 2 closed months.",
        ]
    else:
        d = r.diagnosis
        cause = _cause_name(d.primary_cause if d else "undetermined")
        top_kpis = []
        by_code = {item.code: item for item in r.kpis}
        for code in r.deviation.declining_kpis[:3]:
            item = by_code.get(code)
            if item and item.baseline_avg is not None:
                top_kpis.append(
                    f"{item.name} fell from {_kpi_value(item.baseline_avg, item.unit)} "
                    f"to {_kpi_value(item.recent_avg, item.unit)}"
                )
        kpi_text = "; ".join(top_kpis) if top_kpis else "specific KPI values are not available"
        happened = (
            f"{r.employee_code} has a performance score of {r.overall_score:.1f} out of 100. "
            f"That is {delta} compared with this employee's own usual level in 2024 "
            f"({t.baseline_score:.1f}); the recent results show a clear drop in performance. "
            f"The areas that dropped are {area_text}. The largest KPI drops are: {kpi_text}."
        )

        ranked = d.ranked if d and d.primary_cause != "undetermined" else []
        primary_evidence = ranked[0].evidence if ranked else []
        why = (
            f"The main possible explanation is {cause} "
            f"(strength of evidence: {evidence_strength(d.confidence) if d else 'Weak'}). "
            f"Evidence: {' '.join(primary_evidence) if primary_evidence else 'There is not enough specific context evidence.'}"
        )
        second = ranked[1] if len(ranked) > 1 and ranked[1].evidence else None
        if second:
            why += (
                f" Another possibility is {_cause_name(second.cause)} "
                f"(strength of evidence: {evidence_strength(second.score)}); "
                f"evidence: {' '.join(second.evidence) if second.evidence else 'There is limited evidence.'}"
            )

        if d and d.primary_cause == "workload":
            responsibility = (
                "This is partly a management decision because work volume and overtime "
                "are assigned; it should not be treated as solely the employee's responsibility."
            )
        elif d and d.primary_cause in {"process", "external"}:
            responsibility = (
                "This is not an individual performance concern and should not be used against "
                "the employee; the evidence points to wider system, process or market conditions."
            )
        elif d and d.primary_cause == "skill":
            responsibility = (
                "The evidence may point to a skills or training gap; offer support and training "
                "before drawing conclusions about individual performance."
            )
        else:
            responsibility = (
                "Responsibility is not clear from the available information; speak with the "
                "employee and gather context before making a judgement."
            )

        recommendations = _recommendation_lines(r)
        if not recommendations:
            recommendations = ["Discuss the results with the employee before deciding on support."]

    checkpoints = " ".join(
        (
            _checkpoint_text("Mid-year checkpoint", t.mid_year),
            _checkpoint_text("Full-year checkpoint", t.full_year),
        )
    )
    limits = (
        f"Complete monthly performance data is available through {r.data_through or r.as_of}; "
        "causes are identified using rules and should be reviewed in context."
    )
    return "\n\n".join([
        f"**What happened:**\n{happened}",
        f"**Why it probably happened:**\n{why}",
        f"**Is this the employee's responsibility?:**\n{responsibility}",
        f"**What the data does and does not show:**\n{checkpoints} {limits}",
        "**What we recommend:**\n" + "\n".join(recommendations),
        "This is a recommendation only. A manager must review and approve it before any action is taken.",
    ])


def team_narrative(reports: list[AssessmentReport], as_of: str) -> str:
    total = len(reports)
    if not total:
        return "No workforce records are available for the selected reporting period."
    as_of_fmt = pd.Period(as_of, freq="M").strftime("%B %Y")
    eligible = [r for r in reports if not r.insufficient_data]
    if not eligible:
        return (
            f"For {as_of_fmt}, no workforce performance summary can be calculated because "
            f"all {total} employees have insufficient complete data."
        )
    mean_score = sum(r.overall_score for r in eligible) / len(eligible)
    deviating = [r for r in reports if r.deviation.is_deviating]
    dev_count = len(deviating)
    insufficient_count = sum(r.insufficient_data for r in reports)
    on_track_count = len(eligible) - dev_count
    context_count = sum(
        1 for r in deviating if r.diagnosis and r.diagnosis.employee_controllable in ("no", "partly")
    )
    skill_count = sum(1 for r in deviating if r.diagnosis and r.diagnosis.employee_controllable == "yes")

    return (
        f"For {as_of_fmt}, the team performance score is {mean_score:.1f} out of 100. "
        f"{on_track_count} of {len(eligible)} employees with enough data are on target, "
        f"{dev_count} show a clear drop, and {insufficient_count} have insufficient data. "
        f"Among those needing review, {context_count} have evidence involving workload or wider "
        f"system or market conditions; {skill_count} may benefit from individual coaching."
    )


def narrate(r: AssessmentReport, use_llm: bool | None = None) -> str:
    fallback = template_narrative(r)
    if use_llm is None:
        use_llm = USE_LLM
    if not (use_llm and OPENROUTER_API_KEY):
        return fallback
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=LLM_MODEL,
            api_key=OPENROUTER_API_KEY,
            base_url=OPENROUTER_BASE_URL,
            temperature=0.2,
            timeout=20,
            max_retries=1,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "Explain employee service results to a non-technical service operations or HR manager "
                    "in plain, respectful language. Use only facts in the JSON: do not change, calculate, "
                    "round, infer, or invent any number, cause, KPI value, or score. Do not include KPI "
                    "codes or technical terms. Describe causes using the supplied plain-language wording. "
                    "If the cause is a system/process problem or market conditions, explicitly say this is "
                    "not an individual performance concern and must not be used against the employee. "
                    "Use these short labeled sections in this order: What happened; Why it probably happened; "
                    "Is this the employee's responsibility?; What the data does and does not show; "
                    "What we recommend. Include confirmed and estimated checkpoint status and the supplied "
                    "data limits, including the last month of complete data. Include recommendation steps, "
                    "what to watch, and when to re-check. Do not speculate about data provenance. "
                    "End exactly with: 'This is a recommendation only. A manager must review and approve "
                    "it before any action is taken.' Keep the full explanation to about 250 words.",
                ),
                ("human", "Facts (JSON): {facts}"),
            ]
        )
        result = (prompt | llm).invoke({"facts": facts_for_llm(r)}).content
        return result.strip() if isinstance(result, str) and result.strip() else fallback
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("LLM narration failed; using the deterministic template: %s", exc)
        return fallback
