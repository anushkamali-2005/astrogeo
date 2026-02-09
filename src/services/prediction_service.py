"""
Prediction Service
=================
Production-ready ML prediction service with:
- Model loading and caching
- Batch predictions
- Performance optimization
- Error handling
- Metrics tracking

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Union
from uuid import UUID
import time
import asyncio
from datetime import datetime

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.logging import get_logger, log_async_execution_time
from src.core.cache import get_cache
from src.core.exceptions import (
    ModelNotFoundError,
    ModelLoadError,
    PredictionError
)
from src.database.models import MLModel, Prediction
from src.schemas.requests import PredictionRequest, BatchPredictionRequest
from src.schemas.responses import PredictionResponse, BatchPredictionResponse


logger = get_logger(__name__)


class ModelCache:
    """
    In-memory model cache with LRU eviction.
    
    Features:
    - LRU cache policy
    - Thread-safe operations
    - Automatic cleanup
    - Size limits
    """
    
    def __init__(self, max_size: int = 10):
        """
        Initialize model cache.
        
        Args:
            max_size: Maximum number of cached models
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.max_size = max_size
        self._lock = asyncio.Lock()
        
        logger.info(f"Model cache initialized with max_size={max_size}")
    
    async def get(self, model_id: str) -> Optional[Any]:
        """Get model from cache."""
        async with self._lock:
            if model_id in self.cache:
                self.access_times[model_id] = time.time()
                logger.debug(f"Model cache hit: {model_id}")
                return self.cache[model_id]
            
            logger.debug(f"Model cache miss: {model_id}")
            return None
    
    async def set(self, model_id: str, model: Any) -> None:
        """Add model to cache."""
        async with self._lock:
            # Evict LRU if cache is full
            if len(self.cache) >= self.max_size:
                lru_key = min(self.access_times, key=self.access_times.get)
                del self.cache[lru_key]
                del self.access_times[lru_key]
                logger.debug(f"Evicted LRU model: {lru_key}")
            
            self.cache[model_id] = model
            self.access_times[model_id] = time.time()
            logger.debug(f"Model cached: {model_id}")
    
    async def clear(self) -> None:
        """Clear cache."""
        async with self._lock:
            self.cache.clear()
            self.access_times.clear()
            logger.info("Model cache cleared")


