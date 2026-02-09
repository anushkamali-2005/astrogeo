"""
Authentication Routes
====================
JWT-based authentication endpoints:
- User registration
- Login and logout
- Token refresh
- Password management
- Profile operations

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field, validator

from src.core.config import settings
from src.core.logging import get_logger
from src.core.security import (
    hash_password,
    verify_password,
    JWTManager,
    rate_limiter
)
from src.core.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    DuplicateRecordError,
    RecordNotFoundError,
    ValidationError,
    RateLimitExceededError
)
from src.database.connection import get_db
from src.database.repositories import UserRepository


logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
bearer_scheme = HTTPBearer()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class UserRegisterRequest(BaseModel):
    """User registration request."""
    email: EmailStr = Field(..., description="User email address")
    username: str = Field(..., min_length=3, max_length=50, description="Username")
    password: str = Field(..., min_length=8, max_length=128, description="Password")
    full_name: str | None = Field(None, max_length=255, description="Full name")
    
    @validator("username")
    def validate_username(cls, v):
        """Validate username format."""
        if not v.isalnum() and "_" not in v:
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v.lower()
    
    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLoginRequest(BaseModel):
    """User login request."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Password")


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str = Field(..., description="Access token")
    refresh_token: str = Field(..., description="Refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")


class UserProfileResponse(BaseModel):
    """User profile response."""
    id: UUID
    email: str
    username: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    role: str
    created_at: datetime
    last_login: datetime | None
    
    class Config:
        from_attributes = True


class UserProfileUpdateRequest(BaseModel):
    """User profile update request."""
    full_name: str | None = Field(None, max_length=255)
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    """Change password request."""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class ForgotPasswordRequest(BaseModel):
    """Forgot password request."""
    email: EmailStr = Field(..., description="User email")


class ResetPasswordRequest(BaseModel):
    """Reset password request."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    
    @validator("new_password")
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get current user from JWT access token.
    
    Args:
        credentials: Bearer token credentials
        db: Database session
        
    Returns:
        dict: User information
        
    Raises:
        AuthenticationError: If authentication fails
    """
    if not credentials:
        raise AuthenticationError(
            message="Missing authentication credentials",
            details={"reason": "No bearer token provided"}
        )
    
    try:
        # Verify token
        payload = JWTManager.verify_token(credentials.credentials, token_type="access")
        
        # Get user from database
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="Invalid token payload")
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(user_id))
        
        if not user:
            raise AuthenticationError(message="User not found")
        
        if not user.is_active:
            raise AuthenticationError(message="User account is disabled")
        
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "is_superuser": user.is_superuser
        }
    
    except Exception as e:
        logger.error("Token verification failed", error=e)
        raise AuthenticationError(
            message="Invalid authentication credentials",
            details={"error": str(e)}
        )


