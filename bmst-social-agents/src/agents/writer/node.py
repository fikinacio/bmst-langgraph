"""WRITER agent node — generates one post per platform for the selected topic.

Pipeline:
    1. Read selected_topic from state (set by SCOUT)
    2. Determine mode: fresh write or revision (when revision_note is set)
    3. Single Claude call produces a JSON array of 4 PlatformPost-shaped objects
    4. Parse + Pydantic-validate each post (Pydantic auto-fills char_count)
    5. Score per post against platform specs and prohibited-terms list
    6. Return state delta with posts, REQUEST_APPROVAL action, confidence=mean

Pillar rotation ("never two consecutive posts on same pillar") is enforced
by SCOUT, not WRITER — WRITER honours whatever pillar SCOUT selected.
"""

import json
import logging
import re
from typing import Any, Optional

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from src.config.settings import settings
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import AgentOutput, PlatformPost, ResearchBrief
from src.protocols.vocabulary import ActionType, FaultType, Platform, StatusType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt + constants
# ---------------------------------------------------------------------------

WRITER_SYSTEM_PROMPT = """
You are WRITER, a content creation agent for BMST — Bisca Mais Sistemas e Tecnologias.

You write social media content for Fidel Inácio Kussunga, engineer and founder of BMST.

Fidel's voice:
- Engineer background (MSc, embedded software, C++, AI)
- Founder of an AI and automation company in Angola
- Speaks to Angolan entrepreneurs and professionals
- Direct, concrete, no buzzwords
- Shares knowledge without being academic
- Accessible without being casual

Content pillars (alternate daily — check which pillar was used last):
- Pillar 1: Artificial Intelligence — tools, trends, real applications for business
- Pillar 2: Business Process Automation — workflows, efficiency, digital transformation

Both pillars are always anchored to the Angolan business context.

Language: European Portuguese (pt-PT). Not Brazilian Portuguese.

Hard rules:
- Never use these words: "IA", "inteligência artificial", "algoritmo", "chatbot", "bot", "machine learning"
- "automação" is allowed — it is a core topic of this content
- Never sound like AI wrote this
- Always include a hook, body, CTA, and hashtags
- Always respect character limits per platform
- Always write from Fidel's first person perspective
- Never write two posts on the same pillar consecutively

When revising: honour the revision note exactly. Do not ignore it.

Output: JSON array of PlatformPost objects. Nothing else.
""".strip()


# Lowercased terms that must not appear in any caption.
# "automação" is intentionally NOT in this set — it is a core topic.
PROHIBITED_TERMS: set[str] = {
    "ia",
    "inteligência artificial",
    "algoritmo",
    "chatbot",
    "bot",
    "machine learning",
}


# Platform-specific constraints used by _score_post and embedded in the
# user prompt sent to Claude.
PLATFORM_SPECS: dict[Platform, dict] = {
    Platform.INSTAGRAM: {
        "max_chars": 2200,
        "min_hashtags": 5,
        "max_hashtags": 10,
        "voice": "Hook + body + CTA",
    },
    Platform.LINKEDIN: {
        "max_chars": 3000,
        "min_hashtags": 3,
        "max_hashtags": 5,
        "voice": "professional insight format",
    },
    Platform.FACEBOOK: {
        "max_chars": 63206,
        "min_hashtags": 2,
        "max_hashtags": 5,
        "voice": "conversational",
    },
    Platform.TIKTOK: {
        "max_chars": 2200,
        "min_hashtags": 3,
        "max_hashtags": 7,
        "voice": "punchy and direct",
    },
}


