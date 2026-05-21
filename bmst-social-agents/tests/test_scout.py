"""Unit tests for the SCOUT agent node.

These tests stub every external dependency (Tavily, Supabase, Redis,
AsyncAnthropic) so they run without any network or credentials.
pyproject.toml sets asyncio_mode='auto', so async tests need no decoration.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.agents.scout import node as scout
from src.protocols.io_schema import ResearchBrief
from src.protocols.vocabulary import ActionType, Platform, StatusType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def base_state() -> dict:
    """Minimal SocialAgentState for SCOUT entry."""
    return {
        "session_id": "test-session-001",
        "run_date": "2026-05-21",
        "research_briefs": [],
        "selected_topic": None,
        "posts": {},
        "carousel": None,
        "review_results": [],
        "pending_approval": False,
        "approval_decision": None,
        "revision_note": None,
        "revision_count": 0,
        "publication_results": [],
        "current_agent": "scout",
        "action": ActionType.SEND_MESSAGE,
        "status": StatusType.NEEDS_MORE_CONTEXT,
        "confidence": 1.0,
        "errors": [],
    }


@pytest.fixture
def tavily_hit() -> dict:
    return {
        "title": "AI automation transforming Angolan businesses in 2025",
        "url": "https://example.com/ai-angola",
        "content": "Angolan SMEs are adopting AI and workflow automation...",
        "score": 0.85,
    }


@pytest.fixture
def brief() -> ResearchBrief:
    return ResearchBrief(
        topic="AI automation in Angola",
        source_url="https://example.com/ai-angola",
        summary="Empresas angolanas estão a adoptar IA e automação para "
        "ganhar eficiência operacional num mercado competitivo.",
        relevance_score=0.85,
        content_angles=[
            "Caso de uso de RPA em PMEs angolanas",
            "ROI prático da automação de processos",
            "Tendências de IA generativa em África",
        ],
        platforms_fit=[Platform.LINKEDIN, Platform.INSTAGRAM],
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_scout_happy_path(base_state, tavily_hit, brief):
    """Successful run: search → dedupe → filter → select → brief → state."""
    redis_mock = AsyncMock()
    supa_mock = AsyncMock()
    supa_mock.get_published_topics.return_value = []
    supa_mock.get_last_pillar.return_value = "ai"  # last was ai → prefer automation today

    with (
        patch.object(scout.news_search, "search_ai_news", new=AsyncMock(return_value=[tavily_hit])),
        patch.object(scout, "RedisMemory", return_value=redis_mock),
        patch.object(scout, "SupabaseMemory", return_value=supa_mock),
        patch.object(scout, "AsyncAnthropic"),
        patch.object(scout, "_build_brief", new=AsyncMock(return_value=brief)),
    ):
        result = await scout.scout_node(base_state)

    assert result["current_agent"] == "scout"
    assert result["status"] == StatusType.TASK_COMPLETE
    assert result["action"] == ActionType.COMPLETE
    assert result["selected_topic"] == brief
    assert result["research_briefs"] == [brief]
    assert result["confidence"] == pytest.approx(0.85)
    # Selected topic should have been cached
    redis_mock.set_working.assert_awaited_once()
    args, kwargs = redis_mock.set_working.call_args
    assert kwargs.get("ttl_seconds") == 86400 or (len(args) >= 4 and args[3] == 86400)


async def test_scout_no_results(base_state):
    """All Tavily queries succeed but return nothing → CONFIDENCE_FAULT."""
    redis_mock = AsyncMock()
    supa_mock = AsyncMock()
    supa_mock.get_published_topics.return_value = []
    supa_mock.get_last_pillar.return_value = None

    with (
        patch.object(scout.news_search, "search_ai_news", new=AsyncMock(return_value=[])),
        patch.object(scout, "RedisMemory", return_value=redis_mock),
        patch.object(scout, "SupabaseMemory", return_value=supa_mock),
        patch.object(scout, "AsyncAnthropic"),
    ):
        result = await scout.scout_node(base_state)

    # CONFIDENCE_FAULT escalates to human and sets NEEDS_APPROVAL
    assert result["status"] == StatusType.NEEDS_APPROVAL
    assert result["action"] == ActionType.ESCALATE_HUMAN
    assert len(result["errors"]) == 1
    assert result["errors"][0]["agent"] == "scout"


async def test_scout_tavily_failure(base_state):
    """All Tavily queries raise → EXECUTION_FAULT, status FAILED in delta."""
    redis_mock = AsyncMock()
    supa_mock = AsyncMock()
    supa_mock.get_published_topics.return_value = []
    supa_mock.get_last_pillar.return_value = None

    with (
        patch.object(
            scout.news_search,
            "search_ai_news",
            new=AsyncMock(side_effect=Exception("Tavily down")),
        ),
        patch.object(scout, "RedisMemory", return_value=redis_mock),
        patch.object(scout, "SupabaseMemory", return_value=supa_mock),
        patch.object(scout, "AsyncAnthropic"),
    ):
        result = await scout.scout_node(base_state)

    # First EXECUTION_FAULT attempt → WAIT with retry instructions (status BLOCKED)
    # We assert the fault was recorded and routing fields are present
    assert result["current_agent"] == "scout"
    assert "errors" in result and len(result["errors"]) == 1
    assert result["errors"][0]["agent"] == "scout"
    # FaultHandler at retry_count=0 returns WAIT/BLOCKED for EXECUTION_FAULT
    assert result["status"] in (StatusType.BLOCKED, StatusType.FAILED)


# ---------------------------------------------------------------------------
# Pure-function tests (no async / no mocks needed)
# ---------------------------------------------------------------------------


def test_scout_duplicate_topic(tavily_hit):
    """Dedupe drops results overlapping with published topics ≥10 chars."""
    other = {
        "title": "Unique topic about something else entirely",
        "url": "https://other.example.com",
        "content": "...",
        "score": 0.9,
    }

    # Published topic of 27 chars → must filter the matching result
    published = ["AI automation transforming"]
    filtered = scout._dedupe_against_published([tavily_hit, other], published)
    assert len(filtered) == 1
    assert filtered[0] is other

    # Short topic (<10 chars) is skipped during dedup, both retained
    filtered_short = scout._dedupe_against_published([tavily_hit, other], ["AI"])
    assert len(filtered_short) == 2

    # Empty published list short-circuits, both retained
    assert scout._dedupe_against_published([tavily_hit, other], []) == [tavily_hit, other]


def test_classify_pillar_rotation():
    """Tied keyword counts fall back to the pillar opposite last_pillar."""
    neutral = {"title": "Some title", "content": "Generic technology news"}
    # No matches → tie → opposite of last_pillar
    assert scout._classify_pillar(neutral, last_pillar="ai") == "automation"
    assert scout._classify_pillar(neutral, last_pillar="automation") == "ai"
    assert scout._classify_pillar(neutral, last_pillar=None) == "ai"

    # Clear AI-leaning content
    ai_heavy = {"title": "Generative AI and LLM breakthroughs", "content": "ML and deep learning..."}
    assert scout._classify_pillar(ai_heavy, last_pillar="ai") == "ai"

    # Clear automation-leaning content
    auto_heavy = {"title": "RPA and workflow automation", "content": "n8n integration with Zapier..."}
    assert scout._classify_pillar(auto_heavy, last_pillar="automation") == "automation"
