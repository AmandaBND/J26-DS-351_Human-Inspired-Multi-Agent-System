"""Rule-based, explainable root-cause diagnosis. Every score is a weighted sum of named evidence.

Causes: workload | skill | process | external. Anything below MIN_CONFIDENCE -> 'undetermined'.
"""
from __future__ import annotations

from src.schemas.assessment import CauseScore, ContextFindings, DeviationResult, Diagnosis
from src.schemas.kpi import KPI_REGISTRY

MIN_CONFIDENCE = 0.35
DIAGNOSIS_WEIGHTS = {
    "workload": {
        "workload_ratio": 0.45,
        "overtime": 0.25,
        "feedback": 0.15,
        "efficiency_compliance": 0.15,
    },
    "skill": {
        "quality_customer": 0.35,
        "complexity": 0.20,
        "training_feedback": 0.25,
        "individual_decline": 0.20,
        "parts_delay_penalty": 0.25,
        "workload_penalty": 0.30,
    },
    "process": {
        "peer_decline": 0.30,
        "downtime": 0.15,
        "parts_wait": 0.25,
        "incomplete_input": 0.20,
        "feedback": 0.10,
    },
    "external": {
        "price_change": 0.30,
        "competitor_offers": 0.20,
        "budget_constraints": 0.10,
        "market_sensitive_kpis": 0.30,
        "price_feedback": 0.10,
    },
}