# Maximum tokens for the Claude generation call — 4 posts each up to ~3k chars
# is generous; 4096 keeps headroom for the JSON envelope.
_MAX_TOKENS: int = 4096


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _count_prohibited_terms(caption: str) -> int:
    """Count how many distinct prohibited terms appear in the caption.

    Case-insensitive. Only single- and two-letter terms (i.e. "ia")
    require word boundaries — substring matching against "ia" would
    otherwise flag common Portuguese words like "tecnologia", "família",
    "havia". All terms with 3+ letters use plain substring matching
    because they are long enough to avoid coincidental false positives.

    Substring matching means "chatbot" inside the caption matches both
    "chatbot" and "bot" (count = 2). This is intentional — overlapping
    prohibited terms compound the gradient penalty, which is desirable.

    A term appearing multiple times still counts as one — the question
    is whether the term is used at all.
    """
    text = caption.lower()
    count = 0
    for term in PROHIBITED_TERMS:
        if len(term) <= 2:
            # Word-boundary regex for 1-2 letter terms (only "ia" today)
            if re.search(r"\b" + re.escape(term) + r"\b", text):
                count += 1
        else:
            # Plain substring for 3+ letter terms
            if term in text:
                count += 1
    return count


def _score_post(post: PlatformPost) -> float:
    """Compute a 0.0–1.0 confidence score for a single post.

    Four equal-weighted criteria (0.25 each):
        - char_count within platform max
        - hashtag count within platform min/max range
        - prohibited-term gradient: 0.25 × max(0, 1 - 0.1 × count)
        - image_brief is non-empty
    """
    spec = PLATFORM_SPECS[post.platform]
    score = 0.0

    if post.char_count <= spec["max_chars"]:
        score += 0.25

    hashtag_count = len(post.hashtags)
    if spec["min_hashtags"] <= hashtag_count <= spec["max_hashtags"]:
        score += 0.25

    proh = _count_prohibited_terms(post.caption)
    score += 0.25 * max(0.0, 1.0 - 0.1 * proh)

    if post.image_brief.strip():
        score += 0.25

    return score


def _build_user_prompt(
    brief: ResearchBrief,
    revision_note: Optional[str],
    previous_posts: dict[str, Any],
) -> str:
    """Build the user message sent to Claude.

    For fresh writes: just the brief + platform spec table + output schema.
    For revisions: prepends the previous posts + the revision note so Claude
    can incorporate the feedback exactly.
    """
    sections: list[str] = []

    if revision_note:
        # Serialise previous posts (handle either PlatformPost objects or dicts
        # since the state dict may have been re-hydrated from JSON)
        prev_serialised: dict[str, dict] = {}
        for name, p in previous_posts.items():
            if isinstance(p, PlatformPost):
                prev_serialised[name] = {
                    "caption": p.caption,
                    "hashtags": p.hashtags,
                    "image_brief": p.image_brief,
                }
            elif isinstance(p, dict):
                prev_serialised[name] = {
                    "caption": p.get("caption", ""),
                    "hashtags": p.get("hashtags", []),
                    "image_brief": p.get("image_brief", ""),
                }

        sections.append(
            "This is a REVISION. You wrote these posts previously:\n\n"
            f"{json.dumps(prev_serialised, indent=2, ensure_ascii=False)}\n\n"
            "The reviewer requested this change:\n"
            f'"{revision_note}"\n\n'
            "Generate revised versions respecting the revision request EXACTLY.\n"
        )

    sections.append(
        "Write 4 social media posts in European Portuguese (pt-PT) about:\n\n"
        f"Topic: {brief.topic}\n"
        f"Source: {brief.source_url}\n"
        f"Summary: {brief.summary}\n"
        f"Suggested angles: {' / '.join(brief.content_angles)}\n\n"
        "Generate one post per platform: instagram, linkedin, facebook, tiktok.\n\n"
        "Platform constraints (respect EXACTLY):\n"
        "- instagram: ≤2200 chars, 5-10 hashtags, Hook + body + CTA\n"
        "- linkedin: ≤3000 chars, 3-5 hashtags, professional insight format\n"
        "- facebook: ≤63206 chars, 2-5 hashtags, conversational\n"
        "- tiktok: ≤2200 chars, 3-7 hashtags, punchy and direct\n\n"
        "Output a JSON array with exactly 4 items, each:\n"
        "{\n"
        '  "platform": "instagram" | "linkedin" | "facebook" | "tiktok",\n'
        '  "caption": "<post text>",\n'
        '  "hashtags": ["#tag1", "#tag2"],\n'
        '  "image_brief": "<visual direction for the image>"\n'
        "}\n\n"
        "Return JSON only. No prose, no markdown fences."
    )

    return "\n".join(sections)


