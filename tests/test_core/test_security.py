"""
Test Security Module
====================
Unit tests for security utilities.

Author: Production Team
Version: 1.0.0
"""

import pytest
from datetime import datetime, timedelta

from src.core.security import (
    hash_password,
    verify_password,
    JWTManager,
    RateLimiter
)


class TestPasswordHashing:
    """Test password hashing functions."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestJWTManager:
    """Test JWT token management."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"user_id": "123"}
        token = JWTManager.create_refresh_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_verify_valid_token(self):
        """Test token verification with valid token."""
        data = {"user_id": "123", "email": "test@example.com"}
        token = JWTManager.create_access_token(data)
        
        payload = JWTManager.verify_token(token)
        
        assert payload is not None
        assert payload["user_id"] == "123"
        assert payload["email"] == "test@example.com"
    
    def test_verify_expired_token(self):
        """Test token verification with expired token."""
        data = {"user_id": "123"}
        # Create token that expires immediately
        token = JWTManager.create_access_token(
            data,
            expires_delta=timedelta(seconds=-1)
        )
        
        payload = JWTManager.verify_token(token)
        assert payload is None
    
    def test_verify_invalid_token(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.token.here"
        
        payload = JWTManager.verify_token(invalid_token)
        assert payload is None


class TestRateLimiter:
    """Test rate limiting functionality."""
    
    def test_rate_limit_allowed(self):
        """Test rate limit allows initial requests."""
        limiter = RateLimiter()
        key = "test_user_1"
        
        # First request should be allowed
        assert limiter.is_allowed(key, max_requests=5, window_seconds=60) is True
    
    def test_rate_limit_exceeded(self):
        """Test rate limit blocks excessive requests."""
        limiter = RateLimiter()
        key = "test_user_2"
        
        # Make max_requests
        for _ in range(3):
            limiter.is_allowed(key, max_requests=3, window_seconds=60)
        
        # Next request should be blocked
        assert limiter.is_allowed(key, max_requests=3, window_seconds=60) is False
    
    def test_rate_limit_reset(self):
        """Test rate limit resets after window."""
        limiter = RateLimiter()
        key = "test_user_3"
        
        # Use up quota with short window
        for _ in range(2):
            limiter.is_allowed(key, max_requests=2, window_seconds=1)
        
        # Should be blocked
        assert limiter.is_allowed(key, max_requests=2, window_seconds=1) is False
        
        # Wait for window to expire
        import time
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed(key, max_requests=2, window_seconds=1) is True
