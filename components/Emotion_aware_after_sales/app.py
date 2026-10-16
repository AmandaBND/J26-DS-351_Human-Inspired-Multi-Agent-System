
from pathlib import Path
import tempfile
import time

import pandas as pd
import streamlit as st
import torch
from pyannote.audio import Pipeline

from emotion_aware_after_sales.services.audio_preprocessing_pipeline import (
    AudioPreprocessingPipeline,
)
from emotion_aware_after_sales.services.automatic_diarization_service import (
    AutomaticDiarizationService,
)
from emotion_aware_after_sales.services.customer_audio_service import (
    CustomerAudioService,
)
from emotion_aware_after_sales.services.temporal_acoustic_service import (
    TemporalAcousticService,
)
from emotion_aware_after_sales.services.whisper_backend import (
    WhisperBackend,
)
from emotion_aware_after_sales.services.transcription_service import (
    TranscriptionService,
)
from emotion_aware_after_sales.services.hybrid_normalization_service import (
    HybridNormalizationService,
)

st.set_page_config(
    page_title="Emotion-Aware AMC Decision Intelligence",
    layout="wide",
)

st.title("Emotion-Aware After-Sales Service")
st.caption("Sinhala AMC call analysis — research prototype")


@st.cache_resource
def load_diarization_model():
    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-community-1"
    )
    pipeline.to(torch.device("cpu"))
    return pipeline

@st.cache_resource
def load_whisper_model():
    return WhisperBackend(model_size="base")


@st.cache_data(show_spinner=False)
def run_cached_transcription(audio_bytes: bytes, filename: str):
    """Transcribe the complete call once and cache the result."""

    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / Path(filename).name
        input_path.write_bytes(audio_bytes)

        audio = AudioPreprocessingPipeline().process(input_path)

        transcription_service = TranscriptionService(
            backend=load_whisper_model()
        )

        transcription_result = transcription_service.transcribe_segment(
            samples=audio.samples,
            sample_rate=audio.sample_rate,
            start_seconds=0.0,
            end_seconds=audio.duration_seconds,
            language="si",
        )

        raw_text = transcription_result.text

        normalization = HybridNormalizationService().normalize(
            raw_text
        )

        return {
            "raw_text": raw_text,
            "normalized_text": normalization.normalized_text,
        }


@st.cache_data(show_spinner=False)
def run_cached_diarization(audio_bytes: bytes, filename: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / Path(filename).name
        input_path.write_bytes(audio_bytes)

        audio = AudioPreprocessingPipeline().process(input_path)

        diarization = AutomaticDiarizationService(
            pipeline=load_diarization_model()
        )

        turns = diarization.diarize(
            samples=audio.samples,
            sample_rate=audio.sample_rate,
            num_speakers=2,
        )

        return [
            (
                turn.start_seconds,
                turn.end_seconds,
                turn.speaker_id,
            )
            for turn in turns
        ]

uploaded_file = st.file_uploader(
    "Upload a customer-service call",
    type=["wav", "mp3", "m4a", "mp4", "amr", "3gp"],
)

if uploaded_file is not None:
    st.audio(uploaded_file)

    st.info(
        "For this first prototype, the recording must contain "
        "two speakers. Confirm their roles before analysis."
    )

    agent_speaker = st.selectbox(
        "Which detected speaker is the service agent?",
        ["SPEAKER_00", "SPEAKER_01"],
    )


    if st.button("Analyze Call"):
        with st.spinner("Analyzing call..."):
            audio_bytes = uploaded_file.getvalue()

            # First run performs diarization.
            # Later runs reuse cached speaker timestamps.
            start_time = time.perf_counter()

            cached_turns = run_cached_diarization(
                audio_bytes,
                uploaded_file.name,
            )

            diarization_seconds = (
                time.perf_counter() - start_time
            )

            # Reconstruct SpeakerTurn objects.
            from emotion_aware_after_sales.services.diarization_service import (
                DiarizationService,
                SpeakerTurn,
            )

            turns = [
                SpeakerTurn(
                    start_seconds=start,
                    end_seconds=end,
                    speaker_id=speaker,
                )
                for start, end, speaker in cached_turns
            ]

            customer_speaker = (
                "SPEAKER_01"
                if agent_speaker == "SPEAKER_00"
                else "SPEAKER_00"
            )

            turns = DiarizationService().assign_roles(
                turns,
                {
                    agent_speaker: "agent",
                    customer_speaker: "customer",
                },
            )

            # Preprocess audio for customer extraction.
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = (
                    Path(temp_dir) / Path(uploaded_file.name).name
                )
                input_path.write_bytes(audio_bytes)

                audio = AudioPreprocessingPipeline().process(
                    input_path
                )

            customer_segments = (
                CustomerAudioService().extract_customer_segments(
                    samples=audio.samples,
                    sample_rate=audio.sample_rate,
                    speaker_turns=turns,
                )
            )

            timeline = TemporalAcousticService().analyze(
                customer_segments
            )

            transcription_start = time.perf_counter()
            transcription_result = run_cached_transcription(
                audio_bytes,
                uploaded_file.name,
            )

            transcription_seconds = (
                time.perf_counter() - transcription_start
            )

            # Save results so they survive Streamlit reruns.
            st.session_state["analysis_results"] = {
                "filename": uploaded_file.name,
                "turns": turns,
                "timeline": timeline,
                "diarization_seconds": diarization_seconds,
                "transcription": transcription_result,
                "transcription_seconds": transcription_seconds,
            }

    # Display saved results outside the button condition.
    results = st.session_state.get("analysis_results")

    if results is not None and results["filename"] == uploaded_file.name:
        st.success("Call processing completed.")

        st.info(
            f"Diarization lookup time: "
            f"{results['diarization_seconds']:.2f} seconds"
        )

        st.subheader("Speaker Timeline")

        speaker_df = pd.DataFrame(
            [
                {
                    "Start (s)": turn.start_seconds,
                    "End (s)": turn.end_seconds,
                    "Speaker": turn.speaker_id,
                    "Role": turn.role,
                }
                for turn in results["turns"]
            ]
        )

        st.dataframe(
            speaker_df,
            use_container_width=True,
        )

        st.subheader("Customer Vocal Energy Over Time")

        energy_df = pd.DataFrame(
            [
                {
                    "Time (s)": (
                        point.start_seconds + point.end_seconds
                    ) / 2,
                    "RMS Energy": point.rms_energy,
                }
                for point in results["timeline"]
            ]
        )

        if not energy_df.empty:
            st.line_chart(
                energy_df.set_index("Time (s)")["RMS Energy"]
            )
        else:
            st.warning("No customer segments were detected.")


        st.subheader("Sinhala Call Transcription")

        st.caption(
            "Automatic transcription of the complete call. "
            "Speaker-level alignment has not been added yet."
        )

        st.write("**Raw Whisper transcript**")
        st.text_area(
            "Raw transcript",
            value=results["transcription"]["raw_text"],
            height=140,
            disabled=True,
        )

        st.write("**Normalized transcript**")
        st.text_area(
            "Normalized transcript",
            value=results["transcription"]["normalized_text"],
            height=140,
            disabled=True,
        )

        st.info(
            f"Transcription lookup time: "
            f"{results['transcription_seconds']:.2f} seconds"
        )


        st.caption(
            "RMS energy measures acoustic intensity, not emotion. "
            "Emotion inference and service-context reasoning "
            "will be added later."
        )
