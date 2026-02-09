"""
Redis Cache Manager
====================
Production-level Redis caching with:
- Connection pooling
- Key generation
- TTL management
- Cache invalidation
- Error handling

Author: Production Team
Version: 1.0.0
"""

import hashlib
import json
import pickle
from datetime import timedelta
from typing import Any, Dict, Optional, Union

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# REDIS CACHE MANAGER
# ============================================================================


class RedisCache:
    """
    Redis cache manager with async support.

    Features:
    - Connection pooling
    - Automatic serialization
    - TTL support
    - Key namespacing
    - Error handling

    Design Pattern: Singleton
    """

    _instance: Optional["RedisCache"] = None
    _initialized: bool = False

    def __new__(cls):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Redis cache."""
        if not self._initialized:
            self.redis_client = None
            self.enabled = False
            self._initialize_client()
            RedisCache._initialized = True

    def _initialize_client(self) -> None:
        """Initialize Redis client."""
        try:
            import redis

            # Check if Redis is configured
            redis_host = getattr(settings, "REDIS_HOST", "localhost")
            redis_port = getattr(settings, "REDIS_PORT", 6379)
            redis_db = getattr(settings, "REDIS_DB", 0)

            # Create Redis connection pool
            pool = redis.ConnectionPool(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=False,  # We'll handle encoding
                max_connections=10,
            )

            self.redis_client = redis.Redis(connection_pool=pool)

            # Test connection
            self.redis_client.ping()
            self.enabled = True

            logger.info(
                "Redis cache initialized",
                extra={"host": redis_host, "port": redis_port, "db": redis_db},
            )

        except ImportError:
            logger.warning("Redis library not installed. Cache disabled.")
            self.enabled = False

        except Exception as e:
            logger.warning(f"Redis connection failed. Cache disabled.", error=e)
            self.enabled = False

    def _generate_key(self, namespace: str, identifier: Union[str, Dict[str, Any]]) -> str:
        """
        Generate cache key with namespace.

        Args:
            namespace: Cache namespace (e.g., 'prediction', 'model')
            identifier: Unique identifier (string or dict)

        Returns:
            str: Generated cache key
        """
        if isinstance(identifier, dict):
            # Hash dictionary for consistent key generation
            sorted_items = sorted(identifier.items())
            identifier_str = json.dumps(sorted_items, sort_keys=True)
            hash_obj = hashlib.md5(identifier_str.encode())
            identifier = hash_obj.hexdigest()

        return f"{namespace}:{identifier}"

    def get(self, namespace: str, identifier: Union[str, Dict[str, Any]]) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            namespace: Cache namespace
            identifier: Cache identifier

        Returns:
            Any: Cached value or None
        """
        if not self.enabled:
            return None

        try:
            key = self._generate_key(namespace, identifier)
            value = self.redis_client.get(key)

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            # Deserialize
            deserialized = pickle.loads(value)
            logger.debug(f"Cache hit: {key}")
            return deserialized

        except Exception as e:
            logger.error(f"Cache get failed", error=e)
            return None

    def set(
        self,
        namespace: str,
        identifier: Union[str, Dict[str, Any]],
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            namespace: Cache namespace
            identifier: Cache identifier
            value: Value to cache
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(namespace, identifier)

            # Serialize
            serialized = pickle.dumps(value)

            # Set with optional TTL
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)

            logger.debug(f"Cache set: {key}", extra={"ttl": ttl})
            return True

        except Exception as e:
            logger.error(f"Cache set failed", error=e)
            return False

    def delete(self, namespace: str, identifier: Union[str, Dict[str, Any]]) -> bool:
        """
        Delete value from cache.

        Args:
            namespace: Cache namespace
            identifier: Cache identifier

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            key = self._generate_key(namespace, identifier)
            self.redis_client.delete(key)

            logger.debug(f"Cache deleted: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete failed", error=e)
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Pattern to match (e.g., 'prediction:*')

        Returns:
            int: Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                count = self.redis_client.delete(*keys)
                logger.info(f"Cache invalidated", extra={"pattern": pattern, "count": count})
                return count
            return 0

        except Exception as e:
            logger.error(f"Cache invalidation failed", error=e)
            return 0

    def clear_namespace(self, namespace: str) -> int:
        """
        Clear all keys in namespace.

        Args:
            namespace: Namespace to clear

        Returns:
            int: Number of keys deleted
        """
        pattern = f"{namespace}:*"
        return self.invalidate_pattern(pattern)

    def flush_all(self) -> bool:
        """
        Flush entire cache (use with caution).

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        try:
            self.redis_client.flushdb()
            logger.warning("Redis cache flushed completely")
            return True

        except Exception as e:
            logger.error(f"Cache flush failed", error=e)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            dict: Cache stats
        """
        if not self.enabled:
            return {"enabled": False}

        try:
            info = self.redis_client.info()

            return {
                "enabled": True,
                "keys": self.redis_client.dbsize(),
                "memory_used_mb": round(info.get("used_memory", 0) / (1024**2), 2),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    2,
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats", error=e)
            return {"enabled": True, "error": str(e)}


# ============================================================================
# CACHE DECORATORS
# ============================================================================


def cache_result(
    namespace: str, ttl: Optional[int] = 3600, key_generator: Optional[callable] = None
):
    """
    Decorator to cache function results.

    Args:
        namespace: Cache namespace
        ttl: Time to live in seconds
        key_generator: Custom key generator function

    Usage:
        @cache_result('predictions', ttl=1800)
        def make_prediction(model_id, features):
            return expensive_prediction(model_id, features)
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # Use function name + args as key
                cache_key = {"func": func.__name__, "args": str(args), "kwargs": str(kwargs)}

            # Try to get from cache
            cached = cache.get(namespace, cache_key)
            if cached is not None:
                return cached

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(namespace, cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# ============================================================================
# SINGLETON ACCESSOR
# ============================================================================


def get_cache() -> RedisCache:
    """
    Get Redis cache singleton instance.

    Returns:
        RedisCache: Cache instance
    """
    return RedisCache()


# Export
__all__ = ["RedisCache", "get_cache", "cache_result"]
