"""REVISOR agent node — STUB.

Returns a minimal state delta so the graph compiles and runs end-to-end.
The graph is configured with interrupt_after=["revisor"], so after this node
runs the graph pauses and waits for the human approval webhook.

Replace this with the real REVISOR implementation when the agent is built.
"""

import logging

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


async def revisor_node(state: SocialAgentState) -> dict:
    """Stub REVISOR node — replaces real AI quality check + WhatsApp approval send."""
    logger.info("REVISOR stub invoked", extra={"session_id": state["session_id"]})
    return {
        "current_agent": "revisor",
        "status": StatusType.NEEDS_APPROVAL,
        "action": ActionType.REQUEST_APPROVAL,
        "confidence": 0.80,
        "review_results": [],
        # pending_approval flips True so the router sends us to "wait"
        # if the graph is resumed without an approval_decision.
        "pending_approval": True,
    }
