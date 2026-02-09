"""
Request Schemas
==============
Pydantic models for API request validation with:
- Type validation
- Field constraints
- Custom validators
- Documentation

Author: Production Team
Version: 1.0.0
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, confloat, conint, constr, validator

# ============================================================================
# ENUMS
# ============================================================================


class ModelStatus(str, Enum):
    """ML model status."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class LocationType(str, Enum):
    """Location type."""

    CITY = "city"
    REGION = "region"
    POI = "poi"
    CUSTOM = "custom"


class AgentType(str, Enum):
    """Agent type."""

    DATA = "data"
    ML = "ml"
    GEO = "geo"
    ORCHESTRATOR = "orchestrator"


# ============================================================================
# USER SCHEMAS
# ============================================================================


class UserRegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email address")
    username: constr(min_length=3, max_length=50) = Field(
        ..., description="Username (3-50 characters, alphanumeric)"
    )
    password: constr(min_length=8, max_length=100) = Field(
        ..., description="Password (min 8 characters)"
    )
    full_name: Optional[str] = Field(None, max_length=255)

    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must be alphanumeric (underscores allowed)")
        return v.lower()

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    class Config:
        schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "john_doe",
                "password": "SecurePass123",
                "full_name": "John Doe",
            }
        }


class UserLoginRequest(BaseModel):
    """User login request."""

    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="User password")

    class Config:
        schema_extra = {"example": {"email": "user@example.com", "password": "SecurePass123"}}


class UserUpdateRequest(BaseModel):
    """User profile update request."""

    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    avatar_url: Optional[str] = Field(None, max_length=500)

    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Doe",
                "bio": "Data scientist and ML engineer",
                "avatar_url": "https://example.com/avatar.jpg",
            }
        }


# ============================================================================
# LOCATION SCHEMAS
# ============================================================================


class LocationCreateRequest(BaseModel):
    """Create location request."""

    name: constr(min_length=1, max_length=255) = Field(..., description="Location name")
    description: Optional[str] = Field(None, max_length=1000)
    location_type: LocationType = Field(..., description="Type of location")

    # Coordinates
    latitude: confloat(ge=-90, le=90) = Field(..., description="Latitude (-90 to 90)")
    longitude: confloat(ge=-180, le=180) = Field(..., description="Longitude (-180 to 180)")
    altitude: Optional[float] = Field(None, description="Altitude in meters")

    # Address
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: constr(min_length=2, max_length=2) = Field(
        ..., description="ISO 3166-1 alpha-2 country code"
    )
    postal_code: Optional[str] = Field(None, max_length=20)

    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    properties: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @validator("country")
    def validate_country_code(cls, v):
        """Validate country code format."""
        return v.upper()

    class Config:
        schema_extra = {
            "example": {
                "name": "Central Park",
                "description": "Large public park in Manhattan",
                "location_type": "poi",
                "latitude": 40.785091,
                "longitude": -73.968285,
                "address": "Central Park, New York, NY 10024",
                "city": "New York",
                "state": "New York",
                "country": "US",
                "postal_code": "10024",
                "metadata": {"established": 1857},
            }
        }


class LocationSearchRequest(BaseModel):
    """Search locations request."""

    query: Optional[str] = Field(None, description="Search query")
    location_type: Optional[LocationType] = None
    country: Optional[str] = Field(None, min_length=2, max_length=2)

    # Bounding box search
    min_latitude: Optional[confloat(ge=-90, le=90)] = None
    max_latitude: Optional[confloat(ge=-90, le=90)] = None
    min_longitude: Optional[confloat(ge=-180, le=180)] = None
    max_longitude: Optional[confloat(ge=-180, le=180)] = None

    # Radius search
    center_latitude: Optional[confloat(ge=-90, le=90)] = None
    center_longitude: Optional[confloat(ge=-180, le=180)] = None
    radius_km: Optional[confloat(gt=0, le=10000)] = Field(
        None, description="Search radius in kilometers"
    )

    # Pagination
    limit: conint(ge=1, le=100) = Field(10, description="Results per page")
    offset: conint(ge=0) = Field(0, description="Pagination offset")

    @validator("max_latitude")
    def validate_latitude_range(cls, v, values):
        """Validate latitude range."""
        if "min_latitude" in values and v is not None:
            if v <= values["min_latitude"]:
                raise ValueError("max_latitude must be greater than min_latitude")
        return v

    @validator("max_longitude")
    def validate_longitude_range(cls, v, values):
        """Validate longitude range."""
        if "min_longitude" in values and v is not None:
            if v <= values["min_longitude"]:
                raise ValueError("max_longitude must be greater than min_longitude")
        return v


# ============================================================================
# PREDICTION SCHEMAS
# ============================================================================


class PredictionRequest(BaseModel):
    """ML model prediction request."""

    model_id: Optional[UUID] = Field(
        None, description="Model ID (uses latest production model if not specified)"
    )
    model_name: Optional[str] = Field(None, description="Model name (alternative to model_id)")

    # Input data
    features: Dict[str, Any] = Field(..., description="Feature values for prediction")

    # Options
    return_probabilities: bool = Field(
        False, description="Return class probabilities (classification only)"
    )
    return_feature_importance: bool = Field(False, description="Return feature importance scores")

    class Config:
        schema_extra = {
            "example": {
                "model_name": "geo_classifier_v1",
                "features": {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "population": 8000000,
                    "area_sqkm": 783.8,
                },
                "return_probabilities": True,
            }
        }


