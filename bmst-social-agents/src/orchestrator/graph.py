"""LangGraph pipeline for the social media agent system.

Wires SCOUT → WRITER → CAROUSEL → REVISOR → PUBLISHER with conditional edges.
The graph pauses after REVISOR (interrupt_after) so a human can approve via
WhatsApp before publishing. State is persisted by AsyncRedisSaver between
the pause and resume so the HITL flow survives process restarts.

Checkpoint storage:
    Backend:     Redis (same instance as src/memory/redis_client.py)
    Key pattern: written by langgraph-checkpoint-redis:
                   checkpoint:{thread_id}:{namespace}:{checkpoint_id}
                   checkpoint_blob:{thread_id}:{namespace}:{channel}:{version}
                   checkpoint_write:{thread_id}:{namespace}:{ckpt_id}:{task_id}
                 thread_id is the pipeline session_id, so each pipeline run
                 has its own isolated checkpoint set. No prefix collision with
                 the bmst:social:working: working-memory keys.

    Connection:  this saver opens its own client pool against settings.redis_url
                 rather than reusing the RedisMemory client object. Same Redis
                 instance, separate pool — keeps module import order simple.

Public surface:
    compiled_graph:         the compiled LangGraph instance (importable everywhere).
    setup_checkpointer():   idempotent async — call once at app startup or
                            transparently from run_graph().
    run_graph(session_id):  convenience runner that ensures setup, builds the
                            initial state, and invokes the graph end-to-end.
"""

import logging
from datetime import date

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph import END, START, StateGraph

from src.config.settings import settings

from src.agents.carousel.node import carousel_node
from src.agents.publisher.node import publisher_node
from src.agents.revisor.node import revisor_node
from src.agents.scout.node import scout_node
from src.agents.writer.node import writer_node
from src.orchestrator.router import (
    route_after_carousel,
    route_after_revisor,
    route_after_scout,
    route_after_writer,
)

# route_after_publisher is exported from router.py for symmetry but unused
# here because publisher → END is a direct (unconditional) edge.
from src.orchestrator.state import SocialAgentState
from src.protocols.vocabulary import ActionType, StatusType

logger = logging.getLogger(__name__)


def build_graph() -> StateGraph:
    """Build the social media agent pipeline graph (uncompiled)."""
    graph = StateGraph(SocialAgentState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    graph.add_node("scout", scout_node)
    graph.add_node("writer", writer_node)
    graph.add_node("carousel", carousel_node)
    graph.add_node("revisor", revisor_node)
    graph.add_node("publisher", publisher_node)

    # ── Entry ────────────────────────────────────────────────────────────────
    graph.add_edge(START, "scout")

    # ── Conditional edges ────────────────────────────────────────────────────
    graph.add_conditional_edges(
        "scout",
        route_after_scout,
        {"writer": "writer", "end": END, "escalate": END},
    )

    graph.add_conditional_edges(
        "writer",
        route_after_writer,
        {"carousel": "carousel", "end": END},
    )

    graph.add_conditional_edges(
        "carousel",
        route_after_carousel,
        {"revisor": "revisor"},
    )

    graph.add_conditional_edges(
        "revisor",
        route_after_revisor,
        {
            "publisher": "publisher",
            "writer": "writer",
            "wait": END,
            "end": END,
        },
    )

    graph.add_edge("publisher", END)

    return graph


# ── Checkpointer + graph compilation ────────────────────────────────────────
# AsyncRedisSaver is constructed sync (no I/O) but requires asetup() to be
# awaited once before the first graph operation, to create the RediSearch
# indices. Construction at module import is safe; setup is lazy.
_checkpointer = AsyncRedisSaver(redis_url=settings.redis_url)

compiled_graph = build_graph().compile(
    checkpointer=_checkpointer,
    interrupt_after=["revisor"],
)

# Tracks whether asetup() has already run for this process
_checkpointer_setup_done = False


async def setup_checkpointer() -> None:
    """Idempotent RediSearch index initialisation for the checkpointer.

    Safe to call multiple times — subsequent calls are no-ops. Call once at
    application startup (e.g. FastAPI lifespan) or rely on run_graph() to
    invoke it transparently on first use.
    """
    global _checkpointer_setup_done
    if _checkpointer_setup_done:
        return
    await _checkpointer.asetup()
    _checkpointer_setup_done = True
    logger.info("AsyncRedisSaver indices initialised on %s", settings.redis_url)


async def run_graph(session_id: str) -> SocialAgentState:
    """Run the full pipeline for a given session_id.

    Builds a fresh initial state, threads it through the graph using
    session_id as the LangGraph thread_id (so checkpoints are scoped to the
    session), and returns the final state.

    Note: when the graph pauses at the REVISOR interrupt, this call returns
    with pending_approval=True. To resume after human approval, the caller
    must use compiled_graph.aupdate_state() then ainvoke(None, config) with
    the same thread_id.
    """
    initial_state: SocialAgentState = {
        "session_id": session_id,
        "run_date": date.today().isoformat(),
        "research_briefs": [],
        "selected_topic": None,
        "posts": {},
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "scout",
        "action": ActionType.SEND_MESSAGE,
        "status": StatusType.NEEDS_MORE_CONTEXT,
        "confidence": 1.0,
        "errors": [],
    }

    # Ensure the Redis checkpointer indices exist before the first op
    await setup_checkpointer()

    config = {"configurable": {"thread_id": session_id}}
    logger.info("Graph run starting", extra={"session_id": session_id})

    final_state = await compiled_graph.ainvoke(initial_state, config=config)

    logger.info(
        "Graph run finished",
        extra={
            "session_id": session_id,
            "final_agent": final_state.get("current_agent"),
            "status": final_state.get("status"),
        },
    )
    return final_state
