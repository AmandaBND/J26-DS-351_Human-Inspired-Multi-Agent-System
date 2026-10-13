import html

import json

import sys

from pathlib import Path

import pandas as pd

import streamlit as st

from sqlalchemy import func, select

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:

    sys.path.insert(0, str(PROJECT_ROOT))

from src.database.models import Complaint, SessionLocal, create_database  # noqa: E402

from src.services.review_service import submit_manager_review  # noqa: E402

from src.services.sla_service import get_sla_status  # noqa: E402

from src.services.escalation_service import (  # noqa: E402
    check_overdue_complaints,
    process_overdue_escalations,
)
from src.services.notification_service import (  # noqa: E402
    get_manager_notifications,
    count_unread_notifications,
    mark_notification_read,
)

from src.services.complaint_service import (  # noqa: E402

    get_complaint_by_id,

    process_new_complaint,

)

st.set_page_config(page_title="Metropolitan | Complaint Intelligence", page_icon="📋", layout="wide", initial_sidebar_state="expanded")

create_database()

PENDING = "Pending Human Review"

FAILED = "Analysis Failed"

PRIORITIES = ["High", "Medium", "Low", "Not analyzed"]

PRIORITY_COLORS = {

    "High": ("#b42318", "#fff0ee"),

    "Medium": ("#a65c00", "#fff5df"),

    "Low": ("#087443", "#eafaf1"),

    "Not analyzed": ("#596579", "#eef1f5"),

}

