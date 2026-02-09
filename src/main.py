"""
Application Entry Point
=======================
Compatibility shim so tests can import `src.main.app`.
"""

from src.api.main import app

__all__ = ["app"]
