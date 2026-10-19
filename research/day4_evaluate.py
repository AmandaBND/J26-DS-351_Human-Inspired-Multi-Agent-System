
import csv
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    multilabel_confusion_matrix,
)
from sklearn.preprocessing import MultiLabelBinarizer


# ============================================================
# PATHS
# ============================================================

INPUT_PATH = Path("research/day4_predictions.csv")
REPORT_PATH = Path("research/day4_evaluation_report.txt")
DETAIL_PATH = Path("research/day4_error_analysis.csv")
CONFUSION_PATH = Path("research/day4_confusion_matrix.csv")


# ============================================================
# HELPERS
# ============================================================

def normalize(value):
    return str(value or "").strip()


def parse_emotions(value):
    return {
        emotion.strip()
        for emotion in normalize(value).split(";")
        if emotion.strip()
    }


def safe_divide(a, b):
    return a / b if b else 0.0


def percentage(value):
    return f"{value * 100:.2f}%"


# ============================================================
# LOAD PREDICTIONS
# ============================================================

with INPUT_PATH.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as file:
    rows = list(csv.DictReader(file))

if not rows:
    raise ValueError("No predictions found.")

failed = [
    row for row in rows
    if normalize(row.get("error"))
]

valid = [
    row for row in rows
    if not normalize(row.get("error"))
]

required = [
    "true_primary_emotion",
    "pred_primary_emotion",
    "true_intensity",
    "pred_intensity",
    "true_sentiment",
    "pred_sentiment",
]

for row in valid:
    for column in required:
        if not normalize(row.get(column)):
            raise ValueError(
                f"Missing {column} for {row['complaint_id']}"
            )

if not valid:
    raise ValueError("No successful predictions.")

print(f"Total records : {len(rows)}")
print(f"Evaluated     : {len(valid)}")
print(f"Failed        : {len(failed)}")


# ============================================================
# PRIMARY EMOTION EVALUATION
# ============================================================

y_true = [
    normalize(row["true_primary_emotion"])
    for row in valid
]

y_pred = [
    normalize(row["pred_primary_emotion"])
    for row in valid
]

labels = sorted(set(y_true) | set(y_pred))

primary_accuracy = accuracy_score(y_true, y_pred)

macro_precision = precision_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

macro_recall = recall_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

macro_f1 = f1_score(
    y_true,
    y_pred,
    average="macro",
    zero_division=0,
)

weighted_f1 = f1_score(
    y_true,
    y_pred,
    average="weighted",
    zero_division=0,
)

per_class_report = classification_report(
    y_true,
    y_pred,
    labels=labels,
    zero_division=0,
)


# ============================================================
# SENTIMENT AND INTENSITY
# ============================================================

sentiment_accuracy = accuracy_score(
    [normalize(r["true_sentiment"]) for r in valid],
    [normalize(r["pred_sentiment"]) for r in valid],
)

intensity_accuracy = accuracy_score(
    [normalize(r["true_intensity"]) for r in valid],
    [normalize(r["pred_intensity"]) for r in valid],
)


# ============================================================
# MULTI-LABEL EMOTION EVALUATION
# ============================================================

true_sets = []
pred_sets = []

for row in valid:

    true_emotions = {
        normalize(row["true_primary_emotion"])
    } | parse_emotions(
        row.get("true_secondary_emotions")
    )

    pred_emotions = {
        normalize(row["pred_primary_emotion"])
    } | parse_emotions(
        row.get("pred_secondary_emotions")
    )

    # Neutral represents absence of expressed emotion.
    true_emotions.discard("Neutral")
    pred_emotions.discard("Neutral")

    true_sets.append(true_emotions)
    pred_sets.append(pred_emotions)

emotion_classes = sorted(
    set().union(*true_sets, *pred_sets)
)

if emotion_classes:

    mlb = MultiLabelBinarizer(
        classes=emotion_classes
    )

    mlb.fit([emotion_classes])

    true_binary = mlb.transform(true_sets)
    pred_binary = mlb.transform(pred_sets)

    multilabel_micro_f1 = f1_score(
        true_binary,
        pred_binary,
        average="micro",
        zero_division=0,
    )

    multilabel_macro_f1 = f1_score(
        true_binary,
        pred_binary,
        average="macro",
        zero_division=0,
    )

    multilabel_exact_match = accuracy_score(
        true_binary,
        pred_binary,
    )

else:
    multilabel_micro_f1 = 0.0
    multilabel_macro_f1 = 0.0
    multilabel_exact_match = 1.0


# ============================================================
# EVIDENCE EVALUATION
# ============================================================

total_predicted_evidence = 0
valid_predicted_evidence = 0
evidence_rows = 0
evidence_exact_matches = 0