st.markdown("""

<style>

@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');

:root {--navy:#172641;--blue:#2563eb;--muted:#64748b;--line:#e4eaf2;--bg:#f7f9fc;}

html,body,[class*="css"],.stApp {font-family:'DM Sans',sans-serif;}

.stApp {background:var(--bg);color:var(--navy);}

.block-container {max-width:1250px;padding-top:2rem;padding-bottom:3rem;}

h1,h2,h3 {font-family:'Manrope',sans-serif;letter-spacing:-.035em;color:var(--navy);}

h1 {font-size:2rem!important;font-weight:800!important;}

h3 {font-weight:700!important;}

[data-testid="stSidebar"] {background:#14243e;}

[data-testid="stSidebar"] * {color:#e8eef8;}

[data-testid="stSidebar"] hr {border-color:#31425b;}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#adbed4!important;}

[data-testid="stSidebar"] [role="radiogroup"] label {padding:.65rem .7rem;border-radius:9px;}

[data-testid="stSidebar"] [role="radiogroup"] label:hover {background:#243958;}

.hero {padding:8px 0 19px;}

.eyebrow {color:#2563eb;font-size:.73rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin-bottom:7px;}

.hero-title {font-family:Manrope,sans-serif;font-weight:800;font-size:2rem;letter-spacing:-.04em;line-height:1.2;color:#172641;}

.hero-sub {color:#68768c;margin-top:8px;font-size:.95rem;}

.metric-card {background:#fff;border:1px solid var(--line);border-radius:15px;padding:18px 20px;min-height:118px;box-shadow:0 3px 12px rgba(22,38,65,.025);}

.metric-label {font-size:.83rem;color:#65748b;font-weight:600;}

.metric-value {font-family:Manrope,sans-serif;font-size:2rem;font-weight:800;color:#172641;margin-top:12px;line-height:1.1;}

.metric-foot {font-size:.73rem;color:#8a96a7;margin-top:5px;}

.section-title {font-family:Manrope,sans-serif;font-size:1.13rem;font-weight:800;color:#172641;margin:12px 0 6px;}

.section-sub {color:#78869b;font-size:.86rem;margin-bottom:15px;}

.case-card {background:#fff;border:1px solid var(--line);border-radius:12px;padding:15px 17px;margin-bottom:9px;display:flex;gap:15px;align-items:center;justify-content:space-between;flex-wrap:wrap;}

.case-name {font-weight:700;color:#172641;font-size:.94rem;}

.case-meta {color:#7a8798;font-size:.8rem;margin-top:5px;}

.pill {display:inline-block;border-radius:20px;padding:4px 10px;font-weight:700;font-size:.74rem;white-space:nowrap;}

.detail-box {background:#fff;border:1px solid var(--line);border-radius:13px;padding:19px 21px;margin:9px 0 15px;}

.detail-label {font-size:.76rem;text-transform:uppercase;letter-spacing:.07em;color:#8792a3;font-weight:800;margin-bottom:10px;}

.detail-body {font-size:.95rem;color:#253651;line-height:1.75;white-space:pre-wrap;overflow-wrap:anywhere;}

.result-row {display:flex;gap:8px;flex-wrap:wrap;margin:9px 0 16px;}

.notice {padding:13px 16px;border-radius:11px;background:#edf4ff;border:1px solid #d6e6ff;color:#24529c;font-size:.88rem;margin:12px 0;}

div[data-testid="stForm"] {background:#fff;border:1px solid var(--line);border-radius:15px;padding:22px;}

div[data-testid="stFormSubmitButton"] button {background:#2563eb;border-color:#2563eb;color:white;border-radius:9px;font-weight:700;}

.stButton button {border-radius:9px;}

[data-testid="stTabs"] button {font-weight:700;}

[data-testid="stMetric"] {background:white;border:1px solid var(--line);border-radius:12px;padding:14px;}

@media(max-width:700px){.block-container{padding:1.2rem}.hero-title{font-size:1.65rem}.case-card{align-items:flex-start}.metric-card{min-height:100px;padding:13px}}

/* Manager review styling */

.review-heading {font-family:Manrope,sans-serif;font-size:1.15rem;font-weight:800;color:#172641;margin:22px 0 6px;}

.review-description {font-size:.9rem;color:#52647e;margin-bottom:15px;}

.review-status {border:1px solid #e2e8f0;border-radius:12px;background:#fff;padding:17px 20px;margin:14px 0;}

.review-status .review-label {font-size:.76rem;letter-spacing:.08em;text-transform:uppercase;font-weight:800;color:#64748b;margin-bottom:8px;}

.review-status .review-value {font-weight:800;font-size:1rem;}

.review-pending {color:#975700!important;}

.review-approved {color:#087443!important;}

.review-rejected {color:#b42318!important;}

.review-record {background:#fff;border:1px solid #e4eaf2;border-radius:12px;padding:18px 20px;margin:12px 0;}

.review-record-label {font-size:.76rem;font-weight:800;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px;}

.review-record-value {font-size:.94rem;color:#172641;white-space:pre-wrap;overflow-wrap:anywhere;}

div[data-testid="stForm"] label p {color:#263954!important;font-weight:650;}

div[data-testid="stForm"] input, div[data-testid="stForm"] textarea {color:#172641!important;background:#fff!important;border-color:#cbd5e1!important;}

div[data-testid="stForm"] input::placeholder, div[data-testid="stForm"] textarea::placeholder {color:#8090a5!important;}

/* Accessible font colors: light content, dark sidebar */

.stApp, .stApp p, .stApp li, .stApp label,

.stApp [data-testid="stMarkdownContainer"] { color: #172641; }

.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #14243e; }

.stApp [data-testid="stCaptionContainer"],

.stApp .stCaption, .stApp small { color: #52627a; }

.stApp [data-testid="stWidgetLabel"] p { color: #243650; font-weight: 600; }

.stApp [data-testid="stMetricLabel"] p { color: #475569; }

.stApp [data-testid="stMetricValue"] { color: #14243e; }

.stApp input, .stApp textarea { color: #172641 !important; }

.stApp input::placeholder, .stApp textarea::placeholder { color: #64748b !important; }

.stApp [data-baseweb="select"] * { color: #172641; }

.stApp [data-testid="stTabs"] button { color: #475569; }

.stApp [data-testid="stTabs"] button[aria-selected="true"] { color: #1d4ed8; }

.stApp [data-testid="stSidebar"] { color: #f1f5f9; }

.stApp [data-testid="stSidebar"] p,

.stApp [data-testid="stSidebar"] label,

.stApp [data-testid="stSidebar"] h1,

.stApp [data-testid="stSidebar"] h2,

.stApp [data-testid="stSidebar"] h3,

.stApp [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #f1f5f9; }

.stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #cbd5e1 !important; }

.stApp [data-testid="stSidebar"] [role="radiogroup"] label p { color: #f1f5f9; }

.stApp [data-testid="stAlert"] p { color: inherit; }

</style>

""", unsafe_allow_html=True)

def safe(value):

    return html.escape(str(value)) if value is not None and value != "" else ""

