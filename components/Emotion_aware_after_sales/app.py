"""Streamlit prototype: diarization, agent voice matching, and customer acoustics.
Transcription is intentionally disabled in this workflow.
"""
from __future__ import annotations
import sqlite3
from datetime import date
import hashlib
from html import escape
import tempfile
import time
from pathlib import Path
import pandas as pd
import streamlit as st
import torch
from pyannote.audio import Model, Pipeline
from emotion_aware_after_sales.services.audio_preprocessing_pipeline import AudioPreprocessingPipeline
from emotion_aware_after_sales.services.automatic_diarization_service import AutomaticDiarizationService
from emotion_aware_after_sales.services.automatic_role_identification_service import AutomaticRoleIdentificationService
from emotion_aware_after_sales.services.customer_audio_service import CustomerAudioService
from emotion_aware_after_sales.services.diarization_service import SpeakerTurn
from emotion_aware_after_sales.services.emotion_acoustic_features_service import EmotionAcousticFeaturesService
from emotion_aware_after_sales.services.temporal_acoustic_service import TemporalAcousticService
from emotion_aware_after_sales.services.temporal_acoustic_emotion_service import TemporalAcousticEmotionService
from emotion_aware_after_sales.services.conversation_role_identification_service import ConversationRoleIdentificationService
from emotion_aware_after_sales.services.amc_decision_service import AMCDecisionService
from emotion_aware_after_sales.services.egemaps_ser_service import EGeMAPSSERService
from emotion_aware_after_sales.agents.orchestrator import AMCMultiAgentOrchestrator

from emotion_aware_after_sales.services.voice_customer_service import VoiceCustomerService, reset_customer_context


