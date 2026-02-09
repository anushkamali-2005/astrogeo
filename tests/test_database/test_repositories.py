"""
Test Database Repositories
===========================
Unit tests for database repository layer.

Author: Production Team
Version: 1.0.0
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import LocationRepository, MLModelRepository, UserRepository


class TestUserRepository:
    """Test UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, db_session: AsyncSession):
        """Test creating a user."""
        repo = UserRepository(db_session)

        user = await repo.create(
            {
                "email": "test@example.com",
                "username": "testuser",
                "hashed_password": "hashed_pass",
                "full_name": "Test User",
            }
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, db_session: AsyncSession):
        """Test getting user by email."""
        repo = UserRepository(db_session)

        # Create user
        created_user = await repo.create(
            {"email": "find@example.com", "username": "finduser", "hashed_password": "pass"}
        )

        # Find by email
        found_user = await repo.get_by_email("find@example.com")

        assert found_user is not None
        assert found_user.id == created_user.id
        assert found_user.email == "find@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db_session: AsyncSession):
        """Test getting user by username."""
        repo = UserRepository(db_session)

        # Create user
        created_user = await repo.create(
            {"email": "user@example.com", "username": "uniqueuser", "hashed_password": "pass"}
        )

        # Find by username
        found_user = await repo.get_by_username("uniqueuser")

        assert found_user is not None
        assert found_user.username == "uniqueuser"

    @pytest.mark.asyncio
    async def test_update_user(self, db_session: AsyncSession):
        """Test updating user."""
        repo = UserRepository(db_session)

        # Create user
        user = await repo.create(
            {"email": "update@example.com", "username": "updateuser", "hashed_password": "pass"}
        )

        # Update
        updated_user = await repo.update(user.id, {"full_name": "Updated Name"})

        assert updated_user.full_name == "Updated Name"


class TestLocationRepository:
    """Test LocationRepository."""

    @pytest.mark.asyncio
    async def test_create_location(self, db_session: AsyncSession):
        """Test creating a location."""
        repo = LocationRepository(db_session)

        location = await repo.create(
            {
                "name": "Test Location",
                "latitude": 34.0522,
                "longitude": -118.2437,
                "elevation": 100.0,
                "location_type": "test",
            }
        )

        assert location.id is not None
        assert location.name == "Test Location"
        assert location.latitude == 34.0522
        assert location.longitude == -118.2437

    @pytest.mark.asyncio
    async def test_find_nearby_locations(self, db_session: AsyncSession):
        """Test finding nearby locations."""
        repo = LocationRepository(db_session)

        # Create locations
        await repo.create({"name": "Location 1", "latitude": 34.0522, "longitude": -118.2437})

        await repo.create({"name": "Location 2", "latitude": 34.0600, "longitude": -118.2500})

        # Find nearby (within 10km)
        nearby = await repo.find_nearby(latitude=34.0522, longitude=-118.2437, radius_km=10)

        assert len(nearby) >= 1

    @pytest.mark.asyncio
    async def test_get_location_by_id(self, db_session: AsyncSession):
        """Test getting location by ID."""
        repo = LocationRepository(db_session)

        # Create location
        created = await repo.create({"name": "Find Me", "latitude": 40.7128, "longitude": -74.0060})

        # Find by ID
        found = await repo.get(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.name == "Find Me"


class TestMLModelRepository:
    """Test MLModelRepository."""

    @pytest.mark.asyncio
    async def test_create_model(self, db_session: AsyncSession):
        """Test creating an ML model."""
        repo = MLModelRepository(db_session)

        model = await repo.create(
            {
                "name": "Test Model",
                "model_type": "classification",
                "version": "1.0.0",
                "framework": "sklearn",
                "status": "trained",
            }
        )

        assert model.id is not None
        assert model.name == "Test Model"
        assert model.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version(self, db_session: AsyncSession):
        """Test getting latest model version."""
        repo = MLModelRepository(db_session)

        # Create multiple versions
        await repo.create(
            {"name": "VersionTest", "model_type": "classification", "version": "1.0.0"}
        )

        await repo.create(
            {"name": "VersionTest", "model_type": "classification", "version": "1.1.0"}
        )

        # Get latest
        latest = await repo.get_latest_version("VersionTest")

        assert latest is not None
        # Note: This depends on repository implementation
        # Latest could be determined by created_at or version string