def pill(value, priority=False):

    value = str(value or "Not analyzed")

    fg, bg = PRIORITY_COLORS.get(value, ("#51627a", "#edf2f8")) if priority else ("#51627a", "#edf2f8")

    return f'<span class="pill" style="color:{fg};background:{bg}">{safe(value)}</span>'

def header(title, subtitle):

    st.markdown(f'<div class="hero"><div class="eyebrow">Metropolitan · Service Intelligence</div><div class="hero-title">{safe(title)}</div><div class="hero-sub">{safe(subtitle)}</div></div>', unsafe_allow_html=True)

def detail(label, body):

    st.markdown(f'<div class="detail-box"><div class="detail-label">{safe(label)}</div><div class="detail-body">{safe(body) or "Not available"}</div></div>', unsafe_allow_html=True)

def date_text(value):

    try:

        return pd.to_datetime(value).strftime("%d %b %Y · %I:%M %p") if value is not None else ""

    except (ValueError, TypeError):

        return ""

def fetch_complaints():

    with SessionLocal() as db:

        items = db.execute(select(Complaint).order_by(Complaint.created_at.desc(), Complaint.id.desc())).scalars().all()

        return [{col.name: getattr(item, col.name) for col in Complaint.__table__.columns} for item in items]

def stats():

    with SessionLocal() as db:

        total = db.scalar(select(func.count(Complaint.id))) or 0

        high = db.scalar(select(func.count(Complaint.id)).where(Complaint.priority == "High")) or 0

        pending = db.scalar(select(func.count(Complaint.id)).where(Complaint.status == PENDING)) or 0

        failed = db.scalar(select(func.count(Complaint.id)).where(Complaint.status == FAILED)) or 0

    return total, high, pending, failed

def metric_card(label, value, foot):

    st.markdown(f'<div class="metric-card"><div class="metric-label">{safe(label)}</div><div class="metric-value">{value}</div><div class="metric-foot">{safe(foot)}</div></div>', unsafe_allow_html=True)

def priority_rank(c):

    priority = c.get("priority") or "Not analyzed"

    return PRIORITIES.index(priority) if priority in PRIORITIES else 3

with st.sidebar:

    st.markdown("### ◈ Metropolitan")

    st.caption("CUSTOMER SERVICE · AI WORKSPACE")

    st.divider()

    page = st.radio("Navigation", ["Dashboard", "Submit complaint", "Review complaints", "Notifications"], label_visibility="collapsed")

    st.divider()

    st.caption("Four specialized AI agents support complaint analysis and resolution.")

    st.caption("All proposed replies require human review.")

if page == "Dashboard":

    header("Complaint overview", "Monitor incoming cases, AI priorities, and complaints requiring attention.")

    values = stats()

    for col, label, value, foot in zip(st.columns(4), ["Total complaints", "High priority", "Awaiting review", "Analysis failed"], values, ["All recorded cases", "Urgent attention", "Human decision needed", "Requires investigation"]):

        with col:

            metric_card(label, value, foot)

    st.write("")

    cases = fetch_complaints()

    st.markdown('<div class="section-title">Priority queue</div><div class="section-sub">Most urgent cases first. Open Review complaints to inspect a case.</div>', unsafe_allow_html=True)

    if not cases:

        st.info("No complaints yet. Submit a complaint to start analyzing cases.")

    else:

        for c in sorted(cases, key=lambda x: (priority_rank(x), -int(x["id"])))[:8]:

            st.markdown(f'<div class="case-card"><div><div class="case-name">#{safe(c["id"])} · {safe(c.get("customer_name") or "Unknown customer")}</div><div class="case-meta">{safe(c.get("product"))} · {safe(date_text(c.get("created_at")))}</div></div><div class="result-row">{pill(c.get("category"))}{pill(c.get("priority"), True)}{pill(c.get("status"))}</div></div>', unsafe_allow_html=True)

        st.write("")

        left, right = st.columns(2)

        df = pd.DataFrame(cases)

        with left:

            st.markdown('<div class="section-title">Complaints by priority</div>', unsafe_allow_html=True)

            counts = df["priority"].fillna("Not analyzed").value_counts().reindex(PRIORITIES, fill_value=0)

            st.bar_chart(counts, color="#2563eb", horizontal=True)

        with right:

            st.markdown('<div class="section-title">Complaints by category</div>', unsafe_allow_html=True)

            counts = df["category"].fillna("Not analyzed").value_counts()

            st.bar_chart(counts, color="#2563eb", horizontal=True)

    st.divider()

    st.subheader("SLA Monitoring")

    try:

        overdue_complaints = check_overdue_complaints()

        st.metric("Overdue Complaints", len(overdue_complaints))

        if overdue_complaints:

            st.error(

                f"{len(overdue_complaints)} complaint(s) "

                "have exceeded their proposed SLA deadline."

            )

            st.dataframe(

                pd.DataFrame(overdue_complaints),

                use_container_width=True,

                hide_index=True,

            )

        else:

            st.success("No overdue complaints with configured SLA deadlines.")

    except Exception as error:

        st.error("SLA monitoring could not be loaded.")

        with st.expander("Technical details"):

            st.exception(error)

    st.divider()
    st.subheader("Escalation Monitoring")
    try:
        new_escalations = process_overdue_escalations()
        unread_count = count_unread_notifications()
        left, right = st.columns(2)
        with left:
            st.metric("Overdue Complaints", len(check_overdue_complaints()))
        with right:
            st.metric("Unread Manager Notifications", unread_count)
        if new_escalations:
            st.warning(f"{len(new_escalations)} new SLA escalation(s) created.")
        if unread_count > 0:
            st.warning("Manager notifications require attention. Open the Notifications page.")
    except Exception as error:
        st.error("Escalation monitoring could not be loaded.")
        with st.expander("Technical details"):
            st.exception(error)


