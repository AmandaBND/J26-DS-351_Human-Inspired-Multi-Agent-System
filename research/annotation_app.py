
from pathlib import Path

import pandas as pd
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

DATASET = Path("research/emotion_dataset.csv")

EMOTIONS = [
    "Neutral",
    "Anger",
    "Frustration",
    "Disappointment",
    "Concern",
    "Sadness",
    "Satisfaction",
    "Other",
]

SENTIMENTS = [
    "Neutral",
    "Negative",
    "Positive",
    "Mixed",
]

INTENSITIES = [
    "Low",
    "Medium",
    "High",
]


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Customer Emotion Annotation",
    page_icon="🧠",
    layout="wide",
)

st.title("Customer Emotion Dataset Annotation")

st.caption(
    "Metropolitan Technologies | "
    "Customer Complaint Handling Research | PP1"
)


# ============================================================
# DATABASE / CSV FUNCTIONS
# ============================================================

def load_data():
    return pd.read_csv(
        DATASET,
        encoding="utf-8-sig",
        keep_default_na=False,
    )


def save_data(df):
    df.to_csv(
        DATASET,
        index=False,
        encoding="utf-8-sig",
    )


def get_next_pending(df, current_id=None):

    pending = df.loc[
        df["annotation_status"] != "Reviewed",
        "complaint_id",
    ].tolist()

    if not pending:
        return None

    all_ids = df["complaint_id"].tolist()

    if current_id in all_ids:
        current_index = all_ids.index(current_id)

        for complaint_id in all_ids[current_index + 1:]:
            if complaint_id in pending:
                return complaint_id

    return pending[0]


def existing_index(options, value):

    if value in options:
        return options.index(value)

    return 0


# ============================================================
# VALIDATE DATASET
# ============================================================

if not DATASET.exists():
    st.error(
        f"Dataset not found: {DATASET}"
    )
    st.stop()

df = load_data()

if df.empty:
    st.warning("Dataset is empty.")
    st.stop()

required_columns = [
    "complaint_id",
    "complaint_text",
    "scenario",
    "sentiment_label",
    "primary_emotion_label",
    "secondary_emotions_label",
    "intensity_label",
    "evidence_label",
    "annotation_status",
]

missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(
        f"Missing dataset columns: {missing_columns}"
    )
    st.stop()


# ============================================================
# SESSION STATE - BEFORE WIDGET CREATION
# ============================================================

all_ids = df["complaint_id"].tolist()

pending_ids = df.loc[
    df["annotation_status"] != "Reviewed",
    "complaint_id",
].tolist()


# Apply next selection BEFORE creating selectbox
if "next_selected_id" in st.session_state:

    next_id = st.session_state.pop(
        "next_selected_id"
    )

    if next_id in all_ids:
        st.session_state["selected_id"] = next_id


# Initialize selected complaint
if (
    "selected_id" not in st.session_state
    or st.session_state["selected_id"] not in all_ids
):

    st.session_state["selected_id"] = (
        pending_ids[0]
        if pending_ids
        else all_ids[0]
    )


# ============================================================
# PROGRESS DASHBOARD
# ============================================================

total = len(df)

reviewed = int(
    (df["annotation_status"] == "Reviewed").sum()
)

pending = total - reviewed

c1, c2, c3 = st.columns(3)

c1.metric("Total Complaints", total)
c2.metric("Reviewed", reviewed)
c3.metric("Pending", pending)

st.progress(
    reviewed / total if total else 0
)

if pending == 0:
    st.success(
        "All complaints have been annotated!"
    )


# ============================================================
# DATASET OVERVIEW
# ============================================================

st.divider()

st.subheader("Dataset Overview")

st.dataframe(
    df[
        [
            "complaint_id",
            "scenario",
            "primary_emotion_label",
            "annotation_status",
        ]
    ],
    width="stretch",
    hide_index=True,
)


# ============================================================
# COMPLAINT SELECTION
# ============================================================

st.divider()

st.subheader("Annotate Complaint")

selected_id = st.selectbox(
    "Select Complaint",
    all_ids,
    key="selected_id",
)

matching_rows = df.index[
    df["complaint_id"] == selected_id
]

if len(matching_rows) == 0:
    st.error("Complaint not found.")
    st.stop()

idx = matching_rows[0]

record = df.loc[idx]

st.markdown(
    f"### {record['complaint_id']}"
)

st.info(
    record["complaint_text"]
)

st.caption(
    f"Scenario: {record['scenario']}"
)

if record["annotation_status"] == "Reviewed":
    st.success(
        "This complaint has already been reviewed. "
        "You can update its annotation if needed."
    )
else:
    st.warning(
        "This complaint is pending annotation."
    )


# ============================================================
# ANNOTATION FORM
# ============================================================

# A unique form key for each complaint ensures that
# switching complaints does not reuse old widget values.

form_key = f"annotation_form_{selected_id}"

