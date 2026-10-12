
# AI-Powered Customer Complaint Management Multi-Agent System

### Intelligent After-Sales Complaint Analysis, Prioritization and Resolution

An AI-powered multi-agent customer complaint management system designed for the after-sales service operations of **Metropolitan Technologies (Pvt) Ltd, Sri Lanka**.

The system uses specialized AI agents to analyze customer complaints, identify customer emotions, determine complaint priority and recommend suitable resolutions. It integrates human-in-the-loop decision-making, SLA monitoring, escalation management and a Streamlit dashboard.

> **Project Status:** Active Development  
> **Project Type:** Final Year Research Project  
> **Domain:** Artificial Intelligence | Multi-Agent Systems | Customer Service Automation

---

## 1. Project Overview

Traditional customer complaint management often involves manual complaint analysis, inconsistent prioritization, delayed responses and limited visibility into service performance.

This project introduces an intelligent multi-agent approach to improve the efficiency, consistency and transparency of after-sales complaint handling.

Instead of relying on a single AI model to perform all tasks, the system uses four specialized AI agents, each responsible for a specific stage of complaint processing.

The system supports human oversight by requiring managerial review of AI-generated recommendations before final decisions are made.

### Main Objectives

- Automate customer complaint analysis.
- Identify customer emotions and dissatisfaction.
- Determine complaint urgency and business impact.
- Generate context-aware resolution recommendations.
- Support human-in-the-loop approval and rejection.
- Monitor complaint resolution deadlines.
- Identify overdue complaints for escalation.
- Provide a centralized complaint management dashboard.

---

## 2. Multi-Agent Architecture

The complaint management system consists of four specialized AI agents.

### Agent 1: Complaint Analysis Agent

Analyzes the customer's complaint and extracts relevant information.

**Responsibilities:**
- Identify the main complaint.
- Classify the complaint category.
- Identify affected products or services.
- Extract important complaint details.
- Produce structured complaint analysis.

### Agent 2: Customer Emotion Analysis Agent

Analyzes the emotional context of customer complaints.

**Responsibilities:**
- Identify customer sentiment.
- Detect frustration, dissatisfaction or anger.
- Evaluate emotional intensity.
- Provide emotional context for prioritization.

### Agent 3: Complaint Priority & Business Impact Agent

Determines complaint urgency based on the available information.

**Responsibilities:**
- Evaluate complaint severity.
- Consider customer emotion and business impact.
- Assign High, Medium or Low priority.
- Support SLA deadline assignment.

### Agent 4: Resolution Recommendation Agent

Generates appropriate resolution suggestions.

**Responsibilities:**
- Recommend suitable corrective actions.
- Consider complaint category and urgency.
- Generate explanations for recommendations.
- Support manager decision-making.

---

## 3. System Architecture

```text
             Customer Complaint
                     |
                     v
            Streamlit Interface
                     |
                     v
            Complaint Processing
                     |
                     v
       +---------------------------+
       |  Agent 1                  |
       |  Complaint Analysis       |
       +---------------------------+
                     |
                     v
       +---------------------------+
       |  Agent 2                  |
       |  Emotion Analysis         |
       +---------------------------+
                     |
                     v
       +---------------------------+
       |  Agent 3                  |
       |  Priority & Impact        |
       +---------------------------+
                     |
                     v
       +---------------------------+
       |  Agent 4                  |
       |  Resolution Recommendation|
       +---------------------------+
                     |
                     v
              SQLite Database
                     |
                     v
             Manager Review
                /       \
           Approve      Reject
                \       /
                     |
                     v
             Status Tracking
                     |
                     v
             SLA Monitoring
                     |
                     v
           Escalation Detection
                     |
                     v
            Streamlit Dashboard
```

---

## 4. Key Features

### AI-Based Complaint Processing

- Multi-agent complaint analysis.
- Automated complaint classification.
- Customer emotion identification.
- AI-assisted priority determination.
- Intelligent resolution recommendations.

