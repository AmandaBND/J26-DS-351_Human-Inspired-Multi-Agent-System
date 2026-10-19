
from src.agents.emotion_analysis_v2 import analyze_emotion


# ============================================================
# TEST COMPLAINTS
# ============================================================

complaints = [
    {
        "id": "EMO020",
        "text": (
            "I expected better communication "
            "from your service department."
        ),
    },
    {
        "id": "EMO043",
        "text": (
            "I am worried about our pending invoices "
            "and frustrated by the slow technician response."
        ),
    },
    {
        "id": "EMO045",
        "text": (
            "I am concerned about the recurring fault "
            "and frustrated that it has not been fixed."
        ),
    },
    {
        "id": "EMO046",
        "text": (
            "I appreciate the technician's effort, "
            "but I am disappointed by the long waiting time."
        ),
    },
    {
        "id": "EMO051",
        "text": (
            "Although I am satisfied with the final repair, "
            "I am disappointed that the process took so long."
        ),
    },
    {
        "id": "NEUTRAL_TEST",
        "text": (
            "My printer displays error code E03. "
            "Please arrange a technician."
        ),
    },
]


# ============================================================
# RUN TESTS
# ============================================================

def main():

    print("=" * 65)
    print("CUSTOMER EMOTION ANALYSIS AGENT - VERSION 2")
    print("=" * 65)

    successful = 0
    failed = 0

    for index, complaint in enumerate(
        complaints,
        start=1,
    ):

        print("\n" + "=" * 65)
        print(
            f"TEST {index}/{len(complaints)} "
            f"- {complaint['id']}"
        )
        print("=" * 65)

        print("Complaint:")
        print(complaint["text"])

        try:

            result = analyze_emotion(
                complaint["text"]
            )

            print("\nRESULTS")
            print("-" * 65)

            print(
                "Sentiment:",
                result.sentiment,
            )

            print(
                "Primary Emotion:",
                result.primary_emotion,
            )

            print(
                "Secondary Emotions:",
                result.secondary_emotions,
            )

            print(
                "Emotion Intensity:",
                result.emotion_intensity,
            )

            print(
                "Emotion Score:",
                result.emotion_score,
            )

            print(
                "Emotion Evidence:",
                result.emotion_evidence,
            )

            print(
                "Emotion Triggers:",
                result.emotion_triggers,
            )

            print(
                "Explanation:",
                result.explanation,
            )

            successful += 1

        except Exception as exc:

            failed += 1

            print(
                f"\nERROR: {type(exc).__name__}: {exc}"
            )

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("\n" + "=" * 65)
    print("VERSION 2 TEST SUMMARY")
    print("=" * 65)

    print(
        f"Total Tests : {len(complaints)}"
    )

    print(
        f"Successful  : {successful}"
    )

    print(
        f"Failed      : {failed}"
    )

    print("=" * 65)


if __name__ == "__main__":
    main()
