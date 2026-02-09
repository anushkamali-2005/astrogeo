"""
Integration Tests - Database Operations
========================================
Tests for database integration and transactions.

Author: Production Team
Version: 1.0.0
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from src.database.connection import get_db
from src.database.models import (
    User, MLModel, Prediction, AgentExecution, Dataset
)
from src.database.repositories import (
    UserRepository, MLModelRepository, PredictionRepository
)


@pytest.mark.asyncio
class TestDatabaseTransactions:
    """Test database transaction handling."""
    
    @pytest.fixture
    async def db_session(self):
        """Get database session."""
        async for session in get_db():
            yield session
    
    async def test_create_and_retrieve_user(self, db_session):
        """Test creating and retrieving user."""
        repo = UserRepository(db_session)
        
        # Create user
        user_data = {
            "username": f"testuser_{uuid4().hex[:8]}",
            "email": f"test_{uuid4().hex[:8]}@example.com",
            "hashed_password": "hashed_password",
            "is_active": True,
            "role": "user"
        }
        
        user = await repo.create(user_data)
        
        assert user.id is not None
        assert user.username == user_data["username"]
        
        # Retrieve user
        retrieved = await repo.get_by_id(user.id)
        
        assert retrieved is not None
        assert retrieved.id == user.id
        assert retrieved.email == user_data["email"]
    
    async def test_bulk_create_models(self, db_session):
        """Test bulk creation of models."""
        repo = MLModelRepository(db_session)
        
        models_data = [
            {
                "name": f"model_{i}",
                "version": "1.0.0",
                "model_type": "classification",
                "framework": "scikit-learn",
                "status": "staging",
                "model_path": f"/models/model_{i}.pkl"
            }
            for i in range(5)
        ]
        
        models = await repo.bulk_create(models_data)
        
        assert len(models) == 5
        assert all(model.id is not None for model in models)
    
    async def test_update_model_status(self, db_session):
        """Test updating model status."""
        repo = MLModelRepository(db_session)
        
        # Create model
        model = await repo.create({
            "name": "test_model",
            "version": "1.0.0",
            "model_type": "regression",
            "framework": "tensorflow",
            "status": "staging",
            "model_path": "/models/test.h5"
        })
        
        # Update status
        updated = await repo.update(
            model.id,
            {"status": "production"}
        )
        
        assert updated.status == "production"
    
    async def test_soft_delete_and_retrieve(self, db_session):
        """Test soft delete functionality."""
        repo = MLModelRepository(db_session)
        
        # Create model
        model = await repo.create({
            "name": "delete_test",
            "version": "1.0.0",
            "model_type": "classification",
            "framework": "xgboost",
            "status": "staging",
            "model_path": "/models/delete_test.pkl"
        })
        
        model_id = model.id
        
        # Soft delete
        await repo.delete(model_id)
        
        # Should not be retrievable normally
        retrieved = await repo.get_by_id(model_id)
        assert retrieved is None or retrieved.deleted_at is not None
    
    async def test_filter_by_status(self, db_session):
        """Test filtering models by status."""
        repo = MLModelRepository(db_session)
        
        # Create models with different statuses
        for status in ["staging", "production", "archived"]:
            await repo.create({
                "name": f"model_{status}",
                "version": "1.0.0",
                "model_type": "classification",
                "framework": "scikit-learn",
                "status": status,
                "model_path": f"/models/{status}.pkl"
            })
        
        # Filter by status
        prod_models = await repo.filter_by(status="production")
        
        assert len(prod_models) >= 1
        assert all(m.status == "production" for m in prod_models)
    
    async def test_transaction_rollback(self, db_session):
        """Test transaction rollback on error."""
        repo = UserRepository(db_session)
        
        try:
            # Start transaction
            user = await repo.create({
                "username": "rollback_test",
                "email": "rollback@example.com",
                "hashed_password": "hashed"
            })
            
            # Force an error
            raise Exception("Simulated error")
            
        except Exception:
            await db_session.rollback()
        
        # User should not exist
        users = await repo.filter_by(username="rollback_test")
        assert len(users) == 0


@pytest.mark.asyncio
class TestDatabaseRelationships:
    """Test database relationships and joins."""
    
    @pytest.fixture
    async def db_session(self):
        """Get database session."""
        async for session in get_db():
            yield session
    
    async def test_user_predictions_relationship(self, db_session):
        """Test user -> predictions relationship."""
        user_repo = UserRepository(db_session)
        pred_repo = PredictionRepository(db_session)
        model_repo = MLModelRepository(db_session)
        
        # Create user
        user = await user_repo.create({
            "username": f"user_{uuid4().hex[:8]}",
            "email": f"{uuid4().hex[:8]}@example.com",
            "hashed_password": "hashed"
        })
        
        # Create model
        model = await model_repo.create({
            "name": "test_model",
            "version": "1.0.0",
            "model_type": "classification",
            "framework": "scikit-learn",
            "status": "production",
            "model_path": "/models/test.pkl"
        })
        
        # Create predictions
        for i in range(3):
            await pred_repo.create({
                "model_id": model.id,
                "user_id": user.id,
                "input_data": {"feature": i},
                "output_data": {"prediction": "class_a"},
                "confidence": 0.95,
                "execution_time_ms": 100.0
            })
        
        # Get user's predictions
        predictions = await pred_repo.filter_by(user_id=user.id)
        
        assert len(predictions) >= 3
        assert all(p.user_id == user.id for p in predictions)
    
    async def test_model_predictions_count(self, db_session):
        """Test counting predictions per model."""
        model_repo = MLModelRepository(db_session)
        pred_repo = PredictionRepository(db_session)
        
        # Create model
        model = await model_repo.create({
            "name": "count_test",
            "version": "1.0.0",
            "model_type": "regression",
            "framework": "tensorflow",
            "status": "production",
            "model_path": "/models/count_test.h5"
        })
        
        # Create predictions
        initial_count = await pred_repo.count(model_id=model.id)
        
        for i in range(5):
            await pred_repo.create({
                "model_id": model.id,
                "input_data": {"x": i},
                "output_data": {"y": i * 2},
                "execution_time_ms": 50.0
            })
        
        # Count predictions
        final_count = await pred_repo.count(model_id=model.id)
        
        assert final_count == initial_count + 5


@pytest.mark.asyncio
class TestDatabasePerformance:
    """Test database performance operations."""
    
    @pytest.fixture
    async def db_session(self):
        """Get database session."""
        async for session in get_db():
            yield session
    
    async def test_bulk_operations_performance(self, db_session):
        """Test performance of bulk operations."""
        import time
        
        repo = MLModelRepository(db_session)
        
        # Prepare data
        models_data = [
            {
                "name": f"perf_model_{i}",
                "version": "1.0.0",
                "model_type": "classification",
                "framework": "scikit-learn",
                "status": "staging",
                "model_path": f"/models/perf_{i}.pkl"
            }
            for i in range(50)
        ]
        
        # Bulk create
        start = time.time()
        models = await repo.bulk_create(models_data)
        duration = time.time() - start
        
        assert len(models) == 50
        assert duration < 5.0  # Should complete in under 5 seconds
    
    async def test_search_performance(self, db_session):
        """Test search query performance."""
        import time
        
        repo = MLModelRepository(db_session)
        
        # Search
        start = time.time()
        results = await repo.search("model", limit=100)
        duration = time.time() - start
        
        assert duration < 2.0  # Should complete quickly


@pytest.mark.asyncio
class TestDatabaseConstraints:
    """Test database constraints and validations."""
    
    @pytest.fixture
    async def db_session(self):
        """Get database session."""
        async for session in get_db():
            yield session
    
    async def test_unique_username_constraint(self, db_session):
        """Test unique username constraint."""
        repo = UserRepository(db_session)
        
        username = f"unique_test_{uuid4().hex[:8]}"
        
        # Create first user
        await repo.create({
            "username": username,
            "email": "unique1@example.com",
            "hashed_password": "hashed"
        })
        
        # Try to create duplicate
        with pytest.raises(Exception):  # Will raise IntegrityError
            await repo.create({
                "username": username,
                "email": "unique2@example.com",
                "hashed_password": "hashed"
            })
    
    async def test_foreign_key_constraint(self, db_session):
        """Test foreign key constraints."""
        pred_repo = PredictionRepository(db_session)
        
        # Try to create prediction with non-existent model
        with pytest.raises(Exception):  # Will raise IntegrityError
            await pred_repo.create({
                "model_id": uuid4(),  # Non-existent
                "input_data": {"x": 1},
                "output_data": {"y": 2},
                "execution_time_ms": 100.0
            })
