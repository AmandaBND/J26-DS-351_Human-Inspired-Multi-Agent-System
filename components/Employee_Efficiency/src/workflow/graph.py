"""LangGraph orchestrator: wires the sub-agents into one explainable pipeline.

 identify_role -> performance_analysis -> trend_analysis --(deviation?)--> context_analysis
     -> diagnosis_and_planning -> narrate -> END
                                 \\--(no deviation)--> context_analysis(light) -> narrate -> END
(The human-review gate is handled by src/services/review.py: nothing is acted on until approved.)
"""
from __future__ import annotations

from typing import Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from src.agents import context_agent, improvement_agent, performance_agent, trend_agent
from src.schemas.assessment import AssessmentReport
from src.schemas.assessment import Checkpoint, ContextFindings, Trajectory
from src.schemas.kpi import ROLE_LABELS, Phase, Role
from src.services.data_access import DataBundle
from src.services.llm_narrator import narrate
from src.services.trajectory import determine_phase


class AgentState(TypedDict, total=False):
    employee_code: str
    use_llm: Optional[bool]
    emp_id: int
    role: str
    perf: dict
    trend: dict
    context: object
    diagnosis: object
    recommendations: list
    report: AssessmentReport


def build_graph(bundle: DataBundle):
    def identify_role(state: AgentState) -> AgentState:
        e = bundle.emp(state["employee_code"])
        return {"emp_id": int(e["id"]), "role": e["role"]}

    def performance_analysis(state: AgentState) -> AgentState:
        return {"perf": performance_agent.analyse(bundle, state["emp_id"])}

    def trend_analysis(state: AgentState) -> AgentState:
        p = state["perf"]
        return {"trend": trend_agent.analyse(bundle, state["emp_id"], p["declining_categories"], p["declining_kpis"])}

    def context_analysis(state: AgentState) -> AgentState:
        return {"context": context_agent.analyse(bundle, state["emp_id"], state["role"])}

    def diagnosis_and_planning(state: AgentState) -> AgentState:
        diag, recs = improvement_agent.plan(state["trend"]["deviation"], state["context"])
        return {"diagnosis": diag, "recommendations": recs}

    def narrate_node(state: AgentState) -> AgentState:
        t, p = state["trend"], state["perf"]
        phase = t["trajectory"].phase
        proj = t["trajectory"].full_year.n_projected + t["trajectory"].mid_year.n_projected
        report = AssessmentReport(
            employee_code=state["employee_code"], role=ROLE_LABELS[Role(state["role"])], as_of=bundle.as_of,
            phase=phase, overall_score=p["overall_score"], category_scores=p["category_scores"], kpis=p["kpis"],
            trajectory=t["trajectory"], deviation=t["deviation"], context=state["context"],
            diagnosis=state.get("diagnosis"), recommendations=state.get("recommendations", []),
            data_through=bundle.data_through[state["emp_id"]],
            data_note=("Complete employee data is available through " + bundle.data_through[state["emp_id"]] + ". "
                       + (f"{proj} checkpoint month(s) are PROJECTED from a damped trend." if proj else
                          "All available checkpoint months are confirmed.")))
        report.narrative = narrate(report, state.get("use_llm"))
        return {"report": report}

    g = StateGraph(AgentState)
    g.add_node("identify_role", identify_role)
    g.add_node("performance_analysis", performance_analysis)
    g.add_node("trend_analysis", trend_analysis)
    g.add_node("context_analysis", context_analysis)
    g.add_node("diagnosis_and_planning", diagnosis_and_planning)
    g.add_node("narrate", narrate_node)
    g.add_edge(START, "identify_role")
    g.add_edge("identify_role", "performance_analysis")
    g.add_edge("performance_analysis", "trend_analysis")
    g.add_edge("trend_analysis", "context_analysis")
    g.add_conditional_edges("context_analysis", lambda s: "deviating" if s["trend"]["deviation"].is_deviating else "healthy",
                            {"deviating": "diagnosis_and_planning", "healthy": "narrate"})
    g.add_edge("diagnosis_and_planning", "narrate")
    g.add_edge("narrate", END)
    return g.compile()


def run_assessment(bundle: DataBundle, employee_code: str, use_llm: Optional[bool] = False,
                   graph=None) -> AssessmentReport:
    """Run an employee assessment, withholding diagnosis when data is insufficient."""
    employee_id = int(bundle.emp(employee_code)["id"])
    if bundle.insufficient_data.get(employee_id, False):
        role = Role(bundle.emp(employee_code)["role"])
        through = bundle.data_through.get(employee_id, "")
        reason = bundle.insufficient_reason.get(employee_id, "insufficient complete performance data")
        empty_checkpoint = Checkpoint(
            name="Mid-year", score=None, status="projected", n_confirmed=0, n_projected=0)
        trajectory = Trajectory(
            phase=determine_phase(bundle.as_of),
            cycle_year=int(bundle.as_of[:4]),
            points=[],
            mid_year=empty_checkpoint,
            full_year=Checkpoint(
                name="Full-year", score=None, status="projected", n_confirmed=0, n_projected=0),
            baseline_score=float(bundle.baseline_overall.get(employee_id, 0.0))
                if bundle.baseline_overall.get(employee_id, 0.0) == bundle.baseline_overall.get(employee_id, 0.0)
                else 0.0,
            delta_vs_baseline=0.0,
        )
        report = AssessmentReport(
            employee_code=employee_code,
            role=ROLE_LABELS[role],
            as_of=bundle.as_of,
            phase=determine_phase(bundle.as_of),
            overall_score=0.0,
            category_scores={},
            kpis=[],
            trajectory=trajectory,
            deviation=bundle.deviations[employee_id],
            context=ContextFindings(
                workload_ratio=1.0,
                complexity_delta=0.0,
                overtime_hours=0.0,
                downtime_delta=0.0,
                price_change_pct=0.0,
                competitor_offers=0.0,
                budget_share=0.0,
                sentiment=0.0,
                feedback_tags={},
                peer_deviation_share=0.0,
            ),
            data_through=through,
            insufficient_data=True,
            insufficient_reason=reason,
            data_note=f"Complete employee data is available through {through or 'no month'}.",
        )
        report.narrative = (
            f"An assessment cannot be made because there is insufficient complete data "
            f"through {through or 'the selected reporting period'}. {reason.capitalize()}. "
            "No performance conclusion or action is recommended."
        )
        return report
    graph = graph or build_graph(bundle)
    return graph.invoke({"employee_code": employee_code, "use_llm": use_llm})["report"]


def run_team(bundle: DataBundle) -> list[AssessmentReport]:
    graph = build_graph(bundle)
    return [run_assessment(bundle, c, use_llm=False, graph=graph) for c in bundle.employees["code"]]
