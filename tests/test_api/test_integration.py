"""
API Integration Tests
====================
Test API endpoints with real requests.

Author: Production Team
Version: 1.0.0
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# HEALTH ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_basic_health_check(self, client: AsyncClient):
        """Test basic health endpoint."""
        response = await client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "AstroGeo AI MLOps"
    
    async def test_ping_endpoint(self, client: AsyncClient):
        """Test ping endpoint."""
        response = await client.get("/api/v1/ping")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ping"] == "pong"
    
    async def test_detailed_health_check(self, client: AsyncClient):
        """Test detailed health endpoint."""
        response = await client.get("/api/v1/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert "database" in data["components"]


# ============================================================================
# PREDICTION ENDPOINT TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestPredictionEndpoints:
    """Test prediction endpoints."""
    
    async def test_make_prediction(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features
    ):
        """Test single prediction."""
        client, auth_headers = authenticated_client
        
        response = await client.post(
            "/api/v1/predict",
            json={
                "model_id": str(test_model.id),
                "features": sample_features,
                "return_probabilities": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "prediction" in data["data"]
        assert "confidence" in data["data"]
        assert "execution_time_ms" in data["data"]
    
    async def test_make_prediction_by_name(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features
    ):
        """Test prediction with model name."""
        client, auth_headers = authenticated_client
        
        response = await client.post(
            "/api/v1/predict",
            json={
                "model_name": test_model.name,
                "features": sample_features,
                "return_probabilities": False
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_batch_prediction(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features
    ):
        """Test batch predictions."""
        client, auth_headers = authenticated_client
        
        response = await client.post(
            "/api/v1/predict/batch",
            json={
                "model_id": str(test_model.id),
                "features_list": [sample_features, sample_features],
                "return_probabilities": True
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total_count"] == 2
        assert data["data"]["successful_count"] >= 0
        assert len(data["data"]["predictions"]) == 2
    
    async def test_prediction_without_auth(
        self,
        client: AsyncClient,
        sample_features
    ):
        """Test prediction without authentication."""
        response = await client.post(
            "/api/v1/predict",
            json={"features": sample_features}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    async def test_batch_size_limit(
        self,
        authenticated_client: tuple,
        test_model
    ):
        """Test batch size validation."""
        client, auth_headers = authenticated_client
        
        # Create batch larger than limit
        large_batch = [{"feature": i} for i in range(1001)]
        
        response = await client.post(
            "/api/v1/predict/batch",
            json={
                "model_id": str(test_model.id),
                "features_list": large_batch
            },
            headers=auth_headers
        )
        
        assert response.status_code == 400  # Bad Request
    
    async def test_get_prediction(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features,
        db_session
    ):
        """Test get prediction by ID."""
        from src.database.models import Prediction
        
        client, auth_headers = authenticated_client
        
        # Create a prediction first
        prediction = Prediction(
            model_id=test_model.id,
            input_data=sample_features,
            output_data={"prediction": "test"},
            confidence=0.85,
            execution_time_ms=10.5
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)
        
        # Get prediction
        response = await client.get(
            f"/api/v1/predictions/{prediction.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(prediction.id)
    
    async def test_submit_feedback(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features,
        db_session
    ):
        """Test submit prediction feedback."""
        from src.database.models import Prediction
        
        client, auth_headers = authenticated_client
        
        # Create prediction
        prediction = Prediction(
            model_id=test_model.id,
            input_data=sample_features,
            output_data={"prediction": "test"},
            confidence=0.85,
            execution_time_ms=10.5
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)
        
        # Submit feedback
        response = await client.post(
            f"/api/v1/predictions/{prediction.id}/feedback",
            params={
                "feedback_score": 5,
                "feedback_comment": "Great prediction!"
            },
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    async def test_get_user_predictions(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features,
        db_session
    ):
        """Test get user prediction history."""
        from src.database.models import Prediction, User
        from sqlalchemy import select
        
        client, auth_headers = authenticated_client
        
        # Get user from session
        result = await db_session.execute(
            select(User).where(User.email == "test@example.com")
        )
        user = result.scalar_one()
        
        # Create predictions
        for i in range(5):
            prediction = Prediction(
                model_id=test_model.id,
                user_id=user.id,
                input_data=sample_features,
                output_data={"prediction": f"test_{i}"},
                confidence=0.85,
                execution_time_ms=10.5
            )
            db_session.add(prediction)
        
        await db_session.commit()
        
        # Get history
        response = await client.get(
            "/api/v1/predictions/user/history",
            params={"limit": 3, "offset": 0},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["predictions"]) == 3
        assert data["data"]["total"] == 5
        assert data["data"]["has_more"] is True


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.integration
class TestErrorHandling:
    """Test error handling."""
    
    async def test_invalid_model_id(
        self,
        authenticated_client: tuple,
        sample_features
    ):
        """Test prediction with invalid model ID."""
        client, auth_headers = authenticated_client
        
        response = await client.post(
            "/api/v1/predict",
            json={
                "model_id": "00000000-0000-0000-0000-000000000000",
                "features": sample_features
            },
            headers=auth_headers
        )
        
        assert response.status_code == 404  # Not found
    
    async def test_missing_features(
        self,
        authenticated_client: tuple,
        test_model
    ):
        """Test prediction with missing features."""
        client, auth_headers = authenticated_client
        
        response = await client.post(
            "/api/v1/predict",
            json={
                "model_id": str(test_model.id),
                "features": {}  # Empty features
            },
            headers=auth_headers
        )
        
        # Should handle gracefully
        assert response.status_code in [400, 422, 500]
    
    async def test_invalid_feedback_score(
        self,
        authenticated_client: tuple,
        test_model,
        sample_features,
        db_session
    ):
        """Test invalid feedback score."""
        from src.database.models import Prediction
        
        client, auth_headers = authenticated_client
        
        # Create prediction
        prediction = Prediction(
            model_id=test_model.id,
            input_data=sample_features,
            output_data={"prediction": "test"},
            confidence=0.85,
            execution_time_ms=10.5
        )
        db_session.add(prediction)
        await db_session.commit()
        await db_session.refresh(prediction)
        
        # Submit invalid feedback
        response = await client.post(
            f"/api/v1/predictions/{prediction.id}/feedback",
            params={"feedback_score": 10},  # Invalid: > 5
            headers=auth_headers
        )
        
        assert response.status_code == 400


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
