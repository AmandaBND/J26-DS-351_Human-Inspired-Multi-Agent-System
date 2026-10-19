
import csv
import time
from pathlib import Path

from dotenv import load_dotenv

from src.agents.emotion_analysis import analyze_emotion


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DATASET_PATH = Path("research/emotion_dataset.csv")
OUTPUT_PATH = Path("research/day4_predictions.csv")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# READ DATASET
# ============================================================

with DATASET_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as file:
    complaints = list(csv.DictReader(file))

print(f"Loaded {len(complaints)} complaints.")

if not complaints:
    raise ValueError("The evaluation dataset is empty.")

if any(
    row.get("annotation_status") != "Reviewed"
    for row in complaints
):
    raise ValueError(
        "Some complaints are not marked Reviewed."
    )


# ============================================================
# LOAD PREVIOUS PREDICTIONS (RESUME SUPPORT)
# ============================================================

existing_predictions = {}

if OUTPUT_PATH.exists():

    with OUTPUT_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        for row in csv.DictReader(file):
            existing_predictions[row["complaint_id"]] = row

print(
    f"Existing predictions: {len(existing_predictions)}"
)


# ============================================================
# OUTPUT COLUMNS
# ============================================================

fieldnames = [
    "complaint_id",
    "complaint_text",
    "true_sentiment",
    "true_primary_emotion",
    "true_secondary_emotions",
    "true_intensity",
    "true_evidence",
    "pred_sentiment",
    "pred_primary_emotion",
    "pred_secondary_emotions",
    "pred_intensity",
    "pred_emotion_score",
    "pred_evidence",
    "pred_triggers",
    "pred_explanation",
    "error",
]


# ============================================================
# RUN AGENT
# ============================================================

for index, complaint in enumerate(complaints, start=1):

    complaint_id = complaint["complaint_id"]

    if (
        complaint_id in existing_predictions
        and not existing_predictions[complaint_id].get("error")
    ):
        print(
            f"[{index}/{len(complaints)}] "
            f"{complaint_id}: Already completed"
        )
        continue

    print(
        f"[{index}/{len(complaints)}] "
        f"Analyzing {complaint_id}..."
    )

    result_row = {
        "complaint_id": complaint_id,
        "complaint_text": complaint["complaint_text"],
        "true_sentiment": complaint["sentiment_label"],
        "true_primary_emotion": (
            complaint["primary_emotion_label"]
        ),
        "true_secondary_emotions": (
            complaint["secondary_emotions_label"]
        ),
        "true_intensity": complaint["intensity_label"],
        "true_evidence": complaint["evidence_label"],
        "pred_sentiment": "",
        "pred_primary_emotion": "",
        "pred_secondary_emotions": "",
        "pred_intensity": "",
        "pred_emotion_score": "",
        "pred_evidence": "",
        "pred_triggers": "",
        "pred_explanation": "",
        "error": "",
    }

    try:

        result = analyze_emotion(
            complaint["complaint_text"]
        )

        # Support Pydantic result or dictionary result
        if hasattr(result, "model_dump"):
            prediction = result.model_dump(mode="json")
        elif isinstance(result, dict):
            prediction = result
        else:
            raise TypeError(
                f"Unexpected result type: {type(result)}"
            )

        result_row["pred_sentiment"] = (
            prediction.get("sentiment", "")
        )

        result_row["pred_primary_emotion"] = (
            prediction.get("primary_emotion", "")
        )

        result_row["pred_secondary_emotions"] = (
            "; ".join(
                prediction.get("secondary_emotions") or []
            )
        )

        result_row["pred_intensity"] = (
            prediction.get("emotion_intensity", "")
        )

        result_row["pred_emotion_score"] = (
            prediction.get("emotion_score", "")
        )

        result_row["pred_evidence"] = (
            "; ".join(
                prediction.get("emotion_evidence") or []
            )
        )

        result_row["pred_triggers"] = (
            "; ".join(
                prediction.get("emotion_triggers") or []
            )
        )

        result_row["pred_explanation"] = (
            prediction.get("explanation", "")
        )

        print(
            "  Prediction:",
            result_row["pred_primary_emotion"],
            "|",
            result_row["pred_intensity"],
        )

    except Exception as exc:

        result_row["error"] = str(exc)

        print(f"  ERROR: {exc}")

    existing_predictions[complaint_id] = result_row

    # Save after every complaint to avoid losing progress
    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in complaints:
            saved = existing_predictions.get(
                row["complaint_id"]
            )

            if saved:
                writer.writerow(saved)

    time.sleep(0.3)


# ============================================================
# FINAL SUMMARY
# ============================================================

successful = sum(
    1
    for row in existing_predictions.values()
    if not row.get("error")
)

failed = sum(
    1
    for row in existing_predictions.values()
    if row.get("error")
)

print("\n======================================")
print("DAY 4 - PREDICTION SUMMARY")
print("======================================")
print(f"Total complaints : {len(complaints)}")
print(f"Successful       : {successful}")
print(f"Failed           : {failed}")
print(f"Output file      : {OUTPUT_PATH}")
print("======================================")
