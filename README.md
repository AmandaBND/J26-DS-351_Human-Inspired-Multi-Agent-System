Make your own branch and own component folders till pp1

**Branches**
Amanda(IT23280274) - feature/security-self-attestation
Chamidu(IT23257044) - feature/[Component name]
Chithira(IT23366268) - feature/[Component name]
Hasandi(IT23359406) - feature/[Component name]

**Folders**
Develop individual components inside components/[Your component name]

Amanda(IT23280274) - components/security
Chamidu(IT23257044) - components/Complaint
Chithira(IT23366268) - components/Employee_Efficiency
Hasandi(IT23359406) - components/After_Sales_Service




uv init uv python install 3.11 uv venv --python 3.11

uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy chromadb pytest pandas

uv add langgraph langchain langchain-openai python-dotenv pydantic streamlit sqlalchemy pandas pytest

--Create the initial project folders New-Item -ItemType Directory -Force -Path src, src/agents, src/workflow, src/schemas, src/database, src/services, app, data, tests

--Create empty init.py files: New-Item -ItemType File -Force -Path src/init.py, src/agents/init.py, src/workflow/init.py, src/schemas/init.py, src/database/init.py, src/services/init.py

--Create the database uv run python -m src.database.models

uv run python test_resolution_agent.py

uv run streamlit run app/main.py
