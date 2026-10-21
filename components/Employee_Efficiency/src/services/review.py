"""Human review workflow + closed intervention loop.

Rule: the agent only PROPOSES. A recommendation is `pending` until a manager approves, modifies or
rejects it. Approval creates an Intervention whose outcome is evaluated at later checkpoints.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from src.config import USE_LLM
from src.database.models import Intervention, Recommendation, SessionLocal
from src.schemas.assessment import AssessmentReport
from src.services.data_access import DataBundle, load_bundle
from src.services.llm_narrator import summarize_manager_review
from src.services.manager_context import MANAGER_CONTEXT_FACTORS, adjust_recommendation

IMPROVE_MARGIN = 3.0   # index points

def submit_for_review(report: AssessmentReport, bundle: DataBundle) -> list[int]:
    """Persist the report's recommendations as `pending` (idempotent per employee/as_of/cause)."""
    if not report.deviation.is_deviating:
        return []
    emp_id = int(bundle.emp(report.employee_code)["id"])
    ids = []
    with SessionLocal() as s:
        for r in report.recommendations:
            exists = s.query(Recommendation).filter_by(employee_id=emp_id, as_of=report.as_of, cause=r.cause).first()
            if exists:
                if exists.status == "pending":
                    exists.headline = r.headline
                    exists.actions = json.dumps(r.actions)
                    exists.priority = r.priority
                    exists.monitor_kpis = json.dumps(r.monitor_kpis)
                    exists.diagnosis_summary = report.diagnosis.verdict if report.diagnosis else ""
                    exists.assessment_context_factors = json.dumps(report.manager_context_factors)
                    exists.assessment_context_note = report.manager_context_note
                ids.append(exists.id)
                continue
            rec = Recommendation(
                employee_id=emp_id, as_of=report.as_of, cause=r.cause, headline=r.headline,
                actions=json.dumps(r.actions), priority=r.priority, monitor_kpis=json.dumps(r.monitor_kpis),
                diagnosis_summary=(report.diagnosis.verdict if report.diagnosis else ""),
                assessment_context_factors=json.dumps(report.manager_context_factors),
                assessment_context_note=report.manager_context_note,
                status="pending")
            s.add(rec)
            s.flush()
            ids.append(rec.id)
        s.commit()
    return ids


def pending_queue() -> pd.DataFrame:
    with SessionLocal() as s:
        rows = s.query(Recommendation).filter_by(status="pending").order_by(Recommendation.id).all()
        return pd.DataFrame([{
            "id": r.id, "employee_id": r.employee_id, "as_of": r.as_of, "cause": r.cause, "headline": r.headline,
            "priority": r.priority, "actions": json.loads(r.actions), "summary": r.diagnosis_summary,
            "assessment_context_factors": json.loads(r.assessment_context_factors or "[]"),
            "assessment_context_note": r.assessment_context_note or "",
        } for r in rows])


def decide(
    rec_id: int,
    decision: str,
    note: str = "",
    modified_actions: list[str] | None = None,
    manager_factors: list[str] | None = None,
    modified_headline: str | None = None,
) -> None:
    if decision not in {"approved", "modified", "rejected"}:
        raise ValueError(f"Unsupported recommendation decision: {decision}")
    manager_factors = list(dict.fromkeys(manager_factors or []))
    unknown_factors = set(manager_factors) - MANAGER_CONTEXT_FACTORS.keys()
    if unknown_factors:
        raise ValueError(
            f"Unsupported manager context factor(s): {', '.join(sorted(unknown_factors))}"
        )
    if len(note) > 2000:
        raise ValueError("Manager review note must be 2000 characters or fewer")
    adjusted_headline = modified_headline or ""
    adjusted_actions = modified_actions or []

    with SessionLocal() as s:
        rec = s.get(Recommendation, rec_id)
        if rec is None:
            raise LookupError(f"Recommendation {rec_id} does not exist")
        if rec.status != "pending":
            raise ValueError(f"Recommendation {rec_id} has already been reviewed")

    review_summary = summarize_manager_review(
        note=note,
        factors=[MANAGER_CONTEXT_FACTORS[factor] for factor in manager_factors],
        headline=adjusted_headline,
        actions=adjusted_actions,
        use_llm=USE_LLM,
    )

    with SessionLocal() as s:
        rec = s.get(Recommendation, rec_id)
        if rec is None:
            raise LookupError(f"Recommendation {rec_id} does not exist")
        if rec.status != "pending":
            raise ValueError(f"Recommendation {rec_id} has already been reviewed")

        rec.status, rec.reviewer_note, rec.decided_at = (
            decision, note, datetime.now(UTC).replace(tzinfo=None))
        rec.manager_factors = json.dumps(manager_factors)
        rec.review_context_summary = review_summary
        if decision in {"approved", "modified"} and modified_headline:
            rec.headline = modified_headline
        if decision in {"approved", "modified"} and modified_actions is not None:
            rec.actions = json.dumps(modified_actions)
        if decision in {"approved", "modified"}:
            bundle = load_bundle(rec.as_of)
            base = float(bundle.overall_series(rec.employee_id).iloc[-3:].mean())
            s.add(
                Intervention(
                    recommendation_id=rec.id,
                    employee_id=rec.employee_id,
                    start_period=rec.as_of,
                    baseline_score=round(base, 1),
                )
            )
        s.commit()


def track_interventions(bundle: DataBundle, min_months: int = 2) -> pd.DataFrame:
    """Closed loop: compare the employee's recent score with the score when the intervention started."""
    out = []
    with SessionLocal() as s:
        for iv in s.query(Intervention).all():
            if iv.start_period > bundle.as_of:      # intervention hasn't started yet at this as-of month
                continue
            code = bundle.employees.loc[bundle.employees["id"] == iv.employee_id, "code"].iloc[0]
            series = bundle.overall_series(iv.employee_id)
            start = iv.start_period
            # baseline = 3 months up to the start period (recomputed so seeded rows are consistent)
            before = series[series.index <= start].iloc[-3:].mean()
            months_since = int(bundle.as_of[:4]) * 12 + int(bundle.as_of[5:]) - (int(start[:4]) * 12 + int(start[5:]))
            if months_since < min_months:
                outcome, now, delta = "too_early", np.nan, np.nan
            else:
                now = float(series.iloc[-3:].mean())
                delta = now - float(before)
                outcome = "improved" if delta >= IMPROVE_MARGIN else ("worsened" if delta <= -IMPROVE_MARGIN else "no_change")
                iv.baseline_score, iv.followup_period, iv.followup_score, iv.outcome = (
                    round(float(before), 1), bundle.as_of, round(now, 1), outcome)
            out.append({
                "employee": code,
                "started": start,
                "headline": iv.recommendation.headline,
                "score_at_start": round(float(before), 1),
                "score_now": None if np.isnan(now) else round(now, 1),
                "change": None if np.isnan(delta) else round(delta, 1),
                "outcome": outcome,
            })
        s.commit()
    return pd.DataFrame(out)
