"""Streamlit prototype: diarization, agent voice matching, and customer acoustics.
Transcription is intentionally disabled in this workflow.
"""
from __future__ import annotations
import hashlib
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
from emotion_aware_after_sales.services.speech_emotion_recognition_service import SpeechEmotionRecognitionService
from emotion_aware_after_sales.services.conversation_role_identification_service import ConversationRoleIdentificationService
from emotion_aware_after_sales.services.amc_decision_service import AMCDecisionService


st.set_page_config(page_title="AMC & Service Management", layout="wide")
st.markdown("""<style>
.stApp {background:#f6f7f9;color:#0b2039}
[data-testid="stHeader"] {background:white}
.block-container {max-width:1510px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {color:#0b2039;letter-spacing:-.025em}
h1 {font-size:2.2rem!important} h3 {font-size:1.15rem!important}
[data-testid="stVerticalBlockBorderWrapper"] {background:white;border-color:#d7dde5;border-radius:0!important}
.topbar {background:white;border-bottom:1px solid #d7dde5;padding:18px 24px;margin-bottom:28px;font-size:19px;font-weight:700}
.topbar span {float:right;font-size:13px;color:#64748b;font-weight:400}
/* Shared light resting state for dashboard, navigation, upload and action buttons. */
:is(.stButton, .stDownloadButton, .stFormSubmitButton, [data-testid="stFileUploader"]) button {
    background:#f1f4f8!important;color:#0b2039!important;
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
    background:#0b2039!important;color:#ffffff!important;border-color:#0b2039!important;
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
</style>""", unsafe_allow_html=True)
st.markdown('<div class="topbar">AMC & Service Management <span>Service intelligence workspace</span></div>', unsafe_allow_html=True)

PAGES = ["AMC Revenue Dashboard", "Contract & Renewal Analysis", "Service & Operational Analysis", "Customer Feedback & Voice", "Payment & Business Analysis", "Final AMC Recommendation"]

def navigate(page):
    st.session_state["hub_page"] = page

def page_navigation(index):
    st.button("← Management Hub", on_click=navigate, args=("Hub",), key=f"home_top_{index}")

def render_hub():
    st.title("AMC & Service Management Hub")
    st.caption("Select a specialized dashboard to analyze contract performance, service operations, and renewal risks.")
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
            with column, st.container(border=False, height=310, key=f"hub_card_{index}"):
                st.markdown(f'<div class="card-icon">{["▣", "↻", "⌕", "♧", "▥", "↗"][index]}</div>', unsafe_allow_html=True)
                st.subheader(PAGES[index])
                st.caption(descriptions[index])
                st.button("VIEW RECOMMENDATIONS →" if index == 5 else "OPEN DASHBOARD →", key=f"card_{index}", on_click=navigate, args=(PAGES[index],), use_container_width=True)

def render_voice_metadata():
    st.title("Customer Feedback & Voice Analysis")
    st.caption("Review call audio, confirm speaker roles, and inspect customer-only acoustic evidence.")
    with st.container(border=True):
        for column, label, value in zip(st.columns(4), ["CUSTOMER", "COMPLAINT ID", "DATE LOGGED", "ASSIGNED COORDINATOR"], ["Not linked to recording", "Not available", "Not available", "Not assigned"]):
            with column:
                st.caption(label)
                st.write(value)

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

@st.cache_resource

def load_speech_emotion_model():
    from transformers import (
        AutoFeatureExtractor,
        AutoModelForAudioClassification,
    )
    model_id = "superb/wav2vec2-base-superb-er"
    extractor = AutoFeatureExtractor.from_pretrained(
        model_id,
        local_files_only=True,
    )
    model = AutoModelForAudioClassification.from_pretrained(
        model_id,
        local_files_only=True,
    )
    model.to("cpu")
    model.eval()
    return model, extractor

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

    # TEMPORARILY DISABLED:
    # The old pretrained English SER model requires
    # model files that are unavailable locally.
    #
    # Our Sinhala-English SER model will be connected
    # here later, using the SAME customer segments.

    emotion_predictions = []

    return (
        turns,
        timeline,
        features,
        emotion_predictions,
    )




