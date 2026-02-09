"""
Cache Utilities
================
Helper functions and utilities for caching operations.

Author: Production Team
Version: 1.0.0
"""

from functools import wraps
from typing import Any, Dict

from src.core.cache import get_cache
from src.core.logging import get_logger

logger = get_logger(__name__)


def invalidate_prediction_cache(model_id: str) -> int:
    """
    Invalidate all cached predictions for a model.

    Args:
        model_id: Model ID

    Returns:
        int: Number of cache entries invalidated
    """
    cache = get_cache()
    pattern = f"prediction:*{model_id}*"
    count = cache.invalidate_pattern(pattern)

    logger.info("Prediction cache invalidated", extra={"model_id": model_id, "count": count})

    return count


def clear_all_prediction_cache() -> int:
    """
    Clear all prediction caches.

    Returns:
        int: Number of entries cleared
    """
    cache = get_cache()
    count = cache.clear_namespace("prediction")

    logger.info("All prediction caches cleared", extra={"count": count})

    return count


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.

    Returns:
        dict: Cache statistics
    """
    cache = get_cache()
    return cache.get_stats()


# Export
__all__ = ["invalidate_prediction_cache", "clear_all_prediction_cache", "get_cache_stats"]