### Complaint Management

- Submit new complaints.
- Store complaint records in SQLite.
- Review complaint details.
- Track complaint processing status.
- View AI-generated analysis.

### Human-in-the-Loop Review

- Manager approval interface.
- Approve or reject AI recommendations.
- Record reviewer information.
- Save manager review comments.
- Track review decisions.

### SLA Monitoring

- Assign proposed SLA deadlines based on priority.
- Track complaint deadlines.
- Identify overdue complaints.
- Display SLA information during complaint review.
- Monitor overdue complaint counts.

### Escalation Monitoring

- Detect complaints exceeding configured SLA deadlines.
- Identify complaints requiring management attention.
- Display overdue complaints in the dashboard.

### Dashboard

- Centralized complaint monitoring.
- Complaint status visibility.
- SLA monitoring information.
- Overdue complaint reporting.
- Interactive Streamlit interface.

---

## 5. Technology Stack

| Technology | Purpose |
|------------|---------|
| Python | Core application development |
| OpenAI API | AI-powered complaint analysis |
| LangChain / LangGraph | AI agent orchestration |
| Streamlit | Web application interface |
| SQLite | Local complaint database |
| SQLAlchemy | Database ORM |
| Pandas | Data processing and display |
| python-dotenv | Environment configuration |
| uv | Python dependency management |
| Git & GitHub | Version control |

---

## 6. Project Structure

The project follows a modular architecture.

```text
CustomerComplaintMetro/
|
|-- app/
|   |-- main.py
|
|-- src/
|   |-- agents/
|   |   |-- Complaint analysis agents
|   |   |-- Emotion analysis agents
|   |   |-- Priority analysis agents
|   |   |-- Resolution recommendation agents
|   |
|   |-- services/
|   |   |-- review_service.py
|   |   |-- sla_service.py
|   |   |-- escalation_service.py
|   |
|   |-- database/
|   |-- workflows/
|
|-- data/
|   |-- complaints.db
|
|-- .env
|-- .gitignore
|-- pyproject.toml
|-- uv.lock
|-- README.md
```

> Note: This structure is illustrative. Some folders and filenames may differ from the current implementation.

---

## 7. Installation and Setup

### Prerequisites

- Python 3.11 or later (compatible version)
- Git
- uv package manager
- OpenAI API key

