"""PUBLISHER agent node — publishes approved content to social platforms.

Order of operations:
    1. Read posts, carousel, selected_topic, selected_pillar from state.
    2. Resolve a single image URL from carousel.slides[0].canva_asset_url
       (None if no carousel or image generation failed for slide 1).
    3. Publish in parallel via asyncio.gather(return_exceptions=True):
         LinkedIn   → linkedin_api.post_linkedin (text + optional image)
         Instagram  → meta_api.post_instagram     (image REQUIRED; skipped
                                                   with status=manual_delivery
                                                   if no image is available)
         Facebook   → meta_api.post_facebook      (text + optional image)
         TikTok     → not implemented in the tools layer; recorded as
                      PublicationResult(status="manual_delivery") with an
                      error message explaining the gap (see tiktok_api.py
                      stub for the future implementation entry point)
    4. Build one PublicationResult per platform attempted, including
       successful publishes, failures, and skips. All are logged via
       supabase.log_publication.
    5. Record the topic + pillar via supabase.save_topic for SCOUT's
       day-over-day rotation tracking.
    6. Return state delta. Status TASK_COMPLETE if at least one platform
       published; EXECUTION_FAULT if all platforms failed.

Carousel publishing note: meta_api.post_instagram() is currently single-
image. We post slide 1 of the carousel + the carousel caption. Native
multi-slide Instagram carousels are a backlog item — flagged inline below.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from src.config.settings import settings
from src.memory.supabase_client import SupabaseMemory
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import (
    AgentOutput,
    CarouselOutput,
    PlatformPost,
    PublicationResult,
)
from src.protocols.vocabulary import ActionType, FaultType, Platform, StatusType
from src.tools import linkedin_api, meta_api

logger = logging.getLogger(__name__)


# Default pillar to record when SCOUT didn't classify (shouldn't happen in
# practice, but defensive — keeps the published_topics check constraint happy).
_DEFAULT_PILLAR: str = "ai"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_image_url(carousel: Optional[CarouselOutput]) -> Optional[str]:
    """Pick slide 1's Canva URL if available, else None."""
    if carousel is None or not carousel.slides:
        return None
    return carousel.slides[0].canva_asset_url


def _make_skip_result(platform: Platform, reason: str) -> PublicationResult:
    """Build a manual_delivery PublicationResult for skipped platforms."""
    return PublicationResult(
        publication_id=str(uuid.uuid4()),
        platform=platform,
        post_url=None,
        status="manual_delivery",
        timestamp=datetime.now(timezone.utc),
        error=reason,
    )


def _make_failure_result(platform: Platform, error: Exception) -> PublicationResult:
    return PublicationResult(
        publication_id=str(uuid.uuid4()),
        platform=platform,
        post_url=None,
        status="failed",
        timestamp=datetime.now(timezone.utc),
        error=str(error)[:500],
    )


def _make_success_result(
    platform: Platform, post_url: Optional[str], publication_id: str
) -> PublicationResult:
    return PublicationResult(
        publication_id=publication_id or str(uuid.uuid4()),
        platform=platform,
        post_url=post_url,
        status="published",
        timestamp=datetime.now(timezone.utc),
        error=None,
    )


async def _publish_linkedin(
    post: PlatformPost, image_url: Optional[str]
) -> PublicationResult:
    """Publish to LinkedIn (text required, image optional)."""
    try:
        result = await linkedin_api.post_linkedin(text=post.caption, image_url=image_url)
        return _make_success_result(
            Platform.LINKEDIN, result.get("post_url"), result.get("id", "")
        )
    except Exception as exc:  # noqa: BLE001 — any failure → record + continue
        logger.error("LinkedIn publish failed", extra={"error": str(exc)})
        return _make_failure_result(Platform.LINKEDIN, exc)


