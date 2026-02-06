"""
Core Configuration Module
=======================
Enterprise-grade configuration management with:
- Environment-based settings
- Pydantic validation
- Singleton pattern
- Type safety
- Secret management

Author: Production Team
Version: 1.0.0
"""

import os
from functools import lru_cache
from typing import List, Optional, Dict, Any
from pathlib import Path

from pydantic import (
    BaseSettings,
    Field,
    PostgresDsn,
    validator,
    AnyHttpUrl
)
from pydantic.networks import RedisDsn


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Features:
    - Type validation
    - Environment variable loading
    - Default values
    - Secret management
    - Multi-environment support
    """
    
    # ============================================================================
    # APPLICATION SETTINGS
    # ============================================================================
    APP_NAME: str = Field(default="AstroGeo AI MLOps", env="APP_NAME")
    APP_VERSION: str = Field(default="1.0.0", env="APP_VERSION")
    APP_DESCRIPTION: str = Field(
        default="Enterprise MLOps Platform with Agentic AI",
        env="APP_DESCRIPTION"
    )
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # API Configuration
    API_V1_PREFIX: str = Field(default="/api/v1", env="API_V1_PREFIX")
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=4, env="API_WORKERS")
    
    # CORS Settings
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"], env="CORS_ALLOW_METHODS")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # ============================================================================
    # SECURITY SETTINGS
    # ============================================================================
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    
    # API Key Management
    API_KEY_HEADER: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    ALLOWED_API_KEYS: List[str] = Field(default=[], env="ALLOWED_API_KEYS")
    
    # ============================================================================
    # DATABASE SETTINGS (PostgreSQL + PostGIS)
    # ============================================================================
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_HOST: str = Field(default="localhost", env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    POSTGRES_SCHEMA: str = Field(default="public", env="POSTGRES_SCHEMA")
    
    # Database Connection Pool
    DB_POOL_SIZE: int = Field(default=20, env="DB_POOL_SIZE")
    DB_MAX_OVERFLOW: int = Field(default=10, env="DB_MAX_OVERFLOW")
    DB_POOL_TIMEOUT: int = Field(default=30, env="DB_POOL_TIMEOUT")
    DB_POOL_RECYCLE: int = Field(default=3600, env="DB_POOL_RECYCLE")
    
    # Database URL (auto-generated)
    DATABASE_URL: Optional[PostgresDsn] = None
    
    @validator("DATABASE_URL", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """Construct PostgreSQL connection URL."""
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=str(values.get("POSTGRES_PORT")),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )
    
    # ============================================================================
    # REDIS SETTINGS (Caching & Task Queue)
    # ============================================================================
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_DB: int = Field(default=0, env="REDIS_DB")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    REDIS_URL: Optional[RedisDsn] = None
    
    # Cache Settings
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    CACHE_PREFIX: str = Field(default="astrogeo:", env="CACHE_PREFIX")
    
    @validator("REDIS_URL", pre=True)
    def assemble_redis_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """Construct Redis connection URL."""
        if isinstance(v, str):
            return v
        
        password = values.get("REDIS_PASSWORD")
        auth = f":{password}@" if password else ""
        
        return (
            f"redis://{auth}{values.get('REDIS_HOST')}:"
            f"{values.get('REDIS_PORT')}/{values.get('REDIS_DB')}"
        )
    
    # ============================================================================
    # MLFLOW SETTINGS
    # ============================================================================
    MLFLOW_TRACKING_URI: str = Field(..., env="MLFLOW_TRACKING_URI")
    MLFLOW_EXPERIMENT_NAME: str = Field(
        default="astrogeo-experiments",
        env="MLFLOW_EXPERIMENT_NAME"
    )
    MLFLOW_REGISTRY_URI: Optional[str] = Field(default=None, env="MLFLOW_REGISTRY_URI")
    MLFLOW_ARTIFACT_ROOT: str = Field(
        default="s3://mlflow-artifacts",
        env="MLFLOW_ARTIFACT_ROOT"
    )
    
    # DagsHub Integration
    DAGSHUB_USERNAME: Optional[str] = Field(default=None, env="DAGSHUB_USERNAME")
    DAGSHUB_TOKEN: Optional[str] = Field(default=None, env="DAGSHUB_TOKEN")
    DAGSHUB_REPO: Optional[str] = Field(default=None, env="DAGSHUB_REPO")
    
    # ============================================================================
    # AWS SETTINGS
    # ============================================================================
    AWS_ACCESS_KEY_ID: Optional[str] = Field(default=None, env="AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = Field(default=None, env="AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = Field(default="us-east-1", env="AWS_REGION")
    AWS_S3_BUCKET: Optional[str] = Field(default=None, env="AWS_S3_BUCKET")
    
    # ECR Settings
    ECR_REPOSITORY: Optional[str] = Field(default=None, env="ECR_REPOSITORY")
    AWS_ACCOUNT_ID: Optional[str] = Field(default=None, env="AWS_ACCOUNT_ID")
    
    # EKS Settings
    EKS_CLUSTER_NAME: Optional[str] = Field(default=None, env="EKS_CLUSTER_NAME")
    EKS_NAMESPACE: str = Field(default="astrogeo", env="EKS_NAMESPACE")
    
    # ============================================================================
    # LANGCHAIN / AGENTIC AI SETTINGS
    # ============================================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    
    # Agent Configuration
    AGENT_MODEL: str = Field(default="gpt-4", env="AGENT_MODEL")
    AGENT_TEMPERATURE: float = Field(default=0.7, env="AGENT_TEMPERATURE")
    AGENT_MAX_TOKENS: int = Field(default=2000, env="AGENT_MAX_TOKENS")
    AGENT_MAX_ITERATIONS: int = Field(default=10, env="AGENT_MAX_ITERATIONS")
    
    # Vector Store (for RAG)
    VECTOR_STORE_TYPE: str = Field(default="faiss", env="VECTOR_STORE_TYPE")
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        env="EMBEDDING_MODEL"
    )
    
    # ============================================================================
    # MONITORING & LOGGING
    # ============================================================================
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="json", env="LOG_FORMAT")  # json or text
    LOG_FILE: Optional[str] = Field(default="logs/app.log", env="LOG_FILE")
    
    # Prometheus Metrics
    METRICS_ENABLED: bool = Field(default=True, env="METRICS_ENABLED")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")
    
    # Sentry Integration
    SENTRY_DSN: Optional[str] = Field(default=None, env="SENTRY_DSN")
    SENTRY_ENVIRONMENT: Optional[str] = Field(default=None, env="SENTRY_ENVIRONMENT")
    
    # ============================================================================
    # DATA VERSIONING (DVC)
    # ============================================================================
    DVC_REMOTE: str = Field(default="s3://dvc-storage", env="DVC_REMOTE")
    DVC_CACHE_DIR: str = Field(default=".dvc/cache", env="DVC_CACHE_DIR")
    
    # ============================================================================
    # MODEL SERVING
    # ============================================================================
    MODEL_REGISTRY_PATH: str = Field(
        default="models/production",
        env="MODEL_REGISTRY_PATH"
    )
    MODEL_STAGING_PATH: str = Field(
        default="models/staging",
        env="MODEL_STAGING_PATH"
    )
    
    # Prediction Settings
    BATCH_SIZE: int = Field(default=32, env="BATCH_SIZE")
    MAX_PREDICTION_TIMEOUT: int = Field(default=60, env="MAX_PREDICTION_TIMEOUT")
    
    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    RATE_LIMIT_PER_MINUTE: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    RATE_LIMIT_PER_HOUR: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # ============================================================================
    # PROJECT PATHS
    # ============================================================================
    @property
    def BASE_DIR(self) -> Path:
        """Get project base directory."""
        return Path(__file__).resolve().parent.parent.parent
    
    @property
    def DATA_DIR(self) -> Path:
        """Get data directory."""
        return self.BASE_DIR / "data"
    
    @property
    def MODELS_DIR(self) -> Path:
        """Get models directory."""
        return self.BASE_DIR / "models"
    
    @property
    def LOGS_DIR(self) -> Path:
        """Get logs directory."""
        logs_dir = self.BASE_DIR / "logs"
        logs_dir.mkdir(exist_ok=True)
        return logs_dir
    
    # ============================================================================
    # VALIDATION METHODS
    # ============================================================================
    @validator("ENVIRONMENT")
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed_envs = ["development", "staging", "production", "testing"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of {allowed_envs}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v
    
    # ============================================================================
    # CONFIGURATION
    # ============================================================================
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        # Allow arbitrary types
        arbitrary_types_allowed = True
        
        # Validation
        validate_assignment = True
        
        # JSON schema
        schema_extra = {
            "example": {
                "APP_NAME": "AstroGeo AI MLOps",
                "ENVIRONMENT": "production",
                "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db",
            }
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (Singleton pattern).
    
    Returns:
        Settings: Application settings
        
    Example:
        >>> from src.core.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.APP_NAME)
    """
    return Settings()


# Create global settings instance
settings = get_settings()


# Export public API
__all__ = ["Settings", "get_settings", "settings"]