"""Unit tests for the REVISOR agent node.

All external dependencies (AsyncAnthropic, ai_detection.score_text,
whatsapp.send_text, SupabaseMemory) are stubbed.
"""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.agents.revisor import node as revisor
from src.protocols.io_schema import CarouselOutput, CarouselSlide, PlatformPost
from src.protocols.vocabulary import ActionType, Platform, StatusType


def _load_cases(filename: str) -> list[dict]:
    path = Path(__file__).parent / "datasets" / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["cases"]


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


# ---------------------------------------------------------------------------
# Group A — defence-in-depth checks (G1 + G2 + G3 + G4)
# ---------------------------------------------------------------------------


async def test_revisor_platform_compliance_instagram(base_state):
    """Instagram caption over 2200 chars → routed back to WRITER with issues."""
    # Replace the Instagram post with an over-limit caption (3000 chars)
    state = {
        **base_state,
        "posts": {
            **base_state["posts"],
            "instagram": PlatformPost(
                platform=Platform.INSTAGRAM,
                caption="a" * 3000,  # 3000 chars > 2200 IG limit
                hashtags=["#a", "#b", "#c", "#d", "#e"],
                image_brief="brief",
            ),
        },
    }
    judge = _fake_claude_judge(score=0.95, issues=[])  # judge says clean
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge, ai_detection_score=0.2,  # also clean on AI side
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(state)

    # Compliance violation → QUALITY-FLAG branch
    assert result["approval_decision"] == "revision_requested"
    assert result["pending_approval"] is False
    assert result["status"] == StatusType.BLOCKED
    assert result["action"] == ActionType.DELEGATE_AGENT
    # Note mentions the char overflow
    note = result.get("revision_note", "")
    assert "instagram" in note.lower()
    assert "3000" in note
    assert "2200" in note
    # No WhatsApp sent on the quality-flag path
    ws.assert_not_awaited()


async def test_revisor_platform_compliance_linkedin(base_state):
    """LinkedIn post with 10 hashtags → routed back to WRITER (LI max is 5)."""
    state = {
        **base_state,
        "posts": {
            **base_state["posts"],
            "linkedin": PlatformPost(
                platform=Platform.LINKEDIN,
                caption="Reflexão profissional sobre processos digitais.",
                hashtags=[f"#tag{i}" for i in range(10)],  # 10 hashtags > 5 max
                image_brief="brief",
            ),
        },
    }
    judge = _fake_claude_judge(score=0.95, issues=[])
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge, ai_detection_score=0.2,
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(state)

    assert result["approval_decision"] == "revision_requested"
    assert result["pending_approval"] is False
    note = result.get("revision_note", "")
    assert "linkedin" in note.lower()
    assert "10 hashtags" in note  # exact phrasing from the helper
    ws.assert_not_awaited()


async def test_revisor_prohibited_terms(base_state):
    """Any prohibited term in any caption → routed back to WRITER."""
    state = {
        **base_state,
        "posts": {
            **base_state["posts"],
            "facebook": PlatformPost(
                platform=Platform.FACEBOOK,
                caption="O chatbot vai mudar tudo — IA aplicada no escritório.",
                hashtags=["#a", "#b", "#c"],
                image_brief="brief",
            ),
        },
    }
    judge = _fake_claude_judge(score=0.95, issues=[])
    patches, _, ws, _ = _patch_revisor_deps(
        judge_response=judge, ai_detection_score=0.2,  # clean AI score
    )

    with patches[0], patches[1], patches[2], patches[3]:
        result = await revisor.revisor_node(state)

    # Caught by the prohibited-terms guard, not the AI-flag guard
    assert result["approval_decision"] == "revision_requested"
    assert result["pending_approval"] is False
    note = result.get("revision_note", "")
    assert "facebook" in note.lower()
    assert "prohibited" in note.lower()
    ws.assert_not_awaited()


# ---------------------------------------------------------------------------
# Dataset-driven tests
# ---------------------------------------------------------------------------


def _posts_from_yaml(posts_raw: dict) -> dict[str, PlatformPost]:
    return {plat: PlatformPost(**data) for plat, data in posts_raw.items()}