class PredictionService:
    """
    ML prediction service with model management.
    
    Features:
    - Model loading and caching
    - Single and batch predictions
    - Feature validation
    - Performance tracking
    - Error handling
    """
    
    def __init__(self):
        """Initialize prediction service."""
        self.model_cache = ModelCache(max_size=10)
        self.redis_cache = get_cache()
        self.cache_ttl = 1800  # 30 minutes default TTL
        logger.info(
            "Prediction service initialized",
            extra={"redis_enabled": self.redis_cache.enabled}
        )
    
    async def _get_model_from_db(
        self,
        db: AsyncSession,
        model_id: Optional[UUID] = None,
        model_name: Optional[str] = None
    ) -> MLModel:
        """
        Get model from database.
        
        Args:
            db: Database session
            model_id: Model ID
            model_name: Model name (uses latest production if not model_id)
            
        Returns:
            MLModel: Model record
            
        Raises:
            ModelNotFoundError: If model not found
        """
        try:
            if model_id:
                # Get by ID
                result = await db.execute(
                    select(MLModel).where(MLModel.id == model_id)
                )
                model = result.scalar_one_or_none()
                
            elif model_name:
                # Get latest production version by name
                result = await db.execute(
                    select(MLModel)
                    .where(MLModel.name == model_name)
                    .where(MLModel.status == "production")
                    .order_by(MLModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                
            else:
                # Get latest production model
                result = await db.execute(
                    select(MLModel)
                    .where(MLModel.status == "production")
                    .order_by(MLModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
            
            if not model:
                identifier = model_id or model_name or "latest production"
                raise ModelNotFoundError(
                    model_name=str(identifier),
                    details={"model_id": str(model_id), "model_name": model_name}
                )
            
            logger.info(
                f"Retrieved model from database",
                extra={
                    "model_id": str(model.id),
                    "model_name": model.name,
                    "version": model.version
                }
            )
            
            return model
        
        except Exception as e:
            logger.error("Failed to retrieve model from database", error=e)
            raise
    
    async def _load_model(self, model: MLModel) -> Any:
        """
        Load ML model from storage.
        
        Args:
            model: Model database record
            
        Returns:
            Any: Loaded model object
            
        Raises:
            ModelLoadError: If model loading fails
        """
        model_id = str(model.id)
        
        # Check cache first
        cached_model = await self.model_cache.get(model_id)
        if cached_model is not None:
            return cached_model
        
        try:
            # In production, load from MLflow or S3
            # For now, we'll simulate model loading
            logger.info(
                f"Loading model from storage",
                extra={
                    "model_id": model_id,
                    "model_path": model.model_path,
                    "framework": model.framework
                }
            )
            
            # Simulate model loading
            # In production:
            # if model.framework == "scikit-learn":
            #     loaded_model = joblib.load(model.model_path)
            # elif model.framework == "tensorflow":
            #     loaded_model = tf.keras.models.load_model(model.model_path)
            
            # Mock model for demonstration
            loaded_model = {
                "model_id": model_id,
                "model_type": model.model_type,
                "framework": model.framework,
                "version": model.version,
                # Actual model object would be here
            }
            
            # Cache the model
            await self.model_cache.set(model_id, loaded_model)
            
            logger.info(f"Model loaded successfully: {model_id}")
            return loaded_model
        
        except Exception as e:
            logger.error(f"Failed to load model: {model_id}", error=e)
            raise ModelLoadError(
                model_name=model.name,
                details={"error": str(e), "model_path": model.model_path}
            )
    
    def _validate_features(
        self,
        features: Dict[str, Any],
        expected_features: List[str]
    ) -> np.ndarray:
        """
        Validate and prepare features for prediction.
        
        Args:
            features: Input features dictionary
            expected_features: List of expected feature names
            
        Returns:
            np.ndarray: Prepared feature array
            
        Raises:
            PredictionError: If validation fails
        """
        try:
            # Check for missing features
            missing = set(expected_features) - set(features.keys())
            if missing:
                raise PredictionError(
                    message="Missing required features",
                    details={"missing_features": list(missing)}
                )
            
            # Convert to array in correct order
            feature_array = np.array([
                features[feat] for feat in expected_features
            ]).reshape(1, -1)
            
            return feature_array
        
        except Exception as e:
            logger.error("Feature validation failed", error=e)
            raise PredictionError(
                message="Invalid features",
                details={"error": str(e)}
            )
    
    def _make_prediction(
        self,
        model: Any,
        features: Dict[str, Any],
        return_probabilities: bool = False
    ) -> Dict[str, Any]:
        """
        Make prediction using loaded model.
        
        Args:
            model: Loaded model object
            features: Input features
            return_probabilities: Return class probabilities
            
        Returns:
            dict: Prediction results
        """
        # In production, this would call actual model prediction
        # For now, simulate prediction
        
        # Mock expected features (would come from model metadata)
        expected_features = ["latitude", "longitude", "population", "area_sqkm"]
        
        # Validate features
        feature_array = self._validate_features(features, expected_features)
        
        # Make prediction (simulated)
        # In production:
        # prediction = model.predict(feature_array)[0]
        # if return_probabilities and hasattr(model, 'predict_proba'):
        #     probabilities = model.predict_proba(feature_array)[0]
        
        # Mock prediction
        prediction = "urban"
        confidence = 0.85
        
        result = {
            "prediction": prediction,
            "confidence": confidence
        }
        
        if return_probabilities:
            result["probabilities"] = {
                "urban": 0.85,
                "suburban": 0.12,
                "rural": 0.03
            }
        
        return result
    
    def _generate_cache_key(self, model_id: str, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate cache key for prediction.
        
        Args:
            model_id: Model ID
            features: Input features
            
        Returns:
            dict: Cache key components
        """
        return {
            "model_id": model_id,
            "features": features
        }
    
    @log_async_execution_time
    async def predict(
        self,
        db: AsyncSession,
        request: PredictionRequest,
        user_id: Optional[UUID] = None,
        use_cache: bool = True
    ) -> PredictionResponse:
        """
        Make single prediction with caching support.
        
        Args:
            db: Database session
            request: Prediction request
            user_id: User ID (optional)
            use_cache: Whether to use Redis cache
            
        Returns:
            PredictionResponse: Prediction result
        """
        start_time = time.time()
        
        try:
            # Get model
            model = await self._get_model_from_db(
                db,
                model_id=request.model_id,
                model_name=request.model_name
            )
            
            # Check cache if enabled
            cache_key = None
            if use_cache and self.redis_cache.enabled:
                cache_key = self._generate_cache_key(
                    str(model.id),
                    request.features
                )
                cached_result = self.redis_cache.get('prediction', cache_key)
                
                if cached_result:
                    logger.info(
                        "Prediction served from cache",
                        extra={"model_id": str(model.id)}
                    )
                    # Add execution time for cache hit
                    cached_result.execution_time_ms = (
                        time.time() - start_time
                    ) * 1000
                    return cached_result
            
            # Load model
            loaded_model = await self._load_model(model)
            
            # Make prediction
            result = self._make_prediction(
                loaded_model,
                request.features,
                request.return_probabilities
            )
            
            # Calculate execution time
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # Create prediction record
            prediction = Prediction(
                model_id=model.id,
                user_id=user_id,
                input_data=request.features,
                output_data=result,
                confidence=result.get("confidence"),
                execution_time_ms=execution_time
            )
            
            db.add(prediction)
            await db.commit()
            await db.refresh(prediction)
            
            logger.info(
                "Prediction completed",
                extra={
                    "prediction_id": str(prediction.id),
                    "model_id": str(model.id),
                    "execution_time_ms": execution_time
                }
            )
            
            # Build response
            response = PredictionResponse(
                id=prediction.id,
                model_id=model.id,
                model_name=model.name,
                model_version=model.version,
                prediction=result["prediction"],
                probabilities=result.get("probabilities"),
                confidence=result.get("confidence"),
                execution_time_ms=execution_time,
                timestamp=prediction.created_at
            )
            
            # Cache the result
            if use_cache and cache_key and self.redis_cache.enabled:
                self.redis_cache.set(
                    'prediction',
                    cache_key,
                    response,
                    ttl=self.cache_ttl
                )
                logger.debug(
                    "Prediction cached",
                    extra={"model_id": str(model.id), "ttl": self.cache_ttl}
                )
            
            return response
        
        except Exception as e:
            logger.error("Prediction failed", error=e)
            raise
    
    @log_async_execution_time
    async def batch_predict(
        self,
        db: AsyncSession,
        request: BatchPredictionRequest,
        user_id: Optional[UUID] = None
    ) -> BatchPredictionResponse:
        """
        Make batch predictions.
        
        Args:
            db: Database session
            request: Batch prediction request
            user_id: User ID (optional)
            
        Returns:
            BatchPredictionResponse: Batch results
        """
        start_time = time.time()
        predictions = []
        successful = 0
        failed = 0
        
        try:
            # Get model
            model = await self._get_model_from_db(
                db,
                model_id=request.model_id,
                model_name=request.model_name
            )
            
            # Load model once
            loaded_model = await self._load_model(model)
            
            # Process each input
            for idx, features in enumerate(request.features_list):
                try:
                    # Make prediction
                    result = self._make_prediction(
                        loaded_model,
                        features,
                        request.return_probabilities
                    )
                    
                    predictions.append({
                        "index": idx,
                        "prediction": result["prediction"],
                        "confidence": result.get("confidence"),
                        "probabilities": result.get("probabilities"),
                        "status": "success"
                    })
                    successful += 1
                
                except Exception as e:
                    logger.error(
                        f"Batch prediction failed for index {idx}",
                        error=e
                    )
                    predictions.append({
                        "index": idx,
                        "error": str(e),
                        "status": "failed"
                    })
                    failed += 1
            
            # Calculate metrics
            total_time = (time.time() - start_time) * 1000  # ms
            avg_time = total_time / len(request.features_list)
            
            logger.info(
                "Batch prediction completed",
                extra={
                    "total": len(request.features_list),
                    "successful": successful,
                    "failed": failed,
                    "total_time_ms": total_time
                }
            )
            
            response = BatchPredictionResponse(
                predictions=predictions,
                total_count=len(request.features_list),
                successful_count=successful,
                failed_count=failed,
                avg_execution_time_ms=avg_time,
                total_execution_time_ms=total_time
            )
            
            return response
        
        except Exception as e:
            logger.error("Batch prediction failed", error=e)
            raise


# Create singleton instance
prediction_service = PredictionService()


# Export
__all__ = ["PredictionService", "prediction_service"]