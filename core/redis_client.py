"""
Redis client — session management, message deduplication, HUNTER lock,
and LangGraph checkpointer (RedisSaver for production persistence).
"""
import hashlib
import logging
from functools import lru_cache

import redis
import redis.exceptions
from langgraph.checkpoint.redis import RedisSaver

from core.settings import settings

logger = logging.getLogger(__name__)

# ── Key prefixes ───────────────────────────────────────────────────────────────
_PREFIX_SESSION = "bmst:session:"
_PREFIX_MSG     = "bmst:msg:"
_LOCK_KEY       = "bmst:lock:hunter"


# ── Connection singleton ───────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    """Return a cached Redis client (decode_responses=True)."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_checkpointer() -> RedisSaver:
    """
    Return a LangGraph RedisSaver for interrupt() state persistence.

    RedisSaver.from_conn_string() expects a URL string, not a Redis object.
    In production this is called once in the FastAPI lifespan — interrupted
    graphs can be resumed across restarts because the state lives in Redis.
    In tests, pass MemorySaver() directly to the graph factory instead.
    """
    return RedisSaver.from_conn_string(settings.REDIS_URL)


# ── Helpers ────────────────────────────────────────────────────────────────────

def hash_message(content: str) -> str:
    """Return MD5 hex digest of a message string.

    Used by callers before is_duplicate() / mark_sent() to derive the key.
    MD5 is intentionally used here for speed, not cryptographic security.
    """
    return hashlib.md5(content.encode()).hexdigest()


# ── Session management ─────────────────────────────────────────────────────────

def get_session(key: str) -> str | None:
    """Get a generic session value.  Returns None on error."""
    try:
        return get_redis().get(f"{_PREFIX_SESSION}{key}")
    except redis.exceptions.RedisError as exc:
        logger.error("get_session(%s) failed: %s", key, exc)
        return None


def set_session(key: str, value: str, ttl: int = 3600) -> bool:
    """Set a session value with a TTL (seconds).  Returns False on error."""
    try:
        get_redis().setex(f"{_PREFIX_SESSION}{key}", ttl, value)
        return True
    except redis.exceptions.RedisError as exc:
        logger.error("set_session(%s) failed: %s", key, exc)
        return False


def delete_session(key: str) -> bool:
    """Delete a session key.  Returns False on error."""
    try:
        get_redis().delete(f"{_PREFIX_SESSION}{key}")
        return True
    except redis.exceptions.RedisError as exc:
        logger.error("delete_session(%s) failed: %s", key, exc)
        return False


# ── Message deduplication ──────────────────────────────────────────────────────

def is_duplicate(phone: str, message_hash: str) -> bool:
    """Return True if this message was already processed (exists in Redis).

    On error returns False — safer to process a potential duplicate than to
    silently drop a legitimate message.
    """
    try:
        key = f"{_PREFIX_MSG}{phone}:{message_hash}"
        return bool(get_redis().exists(key))
    except redis.exceptions.RedisError as exc:
        logger.error("is_duplicate(%s) failed: %s", phone, exc)
        return False


def mark_sent(phone: str, message_hash: str) -> bool:
    """Mark a message as sent (TTL=24h).  Returns False on error."""
    try:
        key = f"{_PREFIX_MSG}{phone}:{message_hash}"
        get_redis().setex(key, 86400, "1")
        return True
    except redis.exceptions.RedisError as exc:
        logger.error("mark_sent(%s) failed: %s", phone, exc)
        return False


# ── HUNTER batch lock ──────────────────────────────────────────────────────────

def get_hunter_lock() -> bool:
    """Acquire the HUNTER exclusive lock (atomic SET NX EX 300).

    Returns True  → lock acquired, safe to start a batch run.
    Returns False → another batch is already running, or Redis error.

    The 300-second TTL acts as a safety net: if the process crashes without
    calling release_hunter_lock(), Redis will expire the key automatically.
    """
    try:
        result = get_redis().set(_LOCK_KEY, "1", nx=True, ex=300)
        return result is True
    except redis.exceptions.RedisError as exc:
        logger.error("get_hunter_lock() failed: %s", exc)
        return False


def release_hunter_lock() -> None:
    """Release the HUNTER lock.  Best-effort — errors are logged, not raised."""
    try:
        get_redis().delete(_LOCK_KEY)
    except redis.exceptions.RedisError as exc:
        logger.warning("release_hunter_lock() failed (ignored): %s", exc)
