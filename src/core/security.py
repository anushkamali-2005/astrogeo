"""
Security Module
==============
Enterprise-grade security with:
- JWT token management
- Password hashing (bcrypt)
- API key validation
- Rate limiting
- CORS configuration
- Security headers

Author: Production Team
Version: 1.0.0
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings
from src.core.exceptions import (
    AuthenticationError,
    InvalidAPIKeyError,
    InvalidCredentialsError,
    InvalidTokenError,
    TokenExpiredError,
)

# ============================================================================
# PASSWORD HASHING
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password

    Example:
        >>> hashed = hash_password("mypassword")
    """
    return pwd_context.hash(password)  # type: ignore[no-any-return]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        bool: True if password matches

    Example:
        >>> is_valid = verify_password("mypassword", hashed)
    """
    return pwd_context.verify(plain_password, hashed_password)  # type: ignore[no-any-return]


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================


class JWTManager:
    """
    JWT token creation and validation.

    Features:
    - Access and refresh tokens
    - Token expiration
    - Custom claims
    - Signature verification
    """

    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create JWT access token.

        Args:
            data: Claims to encode
            expires_delta: Custom expiration time

        Returns:
            str: Encoded JWT token

        Example:
            >>> token = JWTManager.create_access_token({"sub": "user@example.com"})
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        return str(encoded_jwt)

    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Claims to encode
            expires_delta: Custom expiration time

        Returns:
            str: Encoded JWT token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        return str(encoded_jwt)

    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token
            token_type: Expected token type (access/refresh)

        Returns:
            Dict: Decoded token payload

        Raises:
            TokenExpiredError: If token has expired
            InvalidTokenError: If token is invalid
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

            # Verify token type
            if payload.get("type") != token_type:
                raise InvalidTokenError(details={"reason": f"Expected {token_type} token"})

            return payload  # type: ignore[no-any-return]

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError(details={"expired_at": datetime.utcnow().isoformat()})

        except JWTError as e:
            raise InvalidTokenError(details={"reason": str(e)})

    @staticmethod
    def decode_token_without_verification(token: str) -> Dict[str, Any]:
        """
        Decode token without verification (for inspection).

        Args:
            token: JWT token

        Returns:
            Dict: Decoded payload
        """
        try:
            return jwt.decode(token, options={"verify_signature": False}, algorithms=[settings.ALGORITHM])  # type: ignore[no-any-return]
        except JWTError:
            return {}


# Convenience alias for callers expecting a module-level helper.
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token (module-level helper).
    """
    return JWTManager.create_access_token(data, expires_delta=expires_delta)


# ============================================================================
# API KEY AUTHENTICATION
# ============================================================================

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


async def validate_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    Validate API key from header.

    Args:
        api_key: API key from request header

    Returns:
        str: Valid API key

    Raises:
        InvalidAPIKeyError: If API key is invalid

    Example:
        >>> from fastapi import Depends
        >>> @app.get("/protected")
        >>> async def protected(api_key: str = Depends(validate_api_key)):
        >>>     return {"message": "Authenticated"}
    """
    if not api_key:
        raise InvalidAPIKeyError(details={"reason": "API key not provided"})

    # Hash API key for comparison
    hashed_key = hashlib.sha256(api_key.encode()).hexdigest()

    # Check against allowed keys
    allowed_hashed_keys = [
        hashlib.sha256(key.encode()).hexdigest() for key in settings.ALLOWED_API_KEYS
    ]

    if hashed_key not in allowed_hashed_keys:
        raise InvalidAPIKeyError(details={"reason": "Invalid API key"})

    return api_key


# ============================================================================
# BEARER TOKEN AUTHENTICATION
# ============================================================================

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> Dict[str, Any]:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        Dict: User information from token

    Raises:
        AuthenticationError: If authentication fails

    Example:
        >>> @app.get("/me")
        >>> async def read_users_me(user: Dict = Depends(get_current_user)):
        >>>     return user
    """
    if not credentials:
        raise AuthenticationError(
            message="Missing authentication credentials",
            details={"reason": "No bearer token provided"},
        )

    token = credentials.credentials

    try:
        payload = JWTManager.verify_token(token, token_type="access")
        return payload

    except (TokenExpiredError, InvalidTokenError) as e:
        raise AuthenticationError(
            message="Invalid authentication credentials", details={"reason": str(e)}
        )


# ============================================================================
# API KEY GENERATOR
# ============================================================================


def generate_api_key(length: int = 32) -> str:
    """
    Generate secure random API key.

    Args:
        length: Key length in bytes

    Returns:
        str: Hex-encoded API key

    Example:
        >>> api_key = generate_api_key()
        >>> print(f"Your API key: {api_key}")
    """
    return secrets.token_hex(length)


def generate_secret_key(length: int = 32) -> str:
    """
    Generate secure random secret key.

    Args:
        length: Key length in bytes

    Returns:
        str: URL-safe base64-encoded key
    """
    return secrets.token_urlsafe(length)


# ============================================================================
# SECURITY HEADERS
# ============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'",
}


# ============================================================================
# RATE LIMITING (Simple in-memory implementation)
# ============================================================================

from collections import defaultdict
from time import time


class RateLimiter:
    """
    Simple in-memory rate limiter.

    For production, use Redis-based rate limiting.
    """

    def __init__(self):
        """Initialize rate limiter."""
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str, limit: int, window: int) -> bool:
        """
        Check if request is allowed.

        Args:
            identifier: Unique identifier (IP, user ID, API key)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            bool: True if request is allowed
        """
        now = time()
        cutoff = now - window

        # Remove old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier] if req_time > cutoff
        ]

        # Check limit
        if len(self.requests[identifier]) >= limit:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True

    def get_remaining(self, identifier: str, limit: int, window: int) -> int:
        """Get remaining requests in window."""
        now = time()
        cutoff = now - window

        # Count recent requests
        recent = sum(1 for req_time in self.requests.get(identifier, []) if req_time > cutoff)
        return max(0, limit - recent)


# Create global rate limiter instance
rate_limiter = RateLimiter()


# Export public API
__all__ = [
    "hash_password",
    "verify_password",
    "JWTManager",
    "create_access_token",
    "validate_api_key",
    "get_current_user",
    "generate_api_key",
    "generate_secret_key",
    "SECURITY_HEADERS",
    "RateLimiter",
    "rate_limiter",
]