st.set_page_config(page_title="AMC & Service Management", layout="wide")
st.markdown("""<style>
.stApp {background:#f6f7f9;color:#071B36}
[data-testid="stHeader"] {background:white}
.block-container {max-width:1510px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {color:#071B36;letter-spacing:-.025em}
h1 {font-size:2.2rem!important} h3 {font-size:1.15rem!important}
[data-testid="stVerticalBlockBorderWrapper"] {background:white;border-color:#d7dde5;border-radius:0!important}
.topbar {background:white;border-bottom:1px solid #d7dde5;padding:18px 24px;margin-bottom:28px;font-size:19px;font-weight:700}
.topbar span {float:right;font-size:13px;color:#64748b;font-weight:400}
/* Shared light resting state for dashboard, navigation, upload and action buttons. */
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button {
    background:#f1f4f8!important;color:#071B36!important;
    border:1px solid #cbd5e1!important;border-radius:0!important;font-weight:650;
    transition:background-color .15s ease,color .15s ease,border-color .15s ease;
}
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button * {
    color:inherit!important;
}
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button:hover:not(:disabled) {
    background:#e3e9f1!important;border-color:#94a3b8!important;
}
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button:is(:active,:focus):not(:disabled) {
    background:#071B36!important;color:#ffffff!important;border-color:#071B36!important;
}
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button:focus-visible {
    outline:2px solid #607d9e;outline-offset:3px;
}
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button:disabled {
    opacity:.5;cursor:not-allowed;
}
/* Stable container keys keep the prototype's square card outline visible. */
[class*="st-key-hub_card_"] {
    background:#ffffff!important;border:1px solid #d7dde5!important;
    border-radius:0!important;padding:24px!important;box-sizing:border-box;
    box-shadow:0 1px 3px rgba(11,32,57,.04);
}
.card-icon {background:#f5f6fa;padding:10px 15px;display:inline-block;margin-bottom:14px;font-size:22px}
.muted {color:#64748b;font-size:14px}

/* Shared AMC palette and accessible emphasis. */
h1,h2,h3 {color:#071B36;line-height:1.25!important}
.topbar {border-top:4px solid #C8102E;border-radius:12px;padding:20px 24px}
.hub-hero {background:#071B36;border-left:6px solid #C8102E;border-radius:16px;
    padding:30px 32px;margin:0 0 24px;color:#fff}
.hub-hero h1 {color:#fff!important;margin:8px 0 12px;font-size:2.25rem!important}
.hub-hero p {color:#e5e7eb;max-width:780px;line-height:1.65;margin:0}
.hub-eyebrow {color:#fff;font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
[class*="st-key-hub_card_"] {border-radius:14px!important;border-top:4px solid #071B36!important;
    padding:24px!important;min-height:300px;box-shadow:0 4px 16px rgba(7,27,54,.06)}
[class*="st-key-hub_card_"]:hover {border-top-color:#C8102E!important}
[class*="st-key-hub_card_"] h3 {min-height:3rem;font-size:1.15rem!important}
[class*="st-key-hub_card_"] [data-testid="stCaptionContainer"] {min-height:4.5rem;color:#475569}
.card-icon {background:#eef1f5;color:#071B36;border-radius:10px;padding:8px 14px;margin-bottom:8px}
:is(.stButton,.stDownloadButton,.stFormSubmitButton) button {border-radius:8px!important;min-height:44px}
[data-testid="stAlert"][data-baseweb="notification"] {border-radius:10px}
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) {background:#071B36!important;border:1px solid #071B36!important}
[data-testid="stAlertContentSuccess"], [data-testid="stAlertContentSuccess"] * {color:#fff!important}
[data-testid="stAlert"]:has([data-testid="stAlertContentSuccess"]) svg {fill:#fff!important;color:#fff!important}
.st-key-run_customer_call_analysis button,
.st-key-run_customer_call_analysis button:is(:hover,:active,:focus):not(:disabled) {
    background:#C8102E!important;border-color:#C8102E!important;color:#fff!important;
    min-height:54px;font-size:1.1rem;font-weight:750;box-shadow:0 4px 12px rgba(200,16,46,.2)}
.st-key-run_customer_call_analysis button:focus-visible {outline:3px solid #071B36;outline-offset:3px}
@media(max-width:640px) {.hub-hero {padding:22px}.topbar span {float:none;display:block;margin-top:8px}}

/* Customer voice workspace, inspired by the supplied reference. */
.voice-heading {display:flex;gap:20px;align-items:center;margin:8px 0 24px}
.voice-symbol {display:grid;place-items:center;background:#fbe8ed;color:#C8102E;
    border-radius:14px;width:76px;height:76px;font-size:34px;font-weight:800;flex-shrink:0}
.voice-heading h1 {margin:0 0 8px!important;font-size:2.2rem!important}
.voice-heading p {color:#526580;margin:0;line-height:1.6}
.voice-steps {display:grid;grid-template-columns:repeat(4,1fr);gap:20px;background:#fff;
    border:1px solid #dce3ed;border-radius:14px;padding:24px;margin:16px 0 24px}
.voice-step {display:flex;gap:12px;align-items:center;color:#071B36}
.step-number {background:#071B36;color:white;border-radius:50%;min-width:38px;height:38px;
    display:grid;place-items:center;font-weight:700}
.voice-step.done .step-number {background:#C8102E}
.voice-step small {display:block;color:#526580;margin-top:5px}
.voice-notice {background:#fff5dc;color:#714800;border:1px solid #edc76d;
    border-left:6px solid #a76a00;border-radius:12px;padding:18px 22px;margin:16px 0}
.voice-notice.ready {background:#071B36;color:white;border-color:#071B36}
.voice-notice strong {display:block;margin-bottom:5px}
[class*="st-key-voice_panel_"] {background:#fff!important;border:1px solid #dce3ed!important;
    border-radius:16px!important;padding:24px!important;margin:18px 0!important;
    box-shadow:0 4px 18px rgba(7,27,54,.035)}
[class*="st-key-voice_panel_"] h3 {font-size:1.3rem!important}
[class*="st-key-voice_panel_"] [data-testid="stVegaLiteChart"] {background:white;border-radius:12px}
.emotion-table-wrap {background:#fff;border:1px solid #dce3ed;border-radius:14px;overflow-x:auto;margin:16px 0}
.emotion-table {border-collapse:collapse;width:100%;font-size:14px;color:#314560}
.emotion-table th {color:#071B36;background:#f8fafc;text-align:left;font-weight:650;padding:16px}
.emotion-table td {padding:16px;border-top:1px solid #edf0f5;white-space:nowrap}
.emotion-table td:last-child {white-space:normal;min-width:180px;color:#526580}
.emotion-badge {display:inline-flex;align-items:center;gap:8px;border-radius:30px;padding:6px 12px;font-weight:650}
.emotion-badge:before {content:'';background:currentColor;width:8px;height:8px;border-radius:50%}
.emotion-angry {color:#b50929;background:#fde7ed}
.emotion-happy {color:#146c3c;background:#ddf5e7}
.emotion-sad {color:#9c4300;background:#fff0df}
.emotion-neutral {color:#785900;background:#fff5bf}
.emotion-other {color:#475569;background:#eef1f5}
.emotion-legend {display:flex;flex-wrap:wrap;gap:12px;margin:12px 0}
@media(max-width:800px) {.voice-steps {grid-template-columns:repeat(2,1fr)}
    .voice-heading h1 {font-size:1.7rem!important}.voice-symbol {width:54px;height:64px}}
@media(max-width:450px) {.voice-steps {grid-template-columns:1fr}}
/* Customer identification styles stay inside this panel. */
.st-key-voice_customer_identification {
    background:#071B36;border-top:3px solid #C8102E;
    border-radius:12px;padding:20px;
}
.st-key-voice_customer_identification [data-testid="stWidgetLabel"] p {
    color:#f1f5f9!important;font-weight:600;
}
.st-key-voice_customer_identification [data-baseweb="select"] > div,
.st-key-voice_customer_identification [data-baseweb="input"] {
    background:#102b4c!important;border-color:#64748b!important;
}
.st-key-voice_customer_identification [data-baseweb="select"] {color:#f1f5f9!important}
.st-key-voice_customer_identification [data-baseweb="select"] input {
    color:#f1f5f9!important;-webkit-text-fill-color:#f1f5f9!important;
}
.st-key-voice_customer_identification [data-baseweb="select"] svg {fill:#f1f5f9!important}
.st-key-voice_customer_identification input:disabled {
    color:#f1f5f9!important;-webkit-text-fill-color:#f1f5f9!important;
    opacity:1!important;background:#102b4c!important;
}
@media(max-width:640px) {
    .st-key-voice_customer_identification {padding:16px}
    .st-key-voice_customer_identification [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important}
    .st-key-voice_customer_identification [data-testid="stColumn"] {
        width:100%!important;flex:1 1 100%!important;min-width:0!important;
    }
}

/* Compact Metropolitan dashboard with explicit light widget surfaces. */
.block-container {padding-top:1.1rem!important;max-width:1510px}
.topbar {border-radius:0!important;padding:12px 18px!important;margin-bottom:14px!important;font-size:16px}
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] p {color:#071B36!important}
[data-baseweb="select"] > div, [data-baseweb="input"] > div {background:#fff!important;color:#071B36!important;border-color:#cbd5e1!important}
[data-baseweb="select"] span, [data-baseweb="select"] input {color:#071B36!important;-webkit-text-fill-color:#071B36!important}
[role="listbox"], [role="option"] {background:#fff!important;color:#071B36!important}
[data-testid="stRadio"] label {color:#071B36!important}
[data-testid="stCaptionContainer"] {color:#52657b!important}
[data-testid="stVerticalBlockBorderWrapper"] {border-radius:5px!important}
.data-note {font-size:11px;color:#64748b;letter-spacing:.035em;margin:0 0 16px}
.data-note b {color:#C8102E}
.revenue-kpi {background:#fff;border:1px solid #d7dde5;border-top:3px solid #071B36;padding:18px 14px;min-height:132px;margin-bottom:8px}
.revenue-kpi.attention {border-top-color:#C8102E}
.kpi-label {font-size:10px;letter-spacing:.065em;color:#52657b;min-height:27px}
.kpi-value {font-size:clamp(16px,1.6vw,26px);font-weight:750;color:#071B36;line-height:1.3;margin:5px 0 9px}
.attention .kpi-value {color:#C8102E}
.kpi-detail {font-size:10px;color:#64748b}
.renewal-ring {max-width:160px;margin:0 auto}
[data-testid="stProgress"] [role="progressbar"] > div {background:#071B36!important}
.st-key-amc_view {border-bottom:1px solid #d7dde5;padding-bottom:5px;margin-bottom:6px}
button[kind="primary"] {background:#071B36!important;color:#fff!important;border-color:#071B36!important}
@media(max-width:760px) {.revenue-kpi {min-height:110px}.kpi-value {font-size:23px}}

</style>""", unsafe_allow_html=True)

PAGES = ["AMC Revenue Dashboard", "Contract & Renewal Analysis", "Service & Operational Analysis", "Customer Feedback & Voice", "Payment & Business Analysis", "Final AMC Recommendation"]

def navigate(page):
    st.session_state["hub_page"] = page

def page_navigation(index):
    st.button(
        "←",
        on_click=navigate,
        args=("Hub",),
        key=f"home_top_{index}",
        help="Back to Management Hub",
    )

def render_hub():
    st.markdown(
        '<section class="hub-hero"><h1>AMC &amp; Service Management</h1></section>',
        unsafe_allow_html=True,
    )
    st.subheader("Explore your dashboards")
    st.caption("Start with customer records, explore service evidence, then review renewal recommendations.")
    descriptions = [
        "Review customer records, warranty coverage, and AMC contracts.",
        "View contract history and renewal dates across customers.",
        "Review device service history and unresolved service requests.",
        "Upload customer calls and review speaker roles and customer acoustic evidence.",
        "Review payment and business information when supported by verified records.",
        "Review explainable AMC recommendations based on customer and service records."]
    for row in range(2):
        columns = st.columns(3, gap="medium")
        for column, index in zip(columns, range(row*3, row*3+3)):
            with column, st.container(border=False, height=340, key=f"hub_card_{index}"):
                st.markdown(f'<div class="card-icon">{["▣", "↻", "⌕", "♧", "▥", "↗"][index]}</div>', unsafe_allow_html=True)
                st.subheader(PAGES[index])
                st.caption(descriptions[index])
                st.button("View recommendations →" if index == 5 else "Open dashboard →", key=f"card_{index}", on_click=navigate, args=(PAGES[index],), use_container_width=True)

