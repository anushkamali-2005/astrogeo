"""
Test Configuration
==================
Pytest configuration and shared fixtures.

Author: Production Team
Version: 1.0.0
"""

import os
import asyncio
from typing import AsyncGenerator, Generator
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from httpx import AsyncClient

from src.core.config import settings
from src.database.connection import Base, get_db
from src.api.main import app


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Pytest configuration hook."""
    # Set test environment
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DEBUG"] = "true"


# ============================================================================
# ASYNC EVENT LOOP
# ============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create event loop for async tests.
    
    Yields:
        asyncio.AbstractEventLoop: Event loop
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# TEST DATABASE
# ============================================================================

@pytest.fixture(scope="session")
async def test_engine():
    """
    Create test database engine.
    
    Yields:
        AsyncEngine: Test database engine
    """
    # Use in-memory SQLite for tests
    test_database_url = "sqlite+aiosqlite:///:memory:"
    
    # Create engine
    engine = create_async_engine(
        test_database_url,
        poolclass=NullPool,
        echo=False
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create database session for tests.
    
    Args:
        test_engine: Test database engine
        
    Yields:
        AsyncSession: Database session
    """
    # Create session factory
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


# ============================================================================
# TEST CLIENT
# ============================================================================

@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Create test HTTP client.
    
    Args:
        db_session: Test database session
        
    Yields:
        AsyncClient: HTTP test client
    """
    # Override database dependency
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create client
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    # Cleanup
    app.dependency_overrides.clear()


# ============================================================================
# AUTHENTICATION FIXTURES
# ============================================================================

@pytest.fixture
def test_user_data() -> dict:
    """Test user data."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",
        "full_name": "Test User"
    }


@pytest.fixture
async def authenticated_client(
    client: AsyncClient,
    test_user_data: dict
) -> AsyncGenerator[tuple[AsyncClient, dict], None]:
    """
    Create authenticated test client.
    
    Args:
        client: HTTP test client
        test_user_data: Test user data
        
    Yields:
        tuple: (client, auth_headers)
    """
    # Register user
    response = await client.post(
        "/api/v1/auth/register",
        json=test_user_data
    )
    
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
    )
    
    token_data = response.json()
    access_token = token_data["data"]["access_token"]
    
    # Create auth headers
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    
    yield client, auth_headers


# ============================================================================
# MODEL FIXTURES
# ============================================================================

@pytest.fixture
async def test_model(db_session: AsyncSession):
    """Create test ML model."""
    from src.database.models import MLModel
    
    model = MLModel(
        name="test_model",
        version="1.0.0",
        model_type="classification",
        framework="scikit-learn",
        status="production",
        metrics={"accuracy": 0.92, "precision": 0.89},
        parameters={"n_estimators": 100}
    )
    
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    
    return model


@pytest.fixture
async def test_location(db_session: AsyncSession):
    """Create test location."""
    from src.database.models import Location
    from geoalchemy2.elements import WKTElement
    
    location = Location(
        name="Test Location",
        description="Test description",
        location_type="poi",
        geometry=WKTElement("POINT(-73.968285 40.785091)", srid=4326),
        city="New York",
        country="US"
    )
    
    db_session.add(location)
    await db_session.commit()
    await db_session.refresh(location)
    
    return location


# ============================================================================
# UTILITY FIXTURES
# ============================================================================

@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Test response from mock OpenAI"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        }
    }


@pytest.fixture
def sample_features():
    """Sample prediction features."""
    return {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "population": 8000000,
        "area_sqkm": 783.8
    }


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_after_test(db_session: AsyncSession):
    """Cleanup after each test."""
    yield
    # Rollback any uncommitted changes
    await db_session.rollback()


# ============================================================================
# MARKERS
# ============================================================================

# Register custom markers
def pytest_configure(config):
    """Register custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )


# Export fixtures
__all__ = [
    "event_loop",
    "test_engine",
    "db_session",
    "client",
    "test_user_data",
    "authenticated_client",
    "test_model",
    "test_location",
    "mock_openai_response",
    "sample_features",
    "cleanup_after_test"
]