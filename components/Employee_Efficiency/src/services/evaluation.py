"""Evaluate assessments only against outcome labels supplied for the company dataset."""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from src.config import DATA_DIR, PRIVATE_DIR
from src.database.models import Employee, HROutcome, SessionLocal
from src.services.baselines import threshold_flag
from src.services.data_access import DataBundle
from src.workflow.graph import build_graph, run_assessment

GROUND_TRUTH_COLUMNS = [
    "employee_code", "role", "scenario", "cycle_year", "has_deviation", "root_cause",
]
VERIFIED_OUTCOMES_PATH = DATA_DIR / "verified_outcomes.csv"


def prf(pred: list[bool], truth: list[bool]) -> dict[str, float | int]:
    """Return precision, recall, F1, and confusion counts for binary labels."""
    tp = sum(p and t for p, t in zip(pred, truth))
    fp = sum(p and not t for p, t in zip(pred, truth))
    fn = sum((not p) and t for p, t in zip(pred, truth))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def load_ground_truth(path: Path = VERIFIED_OUTCOMES_PATH) -> pd.DataFrame:
    """Load company-verified outcomes and replace employee numbers with pseudonyms."""
    if not path.is_file():
        return pd.DataFrame(columns=GROUND_TRUTH_COLUMNS)
    mapping_path = PRIVATE_DIR / "pseudonym_map.csv"
    if not mapping_path.is_file():
        raise FileNotFoundError("A private pseudonym map is required to load verified employee outcomes.")
    labels = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"employee_no", "role", "scenario", "cycle_year", "has_deviation", "root_cause"}
    missing = required - set(labels.columns)
    if missing:
        raise ValueError(f"Verified outcome file is missing required columns: {sorted(missing)}")
    mapping = pd.read_csv(mapping_path, dtype=str, keep_default_na=False)
    code_by_number = dict(zip(mapping["employee_no"], mapping["code"]))
    labels["employee_code"] = labels["employee_no"].map(code_by_number)
    unmapped = labels["employee_code"].isna()
    if unmapped.any():
        raise ValueError(f"{int(unmapped.sum())} verified outcome row(s) reference unknown employees.")
    labels["cycle_year"] = pd.to_numeric(labels["cycle_year"], errors="raise").astype(int)
    labels["has_deviation"] = labels["has_deviation"].str.strip().str.casefold().isin(
        {"true", "1", "yes", "y"})
    labels = labels.rename(columns={"role": "role", "scenario": "scenario", "root_cause": "root_cause"})
    return labels[GROUND_TRUTH_COLUMNS]


def _legacy_outcomes(year: int) -> pd.DataFrame:
    """Read pre-existing outcome rows only when a legacy demo database explicitly contains them."""
    with SessionLocal() as session:
        outcomes = session.query(HROutcome).filter_by(cycle_year=year).all()
        employees = {employee.id: employee for employee in session.query(Employee).all()}
    return pd.DataFrame([
        {
            "employee_code": employees[row.employee_id].code,
            "role": employees[row.employee_id].role,
            "scenario": "",
            "cycle_year": row.cycle_year,
            "has_deviation": bool(row.has_deviation),
            "root_cause": row.root_cause,
        }
        for row in outcomes
        if row.employee_id in employees
    ], columns=GROUND_TRUTH_COLUMNS)


def _summary_row(report, baseline: bool, latency: float) -> dict[str, object]:
    """Build one privacy-safe employee result row."""
    return {
        "employee": report.employee_code,
        "role": report.role,
        "agent_deviation": report.deviation.is_deviating,
        "agent_cause": report.diagnosis.primary_cause if report.diagnosis else "none",
        "baseline_flag": baseline,
        "insufficient_data": report.insufficient_data,
        "data_through": report.data_through,
        "latency_s": latency,
        "evidence": (
            " · ".join(report.diagnosis.ranked[0].evidence)
            if report.diagnosis and report.diagnosis.ranked else ""
        ),
    }


