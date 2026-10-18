
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



st.set_page_config(page_title="Emotion-Aware AMC Decision Intelligence", layout="wide")
st.title("Emotion-Aware After-Sales Service")
st.caption("AMC call research prototype — automatic speaker roles and customer acoustic evidence")


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


@st.cache_data(show_spinner=False)
def run_cached_role_identification(
    audio_bytes: bytes, filename: str, reference_bytes: bytes, reference_filename: str
):
    call_audio = preprocess_bytes(audio_bytes, filename)
    reference_audio = preprocess_bytes(reference_bytes, reference_filename)
    speaker_turns = [
        SpeakerTurn(start_seconds=start, end_seconds=end, speaker_id=speaker)
        for start, end, speaker in run_cached_diarization(audio_bytes, filename)
    ]
    service = AutomaticRoleIdentificationService(model=load_role_identification_model())
    return service.identify(
        samples=call_audio.samples,
        sample_rate=call_audio.sample_rate,
        speaker_turns=speaker_turns,
        agent_reference_samples=reference_audio.samples,
        agent_reference_sample_rate=reference_audio.sample_rate,
    )


@st.cache_data(show_spinner=False)
def run_cached_acoustic_analysis(audio_bytes: bytes, filename: str, role_rows: tuple):
    """Cache by audio AND reviewed roles, so manual corrections are respected."""
    audio = preprocess_bytes(audio_bytes, filename)
    turns = [
        SpeakerTurn(
            start_seconds=float(start),
            end_seconds=float(end),
            speaker_id=str(speaker),
            role=str(role),
        )
        for start, end, speaker, role in role_rows
    ]
    customer_segments = CustomerAudioService().extract_customer_segments(
        samples=audio.samples, sample_rate=audio.sample_rate, speaker_turns=turns
    )
    timeline = TemporalAcousticService().analyze(customer_segments)
    features = EmotionAcousticFeaturesService().analyze(customer_segments)
    return turns, timeline, features


uploaded_file = st.file_uploader(
    "Upload a customer-service call",
    type=["wav", "mp3", "m4a", "mp4", "amr", "3gp"],
    key="customer_call_audio",
)
agent_reference_file = st.file_uploader(
    "Upload service agent reference voice (10–20 seconds)",
    type=["wav", "mp3", "m4a", "mp4"],
    key="agent_reference_audio",
)

upload_identity = (
    (uploaded_file.name, hashlib.sha256(uploaded_file.getvalue()).hexdigest())
    if uploaded_file is not None else None
)
reference_identity = (
    (agent_reference_file.name, hashlib.sha256(agent_reference_file.getvalue()).hexdigest())
    if agent_reference_file is not None else None
)
identity = (upload_identity, reference_identity)
if st.session_state.get("active_audio_identity") != identity:
    for key in (
        "speaker_review_turns", "verified_speaker_turns", "speaker_role_editor",
        "analysis_results", "role_scores", "role_margin", "review_identity",
    ):
        st.session_state.pop(key, None)
    st.session_state["active_audio_identity"] = identity

if uploaded_file is not None:
    st.audio(uploaded_file)
if agent_reference_file is not None:
    st.caption("Service agent reference recording")
    st.audio(agent_reference_file)

if uploaded_file is not None:
    st.subheader("Automatic Speaker Identification")
    st.caption("Designed for a two-speaker call. A clean agent reference is required.")

    if st.button("Detect Speakers and Identify Roles", type="primary"):
        if agent_reference_file is None:
            st.warning("Upload the agent reference voice before identifying roles.")
        else:
            try:
                with st.spinner("Detecting speakers and matching the agent voice..."):
                    audio_bytes = uploaded_file.getvalue()
                    detected_turns = run_cached_diarization(audio_bytes, uploaded_file.name)
                    role_mapping, scores, margin = run_cached_role_identification(
                        audio_bytes, uploaded_file.name,
                        agent_reference_file.getvalue(), agent_reference_file.name,
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
                    st.session_state["speaker_review_turns"] = rows
                    st.session_state["verified_speaker_turns"] = [dict(row) for row in rows]
                    st.session_state["role_scores"] = scores
                    st.session_state["role_margin"] = margin
                    st.session_state.pop("speaker_role_editor", None)
                    st.session_state.pop("analysis_results", None)
                st.success("Automatic roles assigned. You can analyze immediately or edit them below.")
            except Exception as exc:
                st.error(f"Speaker identification failed: {exc}")
                st.exception(exc)

    if "speaker_review_turns" in st.session_state:
        st.write("Voice similarity scores:", st.session_state.get("role_scores", {}))
        margin = st.session_state.get("role_margin")
        if margin is not None:
            st.caption(f"Speaker similarity score margin: {margin:.3f} (not a calibrated confidence)")
            if margin < 0.10:
                st.warning("Close voice matches: review speaker roles before analysis.")

        st.subheader("Review Speaker Roles (Optional)")
        reviewed_df = st.data_editor(
            pd.DataFrame(st.session_state["speaker_review_turns"]),
            column_config={
                "Start (s)": st.column_config.NumberColumn(disabled=True),
                "End (s)": st.column_config.NumberColumn(disabled=True),
                "Detected Speaker": st.column_config.TextColumn(disabled=True),
                "Verified Role": st.column_config.SelectboxColumn(
                    options=["agent", "customer"], required=True
                ),
            },
            disabled=["Start (s)", "End (s)", "Detected Speaker"],
            hide_index=True,
            width="stretch",
            key="speaker_role_editor",
        )

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

        if st.button("Confirm Speaker Roles"):
            st.session_state["verified_speaker_turns"] = reviewed_df.to_dict("records")
            st.session_state.pop("analysis_results", None)
            st.success("Your corrected roles will be used for analysis.")

        if st.button("Analyze Call", type="primary"):
            verified_turns = st.session_state.get("verified_speaker_turns")
            if not verified_turns:
                st.warning("First click 'Detect Speakers and Identify Roles'.")
            else:
                try:
                    with st.spinner("Analyzing customer acoustic features..."):
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
                        turns, timeline, features = run_cached_acoustic_analysis(
                            uploaded_file.getvalue(), uploaded_file.name, role_rows
                        )
                        temporal_emotion = TemporalAcousticEmotionService().analyze(
                            features
                        )
                        elapsed = time.perf_counter() - start_time
                        st.session_state["analysis_results"] = {
                            "identity": identity,
                            "turns": turns,
                            "timeline": timeline,
                            "acoustic_features": features,
                            "analysis_seconds": elapsed,
                            "temporal_emotion": temporal_emotion,
                        }
                    st.success("Customer acoustic analysis completed.")
                except Exception as exc:
                    st.error(f"Analyze Call failed: {exc}")
                    st.exception(exc)

    results = st.session_state.get("analysis_results")
    if results is not None and results.get("identity") == identity:
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

        st.subheader("Customer Acoustic Emotion Evidence")
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

        
        st.subheader("Temporal Customer Vocal Activation")

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

