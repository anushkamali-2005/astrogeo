"""
Enterprise Logging Module
========================
Production-ready logging with:
- Structured JSON logging
- Multiple handlers (file, console, syslog)
- Performance monitoring
- Context managers
- Request tracking
- Error reporting

Author: Production Team
Version: 1.0.0
"""

import json
import logging
import sys
import time
import traceback
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

from src.core.config import settings

# Context variable for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter with additional context.

    Adds:
    - Timestamp
    - Request ID
    - Environment
    - Application name
    """

    def add_fields(
        self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]
    ) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat()

        # Add application context
        log_record["app_name"] = settings.APP_NAME
        log_record["environment"] = settings.ENVIRONMENT
        log_record["version"] = settings.APP_VERSION

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id

        # Add severity level
        log_record["severity"] = record.levelname

        # Add source information
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno


class StructuredLogger:
    """
    Production-grade structured logger with multiple handlers.

    Features:
    - JSON and text formats
    - File and console output
    - Performance tracking
    - Error context capture
    """

    def __init__(self, name: str, log_level: Optional[str] = None):
        """
        Initialize logger.

        Args:
            name: Logger name (typically __name__)
            log_level: Override default log level
        """
        self.logger = logging.getLogger(name)
        self.log_level = log_level or settings.LOG_LEVEL

        # Prevent duplicate handlers
        if not self.logger.handlers:
            self._setup_handlers()

        self.logger.setLevel(self.log_level)
        self.logger.propagate = False

    def _setup_handlers(self) -> None:
        """Configure logging handlers."""
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)

        if settings.LOG_FORMAT == "json":
            # JSON format for production
            json_formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(name)s %(message)s")
            console_handler.setFormatter(json_formatter)
        else:
            # Human-readable format for development
            text_formatter = logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s] - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            console_handler.setFormatter(text_formatter)

        self.logger.addHandler(console_handler)

        # File Handler (if configured)
        if settings.LOG_FILE:
            log_file = Path(settings.LOG_FILE)
            log_file.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self.log_level)

            if settings.LOG_FORMAT == "json":
                file_handler.setFormatter(CustomJsonFormatter())
            else:
                file_handler.setFormatter(text_formatter)

            self.logger.addHandler(file_handler)

    def _format_extra(self, extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Format extra data for logging."""
        if not extra:
            return {}

        # Ensure all values are JSON serializable
        formatted = {}
        for key, value in extra.items():
            try:
                json.dumps(value)
                formatted[key] = value
            except (TypeError, ValueError):
                formatted[key] = str(value)

        return formatted

    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=self._format_extra(extra))

    def info(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self.logger.info(message, extra=self._format_extra(extra))

    def warning(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log warning message with optional exception details.

        Args:
            message: Warning message
            error: Exception object
            extra: Additional context
        """
        extra_data = self._format_extra(extra) or {}

        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
            extra_data["traceback"] = traceback.format_exc()

        self.logger.warning(message, extra=extra_data, exc_info=error is not None)

    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log error message with exception details.

        Args:
            message: Error message
            error: Exception object
            extra: Additional context
        """
        extra_data = self._format_extra(extra) or {}

        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
            extra_data["traceback"] = traceback.format_exc()

        self.logger.error(message, extra=extra_data, exc_info=error is not None)

    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log critical message."""
        extra_data = self._format_extra(extra) or {}

        if error:
            extra_data["error_type"] = type(error).__name__
            extra_data["error_message"] = str(error)
            extra_data["traceback"] = traceback.format_exc()

        self.logger.critical(message, extra=extra_data, exc_info=error is not None)

    def exception(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """Log exception with full traceback."""
        self.logger.exception(message, extra=self._format_extra(extra))


def get_logger(name: str) -> StructuredLogger:
    """
    Get logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger: Logger instance

    Example:
        >>> from src.core.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return StructuredLogger(name)


def log_execution_time(func):
    """
    Decorator to log function execution time.

    Example:
        >>> @log_execution_time
        >>> def process_data():
        >>>     # processing logic
        >>>     pass
    """
    logger = get_logger(func.__module__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                f"Function '{func.__name__}' executed successfully",
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 4),
                    "status": "success",
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                f"Function '{func.__name__}' failed",
                error=e,
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 4),
                    "status": "error",
                },
            )
            raise

    return wrapper


def log_async_execution_time(func):
    """
    Decorator to log async function execution time.

    Example:
        >>> @log_async_execution_time
        >>> async def fetch_data():
        >>>     # async processing
        >>>     pass
    """
    logger = get_logger(func.__module__)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time

            logger.info(
                f"Async function '{func.__name__}' executed successfully",
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 4),
                    "status": "success",
                    "is_async": True,
                },
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time

            logger.error(
                f"Async function '{func.__name__}' failed",
                error=e,
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": round(execution_time, 4),
                    "status": "error",
                    "is_async": True,
                },
            )
            raise

    return wrapper


class LogContext:
    """
    Context manager for logging blocks of code.

    Example:
        >>> with LogContext("data_processing", logger) as ctx:
        >>>     # processing logic
        >>>     ctx.add_metric("records_processed", 1000)
    """

    def __init__(self, operation: str, logger: StructuredLogger):
        """
        Initialize log context.

        Args:
            operation: Operation name
            logger: Logger instance
        """
        self.operation = operation
        self.logger = logger
        self.start_time = None
        self.metrics: Dict[str, Any] = {}

    def __enter__(self):
        """Enter context."""
        self.start_time = time.time()
        self.logger.info(f"Starting operation: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        execution_time = time.time() - self.start_time

        extra_data = {
            "operation": self.operation,
            "execution_time_seconds": round(execution_time, 4),
            **self.metrics,
        }

        if exc_type is None:
            self.logger.info(f"Completed operation: {self.operation}", extra=extra_data)
        else:
            self.logger.error(
                f"Failed operation: {self.operation}", error=exc_val, extra=extra_data
            )

        return False  # Don't suppress exceptions

    def add_metric(self, key: str, value: Any) -> None:
        """Add metric to log context."""
        self.metrics[key] = value


# Export public API
__all__ = [
    "get_logger",
    "StructuredLogger",
    "log_execution_time",
    "log_async_execution_time",
    "LogContext",
    "request_id_var",
]