elif page == "Submit complaint":

    header("New complaint", "Register a customer issue and run the four-agent analysis workflow.")

    with st.form("complaint_form", clear_on_submit=False):

        st.markdown("#### Customer information")

        c1, c2 = st.columns(2)

        with c1:

            customer_name = st.text_input("Customer name *", placeholder="e.g. Nimal Perera")

        with c2:

            product = st.text_input("Product / equipment *", placeholder="e.g. Canon imageRUNNER ADVANCE")

        st.markdown("#### Complaint details")

        complaint_text = st.text_area("Customer complaint *", height=220, placeholder="Paste the customer's complaint, including service history, impact and requested resolution...")

        st.caption("* Required fields · The AI recommendation is not sent automatically.")

        submitted = st.form_submit_button("✦ Analyze complaint", type="primary", use_container_width=True)

    if submitted:

        if not all((customer_name.strip(), product.strip(), complaint_text.strip())):

            st.warning("Please complete all required fields before analyzing.")

        else:

            try:

                with st.spinner("Running complaint analysis, emotion detection, priority assessment and resolution recommendation..."):

                    result = process_new_complaint(customer_name=customer_name.strip(), product=product.strip(), complaint_text=complaint_text.strip())

                st.session_state["last_complaint_id"] = result["complaint_id"]

                analysis = result["results"]["complaint_analysis"]

                emotion = result["results"]["emotion_analysis"]

                priority = result["results"]["priority_analysis"]

                resolution = result["results"]["resolution_analysis"]

                st.success(f"Complaint #{result['complaint_id']} successfully saved and analyzed.")

                st.markdown('<div class="section-title">AI analysis summary</div>', unsafe_allow_html=True)

                st.markdown(f'<div class="result-row">{pill(analysis.get("category"))}{pill(emotion.get("primary_emotion"))}{pill(priority.get("priority"), True)}</div>', unsafe_allow_html=True)

                detail("Recommended resolution", resolution.get("recommended_action"))

                st.markdown('<div class="notice">This is an AI recommendation. No reply has been sent. Review the full analysis before taking action.</div>', unsafe_allow_html=True)

            except Exception as error:

                st.error("The complaint could not be processed. Check your API configuration, agent workflow, and database connection.")

                with st.expander("Technical details"):

                    st.exception(error)

