"""
Test Core Configuration
========================
Unit tests for application configuration.

Author: Production Team
Version: 1.0.0
"""

import pytest
from unittest.mock import patch
import os

from src.core.config import Settings


class TestSettings:
    """Test Settings configuration class."""
    
    def test_default_settings(self):
        """Test default configuration values."""
        settings = Settings()
        
        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True
        assert settings.LOG_LEVEL == "INFO"
    
    @patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "DEBUG": "false",
        "LOG_LEVEL": "WARNING"
    })
    def test_environment_overrides(self):
        """Test environment variable overrides."""
        settings = Settings()
        
        assert settings.ENVIRONMENT == "production"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "WARNING"
    
    @patch.dict(os.environ, {
        "POSTGRES_USER": "test_user",
        "POSTGRES_PASSWORD": "test_pass",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "test_db"
    })
    def test_database_url_construction(self):
        """Test database URL construction."""
        settings = Settings()
        
        expected_url = "postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db"
        assert settings.DATABASE_URL == expected_url
    
    @patch.dict(os.environ, {
        "REDIS_HOST": "redis-server",
        "REDIS_PORT": "6380"
    })
    def test_redis_configuration(self):
        """Test Redis configuration."""
        settings = Settings()
        
        assert settings.REDIS_HOST == "redis-server"
        assert settings.REDIS_PORT == 6380
    
    def test_jwt_settings(self):
        """Test JWT token settings."""
        settings = Settings()
        
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS > 0
        assert len(settings.SECRET_KEY) > 0
    
    def test_mlflow_settings(self):
        """Test MLflow configuration."""
        settings = Settings()
        
        assert settings.MLFLOW_TRACKING_URI is not None
        assert isinstance(settings.MLFLOW_TRACKING_URI, str)
