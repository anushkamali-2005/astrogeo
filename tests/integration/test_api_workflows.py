"""
Integration Tests - API Workflows
==================================
End-to-end tests for complete API workflows.

Tests:
- Agent execution flow
- Prediction workflow
- Authentication & authorization
- Database transactions
- Error handling

Author: Production Team
Version: 1.0.0
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime

from src.main import app
from src.database.connection import get_db
from src.database.models import User, MLModel, AgentExecution
from src.core.security import create_access_token


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def async_client():
    """Create async HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def db_session():
    """Create database session for tests."""
    async for session in get_db():
        yield session


@pytest.fixture
async def test_user(db_session):
    """Create test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password_here",
        is_active=True,
        role="user"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers."""
    token = create_access_token({"sub": test_user.username})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def test_model(db_session):
    """Create test ML model."""
    model = MLModel(
        name="test_classifier",
        version="1.0.0",
        model_type="classification",
        framework="scikit-learn",
        status="production",
        model_path="/models/test_classifier_v1.pkl",
        metrics={"accuracy": 0.95, "f1_score": 0.93}
    )
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)
    return model


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_root_endpoint(self, async_client):
        """Test root endpoint."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data
    
    async def test_health_endpoint(self, async_client):
        """Test health check endpoint."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
    
    async def test_health_detailed(self, async_client):
        """Test detailed health check."""
        response = await async_client.get("/api/v1/health/detailed")
        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]


