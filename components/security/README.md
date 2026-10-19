# Adaptive Self-Attesting Multi-Agent Security Framework

Individual security component of the group project:

**Hierarchical Human-Inspired Multi-Agent Decision Support Framework for Enterprise Technology Service Operations**

## Security Intelligence Workspace

The Streamlit workspace presents the security component as an operational service for Metropolitan. Incoming AI-agent requests are checked before protected data or tools are used.

The working security flow is:

```text
Incoming AI Agent Request
          ↓
Prompt Protection + Access Policy + Behavior Protection
          ↓
Monitor Reliability and Adaptive Trust
          ↓
Trust-Weighted Security Decision
          ↓
ALLOW / REVIEW / BLOCK
          ↓
Guarded SQLite Data / Tool Action
          ↓
Security Audit Log
```

The current workspace uses sample requests to represent the other enterprise agents until direct component integration is enabled. The security pipeline itself uses the implemented monitor, reliability, trust, fusion and audit modules in this repository.

### Main UI pages

- **Overview** — security activity and current protection health.
- **Inspect request** — submit an incoming agent request through the security pipeline.
- **Monitor health** — current monitor health, history and integrity verification.
- **Access activity** — security audit trail of processed requests and actions.
- **Data access** — local SQLite business data and agent access rules.

### Run

From the repository root:

```powershell
pip install -r requirements.txt
streamlit run app/security_dashboard.py
```

The local SQLite workspace is created automatically at:

```text
data/security_workspace.db
```

The database contains local sample business records used until the enterprise databases are connected. Sensitive example values are masked.

### Tests

```powershell
pytest -v
```