for row in valid:

    text = row["complaint_text"]

    predicted_phrases = [
        phrase.strip()
        for phrase in normalize(
            row.get("pred_evidence")
        ).split(";")
        if phrase.strip()
    ]

    reference_phrases = [
        phrase.strip()
        for phrase in normalize(
            row.get("true_evidence")
        ).split(";")
        if phrase.strip()
    ]

    for phrase in predicted_phrases:

        total_predicted_evidence += 1

        if phrase in text:
            valid_predicted_evidence += 1

    if reference_phrases:
        evidence_rows += 1

        if set(predicted_phrases) == set(reference_phrases):
            evidence_exact_matches += 1

evidence_validity = safe_divide(
    valid_predicted_evidence,
    total_predicted_evidence,
)

evidence_exact_match = safe_divide(
    evidence_exact_matches,
    evidence_rows,
)


# ============================================================
# ERROR ANALYSIS
# ============================================================

error_rows = []

for row, true_set, pred_set in zip(
    valid,
    true_sets,
    pred_sets,
):

    primary_correct = (
        normalize(row["true_primary_emotion"])
        == normalize(row["pred_primary_emotion"])
    )

    intensity_correct = (
        normalize(row["true_intensity"])
        == normalize(row["pred_intensity"])
    )

    multilabel_correct = true_set == pred_set

    if not (
        primary_correct
        and intensity_correct
        and multilabel_correct
    ):

        error_rows.append({
            "complaint_id": row["complaint_id"],
            "complaint_text": row["complaint_text"],
            "true_primary": row["true_primary_emotion"],
            "pred_primary": row["pred_primary_emotion"],
            "true_secondary": row["true_secondary_emotions"],
            "pred_secondary": row["pred_secondary_emotions"],
            "true_intensity": row["true_intensity"],
            "pred_intensity": row["pred_intensity"],
            "primary_correct": primary_correct,
            "intensity_correct": intensity_correct,
            "multilabel_correct": multilabel_correct,
        })

error_fields = [
    "complaint_id",
    "complaint_text",
    "true_primary",
    "pred_primary",
    "true_secondary",
    "pred_secondary",
    "true_intensity",
    "pred_intensity",
    "primary_correct",
    "intensity_correct",
    "multilabel_correct",
]

with DETAIL_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=error_fields,
    )

    writer.writeheader()
    writer.writerows(error_rows)


# ============================================================
# CONFUSION MATRIX
# ============================================================

matrix = confusion_matrix(
    y_true,
    y_pred,
    labels=labels,
)

with CONFUSION_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:

    writer = csv.writer(file)

    writer.writerow(["Actual / Predicted"] + labels)

    for label, counts in zip(labels, matrix):
        writer.writerow([label] + list(counts))


# ============================================================
# GENERATE REPORT
# ============================================================

report = f"""
===============================================
DAY 4 - CUSTOMER EMOTION AGENT EVALUATION
===============================================

Total Complaints       : {len(rows)}
Evaluated Complaints   : {len(valid)}
Failed Predictions     : {len(failed)}

PRIMARY EMOTION CLASSIFICATION
-----------------------------------------------
Accuracy               : {percentage(primary_accuracy)}
Macro Precision        : {percentage(macro_precision)}
Macro Recall           : {percentage(macro_recall)}
Macro F1-Score         : {percentage(macro_f1)}
Weighted F1-Score      : {percentage(weighted_f1)}

SENTIMENT AND INTENSITY
-----------------------------------------------
Sentiment Accuracy     : {percentage(sentiment_accuracy)}
Intensity Accuracy     : {percentage(intensity_accuracy)}

MULTI-LABEL EMOTION DETECTION
-----------------------------------------------
Micro F1-Score         : {percentage(multilabel_micro_f1)}
Macro F1-Score         : {percentage(multilabel_macro_f1)}
Exact Match Accuracy   : {percentage(multilabel_exact_match)}

EVIDENCE EXTRACTION
-----------------------------------------------
Evidence Validity      : {percentage(evidence_validity)}
Valid Evidence Phrases : {valid_predicted_evidence}/{total_predicted_evidence}
Evidence Exact Match   : {percentage(evidence_exact_match)}
Reference Evidence Rows: {evidence_rows}

ERROR ANALYSIS
-----------------------------------------------
Records With Errors    : {len(error_rows)}

PER-CLASS PERFORMANCE
-----------------------------------------------
{per_class_report}

===============================================
"""

REPORT_PATH.write_text(
    report,
    encoding="utf-8",
)

print(report)

print("Saved:")
print(f" - {REPORT_PATH}")
print(f" - {DETAIL_PATH}")
print(f" - {CONFUSION_PATH}")