def check_rate_limit(request: Request, max_requests: int, window_seconds: int) -> None:
    """
    Check rate limit for endpoint.
    
    Args:
        request: FastAPI request
        max_requests: Maximum requests allowed
        window_seconds: Time window in seconds
        
    Raises:
        RateLimitExceededError: If rate limit exceeded
    """
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    client_ip = request.client.host if request.client else "unknown"
    
    if not rate_limiter.is_allowed(client_ip, max_requests, window_seconds):
        remaining = rate_limiter.get_remaining(client_ip, max_requests, window_seconds)
        raise RateLimitExceededError(
            limit=max_requests,
            window=f"{window_seconds}s",
            details={"remaining": remaining}
        )


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@router.post("/register", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    """
    Register new user account.
    
    Rate limit: 5 requests per minute per IP.
    
    Args:
        data: Registration data
        request: HTTP request (for rate limiting)
        db: Database session
        
    Returns:
        UserProfileResponse: Created user profile
        
    Raises:
        RateLimitExceededError: If rate limit exceeded
        DuplicateRecordError: If email or username already exists
    """
    # Check rate limit
    check_rate_limit(request, max_requests=5, window_seconds=60)
    
    logger.info("User registration attempt", extra={"email": data.email})
    
    user_repo = UserRepository(db)
    
    # Check if email exists
    existing_email = await user_repo.get_by_email(data.email)
    if existing_email:
        raise DuplicateRecordError(
            resource="User",
            details={"field": "email", "value": data.email}
        )
    
    # Check if username exists
    existing_username = await user_repo.get_by_username(data.username)
    if existing_username:
        raise DuplicateRecordError(
            resource="User",
            details={"field": "username", "value": data.username}
        )
    
    # Hash password
    hashed_password = hash_password(data.password)
    
    # Create user
    user = await user_repo.create(
        email=data.email,
        username=data.username,
        hashed_password=hashed_password,
        full_name=data.full_name,
        is_active=True,
        is_superuser=False,
        role="user"
    )
    
    logger.info(
        "User registered successfully",
        extra={"user_id": str(user.id), "email": user.email}
    )
    
    return UserProfileResponse.from_orm(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Login and get JWT tokens.
    
    Rate limit: 5 requests per minute per IP.
    
    Args:
        data: Login credentials
        request: HTTP request (for rate limiting)
        db: Database session
        
    Returns:
        TokenResponse: Access and refresh tokens
        
    Raises:
        RateLimitExceededError: If rate limit exceeded
        InvalidCredentialsError: If credentials are invalid
    """
    # Check rate limit
    check_rate_limit(request, max_requests=5, window_seconds=60)
    
    logger.info("Login attempt", extra={"email": data.email})
    
    user_repo = UserRepository(db)
    
    # Get user by email
    user = await user_repo.get_by_email(data.email)
    if not user:
        raise InvalidCredentialsError(details={"reason": "User not found"})
    
    # Verify password
    if not verify_password(data.password, user.hashed_password):
        logger.warning("Invalid password attempt", extra={"email": data.email})
        raise InvalidCredentialsError(details={"reason": "Invalid password"})
    
    # Check if user is active
    if not user.is_active:
        raise InvalidCredentialsError(details={"reason": "Account is disabled"})
    
    # Update last login
    await user_repo.update(user.id, last_login=datetime.utcnow())
    
    # Create tokens
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "username": user.username,
        "role": user.role
    }
    
    access_token = JWTManager.create_access_token(data=token_data)
    refresh_token = JWTManager.create_refresh_token(data=token_data)
    
    logger.info("Login successful", extra={"user_id": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.
    
    Args:
        credentials: Bearer refresh token
        db: Database session
        
    Returns:
        TokenResponse: New access and refresh tokens
        
    Raises:
        AuthenticationError: If refresh token is invalid
    """
    if not credentials:
        raise AuthenticationError(message="Missing refresh token")
    
    try:
        # Verify refresh token
        payload = JWTManager.verify_token(credentials.credentials, token_type="refresh")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="Invalid token payload")
        
        # Get user
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(user_id))
        
        if not user or not user.is_active:
            raise AuthenticationError(message="User not found or inactive")
        
        # Create new tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role
        }
        
        access_token = JWTManager.create_access_token(data=token_data)
        refresh_token = JWTManager.create_refresh_token(data=token_data)
        
        logger.info("Token refreshed", extra={"user_id": str(user.id)})
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    except Exception as e:
        logger.error("Token refresh failed", error=e)
        raise AuthenticationError(
            message="Invalid refresh token",
            details={"error": str(e)}
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token)
) -> None:
    """
    Logout user (invalidate token client-side).
    
    Note: JWT tokens are stateless. Actual invalidation happens client-side.
    For production, consider using Redis token blacklist.
    
    Args:
        current_user: Current authenticated user
    """
    logger.info("User logged out", extra={"user_id": str(current_user["id"])})
    # In a full implementation, add token to blacklist in Redis
    return None


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    """
    Get current user profile.
    
    Args:
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserProfileResponse: User profile
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(current_user["id"]))
    
    if not user:
        raise RecordNotFoundError("User", current_user["id"])
    
    return UserProfileResponse.from_orm(user)


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    data: UserProfileUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> UserProfileResponse:
    """
    Update current user profile.
    
    Args:
        data: Profile update data
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserProfileResponse: Updated user profile
    """
    user_repo = UserRepository(db)
    
    # Prepare update data
    update_data = {}
    if data.full_name is not None:
        update_data["full_name"] = data.full_name
    if data.email is not None:
        # Check if email already exists
        existing = await user_repo.get_by_email(data.email)
        if existing and str(existing.id) != current_user["id"]:
            raise DuplicateRecordError(
                resource="User",
                details={"field": "email", "value": data.email}
            )
        update_data["email"] = data.email
    
    # Update user
    user = await user_repo.update(UUID(current_user["id"]), **update_data)
    
    if not user:
        raise RecordNotFoundError("User", current_user["id"])
    
    logger.info("Profile updated", extra={"user_id": str(user.id)})
    
    return UserProfileResponse.from_orm(user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    data: ChangePasswordRequest,
    current_user: Dict[str, Any] = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Change user password.
    
    Args:
        data: Password change data
        current_user: Current authenticated user
        db: Database session
        
    Raises:
        InvalidCredentialsError: If current password is incorrect
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(UUID(current_user["id"]))
    
    if not user:
        raise RecordNotFoundError("User", current_user["id"])
    
    # Verify current password
    if not verify_password(data.current_password, user.hashed_password):
        raise InvalidCredentialsError(details={"reason": "Current password is incorrect"})
    
    # Hash new password
    new_hashed = hash_password(data.new_password)
    
    # Update password
    await user_repo.update(user.id, hashed_password=new_hashed)
    
    logger.info("Password changed", extra={"user_id": str(user.id)})


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Initiate password reset process.
    
    Rate limit: 3 requests per 5 minutes per IP.
    
    Args:
        data: Forgot password data
        request: HTTP request (for rate limiting)
        db: Database session
        
    Returns:
        dict: Success message
        
    Note: In production, send email with reset link instead of returning token.
    """
    # Check rate limit
    check_rate_limit(request, max_requests=3, window_seconds=300)
    
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(data.email)
    
    # Don't reveal if user exists (security best practice)
    if not user:
        logger.warning("Password reset for non-existent user", extra={"email": data.email})
        return {"message": "If the email exists, a reset link has been sent"}
    
    # Create reset token (valid for 1 hour)
    reset_token = JWTManager.create_access_token(
        data={"sub": str(user.id), "purpose": "password_reset"},
        expires_delta=timedelta(hours=1)
    )
    
    # TODO: In production, send email with reset link
    # await email_service.send_password_reset_email(user.email, reset_token)
    
    logger.info("Password reset requested", extra={"user_id": str(user.id)})
    
    # For development, return token (REMOVE IN PRODUCTION)
    if settings.ENVIRONMENT == "development":
        return {
            "message": "Password reset token generated (DEV ONLY)",
            "reset_token": reset_token
        }
    
    return {"message": "If the email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
) -> None:
    """
    Reset password using reset token.
    
    Args:
        data: Reset password data
        db: Database session
        
    Raises:
        AuthenticationError: If reset token is invalid
    """
    try:
        # Verify reset token
        payload = JWTManager.verify_token(data.token, token_type="access")
        
        # Check purpose
        if payload.get("purpose") != "password_reset":
            raise AuthenticationError(message="Invalid reset token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError(message="Invalid token payload")
        
        # Update password
        user_repo = UserRepository(db)
        user = await user_repo.get_by_id(UUID(user_id))
        
        if not user:
            raise RecordNotFoundError("User", user_id)
        
        new_hashed = hash_password(data.new_password)
        await user_repo.update(user.id, hashed_password=new_hashed)
        
        logger.info("Password reset successful", extra={"user_id": str(user.id)})
    
    except Exception as e:
        logger.error("Password reset failed", error=e)
        raise AuthenticationError(
            message="Invalid or expired reset token",
            details={"error": str(e)}
        )


# Export router
__all__ = ["router"]
