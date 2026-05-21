"""LangGraph state for the social media agent pipeline.

SocialAgentState is the single dict passed between every node. Each node
returns a partial dict (state delta) which LangGraph merges into the running
state. Most fields use replacement semantics; `errors` accumulates via
operator.add so error entries from every node are preserved.
"""

from operator import add
from typing import Annotated, Optional, TypedDict

from src.protocols.io_schema import (
    CarouselOutput,
    PlatformPost,
    PublicationResult,
    ResearchBrief,
    ReviewResult,
)
from src.protocols.vocabulary import ActionType, StatusType


class SocialAgentState(TypedDict):
    """State shared across every agent node in the pipeline.

    Field groups follow the agent order: SCOUT → WRITER → CAROUSEL →
    REVISOR → PUBLISHER, plus AOS bookkeeping at the bottom.
    """

    # ── Session ──────────────────────────────────────────────────────────────
    session_id: str
    run_date: str  # ISO-8601 date (YYYY-MM-DD)

    # ── SCOUT output ─────────────────────────────────────────────────────────
    research_briefs: list[ResearchBrief]
    selected_topic: Optional[ResearchBrief]

    # ── WRITER output ────────────────────────────────────────────────────────
    # Keyed by platform name (e.g. "linkedin" → PlatformPost)
    posts: dict[str, PlatformPost]

    # ── CAROUSEL output ──────────────────────────────────────────────────────
    carousel: Optional[CarouselOutput]

    # ── REVISOR output and HITL state ────────────────────────────────────────
    review_results: list[ReviewResult]
    pending_approval: bool
    approval_decision: Optional[str]  # approved | rejected | revision_requested
    revision_note: Optional[str]
    revision_count: int

    # ── PUBLISHER output ─────────────────────────────────────────────────────
    publication_results: list[PublicationResult]

    # ── AOS bookkeeping ──────────────────────────────────────────────────────
    current_agent: str
    action: ActionType
    status: StatusType
    confidence: float
    # Accumulates across nodes: each entry is {"agent": ..., "fault": ..., "context": ...}
    errors: Annotated[list[dict], add]
