"""
Custom Exceptions Module
=======================
Enterprise-grade exception handling with:
- Custom exception hierarchy
- Error codes and messages
- HTTP status code mapping
- Detailed error context
- Logging integration

Author: Production Team
Version: 1.0.0
"""

from typing import Any, Dict, Optional
from fastapi import status


class BaseAPIException(Exception):
    """
    Base exception class for all API errors.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        status_code: HTTP status code
        details: Additional error context
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize base exception.
        
        Args:
            message: Error message
            error_code: Error code (e.g., "ERR_001")
            status_code: HTTP status code
            details: Additional context
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response."""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


# ============================================================================
# AUTHENTICATION & AUTHORIZATION EXCEPTIONS
# ============================================================================

class AuthenticationError(BaseAPIException):
    """Authentication failed."""
    
    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTH_001",
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Invalid credentials provided",
            details=details
        )
        self.error_code = "AUTH_002"


class TokenExpiredError(AuthenticationError):
    """Access token has expired."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Access token has expired",
            details=details
        )
        self.error_code = "AUTH_003"


class InvalidTokenError(AuthenticationError):
    """Invalid or malformed token."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Invalid or malformed token",
            details=details
        )
        self.error_code = "AUTH_004"


class AuthorizationError(BaseAPIException):
    """Insufficient permissions."""
    
    def __init__(
        self,
        message: str = "Insufficient permissions",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHZ_001",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class InvalidAPIKeyError(AuthenticationError):
    """Invalid API key."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Invalid API key",
            details=details
        )
        self.error_code = "AUTH_005"


# ============================================================================
# DATABASE EXCEPTIONS
# ============================================================================

class DatabaseError(BaseAPIException):
    """Database operation failed."""
    
    def __init__(
        self,
        message: str = "Database operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="DB_001",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class RecordNotFoundError(DatabaseError):
    """Requested record not found."""
    
    def __init__(
        self,
        resource: str,
        resource_id: Any,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            "resource": resource,
            "resource_id": str(resource_id)
        })
        super().__init__(
            message=f"{resource} with ID {resource_id} not found",
            details=details
        )
        self.error_code = "DB_002"
        self.status_code = status.HTTP_404_NOT_FOUND


class DuplicateRecordError(DatabaseError):
    """Record already exists."""
    
    def __init__(
        self,
        resource: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"{resource} already exists",
            details=details
        )
        self.error_code = "DB_003"
        self.status_code = status.HTTP_409_CONFLICT


class DatabaseConnectionError(DatabaseError):
    """Database connection failed."""
    
    def __init__(self, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message="Failed to connect to database",
            details=details
        )
        self.error_code = "DB_004"


class IntegrityError(DatabaseError):
    """Database integrity constraint violated."""
    
    def __init__(
        self,
        message: str = "Database integrity constraint violated",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "DB_005"
        self.status_code = status.HTTP_400_BAD_REQUEST


# ============================================================================
# VALIDATION EXCEPTIONS
# ============================================================================

class ValidationError(BaseAPIException):
    """Input validation failed."""
    
    def __init__(
        self,
        message: str = "Input validation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VAL_001",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details
        )


class InvalidInputError(ValidationError):
    """Invalid input data."""
    
    def __init__(
        self,
        field: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            "field": field,
            "reason": reason
        })
        super().__init__(
            message=f"Invalid input for field '{field}': {reason}",
            details=details
        )
        self.error_code = "VAL_002"


class MissingFieldError(ValidationError):
    """Required field is missing."""
    
    def __init__(
        self,
        field: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Required field '{field}' is missing",
            details=details
        )
        self.error_code = "VAL_003"


# ============================================================================
# ML/MODEL EXCEPTIONS
# ============================================================================

class ModelError(BaseAPIException):
    """Model operation failed."""
    
    def __init__(
        self,
        message: str = "Model operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="ML_001",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class ModelNotFoundError(ModelError):
    """ML model not found."""
    
    def __init__(
        self,
        model_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Model '{model_name}' not found",
            details=details
        )
        self.error_code = "ML_002"
        self.status_code = status.HTTP_404_NOT_FOUND


class ModelLoadError(ModelError):
    """Failed to load ML model."""
    
    def __init__(
        self,
        model_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Failed to load model '{model_name}'",
            details=details
        )
        self.error_code = "ML_003"


class PredictionError(ModelError):
    """Model prediction failed."""
    
    def __init__(
        self,
        message: str = "Model prediction failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "ML_004"


class ModelTrainingError(ModelError):
    """Model training failed."""
    
    def __init__(
        self,
        message: str = "Model training failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "ML_005"


class FeatureEngineeringError(ModelError):
    """Feature engineering failed."""
    
    def __init__(
        self,
        message: str = "Feature engineering failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "ML_006"


# ============================================================================
# AGENT EXCEPTIONS
# ============================================================================

class AgentError(BaseAPIException):
    """Agent operation failed."""
    
    def __init__(
        self,
        message: str = "Agent operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AGENT_001",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class AgentExecutionError(AgentError):
    """Agent execution failed."""
    
    def __init__(
        self,
        agent_name: str,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=f"Agent '{agent_name}' execution failed",
            details=details
        )
        self.error_code = "AGENT_002"


class AgentTimeoutError(AgentError):
    """Agent execution timeout."""
    
    def __init__(
        self,
        agent_name: str,
        timeout: int,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["timeout_seconds"] = timeout
        super().__init__(
            message=f"Agent '{agent_name}' execution timed out after {timeout}s",
            details=details
        )
        self.error_code = "AGENT_003"


# ============================================================================
# DATA PROCESSING EXCEPTIONS
# ============================================================================

class DataProcessingError(BaseAPIException):
    """Data processing operation failed."""
    
    def __init__(
        self,
        message: str = "Data processing failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="DATA_001",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class DataIngestionError(DataProcessingError):
    """Data ingestion failed."""
    
    def __init__(
        self,
        message: str = "Data ingestion failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "DATA_002"


class DataValidationError(DataProcessingError):
    """Data validation failed."""
    
    def __init__(
        self,
        message: str = "Data validation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message=message, details=details)
        self.error_code = "DATA_003"


# ============================================================================
# RATE LIMITING EXCEPTIONS
# ============================================================================

class RateLimitExceededError(BaseAPIException):
    """Rate limit exceeded."""
    
    def __init__(
        self,
        limit: int,
        window: str,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details.update({
            "limit": limit,
            "window": window
        })
        super().__init__(
            message=f"Rate limit of {limit} requests per {window} exceeded",
            error_code="RATE_001",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details
        )


# ============================================================================
# EXTERNAL SERVICE EXCEPTIONS
# ============================================================================

class ExternalServiceError(BaseAPIException):
    """External service call failed."""
    
    def __init__(
        self,
        service_name: str,
        message: str = "External service call failed",
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        details["service"] = service_name
        super().__init__(
            message=message,
            error_code="EXT_001",
            status_code=status.HTTP_502_BAD_GATEWAY,
            details=details
        )


class MLflowError(ExternalServiceError):
    """MLflow operation failed."""
    
    def __init__(
        self,
        message: str = "MLflow operation failed",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            service_name="MLflow",
            message=message,
            details=details
        )
        self.error_code = "EXT_002"


# ============================================================================
# SERVICE AVAILABILITY EXCEPTIONS
# ============================================================================

class ServiceUnavailableError(BaseAPIException):
    """Critical service unavailable."""
    
    def __init__(
        self,
        message: str = "Service unavailable",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="SVC_001",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details
        )


# Export public API
__all__ = [
    "BaseAPIException",
    "AuthenticationError",
    "InvalidCredentialsError",
    "TokenExpiredError",
    "InvalidTokenError",
    "AuthorizationError",
    "InvalidAPIKeyError",
    "DatabaseError",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "DatabaseConnectionError",
    "IntegrityError",
    "ValidationError",
    "InvalidInputError",
    "MissingFieldError",
    "ModelError",
    "ModelNotFoundError",
    "ModelLoadError",
    "PredictionError",
    "ModelTrainingError",
    "FeatureEngineeringError",
    "AgentError",
    "AgentExecutionError",
    "AgentTimeoutError",
    "DataProcessingError",
    "DataIngestionError",
    "DataValidationError",
    "RateLimitExceededError",
    "ExternalServiceError",
    "MLflowError",
    "ServiceUnavailableError"
]
