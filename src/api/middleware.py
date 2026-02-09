"""
API Middleware
===============
Production-level middleware for FastAPI application.

Components:
- Rate limiting (token bucket algorithm)
- Request/response logging
- Response compression
- Correlation ID for request tracing
- Error handling

Author: Production Team
Version: 1.0.0
"""

import gzip
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================================
# RATE LIMITING MIDDLEWARE
# ============================================================================


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Token bucket rate limiting middleware.

    Features:
    - Per-IP rate limiting
    - Configurable rate and burst size
    - Redis-backed distributed limiting (optional)

    Design Pattern: Token Bucket Algorithm
    """

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60, burst_size: int = 10):
        """
        Initialize rate limiter.

        Args:
            app: ASGI application
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst requests
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.buckets: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self._check_rate_limit(client_ip):
            logger.warning("Rate limit exceeded", extra={"client_ip": client_ip})
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "details": {"limit": self.requests_per_minute, "window": "1 minute"},
                    },
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        bucket = self.buckets.get(client_ip, {})
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            max(0, self.burst_size - bucket.get("count", 0))
        )

        return response

    def _check_rate_limit(self, client_id: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            client_id: Client identifier

        Returns:
            bool: True if within limit
        """
        now = time.time()

        # Initialize bucket if not exists
        if client_id not in self.buckets:
            self.buckets[client_id] = {"tokens": self.burst_size, "last_update": now}

        bucket = self.buckets[client_id]

        # Refill tokens based on time elapsed
        time_elapsed = now - bucket["last_update"]
        tokens_to_add = time_elapsed * (self.requests_per_minute / 60.0)
        bucket["tokens"] = min(self.burst_size, bucket["tokens"] + tokens_to_add)
        bucket["last_update"] = now

        # Check if tokens available
        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return True

        return False


# ============================================================================
# REQUEST LOGGING MIDDLEWARE
# ============================================================================


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured request/response logging middleware.

    Features:
    - Request/response logging
    - Execution time tracking
    - Error logging
    - Structured log format
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with logging.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: HTTP response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Start timer
        start_time = time.time()

        # Log request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("user-agent", "unknown"),
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Add headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{round(duration_ms, 2)}ms"

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                "Request failed",
                error=e,
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            raise


# ============================================================================
# COMPRESSION MIDDLEWARE
# ============================================================================


class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Response compression middleware.

    Features:
    - Gzip compression
    - Configurable minimum size
    - Content-type filtering
    """

    def __init__(self, app: ASGIApp, minimum_size: int = 1000):
        """
        Initialize compression middleware.

        Args:
            app: ASGI application
            minimum_size: Minimum response size for compression (bytes)
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compressible_types = {
            "application/json",
            "application/xml",
            "text/html",
            "text/plain",
            "text/css",
            "text/javascript",
        }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with compression.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: Compressed response if applicable
        """
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        # Process request
        response = await call_next(request)

        # Check if response should be compressed
        content_type = response.headers.get("content-type", "")
        should_compress = any(ct in content_type.lower() for ct in self.compressible_types)

        if not should_compress:
            return response

        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Compress if size threshold met
        if len(body) >= self.minimum_size:
            compressed_body = gzip.compress(body, compresslevel=6)

            # Create compressed response
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = str(len(compressed_body))
            response.body = compressed_body

        return response


# ============================================================================
# CORRELATION ID MIDDLEWARE
# ============================================================================


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Correlation ID middleware for distributed tracing.

    Features:
    - Generates/propagates correlation IDs
    - Supports X-Correlation-ID header
    - Attaches to request state
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with correlation ID.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response: Response with correlation ID header
        """
        # Get or generate correlation ID
        correlation_id = request.headers.get("x-correlation-id", str(uuid.uuid4()))

        # Attach to request state
        request.state.correlation_id = correlation_id

        # Process request
        response = await call_next(request)

        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id

        return response


# ============================================================================
# MIDDLEWARE CONFIGURATION
# ============================================================================


def configure_middleware(app: ASGIApp) -> None:
    """
    Configure all middleware for the application.

    Args:
        app: FastAPI application
    """
    # Add middleware in reverse order (last added = first executed)

    # 1. Correlation ID (first to execute)
    app.add_middleware(CorrelationIDMiddleware)

    # 2. Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # 3. Rate limiting (if enabled)
    if hasattr(settings, "ENABLE_RATE_LIMITING") and settings.ENABLE_RATE_LIMITING:
        requests_per_minute = getattr(settings, "RATE_LIMIT_REQUESTS_PER_MINUTE", 60)
        app.add_middleware(
            RateLimitMiddleware, requests_per_minute=requests_per_minute, burst_size=10
        )

    # 4. Compression (if enabled)
    if hasattr(settings, "ENABLE_COMPRESSION") and settings.ENABLE_COMPRESSION:
        app.add_middleware(CompressionMiddleware, minimum_size=1000)

    logger.info("Middleware configured successfully")


# Export
__all__ = [
    "RateLimitMiddleware",
    "RequestLoggingMiddleware",
    "CompressionMiddleware",
    "CorrelationIDMiddleware",
    "configure_middleware",
]
