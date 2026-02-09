"""
Response Schemas
===============
Pydantic models for API responses with:
- Consistent structure
- Type safety
- Documentation
- Examples

Author: Production Team
Version: 1.0.0
"""

from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.generics import GenericModel


# ============================================================================
# GENERIC RESPONSE WRAPPERS
# ============================================================================

T = TypeVar('T')


class SuccessResponse(GenericModel, Generic[T]):
    """Generic success response wrapper."""
    
    success: bool = Field(True, description="Success status")
    data: T = Field(..., description="Response data")
    message: Optional[str] = Field(None, description="Optional message")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "Operation completed successfully",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """Error response."""
    
    success: bool = Field(False, description="Success status")
    error: Dict[str, Any] = Field(..., description="Error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "code": "ERR_001",
                    "message": "Operation failed",
                    "details": {}
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class PaginatedResponse(GenericModel, Generic[T]):
    """Paginated response wrapper."""
    
    success: bool = Field(True)
    data: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="More items available")
    
    class Config:
        schema_extra = {
            "example": {
                "success": True,
                "data": [],
                "total": 100,
                "limit": 10,
                "offset": 0,
                "has_more": True
            }
        }


# ============================================================================
# USER RESPONSES
# ============================================================================

class UserResponse(BaseModel):
    """User profile response."""
    
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "username": "john_doe",
                "full_name": "John Doe",
                "bio": "Data scientist",
                "avatar_url": None,
                "is_active": True,
                "is_verified": True,
                "created_at": "2024-01-01T12:00:00Z",
                "last_login": "2024-01-15T08:30:00Z"
            }
        }


class TokenResponse(BaseModel):
    """Authentication token response."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user: UserResponse = Field(..., description="User information")
    
    class Config:
        schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "username": "john_doe"
                }
            }
        }


# ============================================================================
# LOCATION RESPONSES
# ============================================================================

class LocationResponse(BaseModel):
    """Location response."""
    
    id: UUID
    name: str
    description: Optional[str]
    location_type: str
    latitude: float
    longitude: float
    altitude: Optional[float]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: str
    postal_code: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Central Park",
                "description": "Large public park",
                "location_type": "poi",
                "latitude": 40.785091,
                "longitude": -73.968285,
                "altitude": 10.0,
                "address": "Central Park, New York, NY",
                "city": "New York",
                "state": "New York",
                "country": "US",
                "postal_code": "10024",
                "metadata": {"established": 1857},
                "created_at": "2024-01-01T12:00:00Z"
            }
        }


class LocationDistanceResponse(BaseModel):
    """Location with distance."""
    
    location: LocationResponse
    distance_km: float = Field(..., description="Distance in kilometers")
    
    class Config:
        schema_extra = {
            "example": {
                "location": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "name": "Central Park",
                    "latitude": 40.785091,
                    "longitude": -73.968285
                },
                "distance_km": 5.2
            }
        }


# ============================================================================
# PREDICTION RESPONSES
# ============================================================================

class PredictionResponse(BaseModel):
    """Single prediction response."""
    
    id: UUID
    model_id: UUID
    model_name: str
    model_version: str
    prediction: Any = Field(..., description="Prediction value")
    probabilities: Optional[Dict[str, float]] = Field(
        None,
        description="Class probabilities"
    )
    confidence: Optional[float] = Field(None, description="Confidence score")
    feature_importance: Optional[Dict[str, float]] = Field(
        None,
        description="Feature importance scores"
    )
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    timestamp: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "model_id": "660e8400-e29b-41d4-a716-446655440000",
                "model_name": "geo_classifier_v1",
                "model_version": "1.0.0",
                "prediction": "urban",
                "probabilities": {
                    "urban": 0.85,
                    "suburban": 0.12,
                    "rural": 0.03
                },
                "confidence": 0.85,
                "feature_importance": {
                    "population": 0.45,
                    "area": 0.30,
                    "density": 0.25
                },
                "execution_time_ms": 23.5,
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class BatchPredictionResponse(BaseModel):
    """Batch prediction response."""
    
    predictions: List[Dict[str, Any]] = Field(..., description="List of predictions")
    total_count: int = Field(..., description="Total predictions made")
    successful_count: int = Field(..., description="Successful predictions")
    failed_count: int = Field(..., description="Failed predictions")
    avg_execution_time_ms: float = Field(..., description="Average execution time")
    total_execution_time_ms: float = Field(..., description="Total execution time")
    
    class Config:
        schema_extra = {
            "example": {
                "predictions": [
                    {"prediction": "urban", "confidence": 0.85},
                    {"prediction": "suburban", "confidence": 0.72}
                ],
                "total_count": 2,
                "successful_count": 2,
                "failed_count": 0,
                "avg_execution_time_ms": 15.3,
                "total_execution_time_ms": 30.6
            }
        }


# ============================================================================
# MODEL RESPONSES
# ============================================================================

class MLModelResponse(BaseModel):
    """ML model response."""
    
    id: UUID
    name: str
    version: str
    model_type: str
    framework: str
    status: str
    metrics: Dict[str, float]
    parameters: Dict[str, Any]
    mlflow_run_id: Optional[str]
    created_at: datetime
    deployed_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "churn_predictor",
                "version": "2.1.0",
                "model_type": "classification",
                "framework": "scikit-learn",
                "status": "production",
                "metrics": {
                    "accuracy": 0.92,
                    "precision": 0.89,
                    "recall": 0.91,
                    "f1_score": 0.90
                },
                "parameters": {
                    "n_estimators": 100,
                    "max_depth": 10
                },
                "mlflow_run_id": "abc123xyz",
                "created_at": "2024-01-01T12:00:00Z",
                "deployed_at": "2024-01-05T10:00:00Z"
            }
        }


class ModelTrainingResponse(BaseModel):
    """Model training response."""
    
    job_id: UUID = Field(..., description="Training job ID")
    model_name: str
    status: str = Field(..., description="Training status (pending/running/completed/failed)")
    started_at: datetime
    estimated_completion: Optional[datetime] = None
    progress_percent: Optional[float] = Field(None, ge=0, le=100)
    
    class Config:
        schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "model_name": "churn_predictor_v3",
                "status": "running",
                "started_at": "2024-01-01T12:00:00Z",
                "estimated_completion": "2024-01-01T12:15:00Z",
                "progress_percent": 45.0
            }
        }


# ============================================================================
# AGENT RESPONSES
# ============================================================================

class AgentExecutionResponse(BaseModel):
    """Agent execution response."""
    
    id: UUID
    agent_name: str
    task: str
    status: str
    result: Optional[Dict[str, Any]]
    error_message: Optional[str]
    execution_time_ms: float
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_name": "ml_agent",
                "task": "Train classification model",
                "status": "completed",
                "result": {
                    "model_id": "abc123",
                    "accuracy": 0.92
                },
                "error_message": None,
                "execution_time_ms": 5432.1,
                "tokens_used": 1250,
                "cost_usd": 0.025,
                "created_at": "2024-01-01T12:00:00Z",
                "completed_at": "2024-01-01T12:05:32Z"
            }
        }


# ============================================================================
# HEALTH CHECK RESPONSES
# ============================================================================

class ComponentHealth(BaseModel):
    """Individual component health."""
    
    status: str = Field(..., description="Component status (healthy/unhealthy/degraded)")
    response_time_ms: Optional[float] = None
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Basic health response."""
    
    status: str = Field(..., description="Health status (healthy/unhealthy/degraded)")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "AstroGeo AI MLOps",
                "version": "1.0.0",
                "environment": "production",
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class DetailedHealthResponse(BaseModel):
    """Detailed health response with components."""
    
    status: str = Field(..., description="Overall health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Environment name")
    components: Dict[str, Any] = Field(..., description="Component health details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "service": "AstroGeo AI MLOps",
                "version": "1.0.0",
                "environment": "production",
                "components": {
                    "database": {"status": "healthy"},
                    "redis": {"status": "healthy"}
                },
                "timestamp": "2024-01-01T12:00:00Z"
            }
        }


