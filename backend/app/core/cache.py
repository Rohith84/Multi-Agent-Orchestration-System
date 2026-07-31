"""
Redis Cache Adapter.

Provides asynchronous caching for LLM responses, RAG search results, prompt templates, and tool outputs with fallback support when Redis is unreachable.
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Any | None = None
_cache_hits = 0
_cache_misses = 0


async def get_redis_connection() -> Any | None:
    """Lazy initialization of async Redis connection."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        import redis.asyncio as aioredis
        client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        _redis_client = client
        logger.info("Redis cache connected at %s", redis_url)
        return _redis_client
    except Exception as e:
        logger.warning("Redis cache unreachable at %s (%s). Caching disabled.", redis_url, e)
        return None


class RedisCache:
    """
    Caching adapter with in-memory fallback and hit/miss metrics.
    """

    def __init__(self) -> None:
        self._in_memory_fallback: dict[str, str] = {}

    async def get(self, key: str) -> Any | None:
        """Get item from Redis cache or fallback."""
        global _cache_hits, _cache_misses
        try:
            client = await get_redis_connection()
            if client:
                val = await client.get(key)
                if val is not None:
                    _cache_hits += 1
                    logger.debug("Redis Cache HIT for key: %s", key)
                    return json.loads(val)
        except Exception as e:
            logger.debug("Redis cache get failed for %s: %s", key, e)

        # In-memory fallback check
        if key in self._in_memory_fallback:
            _cache_hits += 1
            return json.loads(self._in_memory_fallback[key])

        _cache_misses += 1
        logger.debug("Redis Cache MISS for key: %s", key)
        return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set item in Redis cache with TTL."""
        serialized = json.dumps(value, default=str)
        try:
            client = await get_redis_connection()
            if client:
                await client.setex(key, ttl_seconds, serialized)
                logger.debug("Redis Cache SET key: %s (ttl=%ds)", key, ttl_seconds)
                return
        except Exception as e:
            logger.debug("Redis cache set failed for %s: %s", key, e)

        # Fallback to in-memory store
        self._in_memory_fallback[key] = serialized

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        try:
            client = await get_redis_connection()
            if client:
                await client.delete(key)
        except Exception:
            pass
        self._in_memory_fallback.pop(key, None)

    async def clear(self) -> None:
        """Flush all cache entries."""
        try:
            client = await get_redis_connection()
            if client:
                await client.flushdb()
        except Exception:
            pass
        self._in_memory_fallback.clear()

    async def get_stats(self) -> dict[str, Any]:
        """Return cache hit ratio and metrics."""
        total = _cache_hits + _cache_misses
        hit_ratio = round((_cache_hits / max(1, total)) * 100, 1)
        return {
            "hits": _cache_hits,
            "misses": _cache_misses,
            "total_requests": total,
            "hit_ratio_percentage": hit_ratio,
            "fallback_keys_count": len(self._in_memory_fallback),
        }


# Global cache instance
_cache_instance = RedisCache()


def get_redis_cache() -> RedisCache:
    return _cache_instance
