
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
]


output_path = Path(
    "research/day1_baseline_results.csv"
)

output_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

rows = []


for complaint_id, text in COMPLAINTS:

    print(f"Analyzing {complaint_id}...")

    try:

        result = analyze_emotion(text)

        rows.append({
            "complaint_id": complaint_id,
            "complaint_text": text,
            "sentiment": result.sentiment,
            "primary_emotion": result.primary_emotion,
            "emotion_intensity": result.emotion_intensity,
            "emotion_score": result.emotion_score,
            "explanation": result.explanation,
            "error": "",
        })

        print(
            f"  Emotion: {result.primary_emotion}"
        )
        print(
            f"  Intensity: {result.emotion_intensity}"
        )
        print(
            f"  Score: {result.emotion_score}"
        )

    except Exception as exc:

        print(
            f"  ERROR: {exc}"
        )

        rows.append({
            "complaint_id": complaint_id,
            "complaint_text": text,
            "sentiment": "",
            "primary_emotion": "",
            "emotion_intensity": "",
            "emotion_score": "",
            "explanation": "",
            "error": str(exc),
        })


fieldnames = [
    "complaint_id",
    "complaint_text",
    "sentiment",
    "primary_emotion",
    "emotion_intensity",
    "emotion_score",
    "explanation",
    "error",
]


with output_path.open(
    "w",
    newline="",
    encoding="utf-8",
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames,
    )

    writer.writeheader()
    writer.writerows(rows)


success_count = sum(
    1 for row in rows if not row["error"]
)

print("\n" + "=" * 50)
print("DAY 1 BASELINE SUMMARY")
print("=" * 50)

print(f"Total Complaints: {len(rows)}")
print(f"Successful: {success_count}")
print(f"Failed: {len(rows) - success_count}")
print(f"Results Saved: {output_path}")
