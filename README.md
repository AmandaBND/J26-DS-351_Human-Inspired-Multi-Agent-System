# Emotion-Aware After Sales Service Decision Intelligence Agent

## Overview

The Emotion-Aware After Sales Service Decision Intelligence Agent is a hierarchical multi-agent decision-support system designed to support after-sales service decision-making.

The system combines three main sources of information:

- Customer voice-derived affective signals
- Conversational context from customer interactions
- After-sales operational data

Specialized agents analyze these information sources and combine them to create a more complete understanding of the customer and service situation. The system then generates explainable service recommendations with supporting evidence and confidence information.

A Human-in-the-Loop approach is used so that an authorized Area Coordinator or manager can review, accept, modify, or reject the generated recommendation before an important service action is taken.

## Main Components

- Voice Emotion Analysis Agent
- Text Context Analysis Agent
- Operational Context Agent
- Context Fusion Agent
- Analytical Agents
- Supervisor Agent
- Human-in-the-Loop Review and Feedback Mechanism

## Research Focus

The research investigates whether combining voice-derived affective signals, conversational context, and after-sales operational evidence within a hierarchical multi-agent framework can provide more context-aware, explainable, and human-validated after-sales service decision support.

## Development Status

**Current Phase:** Initial Development

Development started in October 2026.

### Current Progress

- [x] Research proposal completed
- [x] Git repository configured
- [x] Feature branch created
- [x] Initial project documentation
- [x] Development environment setup
- [ ] Data preparation
- [ ] Voice Emotion Analysis Agent
- [ ] Text Context Analysis Agent
- [ ] Operational Context Agent
- [ ] Context Fusion Agent
- [ ] Analytical Agents
- [ ] Supervisor Agent
- [ ] Human-in-the-Loop mechanism
- [ ] System integration
- [ ] Testing and evaluation

## Student

**M. A. H. M. Chandrakeerthi**  
**Student ID:** IT23359406  
**Specialization:** Data Science
--------------------------------------------------------------------------------------------------------------------------------------------------

uv init uv python install 3.11 uv venv --python 3.11

uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy chromadb pytest pandas

uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy pandas pytest

--Create the initial project folders New-Item -ItemType Directory -Force -Path src, src/agents, src/workflow, src/schemas, src/database, src/services, app, data, tests

--Create empty init.py files: New-Item -ItemType File -Force -Path src/init.py, src/agents/init.py, src/workflow/init.py, src/schemas/init.py, src/database/init.py, src/services/init.py

--Create the database uv run python -m src.database.models

uv run python test_resolution_agent.py

uv run streamlit run app/main.py
