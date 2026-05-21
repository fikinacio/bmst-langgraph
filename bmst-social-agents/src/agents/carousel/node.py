"""CAROUSEL agent node — designs an Instagram-native slide carousel.

Pipeline:
    1. Read selected_topic from state (set by SCOUT)
    2. Single Claude call produces a JSON CarouselOutput (5–7 slides, hook +
       body slides + CTA), Pydantic-validated
    3. Generate one Canva image per slide in parallel; the Canva wrapper
       already returns None on failure (it doesn't raise), so missing
       images degrade gracefully instead of failing the agent
    4. Confidence drops with each missing slide image:
           confidence = max(0.2, 1.0 - 0.15 × failure_count)
       0 failures → 1.0,  2 failures → 0.70,  3+ failures → < 0.70
    5. Return state delta with the carousel; status TASK_COMPLETE even
       when some images are missing (graceful degradation)

Platform handling:
    The CarouselOutput schema carries a single platform value. We set it to
    Platform.INSTAGRAM because carousels are an Instagram-native format.
    PUBLISHER can reuse the same slide URLs + caption on LinkedIn as a
    multi-image post — that's PUBLISHER's responsibility, not CAROUSEL's.

Prohibited terms and brand voice are imported from WRITER so the two
agents share a single source of truth.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from anthropic import AsyncAnthropic
from pydantic import ValidationError

from src.agents.writer.node import (
    PROHIBITED_TERMS,  # noqa: F401 — imported for visibility / docs reference
)
from src.config.settings import settings
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import AgentOutput, CarouselOutput, CarouselSlide
from src.protocols.vocabulary import ActionType, FaultType, Platform, StatusType
from src.tools import canva_mcp

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt and constants
# ---------------------------------------------------------------------------

# Verbatim from spec, with "automação" struck from the prohibited list to
# match WRITER's resolved rule — both agents now share the same 6 forbidden
# terms (ia, inteligência artificial, algoritmo, chatbot, bot, machine learning).
CAROUSEL_SYSTEM_PROMPT = """
You are CAROUSEL, a carousel content agent for BMST — Bisca Mais Sistemas e Tecnologias.

You design educational carousel posts for Instagram and LinkedIn.

Rules:
- Slide 1 is always a hook: a bold question or statement that stops the scroll
- Each slide has exactly ONE idea
- Max 30 words per slide body. Less is better.
- Last slide always has a CTA
- Language: European Portuguese (pt-PT)
- Voice: Fidel Inácio Kussunga — direct, concrete, no buzzwords
- Never use: "IA", "inteligência artificial", "algoritmo", "chatbot", "bot", "machine learning"
- "automação" is allowed — it is a core topic of this content

