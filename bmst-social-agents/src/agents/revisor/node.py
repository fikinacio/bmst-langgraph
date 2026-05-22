"""REVISOR agent node — automated quality gate + WhatsApp HITL approval.

Two distinct phases run inside one node call:

    Phase 1 — automatic, always runs:
        a) Quality judge: Claude evaluates the WRITER posts + CAROUSEL output
           and returns {score, issues[]}.
        b) AI detection: ai_detection.score_text() per caption + carousel
           bundle; aggregate by max (worst single signal wins).
        c) Log one ReviewResult per content piece to review_log (with
           human_decision=NULL — the human decision is filled later by the
           WhatsApp webhook via SupabaseMemory.update_approval_by_session()).

    Phase 2 — conditional:
        Three branches:
        - ESCALATION (revision_count >= MAX_REVISIONS):
            Send escalation WhatsApp message that includes session_id, set
            approval_decision='rejected' + pending_approval=False. The
            run_graph auto-resume loop carries the state to the router → END.
        - AI-FLAG (ai_detection_score > 0.70):
            Skip the human entirely. Set approval_decision='revision_requested'
            with revision_note explaining the AI flag, pending_approval=False.
            The router sends control back to WRITER (or END if at max revisions).
        - HUMAN (default):
            Send the WhatsApp approval message with content preview + scores,
            set pending_approval=True. The graph pauses via interrupt_after
            and waits for the WhatsApp webhook to resume it.

REVISOR never modifies content — it only scores, flags, and routes.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from src.agents.writer.node import PLATFORM_SPECS, _count_prohibited_terms
from src.config.settings import settings
from src.memory.supabase_client import SupabaseMemory
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import (
    AgentOutput,
    CarouselOutput,
    PlatformPost,
    ReviewResult,
)
from src.protocols.vocabulary import ActionType, FaultType, Platform, StatusType
from src.tools import ai_detection, whatsapp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REVISOR_SYSTEM_PROMPT = """
You are REVISOR, a quality control agent for BMST — Bisca Mais Sistemas e Tecnologias.

You evaluate social media content for:
- Brand voice fit: Fidel Inácio Kussunga's voice (engineer-founder, direct, no buzzwords)
- Language correctness: European Portuguese (pt-PT), NOT Brazilian Portuguese
- Engagement quality: hook strength, CTA clarity
- Platform fit: tone matches each platform

You never modify content — only score and flag issues.

