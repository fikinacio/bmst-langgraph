"""WRITER agent node — STUB.

Returns a minimal state delta so the graph compiles and runs end-to-end.
Replace this with the real WRITER implementation when the agent is built.
"""

import logging

from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


async def writer_node(state: SocialAgentState) -> dict:
    """Stub WRITER node — replaces real content writing."""
    logger.info("WRITER stub invoked", extra={"session_id": state["session_id"]})
    return {
        "current_agent": "writer",
        "status": StatusType.TASK_COMPLETE,
        "action": ActionType.COMPLETE,
        "confidence": 0.90,
        "posts": {},
    }
