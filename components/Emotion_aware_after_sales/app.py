from pathlib import Path
import hashlib
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
from emotion_aware_after_sales.services.sinhala_asr_service import (
    SinhalaASRService,
)
from emotion_aware_after_sales.services.amc_vocabulary_normalizer import (
    AMCVocabularyNormalizer,
)
from emotion_aware_after_sales.services.diarization_service import (
    DiarizationService,
    SpeakerTurn,
)

from emotion_aware_after_sales.services.diarized_transcription_service import (
    DiarizedTranscriptionService,
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

@st.cache_resource
def load_sinhala_asr_model():
    return SinhalaASRService()

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
def run_cached_sinhala_transcription(audio_bytes, filename):
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / Path(filename).name
        audio_path.write_bytes(audio_bytes)

        audio = AudioPreprocessingPipeline().process(audio_path)

        segments = load_sinhala_asr_model().transcribe(
            samples=audio.samples,
            sample_rate=audio.sample_rate,
            chunk_seconds=20,
        )

    vocabulary_path = (
        Path(__file__).resolve().parent
        / "config"
        / "amc_vocabulary.json"
    )

    normalizer = AMCVocabularyNormalizer(vocabulary_path)

    results = []

    for segment in segments:
        normalized = normalizer.normalize(segment.raw_text)

        results.append(
            {
                "start_seconds": segment.start_seconds,
                "end_seconds": segment.end_seconds,
                "raw_text": segment.raw_text,
                "normalized_text": normalized.normalized_text,
                "corrections": [
                    {
                        "original": item.original,
                        "replacement": item.replacement,
                    }
                    for item in normalized.corrections
                ],
                "review_suggestions": [
                    {
                        "original": item.original,
                        "suggested_replacement": (
                            item.suggested_replacement
                        ),
                    }
                    for item in normalized.suggestions
                ],
            }
        )

    return results

@st.cache_data(show_spinner=False)
def run_cached_diarized_transcription(
    audio_bytes,
    filename,
    agent_speaker_id,
):
    with tempfile.TemporaryDirectory() as temp_dir:
        audio_path = Path(temp_dir) / Path(filename).name
        audio_path.write_bytes(audio_bytes)

        audio = AudioPreprocessingPipeline().process(audio_path)

    # Reuse cached speaker detection instead of running pyannote again.
    cached_turns = run_cached_diarization(audio_bytes, filename)

    speaker_turns = []

    for start, end, speaker_id in cached_turns:
        role = (
            "agent"
            if speaker_id == agent_speaker_id
            else "customer"
        )

        speaker_turns.append(
            SpeakerTurn(
                start_seconds=start,
                end_seconds=end,
                speaker_id=speaker_id,
                role=role,
            )
        )

    service = DiarizedTranscriptionService(
        asr_service=load_sinhala_asr_model()
    )

    results = service.transcribe(
        samples=audio.samples,
        sample_rate=audio.sample_rate,
        speaker_turns=speaker_turns,
    )

    vocabulary_path = (
        Path(__file__).resolve().parent
        / "config"
        / "amc_vocabulary.json"
    )
    normalizer = AMCVocabularyNormalizer(vocabulary_path)

    output = []

    for turn in results:
        normalized = normalizer.normalize(turn.raw_text)

        output.append(
            {
                "start_seconds": turn.start_seconds,
                "end_seconds": turn.end_seconds,
                "speaker_id": turn.speaker_id,
                "role": turn.role,
                "raw_text": turn.raw_text,
                "normalized_text": normalized.normalized_text,
                "review_suggestions": [
                    {
                        "original": suggestion.original,
                        "replacement": suggestion.suggested_replacement,
                    }
                    for suggestion in normalized.suggestions
                ],
            }
        )

    return output

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

# Clear upload-dependent results even when a new file has the same name.
upload_identity = (
    (uploaded_file.name, hashlib.sha256(uploaded_file.getvalue()).hexdigest())
    if uploaded_file is not None
    else None
)
if st.session_state.get("active_upload_identity") != upload_identity:
    for key in (
        "analysis_results", "sinhala_results", "diarized_results",
        "selected_agent_speaker", "active_agent_speaker",
    ):
        st.session_state.pop(key, None)
    st.session_state["active_upload_identity"] = upload_identity

if uploaded_file is not None:
    st.audio(uploaded_file)

    st.info(
        "For this first prototype, the recording must contain "
        "two speakers. Confirm their roles before analysis."
    )

    agent_speaker = st.selectbox(
        "Which detected speaker is the service agent?",
        ["SPEAKER_00", "SPEAKER_01"],
        key="selected_agent_speaker",
    )

    # Role-dependent results must match the current speaker selection.
    if st.session_state.get("active_agent_speaker") != agent_speaker:
        st.session_state.pop("analysis_results", None)
        st.session_state.pop("diarized_results", None)
        st.session_state["active_agent_speaker"] = agent_speaker

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
            "Use Generate Diarized Transcript below for speaker-level alignment."
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


# Run Sinhala ASR separately from diarization.
if uploaded_file is not None:
    st.subheader("Sinhala Call Transcription")

    if st.button("Transcribe in Sinhala", key="sinhala_asr_button"):
        with st.spinner(
            "Transcribing Sinhala audio. This may take a few minutes..."
        ):
            sinhala_results = run_cached_sinhala_transcription(
                uploaded_file.getvalue(),
                uploaded_file.name,
            )

        st.session_state["sinhala_results"] = sinhala_results

    if "sinhala_results" in st.session_state:
        for segment in st.session_state["sinhala_results"]:
            st.markdown(
                f"**[{segment['start_seconds']:.1f}s – "
                f"{segment['end_seconds']:.1f}s]**"
            )

            st.write(segment["normalized_text"])

            with st.expander("Raw transcript and vocabulary review"):
                st.write("**Raw transcription:**")
                st.write(segment["raw_text"])

                for correction in segment["corrections"]:
                    st.write(
                        f"Corrected: {correction['original']} "
                        f"→ {correction['replacement']}"
                    )

                for suggestion in segment["review_suggestions"]:
                    st.warning(
                        f"Review: {suggestion['original']} "
                        f"→ {suggestion['suggested_replacement']}"
                    )

if uploaded_file is not None:
    st.subheader("Diarized Sinhala Transcription")

    if st.button(
        "Generate Diarized Transcript",
        key="diarized_transcript_button",
    ):
        with st.spinner(
            "Matching Sinhala speech to speakers..."
        ):
            diarized_results = run_cached_diarized_transcription(
                uploaded_file.getvalue(),
                uploaded_file.name,
                agent_speaker,
            )

            st.session_state["diarized_results"] = diarized_results

    if "diarized_results" in st.session_state:
        for turn in st.session_state["diarized_results"]:
            speaker_label = (
                "Service Agent"
                if turn["role"] == "agent"
                else "Customer"
            )

            st.markdown(
                f"**{speaker_label} — {turn['speaker_id']}** "
                f"({turn['start_seconds']:.1f}s – "
                f"{turn['end_seconds']:.1f}s)"
            )

            st.write(turn["normalized_text"])

            with st.expander("Raw text and vocabulary review"):
                st.write(turn["raw_text"])

                for suggestion in turn["review_suggestions"]:
                    st.warning(
                        f"{suggestion['original']} "
                        f"→ {suggestion['replacement']} "
                        "(review required)"
                    )
