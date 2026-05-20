"""Redis-backed working memory and short-term memory.

Key namespaces:
    Working memory:    bmst:social:working:{session_id}:{key}  (default TTL 3600s)
    Short-term memory: bmst:social:short:{key}                 (caller-specified TTL)

All values are serialised as JSON. The connection is created once via connect()
and reused for the lifetime of the process.
"""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from src.config.settings import settings

logger = logging.getLogger(__name__)

_KEY_PREFIX = "bmst:social:"


class RedisMemory:
    """Async Redis client for agent working memory and short-term state."""

    def __init__(self) -> None:
        self._client: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Open the async Redis connection and verify it with PING."""
        self._client = await aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("RedisMemory connected to %s", settings.redis_url)

    # ------------------------------------------------------------------
    # Working memory — scoped to a session, default TTL 1 hour
    # ------------------------------------------------------------------

    async def set_working(
        self,
        session_id: str,
        key: str,
        value: dict,
        ttl_seconds: int = 3600,
    ) -> None:
        """Store a dict in session-scoped working memory with a TTL."""
        full_key = f"{_KEY_PREFIX}working:{session_id}:{key}"
        await self._client.set(full_key, json.dumps(value), ex=ttl_seconds)
        logger.debug("set_working key=%s ttl=%ds", full_key, ttl_seconds)

    async def get_working(self, session_id: str, key: str) -> Optional[dict]:
        """Retrieve a dict from session-scoped working memory.

        Returns None if the key does not exist or has expired.
        """
        full_key = f"{_KEY_PREFIX}working:{session_id}:{key}"
        raw = await self._client.get(full_key)
        return json.loads(raw) if raw is not None else None

    # ------------------------------------------------------------------
    # Short-term memory — global scope, caller sets TTL
    # ------------------------------------------------------------------

    async def set_short_term(
        self,
        key: str,
        value: dict,
        ttl_seconds: int,
    ) -> None:
        """Store a dict in short-term memory with a caller-specified TTL."""
        full_key = f"{_KEY_PREFIX}short:{key}"
        await self._client.set(full_key, json.dumps(value), ex=ttl_seconds)
        logger.debug("set_short_term key=%s ttl=%ds", full_key, ttl_seconds)

    async def get_short_term(self, key: str) -> Optional[dict]:
        """Retrieve a dict from short-term memory.

        Returns None if the key does not exist or has expired.
        """
        full_key = f"{_KEY_PREFIX}short:{key}"
        raw = await self._client.get(full_key)
        return json.loads(raw) if raw is not None else None

    # ------------------------------------------------------------------
    # Generic delete — caller provides the full Redis key
    # ------------------------------------------------------------------

    async def delete(self, key: str) -> None:
        """Delete a key from Redis.

        The caller is responsible for providing the full key (including prefix
        if applicable). Use the _KEY_PREFIX constant when constructing keys
        outside this class.
        """
        await self._client.delete(key)
        logger.debug("deleted key=%s", key)