def _parse_posts(raw_json: str) -> dict[str, PlatformPost]:
    """Parse Claude's JSON array into {platform_name: PlatformPost}.

    Strips ```json...``` fences if Claude wraps the output. Raises ValueError
    on structural issues; Pydantic raises ValidationError on field-level issues.
    """
    text = raw_json.strip()

    if text.startswith("```"):
        first_nl = text.find("\n")
        text = text[first_nl + 1:] if first_nl >= 0 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip().rsplit("```", 1)[0]
        text = text.strip()

    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array, got {type(data).__name__}")

    posts: dict[str, PlatformPost] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each post must be an object, got {type(item).__name__}")
        post = PlatformPost(**item)
        posts[post.platform.value] = post

    return posts


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    """Convert a FaultHandler AgentOutput into a WRITER state delta."""
    return {
        "current_agent": "writer",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "writer",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


async def writer_node(state: SocialAgentState) -> dict:
    """WRITER — generate one post per platform for SCOUT's selected topic.

    Returns a state delta. On revision (when revision_note is set), increments
    revision_count and clears revision_note so a subsequent rejection produces
    a clean signal.
    """
    session_id = state["session_id"]
    logger.info("WRITER start", extra={"session_id": session_id})

    handler = FaultHandler()

    # Step 1: must have a selected_topic from SCOUT
    selected: Optional[ResearchBrief] = state.get("selected_topic")
    if selected is None:
        logger.warning("WRITER no selected_topic")
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_topic"}, retry_count=0),
            "no selected_topic in state",
        )

    # Step 2: revision mode?
    revision_note = state.get("revision_note")
    previous_posts = state.get("posts") or {}
    is_revision = bool(revision_note)

    if is_revision:
        logger.info(
            "WRITER revision mode",
            extra={"session_id": session_id, "note_preview": (revision_note or "")[:120]},
        )

    # Step 3: build user prompt
    user_prompt = _build_user_prompt(selected, revision_note, previous_posts)

    # Step 4: single Claude call
    llm = AsyncAnthropic(api_key=settings.anthropic_api_key)
    try:
        response = await llm.messages.create(
            model=settings.writer_model,
            max_tokens=_MAX_TOKENS,
            system=WRITER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # noqa: BLE001 — network/API errors are broad
        logger.error("WRITER LLM call failed", extra={"error": str(exc)})
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "llm"}, retry_count=0),
            exc,
        )

    if not response.content:
        return _fault_state(
            handler.handle(FaultType.SCHEMA_FAULT, {"step": "empty_response"}, retry_count=0),
            "Claude returned empty response",
        )

    raw = response.content[0].text

    # Step 5: parse + Pydantic-validate
    try:
        posts = _parse_posts(raw)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.error(
            "WRITER parse failed",
            extra={"error": str(exc), "raw_preview": raw[:200] if raw else ""},
        )
        return _fault_state(
            handler.handle(FaultType.SCHEMA_FAULT, {"step": "parse"}, retry_count=0),
            exc,
        )

    if not posts:
        return _fault_state(
            handler.handle(FaultType.SCHEMA_FAULT, {"step": "no_posts"}, retry_count=0),
            "Claude returned an empty post list",
        )

    # Step 6: score per-post, average
    per_post_scores = [_score_post(p) for p in posts.values()]
    confidence = sum(per_post_scores) / len(per_post_scores)

    logger.info(
        "WRITER posts generated",
        extra={
            "platforms": list(posts.keys()),
            "confidence": round(confidence, 3),
            "revision": is_revision,
        },
    )

    # Step 7: state delta
    delta: dict[str, Any] = {
        "current_agent": "writer",
        "action": ActionType.REQUEST_APPROVAL,
        "status": StatusType.TASK_COMPLETE,
        "confidence": confidence,
        "posts": posts,
    }

    if is_revision:
        delta["revision_count"] = state.get("revision_count", 0) + 1
        # Clear the note so the next loop starts clean unless REVISOR rejects again
        delta["revision_note"] = None

    return delta
