
import csv
from pathlib import Path


DATASET_PATH = Path("research/emotion_dataset.csv")

EMOTIONS = [
    "Anger",
    "Frustration",
    "Disappointment",
    "Concern",
    "Sadness",
    "Satisfaction",
    "Neutral",
    "Other",
]

SENTIMENTS = [
    "Positive",
    "Neutral",
    "Negative",
    "Mixed",
]

INTENSITIES = [
    "Low",
    "Medium",
    "High",
]


def choose_option(label, options):
    while True:
        print(f"\n{label}")

        for index, option in enumerate(options, start=1):
            print(f"  {index}. {option}")

        choice = input("Choose number: ").strip()

        if choice.isdigit():
            index = int(choice) - 1

            if 0 <= index < len(options):
                return options[index]

        print("Invalid selection. Try again.")


def annotate():
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    with DATASET_PATH.open(
        "r",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not fieldnames:
        raise ValueError("Dataset has no column headers.")

    for row in rows:
        if row["annotation_status"] == "Reviewed":
            continue

        print("\n" + "=" * 65)
        print("Complaint ID:", row["complaint_id"])
        print("Scenario:", row["scenario"])
        print("Complaint:", row["complaint_text"])
        print("=" * 65)

        action = input(
            "\nPress Enter to annotate, "
            "'s' to skip, or 'q' to quit: "
        ).strip().lower()

        if action == "q":
            break

        if action == "s":
            continue

        sentiment = choose_option(
            "Select sentiment:",
            SENTIMENTS,
        )

        primary = choose_option(
            "Select primary emotion:",
            EMOTIONS,
        )

        secondary = []

        if primary != "Neutral":
            while True:
                print(
                    "\nSecondary emotions:",
                    ", ".join(EMOTIONS),
                )

                value = input(
                    "Enter secondary emotion "
                    "(blank if none): "
                ).strip()

                if not value:
                    break

                if (
                    value in EMOTIONS
                    and value != primary
                    and value != "Neutral"
                    and value not in secondary
                ):
                    secondary.append(value)
                else:
                    print("Invalid or duplicate emotion.")

        intensity = choose_option(
            "Select emotion intensity:",
            INTENSITIES,
        )

        evidence = input(
            "\nEnter exact evidence phrases "
            "separated by semicolons "
            "(blank if none): "
        ).strip()

        evidence_phrases = [
            phrase.strip()
            for phrase in evidence.split(";")
            if phrase.strip()
        ]

        invalid = [
            phrase
            for phrase in evidence_phrases
            if phrase not in row["complaint_text"]
        ]

        if invalid:
            print(
                "Evidence must match complaint text exactly."
            )
            print("Invalid phrases:", invalid)
            print("This record remains Pending.")
            continue

        print("\nAnnotation summary:")
        print("Sentiment:", sentiment)
        print("Primary:", primary)
        print("Secondary:", secondary)
        print("Intensity:", intensity)
        print("Evidence:", evidence_phrases)

        confirm = input(
            "\nConfirm annotation? (y/n): "
        ).strip().lower()

        if confirm != "y":
            print("Annotation not saved.")
            continue

        row["sentiment_label"] = sentiment
        row["primary_emotion_label"] = primary
        row["secondary_emotions_label"] = "; ".join(
            secondary
        )
        row["intensity_label"] = intensity
        row["evidence_label"] = "; ".join(
            evidence_phrases
        )
        row["annotation_status"] = "Reviewed"

        # Save after each confirmed annotation.
        with DATASET_PATH.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
            writer.writeheader()
            writer.writerows(rows)

        print("Annotation saved successfully!")

    reviewed = sum(
        row["annotation_status"] == "Reviewed"
        for row in rows
    )

    print("\n" + "=" * 65)
    print("ANNOTATION PROGRESS")
    print("=" * 65)
    print("Total:", len(rows))
    print("Reviewed:", reviewed)
    print("Pending:", len(rows) - reviewed)


if __name__ == "__main__":
    annotate()
