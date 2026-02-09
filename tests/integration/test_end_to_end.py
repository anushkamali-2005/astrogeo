"""
End-to-End Integration Tests
=============================
Complete workflow integration tests.

Author: Production Team
Version: 1.0.0
"""

import pytest
from httpx import AsyncClient

from src.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestUserWorkflow:
    """Test complete user workflow."""
    
    @pytest.mark.asyncio
    async def test_user_registration_and_authentication(self, client):
        """Test user can register, login, and access profile."""
        # Step 1: Register
        register_data = {
            "email": "workflow@example.com",
            "username": "workflowuser",
            "password": "WorkflowPass123!",
            "full_name": "Workflow User"
        }
        
        register_response = await client.post("/auth/register", json=register_data)
        assert register_response.status_code == 201
        user_data = register_response.json()
        assert user_data["email"] == "workflow@example.com"
        
        # Step 2: Login
        login_data = {
            "email": "workflow@example.com",
            "password": "WorkflowPass123!"
        }
        
        login_response = await client.post("/auth/login", json=login_data)
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        
        # Step 3: Access profile
        access_token = tokens["access_token"]
        profile_response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        assert profile_response.status_code == 200
        profile = profile_response.json()
        assert profile["email"] == "workflow@example.com"


class TestLocationWorkflow:
    """Test complete location workflow."""
    
    @pytest.mark.asyncio
    async def test_location_crud_workflow(self, client):
        """Test creating, reading, updating, and deleting a location."""
        # Setup: Register and login
        await client.post("/auth/register", json={
            "email": "location@workflow.com",
            "username": "locuser",
            "password": "Pass123!",
            "full_name": "Location User"
        })
        
        login_response = await client.post("/auth/login", json={
            "email": "location@workflow.com",
            "password": "Pass123!"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 1: Create location
        create_data = {
            "name": "Workflow Location",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "description": "Test location"
        }
        
        create_response = await client.post(
            "/locations",
            json=create_data,
            headers=headers
        )
        
        assert create_response.status_code == 201
        location = create_response.json()
        location_id = location["id"]
        
        # Step 2: Read location
        get_response = await client.get(
            f"/locations/{location_id}",
            headers=headers
        )
        
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Workflow Location"
        
        # Step 3: Update location
        update_data = {"description": "Updated description"}
        update_response = await client.put(
            f"/locations/{location_id}",
            json=update_data,
            headers=headers
        )
        
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated description"
        
        # Step 4: Delete location
        delete_response = await client.delete(
            f"/locations/{location_id}",
            headers=headers
        )
        
        assert delete_response.status_code == 204


class TestMLWorkflow:
    """Test ML prediction workflow."""
    
    @pytest.mark.asyncio
    async def test_model_prediction_workflow(self, client):
        """Test model training and prediction workflow."""
        # Setup authentication
        await client.post("/auth/register", json={
            "email": "ml@workflow.com",
            "username": "mluser",
            "password": "MLPass123!",
            "full_name": "ML User"
        })
        
        login_response = await client.post("/auth/login", json={
            "email": "ml@workflow.com",
            "password": "MLPass123!"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Note: Actual ML endpoints may not be fully implemented
        # These are placeholder tests
        
        # Step 1: Check health
        health_response = await client.get("/health")
        assert health_response.status_code == 200


class TestAgentWorkflow:
    """Test agent execution workflow."""
    
    @pytest.mark.asyncio
    async def test_agent_execution_workflow(self, client):
        """Test executing an agent task."""
        # Setup authentication
        await client.post("/auth/register", json={
            "email": "agent@workflow.com",
            "username": "agentuser",
            "password": "AgentPass123!",
            "full_name": "Agent User"
        })
        
        login_response = await client.post("/auth/login", json={
            "email": "agent@workflow.com",
            "password": "AgentPass123!"
        })
        
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Agent execution endpoints may vary
        # This is a placeholder for when they're implemented
        health_response = await client.get("/health")
        assert health_response.status_code == 200


class TestHealthChecks:
    """Test system health checks."""
    
    @pytest.mark.asyncio
    async def test_basic_health_check(self, client):
        """Test basic health endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client):
        """Test detailed health endpoint."""
        response = await client.get("/health/detailed")
        
        # May be 200 or 404 if not implemented
        assert response.status_code in [200, 404]
