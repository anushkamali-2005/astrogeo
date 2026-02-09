"""
Cache Service
=============
Redis-based caching layer for application performance:
- Key-value caching
- TTL support
- Invalidation strategies
- Cache statistics

Author: Production Team
Version: 1.0.0
"""

import hashlib
import json
from datetime import timedelta
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from src.core.config import settings
from src.core.exceptions import CacheError
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# CACHE SERVICE
# ============================================================================


class CacheService:
    """
    Redis-based caching service.

    Features:
    - Async Redis operations
    - Automatic JSON serialization
    - TTL support
    - Key prefixing
    - Cache statistics

    Time complexity: O(1) for get/set operations
    Space complexity: Depends on cached data size
    """

    def __init__(self, prefix: str = "astrogeo"):
        """
        Initialize cache service.

        Args:
            prefix: Key prefix for namespacing
        """
        self.prefix = prefix
        self.redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis server."""
        try:
            self.redis = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True,
                max_connections=50,
            )

            # Test connection
            if self.redis:
                result: bool = await self.redis.ping()  # type: ignore[assignment]
                self._connected = True

            logger.info(
                "Cache service connected",
                extra={"host": settings.REDIS_HOST, "port": settings.REDIS_PORT},
            )

        except Exception as e:
            logger.error("Cache connection failed", error=e)
            raise CacheError(message="Failed to connect to Redis", details={"error": str(e)})

    async def disconnect(self) -> None:
        """Disconnect from Redis server."""
        if self.redis:
            await self.redis.close()
            self._connected = False
            logger.info("Cache service disconnected")

    def _make_key(self, key: str) -> str:
        """Create prefixed cache key."""
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._connected:
            await self.connect()

        try:
            full_key = self._make_key(key)
            if self.redis:
                value = await self.redis.get(full_key)
            else:
                return None

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return json.loads(value)

        except Exception as e:
            logger.error(f"Cache get failed for key: {key}", error=e)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            bool: True if successful
        """
        if not self._connected:
            await self.connect()

        try:
            full_key = self._make_key(key)
            serialized = json.dumps(value)

            if ttl:
                if self.redis:
                    await self.redis.setex(full_key, ttl, serialized)
            else:
                if self.redis:
                    await self.redis.set(full_key, serialized)

            logger.debug(f"Cache set: {key} (TTL: {ttl})")
            return True

        except Exception as e:
            logger.error(f"Cache set failed for key: {key}", error=e)
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            bool: True if deleted
        """
        if not self._connected:
            await self.connect()

        try:
            full_key = self._make_key(key)
            if self.redis:
                result = await self.redis.delete(full_key)
                logger.debug(f"Cache delete: {key}")
                return bool(result > 0)
            return False

        except Exception as e:
            logger.error(f"Cache delete failed for key: {key}", error=e)
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self._connected:
            await self.connect()

        try:
            full_key = self._make_key(key)
            if self.redis:
                result = await self.redis.exists(full_key)
                return bool(result > 0)
            return False
        except Exception as e:
            logger.error(f"Cache exists check failed for key: {key}", error=e)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern.

        Args:
            pattern: Key pattern (* wildcard supported)

        Returns:
            int: Number of keys deleted
        """
        if not self._connected:
            await self.connect()

        try:
            full_pattern = self._make_key(pattern)
            keys = []

            # The original line `async for key in self.redis.scan_iter(match=full_pattern) if self.redis else []:`
            # is syntactically incorrect. The `if self.redis else []:` part cannot be directly appended to `async for`.
            # The correct way to handle `self.redis` being Optional is to check it before the loop.
            # The user's requested change `async for key in self.redis.scan_iter(match=full_pattern): # type: ignore[union-attr]`
            # implies that `self.redis` is guaranteed to be not None at this point, or the type ignore handles it.
            # Given `if not self._connected: await self.connect()`, `self.redis` should be connected.
            # Adding the type ignore as requested.
            async for key in self.redis.scan_iter(match=full_pattern):  # type: ignore[union-attr]
                keys.append(key)

            if keys and self.redis:
                deleted = await self.redis.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching: {pattern}")
                return int(deleted)

            return 0

        except Exception as e:
            logger.error(f"Cache clear pattern failed: {pattern}", error=e)
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._connected:
            await self.connect()

        try:
            if self.redis:
                info = await self.redis.info("stats")
            else:
                return {}

            return {
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calc_hit_rate(
                    info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)
                ),
            }

        except Exception as e:
            logger.error("Failed to get cache stats", error=e)
            return {}

    def _calc_hit_rate(self, hits: int, misses: int) -> float:
        """Calculate cache hit rate percentage."""
        total = hits + misses
        return round((hits / total * 100), 2) if total > 0 else 0.0


# Export
__all__ = ["CacheService"]
