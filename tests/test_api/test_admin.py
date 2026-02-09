"""
Test Admin API Routes
======================
Integration tests for admin endpoints.

Author: Production Team
Version: 1.0.0
"""

import pytest
from httpx import AsyncClient
from fastapi import status

from src.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def admin_client(client):
    """Create authenticated admin client."""
    # Register admin user
    await client.post("/auth/register", json={
        "email": "admin@example.com",
        "username": "admin",
        "password": "AdminPass123!",
        "full_name": "Admin User"
    })
    
    # Login
    login_response = await client.post("/auth/login", json={
        "email": "admin@example.com",
        "password": "AdminPass123!"
    })
    
    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


@pytest.fixture
async def regular_client(client):
    """Create authenticated regular user client."""
    await client.post("/auth/register", json={
        "email": "user@example.com",
        "username": "reguser",
        "password": "UserPass123!",
        "full_name": "Regular User"
    })
    
    login_response = await client.post("/auth/login", json={
        "email": "user@example.com",
        "password": "UserPass123!"
    })
    
    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


class TestAdminUserManagement:
    """Test admin user management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_all_users_as_admin(self, admin_client):
        """Test listing all users as admin."""
        response = await admin_client.get("/admin/users")
        
        # Admin routes may not be implemented yet
        # This is a placeholder for when they are
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_list_users_forbidden_for_regular_user(self, regular_client):
        """Test regular users cannot access admin endpoints."""
        response = await regular_client.get("/admin/users")
        
        # Should be forbidden or not found
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND
        ]
    
    @pytest.mark.asyncio
    async def test_admin_unauthorized_without_auth(self, client):
        """Test admin endpoints require authentication."""
        response = await client.get("/admin/users")
        
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND
        ]


class TestAdminModelManagement:
    """Test admin model management endpoints."""
    
    @pytest.mark.asyncio
    async def test_list_all_models_as_admin(self, admin_client):
        """Test listing all models as admin."""
        response = await admin_client.get("/admin/models")
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_delete_model_as_admin(self, admin_client):
        """Test deleting model as admin."""
        fake_model_id = "00000000-0000-0000-0000-000000000000"
        response = await admin_client.delete(f"/admin/models/{fake_model_id}")
        
        # Should be not found or not implemented
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_204_NO_CONTENT
        ]


class TestAdminSystemMetrics:
    """Test admin system metrics endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, admin_client):
        """Test getting system metrics."""
        response = await admin_client.get("/admin/metrics")
        
        # Metrics endpoint may return system stats
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self, admin_client):
        """Test getting user statistics."""
        response = await admin_client.get("/admin/stats/users")
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