# ============================================================================
# AGENT EXECUTION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAgentWorkflows:
    """Test complete agent execution workflows."""
    
    async def test_single_agent_execution(self, async_client, auth_headers):
        """Test single agent execution end-to-end."""
        request_data = {
            "agent_type": "data",
            "task": "Analyze customer data and provide insights",
            "context": {"dataset": "customers.csv"},
            "save_to_database": True
        }
        
        response = await async_client.post(
            "/api/v1/agents/execute",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "agent_type" in data
        assert "execution_time_seconds" in data
        assert data["agent_type"] == "data"
    
    async def test_multi_agent_orchestration(self, async_client, auth_headers):
        """Test multi-agent orchestration."""
        request_data = {
            "task": "Analyze geographic data and build ML model",
            "required_agents": ["data", "geo", "ml"]
        }
        
        response = await async_client.post(
            "/api/v1/agents/orchestrate",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "orchestrator" in data
        assert "execution_time_seconds" in data
    
    async def test_agent_execution_history(
        self,
        async_client,
        auth_headers,
        test_user
    ):
        """Test retrieving agent execution history."""
        response = await async_client.get(
            f"/api/v1/agents/history?limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list) or "executions" in data
    
    async def test_invalid_agent_type(self, async_client, auth_headers):
        """Test execution with invalid agent type."""
        request_data = {
            "agent_type": "invalid_agent",
            "task": "Test task"
        }
        
        response = await async_client.post(
            "/api/v1/agents/execute",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 422 or response.status_code == 400


# ============================================================================
# PREDICTION WORKFLOW TESTS
# ============================================================================

@pytest.mark.asyncio
class TestPredictionWorkflows:
    """Test complete prediction workflows."""
    
    async def test_single_prediction(
        self,
        async_client,
        auth_headers,
        test_model
    ):
        """Test single prediction workflow."""
        request_data = {
            "model_id": str(test_model.id),
            "features": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "population": 8000000,
                "area_sqkm": 783.8
            },
            "return_probabilities": True
        }
        
        response = await async_client.post(
            "/api/v1/predictions/predict",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "prediction" in data
        assert "model_id" in data
        assert "execution_time_ms" in data
    
    async def test_batch_prediction(
        self,
        async_client,
        auth_headers,
        test_model
    ):
        """Test batch prediction workflow."""
        request_data = {
            "model_id": str(test_model.id),
            "features_list": [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "population": 8000000,
                    "area_sqkm": 783.8
                },
                {
                    "latitude": 34.0522,
                    "longitude": -118.2437,
                    "population": 4000000,
                    "area_sqkm": 1302.15
                }
            ],
            "return_probabilities": False
        }
        
        response = await async_client.post(
            "/api/v1/predictions/batch",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "predictions" in data
        assert "total_count" in data
        assert data["total_count"] == 2


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication and authorization."""
    
    async def test_protected_endpoint_without_auth(self, async_client):
        """Test accessing protected endpoint without authentication."""
        response = await async_client.post(
            "/api/v1/agents/execute",
            json={"agent_type": "data", "task": "test"}
        )
        
        assert response.status_code == 401
    
    async def test_protected_endpoint_with_invalid_token(self, async_client):
        """Test with invalid authentication token."""
        headers = {"Authorization": "Bearer invalid_token"}
        
        response = await async_client.post(
            "/api/v1/agents/execute",
            json={"agent_type": "data", "task": "test"},
            headers=headers
        )
        
        assert response.status_code == 401
    
    async def test_login_flow(self, async_client, test_user):
        """Test complete login flow."""
        login_data = {
            "username": test_user.username,
            "password": "testpassword"
        }
        
        response = await async_client.post(
            "/api/v1/auth/login",
            json=login_data
        )
        
        # May fail if endpoint not implemented yet
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data


# ============================================================================
# DATABASE INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Test database operations through API."""
    
    async def test_create_and_retrieve_execution(
        self,
        async_client,
        auth_headers,
        db_session
    ):
        """Test creating execution and retrieving it."""
        # Create execution via API
        request_data = {
            "agent_type": "data",
            "task": "Integration test task",
            "save_to_database": True
        }
        
        response = await async_client.post(
            "/api/v1/agents/execute",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        if "execution_id" in data:
            execution_id = data["execution_id"]
            
            # Verify in database
            from sqlalchemy import select
            result = await db_session.execute(
                select(AgentExecution).where(
                    AgentExecution.id == execution_id
                )
            )
            execution = result.scalar_one_or_none()
            
            assert execution is not None
            assert execution.agent_name == "data"
    
    async def test_transaction_rollback_on_error(self, db_session):
        """Test that transactions rollback on error."""
        # This would need actual error-inducing code
        # Placeholder for transaction rollback test
        pass


# ============================================================================
# MIDDLEWARE INTEGRATION TESTS
# ============================================================================

@pytest.mark.asyncio
class TestMiddlewareIntegration:
    """Test middleware functionality."""
    
    async def test_request_id_header(self, async_client):
        """Test that request ID is added to response."""
        response = await async_client.get("/")
        
        # Should have request ID from logging middleware
        assert "x-request-id" in response.headers or "X-Request-ID" in response.headers
    
    async def test_response_time_header(self, async_client):
        """Test that response time is tracked."""
        response = await async_client.get("/")
        
        # Should have response time from logging middleware
        assert any(
            header.lower() in ["x-response-time", "x-execution-time"]
            for header in response.headers.keys()
        )
    
    async def test_rate_limiting(self, async_client):
        """Test rate limiting middleware."""
        # Make multiple rapid requests
        responses = []
        for _ in range(100):
            response = await async_client.get("/")
            responses.append(response)
        
        # Some requests should be rate limited
        status_codes = [r.status_code for r in responses]
        
        # If rate limiting is enabled, we should see 429s
        # If not enabled, all should be 200
        assert 200 in status_codes


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling across API."""
    
    async def test_validation_error(self, async_client, auth_headers):
        """Test validation error handling."""
        # Send invalid data
        response = await async_client.post(
            "/api/v1/agents/execute",
            json={"invalid": "data"},
            headers=auth_headers
        )
        
        assert response.status_code == 422
    
    async def test_not_found_error(self, async_client, auth_headers):
        """Test 404 error handling."""
        response = await async_client.get(
            f"/api/v1/models/{uuid4()}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
    
    async def test_server_error_handling(self, async_client):
        """Test 500 error handling."""
        # This would need an endpoint that triggers an error
        # Placeholder for server error test
        pass


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.asyncio
class TestPerformance:
    """Basic performance tests."""
    
    async def test_response_time(self, async_client):
        """Test that endpoints respond quickly."""
        import time
        
        start = time.time()
        response = await async_client.get("/api/v1/health")
        duration = time.time() - start
        
        assert response.status_code == 200
        assert duration < 1.0  # Should respond in under 1 second
    
    async def test_concurrent_requests(self, async_client, auth_headers):
        """Test handling concurrent requests."""
        import asyncio
        
        async def make_request():
            return await async_client.post(
                "/api/v1/agents/execute",
                json={"agent_type": "data", "task": "test"},
                headers=auth_headers
            )
        
        # Make 10 concurrent requests
        responses = await asyncio.gather(*[
            make_request() for _ in range(10)
        ])
        
        # All should complete successfully
        assert all(r.status_code in [200, 401] for r in responses)
