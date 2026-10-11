from src.agents.emotion_analysis import (
    analyze_emotion,
)


complaints = [
    """
    Our printer has not worked for three days.
    We contacted the service department,
    but no technician has attended.
    """,

    """
    I am extremely disappointed with your service!
    I have called five times and nobody has helped.
    This is completely unacceptable!
    """,

    """
    The printer is showing an error code.
    Please arrange a technician visit.
    """,
]


for index, complaint in enumerate(complaints, start=1):

    result = analyze_emotion(complaint)

    print(f"\nCOMPLAINT {index}")
    print("=" * 45)

    print("Sentiment:", result.sentiment)
    print("Primary Emotion:", result.primary_emotion)
    print("Intensity:", result.emotion_intensity)
    print("Emotion Score:", result.emotion_score)
    print("Explanation:", result.explanation)