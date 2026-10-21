import json
from types import SimpleNamespace
from uuid import uuid4

import pandas as pd
import pytest

from src.schemas.assessment import CauseScore, DeviationResult, Diagnosis
from src.database.models import Employee, Intervention, Recommendation, SessionLocal, init_db
from src.services import review
from src.services.assessment_context import apply_assessment_context


def test_context_factors_replace_actions_for_non_individual_context():
    headline, actions = review.adjust_recommendation(
        "Offer focused training and mentoring",
        ["Arrange coaching."],
        ["system_process", "training_support"],
    )

    assert headline == "Reassess using manager-confirmed context"
    assert any("operations or IT" in action for action in actions)
    assert any("not as a disciplinary action" in action for action in actions)
    assert "Arrange coaching." not in actions


def test_training_context_augments_existing_actions():
    headline, actions = review.adjust_recommendation(
        "Manager review needed", ["Speak with the employee."], ["training_support"]
    )

    assert headline == "Manager review needed"
    assert actions[0] == "Speak with the employee."
    assert any("developmental support" in action for action in actions)


def test_unknown_manager_context_factor_is_rejected():
    with pytest.raises(ValueError, match="Unsupported manager context factor"):
        review.adjust_recommendation("Plan", [], ["unknown"])


def test_assessment_context_changes_diagnosis_and_recommendation():
    deviation = DeviationResult(
        is_deviating=True,
        severity="medium",
        drop=8.0,
        slope_per_month=-2.0,
        months_below=3,
        declining_categories=["Quality"],
        declining_kpis=["TECH_CSAT"],
    )
    diagnosis = Diagnosis(
        primary_cause="skill",
        confidence=0.3,
        ranked=[
            CauseScore(cause="skill", score=0.3, evidence=["Quality declined."]),
            CauseScore(cause="process", score=0.2, evidence=[]),
            CauseScore(cause="workload", score=0.1, evidence=[]),
            CauseScore(cause="external", score=0.05, evidence=[]),
        ],
        employee_controllable="yes",
        verdict="Possible training gap.",
    )

    adjusted_diagnosis, recommendations = apply_assessment_context(
        deviation, diagnosis, ["system_process"]
    )

    assert adjusted_diagnosis.primary_cause == "process"
    assert "Manager-reported context (not independently verified)" in (
        adjusted_diagnosis.ranked[0].evidence[-1]
    )
    assert recommendations[0].cause == "process"
    assert diagnosis.primary_cause == "skill"


def test_data_quality_context_suppresses_causal_conclusion():
    diagnosis = Diagnosis(
        primary_cause="skill",
        confidence=0.5,
        ranked=[CauseScore(cause="skill", score=0.5, evidence=[])],
        employee_controllable="yes",
        verdict="Possible training gap.",
    )
    deviation = DeviationResult(
        is_deviating=True,
        severity="medium",
        drop=8.0,
        slope_per_month=-2.0,
        months_below=3,
    )

    adjusted, recommendations = apply_assessment_context(
        deviation, diagnosis, ["data_quality"]
    )

    assert adjusted.primary_cause == "undetermined"
    assert adjusted.employee_controllable == "unknown"
    assert recommendations[0].headline == "Verify source data before drawing conclusions"


def test_review_queue_submission_persists_assessment_context():
    init_db()
    code = f"TEST-{uuid4().hex[:12]}"
    with SessionLocal() as session:
        employee = Employee(code=code, role="technician", team="Test", hire_year=2020)
        session.add(employee)
        session.flush()
        employee_id = employee.id

    report = SimpleNamespace(
        deviation=SimpleNamespace(is_deviating=True),
        employee_code=code,
        as_of="2026-09",
        recommendations=[
            SimpleNamespace(
                cause="process",
                headline="Fix the system or process issue",
                actions=["Refer issue to operations."],
                priority="medium",
                monitor_kpis=[],
            )
        ],
        diagnosis=SimpleNamespace(verdict="Manager-reported process disruption."),
        manager_context_factors=["system_process"],
        manager_context_note="A system outage affected this period.",
    )
    bundle = SimpleNamespace(emp=lambda _code: {"id": employee_id})

    recommendation_ids = review.submit_for_review(report, bundle)

    with SessionLocal() as session:
        saved = session.get(Recommendation, recommendation_ids[0])
        assert json.loads(saved.assessment_context_factors) == ["system_process"]
        assert saved.assessment_context_note == "A system outage affected this period."


def test_review_decision_persists_manager_context(monkeypatch):
    init_db()
    monkeypatch.setattr(review, "USE_LLM", False)
    code = f"TEST-{uuid4().hex[:12]}"
    with SessionLocal() as session:
        employee = Employee(code=code, role="technician", team="Test", hire_year=2020)
        session.add(employee)
        session.flush()
        recommendation = Recommendation(
            employee_id=employee.id,
            as_of="2026-09",
            cause="skill",
            headline="Offer focused training and mentoring",
            actions='["Arrange coaching."]',
            priority="medium",
            monitor_kpis="[]",
            diagnosis_summary="Test recommendation",
            status="pending",
        )
        session.add(recommendation)
        session.flush()
        recommendation_id = recommendation.id
        session.commit()

    review.decide(
        recommendation_id,
        "rejected",
        "System downtime affected this review.",
        manager_factors=["system_process"],
    )

    with SessionLocal() as session:
        saved = session.get(Recommendation, recommendation_id)
        assert saved.status == "rejected"
        assert saved.reviewer_note == "System downtime affected this review."
        assert json.loads(saved.manager_factors) == ["system_process"]
        assert "System or process disruption" in saved.review_context_summary


def test_approved_context_adjustment_updates_actions_and_creates_intervention(monkeypatch):
    init_db()
    monkeypatch.setattr(review, "USE_LLM", False)
    monkeypatch.setattr(
        review,
        "load_bundle",
        lambda _as_of: SimpleNamespace(
            overall_series=lambda _employee_id: pd.Series([70.0, 72.0, 74.0])
        ),
    )
    code = f"TEST-{uuid4().hex[:12]}"
    with SessionLocal() as session:
        employee = Employee(code=code, role="technician", team="Test", hire_year=2020)
        session.add(employee)
        session.flush()
        recommendation = Recommendation(
            employee_id=employee.id,
            as_of="2026-09",
            cause="skill",
            headline="Offer focused training and mentoring",
            actions='["Arrange coaching."]',
            priority="medium",
            monitor_kpis="[]",
            diagnosis_summary="Test recommendation",
            status="pending",
        )
        session.add(recommendation)
        session.flush()
        recommendation_id = recommendation.id
        session.commit()

    review.decide(
        recommendation_id,
        "modified",
        "System issue confirmed.",
        modified_actions=[
            "Refer the disruption to operations.",
            "Defer individual conclusions until the issue is resolved.",
        ],
        manager_factors=["system_process"],
        modified_headline="Reassess using manager-confirmed context",
    )

    with SessionLocal() as session:
        saved = session.get(Recommendation, recommendation_id)
        intervention = session.query(Intervention).filter_by(
            recommendation_id=recommendation_id
        ).one()
        assert saved.headline == "Reassess using manager-confirmed context"
        assert json.loads(saved.actions) == [
            "Refer the disruption to operations.",
            "Defer individual conclusions until the issue is resolved.",
        ]
        assert intervention.baseline_score == 72.0
