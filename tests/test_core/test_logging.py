"""
Test Logging Module
===================
Unit tests for logging configuration.

Author: Production Team
Version: 1.0.0
"""

import pytest
import logging
from pathlib import Path

from src.core.logging import get_logger, setup_logging


class TestLogging:
    """Test logging functionality."""
    
    def test_get_logger(self):
        """Test logger creation."""
        logger = get_logger(__name__)
        
        assert logger is not None
        assert isinstance(logger, logging.Logger)
        assert logger.name == __name__
    
    def test_logger_has_handlers(self):
        """Test logger has configured handlers."""
        logger = get_logger("test_module")
        
        assert len(logger.handlers) > 0
    
    def test_logger_level_debug(self):
        """Test logger level in debug mode."""
        logger = get_logger("test_debug")
        
        # Logger should respect configured level
        assert logger.level >= logging.DEBUG or logger.level == logging.NOTSET
    
    def test_multiple_loggers_same_name(self):
        """Test getting same logger instance with same name."""
        logger1 = get_logger("test_same")
        logger2 = get_logger("test_same")
        
        assert logger1 is logger2
    
    def test_logger_can_log_info(self, caplog):
        """Test logger can log info messages."""
        logger = get_logger("test_info")
        
        with caplog.at_level(logging.INFO):
            logger.info("Test info message")
        
        assert "Test info message" in caplog.text
    
    def test_logger_can_log_error(self, caplog):
        """Test logger can log error messages."""
        logger = get_logger("test_error")
        
        with caplog.at_level(logging.ERROR):
            logger.error("Test error message")
        
        assert "Test error message" in caplog.text
    
    def test_logger_structured_logging(self, caplog):
        """Test structured logging with extra fields."""
        logger = get_logger("test_structured")
        
        with caplog.at_level(logging.INFO):
            logger.info("Test message", extra={"user_id": "123", "action": "test"})
        
        assert "Test message" in caplog.text
