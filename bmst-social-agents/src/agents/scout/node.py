"""SCOUT agent node — STUB.

Returns a minimal state delta so the graph compiles and runs end-to-end.
Replace this with the real SCOUT implementation when the agent is built.
"""

import logging

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


async def scout_node(state: SocialAgentState) -> dict:
    """Stub SCOUT node — replaces real news research."""
    logger.info("SCOUT stub invoked", extra={"session_id": state["session_id"]})
    return {
        "current_agent": "scout",
        "status": StatusType.TASK_COMPLETE,
        "action": ActionType.COMPLETE,
        "confidence": 0.85,
        "research_briefs": [],
        "selected_topic": None,
    }
