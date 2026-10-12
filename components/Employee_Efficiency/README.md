# Employee Efficiency and Monitoring AI Agent

Individual research component of:

**Hierarchical Human-Inspired Multi-Agent Decision Support Framework for Enterprise Technology Service Operations**

Student: **K.A.C.N. Jayarathna – IT23366268**

---

## Research Goal

This component investigates whether an explainable, human-in-the-loop agent can continuously monitor
after-sales employee performance, separate genuine performance problems from context-driven variation,
and track whether recommended interventions actually work.

The proposed approach combines:

- role-specific KPI monitoring (29 KPIs, 4 roles, 5 categories);
- historical benchmarking and trajectory/checkpoint analysis;
- explicit confirmed vs projected data labelling (three-phase state machine);
- contextual analysis before any performance conclusion;
- explainable root-cause diagnosis (workload, skill, process, external);
- scenario-based recommendations with mandatory human review;
- closed intervention-tracking loop.

Deterministic Python performs all KPI maths and diagnosis. The LLM (optional) only narrates
aggregated, pseudonymised facts.

---

## Research Pipeline

```text
Employee KPI Records (SQLite, pseudonymised)
          v
  Role Identification
          v
  Performance Analysis      -> role-specific KPIs, 0-100 index, category scores
          v
  Trend Analysis            -> trajectory, checkpoints, confirmed/projected, deviation detection
          v
  Context & Gap Analysis    -> workload, complexity, downtime, market pressure, feedback, peers
          v
  Root-Cause Diagnosis      -> workload / skill / process / external / undetermined
          v
  Improvement Planning      -> scenario-based recommendation
          v
  Manager Review            -> Approve / Modify / Reject
          v
  Intervention Tracking     -> improved / no change / worsened
```

---

## Three-Phase State Machine

| Phase | As-of month | Mid-year checkpoint | Full-year checkpoint |
|-------|-------------|---------------------|----------------------|
| Pre mid-year | Jan–May | Projected | Projected |
| Post mid-year | Jun–Nov | Confirmed | Projected |
| Post full-year | Dec | Confirmed | Confirmed |

---

## Project Structure

```text
src/config.py            settings
src/schemas/             KPI registry and typed outputs
src/database/models.py   SQLite schema
src/services/            data generator, KPI engine, trajectory, context, diagnosis,
                         recommendation, review, baselines, evaluation, narrator
src/agents/              performance, trend, context and improvement sub-agents
src/workflow/graph.py    LangGraph orchestrator
app/main.py              Streamlit dashboard
tests/                   pytest suite
```

---

## Data

No real Metropolitan data is used. `src/services/data_generator.py` creates pseudonymised synthetic
employees with known scenarios and ground-truth labels. Evaluation results therefore validate the
pipeline, not real-world accuracy.

---

## Run

```powershell
cd components\Employee_Efficiency
uv python install 3.11
uv sync
copy .env.example .env
uv run python -m src.database.models
uv run python -m src.services.data_generator
uv run python test_database.py
uv run pytest -v
uv run streamlit run app/main.py
```

Optional LLM narration: set `OPENROUTER_API_KEY` in `.env`, then run `uv run python test_connection.py`.

---

## Status

Implemented: KPI engine, trajectory/checkpoints, deviation detection, context analysis, diagnosis,
recommendations, human review, intervention tracking, evaluation, dashboard.

Planned: wellbeing signals, Security Layer integration, shared dashboard integration, evaluation
with real or expert-labelled data.