"""Legacy 20-employee pipeline checks retained during company-data migration."""

import pytest

from src.database.models import Intervention, Recommendation, SessionLocal, init_db
from src.schemas.kpi import KPI_REGISTRY, ROLE_KPIS, Phase, Role
from src.services import trajectory
from src.services.data_generator import generate_and_seed
from src.services.data_access import load_bundle
from src.services.diagnosis import sat
from src.services.evaluation import evaluate, prf
from src.services.kpi_engine import INDEX_CENTER, label_for
from src.services.review import decide
from src.workflow.graph import run_assessment


@pytest.fixture(scope="session")
def bundle():
    init_db()
    generate_and_seed()
    return load_bundle("2026-09")


def test_registry_matches_framework():
    assert len(KPI_REGISTRY) == 29
    assert {r: len(v) for r, v in ROLE_KPIS.items()} == {
        Role.TECHNICIAN: 8, Role.TPO_SERVICE: 8, Role.AMC_PROCESSING: 7, Role.CONTRACTS_COORDINATOR: 6}


@pytest.mark.parametrize("as_of,phase", [("2026-03", Phase.PRE_MID_YEAR), ("2026-05", Phase.PRE_MID_YEAR),
                                          ("2026-06", Phase.POST_MID_YEAR), ("2026-11", Phase.POST_MID_YEAR),
                                          ("2025-12", Phase.POST_FULL_YEAR)])
def test_phase_state_machine(as_of, phase):
    assert trajectory.determine_phase(as_of) == phase


def test_benchmark_center(bundle):
    base = bundle.kpi[bundle.kpi["period"].str[:4] == "2024"]
    assert abs(base["index"].mean() - INDEX_CENTER) < 3     # history sits near the benchmark by construction


def test_index_direction(bundle):
    # lower MTTR (lower-is-better) must give a higher index than a high MTTR
    k = bundle.kpi[bundle.kpi["kpi_code"] == "TECH_MTTR"].sort_values("value")
    assert k["index"].iloc[0] > k["index"].iloc[-1]


def test_confirmed_vs_projected_labels(bundle):
    r = run_assessment(bundle, "EMP-001")
    labels = {p.period: p.status.value for p in r.trajectory.points}
    assert all(v == "confirmed" for p, v in labels.items() if p <= "2026-09")
    assert all(v == "projected" for p, v in labels.items() if p > "2026-09")
    assert r.trajectory.full_year.status == "partly projected"
    assert r.trajectory.mid_year.status == "confirmed"


def test_no_future_leakage():
    b = load_bundle("2026-03")
    assert b.kpi["period"].max() == "2026-03"


def test_expected_diagnoses(bundle):
    expect = {"EMP-003": "workload", "EMP-004": "skill", "EMP-011": "process", "EMP-018": "external"}
    for code, cause in expect.items():
        r = run_assessment(bundle, code)
        assert r.deviation.is_deviating
        assert r.diagnosis.primary_cause == cause
        assert r.recommendations and r.recommendations[0].requires_human_review


def test_stable_employee_not_flagged(bundle):
    r = run_assessment(bundle, "EMP-001")
    assert not r.deviation.is_deviating and r.diagnosis is None


def test_context_driven_not_blamed(bundle):
    assert run_assessment(bundle, "EMP-018").diagnosis.employee_controllable == "no"


def test_saturation():
    assert sat(0, 1, 2) == 0 and sat(3, 1, 2) == 1 and sat(1.5, 1, 2) == 0.5


def test_label_text():
    assert label_for(90) == "Strong" and label_for(40) == "Concern"


def test_evaluation_meets_targets(bundle):
    res = evaluate(bundle)
    assert res["agent"]["f1"] >= 0.80 and res["root_cause_accuracy"] >= 0.80
    assert res["max_latency_s"] <= 5


def test_prf_reports_accuracy_and_confusion_counts():
    result = prf([True, False, True, False], [True, True, False, False])
    assert result == {
        "accuracy": 0.5,
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "tp": 1,
        "fp": 1,
        "fn": 1,
        "tn": 1,
    }


def test_decide_rejects_invalid_decision():
    with pytest.raises(ValueError, match="Unsupported recommendation decision"):
        decide(-1, "approve")


def test_decide_rejects_missing_recommendation():
    with pytest.raises(LookupError, match="does not exist"):
        decide(-1, "approved")


def test_recommendation_can_only_be_reviewed_once(bundle):
    with SessionLocal() as session:
        recommendation = Recommendation(
            employee_id=int(bundle.employees.iloc[0]["id"]),
            as_of=bundle.as_of,
            cause="test",
            headline="Review lifecycle test",
            actions="[]",
            priority="low",
            monitor_kpis="[]",
            status="pending",
        )
        session.add(recommendation)
        session.commit()
        rec_id = recommendation.id

    decide(rec_id, "approved")
    with pytest.raises(ValueError, match="already been reviewed"):
        decide(rec_id, "rejected")

    with SessionLocal() as session:
        recommendation = session.get(Recommendation, rec_id)
        interventions = session.query(Intervention).filter_by(recommendation_id=rec_id).all()
        assert recommendation is not None
        assert recommendation.status == "approved"
        assert len(interventions) == 1
