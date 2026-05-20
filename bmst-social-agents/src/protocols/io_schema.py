"""AOS I/O schema — typed contracts for all agent inputs and outputs.

All models use Pydantic v2. No imports from other src modules except vocabulary.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from src.protocols.vocabulary import ActionType, Platform, StatusType


# ---------------------------------------------------------------------------
# Core I/O
# ---------------------------------------------------------------------------


class AgentInput(BaseModel):
    """Universal input envelope received by every agent endpoint."""

    source: Literal["human", "agent", "system", "webhook"]
    payload: dict
    context_ref: Optional[str] = None
    timestamp: datetime
    session_id: str


class AgentOutput(BaseModel):
    """Universal output envelope returned by every agent.

    block_client is sent to the end user (WhatsApp / social caption).
    block_internal is always present and used for founder notes and n8n routing.
    The to_wire() method formats both blocks with the mandatory --- separator
    that n8n splits on.
    """

    block_client: Optional[str] = None
    block_internal: str
    action: ActionType
    status: StatusType
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime

    def to_wire(self) -> str:
        """Return the dual-block wire format used by n8n.

        n8n splits the response on the literal string '---' to route
        block_client to WhatsApp and block_internal to Telegram.
        When block_client is None only the internal block is returned.
        """
        if self.block_client is None:
            return self.block_internal
        return f"{self.block_client}\n---\n{self.block_internal}"


# ---------------------------------------------------------------------------
# SCOUT output
# ---------------------------------------------------------------------------


class ResearchBrief(BaseModel):
    """Structured article brief produced by the SCOUT agent."""

    topic: str
    source_url: str
    summary: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    content_angles: list[str]
    platforms_fit: list[Platform]

    @field_validator("summary")
    @classmethod
    def validate_summary_length(cls, v: str) -> str:
        word_count = len(v.split())
        if word_count > 150:
            raise ValueError(f"summary must be at most 150 words, got {word_count}")
        return v


# ---------------------------------------------------------------------------
# WRITER output
# ---------------------------------------------------------------------------


class PlatformPost(BaseModel):
    """A single platform post produced by the WRITER agent.

    char_count is computed automatically from caption length.
    """

    platform: Platform
    caption: str
    hashtags: list[str]
    image_brief: str
    char_count: int = Field(default=0, description="Auto-computed from caption")
    revision_notes: Optional[str] = None

    @model_validator(mode="after")
    def compute_char_count(self) -> "PlatformPost":
        self.char_count = len(self.caption)
        return self


# ---------------------------------------------------------------------------
# CAROUSEL output
# ---------------------------------------------------------------------------


class CarouselSlide(BaseModel):
    """One slide within a carousel."""

    slide_number: int
    headline: str
    body: str
    visual_brief: str
    canva_asset_url: Optional[str] = None

    @field_validator("body")
    @classmethod
    def validate_body_length(cls, v: str) -> str:
        word_count = len(v.split())
        if word_count > 30:
            raise ValueError(f"body must be at most 30 words, got {word_count}")
        return v


class CarouselOutput(BaseModel):
    """Full carousel produced by the CAROUSEL agent."""

    carousel_title: str
    platform: Platform
    slides: list[CarouselSlide] = Field(min_length=3, max_length=10)
    caption: str
    hashtags: list[str]


# ---------------------------------------------------------------------------
# REVISOR output
# ---------------------------------------------------------------------------


class ReviewResult(BaseModel):
    """Quality-gate result produced by the REVISOR agent.

    decision reflects the AI recommendation before human approval.
    The human decision is stored separately in the review_log table
    via SupabaseMemory.update_approval().
    """

    review_id: str
    platform: Platform
    quality_score: float = Field(ge=0.0, le=1.0)
    ai_detection_score: float = Field(ge=0.0, le=1.0)
    issues: list[str]
    decision: Literal["approved", "rejected", "revision_requested"]
    revision_note: Optional[str] = None
    approver: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# PUBLISHER output
# ---------------------------------------------------------------------------


class PublicationResult(BaseModel):
    """Result of a publish attempt produced by the PUBLISHER agent."""

    publication_id: str
    platform: Platform
    post_url: Optional[str] = None
    status: Literal["published", "failed", "manual_delivery"]
    timestamp: datetime
    error: Optional[str] = None
