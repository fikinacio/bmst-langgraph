"""PUBLISHER agent node — STUB.

Returns a minimal state delta so the graph compiles and runs end-to-end.
Replace this with the real PUBLISHER implementation when the agent is built.
"""

import logging

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


async def publisher_node(state: SocialAgentState) -> dict:
    """Stub PUBLISHER node — replaces real LinkedIn + Instagram publishing."""
    logger.info("PUBLISHER stub invoked", extra={"session_id": state["session_id"]})
    return {
        "current_agent": "publisher",
        "status": StatusType.TASK_COMPLETE,
        "action": ActionType.COMPLETE,
        "confidence": 0.95,
        "publication_results": [],
    }
