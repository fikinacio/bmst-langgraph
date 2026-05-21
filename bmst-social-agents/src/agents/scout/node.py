"""SCOUT agent node — daily news research and topic selection.

Pipeline:
    1. Run all 7 Tavily search queries in parallel (last 24h, news topic)
    2. Drop results whose title overlaps with a topic published in the
       previous 7 days (substring match, only on topics >= 10 chars)
    3. Drop results with relevance score < 0.6
    4. Classify each remaining result as 'ai' or 'automation' by keyword
       count; prioritise the pillar opposite to yesterday's selection
    5. Sort: target-pillar first, then by score descending
    6. Build a full ResearchBrief for the top result via Claude
    7. Persist the brief to Redis (24h TTL) and return state delta

All fault paths route through FaultHandler and translate the returned
AgentOutput into a state delta with appropriate status / errors entry.
"""

import asyncio
import json
import logging
from typing import Any, Optional

from anthropic import AsyncAnthropic

from src.config.settings import settings
from src.memory.redis_client import RedisMemory
from src.memory.supabase_client import SupabaseMemory
from src.orchestrator.state import SocialAgentState
from src.protocols.fault_handler import FaultHandler
from src.protocols.io_schema import AgentOutput, ResearchBrief
from src.protocols.vocabulary import ActionType, FaultType, StatusType
from src.tools import news_search

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# System prompt and constants
# ---------------------------------------------------------------------------

SCOUT_SYSTEM_PROMPT = """
You are SCOUT, a news research agent for BMST — Bisca Mais Sistemas e Tecnologias.

Your role: Research and curate the most relevant daily AI news for the Angolan business audience.

Your output must always be:
1. Based only on real news from the last 24 hours
2. Relevant to African or Angolan business context
3. Structured as a research brief with topic, summary, content angles, and platform fit

You never fabricate news. If you cannot find relevant news, you report that clearly.
You never write social media content. That is not your job.

Output format: JSON matching the ResearchBrief schema. Nothing else.
""".strip()


QUERIES: list[str] = [
    "artificial intelligence Africa business 2025",
    "AI automation Angola technology",
    "business process automation Africa 2025",
    "workflow automation SME Angola",
    "digital transformation business Angola",
    "process efficiency technology Africa",
    "RPA robotic process automation Africa",
]


# Keyword sets used by _classify_pillar(). Lowercased; multi-word tokens are matched as substrings.
AI_KEYWORDS: set[str] = {
    "ai", "artificial intelligence", "ia", "genai", "llm",
    "ml", "machine learning", "deep learning", "neural network",
    "generative ai", "claude", "gpt",
}

AUTOMATION_KEYWORDS: set[str] = {
    "automation", "automação", "rpa", "robotic process",
    "workflow", "n8n", "zapier", "integration", "make.com",
    "business process", "process efficiency",
}


# Minimum length for a published-topic string to participate in dedup matching.
# Topics shorter than this are skipped to avoid false-positive substring hits
# (e.g. the string "AI" would match almost every search result).
_DEDUP_MIN_TOPIC_LENGTH: int = 10

# Minimum Tavily relevance score to consider a result viable
_MIN_RELEVANCE_SCORE: float = 0.6

# Redis TTL for the selected_topic cache (24h)
_SELECTED_TOPIC_TTL_SECONDS: int = 86400


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _classify_pillar(result: dict, last_pillar: Optional[str]) -> str:
    """Classify a Tavily result as 'ai' or 'automation' by keyword frequency.

    Counts AI vs automation keyword occurrences in the result's title and
    content. On a tie (including zero matches on both sides), prefer the
    pillar opposite to last_pillar so rotation continues. When last_pillar
    is None, default to 'ai'.
    """
    text = (
        (result.get("title", "") or "") + " " + (result.get("content", "") or "")
    ).lower()

    ai_count = sum(1 for kw in AI_KEYWORDS if kw in text)
    auto_count = sum(1 for kw in AUTOMATION_KEYWORDS if kw in text)

    if ai_count > auto_count:
        return "ai"
    if auto_count > ai_count:
        return "automation"

    # Tie or no matches — use rotation default
    if last_pillar == "ai":
        return "automation"
    if last_pillar == "automation":
        return "ai"
    return "ai"