elif page == "Review complaints":

    header("Review complaints", "Find a case, inspect agent decisions, and review the proposed customer response.")

    cases = fetch_complaints()

    if not cases:

        st.info("No complaints to review yet.")

    else:

        search_col, priority_col, status_col = st.columns([2, 1, 1])

        with search_col:

            search = st.text_input("Search complaints", placeholder="Customer, equipment, complaint ID or text")

        with priority_col:

            selected_priorities = st.multiselect("Priority", PRIORITIES, placeholder="All priorities")

        with status_col:

            selected_statuses = st.multiselect("Status", sorted({str(c.get("status")) for c in cases if c.get("status")}), placeholder="All statuses")

        needle = search.strip().lower()

        filtered = [c for c in cases if (not needle or any(needle in str(c.get(k) or "").lower() for k in ("id", "customer_name", "product", "complaint_text", "category"))) and (not selected_priorities or (c.get("priority") or "Not analyzed") in selected_priorities) and (not selected_statuses or c.get("status") in selected_statuses)]

        st.caption(f"Showing {len(filtered)} of {len(cases)} complaints")

        if not filtered:

            st.info("No complaints match your filters.")

        else:

            by_id = {c["id"]: c for c in filtered}

            ids = list(by_id)

            last_id = st.session_state.get("last_complaint_id")

            selected_id = st.selectbox("Select complaint", ids, index=ids.index(last_id) if last_id in ids else 0, format_func=lambda cid: f"#{cid} · {by_id[cid].get('customer_name') or 'Unknown'} · {by_id[cid].get('priority') or 'Not analyzed'}")

            complaint = get_complaint_by_id(selected_id)

            if complaint:

                st.markdown(f'<div class="section-title">Complaint #{safe(complaint.get("id"))}</div><div class="result-row">{pill(complaint.get("priority"), True)}{pill(complaint.get("category"))}{pill(complaint.get("emotion"))}{pill(complaint.get("status"))}</div>', unsafe_allow_html=True)

                st.markdown("### SLA Information")

                sla_status = get_sla_status(

                    due_at=complaint.get("sla_due_at"),

                    completed_at=complaint.get("sla_completed_at"),

                )

                c1, c2 = st.columns(2)

                c1.metric(

                    "Proposed SLA",

                    (

                        f"{complaint['proposed_sla_hours']} hours"

                        if complaint.get("proposed_sla_hours") is not None

                        else "N/A"

                    ),

                )

                c2.metric("SLA Status", sla_status)

                if complaint.get("sla_due_at"):

                    st.write("**Deadline (UTC):**", complaint["sla_due_at"])

                if sla_status == "Overdue":

                    st.error(

                        "This complaint is overdue. "

                        "Escalation is recommended."

                    )

                tab1, tab2, tab3 = st.tabs(["Complaint details", "Resolution plan", "Customer reply"])

                with tab1:

                    a, b = st.columns(2)

                    with a:

                        detail("Customer", complaint.get("customer_name"))

                    with b:

                        detail("Product / equipment", complaint.get("product"))

                    detail("Original complaint", complaint.get("complaint_text"))

                    detail("Business impact", complaint.get("business_impact"))

                with tab2:

                    detail("AI-recommended resolution", complaint.get("recommended_resolution"))

                    raw_details = complaint.get("resolution_details")

                    details = {}

                    if isinstance(raw_details, dict):

                        details = raw_details

                    elif raw_details:

                        try:

                            details = json.loads(raw_details)

                        except (json.JSONDecodeError, TypeError):

                            st.warning("Resolution details are not valid JSON.")

                    if isinstance(details, dict) and details:

                        steps = details.get("action_steps") or []

                        if isinstance(steps, list) and steps:

                            st.markdown("#### Recommended action steps")

                            for idx, step in enumerate(steps, 1):

                                st.write(f"{idx}. {step}")

                        a, b = st.columns(2)

                        with a:

                            detail("Responsible team", details.get("responsible_team", "Not specified"))

                        with b:

                            detail("Escalation", "Manager escalation recommended" if details.get("escalation_required") else "No escalation indicated")

                with tab3:

                    st.markdown('<div class="notice">Draft only. No message has been sent to the customer.</div>', unsafe_allow_html=True)

                    st.text_area("AI-generated response", value=complaint.get("customer_response") or "", height=260, disabled=True)

                    st.caption("Manager approval and rejection are available below the tabs.")

                if st.session_state.get("review_notice"):

                    st.success(st.session_state.pop("review_notice"))

                # ==================================================

                # MANAGER APPROVAL / REJECTION

                # ==================================================

                status = complaint.get("status") or "Unknown"

                status_class = (

                    "review-approved" if status == "Resolution Approved"

                    else "review-rejected" if status == "Resolution Rejected"

                    else "review-pending" if status == PENDING

                    else ""

                )

                st.markdown(

                    '<div class="review-status">'

                    '<div class="review-label">Review status</div>'

                    f'<div class="review-value {status_class}">{safe(status)}</div>'

                    '</div>',

                    unsafe_allow_html=True,

                )

                if status == PENDING:

                    st.markdown('<div class="review-heading">Manager decision</div>', unsafe_allow_html=True)

                    st.markdown(

                        '<div class="review-description">Check the AI recommendation and draft customer '

                        'response above before recording a decision.</div>',

                        unsafe_allow_html=True,

                    )

                    with st.form(f"manager_review_{selected_id}"):

                        reviewer_name = st.text_input(

                            "Reviewer name *", placeholder="Enter manager name"

                        )

                        review_comments = st.text_area(

                            "Review comments",

                            placeholder="Approval notes or reason for rejection...",

                            height=110,

                        )

                        decision = st.radio(

                            "Decision", ["Approve", "Reject"], horizontal=True

                        )

                        confirm = st.checkbox(

                            "I have reviewed the AI recommendation and confirm this decision."

                        )

                        submitted_review = st.form_submit_button(

                            "Submit manager decision", type="primary",

                            use_container_width=True,

                        )

                    if submitted_review:

                        if not reviewer_name.strip():

                            st.warning("Please enter the reviewer name.")

                        elif decision == "Reject" and not review_comments.strip():

                            st.warning("Please provide a reason for rejection.")

                        elif not confirm:

                            st.warning("Please confirm your decision.")

                        else:

                            try:

                                result = submit_manager_review(

                                    complaint_id=selected_id,

                                    reviewer_name=reviewer_name.strip(),

                                    decision=decision,

                                    comments=review_comments.strip(),

                                )

                                st.session_state["review_notice"] = (

                                    f"Complaint #{selected_id}: {result['status']}"

                                )

                                st.rerun()

                            except ValueError as error:

                                st.error(str(error))

                            except Exception:

                                st.error("Could not save the review. Check the application logs.")

                                raise

                elif status in ("Resolution Approved", "Resolution Rejected"):

                    st.markdown('<div class="review-heading">Manager review record</div>', unsafe_allow_html=True)

                    for label, value in (

                        ("Reviewed by", complaint.get("reviewed_by") or "N/A"),

                        ("Decision", status),

                        ("Comments", complaint.get("review_comments") or "None"),

                        ("Reviewed at (UTC)", str(complaint.get("reviewed_at") or "N/A")),

                    ):

                        st.markdown(

                            '<div class="review-record">'

                            f'<div class="review-record-label">{safe(label)}</div>'

                            f'<div class="review-record-value">{safe(value)}</div>'

                            '</div>', unsafe_allow_html=True,

                        )

                    st.info("Decision recorded. No customer message has been sent.")


