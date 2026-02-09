"""
Integration Test Configuration
================================
Pytest configuration for integration tests.

Author: Production Team
Version: 1.0.0
"""

import pytest
import asyncio
from typing import Generator


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (slow)"
    )
    config.addinivalue_line(
        "markers",
        "database: marks tests that require database"
    )
    config.addinivalue_line(
        "markers",
        "redis: marks tests that require Redis"
    )


# ============================================================================
# EVENT LOOP FIXTURE
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
async def setup_test_database():
    """Set up test database."""
    # This would create test database schema
    # For now, we'll use the existing database
    yield
    # Cleanup would go here


@pytest.fixture(scope="function", autouse=True)
async def cleanup_database():
    """Clean up database after each test."""
    yield
    # Cleanup logic here
    # E.g., delete test records created during tests


# ============================================================================
# REDIS FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available."""
    try:
        from src.core.cache import get_cache
        cache = get_cache()
        return cache.enabled
    except Exception:
        return False


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_prediction_data():
    """Sample prediction data."""
    return {
        "features": {
            "latitude": 40.7128,
            "longitude": -74.0060,
            "population": 8000000,
            "area_sqkm": 783.8
        }
    }


@pytest.fixture
def sample_agent_task():
    """Sample agent task."""
    return {
        "agent_type": "data",
        "task": "Analyze customer data and provide insights",
        "context": {"dataset": "customers.csv"}
    }


# ============================================================================
# SKIP CONDITIONS
# ============================================================================

def _redis_available():
    """Check if Redis is available."""
    try:
        from src.core.cache import get_cache
        cache = get_cache()
        return cache.enabled
    except Exception:
        return False

def _postgres_available():
    """Check if PostgreSQL is available."""
    try:
        from src.core.database import get_db
        # Try to get a database connection
        next(get_db())
        return True
    except Exception:
        return False

skip_if_no_redis = pytest.mark.skipif(
    not _redis_available(),
    reason="Redis not available"
)

skip_if_no_db = pytest.mark.skipif(
    not _postgres_available(),
    reason="PostgreSQL not available"
)