existing_secondary = [
    item.strip()
    for item in record["secondary_emotions_label"].split(";")
    if item.strip() in EMOTIONS
    and item.strip() != "Neutral"
]


with st.form(form_key):

    left, right = st.columns(2)

    with left:

        sentiment = st.selectbox(
            "Sentiment",
            SENTIMENTS,
            index=existing_index(
                SENTIMENTS,
                record["sentiment_label"],
            ),
            key=f"sentiment_{selected_id}",
        )

        primary = st.selectbox(
            "Primary Emotion",
            EMOTIONS,
            index=existing_index(
                EMOTIONS,
                record["primary_emotion_label"],
            ),
            key=f"primary_{selected_id}",
        )

    with right:

        intensity = st.selectbox(
            "Emotion Intensity",
            INTENSITIES,
            index=existing_index(
                INTENSITIES,
                record["intensity_label"],
            ),
            key=f"intensity_{selected_id}",
        )

        secondary = st.multiselect(
            "Secondary Emotions",
            EMOTIONS[1:],
            default=existing_secondary,
            key=f"secondary_{selected_id}",
        )

    evidence = st.text_area(
        "Exact Emotion Evidence",
        value=record["evidence_label"],
        placeholder=(
            "Copy exact phrases from the complaint. "
            "Separate multiple phrases with semicolons."
        ),
        height=100,
        key=f"evidence_{selected_id}",
    )

    st.caption(
        "Use exact text from the complaint. "
        "Leave blank for neutral factual requests."
    )

    save = st.form_submit_button(
        "Save & Next",
        type="primary",
        width="stretch",
    )


# ============================================================
# SAVE ANNOTATION
# ============================================================

if save:

    evidence_phrases = [
        phrase.strip()
        for phrase in evidence.split(";")
        if phrase.strip()
    ]

    invalid_evidence = [
        phrase
        for phrase in evidence_phrases
        if phrase not in record["complaint_text"]
    ]

    errors = []

    if invalid_evidence:
        errors.append(
            "Evidence phrases must exactly match "
            f"the complaint: {invalid_evidence}"
        )

    if primary in secondary:
        errors.append(
            "Primary emotion cannot also appear "
            "as a secondary emotion."
        )

    if primary == "Neutral":

        if secondary:
            errors.append(
                "Neutral complaints cannot have "
                "secondary emotions."
            )

        if intensity != "Low":
            errors.append(
                "Neutral complaints must have "
                "Low emotional intensity."
            )

        if evidence_phrases:
            errors.append(
                "Neutral complaints should not "
                "contain emotional evidence."
            )

    if errors:

        for error in errors:
            st.error(error)

    else:

        df.at[idx, "sentiment_label"] = sentiment

        df.at[idx, "primary_emotion_label"] = primary

        df.at[idx, "secondary_emotions_label"] = (
            "; ".join(secondary)
        )

        df.at[idx, "intensity_label"] = intensity

        df.at[idx, "evidence_label"] = (
            "; ".join(evidence_phrases)
        )

        df.at[idx, "annotation_status"] = "Reviewed"

        save_data(df)

        next_id = get_next_pending(
            df,
            current_id=selected_id,
        )

        if next_id is not None:
            st.session_state["next_selected_id"] = next_id

        st.rerun()


# ============================================================
# BULK REVIEW - FIRST 10 NEUTRAL COMPLAINTS
# ============================================================

st.divider()

st.subheader("Bulk Review: Neutral Complaints")

st.caption(
    "This option is only for EMO001–EMO010. "
    "Review their text before applying labels."
)

confirm_bulk = st.checkbox(
    "I have independently reviewed EMO001–EMO010 "
    "and confirm they contain no expressed emotion."
)

if st.button(
    "Apply Neutral Labels to First 10",
    disabled=not confirm_bulk,
):

    neutral_ids = [
        f"EMO{i:03d}"
        for i in range(1, 11)
    ]

    mask = (
        df["complaint_id"].isin(neutral_ids)
        & (df["annotation_status"] != "Reviewed")
    )

    df.loc[mask, "sentiment_label"] = "Neutral"
    df.loc[mask, "primary_emotion_label"] = "Neutral"
    df.loc[mask, "secondary_emotions_label"] = ""
    df.loc[mask, "intensity_label"] = "Low"
    df.loc[mask, "evidence_label"] = ""
    df.loc[mask, "annotation_status"] = "Reviewed"

    save_data(df)

    next_id = get_next_pending(df)

    if next_id is not None:
        st.session_state["next_selected_id"] = next_id

    st.rerun()


# ============================================================
# DATASET DOWNLOAD
# ============================================================

st.divider()

st.subheader("Export Annotations")

csv_data = df.to_csv(
    index=False
).encode("utf-8-sig")

st.download_button(
    "Download Annotated Dataset",
    data=csv_data,
    file_name="emotion_dataset_annotated.csv",
    mime="text/csv",
    width="stretch",
)