# ============================================================
# MANAGER NOTIFICATION CENTER
# ============================================================

elif page == "Notifications":
    header("Manager notification center", "SLA escalation alerts and manager notifications.")

    try:
        new_escalations = process_overdue_escalations()
        if new_escalations:
            st.warning(f"{len(new_escalations)} new SLA escalation(s) created.")

        unread_count = count_unread_notifications()
        st.metric("Unread Notifications", unread_count)

        if st.button("Refresh notifications", use_container_width=False):
            st.rerun()

        unread_only = st.checkbox("Show unread notifications only", value=False)
        notifications = get_manager_notifications(unread_only=unread_only)

        if not notifications:
            st.info("No notifications found.")
        else:
            for notification in notifications:
                notification_id = notification["id"]
                complaint_id = notification["complaint_id"]

                with st.container(border=True):
                    left, right = st.columns([4, 1])
                    with left:
                        st.markdown(f"#### {safe(notification['title'])}")
                    with right:
                        st.caption("Read" if notification["is_read"] else "Unread")

                    st.write(notification["message"])
                    st.caption(f"Complaint ID: {complaint_id}")
                    st.caption(f"Recipient role: {notification['recipient_role']}")
                    st.caption(f"Created (UTC): {notification['created_at']}")

                    if not notification["is_read"]:
                        if st.button("Mark as Read", key=f"read_{notification_id}"):
                            updated = mark_notification_read(notification_id)
                            if updated:
                                st.rerun()
                            else:
                                st.info("Notification was already read.")
    except Exception as error:
        st.error("Notifications could not be loaded.")
        with st.expander("Technical details"):
            st.exception(error)