class HealthCheckResponse(BaseModel):
    """Detailed health check response."""
    
    status: str = Field(..., description="Overall status")
    timestamp: datetime
    service: str
    version: str
    environment: str
    components: Dict[str, ComponentHealth] = Field(..., description="Component health statuses")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "service": "AstroGeo AI MLOps",
                "version": "1.0.0",
                "environment": "production",
                "components": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 5.2,
                        "details": {"connections": 10}
                    },
                    "cache": {
                        "status": "healthy",
                        "response_time_ms": 1.1
                    },
                    "mlflow": {
                        "status": "healthy",
                        "response_time_ms": 23.4
                    }
                }
            }
        }


# ============================================================================
# STATISTICS RESPONSES
# ============================================================================

class SystemStatsResponse(BaseModel):
    """System statistics response."""
    
    total_users: int
    total_predictions: int
    total_models: int
    total_locations: int
    active_agents: int
    uptime_seconds: float
    cpu_usage_percent: float
    memory_usage_percent: float
    
    class Config:
        schema_extra = {
            "example": {
                "total_users": 1250,
                "total_predictions": 45000,
                "total_models": 23,
                "total_locations": 5600,
                "active_agents": 3,
                "uptime_seconds": 864000,
                "cpu_usage_percent": 45.2,
                "memory_usage_percent": 62.8
            }
        }


# Export all schemas
__all__ = [
    "SuccessResponse",
    "ErrorResponse",
    "PaginatedResponse",
    "UserResponse",
    "TokenResponse",
    "LocationResponse",
    "LocationDistanceResponse",
    "PredictionResponse",
    "BatchPredictionResponse",
    "MLModelResponse",
    "ModelTrainingResponse",
    "AgentExecutionResponse",
    "ComponentHealth",
    "HealthResponse",
    "DetailedHealthResponse",
    "HealthCheckResponse",
    "SystemStatsResponse"
]