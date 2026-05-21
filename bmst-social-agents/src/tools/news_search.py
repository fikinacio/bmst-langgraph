"""Tavily search wrapper used by the SCOUT agent.

Tavily is purpose-built for AI agents and returns a relevance `score` per
result, which makes filter_by_relevance trivial. The extract endpoint
gives us a clean fetch_full_article without scraping.
"""

import logging
from typing import Optional

from tavily import AsyncTavilyClient

from src.config.settings import settings

logger = logging.getLogger(__name__)


class TavilyError(Exception):
    """Raised when Tavily returns an error or the SDK throws."""


def _client() -> AsyncTavilyClient:
    """Construct an AsyncTavilyClient lazily, validating the key at call time."""
    if not settings.tavily_api_key:
        raise TavilyError("TAVILY_API_KEY is not configured")
    return AsyncTavilyClient(api_key=settings.tavily_api_key)


async def search_ai_news(
    query: str,
    days: int = 1,
    max_results: int = 10,
) -> list[dict]:
    """Search recent news for `query` using the Tavily news topic.

    Returns a list of result dicts with at least: title, url, content, score.
    Raises TavilyError on any SDK or HTTP failure.
    """
    logger.debug(
        "Tavily search",
        extra={"query": query, "days": days, "max_results": max_results},
    )
    try:
        response = await _client().search(
            query=query,
            topic="news",
            days=days,
            max_results=max_results,
            search_depth="advanced",
        )
    except Exception as exc:
        logger.error("Tavily search failed", extra={"query": query, "error": str(exc)})
        raise TavilyError(f"Tavily search failed: {exc}") from exc

    results: list[dict] = response.get("results", [])
    logger.debug("Tavily returned %d results", len(results))
    return results


def filter_by_relevance(
    results: list[dict],
    min_score: float = 0.6,
) -> list[dict]:
    """Drop results whose Tavily relevance score is below `min_score`."""
    return [r for r in results if r.get("score", 0.0) >= min_score]


async def fetch_full_article(url: str) -> Optional[str]:
    """Extract the full article text from a URL via Tavily's extract endpoint.

    Returns None on failure rather than raising — SCOUT can still proceed
    with the snippet from the search result if extract fails.
    """
    logger.debug("Tavily extract", extra={"url": url})
    try:
        response = await _client().extract(urls=[url])
    except Exception as exc:
        logger.error("Tavily extract failed", extra={"url": url, "error": str(exc)})
        return None

    results = response.get("results", [])
    if not results:
        logger.debug("Tavily extract returned no content for %s", url)
        return None
    return results[0].get("raw_content")
