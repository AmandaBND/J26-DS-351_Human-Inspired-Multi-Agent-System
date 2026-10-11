uv init
uv python install 3.11
uv venv --python 3.11

uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy chromadb pytest pandas


uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy pandas pytest

--Create the initial project folders
New-Item -ItemType Directory -Force -Path src, src/agents, src/workflow, src/schemas, src/database, src/services, app, data, tests

--Create empty __init__.py files:
New-Item -ItemType File -Force -Path src/__init__.py, src/agents/__init__.py, src/workflow/__init__.py, src/schemas/__init__.py, src/database/__init__.py, src/services/__init__.py


--Create the database
uv run python -m src.database.models