def sat(x: float, lo: float, hi: float) -> float:
    """Linear saturation: 0 at/below lo, 1 at/above hi."""
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def diagnose(dev: DeviationResult, ctx: ContextFindings) -> Diagnosis:
    cats = set(dev.declining_categories)
    ext_kpis = [k for k in dev.declining_kpis if KPI_REGISTRY[k].external_sensitive]
    ext_share = len(ext_kpis) / max(1, len(dev.declining_kpis))

    # ---- workload ---------------------------------------------------------
    w_parts = {
        "workload ratio": DIAGNOSIS_WEIGHTS["workload"]["workload_ratio"] * sat(ctx.workload_ratio, 1.0, 1.4),
        "overtime": DIAGNOSIS_WEIGHTS["workload"]["overtime"] * sat(ctx.overtime_hours, 8, 30),
        "workload feedback": DIAGNOSIS_WEIGHTS["workload"]["feedback"]
        * sat(ctx.feedback_tags.get("workload", 0), 0, 2),
        "efficiency/compliance decline": DIAGNOSIS_WEIGHTS["workload"]["efficiency_compliance"]
        * float(bool(cats & {"Efficiency", "Compliance"})),
    }
    # ---- skill ------------------------------------------------------------
    quality_hit = bool(cats & {"Quality", "Customer"})
    s_raw = {
        "quality/customer decline": DIAGNOSIS_WEIGHTS["skill"]["quality_customer"] * float(quality_hit),
        "job complexity increase": DIAGNOSIS_WEIGHTS["skill"]["complexity"]
        * sat(ctx.complexity_delta, 0.3, 1.0),
        "training feedback": DIAGNOSIS_WEIGHTS["skill"]["training_feedback"]
        * sat(ctx.feedback_tags.get("training", 0), 0, 2),
        "individual decline while peers are stable": DIAGNOSIS_WEIGHTS["skill"]["individual_decline"]
        * (1 - ctx.peer_deviation_share),
    }
    s_penalty = (
        DIAGNOSIS_WEIGHTS["skill"]["workload_penalty"] if ctx.workload_ratio >= 1.2 else 0.0
    )
    if ctx.parts_wait_share_delta >= 0.12:
        s_penalty += DIAGNOSIS_WEIGHTS["skill"]["parts_delay_penalty"]
    # ---- process ----------------------------------------------------------
    process_feedback = max(
        ctx.feedback_tags.get(tag, 0) for tag in ("process", "parts", "incomplete")
    )
    p_parts = {
        "same-role colleagues show a similar decline": DIAGNOSIS_WEIGHTS["process"]["peer_decline"]
        * sat(ctx.peer_deviation_share, 0.3, 0.8),
        "system downtime": DIAGNOSIS_WEIGHTS["process"]["downtime"] * sat(ctx.downtime_delta, 3, 15),
        "more jobs are waiting for parts": DIAGNOSIS_WEIGHTS["process"]["parts_wait"]
        * sat(ctx.parts_wait_share_delta, 0.08, 0.20),
        "more incoming records are incomplete": DIAGNOSIS_WEIGHTS["process"]["incomplete_input"]
        * sat(ctx.incomplete_input_delta, 0.08, 0.25),
        "process-related feedback": DIAGNOSIS_WEIGHTS["process"]["feedback"] * sat(process_feedback, 0, 2),
    }
    # ---- external ---------------------------------------------------------
    e_parts = {
        "price/market change": DIAGNOSIS_WEIGHTS["external"]["price_change"]
        * sat(ctx.price_change_pct, 3, 10),
        "competing offers": DIAGNOSIS_WEIGHTS["external"]["competitor_offers"]
        * sat(ctx.competitor_offers, 1.5, 3.5),
        "customer budget limits": DIAGNOSIS_WEIGHTS["external"]["budget_constraints"]
        * sat(ctx.budget_share, 0.3, 0.6),
        "market-sensitive KPIs declined": DIAGNOSIS_WEIGHTS["external"]["market_sensitive_kpis"] * ext_share,
        "price feedback": DIAGNOSIS_WEIGHTS["external"]["price_feedback"]
        * sat(ctx.feedback_tags.get("price", 0), 0, 2),
    }

    def evidence(parts: dict[str, float], note_fmt: dict[str, str]) -> list[str]:
        return [note_fmt[k] for k, value in parts.items() if value > 0.02]

    ranked = [
        CauseScore(cause="workload", score=round(sum(w_parts.values()), 2),
                   evidence=evidence(w_parts, {
                       "workload ratio": f"Jobs assigned are {ctx.workload_ratio:.2f} times this employee's own usual level in 2024.",
                       "overtime": f"Overtime is about {ctx.overtime_hours:.0f} hours a month.",
                       "workload feedback": f"Recent employee feedback mentioned heavy workload ({ctx.feedback_tags.get('workload', 0)} signal(s)).",
                       "efficiency/compliance decline": "The decline is in service efficiency or meeting service commitments.",
                   })),
        CauseScore(cause="skill", score=round(max(0.0, sum(s_raw.values()) - s_penalty), 2),
                   evidence=evidence(s_raw, {
                       "quality/customer decline": "The largest drops are in service quality or customer experience.",
                       "job complexity increase": f"Jobs are about {ctx.complexity_delta:.1f} points more complex than this employee's own usual level in 2024.",
                       "training feedback": f"Recent feedback mentioned unfamiliar work or a need for training ({ctx.feedback_tags.get('training', 0)} signal(s)).",
                       "individual decline while peers are stable": f"{1 - ctx.peer_deviation_share:.0%} of same-role colleagues do not show the same decline.",
                   }) + (["The high workload makes a skills or training explanation less certain."] if s_penalty else [])),
        CauseScore(cause="process", score=round(sum(p_parts.values()), 2),
                   evidence=evidence(p_parts, {
                       "same-role colleagues show a similar decline": f"{ctx.peer_deviation_share:.0%} of employees in the same role show a similar decline.",
                       "system downtime": f"System downtime is about {ctx.downtime_delta:.0f} hours a month above its 2024 level.",
                       "more jobs are waiting for parts": f"Jobs waiting for parts increased by {ctx.parts_wait_share_delta:.0%} from the employee's 2024 level.",
                       "more incoming records are incomplete": f"Incomplete incoming records increased by {ctx.incomplete_input_delta:.0%} from the employee's 2024 level.",
                       "process-related feedback": f"Recent feedback mentioned process delays or missing information ({process_feedback} signal(s)).",
                   })),
        CauseScore(cause="external", score=round(sum(e_parts.values()), 2),
                   evidence=evidence(e_parts, {
                       "price/market change": f"Prices changed by {ctx.price_change_pct:+.1f}%.",
                       "competing offers": f"There are about {ctx.competitor_offers:.1f} competitor offers per customer.",
                       "customer budget limits": f"Budget constraints affect about {ctx.budget_share:.0%} of customers.",
                       "market-sensitive KPIs declined": "The KPIs that dropped are strongly affected by market conditions.",
                       "price feedback": f"Recent feedback mentioned pricing, competitors or budgets ({ctx.feedback_tags.get('price', 0)} signal(s)).",
                   })),
    ]
    ranked.sort(key=lambda c: c.score, reverse=True)
    top = ranked[0]

    if top.score < MIN_CONFIDENCE:
        return Diagnosis(primary_cause="undetermined", confidence=round(top.score, 2), ranked=ranked,
                         employee_controllable="unknown",
                         verdict="There is a clear drop in performance, but the available information does not "
                                 "show a clear cause. A manager should speak with the employee and gather more "
                                 "context before drawing conclusions.")
    controllable = {"skill": "yes", "workload": "partly", "process": "no", "external": "no"}[top.cause]
    verdicts = {
        "skill": "The pattern may reflect a skills or training gap. Offer support and training before drawing conclusions about individual performance.",
        "workload": "The decline may be related to heavy workload. Work volume and overtime are partly management decisions, so this should not be treated as solely the employee's responsibility.",
        "process": "The decline may be related to a system or process problem. This is not an individual performance concern and should not be used against the employee.",
        "external": "The decline may be related to market conditions such as pricing or competitor offers. This is not an individual performance concern and should not be used against the employee.",
    }
    return Diagnosis(primary_cause=top.cause, confidence=round(top.score, 2), ranked=ranked,
                     employee_controllable=controllable, verdict=verdicts[top.cause])
