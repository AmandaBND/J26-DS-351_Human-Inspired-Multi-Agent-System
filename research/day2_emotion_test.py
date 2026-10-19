
import csv
from pathlib import Path

from src.agents.emotion_analysis import analyze_emotion


COMPLAINTS = [
    (
        "C001",
        "My printer has not worked for three days. "
        "I have called repeatedly and I am extremely frustrated."
    ),
    (
        "C002",
        "My printer shows error code E03. "
        "Please arrange a technician."
    ),
    (
        "C003",
        "I am worried that this breakdown "
        "will delay our customer invoices."
    ),
    (
        "C004",
        "Thank you for resolving our printer issue. "
        "I am very satisfied with the service."
    ),
    (
        "C005",
        "I am disappointed that nobody has updated me "
        "about the repair."
    ),
    (
        "C006",
        "I am extremely frustrated because I have "
        "contacted your service team several times. "
        "I am also disappointed with the lack of response."
    ),
]


rows = []

for complaint_id, complaint_text in COMPLAINTS:

    print("\n" + "=" * 60)
    print(f"COMPLAINT: {complaint_id}")
    print("=" * 60)

    try:
        result = analyze_emotion(complaint_text)

        print("Sentiment:", result.sentiment)
        print("Primary Emotion:", result.primary_emotion)
        print("Secondary Emotions:", result.secondary_emotions)
        print("Intensity:", result.emotion_intensity)
        print("Score:", result.emotion_score)
        print("Evidence:", result.emotion_evidence)
        print("Triggers:", result.emotion_triggers)
        print("Explanation:", result.explanation)

        rows.append({
            "complaint_id": complaint_id,
            "sentiment": result.sentiment,
            "primary_emotion": result.primary_emotion,
            "secondary_emotions": "; ".join(
                result.secondary_emotions
            ),
            "emotion_intensity": result.emotion_intensity,
            "emotion_score": result.emotion_score,
            "emotion_evidence": "; ".join(
                result.emotion_evidence
            ),
            "emotion_triggers": "; ".join(
                result.emotion_triggers
            ),
            "explanation": result.explanation,
            "error": "",
        })

    except Exception as exc:
        print("ERROR:", exc)

        rows.append({
            "complaint_id": complaint_id,
            "sentiment": "",
            "primary_emotion": "",
            "secondary_emotions": "",
            "emotion_intensity": "",
            "emotion_score": "",
            "emotion_evidence": "",
            "emotion_triggers": "",
            "explanation": "",
            "error": str(exc),
        })


output = Path("research/day2_emotion_results.csv")

with output.open(
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=list(rows[0].keys()),
    )

    writer.writeheader()
    writer.writerows(rows)


successful = sum(
    1 for row in rows if not row["error"]
)

print("\n" + "=" * 60)
print("DAY 2 EMOTION ANALYSIS SUMMARY")
print("=" * 60)
print("Total Complaints:", len(rows))
print("Successful:", successful)
print("Failed:", len(rows) - successful)
print("Results:", output)