def render_voice():
    render_voice_metadata()
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
    identity = upload_identity
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
            evidence = st.session_state.get("role_scores", {})
            # Explain how the roles were suggested
            if isinstance(evidence, dict) and evidence.get("explanation"):
                st.info(evidence["explanation"])
            # Display the diarization results
            st.dataframe(
                rows,
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
                    index=speaker_ids.index(suggested_agent),
                    key="review_agent_speaker",
                )
                # The other speaker is automatically the customer
                selected_customer = next(
                    speaker
                    for speaker in speaker_ids
                    if speaker != selected_agent
                )
                st.write(f"**Agent:** {selected_agent}")
                st.write(f"**Customer:** {selected_customer}")
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
                        st.caption(f"Segment {index + 1}: {start:.1f}s–{end:.1f}s — {row['Detected Speaker']}")
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

            # TEMPORARY DEBUG — check customer segments
            customer_rows = [
                row
                for row in verified_turns
                if str(
                    row.get("Verified Role", "")
                ).strip().casefold() == "customer"
            ]

            st.write(
                "DEBUG — Total verified turns:",
                len(verified_turns),
            )
            st.write(
                "DEBUG — Customer turns:",
                len(customer_rows),
            )

            if customer_rows:
                st.dataframe(
                    customer_rows,
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.warning(
                    "No turns are currently marked as Customer."
                )

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
                            "turns": turns,
                            "timeline": timeline,
                            "acoustic_features": features,
                            "analysis_seconds": (
                                time.perf_counter() - start_time
                            ),
                            "temporal_emotion": temporal_emotion,
                            "emotion_predictions": emotion_predictions,
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
        st.subheader("Speaker Timeline")
        speaker_df = pd.DataFrame([
            {
                "Start (s)": turn.start_seconds,
                "End (s)": turn.end_seconds,
                "Speaker": turn.speaker_id,
                "Role": turn.role,
            }
            for turn in results["turns"]
        ])
        st.dataframe(speaker_df, width="stretch", hide_index=True)
        st.caption(f"Analysis time (cached if repeated): {results['analysis_seconds']:.2f} seconds")
        st.subheader("Customer Vocal Energy Over Time")
        energy_df = pd.DataFrame([
            {
                "Time (s)": (point.start_seconds + point.end_seconds) / 2,
                "RMS Energy": point.rms_energy,
            }
            for point in results["timeline"]
        ])
        if not energy_df.empty:
            st.line_chart(energy_df.set_index("Time (s)"))
        else:
            st.warning("No customer speech segments were detected. Review the roles.")
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
                st.line_chart(pitch_df.set_index("Start (s)"))
            else:
                st.info("No usable pitch estimates for these segments.")
            st.caption(
                "Acoustic measurements are emotion-related evidence, not validated "
                "emotion labels. Speaker identification may also contain errors."
            )
        else:
            st.info("No customer acoustic features available. Check speaker roles and audio length.")
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
                ]
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
        st.subheader("Customer Speech Emotion Recognition")
        predictions = results.get("emotion_predictions", [])
        if predictions:
            emotion_df = pd.DataFrame([
                {
                    "Start (s)": round(p.start_seconds, 2),
                    "End (s)": round(p.end_seconds, 2),
                    "Emotion": p.emotion,
                    "Model Score": p.model_score,
                    "Uncertain": p.uncertain,
                    "Neutral": p.scores.get("neutral"),
                    "Happy": p.scores.get("happy"),
                    "Angry": p.scores.get("angry"),
                    "Sad": p.scores.get("sad"),
                }
                for p in predictions
            ])
            st.dataframe(
                emotion_df,
                width="stretch",
                hide_index=True,
            )
            st.subheader("Emotion Scores Over Time")
            chart_df = emotion_df[
                ["Start (s)", "Neutral", "Happy", "Angry", "Sad"]
            ].dropna()
            if not chart_df.empty:
                st.line_chart(
                    chart_df.set_index("Start (s)")
                )
            uncertain_count = sum(p.uncertain for p in predictions)
            st.caption(
                f"{uncertain_count} of {len(predictions)} "
                "segments flagged for review. "
                "Model scores are not calibrated probabilities."
            )
            st.warning(
                "Emotion predictions are exploratory because "
                "the pretrained model was trained on English speech, "
                "not validated Sinhala-English AMC calls."
            )
        else:
            st.info("No speech emotion predictions available.")



def render_amc():
    st.divider()
    st.header("AMC Customer & Decision Intelligence")

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
        profile = amc_service.get_customer_profile(customer_id)

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
    else:
        render_placeholder(page)
