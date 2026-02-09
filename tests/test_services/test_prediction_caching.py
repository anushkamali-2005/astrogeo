"""
Test Prediction Service with Caching
======================================
Tests for Redis caching integration in PredictionService.

Author: Production Team  
Version: 1.0.0
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from src.services.prediction_service import PredictionService
from src.core.cache import get_cache
from src.schemas.requests import PredictionRequest


class TestPredictionServiceCaching:
    """Tests for PredictionService caching functionality."""
    
    @pytest.fixture
    async def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        db.add = Mock()
        return db
    
    @pytest.fixture
    def prediction_service(self):
        """Create prediction service instance."""
        return PredictionService()
    
    @pytest.fixture
    def sample_request(self):
        """Create sample prediction request."""
        return PredictionRequest(
            model_id=uuid4(),
            features={
                "latitude": 40.7128,
                "longitude": -74.0060,
                "population": 8000000,
                "area_sqkm": 783.8
            },
            return_probabilities=True
        )
    
    @pytest.mark.asyncio
    async def test_cache_initialization(self, prediction_service):
        """Test that cache is initialized."""
        assert prediction_service.redis_cache is not None
        assert prediction_service.cache_ttl == 1800
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, prediction_service):
        """Test cache key generation."""
        model_id = str(uuid4())
        features = {"lat": 1.0, "lon": 2.0}
        
        cache_key = prediction_service._generate_cache_key(model_id, features)
        
        assert "model_id" in cache_key
        assert "features" in cache_key
        assert cache_key["model_id"] == model_id
        assert cache_key["features"] == features
    
    @pytest.mark.asyncio
    async def test_prediction_without_cache(
        self,
        prediction_service,
        mock_db,
        sample_request
    ):
        """Test prediction without using cache."""
        with patch.object(prediction_service, '_get_model_from_db') as mock_get_model, \
             patch.object(prediction_service, '_load_model') as mock_load, \
             patch.object(prediction_service, '_make_prediction') as mock_predict:
            
            # Mock model
            mock_model = Mock()
            mock_model.id = uuid4()
            mock_model.name = "test_model"
            mock_model.version = "1.0.0"
            mock_get_model.return_value = mock_model
            
            # Mock loaded model
            mock_load.return_value = {"model": "loaded"}
            
            # Mock prediction
            mock_predict.return_value = {
                "prediction": "urban",
                "confidence": 0.85,
                "probabilities": {"urban": 0.85, "rural": 0.15}
            }
            
            # Make prediction without cache
            result = await prediction_service.predict(
                db=mock_db,
                request=sample_request,
                use_cache=False
            )
            
            assert result is not None
            assert result.prediction == "urban"
    
    @pytest.mark.asyncio
    async def test_prediction_cache_miss_then_hit(
        self,
        prediction_service,
        mock_db,
        sample_request
    ):
        """Test cache miss followed by cache hit."""
        if not prediction_service.redis_cache.enabled:
            pytest.skip("Redis not available")
        
        with patch.object(prediction_service, '_get_model_from_db') as mock_get_model, \
             patch.object(prediction_service, '_load_model') as mock_load, \
             patch.object(prediction_service, '_make_prediction') as mock_predict:
            
            mock_model = Mock()
            mock_model.id = uuid4()
            mock_model.name = "test_model"
            mock_model.version = "1.0.0"
            mock_get_model.return_value = mock_model
            
            mock_load.return_value = {"model": "loaded"}
            
            mock_predict.return_value = {
                "prediction": "urban",
                "confidence": 0.85
            }
            
            # First call - cache miss
            result1 = await prediction_service.predict(
                db=mock_db,
                request=sample_request,
                use_cache=True
            )
            
            # Model should be loaded
            assert mock_load.called
            
            # Second call with same request - cache hit
            result2 = await prediction_service.predict(
                db=mock_db,
                request=sample_request,
                use_cache=True
            )
            
            # Results should match
            assert result1.prediction == result2.prediction
    
    def test_cache_invalidation(self, prediction_service):
        """Test cache invalidation."""
        if not prediction_service.redis_cache.enabled:
            pytest.skip("Redis not available")
        
        from src.core.cache_utils import clear_all_prediction_cache
        
        # Clear cache
        count = clear_all_prediction_cache()
        
        assert isinstance(count, int)
    
    def test_cache_stats(self, prediction_service):
        """Test cache statistics."""
        from src.core.cache_utils import get_cache_stats
        
        stats = get_cache_stats()
        
        assert "enabled" in stats
        if stats["enabled"]:
            assert "keys" in stats or "error" in stats
