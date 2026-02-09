"""
Database Models
===============
SQLAlchemy ORM models for AstroGeo AI MLOps platform.

Models:
- User: User accounts and authentication
- Location: Geographic locations with PostGIS support
- MLModel: ML model metadata and versioning
- Prediction: Prediction records and results
- AgentExecution: Agent task execution logs
- Feedback: User feedback on predictions

Author: Production Team
Version: 1.0.0
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, JSON, Text,
    ForeignKey, Enum as SQLEnum, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, declarative_base
from geoalchemy2 import Geometry

# Create base class
Base = declarative_base()


# ============================================================================
# USER MODEL
# ============================================================================

class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    role = Column(String(50), default="user", nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # API Keys
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="user", cascade="all, delete-orphan")
    agent_executions = relationship("AgentExecution", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_username", "username"),
    )
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


# ============================================================================
# LOCATION MODEL
# ============================================================================

class Location(Base):
    """Location model with PostGIS geometry support."""
    
    __tablename__ = "locations"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Location Details
    name = Column(String(255), nullable=False, index=True)
    location_type = Column(
        SQLEnum("city", "region", "country", "poi", "custom", name="location_type_enum"),
        nullable=False
    )
    
    # Address Components
    address = Column(Text, nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True, index=True)
    postal_code = Column(String(20), nullable=True)
    
    # Coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # PostGIS Geometry (POINT)
    geom = Column(Geometry(geometry_type="POINT", srid=4326), nullable=False)
    
    # Additional Metadata
    population = Column(Integer, nullable=True)
    area_sqkm = Column(Float, nullable=True)
    extra_data = Column(JSON, default={}, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_location_name", "name"),
        Index("idx_location_type", "location_type"),
        Index("idx_location_country", "country"),
        Index("idx_location_geom", "geom", postgresql_using="gist"),
        CheckConstraint("latitude >= -90 AND latitude <= 90", name="check_latitude"),
        CheckConstraint("longitude >= -180 AND longitude <= 180", name="check_longitude"),
    )
    
    def __repr__(self):
        return f"<Location(id={self.id}, name={self.name}, lat={self.latitude}, lon={self.longitude})>"


# ============================================================================
# ML MODEL
# ============================================================================

class MLModel(Base):
    """ML Model metadata and versioning."""
    
    __tablename__ = "ml_models"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Model Identification
    name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    # Model Type
    model_type = Column(
        SQLEnum("classification", "regression", "clustering", "other", name="model_type_enum"),
        nullable=False
    )
    framework = Column(String(50), nullable=False)  # scikit-learn, tensorflow, pytorch, etc.
    
    # Storage
    model_path = Column(String(500), nullable=False)
    artifact_uri = Column(String(500), nullable=True)
    
    # Features
    features = Column(ARRAY(String), nullable=False)
    target_column = Column(String(100), nullable=True)
    
    # Performance Metrics
    metrics = Column(JSON, default={}, nullable=False)
    
    # Status
    status = Column(
        SQLEnum("training", "staging", "production", "archived", name="model_status_enum"),
        default="staging",
        nullable=False,
        index=True
    )
    
    # MLflow Integration
    mlflow_run_id = Column(String(255), nullable=True, index=True)
    mlflow_experiment_id = Column(String(255), nullable=True)
    
    # Deployment
    deployed_at = Column(DateTime, nullable=True)
    deployment_config = Column(JSON, default={}, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="model", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_model_name", "name"),
        Index("idx_model_status", "status"),
        Index("idx_model_name_version", "name", "version", unique=True),
    )
    
    def __repr__(self):
        return f"<MLModel(id={self.id}, name={self.name}, version={self.version}, status={self.status})>"


# ============================================================================
# PREDICTION MODEL
# ============================================================================

class Prediction(Base):
    """Prediction records and results."""
    
    __tablename__ = "predictions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign Keys
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Input/Output
    input_data = Column(JSON, nullable=False)
    output_data = Column(JSON, nullable=False)
    
    # Results
    prediction = Column(Text, nullable=True)  # Main prediction value
    confidence = Column(Float, nullable=True)
    probabilities = Column(JSON, nullable=True)
    
    # Performance
    execution_time_ms = Column(Float, nullable=True)
    
    # Feedback
    user_feedback_score = Column(Integer, nullable=True)  # 1-5 rating
    user_feedback_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    model = relationship("MLModel", back_populates="predictions")
    user = relationship("User", back_populates="predictions")
    feedbacks = relationship("Feedback", back_populates="prediction", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_prediction_model", "model_id"),
        Index("idx_prediction_user", "user_id"),
        Index("idx_prediction_created", "created_at"),
        CheckConstraint(
            "user_feedback_score IS NULL OR (user_feedback_score >= 1 AND user_feedback_score <= 5)",
            name="check_feedback_score"
        ),
    )
    
    def __repr__(self):
        return f"<Prediction(id={self.id}, model_id={self.model_id}, confidence={self.confidence})>"


# ============================================================================
# AGENT EXECUTION MODEL
# ============================================================================

class AgentExecution(Base):
    """Agent task execution logs."""
    
    __tablename__ = "agent_executions"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign Keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    
    # Task Details
    task = Column(Text, nullable=False)
    agent_type = Column(String(50), nullable=False, index=True)
    
    # Execution
    status = Column(
        SQLEnum("pending", "running", "completed", "failed", name="execution_status_enum"),
        default="pending",
        nullable=False,
        index=True
    )
    
    # Results
    input_data = Column(JSON, default={}, nullable=False)
    output_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Performance
    execution_time_seconds = Column(Float, nullable=True)
    
    # Orchestration
    is_orchestrated = Column(Boolean, default=False, nullable=False)
    parent_execution_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="agent_executions")
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_execution_user", "user_id"),
        Index("idx_agent_execution_status", "status"),
        Index("idx_agent_execution_type", "agent_type"),
        Index("idx_agent_execution_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<AgentExecution(id={self.id}, agent_type={self.agent_type}, status={self.status})>"


# ============================================================================
# FEEDBACK MODEL
# ============================================================================

class Feedback(Base):
    """User feedback on predictions."""
    
    __tablename__ = "feedbacks"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign Keys
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Feedback
    score = Column(Integer, nullable=False)  # 1-5 rating
    comment = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    
    # Metadata
    feedback_type = Column(String(50), default="user", nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    prediction = relationship("Prediction", back_populates="feedbacks")
    user = relationship("User", back_populates="feedbacks")
    
    # Indexes
    __table_args__ = (
        Index("idx_feedback_prediction", "prediction_id"),
        Index("idx_feedback_user", "user_id"),
        CheckConstraint("score >= 1 AND score <= 5", name="check_score"),
    )
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, prediction_id={self.prediction_id}, score={self.score})>"


# ============================================================================
# DATASET MODEL
# ============================================================================

class Dataset(Base):
    """Dataset metadata for data management."""
    
    __tablename__ = "datasets"
    
    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Identification
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    
    # Schema/Stats
    schema = Column(JSON, default={}, nullable=False)
    stats = Column(JSON, default={}, nullable=False)
    
    # Storage
    uri = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Dataset(id={self.id}, name={self.name})>"


# Export all models
__all__ = [
    "Base",
    "User",
    "Location",
    "MLModel",
    "Prediction",
    "AgentExecution",
    "Feedback",
    "Dataset"
]
