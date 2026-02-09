"""
Test Location API Routes
=========================
Integration tests for location endpoints.

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
async def authenticated_client(client):
    """Create authenticated test client."""
    # Register and login
    await client.post("/auth/register", json={
        "email": "location@example.com",
        "username": "locationuser",
        "password": "SecurePass123!",
        "full_name": "Location User"
    })
    
    login_response = await client.post("/auth/login", json={
        "email": "location@example.com",
        "password": "SecurePass123!"
    })
    
    token = login_response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    
    return client


class TestLocationCreation:
    """Test location creation endpoint."""
    
    @pytest.mark.asyncio
    async def test_create_location_success(self, authenticated_client):
        """Test successful location creation."""
        location_data = {
            "name": "Observatory",
            "description": "Main observatory",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "elevation": 100.5,
            "location_type": "observatory"
        }
        
        response = await authenticated_client.post("/locations", json=location_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == "Observatory"
        assert data["latitude"] == 34.0522
        assert data["longitude"] == -118.2437
    
    @pytest.mark.asyncio
    async def test_create_location_unauthorized(self, client):
        """Test location creation without authentication."""
        location_data = {
            "name": "Test",
            "latitude": 34.0,
            "longitude": -118.0
        }
        
        response = await client.post("/locations", json=location_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    @pytest.mark.asyncio
    async def test_create_location_invalid_coordinates(self, authenticated_client):
        """Test location creation with invalid coordinates."""
        location_data = {
            "name": "Invalid",
            "latitude": 100.0,  # Invalid latitude
            "longitude": -118.0
        }
        
        response = await authenticated_client.post("/locations", json=location_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLocationRetrieval:
    """Test location retrieval endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_location_by_id(self, authenticated_client):
        """Test getting location by ID."""
        # Create location
        create_response = await authenticated_client.post("/locations", json={
            "name": "GetTest",
            "latitude": 40.7128,
            "longitude": -74.0060
        })
        location_id = create_response.json()["id"]
        
        # Get location
        response = await authenticated_client.get(f"/locations/{location_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == location_id
        assert data["name"] == "GetTest"
    
    @pytest.mark.asyncio
    async def test_get_location_not_found(self, authenticated_client):
        """Test getting non-existent location."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await authenticated_client.get(f"/locations/{fake_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    @pytest.mark.asyncio
    async def test_list_locations(self, authenticated_client):
        """Test listing locations."""
        # Create multiple locations
        await authenticated_client.post("/locations", json={
            "name": "Location 1",
            "latitude": 34.0,
            "longitude": -118.0
        })
        
        await authenticated_client.post("/locations", json={
            "name": "Location 2",
            "latitude": 35.0,
            "longitude": -119.0
        })
        
        # List locations
        response = await authenticated_client.get("/locations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestLocationUpdate:
    """Test location update endpoint."""
    
    @pytest.mark.asyncio
    async def test_update_location(self, authenticated_client):
        """Test updating location."""
        # Create location
        create_response = await authenticated_client.post("/locations", json={
            "name": "UpdateTest",
            "latitude": 40.0,
            "longitude": -74.0
        })
        location_id = create_response.json()["id"]
        
        # Update location
        update_data = {"name": "Updated Name", "description": "New description"}
        response = await authenticated_client.put(
            f"/locations/{location_id}",
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"


class TestLocationDeletion:
    """Test location deletion endpoint."""
    
    @pytest.mark.asyncio
    async def test_delete_location(self, authenticated_client):
        """Test deleting location."""
        # Create location
        create_response = await authenticated_client.post("/locations", json={
            "name": "DeleteTest",
            "latitude": 40.0,
            "longitude": -74.0
        })
        location_id = create_response.json()["id"]
        
        # Delete location
        response = await authenticated_client.delete(f"/locations/{location_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestSpatialQueries:
    """Test spatial query endpoints."""
    
    @pytest.mark.asyncio
    async def test_find_nearby_locations(self, authenticated_client):
        """Test finding nearby locations."""
        # Create locations
        await authenticated_client.post("/locations", json={
            "name": "Nearby 1",
            "latitude": 34.0522,
            "longitude": -118.2437
        })
        
        await authenticated_client.post("/locations", json={
            "name": "Nearby 2",
            "latitude": 34.0600,
            "longitude": -118.2500
        })
        
        # Search nearby
        response = await authenticated_client.get(
            "/locations/nearby",
            params={
                "latitude": 34.0522,
                "longitude": -118.2437,
                "radius_km": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
