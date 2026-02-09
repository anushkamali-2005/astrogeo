"""
Sentry Error Tracking Integration
==================================
Production error tracking and performance monitoring.

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from src.core.config import settings
from src.core.logging import get_logger


logger = get_logger(__name__)


# ============================================================================
# SENTRY INITIALIZATION
# ============================================================================

def init_sentry() -> None:
    """
    Initialize Sentry SDK with production integrations.
    
    Features:
    - Error tracking and grouping
    - Performance monitoring
    - Release tracking
    - Environment tagging
    - User context capture
    """
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured, error tracking disabled")
        return
    
    try:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=f"astrogeo@{settings.VERSION}",
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                CeleryIntegration()
            ],
            
            # Performance monitoring
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
            
            # Error filtering
            before_send=before_send_filter,
            
            # Additional options
            send_default_pii=False,  # Don't send PII by default
            attach_stacktrace=True,
            max_breadcrumbs=50,
            debug=settings.DEBUG
        )
        
        logger.info(
            "Sentry initialized",
            extra={
                "environment": settings.ENVIRONMENT,
                "release": f"astrogeo@{settings.VERSION}"
            }
        )
    
    except Exception as e:
        logger.error("Failed to initialize Sentry", error=e)


# ============================================================================
# FILTERS AND HOOKS
# ============================================================================

def before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry.
    
    Args:
        event: Sentry event dictionary
        hint: Additional context
        
    Returns:
        Filtered event or None to drop
    """
    # Don't send 404 errors
    if event.get("exception"):
        exc_type = event["exception"]["values"][0].get("type", "")
        if exc_type == "RecordNotFoundError":
            return None
    
    # Don't send validation errors
    if event.get("exception"):
        exc_type = event["exception"]["values"][0].get("type", "")
        if exc_type == "ValidationError":
            return None
    
    # Filter out noisy errors in development
    if settings.ENVIRONMENT == "development":
        return None
    
    return event


# ============================================================================
# CONTEXT MANAGEMENT
# ============================================================================

def set_user_context(user_id: str, email: str, username: str) -> None:
    """
    Set user context for error tracking.
    
    Args:
        user_id: User ID
        email: User email
        username: Username
    """
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username
    })


def set_tags(**tags: str) -> None:
    """
    Set custom tags for error grouping.
    
    Args:
        **tags: Key-value pairs for tags
    """
    for key, value in tags.items():
        sentry_sdk.set_tag(key, value)


def set_context(name: str, context: Dict[str, Any]) -> None:
    """
    Set custom context data.
    
    Args:
        name: Context section name
        context: Context data dictionary
    """
    sentry_sdk.set_context(name, context)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add breadcrumb for event trail.
    
    Args:
        message: Breadcrumb message
        category: Breadcrumb category
        level: Severity level
        data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


# ============================================================================
# ERROR CAPTURE
# ============================================================================

def capture_exception(exception: Exception, **extra: Any) -> str:
    """
    Manually capture exception.
    
    Args:
        exception: Exception to capture
        **extra: Additional context
        
    Returns:
        str: Sentry event ID
    """
    if extra:
        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            event_id = sentry_sdk.capture_exception(exception)
    else:
        event_id = sentry_sdk.capture_exception(exception)
    
    logger.error(
        "Exception captured by Sentry",
        extra={"sentry_event_id": event_id}
    )
    
    return event_id


def capture_message(
    message: str,
    level: str = "info",
    **extra: Any
) -> str:
    """
    Capture custom message.
    
    Args:
        message: Message to capture
        level: Severity level
        **extra: Additional context
        
    Returns:
        str: Sentry event ID
    """
    if extra:
        with sentry_sdk.push_scope() as scope:
            for key, value in extra.items():
                scope.set_extra(key, value)
            event_id = sentry_sdk.capture_message(message, level)
    else:
        event_id = sentry_sdk.capture_message(message, level)
    
    return event_id


# Export
__all__ = [
    "init_sentry",
    "set_user_context",
    "set_tags",
    "set_context",
    "add_breadcrumb",
    "capture_exception",
    "capture_message"
]
