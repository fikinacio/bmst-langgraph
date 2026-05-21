"""Unit tests for the REVISOR agent node.

All external dependencies (AsyncAnthropic, ai_detection.score_text,
whatsapp.send_text, SupabaseMemory) are stubbed.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.revisor import node as revisor
from src.protocols.io_schema import CarouselOutput, CarouselSlide, PlatformPost
from src.protocols.vocabulary import ActionType, Platform, StatusType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_posts() -> dict[str, PlatformPost]:
    return {
        "instagram": PlatformPost(
            platform=Platform.INSTAGRAM,
            caption="Hook directo sobre processos. Body prático. CTA claro.",
            hashtags=["#a", "#b", "#c", "#d", "#e"],
            image_brief="brief",
        ),
        "linkedin": PlatformPost(
            platform=Platform.LINKEDIN,
            caption="Reflexão profissional sobre automação em PMEs.",
            hashtags=["#a", "#b", "#c"],
            image_brief="brief",
        ),
        "facebook": PlatformPost(
            platform=Platform.FACEBOOK,
            caption="Conversa sobre transformação digital em Luanda.",
            hashtags=["#a", "#b"],
            image_brief="brief",
        ),
        "tiktok": PlatformPost(
            platform=Platform.TIKTOK,
            caption="Resposta rápida sobre eficiência no escritório.",
            hashtags=["#a", "#b", "#c"],
            image_brief="brief",
        ),
    }


@pytest.fixture
def sample_carousel() -> CarouselOutput:
    slides = [
        CarouselSlide(slide_number=i, headline=f"H{i}", body=f"Body {i}", visual_brief="brief")
        for i in range(1, 6)
    ]
    return CarouselOutput(
        carousel_title="Automação para PMEs",
        platform=Platform.INSTAGRAM,
        slides=slides,
        caption="Carousel caption",
        hashtags=["#bmst", "#angola"],
    )


@pytest.fixture
def base_state(sample_posts, sample_carousel) -> dict:
    return {
        "session_id": "test-revisor-001",
        "run_date": "2026-05-21",
        "research_briefs": [],
        "selected_topic": None,
        "posts": sample_posts,
        "carousel": sample_carousel,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "carousel",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


def _fake_claude_judge(score: float = 0.85, issues: list[str] | None = None) -> MagicMock:
    """Build a fake Anthropic response containing the judge's JSON."""
    response = MagicMock()
    payload = {"score": score, "issues": issues or []}
    response.content = [MagicMock(text=json.dumps(payload))]
    return response


def _patch_revisor_deps(
    *,
    judge_response: MagicMock,
    ai_detection_score: float,
    whatsapp_send_text: AsyncMock | None = None,
    supabase_mock: MagicMock | None = None,
):
    """Build the standard set of patches every REVISOR test needs."""
    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=judge_response)

    if whatsapp_send_text is None:
        whatsapp_send_text = AsyncMock(return_value={"status": "sent"})

    if supabase_mock is None:
        supabase_mock = AsyncMock()
        supabase_mock.log_review = AsyncMock(return_value="row-id")

    return [
        patch.object(revisor, "AsyncAnthropic", return_value=mock_llm),
        patch.object(
            revisor.ai_detection, "score_text",
            new=AsyncMock(return_value=ai_detection_score),
        ),
        patch.object(revisor.whatsapp, "send_text", new=whatsapp_send_text),
        patch.object(revisor, "SupabaseMemory", return_value=supabase_mock),
    ], mock_llm, whatsapp_send_text, supabase_mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_revisor_quality_check_runs(base_state):
    """Phase 1a executes: the judge produces a score that lands in review_results."""
    judge = _fake_claude_judge(score=0.92, issues=["minor: tighten Instagram hook"])
    patches, _, _, _ = _patch_revisor_deps(
        judge_response=judge, ai_detection_score=0.3,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(base_state)

    assert "review_results" in result
    assert len(result["review_results"]) == 5  # 4 posts + 1 carousel
    first = result["review_results"][0]
    assert first.quality_score == pytest.approx(0.92)
    assert "minor: tighten Instagram hook" in first.issues


async def test_revisor_ai_detection_flags(base_state):
    """AI score > 0.70 → revision_requested branch, no WhatsApp sent."""
    judge = _fake_claude_judge(score=0.85, issues=[])
    whatsapp_mock = AsyncMock(return_value={"status": "sent"})
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge,
        ai_detection_score=0.85,  # over the 0.70 threshold
        whatsapp_send_text=whatsapp_mock,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(base_state)

    assert result["approval_decision"] == "revision_requested"
    assert result["pending_approval"] is False
    assert result["status"] == StatusType.BLOCKED
    assert "AI-detection score" in (result.get("revision_note") or "")
    # Critical: NO WhatsApp sent on the AI-flag path
    ws.assert_not_awaited()


async def test_revisor_sends_whatsapp_on_clean_content(base_state):
    """Clean AI score → human approval path: WhatsApp sent, pending_approval=True."""
    judge = _fake_claude_judge(score=0.9, issues=[])
    whatsapp_mock = AsyncMock(return_value={"status": "sent"})
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge,
        ai_detection_score=0.2,  # well under threshold
        whatsapp_send_text=whatsapp_mock,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(base_state)

    assert result["pending_approval"] is True
    assert result["status"] == StatusType.NEEDS_APPROVAL
    assert result["action"] == ActionType.REQUEST_APPROVAL
    ws.assert_awaited_once()
    # The phone number sent to is from settings, not hardcoded
    args, kwargs = ws.call_args
    # send_text(to, message) — first positional or keyword 'to'
    sent_to = args[0] if args else kwargs.get("to")
    assert sent_to.startswith("+")  # E.164 format


async def test_revisor_escalates_at_max_revisions(base_state):
    """revision_count >= 3 → escalation WhatsApp containing session_id."""
    state = {**base_state, "revision_count": 3}

    judge = _fake_claude_judge(score=0.5, issues=["something"])
    whatsapp_mock = AsyncMock(return_value={"status": "sent"})
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge,
        ai_detection_score=0.4,  # below AI threshold so we test the revision_count branch
        whatsapp_send_text=whatsapp_mock,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(state)

    assert result["approval_decision"] == "rejected"
    assert result["pending_approval"] is False
    assert result["status"] == StatusType.FAILED
    # Escalation WhatsApp was sent (NOT the regular approval message)
    ws.assert_awaited_once()
    args, kwargs = ws.call_args
    sent_msg = args[1] if len(args) > 1 else kwargs.get("message", "")
    # Must include session_id per the spec
    assert "test-revisor-001" in sent_msg
    assert "ESCALATION" in sent_msg
    assert "Revision count: 3" in sent_msg


async def test_revisor_logs_per_content_piece(base_state):
    """One review_log row per content piece: 4 posts + 1 carousel = 5 calls."""
    judge = _fake_claude_judge(score=0.85, issues=[])

    supabase_mock = AsyncMock()
    supabase_mock.log_review = AsyncMock(return_value="row-id")

    patches, _, _, supa = _patch_revisor_deps(
        judge_response=judge,
        ai_detection_score=0.3,
        supabase_mock=supabase_mock,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(base_state)

    # 4 PlatformPosts + 1 CarouselOutput = 5 review rows
    assert supa.log_review.await_count == 5
    # All ReviewResults share the same session_id
    session_ids = {r.session_id for r in result["review_results"]}
    assert session_ids == {"test-revisor-001"}
    # Each row has a unique review_id
    review_ids = {r.review_id for r in result["review_results"]}
    assert len(review_ids) == 5