### Step 1: Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd CustomerComplaintMetro
```

### Step 2: Install Dependencies

```bash
uv sync
```

This installs the dependencies defined in the project configuration.

### Step 3: Configure Environment Variables

Create a `.env` file in the project root.

```env
OPENAI_API_KEY=your_openai_api_key_here
```

Never commit the `.env` file to GitHub.

### Step 4: Run the Application

```bash
uv run streamlit run app/main.py
```

### Step 5: Open the Dashboard

Open the local URL displayed in the terminal.

```text
http://localhost:8501
```

---

## 8. Complaint Processing Workflow

**Step 1: Complaint Submission**

A user submits a customer complaint through the Streamlit interface.

**Step 2: Complaint Analysis**

Agent 1 identifies the complaint category and extracts relevant information.

**Step 3: Emotion Analysis**

Agent 2 identifies customer emotions and dissatisfaction.

**Step 4: Priority Evaluation**

Agent 3 evaluates complaint urgency and business impact.

**Step 5: Resolution Recommendation**

Agent 4 generates a recommended resolution.

**Step 6: Complaint Storage**

Complaint details and AI-generated outputs are stored in the database.

**Step 7: Manager Review**

A manager reviews the recommendation and approves or rejects it.

**Step 8: SLA Monitoring**

The application evaluates complaint deadlines and detects overdue complaints.

**Step 9: Escalation**

Overdue complaints are identified for further management attention.

---

## 9. SLA Management

The system uses configurable, priority-based SLA deadlines.

Example proposed SLA configuration:

| Priority | Proposed SLA |
|----------|--------------|
| High | 24 Hours |
| Medium | 48 Hours |
| Low | 72 Hours |

These values are illustrative and should be validated against the organization's actual service agreements.

SLA monitoring supports:

- Deadline calculation.
- Overdue complaint detection.
- Completion tracking.
- Dashboard reporting.
- Escalation identification.

---

## 10. Example Complaint

**Customer Complaint:**

"My office printer has stopped working again even though the technician repaired it two days ago. We urgently need the printer for daily business operations. I am extremely disappointed with the repeated failures."

### Expected AI Processing

| Agent | Example Output |
|-------|----------------|
| Complaint Analysis | Repeated printer malfunction |
| Emotion Analysis | Frustration / Dissatisfaction |
| Priority Agent | High Priority |
| Resolution Agent | Urgent technical inspection and escalation |

The outputs shown are examples. Actual results depend on the AI model and complaint context.

---

## 11. Human-in-the-Loop Decision Making

AI-generated recommendations are treated as decision-support information rather than automatic final decisions.

The manager can:

1. Review the original complaint.
2. Examine the AI-generated analysis.
3. Review the proposed resolution.
4. Approve or reject the recommendation.
5. Add comments and justification.

This improves accountability, transparency and human oversight.

---

## 12. Current Development Status

| Module | Status |
|--------|--------|
| Complaint Analysis Agent | Implemented |
| Emotion Analysis Agent | Implemented |
| Priority & Impact Agent | Implemented |
| Resolution Recommendation Agent | Implemented |
| SQLite Complaint Storage | Implemented |
| Streamlit Dashboard | Implemented |
| Manager Approval / Rejection | Implemented |
| SLA Monitoring | Implemented |
| Overdue Complaint Detection | Implemented |
| External Notification Integration | Planned / In Progress |
| Customer Satisfaction Collection | Planned |
| Advanced Analytics | Planned |

---

## 13. Future Enhancements

Planned improvements include:

- Automated email notifications.
- Microsoft Teams notification integration.
- Power Automate workflow integration.
- SharePoint integration.
- Automated escalation notifications.
- Customer satisfaction feedback collection.
- Complaint trend analysis.
- Advanced reporting and analytics.
- Role-based access control.
- Deployment and production security improvements.

---

## 14. Security and Privacy

The project should follow secure application development practices.

- Store API keys in environment variables.
- Exclude sensitive files from version control.
- Avoid publishing real customer complaint data.
- Validate application inputs.
- Restrict access to complaint records.
- Maintain human oversight for important decisions.
- Implement authentication before production deployment.

### Recommended .gitignore Entries

```gitignore
.env
.env.*
!.env.example
.venv/
__pycache__/
*.pyc
.streamlit/secrets.toml
data/*.db
data/*.sqlite
data/*.sqlite3
```

---

## 15. Research Context

This project forms part of an undergraduate final year research initiative focused on intelligent multi-agent systems for business decision support.

**Institution:** Sri Lanka Institute of Information Technology (SLIIT)

**Degree:** BSc (Hons) in Information Technology, Specializing in Data Science

**Industry Context:** Metropolitan Technologies (Pvt) Ltd, Sri Lanka

**Research Component:** AI-Powered Customer Complaint Management Agent

The component explores how specialized AI agents, human oversight and operational monitoring can support more effective after-sales complaint management.

---

## 16. Disclaimer

This system is a research and development prototype.

AI-generated analysis, priority assignments and resolution recommendations may contain inaccuracies and should be reviewed by authorized personnel.

The system is not intended for unsupervised production use without additional validation, security controls and organizational approval.

---

## 17. Author

**Chamidu Gunathunga**

BSc (Hons) Information Technology  
Specializing in Data Science  
Sri Lanka Institute of Information Technology (SLIIT)

---

## 18. License

This project is developed for academic research purposes.

Usage, distribution and commercialization are subject to applicable institutional and organizational permissions.