Output JSON: {"score": <float 0-1>, "issues": ["specific issue 1", ...]}
Score 1.0 = excellent, 0.0 = unacceptable. Issues must be specific and
actionable (e.g. "Slide 1 hook is weak — too generic"). Return JSON only,
no prose, no markdown fences.
""".strip()


# Max revisions before forcing escalation (matches router constant)
_MAX_REVISIONS: int = 3

# Confidence threshold: content scoring below this is sent back to WRITER
# even when the AI-detection score is clean. Provides defence-in-depth:
# Claude's judge call might give a high score while structural checks
# below still fail (e.g. char overflow, hashtag count mismatch).
_CONFIDENCE_THRESHOLD: float = 0.80

# Maximum number of issues to surface in the revision_note sent to WRITER.
# Truncates the prompt while preserving the most actionable feedback.
_MAX_ISSUES_IN_NOTE: int = 10

# Approver display name (matches the approvers table seed)
_APPROVER_NAME: str = "Fidel Inácio Kussunga"

# Token budget for the quality judge call — 2 short JSON fields, generous
_MAX_TOKENS: int = 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_content_bundle(
    posts: dict[str, PlatformPost],
    carousel: Optional[CarouselOutput],
) -> str:
    """Concatenate all content into a single text bundle for the judge call."""
    lines: list[str] = []
    for name, post in posts.items():
        lines.append(f"=== {name.upper()} POST ===")
        lines.append(f"Caption: {post.caption}")
        lines.append(f"Hashtags: {' '.join(post.hashtags)}")
        lines.append("")
    if carousel is not None:
        lines.append("=== CAROUSEL ===")
        lines.append(f"Title: {carousel.carousel_title}")
        lines.append(f"Caption: {carousel.caption}")
        for slide in carousel.slides:
            lines.append(f"  Slide {slide.slide_number}: {slide.headline} — {slide.body}")
    return "\n".join(lines)


def _check_platform_compliance(post: PlatformPost) -> list[str]:
    """Verify per-platform mechanical constraints. Returns human-readable issues.

    Defence-in-depth: WRITER's _score_post already applies these checks at
    generation time, but REVISOR re-verifies before approval to catch any
    drift between what WRITER produced and what the platform actually accepts.

    Checks:
        - caption.char_count must be <= platform max
        - len(hashtags) must be within [min_hashtags, max_hashtags] for the
          platform
    """
    spec = PLATFORM_SPECS.get(post.platform)
    if spec is None:
        return []

    issues: list[str] = []

    if post.char_count > spec["max_chars"]:
        issues.append(
            f"{post.platform.value}: caption is {post.char_count} chars, "
            f"exceeds platform maximum of {spec['max_chars']}"
        )

    n_hashtags = len(post.hashtags)
    if n_hashtags < spec["min_hashtags"]:
        issues.append(
            f"{post.platform.value}: {n_hashtags} hashtags is below "
            f"platform minimum of {spec['min_hashtags']}"
        )
    elif n_hashtags > spec["max_hashtags"]:
        issues.append(
            f"{post.platform.value}: {n_hashtags} hashtags exceeds "
            f"platform maximum of {spec['max_hashtags']}"
        )

    return issues


def _check_prohibited_terms_in_post(post: PlatformPost) -> list[str]:
    """Independent prohibited-terms check (defence-in-depth over WRITER).

    Uses WRITER's PROHIBITED_TERMS + _count_prohibited_terms so both agents
    agree on the rule set. If WRITER ever leaks a banned term past its own
    scoring (e.g. low-confidence post was accepted), REVISOR catches it here.
    """
    count = _count_prohibited_terms(post.caption)
    if count > 0:
        return [
            f"{post.platform.value}: {count} prohibited term(s) detected "
            "in caption (see WRITER PROHIBITED_TERMS)"
        ]
    return []


def _build_preview(
    posts: dict[str, PlatformPost],
    carousel: Optional[CarouselOutput],
) -> str:
    """Short preview shown inside the WhatsApp approval message."""
    parts: list[str] = []
    for name, post in posts.items():
        # First 200 chars per platform caption
        preview = post.caption if len(post.caption) <= 200 else post.caption[:200] + "…"
        parts.append(f"📱 {name.upper()}: {preview}")
    if carousel is not None:
        slide_one = carousel.slides[0] if carousel.slides else None
        if slide_one:
            parts.append(f"🎴 CAROUSEL · slide 1: {slide_one.headline}")
    return "\n\n".join(parts)


async def _score_quality(content_bundle: str) -> tuple[float, list[str]]:
    """Run the Claude quality judge. Returns (score, issues).

    On any error returns (0.5, ["judge_unavailable"]) so REVISOR can still
    proceed — the AI detection layer and human review are the hard gates.
    """
    model = settings.revisor_model or settings.writer_model
    llm = AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        response = await llm.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=REVISOR_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Evaluate this content:\n\n{content_bundle}"}],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("REVISOR quality judge call failed", extra={"error": str(exc)})
        return 0.5, ["judge_unavailable"]

    if not response.content:
        return 0.5, ["judge_unavailable"]

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        first_nl = raw.find("\n")
        raw = raw[first_nl + 1:] if first_nl >= 0 else raw[3:]
        if raw.rstrip().endswith("```"):
            raw = raw.rstrip().rsplit("```", 1)[0]
        raw = raw.strip()

    try:
        data = json.loads(raw)
        score = float(data.get("score", 0.5))
        issues = list(data.get("issues", []))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.error("REVISOR judge response parse failed", extra={"error": str(exc)})
        return 0.5, ["judge_parse_failed"]

    score = max(0.0, min(1.0, score))
    return score, issues


async def _score_ai_detection(
    posts: dict[str, PlatformPost],
    carousel: Optional[CarouselOutput],
) -> float:
    """Aggregate AI-detection score across all captions (worst signal wins).

    Returns max(per-caption scores). Each call to ai_detection.score_text
    returns 0.0–1.0. If every call fails, score_text returns 0.5 (neutral)
    per its contract.
    """
    texts: list[str] = []
    for post in posts.values():
        texts.append(post.caption)
    if carousel is not None:
        bundle = carousel.caption + "\n" + "\n".join(
            f"{s.headline} {s.body}" for s in carousel.slides
        )
        texts.append(bundle)

    if not texts:
        return 0.0

    scores = await asyncio.gather(*(ai_detection.score_text(t) for t in texts))
    return max(scores)


def _build_review_results(
    session_id: str,
    posts: dict[str, PlatformPost],
    carousel: Optional[CarouselOutput],
    quality_score: float,
    ai_detection_score: float,
    issues: list[str],
    ai_recommendation: str,
    revision_note: Optional[str],
) -> list[ReviewResult]:
    """Build one ReviewResult per content piece. All share session_id."""
    now = datetime.now(timezone.utc)
    results: list[ReviewResult] = []

    for name, post in posts.items():
        results.append(
            ReviewResult(
                review_id=str(uuid.uuid4()),
                session_id=session_id,
                platform=post.platform,
                quality_score=quality_score,
                ai_detection_score=ai_detection_score,
                issues=issues,
                decision=ai_recommendation,
                revision_note=revision_note,
                approver=_APPROVER_NAME,
                timestamp=now,
            )
        )

    if carousel is not None:
        results.append(
            ReviewResult(
                review_id=str(uuid.uuid4()),
                session_id=session_id,
                platform=carousel.platform,
                quality_score=quality_score,
                ai_detection_score=ai_detection_score,
                issues=issues,
                decision=ai_recommendation,
                revision_note=revision_note,
                approver=_APPROVER_NAME,
                timestamp=now,
            )
        )

    return results


def _format_escalation_message(session_id: str, revision_count: int) -> str:
    """Escalation WhatsApp message format (per spec).

    session_id is included so investigators can correlate the alert with
    the exact run in Supabase.
    """
    return (
        "⚠️ ESCALATION — max revisions reached\n"
        f"Session: {session_id}\n"
        f"Revision count: {revision_count}\n"
        "Review the content manually in Supabase."
    )


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    """Convert a FaultHandler AgentOutput into a REVISOR state delta."""
    return {
        "current_agent": "revisor",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "revisor",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


async def revisor_node(state: SocialAgentState) -> dict:
    """REVISOR — automated quality gate plus conditional WhatsApp HITL."""
    session_id = state["session_id"]
    revision_count = state.get("revision_count", 0)

    logger.info(
        "REVISOR start",
        extra={"session_id": session_id, "revision_count": revision_count},
    )

    handler = FaultHandler()

    posts: dict[str, PlatformPost] = state.get("posts") or {}
    carousel: Optional[CarouselOutput] = state.get("carousel")

    if not posts and carousel is None:
        logger.warning("REVISOR no content to review")
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_content"}, retry_count=0),
            "no posts or carousel in state",
        )

    # ── Phase 1 — automatic scoring ───────────────────────────────────────────
    content_bundle = _build_content_bundle(posts, carousel)

    quality_score, judge_issues = await _score_quality(content_bundle)
    ai_detection_score = await _score_ai_detection(posts, carousel)

    # Defence-in-depth structural checks per platform (G1 + G2).
    # These run independently of the Claude judge so structural drift
    # between WRITER and the platform's actual rules can't slip through.
    compliance_issues: list[str] = []
    prohibited_issues: list[str] = []
    for post in posts.values():
        compliance_issues.extend(_check_platform_compliance(post))
        prohibited_issues.extend(_check_prohibited_terms_in_post(post))

    # Issues used by both review_log (audit) and the revision_note (feedback)
    issues: list[str] = list(judge_issues) + compliance_issues + prohibited_issues

    logger.info(
        "REVISOR scores",
        extra={
            "session_id": session_id,
            "quality_score": round(quality_score, 3),
            "ai_detection_score": round(ai_detection_score, 3),
            "judge_issues": len(judge_issues),
            "compliance_issues": len(compliance_issues),
            "prohibited_issues": len(prohibited_issues),
        },
    )

    # Decide REVISOR's AI recommendation (NOT the final decision — that's the human's)
    if ai_detection_score > ai_detection.DETECTION_THRESHOLD:
        ai_recommendation = "revision_requested"
        ai_revision_note = (
            f"AI-detection score {ai_detection_score:.2f} exceeds threshold "
            f"{ai_detection.DETECTION_THRESHOLD:.2f}. Rewrite the captions to "
            "sound less artificial and more conversational."
        )
    else:
        ai_recommendation = "approved"
        ai_revision_note = None

    # ── Phase 1c — log one ReviewResult per content piece ─────────────────────
    review_results = _build_review_results(
        session_id=session_id,
        posts=posts,
        carousel=carousel,
        quality_score=quality_score,
        ai_detection_score=ai_detection_score,
        issues=issues,
        ai_recommendation=ai_recommendation,
        revision_note=ai_revision_note,
    )

    supa = SupabaseMemory()
    try:
        await supa.connect()
        await asyncio.gather(*(supa.log_review(r) for r in review_results))
    except Exception as exc:  # noqa: BLE001 — logging is best-effort
        logger.error(
            "REVISOR failed to log reviews to Supabase",
            extra={"error": str(exc), "session_id": session_id},
        )
        # Continue — logging failure is not fatal to the agent

    # Confidence: high quality + low AI score = high confidence
    confidence = (quality_score + (1.0 - ai_detection_score)) / 2.0

    # ── Phase 2 — decision tree ───────────────────────────────────────────────

    # Branch A: ESCALATION — max revisions reached, send alert and end
    if revision_count >= _MAX_REVISIONS:
        logger.warning(
            "REVISOR escalating — max revisions reached",
            extra={"session_id": session_id, "revision_count": revision_count},
        )
        escalation_msg = _format_escalation_message(session_id, revision_count)
        try:
            await whatsapp.send_text(settings.revisor_approver_phone, escalation_msg)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "REVISOR escalation WhatsApp failed",
                extra={"session_id": session_id, "error": str(exc)},
            )
        return {
            "current_agent": "revisor",
            "action": ActionType.ESCALATE_HUMAN,
            "status": StatusType.FAILED,
            "confidence": confidence,
            "review_results": review_results,
            "approval_decision": "rejected",
            "pending_approval": False,
        }

    # Branch B: AI-FLAG — auto-revise without bothering the human
    if ai_detection_score > ai_detection.DETECTION_THRESHOLD:
        logger.info(
            "REVISOR AI-flagging content for revision",
            extra={"session_id": session_id, "ai_score": round(ai_detection_score, 3)},
        )
        return {
            "current_agent": "revisor",
            "action": ActionType.DELEGATE_AGENT,
            "status": StatusType.BLOCKED,
            "confidence": confidence,
            "review_results": review_results,
            "approval_decision": "revision_requested",
            "revision_note": ai_revision_note,
            "pending_approval": False,
        }

    # Branch B+: QUALITY-FLAG — confidence below threshold or structural
    # violations detected. Route back to WRITER with the issues list so the
    # next revision can address them specifically.
    quality_below_threshold = confidence < _CONFIDENCE_THRESHOLD
    has_structural_violations = bool(compliance_issues or prohibited_issues)

    if quality_below_threshold or has_structural_violations:
        # Build a concise feedback note containing the most actionable issues.
        capped_issues = issues[:_MAX_ISSUES_IN_NOTE]
        truncation_note = (
            f" (+{len(issues) - _MAX_ISSUES_IN_NOTE} more)"
            if len(issues) > _MAX_ISSUES_IN_NOTE
            else ""
        )
        quality_note = (
            "Quality issues detected — please address: "
            + "; ".join(capped_issues)
            + truncation_note
            if capped_issues
            else (
                f"Confidence {confidence:.2f} is below threshold "
                f"{_CONFIDENCE_THRESHOLD:.2f}. Tighten brand voice and clarity."
            )
        )

        logger.info(
            "REVISOR quality-flagging content for revision",
            extra={
                "session_id": session_id,
                "confidence": round(confidence, 3),
                "below_threshold": quality_below_threshold,
                "structural_violations": has_structural_violations,
                "issue_count": len(issues),
            },
        )

        return {
            "current_agent": "revisor",
            "action": ActionType.DELEGATE_AGENT,
            "status": StatusType.BLOCKED,
            "confidence": confidence,
            "review_results": review_results,
            "approval_decision": "revision_requested",
            "revision_note": quality_note,
            "pending_approval": False,
        }

    # Branch C: HUMAN — send approval request and pause for webhook
    primary_review = review_results[0]  # any row works for the WhatsApp formatter
    preview = _build_preview(posts, carousel)
    approval_msg = whatsapp.format_approval_message(primary_review, preview)

    try:
        await whatsapp.send_text(settings.revisor_approver_phone, approval_msg)
        logger.info("REVISOR sent approval request", extra={"session_id": session_id})
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "REVISOR approval WhatsApp send failed",
            extra={"session_id": session_id, "error": str(exc)},
        )
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "whatsapp"}, retry_count=0),
            exc,
        )

    return {
        "current_agent": "revisor",
        "action": ActionType.REQUEST_APPROVAL,
        "status": StatusType.NEEDS_APPROVAL,
        "confidence": confidence,
        "review_results": review_results,
        "pending_approval": True,
    }
