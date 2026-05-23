"""Unit tests for the WRITER agent node.

All external dependencies (AsyncAnthropic) are stubbed so tests run with
no network and no credentials. tests/conftest.py sets the env vars.
"""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from src.agents.writer import node as writer
from src.protocols.io_schema import PlatformPost, ResearchBrief
from src.protocols.vocabulary import ActionType, Platform, StatusType


def _load_cases(filename: str) -> list[dict]:
    path = Path(__file__).parent / "datasets" / filename
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["cases"]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_brief() -> ResearchBrief:
    return ResearchBrief(
        topic="Automação em empresas angolanas",
        source_url="https://example.com/article",
        summary="Empresas angolanas estão a adoptar fluxos automáticos para "
        "ganhar eficiência operacional.",
        relevance_score=0.85,
        content_angles=[
            "Casos práticos em PMEs",
            "ROI de processos digitais",
            "Erros comuns ao começar",
        ],
        platforms_fit=[Platform.LINKEDIN, Platform.INSTAGRAM],
    )


@pytest.fixture
def base_state(sample_brief) -> dict:
    return {
        "session_id": "test-writer-001",
        "run_date": "2026-05-21",
        "research_briefs": [sample_brief],
        "selected_topic": sample_brief,
        "posts": {},
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "scout",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.85,
        "errors": [],
    }


def _make_post_dict(
    platform: str,
    caption: str = "Hook concreto sobre processos. Corpo prático. CTA claro.",
    hashtags: list[str] | None = None,
    image_brief: str = "Foto de um escritório moderno em Luanda",
) -> dict:
    """Build a PlatformPost-shaped dict valid for the given platform."""
    if hashtags is None:
        # Provide a hashtag count valid for every platform (5 is in every range)
        hashtags = ["#angola", "#tech", "#fidelinacio", "#bmst", "#empreender"]
    return {
        "platform": platform,
        "caption": caption,
        "hashtags": hashtags,
        "image_brief": image_brief,
    }


def _fake_claude_response(posts_payload: list[dict]) -> MagicMock:
    """Build a MagicMock that mimics anthropic Message response shape."""
    response = MagicMock()
    response.content = [MagicMock(text=json.dumps(posts_payload, ensure_ascii=False))]
    return response


def _patch_anthropic(fake_response: MagicMock):
    """Context-manager-friendly patch for AsyncAnthropic inside writer module."""
    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=fake_response)
    return patch.object(writer, "AsyncAnthropic", return_value=mock_llm), mock_llm


# ---------------------------------------------------------------------------
# Tests — main flow
# ---------------------------------------------------------------------------


async def test_writer_fresh_post_all_platforms(base_state):
    """Fresh write: Claude returns 4 valid posts → state has all 4, TASK_COMPLETE."""
    payload = [
        _make_post_dict("instagram"),
        _make_post_dict("linkedin", hashtags=["#angola", "#tech", "#bmst"]),  # 3 = ok
        _make_post_dict("facebook", hashtags=["#angola", "#bmst"]),  # 2 = ok
        _make_post_dict("tiktok"),
    ]
    fake_resp = _fake_claude_response(payload)
    patcher, _ = _patch_anthropic(fake_resp)

    with patcher:
        result = await writer.writer_node(base_state)

    assert result["current_agent"] == "writer"
    assert result["status"] == StatusType.TASK_COMPLETE
    assert result["action"] == ActionType.REQUEST_APPROVAL
    assert set(result["posts"].keys()) == {"instagram", "linkedin", "facebook", "tiktok"}
    assert all(isinstance(p, PlatformPost) for p in result["posts"].values())
    # No revision_count change on a fresh write
    assert "revision_count" not in result
    # All posts are within spec → confidence should be 1.0
    assert result["confidence"] == pytest.approx(1.0)


