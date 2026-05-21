"""Supabase-backed long-term and shared memory.

Tables used:
    content_drafts    — per-session draft content from WRITER / CAROUSEL
    review_log        — REVISOR quality-check results + human approval tracking
    publication_log   — PUBLISHER outcomes
    published_topics  — deduplication log of topics already covered
    approvers         — registered human approvers

All write operations emit a structured log entry at INFO level so every
state change is auditable without querying the database.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from supabase import acreate_client, AsyncClient

from src.config.settings import settings
from src.protocols.io_schema import PublicationResult, ReviewResult

logger = logging.getLogger(__name__)


class SupabaseMemory:
    """Async Supabase client for persistent agent memory."""

    def __init__(self) -> None:
        self._client: Optional[AsyncClient] = None

    async def connect(self) -> None:
        """Initialise the async Supabase client."""
        self._client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
        logger.info("SupabaseMemory connected to %s", settings.supabase_url)

    # ------------------------------------------------------------------
    # content_drafts
    # ------------------------------------------------------------------

    async def save_draft(
        self, session_id: str, platform: str, content: dict
    ) -> str:
        """Persist a content draft and return its database id.

        Overwrites are intentional — the latest draft per (session, platform)
        is always the canonical one; use get_draft() to retrieve it.
        """
        result = await (
            self._client.table("content_drafts")
            .insert(
                {
                    "session_id": session_id,
                    "platform": platform,
                    "content": content,
                }
            )
            .execute()
        )
        record_id: str = result.data[0]["id"]
        logger.info(
            "Draft saved",
            extra={"session_id": session_id, "platform": platform, "id": record_id},
        )
        return record_id

    async def get_draft(
        self, session_id: str, platform: str
    ) -> Optional[dict]:
        """Return the most recent draft for (session_id, platform), or None."""
        result = await (
            self._client.table("content_drafts")
            .select("*")
            .eq("session_id", session_id)
            .eq("platform", platform)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ------------------------------------------------------------------
    # review_log
    # ------------------------------------------------------------------

    async def log_review(self, review_result: ReviewResult) -> str:
        """Log the REVISOR AI quality-check result.

        human_decision is NULL on insert — the record is pending human
        approval. Call update_approval() when the human responds.
        Returns the database row id.
        """
        result = await (
            self._client.table("review_log")
            .insert(
                {
                    "review_id": review_result.review_id,
                    "session_id": review_result.session_id,
                    "platform": review_result.platform.value,
                    "quality_score": review_result.quality_score,
                    "ai_detection_score": review_result.ai_detection_score,
                    "issues": review_result.issues,
                    "ai_recommendation": review_result.decision,
                    "revision_note": review_result.revision_note,
                    "approver": review_result.approver,
                    "reviewed_at": review_result.timestamp.isoformat(),
                    # human_decision, human_note, human_decided_at start as NULL
                }
            )
            .execute()
        )
        record_id: str = result.data[0]["id"]
        logger.info(
            "Review logged",
            extra={"review_id": review_result.review_id, "id": record_id},
        )
        return record_id

    async def get_pending_approvals(self, session_id: str) -> list[dict]:
        """Return review_log rows that have not yet received a human decision.

        Filters by session_id when the column is populated. Reviews logged
        before session_id tracking was added will appear for all sessions —
        agents should reconcile using review_id if needed.
        """
        result = await (
            self._client.table("review_log")
            .select("*")
            .is_("human_decision", "null")
            .eq("session_id", session_id)
            .execute()
        )
        return result.data

    async def update_approval(
        self,
        review_id: str,
        decision: str,
        note: Optional[str],
    ) -> None:
        """Record the human decision for a previously logged review."""
        await (
            self._client.table("review_log")
            .update(
                {
                    "human_decision": decision,
                    "human_note": note,
                    "human_decided_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("review_id", review_id)
            .execute()
        )
        logger.info(
            "Approval updated",
            extra={"review_id": review_id, "decision": decision},
        )

    # ------------------------------------------------------------------
    # publication_log
    # ------------------------------------------------------------------

    async def log_publication(self, result: PublicationResult) -> str:
        """Log a PUBLISHER outcome and return the database row id."""
        db_result = await (
            self._client.table("publication_log")
            .insert(
                {
                    "publication_id": result.publication_id,
                    "platform": result.platform.value,
                    "post_url": result.post_url,
                    "status": result.status,
                    "published_at": result.timestamp.isoformat(),
                    "error": result.error,
                }
            )
            .execute()
        )
        record_id: str = db_result.data[0]["id"]
        logger.info(
            "Publication logged",
            extra={"publication_id": result.publication_id, "id": record_id},
        )
        return record_id

    # ------------------------------------------------------------------
    # published_topics
    # ------------------------------------------------------------------

    async def get_published_topics(self, days: int = 7) -> list[str]:
        """Return topics published within the last N days for deduplication."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = await (
            self._client.table("published_topics")
            .select("topic")
            .gte("created_at", since)
            .execute()
        )
        return [row["topic"] for row in result.data]

    async def save_topic(
        self, topic: str, run_date: str, pillar: str
    ) -> None:
        """Record a published topic for future deduplication.

        Args:
            topic:    The topic string as used by the SCOUT agent.
            run_date: ISO-8601 date string of the pipeline run (YYYY-MM-DD).
            pillar:   Content pillar — must be 'ai' or 'automation'.
        """
        await (
            self._client.table("published_topics")
            .insert(
                {
                    "topic": topic,
                    "run_date": run_date,
                    "pillar": pillar,
                }
            )
            .execute()
        )
        logger.info(
            "Topic saved",
            extra={"topic": topic, "run_date": run_date, "pillar": pillar},
        )
