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





## Run

```powershell
cd components\Employee_Efficiency
uv sync
uv run python -m src.database.models
uv run python -m src.services.preprocessing.pipeline
uv run python test_database.py
uv run pytest -v
uv run streamlit run app/main.py
```

Optional LLM narration: add your key to `OPENROUTER_API_KEY` in `.env` (and keep `USE_LLM=true`),
then run `uv run python test_connection.py`. Individual employee assessments use the LLM when enabled;
the workforce batch summary remains deterministic. Narration receives only aggregated facts and
pseudonymous employee codes. Raw feedback and row-level data remain local.

On Employee Performance Analysis, managers can also provide context before running an assessment.
Each selected structured factor contributes 0.25 to its mapped rule-based cause score; reporting a
data-quality concern withholds causal conclusions and recommends verifying the source data first.
This never changes KPI values or overall performance scores. The free-text note is labeled
manager-reported and can inform narration, but is not used as a numeric diagnosis signal. Assessment
context is retained when a proposal is submitted to the review queue. Managers review or edit the
resulting action plan there, while intervention tracking focuses on outcomes and scores.

## Data handling

- `data/raw/` contains the company operational exports used by this component.
- The pipeline maps employee numbers to `EMP-001` through `EMP-034` before writing database records.
- The private mapping is stored in `data/private/pseudonym_map.csv`; never commit or share that directory.
- `data/employee_efficiency_company.db` is the company-data database generated locally and ignored by Git.
- The previous `data/employee_efficiency.db` is left untouched; set `DATABASE_PATH` in `.env` to use another database.
- Verified assessment outcomes, when supplied, belong in `data/verified_outcomes.csv`. The evaluation does not treat historical KPI data as ground truth.
- The Evaluation workspace can also compare against `data/synthetic_truth/ground_truth_labels.csv` as a development benchmark. Results against generated labels are not real-world accuracy.
- `src/services/data_generator.py` is a legacy 20-employee demo seed; use the preprocessing pipeline for the company export.

---

## Status

Implemented: company-export cleaning and pseudonymization, monthly KPI/context aggregation,
trajectory/checkpoints, missing-data handling, explainable diagnosis, manager review, intervention
tracking, evaluation where verified outcomes are available, and the six-workspace dashboard.

Planned: wellbeing signals, Security Layer integration, shared dashboard integration, and validated
period-specific outcome labels for evaluation.