Visual direction: BMST brand — dark professional feel, azure blue (#1a4a6b), teal (#2a8a7a), orange accents (#d4601a).

Output: JSON matching CarouselOutput schema. Nothing else.
""".strip()


# BMST brand palette passed to every Canva slide generation call.
BMST_BRAND_COLORS: dict[str, str] = {
    "azure": "#1a4a6b",
    "teal": "#2a8a7a",
    "orange": "#d4601a",
}

# Target slide count window (soft — Pydantic enforces 3–10 hard bounds).
_TARGET_SLIDE_MIN: int = 5
_TARGET_SLIDE_MAX: int = 7

# Confidence formula constants
_CONFIDENCE_FAILURE_PENALTY: float = 0.15
_CONFIDENCE_FLOOR: float = 0.2

# Claude generation settings — 5–7 slides at ~30 words each is small;
# 2048 leaves headroom for the JSON envelope and caption.
_MAX_TOKENS: int = 2048


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_user_prompt(brief) -> str:
    """Build the user message sent to Claude for carousel structuring."""
    return (
        "Design an educational carousel (5–7 slides) on this topic:\n\n"
        f"Topic: {brief.topic}\n"
        f"Source: {brief.source_url}\n"
        f"Summary: {brief.summary}\n"
        f"Suggested angles: {' / '.join(brief.content_angles)}\n\n"
        "Structure:\n"
        "- Slide 1: hook (bold question or statement)\n"
        "- Middle slides: one key insight per slide, ≤30 words body\n"
        "- Final slide: CTA (follow Fidel, comment, or contact BMST)\n\n"
        "Output JSON matching this schema EXACTLY:\n"
        "{\n"
        '  "carousel_title": "<short title>",\n'
        '  "platform": "instagram",\n'
        '  "slides": [\n'
        "    {\n"
        '      "slide_number": 1,\n'
        '      "headline": "<short headline>",\n'
        '      "body": "<≤30 words>",\n'
        '      "visual_brief": "<visual direction for the slide image>",\n'
        '      "canva_asset_url": null\n'
        "    }\n"
        "    // … 5 to 7 slides total …\n"
        "  ],\n"
        '  "caption": "<caption suitable for both Instagram and LinkedIn>",\n'
        '  "hashtags": ["#tag1", "#tag2", "#tag3"]\n'
        "}\n\n"
        'platform must be "instagram". canva_asset_url must be null in your '
        "output — it is filled in later. Return JSON only, no prose, no fences."
    )


def _parse_carousel(raw_json: str) -> CarouselOutput:
    """Parse Claude's response into a CarouselOutput.

    Strips ```json...``` fences if present. Pydantic validates slide count
    bounds (3–10), body word count (≤30), and field types.
    """
    text = raw_json.strip()

    if text.startswith("```"):
        first_nl = text.find("\n")
        text = text[first_nl + 1:] if first_nl >= 0 else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip().rsplit("```", 1)[0]
        text = text.strip()

    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object, got {type(data).__name__}")

    # Force platform to instagram even if Claude tried something else
    data["platform"] = Platform.INSTAGRAM.value

    return CarouselOutput(**data)


async def _generate_slide_image(
    slide: CarouselSlide,
    total_slides: int,
) -> Optional[str]:
    """Generate one slide image via Canva. Returns None on any failure.

    The canva_mcp wrapper already handles errors internally (it returns
    None rather than raising). We use that contract directly.
    """
    try:
        return await canva_mcp.generate_carousel_slide(
            headline=slide.headline,
            body=slide.body,
            visual_brief=slide.visual_brief,
            brand_colors=BMST_BRAND_COLORS,
            slide_number=slide.slide_number,
            total_slides=total_slides,
        )
    except Exception as exc:  # noqa: BLE001 — defensive: shouldn't happen since wrapper catches
        logger.error(
            "Canva slide generation raised unexpectedly",
            extra={"slide_number": slide.slide_number, "error": str(exc)},
        )
        return None


def _compute_confidence(failure_count: int) -> float:
    """Apply the failure-count penalty with a floor."""
    return max(
        _CONFIDENCE_FLOOR,
        1.0 - _CONFIDENCE_FAILURE_PENALTY * failure_count,
    )


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    """Convert a FaultHandler AgentOutput into a CAROUSEL state delta."""
    return {
        "current_agent": "carousel",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "carousel",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


async def carousel_node(state: SocialAgentState) -> dict:
    """CAROUSEL — produce a 5–7 slide carousel + Canva images for SCOUT's topic."""
    session_id = state["session_id"]
    logger.info("CAROUSEL start", extra={"session_id": session_id})

    handler = FaultHandler()

    # Step 1: must have a selected_topic from SCOUT
    selected = state.get("selected_topic")
    if selected is None:
        logger.warning("CAROUSEL no selected_topic")
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_topic"}, retry_count=0),
            "no selected_topic in state",
        )

    # Step 2: Claude call for carousel structure
    llm = AsyncAnthropic(api_key=settings.anthropic_api_key)
    user_prompt = _build_user_prompt(selected)

    try:
        response = await llm.messages.create(
            model=settings.writer_model,
            max_tokens=_MAX_TOKENS,
            system=CAROUSEL_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("CAROUSEL LLM call failed", extra={"error": str(exc)})
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

    # Step 3: parse + Pydantic-validate
    try:
        carousel = _parse_carousel(raw)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        logger.error(
            "CAROUSEL parse failed",
            extra={"error": str(exc), "raw_preview": (raw or "")[:200]},
        )
        return _fault_state(
            handler.handle(FaultType.SCHEMA_FAULT, {"step": "parse"}, retry_count=0),
            exc,
        )

    # Soft warning if slide count is outside the 5–7 target (Pydantic already
    # enforced the 3–10 hard bounds upstream).
    n = len(carousel.slides)
    if not (_TARGET_SLIDE_MIN <= n <= _TARGET_SLIDE_MAX):
        logger.warning(
            "CAROUSEL slide count outside target window",
            extra={"slide_count": n, "target_min": _TARGET_SLIDE_MIN, "target_max": _TARGET_SLIDE_MAX},
        )

    # Step 4: parallel Canva image generation
    image_tasks = [_generate_slide_image(s, n) for s in carousel.slides]
    urls = await asyncio.gather(*image_tasks)

    # Step 5: attach URLs + count failures
    failure_count = 0
    for slide, url in zip(carousel.slides, urls):
        slide.canva_asset_url = url
        if url is None:
            failure_count += 1

    confidence = _compute_confidence(failure_count)

    logger.info(
        "CAROUSEL complete",
        extra={
            "session_id": session_id,
            "slides": n,
            "image_failures": failure_count,
            "confidence": round(confidence, 3),
        },
    )

    # Step 6: state delta. status is always TASK_COMPLETE — Canva failures
    # degrade confidence but don't fault the agent.
    return {
        "current_agent": "carousel",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": confidence,
        "carousel": carousel,
    }
