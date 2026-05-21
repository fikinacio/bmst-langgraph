"""CAROUSEL agent node — STUB.

Returns a minimal state delta so the graph compiles and runs end-to-end.
Replace this with the real CAROUSEL implementation when the agent is built.
"""

import logging

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


async def carousel_node(state: SocialAgentState) -> dict:
    """Stub CAROUSEL node — replaces real carousel + Canva generation."""
    logger.info("CAROUSEL stub invoked", extra={"session_id": state["session_id"]})
    return {
        "current_agent": "carousel",
        "status": StatusType.TASK_COMPLETE,
        "action": ActionType.COMPLETE,
        "confidence": 0.85,
        "carousel": None,
    }
