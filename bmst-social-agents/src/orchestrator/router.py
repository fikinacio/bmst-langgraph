"""Routing functions for LangGraph conditional edges.

Each function inspects the current SocialAgentState and returns the name of
the next node (or one of the literal control tokens "end", "escalate",
"wait"). The graph builder maps these strings to actual node names or END.
"""

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import StatusType

# Threshold below which SCOUT output is considered too weak to continue
_CONFIDENCE_THRESHOLD = 0.70

# Maximum revision rounds before forcing an escalation
_MAX_REVISIONS = 3


def route_after_scout(state: SocialAgentState) -> str:
    """Route after SCOUT.

    Outcomes:
        FAILED              → "end"
        confidence < 0.70   → "escalate"
        TASK_COMPLETE       → "writer"
        anything else       → "end" (safety default)
    """
    if state["status"] == StatusType.FAILED:
        return "end"
    if state["confidence"] < _CONFIDENCE_THRESHOLD:
        return "escalate"
    if state["status"] == StatusType.TASK_COMPLETE:
        return "writer"
    return "end"


def route_after_writer(state: SocialAgentState) -> str:
    """Route after WRITER.

    Outcomes:
        TASK_COMPLETE → "carousel"
        anything else → "end"
    """
    if state["status"] == StatusType.TASK_COMPLETE:
        return "carousel"
    return "end"


def route_after_carousel(state: SocialAgentState) -> str:
    """Route after CAROUSEL.

    Both success and failure proceed to REVISOR; carousel failure is treated
    as graceful degradation and REVISOR handles the case where state["carousel"]
    is None.
    """
    return "revisor"


def route_after_revisor(state: SocialAgentState) -> str:
    """Route after REVISOR.

    Outcomes:
        pending_approval is True                        → "wait"
        approval_decision == "approved"                 → "publisher"
        approval_decision == "rejected"                 → "end"
        approval_decision == "revision_requested" and
            revision_count >= _MAX_REVISIONS            → "end"  (escalate)
        approval_decision == "revision_requested"       → "writer"  (loop back)
        anything else                                   → "end"
    """
    if state.get("pending_approval"):
        return "wait"

    decision = state.get("approval_decision")

    if decision == "approved":
        return "publisher"
    if decision == "rejected":
        return "end"
    if decision == "revision_requested":
        if state.get("revision_count", 0) >= _MAX_REVISIONS:
            return "end"
        return "writer"

    return "end"


def route_after_publisher(state: SocialAgentState) -> str:
    """PUBLISHER is the terminal node — always end."""
    return "end"