def _carousel_from_yaml(carousel_raw: dict | None) -> CarouselOutput | None:
    if not carousel_raw:
        return None
    slides = [CarouselSlide(**s) for s in carousel_raw.get("slides", [])]
    return CarouselOutput(
        carousel_title=carousel_raw["carousel_title"],
        platform=carousel_raw["platform"],
        slides=slides,
        caption=carousel_raw["caption"],
        hashtags=carousel_raw["hashtags"],
    )


def _build_revisor_state(inp: dict) -> dict:
    posts_raw = inp.get("posts", {})
    posts = _posts_from_yaml(posts_raw) if posts_raw else {}
    carousel = _carousel_from_yaml(inp.get("carousel"))

    return {
        "session_id": inp.get("session_id", "ds-revisor-test"),
        "run_date": inp.get("run_date", "2026-05-23"),
        "research_briefs": [],
        "selected_topic": None,
        "selected_pillar": None,
        "posts": posts,
        "carousel": carousel,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": inp.get("revision_count", 0),
        "publication_results": [],
        "current_agent": "carousel",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


@pytest.mark.parametrize("case", _load_cases("revisor_cases.yaml"), ids=lambda c: c["id"])
async def test_revisor_dataset(case):
    """Parametrized test driven by tests/datasets/revisor_cases.yaml."""
    mocks = case.get("mocks", {})
    inp = case.get("input", {})

    # Apply revision_count from mocks if specified (used for loop-fault scenarios)
    inp.setdefault("revision_count", mocks.get("revision_count", 0))

    state = _build_revisor_state(inp)

    judge_score = mocks.get("judge_score", 0.85)
    judge_issues = mocks.get("judge_issues", [])
    ai_score = mocks.get("ai_detection_score", 0.20)
    ai_raises = mocks.get("ai_detection_raises", False)
    wa_raises = mocks.get("whatsapp_raises", False)

    judge_resp = MagicMock()
    judge_resp.content = [MagicMock(text=json.dumps({"score": judge_score, "issues": judge_issues}))]

    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=judge_resp)

    ai_mock = (
        AsyncMock(side_effect=Exception("GPTZero unavailable"))
        if ai_raises
        else AsyncMock(return_value=ai_score)
    )
    wa_mock = (
        AsyncMock(side_effect=Exception("WhatsApp unreachable"))
        if wa_raises
        else AsyncMock(return_value={"status": "sent"})
    )

    supa_mock = AsyncMock()
    supa_mock.log_review = AsyncMock(return_value="row-id")

    patches = [
        patch.object(revisor, "AsyncAnthropic", return_value=mock_llm),
        patch.object(revisor.ai_detection, "score_text", new=ai_mock),
        patch.object(revisor.whatsapp, "send_text", new=wa_mock),
        patch.object(revisor, "SupabaseMemory", return_value=supa_mock),
    ]

    with ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        result = await revisor.revisor_node(state)

    exp = case["expected_output"]
    result_action = result["action"].value if hasattr(result["action"], "value") else result["action"]
    result_status = result["status"].value if hasattr(result["status"], "value") else result["status"]

    assert result_action == exp["action"], (
        f"[{case['id']}] action: got {result_action!r}, want {exp['action']!r}"
    )
    assert result_status == exp["status"], (
        f"[{case['id']}] status: got {result_status!r}, want {exp['status']!r}"
    )
    conf = result.get("confidence", 0)
    assert exp["confidence_min"] <= conf <= exp["confidence_max"], (
        f"[{case['id']}] confidence {conf} not in "
        f"[{exp['confidence_min']}, {exp['confidence_max']}]"
    )

    behavior = case["expected_behavior"]
    if behavior.get("should_escalate"):
        assert result_action == "escalate_human" or result.get("approval_decision") == "rejected", (
            f"[{case['id']}] expected escalation/rejection, got action={result_action!r}"
        )
    if behavior.get("should_block"):
        assert result_status in ("blocked", "failed"), (
            f"[{case['id']}] expected block/fail, got status={result_status!r}"
        )
