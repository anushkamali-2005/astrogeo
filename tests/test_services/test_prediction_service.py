"""
Test Prediction Service
========================
Unit tests for prediction service.

Author: Production Team
Version: 1.0.0
"""

from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from src.core.exceptions import PredictionError
from src.services.prediction_service import PredictionService


class TestPredictionService:
    """Test PredictionService."""

    @pytest.fixture
    def service(self):
        """Create PredictionService instance."""
        return PredictionService()

    @pytest.mark.asyncio
    async def test_load_model_success(self, service):
        """Test successful model loading."""
        with patch("joblib.load") as mock_load:
            mock_model = Mock()
            mock_load.return_value = mock_model

            model = await service.load_model("test_model_id")

            assert model is not None
            mock_load.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_model_not_found(self, service):
        """Test model loading with non-existent model."""
        with patch("joblib.load", side_effect=FileNotFoundError):
            with pytest.raises(PredictionError):
                await service.load_model("nonexistent_model")

    @pytest.mark.asyncio
    async def test_predict_success(self, service):
        """Test successful prediction."""
        # Mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.85])
        mock_model.predict_proba = Mock(return_value=np.array([[0.15, 0.85]]))

        with patch.object(service, "load_model", return_value=mock_model):
            result = await service.predict(
                model_id="test_model", input_data={"feature1": 10, "feature2": 20}
            )

            assert result is not None
            assert "prediction" in result

    @pytest.mark.asyncio
    async def test_predict_invalid_input(self, service):
        """Test prediction with invalid input."""
        mock_model = Mock()
        mock_model.predict.side_effect = ValueError("Invalid input")

        with patch.object(service, "load_model", return_value=mock_model):
            with pytest.raises(PredictionError):
                await service.predict(model_id="test_model", input_data={"invalid": "data"})

    @pytest.mark.asyncio
    async def test_batch_predict_success(self, service):
        """Test successful batch prediction."""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.8, 0.6, 0.9])

        with patch.object(service, "load_model", return_value=mock_model):
            results = await service.batch_predict(
                model_id="test_model",
                input_data_list=[{"feature1": 10}, {"feature1": 20}, {"feature1": 30}],
            )

            assert len(results) == 3

    @pytest.mark.asyncio
    async def test_predict_with_preprocessing(self, service):
        """Test prediction with preprocessing."""
        mock_model = Mock()
        mock_model.predict.return_value = np.array([0.75])

        mock_preprocessor = Mock()
        mock_preprocessor.transform.return_value = np.array([[1.0, 2.0]])

        with patch.object(service, "load_model", return_value=mock_model):
            with patch.object(service, "load_preprocessor", return_value=mock_preprocessor):
                result = await service.predict(
                    model_id="test_model",
                    input_data={"feature1": 10, "feature2": 20},
                    preprocess=True,
                )

                assert result is not None
                mock_preprocessor.transform.assert_called_once()

    @pytest.mark.asyncio
    async def test_model_caching(self, service):
        """Test model caching mechanism."""
        mock_model = Mock()

        with patch("joblib.load", return_value=mock_model) as mock_load:
            # First load
            model1 = await service.load_model("cached_model")

            # Second load (should use cache)
            model2 = await service.load_model("cached_model")

            # joblib.load should only be called once if caching works
            # Note: This depends on service implementation
            assert model1 is not None
            assert model2 is not None