async def test_writer_revision_with_note(base_state):
    """Revision mode: prompt includes previous posts + note, revision_count increments."""
    # Seed previous posts and a revision note
    previous = {
        "instagram": PlatformPost(
            platform=Platform.INSTAGRAM,
            caption="Versão anterior do post.",
            hashtags=["#a", "#b", "#c", "#d", "#e"],
            image_brief="velho brief",
        ),
    }
    revision_state = {**base_state, "revision_note": "Adicionar exemplos concretos", "posts": previous}

    payload = [
        _make_post_dict("instagram", caption="Versão revista com exemplos concretos. Body. CTA."),
        _make_post_dict("linkedin", hashtags=["#a", "#b", "#c"]),
        _make_post_dict("facebook", hashtags=["#a", "#b"]),
        _make_post_dict("tiktok"),
    ]
    fake_resp = _fake_claude_response(payload)
    patcher, mock_llm = _patch_anthropic(fake_resp)

    with patcher:
        result = await writer.writer_node(revision_state)

    # revision_count: 0 → 1
    assert result["revision_count"] == 1
    # revision_note cleared for next loop
    assert result["revision_note"] is None
    # Verify the prompt actually contained the revision instructions
    sent_messages = mock_llm.messages.create.call_args.kwargs["messages"]
    user_content = sent_messages[0]["content"]
    assert "REVISION" in user_content
    assert "Adicionar exemplos concretos" in user_content
    assert "Versão anterior do post" in user_content


# ---------------------------------------------------------------------------
# Tests — pure helpers (no async, no mocks)
# ---------------------------------------------------------------------------


def test_writer_character_limit_compliance():
    """Posts exceeding the platform char limit lose the char-count quarter-point."""
    spec = writer.PLATFORM_SPECS[Platform.INSTAGRAM]
    overlimit_caption = "a" * (spec["max_chars"] + 100)

    over = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption=overlimit_caption,
        hashtags=["#a", "#b", "#c", "#d", "#e"],  # 5 = valid
        image_brief="brief presente",
    )
    score = writer._score_post(over)
    # Missing char-count quarter → max 0.75 (hashtag + prohibited-clean + image)
    assert score == pytest.approx(0.75)

    # Same post within limits → 1.0
    within = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption="Texto curto e directo.",
        hashtags=["#a", "#b", "#c", "#d", "#e"],
        image_brief="brief presente",
    )
    assert writer._score_post(within) == pytest.approx(1.0)


def test_writer_prohibited_terms_check():
    """Prohibited terms degrade the score on a 0.1-per-term gradient.

    Rule: word boundary only for 1-2 letter terms ("ia"); plain substring
    match for 3+ letter terms (including "bot"). This means "chatbot" in
    a caption counts as 2 violations (chatbot + bot inside it), which is
    intentional — overlapping prohibited terms compound the penalty.

    "ia" must NOT trigger on common Portuguese words like "tecnologia",
    "família", "havia", "experiência" — word boundaries protect against this.
    """
    # "IA" (word-bounded match) + "chatbot" (substring) + "bot" (substring
    # inside "chatbot") = 3 hits.
    text_two = "Falar de IA e usar um chatbot é diferente de automação."
    assert writer._count_prohibited_terms(text_two) == 3

    # "IA" + "chatbot" (inside "chatbots") + "bot" (inside "chatbots") = 3 hits.
    text_one = "Apenas IA, sem chatbots ou outros termos proibidos. A automação é o futuro."
    assert writer._count_prohibited_terms(text_one) == 3

    # Clean text — "experiência" contains "ia" as substring but NOT as a
    # whole word, so the word-boundary check protects it.
    clean = "A automação está a mudar o trabalho em Angola, na minha experiência."
    assert writer._count_prohibited_terms(clean) == 0

    # Word-boundary protection verification — common Portuguese words must not trigger
    for innocent in ["tecnologia", "família", "havia", "ciência", "Maria"]:
        assert writer._count_prohibited_terms(f"Esta {innocent} é importante.") == 0, (
            f"False positive on '{innocent}'"
        )

    # Score impact — intentional separation from the assertions above
    clean_post = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption="Texto limpo sem termos proibidos. Body. CTA.",
        hashtags=["#a", "#b", "#c", "#d", "#e"],
        image_brief="brief",
    )
    assert writer._score_post(clean_post) == pytest.approx(1.0)

    # 3 prohibited terms (ia + chatbot + bot-inside-chatbot)
    dirty_post = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption="A IA e o chatbot vão substituir tudo.",
        hashtags=["#a", "#b", "#c", "#d", "#e"],
        image_brief="brief",
    )
    # 0.25 (chars) + 0.25 (hashtags) + 0.25*(1-0.3)=0.175 + 0.25 (image) = 0.925
    assert writer._score_post(dirty_post) == pytest.approx(0.925)


