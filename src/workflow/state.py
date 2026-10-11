from typing import TypedDict, NotRequired


class ComplaintState(TypedDict):
    complaint_text: str

    complaint_analysis: NotRequired[dict]
    emotion_analysis: NotRequired[dict]
    priority_analysis: NotRequired[dict]
    resolution_analysis: NotRequired[dict]