def evaluate(bundle: DataBundle) -> dict[str, object]:
    """Compare agent and baseline results with verified labels when present."""
    year = int(bundle.as_of[:4])
    labels = load_ground_truth()
    label_source = "verified_outcomes.csv" if not labels.empty else ""
    if labels.empty:
        labels = _legacy_outcomes(year)
        label_source = "stored review outcomes" if not labels.empty else ""

    graph = build_graph(bundle)
    rows, times = [], []
    for _, employee in bundle.employees.iterrows():
        started = time.perf_counter()
        report = run_assessment(bundle, str(employee["code"]), use_llm=False, graph=graph)
        elapsed = time.perf_counter() - started
        times.append(elapsed)
        rows.append(_summary_row(
            report,
            threshold_flag(bundle, int(employee["id"])) if not report.insufficient_data else False,
            elapsed,
        ))
    detail = pd.DataFrame(rows)
    comparable = detail.merge(
        labels[labels["cycle_year"] == year],
        left_on="employee",
        right_on="employee_code",
        how="inner",
        suffixes=("", "_truth"),
    ) if not labels.empty else pd.DataFrame()

    if comparable.empty:
        no_labels = "No verified outcome labels are available for this reporting cycle."
        return {
            "as_of": bundle.as_of,
            "n": len(detail),
            "labels_available": False,
            "label_source": "",
            "label_message": no_labels,
            "agent": None,
            "rule_based_baseline": None,
            "root_cause_accuracy": None,
            "context_driven_correctly_not_blamed": None,
            "avg_latency_s": round(sum(times) / len(times), 3) if times else 0.0,
            "max_latency_s": round(max(times), 3) if times else 0.0,
            "agent_baseline_agreement": (
                round(float((detail["agent_deviation"] == detail["baseline_flag"]).mean()), 3)
                if not detail.empty else None
            ),
            "confusion_matrix": pd.DataFrame(),
            "per_scenario": pd.DataFrame(),
            "disagreements": pd.DataFrame(),
            "detail": detail,
        }

    eligible = comparable[~comparable["insufficient_data"]]
    prediction = eligible["agent_deviation"].astype(bool).tolist()
    truth = eligible["has_deviation"].astype(bool).tolist()
    baseline_prediction = eligible["baseline_flag"].astype(bool).tolist()
    truth_causes = comparable[comparable["has_deviation"]]
    cause_rows = truth_causes[
        truth_causes["agent_cause"].ne("none")
    ]
    cause_accuracy = (
        float((cause_rows["agent_cause"] == cause_rows["root_cause"]).mean())
        if not cause_rows.empty else float("nan")
    )
    context_rows = truth_causes[truth_causes["root_cause"].isin(["process", "external"])]
    context_ok = (
        float(context_rows["agent_cause"].isin(["process", "external"]).mean())
        if not context_rows.empty else float("nan")
    )
    confusion = pd.crosstab(
        truth_causes["root_cause"], truth_causes["agent_cause"], rownames=["Truth"], colnames=["Assessment"]
    )
    scenario_rows = []
    if "scenario" in comparable and comparable["scenario"].astype(str).str.len().gt(0).any():
        for scenario, group in comparable.groupby("scenario"):
            scenario_rows.append({
                "scenario": scenario,
                "n": len(group),
                "deviation_f1": prf(
                    group["agent_deviation"].astype(bool).tolist(),
                    group["has_deviation"].astype(bool).tolist(),
                )["f1"],
                "cause_accuracy": float(
                    (group[group["has_deviation"]]["agent_cause"]
                     == group[group["has_deviation"]]["root_cause"]).mean()
                ) if group["has_deviation"].any() else float("nan"),
            })
    disagreements = comparable[
        comparable["has_deviation"]
        & comparable["agent_cause"].ne(comparable["root_cause"])
    ][["employee", "role", "root_cause", "agent_cause", "evidence"]]
    return {
        "as_of": bundle.as_of,
        "n": len(comparable),
        "labels_available": True,
        "label_source": label_source,
        "label_message": "",
        "agent": prf(prediction, truth),
        "rule_based_baseline": prf(baseline_prediction, truth),
        "root_cause_accuracy": round(cause_accuracy, 3),
        "context_driven_correctly_not_blamed": round(context_ok, 3),
        "avg_latency_s": round(sum(times) / len(times), 3) if times else 0.0,
        "max_latency_s": round(max(times), 3) if times else 0.0,
        "agent_baseline_agreement": round(float(
            (eligible["agent_deviation"] == eligible["baseline_flag"]).mean()
        ), 3) if not eligible.empty else None,
        "confusion_matrix": confusion,
        "per_scenario": pd.DataFrame(scenario_rows),
        "disagreements": disagreements,
        "detail": detail,
    }


def evaluate_recovery_case() -> dict[str, object]:
    """Report whether a verified recovery case is configured for assessment."""
    labels = load_ground_truth()
    recovered = labels[labels["scenario"].astype(str).str.casefold().eq("recovered")]
    if recovered.empty:
        return {
            "available": False,
            "message": "No verified recovery-case outcome labels are configured.",
        }
    return {
        "available": False,
        "message": "Recovery replay requires a period-specific verified outcome export.",
    }
