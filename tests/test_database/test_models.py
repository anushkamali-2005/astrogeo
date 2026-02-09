"""
Test Database Models
====================
Unit tests for SQLAlchemy models.

Author: Production Team
Version: 1.0.0
"""

from datetime import datetime

import pytest
from geoalchemy2.shape import to_shape
from shapely.geometry import Point

from src.database.models import AgentExecution, Location, MLModel, Prediction, User


class TestUserModel:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a user instance."""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_pass",
            full_name="Test User",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_repr(self):
        """Test user string representation."""
        user = User(email="test@example.com", username="testuser")

        repr_str = repr(user)
        assert "testuser" in repr_str


class TestLocationModel:
    """Test Location model."""

    def test_location_creation(self):
        """Test creating a location instance."""
        location = Location(
            name="Test Location",
            latitude=34.0522,
            longitude=-118.2437,
            elevation=100.0,
            location_type="test",
        )

        assert location.name == "Test Location"
        assert location.latitude == 34.0522
        assert location.longitude == -118.2437
        assert location.elevation == 100.0

    def test_location_geometry_property(self):
        """Test location geometry is set from lat/lon."""
        location = Location(name="Test", latitude=40.7128, longitude=-74.0060)

        # Geometry should be set from coordinates
        assert location.geometry is not None


class TestMLModelModel:
    """Test MLModel model."""

    def test_mlmodel_creation(self):
        """Test creating an ML model instance."""
        model = MLModel(
            name="Test Model",
            model_type="classification",
            version="1.0.0",
            framework="sklearn",
            status="trained",
        )

        assert model.name == "Test Model"
        assert model.model_type == "classification"
        assert model.version == "1.0.0"
        assert model.status == "trained"

    def test_mlmodel_metrics_json(self):
        """Test ML model can store metrics as JSON."""
        model = MLModel(
            name="Test", model_type="classification", metrics={"accuracy": 0.95, "precision": 0.92}
        )

        assert model.metrics["accuracy"] == 0.95
        assert model.metrics["precision"] == 0.92


class TestPredictionModel:
    """Test Prediction model."""

    def test_prediction_creation(self):
        """Test creating a prediction instance."""
        prediction = Prediction(
            model_id="550e8400-e29b-41d4-a716-446655440000",
            input_data={"feature1": 10, "feature2": 20},
            prediction_result=0.85,
            confidence_score=0.92,
        )

        assert prediction.prediction_result == 0.85
        assert prediction.confidence_score == 0.92
        assert prediction.input_data["feature1"] == 10


class TestAgentExecutionModel:
    """Test AgentExecution model."""

    def test_agent_execution_creation(self):
        """Test creating an agent execution instance."""
        execution = AgentExecution(
            agent_type="data", task="Process dataset", status="completed", duration_seconds=5.2
        )

        assert execution.agent_type == "data"
        assert execution.task == "Process dataset"
        assert execution.status == "completed"
        assert execution.duration_seconds == 5.2

    def test_agent_execution_result_json(self):
        """Test agent execution can store result as JSON."""
        execution = AgentExecution(
            agent_type="ml", task="Train model", result={"model_id": "123", "accuracy": 0.95}
        )

        assert execution.result["model_id"] == "123"
        assert execution.result["accuracy"] == 0.95