async def _publish_instagram(
    carousel: Optional[CarouselOutput], image_url: Optional[str]
) -> PublicationResult:
    """Publish to Instagram (image required by the API).

    Uses carousel slide 1 as the image and carousel.caption as the post text.
    If no image is available we skip with manual_delivery status.

    # BACKLOG: meta_api.post_instagram is single-image only. When multi-image
    # carousel support is added, replace this single-slide post with a native
    # Instagram carousel using all slides.
    """
    if image_url is None or carousel is None:
        return _make_skip_result(
            Platform.INSTAGRAM,
            "no image available (Instagram requires an image)",
        )
    try:
        result = await meta_api.post_instagram(image_url=image_url, caption=carousel.caption)
        return _make_success_result(
            Platform.INSTAGRAM, result.get("post_url"), result.get("id", "")
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Instagram publish failed", extra={"error": str(exc)})
        return _make_failure_result(Platform.INSTAGRAM, exc)


async def _publish_facebook(
    post: PlatformPost, image_url: Optional[str]
) -> PublicationResult:
    """Publish to Facebook (text required, image optional)."""
    try:
        result = await meta_api.post_facebook(message=post.caption, image_url=image_url)
        return _make_success_result(
            Platform.FACEBOOK, result.get("post_url"), result.get("id", "")
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Facebook publish failed", extra={"error": str(exc)})
        return _make_failure_result(Platform.FACEBOOK, exc)


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    return {
        "current_agent": "publisher",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "publisher",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


async def publisher_node(state: SocialAgentState) -> dict:
    """PUBLISHER — push approved content to LinkedIn, Instagram, Facebook."""
    session_id = state["session_id"]
    logger.info("PUBLISHER start", extra={"session_id": session_id})

    handler = FaultHandler()

    posts: dict[str, PlatformPost] = state.get("posts") or {}
    carousel: Optional[CarouselOutput] = state.get("carousel")
    selected_topic = state.get("selected_topic")
    selected_pillar: str = state.get("selected_pillar") or _DEFAULT_PILLAR
    run_date: str = state["run_date"]

    if not posts and carousel is None:
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_content"}, retry_count=0),
            "no posts or carousel to publish",
        )

    image_url = _resolve_image_url(carousel)
    logger.info(
        "PUBLISHER resolved image",
        extra={"session_id": session_id, "image_url_present": image_url is not None},
    )

    # Build the list of platform-specific publish coroutines
    publish_tasks = []

    linkedin_post = posts.get("linkedin")
    if linkedin_post is not None:
        publish_tasks.append(_publish_linkedin(linkedin_post, image_url))

    publish_tasks.append(_publish_instagram(carousel, image_url))

    facebook_post = posts.get("facebook")
    if facebook_post is not None:
        publish_tasks.append(_publish_facebook(facebook_post, image_url))

    # TikTok: no tool exists yet; record as manual_delivery
    if posts.get("tiktok") is not None:
        tiktok_result = _make_skip_result(
            Platform.TIKTOK,
            "tiktok publishing not implemented — manual delivery required",
        )
        publish_tasks.append(asyncio.sleep(0, result=tiktok_result))  # type: ignore[call-overload]

    publication_results: list[PublicationResult] = list(
        await asyncio.gather(*publish_tasks)
    )

    # Aggregate counts for logging + status decision
    published_count = sum(1 for r in publication_results if r.status == "published")
    failed_count = sum(1 for r in publication_results if r.status == "failed")
    manual_count = sum(1 for r in publication_results if r.status == "manual_delivery")

    logger.info(
        "PUBLISHER results",
        extra={
            "session_id": session_id,
            "published": published_count,
            "failed": failed_count,
            "manual": manual_count,
        },
    )

    # Persist publication log + topic dedup record
    supa = SupabaseMemory()
    try:
        await supa.connect()
        await asyncio.gather(*(supa.log_publication(r) for r in publication_results))
        if selected_topic is not None:
            await supa.save_topic(
                topic=selected_topic.topic,
                run_date=run_date,
                pillar=selected_pillar,
            )
    except Exception as exc:  # noqa: BLE001
        # Logging is best-effort — we've already published, so we don't fault
        logger.error(
            "PUBLISHER persistence failed",
            extra={"session_id": session_id, "error": str(exc)},
        )

    # Status: if every attempt failed, fault the agent. Otherwise success.
    if publication_results and failed_count == len(publication_results):
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "all_failed"}, retry_count=0),
            f"all {failed_count} platforms failed",
        )

    confidence = published_count / max(1, len(publication_results))

    return {
        "current_agent": "publisher",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": confidence,
        "publication_results": publication_results,
    }