class BatchPredictionRequest(BaseModel):
    """Batch prediction request."""

    model_id: Optional[UUID] = None
    model_name: Optional[str] = None

    # Batch inputs
    features_list: List[Dict[str, Any]] = Field(
        ..., description="List of feature dictionaries", min_items=1, max_items=1000
    )

    # Options
    return_probabilities: bool = False

    class Config:
        schema_extra = {
            "example": {
                "model_name": "geo_classifier_v1",
                "features_list": [
                    {"latitude": 40.7128, "longitude": -74.0060},
                    {"latitude": 34.0522, "longitude": -118.2437},
                ],
                "return_probabilities": True,
            }
        }


# ============================================================================
# AGENT SCHEMAS
# ============================================================================


class AgentExecutionRequest(BaseModel):
    """Agent execution request."""

    agent_type: AgentType = Field(..., description="Type of agent to execute")
    task: constr(min_length=10, max_length=5000) = Field(
        ..., description="Task description for the agent"
    )

    # Context and parameters
    context: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional context for the agent"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Agent-specific parameters"
    )

    # Options
    timeout: conint(ge=10, le=600) = Field(300, description="Execution timeout in seconds (10-600)")
    save_to_database: bool = Field(True, description="Save execution history to database")

    class Config:
        schema_extra = {
            "example": {
                "agent_type": "ml",
                "task": "Train a classification model on the latest dataset",
                "context": {"dataset_id": "abc123", "target_column": "category"},
                "parameters": {"model_type": "random_forest", "test_size": 0.2},
                "timeout": 300,
            }
        }


class MultiAgentRequest(BaseModel):
    """Multi-agent orchestration request."""

    task: constr(min_length=10, max_length=5000) = Field(
        ..., description="High-level task description"
    )

    # Agent selection
    agents: Optional[List[AgentType]] = Field(
        None, description="Specific agents to use (auto-select if not provided)"
    )

    # Options
    max_iterations: conint(ge=1, le=20) = Field(10, description="Maximum agent iterations")
    timeout: conint(ge=30, le=1800) = Field(600, description="Total timeout in seconds")

    class Config:
        schema_extra = {
            "example": {
                "task": "Analyze the geospatial distribution of customers and build a predictive model",
                "agents": ["data", "geo", "ml"],
                "max_iterations": 10,
                "timeout": 600,
            }
        }


# ============================================================================
# MODEL TRAINING SCHEMAS
# ============================================================================


class ModelTrainingRequest(BaseModel):
    """Model training request."""

    # Model info
    model_name: constr(min_length=1, max_length=255) = Field(..., description="Name for the model")
    model_type: str = Field(..., description="Type of model (e.g., 'classification', 'regression')")

    # Data
    dataset_id: Optional[UUID] = Field(None, description="Dataset ID")
    dataset_path: Optional[str] = Field(None, description="Path to dataset")
    target_column: str = Field(..., description="Target variable column name")
    feature_columns: Optional[List[str]] = Field(
        None, description="Feature columns (uses all if not specified)"
    )

    # Training parameters
    test_size: confloat(gt=0, lt=1) = Field(0.2, description="Test set size (0-1)")
    random_state: Optional[int] = Field(42, description="Random seed")

    # Hyperparameters
    hyperparameters: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Model-specific hyperparameters"
    )

    # MLflow tracking
    experiment_name: Optional[str] = Field(None, description="MLflow experiment name")

    class Config:
        schema_extra = {
            "example": {
                "model_name": "customer_churn_predictor",
                "model_type": "classification",
                "dataset_path": "s3://bucket/data/customers.csv",
                "target_column": "churn",
                "feature_columns": ["age", "tenure", "monthly_charges"],
                "test_size": 0.2,
                "hyperparameters": {"n_estimators": 100, "max_depth": 10},
                "experiment_name": "churn_prediction",
            }
        }


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================


class ModelDeployRequest(BaseModel):
    """Deploy model to production."""

    model_id: UUID = Field(..., description="Model ID to deploy")
    status: ModelStatus = Field(ModelStatus.PRODUCTION, description="Deployment status")
    notes: Optional[str] = Field(None, max_length=1000)

    class Config:
        schema_extra = {
            "example": {
                "model_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "production",
                "notes": "Deploying after successful A/B test",
            }
        }


class SystemHealthRequest(BaseModel):
    """System health check request."""

    include_database: bool = Field(True, description="Check database health")
    include_cache: bool = Field(True, description="Check Redis health")
    include_mlflow: bool = Field(True, description="Check MLflow health")

    class Config:
        schema_extra = {
            "example": {"include_database": True, "include_cache": True, "include_mlflow": True}
        }


# Export all schemas
__all__ = [
    "ModelStatus",
    "LocationType",
    "AgentType",
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserUpdateRequest",
    "LocationCreateRequest",
    "LocationSearchRequest",
    "PredictionRequest",
    "BatchPredictionRequest",
    "AgentExecutionRequest",
    "MultiAgentRequest",
    "ModelTrainingRequest",
    "ModelDeployRequest",
    "SystemHealthRequest",
]
