from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from src.workflow.state import ComplaintState

from src.agents.complaint_analysis import (
    analyze_complaint,
)
from src.agents.emotion_analysis import (
    analyze_emotion,
)
from src.agents.priority_impact import (
    analyze_priority,
)
from src.agents.resolution_agent import (
    recommend_resolution,
)


# ==================================================
# AGENT 1: COMPLAINT ANALYSIS
# ==================================================

def complaint_analysis_node(
    state: ComplaintState,
) -> dict:

    print("Agent 1: Analyzing complaint...")

    result = analyze_complaint(
        state["complaint_text"]
    )

    return {
        "complaint_analysis": result.model_dump()
    }


# ==================================================
# AGENT 2: EMOTION ANALYSIS
# ==================================================

def emotion_analysis_node(
    state: ComplaintState,
) -> dict:

    print("Agent 2: Analyzing customer emotion...")

    result = analyze_emotion(
        state["complaint_text"]
    )

    return {
        "emotion_analysis": result.model_dump()
    }


# ==================================================
# AGENT 3: PRIORITY & BUSINESS IMPACT
# ==================================================

def priority_analysis_node(
    state: ComplaintState,
) -> dict:

    print("Agent 3: Calculating priority...")

    result = analyze_priority(
        complaint_text=state["complaint_text"],
        complaint_analysis=state["complaint_analysis"],
        emotion_analysis=state["emotion_analysis"],
    )

    return {
        "priority_analysis": result.model_dump()
    }


# ==================================================
# AGENT 4: RESOLUTION RECOMMENDATION
# ==================================================

def resolution_node(
    state: ComplaintState,
) -> dict:

    print("Agent 4: Recommending resolution...")

    result = recommend_resolution(
        complaint_text=state["complaint_text"],
        complaint_analysis=state["complaint_analysis"],
        emotion_analysis=state["emotion_analysis"],
        priority_analysis=state["priority_analysis"],
    )

    return {
        "resolution_analysis": result.model_dump()
    }


# ==================================================
# BUILD LANGGRAPH WORKFLOW
# ==================================================

def build_complaint_graph():

    workflow = StateGraph(ComplaintState)

    # Register the four agent nodes
    workflow.add_node(
        "complaint_analysis",
        complaint_analysis_node,
    )

    workflow.add_node(
        "emotion_analysis",
        emotion_analysis_node,
    )

    workflow.add_node(
        "priority_analysis",
        priority_analysis_node,
    )

    workflow.add_node(
        "resolution_recommendation",
        resolution_node,
    )

    # Define execution order
    workflow.add_edge(
        START,
        "complaint_analysis",
    )

    workflow.add_edge(
        "complaint_analysis",
        "emotion_analysis",
    )

    workflow.add_edge(
        "emotion_analysis",
        "priority_analysis",
    )

    workflow.add_edge(
        "priority_analysis",
        "resolution_recommendation",
    )

    workflow.add_edge(
        "resolution_recommendation",
        END,
    )

    return workflow.compile()


complaint_graph = build_complaint_graph()