def render_voice_metadata():
    st.markdown(
        '<div class="voice-heading"><div class="voice-symbol" aria-hidden="true">▥</div>'
        '<div><h1>Customer Emotion Analysis</h1>'
        '<p>Analyze verified customer speech using acoustic features and experimental Sinhala-English SER.</p>'
        '</div></div>', unsafe_allow_html=True,
    )

def render_placeholder(page):
    st.title(page)
    with st.container(border=True):
        st.subheader("Dashboard awaiting data integration")
        st.info("This page is ready for the next UI increment. No analytics have been calculated.")
        if page == PAGES[4]:
            st.caption("The current database has no payment amounts, invoices, or business-factor records.")
        else:
            st.caption("Use AMC Revenue Dashboard to review the existing customer, contract, warranty, service, and recommendation records.")

@st.cache_resource

def load_diarization_model():
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-community-1")
    if pipeline is None:
        raise RuntimeError("Diarization model could not be loaded.")
    pipeline.to(torch.device("cpu"))
    return pipeline

@st.cache_resource

def load_role_identification_model():
    model = Model.from_pretrained("pyannote/embedding")
    if model is None:
        raise RuntimeError("Speaker embedding model could not be loaded.")
    return model

def preprocess_bytes(audio_bytes: bytes, filename: str):
    """Return normalized audio; keep temporary source file alive while decoding."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / ("recording" + Path(filename).suffix.lower())
        path.write_bytes(audio_bytes)
        return AudioPreprocessingPipeline().process(path)

@st.cache_data(show_spinner=False)

def run_cached_diarization(audio_bytes: bytes, filename: str):
    audio = preprocess_bytes(audio_bytes, filename)
    turns = AutomaticDiarizationService(
        pipeline=load_diarization_model()
    ).diarize(samples=audio.samples, sample_rate=audio.sample_rate, num_speakers=2)
    return [(turn.start_seconds, turn.end_seconds, turn.speaker_id) for turn in turns]

def smooth_short_speaker_turns(
    turns,
    max_duration=0.75,
    max_gap=0.15,
):
    """
    Correct short isolated speaker-label changes.
    Only relabels a short turn if:
    - Both neighboring turns belong to the same speaker.
    - The short turn has a different speaker.
    - Both gaps are small.
    Returns a new list without modifying the original.
    """
    ordered = sorted(turns, key=lambda x: x[0])
    corrected = list(ordered)
    for i in range(1, len(ordered) - 1):
        start, end, speaker = ordered[i]
        prev_start, prev_end, prev_speaker = ordered[i - 1]
        next_start, next_end, next_speaker = ordered[i + 1]
        duration = end - start
        gap_before = start - prev_end
        gap_after = next_start - end
        if (
            duration <= max_duration
            and prev_speaker == next_speaker
            and speaker != prev_speaker
            and 0 <= gap_before <= max_gap
            and 0 <= gap_after <= max_gap
        ):
            corrected[i] = (
                start,
                end,
                prev_speaker,
            )
    return corrected

@st.cache_data(show_spinner=False)

def run_cached_role_identification(
    audio_bytes: bytes,
    filename: str,
):
    detected_turns = run_cached_diarization(
        audio_bytes, filename
    )
    ordered_turns = sorted(
        detected_turns,
        key=lambda turn: turn[0],
    )
    speakers = list(dict.fromkeys(
        speaker
        for start, end, speaker in ordered_turns
    ))
    if len(speakers) != 2:
        raise ValueError(
            f"Expected exactly 2 speakers, "
            f"but detected {len(speakers)}. "
            "Please review the diarization."
        )
    agent_speaker = speakers[0]
    customer_speaker = speakers[1]
    role_mapping = {
        agent_speaker: "Agent",
        customer_speaker: "Customer",
    }
    evidence = {
        "method": "first_speaker_amc_prior",
        "agent_speaker": agent_speaker,
        "customer_speaker": customer_speaker,
        "requires_review": True,
        "explanation": (
            "The first detected speaker is tentatively "
            "assigned as Agent because Metropolitan "
            "typically initiates AMC calls. "
            "This is not voice-based role recognition."
        ),
    }
    return role_mapping, evidence, None


@st.cache_data(show_spinner=False)
def run_cached_acoustic_analysis(
    audio_bytes: bytes,
    filename: str,
    role_rows: tuple,
):
    """Analyze verified customer speech without requiring the old SER model."""

    audio = preprocess_bytes(audio_bytes, filename)

    turns = [
        SpeakerTurn(
            start_seconds=float(start),
            end_seconds=float(end),
            speaker_id=str(speaker),
            role=str(role).strip().casefold(),
        )
        for start, end, speaker, role in role_rows
    ]

    customer_segments = (
        CustomerAudioService().extract_customer_segments(
            samples=audio.samples,
            sample_rate=audio.sample_rate,
            speaker_turns=turns,
        )
    )

    print(
        "[CUSTOMER AUDIO] "
        f"Verified turns: {len(turns)} | "
        f"Customer segments: {len(customer_segments)} | "
        f"Sample rate: {audio.sample_rate}"
    )

    # Existing customer acoustic analysis
    timeline = TemporalAcousticService().analyze(
        customer_segments
    )

    features = EmotionAcousticFeaturesService().analyze(
        customer_segments
    )

    # Locally trained eGeMAPS + SVM; retain the five-value result contract.
    experimental_ser = EGeMAPSSERService().analyze(customer_segments)
    emotion_predictions = []
    return turns, timeline, features, emotion_predictions, experimental_ser




EMOTION_STYLES = {"angry": "angry", "happy": "happy", "sad": "sad", "neutral": "neutral"}


def emotion_badge(value):
    label = str(value).strip()
    style = EMOTION_STYLES.get(label.casefold(), "other")
    return f'<span class="emotion-badge emotion-{style}">{escape(label.capitalize())}</span>'


def format_call_time(value):
    # Round once to centiseconds so minute boundaries remain valid.
    total = max(0, round(float(value) * 100))
    minutes, remainder = divmod(total, 6000)
    seconds, hundredths = divmod(remainder, 100)
    return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"


def render_emotion_table(predictions):
    legend = ''.join(emotion_badge(label) for label in EMOTION_STYLES)
    st.markdown(f'<div class="emotion-legend">{legend}</div>', unsafe_allow_html=True)
    rows = []
    for item in predictions:
        start = format_call_time(item["start_seconds"])
        end = format_call_time(item["end_seconds"])
        duration = float(item["duration_seconds"])
        emotion = emotion_badge(item["predicted_emotion"])
        status = escape(str(item["status"]))
        rows.append(f'<tr><td>{start}</td><td>{end}</td><td>{duration:.2f}s</td>'
                    f'<td>{emotion}</td><td>{status}</td></tr>')
    st.markdown('<div class="emotion-table-wrap"><table class="emotion-table">'
                '<thead><tr><th scope="col">Start</th><th scope="col">End</th>'
                '<th scope="col">Duration</th><th scope="col">Emotion</th>'
                '<th scope="col">Status</th></tr></thead><tbody>'
                + ''.join(rows) + '</tbody></table></div>', unsafe_allow_html=True)


def render_voice_workflow(uploaded, detected, confirmed, analyzed):
    if analyzed:
        title, detail = "Analysis complete", "Review the customer timeline, acoustic evidence and experimental emotion predictions below."
    elif confirmed:
        title, detail = "Customer role confirmed", "Your verified customer speech is ready. Select Analyze Call to continue."
    else:
        title, detail = "Speakers not confirmed", "Upload a recording, detect speakers, and confirm the customer role to enable emotion analysis."
    style = " ready" if confirmed else ""
    st.markdown(f'<div class="voice-notice{style}" role="status"><strong>{title}</strong>{detail}</div>', unsafe_allow_html=True)
    stages = [("Upload Call", "Add a supported audio file", uploaded),
              ("Detect Speakers", "Identify different speakers", detected),
              ("Confirm Roles", "Mark the customer speaker", confirmed),
              ("Analyze Call", "View voice analysis & emotions", analyzed)]
    items = []
    for index, (label, detail, done) in enumerate(stages, 1):
        state = " done" if done else ""
        number = "✓" if done else str(index)
        items.append(f'<div class="voice-step{state}"><span class="step-number">{number}</span>'
                     f'<div><strong>{label}</strong><small>{detail}</small></div></div>')
    st.markdown('<div class="voice-steps">' + ''.join(items) + '</div>', unsafe_allow_html=True)


def render_voice():
    render_voice_metadata()
    service = VoiceCustomerService()
    try:
        customers = service.list_customers()
        names = {c['customer_id']: c['customer_name'] for c in customers}
        with st.container(key="voice_customer_identification"):
            id_column, name_column, device_column = st.columns([1, 1.2, 1.8], gap="medium")
            with id_column:
                customer_id = st.selectbox(
                    "Customer ID", options=list(names), index=None,
                    placeholder="Select or type a customer ID",
                    help="Open the dropdown and type to filter customer IDs.", key="voice_customer_selector",
                )
            with name_column:
                st.text_input("Customer Name", value=names.get(customer_id, ""), disabled=True)
            devices = service.list_devices(customer_id) if customer_id is not None else []
            device_map = {d['device_id']: d for d in devices}
            with device_column:
                # A customer's selector gets its own widget key; old device IDs cannot carry over.
                device_id = st.selectbox(
                    "Customer Device", options=list(device_map),
                    index=0 if len(devices) == 1 else None,
                    format_func=lambda value: (
                        f"{value} — {device_map[value]['brand']} {device_map[value]['model']}"
                        f" — Serial: {device_map[value]['serial_number']}"
                    ),
                    key=f"voice_device_selector_{customer_id}",
                    disabled=not devices, placeholder="Select the device for this call",
                )
        context = (customer_id, device_id)
        reset_customer_context(st.session_state, context)
        if customer_id is None:
            st.info("Select a customer before uploading a recording.")
            return
        if not devices:
            st.warning("This customer has no registered devices.")
            return
        if device_id is None:
            st.info("Select the device discussed in this call.")
            return
        device = device_map[device_id]
        st.caption(f"Device ownership: customer {customer_id}, device {device_id}")
        st.write("**Purchase date:**", device['purchase_date'])
        st.write("**Warranty:**", device['warranty_start_date'], "to", device['warranty_end_date'])
        today = date.today().isoformat()
        warranty_status = (
            "Upcoming" if today < device['warranty_start_date'] else
            "Under warranty" if today <= device['warranty_end_date'] else "Expired"
        )
        st.write("**Warranty status:**", warranty_status)
        contracts = service.contracts(customer_id, device_id)
        if contracts:
            st.dataframe(contracts, hide_index=True, use_container_width=True)
        else:
            st.info("No AMC contracts are registered for this customer and device.")
    except (OSError, sqlite3.DatabaseError) as exc:
        reset_customer_context(st.session_state, None)
        st.error(f"Customer database unavailable: {exc}")
        return
    workflow = st.empty()
    uploaded_file = st.file_uploader(
        "Upload a customer-service call",
        type=["wav", "mp3", "m4a", "mp4", "amr", "3gp"],
        key="customer_call_audio",
    )
    upload_identity = (
        (uploaded_file.name, hashlib.sha256(uploaded_file.getvalue()).hexdigest())
        if uploaded_file is not None else None
    )
    # ==========================================================
    # RESET RESULTS WHEN A NEW CALL RECORDING IS UPLOADED
    # ==========================================================
    identity = (customer_id, device_id, upload_identity)
    if st.session_state.get("active_audio_identity") != identity:
        for key in (
            "speaker_review_turns",
            "verified_speaker_turns",
            "speaker_role_editor",
            "analysis_results",
            "role_scores",
            "role_margin",
            "review_identity",
            "role_review_confirmed",
            "confirmed_agent_speaker",
            "review_agent_speaker",
        ):
            st.session_state.pop(key, None)
        st.session_state["active_audio_identity"] = identity

    if uploaded_file is not None:
        try:
            recording_id = service.associate_recording(
                customer_id, device_id, uploaded_file.getvalue(),
            )
            st.session_state['voice_recording_id'] = recording_id
            st.caption(f"Recording {recording_id} linked to {names[customer_id]} · device {device_id}")
        except (ValueError, OSError, sqlite3.DatabaseError) as exc:
            for key in ('analysis_results', 'verified_speaker_turns', 'role_review_confirmed'):
                st.session_state.pop(key, None)
            st.error(f"Recording could not be associated: {exc}")
            return
        st.audio(uploaded_file)

    if uploaded_file is not None:
        if uploaded_file is not None:
            st.subheader("Automatic Speaker Identification")
            st.caption(
                "Two-speaker AMC calls. No agent reference "
                "voice or transcription required."
            )
            if st.button(
                "Detect Speakers and Identify Roles",
                type="primary",
            ):
                try:
                    with st.spinner(
                        "Detecting speakers and suggesting roles..."
                    ):
                        audio_bytes = uploaded_file.getvalue()
                        raw_turns = run_cached_diarization(
                            audio_bytes,
                            uploaded_file.name,
                        )
                        detected_turns = list(raw_turns)
                        for _ in range(3):
                            updated_turns = smooth_short_speaker_turns(
                                detected_turns,
                                max_duration=0.75,
                                max_gap=0.15,
                            )
                            if updated_turns == detected_turns:
                                break
                            detected_turns = updated_turns
                        role_mapping, evidence, margin = (
                            run_cached_role_identification(
                                audio_bytes,
                                uploaded_file.name,
                            )
                        )
                        rows = [
                            {
                                "Start (s)": round(start, 2),
                                "End (s)": round(end, 2),
                                "Detected Speaker": speaker,
                                "Verified Role": role_mapping[speaker],
                            }
                            for start, end, speaker in detected_turns
                        ]
                        st.session_state[
                            "speaker_review_turns"
                        ] = rows
                        st.session_state[
                            "verified_speaker_turns"
                        ] = [
                            dict(row) for row in rows
                        ]
                        st.session_state[
                            "role_scores"
                        ] = evidence
                        st.session_state[
                            "role_margin"
                        ] = margin
                        st.session_state[
                            "role_review_confirmed"
                        ] = False
                        st.session_state.pop("speaker_role_editor", None)
                        st.session_state.pop("review_agent_speaker", None)
                        st.session_state.pop("confirmed_agent_speaker", None)
                        st.session_state.pop(
                            "analysis_results", None
                        )
                    st.success(
                        "Speakers detected and roles suggested. "
                        "Please review the assignments below."
                    )
                except Exception as exc:
                    st.error(
                        f"Speaker identification failed: {exc}"
                    )
                    st.exception(exc)
                # ==========================================================
                # SPEAKER ROLE REVIEW AND CONFIRMATION

        if st.session_state.get("speaker_review_turns"):
            st.subheader("Review Speaker Roles")
            rows = st.session_state["speaker_review_turns"]
            # Get the unique speakers detected by pyannote
            speaker_ids = list(dict.fromkeys(
                row["Detected Speaker"]
                for row in rows
            ))
            speaker_labels = {
                speaker: f"Speaker {index + 1}"
                for index, speaker in enumerate(speaker_ids)
            }
            evidence = st.session_state.get("role_scores", {})
            # Explain how the roles were suggested
            if isinstance(evidence, dict) and evidence.get("explanation"):
                st.info(evidence["explanation"])
            # Display the diarization results
            display_rows = [
                {**row, "Detected Speaker": speaker_labels[row["Detected Speaker"]]}
                for row in rows
            ]
            st.dataframe(
                display_rows,
                hide_index=True,
                use_container_width=True,
            )
            if len(speaker_ids) == 2:
                suggested_agent = (
                    evidence.get("agent_speaker", speaker_ids[0])
                    if isinstance(evidence, dict)
                    else speaker_ids[0]
                )
                if suggested_agent not in speaker_ids:
                    suggested_agent = speaker_ids[0]
                # User can correct the automatically suggested agent
                selected_agent = st.selectbox(
                    "Select the Service Agent",
                    options=speaker_ids,
                    format_func=speaker_labels.get,
                    index=speaker_ids.index(suggested_agent),
                    key="review_agent_speaker",
                )
                # The other speaker is automatically the customer
                selected_customer = next(
                    speaker
                    for speaker in speaker_ids
                    if speaker != selected_agent
                )
                st.write(f"**Agent:** {speaker_labels[selected_agent]}")
                st.write(f"**Customer:** {speaker_labels[selected_customer]}")
                # If selection changes, require reconfirmation
                confirmed_agent = st.session_state.get(
                    "confirmed_agent_speaker"
                )
                if selected_agent != confirmed_agent:
                    st.session_state["role_review_confirmed"] = False
                    st.session_state.pop("analysis_results", None)
                    st.session_state.pop("verified_speaker_turns", None)
                if st.button(
                    "Confirm Speaker Roles",
                    type="primary",
                    key="confirm_speaker_roles",
                ):
                    role_mapping = {
                        selected_agent: "Agent",
                        selected_customer: "Customer",
                    }
                    # Apply the role consistently to every turn
                    st.session_state["verified_speaker_turns"] = [
                        {
                            **row,
                            "Verified Role": role_mapping[
                                row["Detected Speaker"]
                            ],
                        }
                        for row in rows
                    ]
                    st.session_state["confirmed_agent_speaker"] = (
                        selected_agent
                    )
                    st.session_state["role_review_confirmed"] = True
                    # Clear old emotion analysis results
                    st.session_state.pop("analysis_results", None)
                    st.success(
                        "Speaker roles confirmed successfully. "
                        "Customer emotion analysis is now ready."
                    )
                if st.session_state.get("role_review_confirmed", False):
                    st.success("Speaker roles are verified.")
            else:
                st.warning(
                    "Exactly two speakers are required for "
                    "automatic Agent/Customer assignment."
                )

        if (
            uploaded_file is not None
            and st.session_state.get("speaker_review_turns")
        ):
            with st.expander("Listen to detected speaker segments"):
                try:
                    review_audio = preprocess_bytes(uploaded_file.getvalue(), uploaded_file.name)
                    for index, row in enumerate(st.session_state["speaker_review_turns"]):
                        start, end = float(row["Start (s)"]), float(row["End (s)"])
                        if end - start < 0.1:
                            continue
                        sr = review_audio.sample_rate
                        segment = review_audio.samples[int(start * sr):int(end * sr)]
                        st.caption(f"Segment {index + 1}: {start:.1f}s–{end:.1f}s — {speaker_labels[row['Detected Speaker']]}")
                        st.audio(segment, sample_rate=sr)
                except Exception as exc:
                    st.warning(f"Could not play speaker segments: {exc}")



        # ==========================================================
        # CUSTOMER EMOTION ANALYSIS
        # ==========================================================

        if uploaded_file is not None:
            st.divider()
            st.subheader("Customer Emotion Analysis")

            verified_turns = (
                st.session_state.get("verified_speaker_turns") or []
            )

            customer_rows = [
                row for row in verified_turns
                if str(row.get("Verified Role", "")).strip().casefold() == "customer"
            ]
            if st.session_state.get("role_review_confirmed", False):
                st.caption(f"{len(customer_rows)} customer speech segments ready for analysis.")

            # The button is OUTSIDE the customer_rows if/else.
            # It is visible even before roles are confirmed.
            ready_for_analysis = bool(
                st.session_state.get(
                    "role_review_confirmed", False
                )
                and customer_rows
            )

            if not ready_for_analysis:
                st.info(
                    "Detect speakers, review the assignments, "
                    "and confirm speaker roles to enable analysis."
                )

            if st.button(
                "Analyze Call",
                type="primary",
                key="run_customer_call_analysis",
                use_container_width=True,
                disabled=not ready_for_analysis,
            ):
                try:
                    with st.spinner(
                        "Analyzing customer acoustic features..."
                    ):
                        start_time = time.perf_counter()

                        role_rows = tuple(
                            (
                                float(row["Start (s)"]),
                                float(row["End (s)"]),
                                str(row["Detected Speaker"]),
                                str(row["Verified Role"]),
                            )
                            for row in verified_turns
                        )

                        (
                            turns,
                            timeline,
                            features,
                            emotion_predictions,
                            experimental_ser,
                        ) = run_cached_acoustic_analysis(
                            uploaded_file.getvalue(),
                            uploaded_file.name,
                            role_rows,
                        )

                        temporal_emotion = (
                            TemporalAcousticEmotionService().analyze(
                                features
                            )
                        )

                        st.session_state["analysis_results"] = {
                            "identity": identity,
                            "customer_id": customer_id,
                            "device_id": device_id,
                            "recording_id": recording_id,
                            "turns": turns,
                            "timeline": timeline,
                            "acoustic_features": features,
                            "analysis_seconds": (
                                time.perf_counter() - start_time
                            ),
                            "temporal_emotion": temporal_emotion,
                            "emotion_predictions": emotion_predictions,
                            "experimental_ser": experimental_ser,
                        }

                    st.success(
                        "Customer acoustic analysis completed."
                    )

                except Exception as exc:
                    st.session_state.pop(
                        "analysis_results", None
                    )
                    st.error(
                        f"Analyze Call failed: {exc}"
                    )
                    st.exception(exc)



    results = st.session_state.get("analysis_results")
    if (uploaded_file is not None and results is not None
            and results.get("identity") == identity
            and st.session_state.get("role_review_confirmed", False)):
        with st.container(border=False, key="voice_panel_speakers"):
            st.subheader("Speaker Timeline")
            speaker_df = pd.DataFrame([
                {
                    "Start (s)": turn.start_seconds,
                    "End (s)": turn.end_seconds,
                    "Speaker": speaker_labels.get(turn.speaker_id, "Speaker"),
                    "Role": turn.role,
                }
                for turn in results["turns"]
            ])
            st.dataframe(speaker_df, width="stretch", hide_index=True)
            st.caption(f"Analysis time (cached if repeated): {results['analysis_seconds']:.2f} seconds")

        with st.container(border=False, key="voice_panel_energy"):
            st.subheader("Customer Vocal Energy Over Time")
            energy_df = pd.DataFrame([
                {
                    "Time (s)": (point.start_seconds + point.end_seconds) / 2,
                    "RMS Energy": point.rms_energy,
                }
                for point in results["timeline"]
            ])
            if not energy_df.empty:
                st.line_chart(energy_df.set_index("Time (s)"), color="#C8102E", x_label="Call time (seconds)", y_label="RMS energy", height=280)
            else:
                st.warning("No customer speech segments were detected. Review the roles.")

        with st.container(border=False, key="voice_panel_pitch"):
            st.subheader("Customer Acoustic Features — Pitch & RMS Energy")
            features = results.get("acoustic_features", [])
            if features:
                acoustic_df = pd.DataFrame([
                    {
                        "Start (s)": round(item.start_seconds, 2),
                        "End (s)": round(item.end_seconds, 2),
                        "RMS Energy": round(item.rms_energy, 4),
                        "Energy Variability": round(item.energy_variability, 4),
                        "Silence Ratio": round(item.silence_ratio, 3),
                        "Median Pitch (Hz)": item.median_pitch_hz,
                        "Pitch Variability (Hz)": item.pitch_variability_hz,
                    }
                    for item in features
                ])
                st.dataframe(acoustic_df, width="stretch", hide_index=True)
                pitch_df = acoustic_df[["Start (s)", "Median Pitch (Hz)"]].dropna()
                if not pitch_df.empty:
                    st.subheader("Customer Pitch Over Time")
                    st.line_chart(pitch_df.set_index("Start (s)"), color="#38BDF8", x_label="Call time (seconds)", y_label="Median pitch (Hz)", height=280)
                else:
                    st.info("No usable pitch estimates for these segments.")
                st.caption(
                    "Acoustic measurements are emotion-related evidence, not validated "
                    "emotion labels. Speaker identification may also contain errors."
                )
            else:
                st.info("No customer acoustic features available. Check speaker roles and audio length.")

        with st.container(border=False, key="voice_panel_activation"):
            st.subheader("Temporal Vocal Activation Evidence")
            temporal_points = results.get("temporal_emotion", [])
            if temporal_points:
                temporal_df = pd.DataFrame([
                    {
                        "Time (s)": (
                            point.start_seconds + point.end_seconds
                        ) / 2,
                        "Activation Score": point.activation_score,
                        "Uncertainty": point.uncertainty,
                        "Trend": point.trend,
                    }
                    for point in temporal_points
                ])
                st.line_chart(
                    temporal_df.set_index("Time (s)")[
                        ["Activation Score", "Uncertainty"]
                    ],
                    color=["#C8102E", "#64748B"],
                    x_label="Call time (seconds)", y_label="Relative score", height=280,
                )
                st.dataframe(
                    temporal_df,
                    width="stretch",
                    hide_index=True,
                )
                for point in temporal_points:
                    with st.expander(
                        f"{point.start_seconds:.1f}s–"
                        f"{point.end_seconds:.1f}s | "
                        f"{point.trend}"
                    ):
                        st.write(
                            f"Activation score: {point.activation_score:.2f}"
                        )
                        st.write(
                            f"Heuristic uncertainty: {point.uncertainty:.2f}"
                        )
                        for item in point.evidence:
                            st.write(f"- {item}")
                st.caption(
                    "Activation is relative to this call. "
                    "It is not an anger or satisfaction probability."
                )
            else:
                st.info("No temporal acoustic evidence available.")

        with st.container(border=False, key="voice_panel_emotions"):
            st.subheader("Customer Emotion Timeline")
            st.caption("Locally trained eGeMAPS + SVM · Experimental Sinhala-English SER")
            experimental_ser = results.get("experimental_ser", [])
            if experimental_ser:
                render_emotion_table(experimental_ser)
                st.caption("Experimental predictions require human review. Short or unavailable segments are identified in the Status column.")
            else:
                st.info("No experimental speech emotion results available.")


    if uploaded_file is None:
        st.button("Analyze Call", key="run_customer_call_analysis", type="primary",
                  disabled=True, use_container_width=True)
    with workflow.container():
        render_voice_workflow(
            uploaded_file is not None,
            bool(st.session_state.get("speaker_review_turns")),
            bool(st.session_state.get("role_review_confirmed")),
            bool(uploaded_file is not None and st.session_state.get("role_review_confirmed")
                 and results and results.get("identity") == identity),
        )



def render_amc_evidence():

    amc_service = AMCDecisionService()
    customers = amc_service.list_customers()

    if not customers:
        st.warning("No customer records found.")
    else:
        customer_options = {
            f"{c['customer_name']} (ID: {c['customer_id']})":
            c["customer_id"]
            for c in customers
        }

        selected = st.selectbox(
            "Select Customer",
            options=list(customer_options),
            key="amc_customer_selector",
        )

        customer_id = customer_options[selected]

        st.subheader("Multi-Agent AMC Evidence Analysis")

        from emotion_aware_after_sales.database.setup_database import get_connection

        with get_connection() as conn:
            device_rows = conn.execute(
                """
                SELECT d.device_id, d.device_type, d.brand,
                       d.model, d.serial_number
                FROM customer_devices cd
                JOIN devices d ON d.device_id = cd.device_id
                WHERE cd.customer_id = ?
                  AND (
                      LOWER(d.device_type) LIKE '%printer%'
                      OR LOWER(d.device_type) LIKE '%copier%'
                  )
                ORDER BY d.device_id
                """,
                (customer_id,),
            ).fetchall()

        devices = [dict(row) for row in device_rows]

        if not devices:
            st.warning("No registered printers or copiers found.")
            return
        else:
            device_options = {
                f"{d['device_id']} — {d['brand']} {d['model']}": d["device_id"]
                for d in devices
            }

            selected_device = st.selectbox(
                "Select Printer or Copier",
                options=list(device_options),
                key=f"amc_agent_device_{customer_id}",
            )

            agent_device_id = device_options[selected_device]

            if st.button(
                "Run Multi-Agent Analysis",
                type="primary",
                key="run_amc_agents",
            ):
                with st.spinner("Coordinating AMC agents..."):
                    try:
                        result = AMCMultiAgentOrchestrator().analyze(
                            customer_id=customer_id,
                            device_id=agent_device_id,
                        )
                        st.session_state["amc_agent_result"] = {
                            "customer_id": customer_id,
                            "device_id": agent_device_id,
                            "result": result,
                        }
                    except Exception as exc:
                        st.error(f"Multi-agent analysis failed: {exc}")

            saved = st.session_state.get("amc_agent_result")

            if (
                saved
                and saved["customer_id"] == customer_id
                and saved["device_id"] == agent_device_id
            ):
                result = saved["result"]

                st.subheader("Agent Activity")
                st.dataframe(
                    result["activity"],
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader("Orchestrator Assessment")
                st.info(result["assessment"])

                with st.expander("Contract Evidence"):
                    st.json(result["evidence"].get("contract", {}))

                with st.expander("Service Evidence"):
                    st.json(result["evidence"].get("service", {}))

                with st.expander("Payment Evidence"):
                    st.json(result["evidence"].get("payment", {}))
                with st.expander("Maintenance Substitution Decisions"):
                    st.json(result.get("decisions", []))
                st.caption(f"Persisted run: {result.get('run_id', 'unavailable')} · Emotion/Voice remains standalone")

                with st.expander("Retrieved AMC Policy Evidence"):
                    for policy in result["evidence"].get("policies", []):
                        st.markdown(
                            f"**{policy['policy_id']} — {policy['document']}**"
                        )
                        st.write(policy["passage"])
                        st.caption("Source: Synthetic research policy")
                        st.divider()

        profile = amc_service.get_customer_profile(
            customer_id,
            agent_device_id,
        )

        if profile:
            contracts = amc_service.get_amc_contracts(
                profile["customer_id"],
                profile["device_id"],
            )
            history = amc_service.get_service_history(
                profile["customer_id"],
                profile["device_id"],
            )
            decision = amc_service.recommend(
                profile,
                contracts,
                history,
            )

            st.subheader("Customer & Device Information")

            st.write("**Customer:**", profile["customer_name"])
            st.write("**Device Type:**", profile["device_type"])
            st.write(
                "**Device:**",
                f"{profile['brand']} {profile['model']}",
            )
            st.write("**Serial Number:**", profile["serial_number"])
            st.write("**Device Features:**", profile["device_features"])

            st.subheader("Warranty Information")

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Purchase Date",
                    profile["purchase_date"],
                )

            with col2:
                st.metric(
                    "Warranty End",
                    profile["warranty_end_date"],
                )

            with col3:
                st.metric(
                    "Warranty Status",
                    decision["warranty_status"],
                )

            st.subheader("AMC Contract Information")
            st.write("**AMC Status:**", decision["amc_status"])

            if contracts:
                st.dataframe(
                    contracts,
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("This customer has no AMC contract.")

            st.subheader("Service History")

            if history:
                st.dataframe(
                    history,
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.info("No service records available.")

            st.subheader("Decision Intelligence Recommendations")

            for action in decision["recommended_actions"]:
                st.write(f"• {action}")

            st.subheader("Decision Explanation")

            for reason in decision["decision_reasons"]:
                st.write(f"• {reason}")

            st.caption(
                "Synthetic customer data and illustrative AMC decision rules. "
                "Recommendations require human verification."
            )

def load_amc_dashboard(conn, year="All years", status="All statuses", device="All devices"):
    from emotion_aware_after_sales.services.amc_revenue_service import load_dashboard
    return load_dashboard(conn, year, status, device)


def render_amc_revenue():
    from contextlib import closing
    from emotion_aware_after_sales.services.amc_revenue_service import open_demo
    st.caption("Contract lifecycle and renewal conversion · Printers & copiers only")
    st.markdown('<div class="data-note"><b>SYNTHETIC RESEARCH DATA</b> · Dedicated demo ledger · 2023–2026 · Not actual Metropolitan revenue.</div>', unsafe_allow_html=True)
    with closing(open_demo()) as conn:
        options = load_amc_dashboard(conn)
        filters = st.columns([1, 1, 1, 1.3])
        year = filters[0].selectbox("Contract start year", ['All years'] + options['years'], key='revenue_year')
        status = filters[1].selectbox("Contract status", ['All statuses'] + options['statuses'], key='revenue_status')
        device = filters[2].selectbox("Device type", ['All devices', 'Printer', 'Copier'], key='revenue_device')
        filters[3].caption("Filters apply immediately. Status is measured at the demo reporting date: 20 October 2026.")
        data = load_amc_dashboard(conn, year, status, device)
    rows, renewals = data['rows'], data['renewals']
    expired = sum(r['dashboard_status'] == 'Expired' for r in rows)
    cards = [
        ('TOTAL CONTRACTS', f'{len(rows):,}', 'Selected contract cohort', ''),
        ('RENEWED CONTRACTS', f"{data['renewed_contracts']:,}", 'Linked to a previous contract', ''),
        ('INVOICED', f"{data['invoiced_cents']/100:,.0f}", 'LKR · linked AMC invoices', ''),
        ('PAID', f"{data['paid_cents']/100:,.0f}", 'LKR · received payments', ''),
        ('OUTSTANDING', f"{data['outstanding_cents']/100:,.0f}", 'LKR · unpaid invoice balance', 'attention'),
        ('EXPIRED CONTRACTS', f'{expired:,}', 'Ended before reporting date', 'attention'),
    ]
    for col, (label, value, detail, accent) in zip(st.columns(6), cards):
        col.markdown(f'<div class="revenue-kpi {accent}"><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div><div class="kpi-detail">{detail}</div></div>', unsafe_allow_html=True)
    st.caption(f"Demo reporting date: {data['as_of']} · Amounts in LKR. Year selects contract start year; payments include receipts against those contracts through the reporting date.")
    if not rows:
        st.info("No printer/copier contracts match these filters. Choose another year or status.")
    left, right = st.columns([2.25, 1], gap='large')
    with left:
        with st.container(border=True):
            st.subheader('Contracts Growth by Year')
            st.caption('Contracts started per year · status and device filters apply; year filter selects the detail cohort below.')
            counts = {str(y): {'New': 0, 'Renewed': 0} for y in range(2023, 2027)}
            for record in data['growth']:
                key = record['start_date'][:4]
                kind = 'Renewed' if record['renewed_from_id'] is not None else 'New'
                counts.setdefault(key, {'New': 0, 'Renewed': 0})[kind] += 1
            chart = pd.DataFrame([{'Year': y, **values} for y, values in sorted(counts.items())])
            st.bar_chart(chart, x='Year', y=['New', 'Renewed'], color=['#071B36', '#8299b6'], height=335)
    with right:
        with st.container(border=True):
            st.subheader('Renewal Status')
            st.caption('Renewal opportunities for the selected contracts, at the demo reporting date.')
            if renewals:
                totals = {s: sum(r['status'] == s for r in renewals) for s in ('Accepted', 'Pending', 'Contacted', 'Declined')}
                colors = {'Accepted': '#071B36', 'Pending': '#d5deea', 'Contacted': '#8299b6', 'Declined': '#C8102E'}
                offset, arcs = 0, []
                for label, n in totals.items():
                    percent = n * 100 / len(renewals)
                    arcs.append(f'<circle cx="60" cy="60" r="44" fill="none" stroke="{colors[label]}" stroke-width="13" pathLength="100" stroke-dasharray="{percent} {100-percent}" stroke-dashoffset="{-offset}" transform="rotate(-90 60 60)"/>')
                    offset += percent
                rate = totals['Accepted'] * 100 / len(renewals)
                st.markdown('<div class="renewal-ring"><svg viewBox="0 0 120 120" role="img" aria-label="Accepted renewal rate">' + ''.join(arcs) + f'<text x="60" y="60" text-anchor="middle" fill="#071B36" font-size="18">{rate:.0f}%</text><text x="60" y="75" text-anchor="middle" fill="#64748b" font-size="8">accepted</text></svg></div>', unsafe_allow_html=True)
                st.caption(' · '.join(f'{k}: {v}' for k, v in totals.items()))
            else:
                st.info('No renewal events in this cohort.' if renewals is not None else 'Renewal table unavailable.')
        with st.container(border=True):
            st.subheader('Conversion Funnel')
            st.caption('Distinct contracts → invoiced contracts → fully paid contracts')
            stages = [('Contracts', len(rows)),
                      ('Invoiced', sum(r['invoice_id'] is not None for r in rows)),
                      ('Fully paid', sum(r['invoice_id'] is not None and r['outstanding_cents'] == 0 for r in rows))]
            for label, count in stages:
                percent = count * 100 / len(rows) if rows else 0
                st.caption(f'{label} · {count:,} · {percent:.0f}%')
                st.progress(count / len(rows) if rows else 0)
    actions = st.columns([1, 1, 1])
    export = pd.DataFrame(rows)
    from emotion_aware_after_sales.services.pdf_report import build_pdf
    actions[0].download_button('Export filtered contracts PDF',
        build_pdf('AMC Revenue Dashboard', {'Year':year,'Status':status,'Device':device,'Reporting date':data['as_of']},
                  {label:value for label,value,detail,accent in cards}, rows,
                  'Amounts in LKR. Synthetic demo ledger; selected contract cohort through reporting date.'),
        'synthetic_amc_contracts.pdf', 'application/pdf', use_container_width=True)
    actions[1].button('Review unpaid invoices', on_click=lambda: st.session_state.update(revenue_followups=True), use_container_width=True)
    actions[2].button('Open customer evidence →', on_click=lambda: st.session_state.update(amc_view='AMC Evidence Analysis'), use_container_width=True, type='primary')
    with st.expander('Contract register & follow-up priorities', expanded=st.session_state.get('revenue_followups', False)):
        st.caption(f'{expired} expired contracts in this selection. These are demo organisations, not the customer records in Evidence Analysis.')
        st.dataframe(export, hide_index=True, use_container_width=True)
        st.subheader('Outstanding invoice follow-up')
        unpaid = [dict(customer=r['customer_name'], contract=r['contract_id'], invoice=r['invoice_number'],
                       due=r['due_date'], outstanding_lkr=r['outstanding_cents']/100,
                       priority='Overdue' if r['due_date'] < data['as_of'] else 'Not yet due')
                  for r in rows if r['invoice_id'] is not None and r['outstanding_cents'] > 0]
        if unpaid:
            st.dataframe(unpaid, hide_index=True, use_container_width=True)
        else:
            st.info('No outstanding invoices in this selection.')
    with st.expander('Metric definitions & data limitations'):
        st.write('Synthetic demo data is stored separately in amc_revenue_demo.db. Contract year means start year. Renewed contracts have an explicit previous-contract link. Renewal status describes recorded opportunities for the selected contracts; accepted opportunities link to successor contracts. Invoiced and paid amounts use explicit invoice-to-contract and payment-to-invoice links. Outstanding is the unpaid invoice balance, including amounts not yet due. Payments are aggregated before joining contracts to avoid double counting installments. All amounts are LKR; the reporting date is frozen at 20 October 2026. The growth chart retains all four years while respecting status and device filters. Evidence Analysis continues to use the separate existing customer database.')


def render_amc():
    st.title("AMC Revenue Dashboard")
    st.radio('AMC workspace', ['Revenue Dashboard', 'AMC Evidence Analysis'], horizontal=True,
             key='amc_view', label_visibility='collapsed')
    if st.session_state['amc_view'] == 'Revenue Dashboard':
        render_amc_revenue()
    else:
        st.caption('Customer and device evidence · Synthetic research policies · Human review required')
        render_amc_evidence()


page = st.session_state.get("hub_page", "Hub")

if page == "Hub":
    render_hub()
else:
    index = PAGES.index(page) if page in PAGES else 0

    page_navigation(index)

    if page == PAGES[3]:
        render_voice()
    elif page == PAGES[0]:
        try:
            render_amc()
        except (OSError, __import__('sqlite3').DatabaseError) as exc:
            st.error(f"Customer database unavailable: {exc}")
    elif page == PAGES[4]:
        try:
            from emotion_aware_after_sales.services.payment_business_dashboard import render_payment_business
            render_payment_business(st)
        except (OSError, sqlite3.DatabaseError, ValueError) as exc:
            st.error(f"Payment dashboard unavailable: {exc}")
    elif page == PAGES[2]:
        try:
            from emotion_aware_after_sales.services.service_dashboard import render_service_dashboard
            render_service_dashboard(st)
        except (OSError, sqlite3.DatabaseError, ValueError) as exc:
            st.error(f"Service dashboard unavailable: {exc}")
    elif page == PAGES[1]:
        try:
            from emotion_aware_after_sales.services.contract_renewal_dashboard import render_contract_renewal
            render_contract_renewal(st)
        except (OSError, sqlite3.DatabaseError, ValueError) as exc:
            st.error(f"Contract dashboard unavailable: {exc}")
    else:
        render_placeholder(page)