def _dedupe_against_published(
    results: list[dict],
    published_topics: list[str],
) -> list[dict]:
    """Drop results whose title overlaps with a recently published topic.

    Substring match (case-insensitive) in either direction. Only published
    topics with at least _DEDUP_MIN_TOPIC_LENGTH characters participate —
    shorter strings would cause false positives across unrelated results.
    """
    significant = [
        t.lower() for t in published_topics
        if len(t) >= _DEDUP_MIN_TOPIC_LENGTH
    ]
    if not significant:
        return results

    filtered: list[dict] = []
    for r in results:
        title_lower = (r.get("title", "") or "").lower()
        if not title_lower:
            filtered.append(r)
            continue

        is_duplicate = any(
            topic in title_lower or title_lower in topic
            for topic in significant
        )
        if not is_duplicate:
            filtered.append(r)

    return filtered


async def _build_brief(result: dict, llm: AsyncAnthropic) -> ResearchBrief:
    """Build a full ResearchBrief from a Tavily result via Claude.

    The Tavily relevance score is passed in as context; Claude returns its
    own relevance_score in the brief, which may differ slightly after
    reading the article. Pydantic validates summary length (<=150 words).

    # TODO: add scout_model to settings (e.g. claude-haiku)
    # to reduce cost on daily summarisation calls
    """
    user_prompt = (
        "Build a research brief for this article.\n\n"
        f"Title: {result.get('title', '')}\n"
        f"URL: {result.get('url', '')}\n"
        f"Content: {(result.get('content', '') or '')[:3000]}\n"
        f"Tavily relevance: {result.get('score', 0.0)}\n\n"
        "Respond with JSON only, matching this schema exactly:\n"
        "{\n"
        '  "topic": "<short topic title>",\n'
        '  "source_url": "<article URL>",\n'
        '  "summary": "<max 150 words, in Portuguese (pt-PT)>",\n'
        '  "relevance_score": <float between 0 and 1>,\n'
        '  "content_angles": ["<angle 1>", "<angle 2>", "<angle 3>"],\n'
        '  "platforms_fit": ["linkedin", "instagram"]\n'
        "}\n\n"
        "platforms_fit values must be lowercase from: "
        "instagram, linkedin, facebook, tiktok.\n"
        "Provide 3 to 5 content_angles. No prose outside the JSON."
    )

    response = await llm.messages.create(
        model=settings.writer_model,
        max_tokens=1024,
        system=SCOUT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    if not response.content:
        raise ValueError("Claude returned empty response for brief")

    raw = response.content[0].text.strip()

    # Strip code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        # Remove opening fence (e.g. ```json\n)
        first_newline = raw.find("\n")
        raw = raw[first_newline + 1:] if first_newline >= 0 else raw[3:]
        # Remove closing fence
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    data = json.loads(raw)
    return ResearchBrief(**data)


def _fault_state(fault_output: AgentOutput, error_context: Any) -> dict:
    """Convert a FaultHandler AgentOutput into a SCOUT state delta."""
    return {
        "current_agent": "scout",
        "action": fault_output.action,
        "status": fault_output.status,
        "confidence": fault_output.confidence,
        "errors": [
            {
                "agent": "scout",
                "fault": fault_output.block_internal,
                "context": str(error_context)[:500],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


async def scout_node(state: SocialAgentState) -> dict:
    """SCOUT — research the day's top AI/automation topic for Angola.

    Returns a state delta (partial SocialAgentState dict) that LangGraph
    merges into the running state.
    """
    session_id = state["session_id"]
    logger.info("SCOUT start", extra={"session_id": session_id})

    handler = FaultHandler()

    # Connect persistence clients
    redis_mem = RedisMemory()
    supa = SupabaseMemory()
    try:
        await redis_mem.connect()
        await supa.connect()
    except Exception as exc:  # noqa: BLE001 — connection failure is broad on purpose
        logger.error("SCOUT connect failed", extra={"error": str(exc)})
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "connect"}, retry_count=0),
            exc,
        )

    llm = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Step 1: run all 7 queries in parallel
    search_tasks = [
        news_search.search_ai_news(q, days=1, max_results=10)
        for q in QUERIES
    ]
    search_outputs = await asyncio.gather(*search_tasks, return_exceptions=True)

    all_results: list[dict] = []
    failures = 0
    for query, out in zip(QUERIES, search_outputs):
        if isinstance(out, Exception):
            failures += 1
            logger.warning(
                "Tavily query failed",
                extra={"query": query, "error": str(out)},
            )
            continue
        all_results.extend(out)

    if failures == len(QUERIES):
        logger.error("SCOUT all Tavily queries failed")
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "tavily"}, retry_count=0),
            "all 7 Tavily queries failed",
        )

    logger.info(
        "SCOUT search complete",
        extra={"total_results": len(all_results), "failed_queries": failures},
    )

    # Step 1b: URL-level dedup across the 7 queries. Tavily often returns
    # the same article for related queries; keep the highest-score entry
    # per URL so downstream stages don't waste effort on duplicates.
    seen: dict[str, dict] = {}
    for r in all_results:
        url = r.get("url", "")
        if not url:
            continue
        if url not in seen or r.get("score", 0.0) > seen[url].get("score", 0.0):
            seen[url] = r
    all_results = list(seen.values())
    logger.info("SCOUT deduped by URL", extra={"unique_results": len(all_results)})

    # Step 2: dedupe against published topics
    try:
        published = await supa.get_published_topics(days=7)
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_published_topics failed, skipping dedup", extra={"error": str(exc)})
        published = []
    deduped = _dedupe_against_published(all_results, published)

    # Step 3: relevance filter
    high_relevance = [r for r in deduped if r.get("score", 0.0) >= _MIN_RELEVANCE_SCORE]
    logger.info(
        "SCOUT filtered",
        extra={
            "after_dedup": len(deduped),
            "after_relevance": len(high_relevance),
        },
    )

    if not high_relevance:
        logger.warning("SCOUT no topics passed filtering")
        return _fault_state(
            handler.handle(FaultType.CONFIDENCE_FAULT, {"step": "no_topics"}, retry_count=0),
            "no relevant topics after dedup+filter",
        )

    # Step 4: pillar classification + rotation
    try:
        last_pillar = await supa.get_last_pillar()
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_last_pillar failed, defaulting", extra={"error": str(exc)})
        last_pillar = None

    for r in high_relevance:
        r["_pillar"] = _classify_pillar(r, last_pillar)

    target_pillar = "automation" if last_pillar == "ai" else "ai"

    # Sort: target pillar first, then by relevance score descending
    high_relevance.sort(
        key=lambda r: (0 if r["_pillar"] == target_pillar else 1, -r.get("score", 0.0))
    )

    top_result = high_relevance[0]
    logger.info(
        "SCOUT selected",
        extra={
            "title": top_result.get("title", "")[:120],
            "score": top_result.get("score"),
            "pillar": top_result.get("_pillar"),
            "last_pillar": last_pillar,
        },
    )

    # Step 6: build the ResearchBrief for the selected topic
    try:
        selected_brief = await _build_brief(top_result, llm)
    except Exception as exc:  # noqa: BLE001
        logger.error("SCOUT brief build failed", extra={"error": str(exc)})
        return _fault_state(
            handler.handle(FaultType.EXECUTION_FAULT, {"step": "build_brief"}, retry_count=0),
            exc,
        )

    # Step 7: cache selected topic in Redis (24h TTL)
    try:
        await redis_mem.set_working(
            session_id,
            "selected_topic",
            selected_brief.model_dump(mode="json"),
            ttl_seconds=_SELECTED_TOPIC_TTL_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001
        # Caching is best-effort — log but don't fail the agent
        logger.warning("Redis cache write failed", extra={"error": str(exc)})

    # Step 8: return state delta. research_briefs contains only the
    # fully-built brief; building a brief per Tavily result would mean
    # 7×10 = up to 70 Claude calls per run, which isn't worth the cost
    # since only selected_topic is consumed downstream by WRITER.
    return {
        "current_agent": "scout",
        "action": ActionType.COMPLETE,
        "status": StatusType.TASK_COMPLETE,
        "confidence": selected_brief.relevance_score,
        "research_briefs": [selected_brief],
        "selected_topic": selected_brief,
    }