def test_writer_confidence_calibration():
    """Perfect post → 1.0. Worst possible post → 0.10 (gradient bottom).

    With 6 distinct prohibited terms in the set, hitting all 6 yields
    proh contribution = 0.25 * (1 - 0.1*6) = 0.10. The other three
    criteria contribute 0 each when fully broken. So worst case is 0.10,
    not 0.0 — the prohibited-terms gradient never fully saturates.
    """
    # Fully compliant Instagram post
    perfect = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption="Hook + body + CTA, sem termos proibidos.",
        hashtags=["#a", "#b", "#c", "#d", "#e"],  # 5 = within 5-10
        image_brief="brief presente",
    )
    assert writer._score_post(perfect) == pytest.approx(1.0)

    # Fully broken: over char limit + wrong hashtag count + all 6 prohibited terms + empty image_brief
    long_caption = (
        "IA inteligência artificial algoritmo chatbot bot machine learning "
        * 50  # also way over 2200 chars
    )
    broken = PlatformPost(
        platform=Platform.INSTAGRAM,
        caption=long_caption,
        hashtags=["#one"],  # 1 = under min 5
        image_brief="",  # empty
    )
    # char_count: 0 + hashtag: 0 + proh(6 terms): 0.25*0.4 = 0.10 + image: 0 = 0.10
    assert writer._score_post(broken) == pytest.approx(0.10)


# ---------------------------------------------------------------------------
# Dataset-driven tests
# ---------------------------------------------------------------------------


def _build_writer_state(inp: dict) -> dict:
    """Build SocialAgentState for the WRITER node from YAML input overrides."""
    selected_topic_raw = inp.get("selected_topic")
    selected_topic = ResearchBrief(**selected_topic_raw) if selected_topic_raw else None

    existing_posts_raw = inp.get("existing_posts", {})
    existing_posts = {
        plat: PlatformPost(**data)
        for plat, data in existing_posts_raw.items()
    } if existing_posts_raw else {}

    return {
        "session_id": inp.get("session_id", "ds-writer-test"),
        "run_date": inp.get("run_date", "2026-05-23"),
        "research_briefs": [selected_topic] if selected_topic else [],
        "selected_topic": selected_topic,
        "selected_pillar": inp.get("selected_pillar"),
        "posts": existing_posts,
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": inp.get("revision_note"),
        "revision_count": inp.get("revision_count", 0),
        "publication_results": [],
        "current_agent": "writer",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": 0.9,
        "errors": [],
    }


@pytest.mark.parametrize("case", _load_cases("writer_cases.yaml"), ids=lambda c: c["id"])
async def test_writer_dataset(case):
    """Parametrized test driven by tests/datasets/writer_cases.yaml."""
    mocks = case.get("mocks", {})
    state = _build_writer_state(case.get("input", {}))

    payload = mocks.get("claude_payload", [])
    fake_resp = MagicMock()
    fake_resp.content = [MagicMock(text=json.dumps(payload, ensure_ascii=False))]

    mock_llm = MagicMock()
    mock_llm.messages = MagicMock()
    mock_llm.messages.create = AsyncMock(return_value=fake_resp)

    with patch.object(writer, "AsyncAnthropic", return_value=mock_llm):
        result = await writer.writer_node(state)

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
        assert result_action == "escalate_human", (
            f"[{case['id']}] expected escalation, got action={result_action!r}"
        )
    if behavior.get("should_block"):
        assert result_status in ("blocked", "failed"), (
            f"[{case['id']}] expected block/fail, got status={result_status!r}"
        )
