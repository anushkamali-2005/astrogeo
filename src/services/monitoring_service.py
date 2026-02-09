"""
Monitoring Service
==================
Production-level system monitoring and health check service.

Features:
- Database connectivity health checks
- Redis cache monitoring
- System resource metrics (CPU, memory, disk)
- Agent performance tracking
- Prometheus metrics export

Author: Production Team
Version: 1.0.0
"""

import asyncio
from datetime import datetime
from threading import Lock
from typing import Any, Dict, Optional

import psutil
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.exceptions import ServiceUnavailableError
from src.core.logging import get_logger
from src.database.connection import DatabaseManager

logger = get_logger(__name__)


# ============================================================================
# SINGLETON PATTERN FOR MONITORING SERVICE
# ============================================================================


class SingletonMeta(type):
    """
    Thread-safe singleton metaclass.
    """

    _instances = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


# ============================================================================
# MONITORING SERVICE
# ============================================================================


class MonitoringService(metaclass=SingletonMeta):
    """
    Singleton service for system monitoring and health checks.

    Features:
    - Infrastructure health checks (DB, Redis)
    - System resource monitoring
    - Performance metrics collection
    - Prometheus integration ready

    Design Pattern: Singleton with lazy initialization
    """

    def __init__(self):
        """Initialize monitoring service."""
        self._initialized = False
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_timeout = 30  # seconds
        self._last_update: Optional[datetime] = None

        logger.info("MonitoringService initialized (Singleton)")

    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.

        Returns:
            dict: Health status with component checks
        """
        logger.debug("Performing health check")

        # Run all health checks concurrently
        db_health, redis_health, system_health = await asyncio.gather(
            self.check_database_health(),
            self.check_redis_health(),
            self.get_system_metrics(),
            return_exceptions=True,
        )

        # Process results
        components = {
            "database": self._process_health_result(db_health),
            "redis": self._process_health_result(redis_health),
            "system": self._process_health_result(system_health),
        }

        # Determine overall status
        all_healthy = all(comp.get("status") == "healthy" for comp in components.values())

        overall_status = "healthy" if all_healthy else "degraded"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "components": components,
            "version": settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "1.0.0",
        }

    async def check_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and performance.

        Returns:
            dict: Database health status
        """
        try:
            db_manager = DatabaseManager()

            # Get a session
            async with db_manager.get_session() as session:
                start_time = datetime.utcnow()

                # Execute simple query
                result = await session.execute(text("SELECT 1"))
                result.scalar()

                # Calculate response time
                response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

                # Get connection pool stats
                pool = db_manager.engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                }

                return {
                    "status": "healthy",
                    "response_time_ms": round(response_time_ms, 2),
                    "pool": pool_status,
                    "database": settings.POSTGRES_DB,
                    "host": settings.POSTGRES_HOST,
                }

        except Exception as e:
            logger.error("Database health check failed", error=e)
            return {"status": "unhealthy", "error": str(e), "database": settings.POSTGRES_DB}

    async def check_redis_health(self) -> Dict[str, Any]:
        """
        Check Redis connectivity and performance.

        Returns:
            dict: Redis health status
        """
        try:
            # Import redis here to make it optional
            import redis.asyncio as aioredis

            # Create Redis client
            redis_client = aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
                encoding="utf-8",
                decode_responses=True,
            )

            start_time = datetime.utcnow()

            # Ping Redis
            await redis_client.ping()

            # Get server info
            info = await redis_client.info("server")

            response_time_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            await redis_client.close()

            return {
                "status": "healthy",
                "response_time_ms": round(response_time_ms, 2),
                "version": info.get("redis_version"),
                "host": settings.REDIS_HOST,
                "port": settings.REDIS_PORT,
            }

        except ImportError:
            # Redis library not installed
            return {
                "status": "unavailable",
                "message": "Redis client not installed",
                "note": "Install with: pip install redis",
            }

        except Exception as e:
            logger.error("Redis health check failed", error=e)
            return {"status": "unhealthy", "error": str(e), "host": settings.REDIS_HOST}

    async def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system resource metrics.

        Returns:
            dict: System metrics (CPU, memory, disk)
        """
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()

            # Get memory usage
            memory = psutil.virtual_memory()

            # Get disk usage
            disk = psutil.disk_usage("/")

            # Get network stats (optional)
            try:
                network = psutil.net_io_counters()
                network_stats = {"bytes_sent": network.bytes_sent, "bytes_recv": network.bytes_recv}
            except Exception:
                network_stats = None

            return {
                "status": "healthy",
                "cpu": {"usage_percent": round(cpu_percent, 2), "count": cpu_count},
                "memory": {
                    "total_mb": round(memory.total / (1024**2), 2),
                    "used_mb": round(memory.used / (1024**2), 2),
                    "available_mb": round(memory.available / (1024**2), 2),
                    "usage_percent": round(memory.percent, 2),
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.percent, 2),
                },
                "network": network_stats,
            }

        except Exception as e:
            logger.error("System metrics collection failed", error=e)
            return {"status": "unhealthy", "error": str(e)}

    async def get_application_metrics(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get application-specific metrics.

        Args:
            db: Database session

        Returns:
            dict: Application metrics
        """
        try:
            from sqlalchemy import func, select

            from src.database.models import AgentExecution, MLModel, Prediction, User

            # Run queries concurrently
            users_query = select(func.count()).select_from(User)
            executions_query = select(func.count()).select_from(AgentExecution)
            predictions_query = select(func.count()).select_from(Prediction)
            models_query = select(func.count()).select_from(MLModel)

            results = await asyncio.gather(
                db.execute(users_query),
                db.execute(executions_query),
                db.execute(predictions_query),
                db.execute(models_query),
            )

            return {
                "total_users": results[0].scalar(),
                "total_agent_executions": results[1].scalar(),
                "total_predictions": results[2].scalar(),
                "total_models": results[3].scalar(),
            }

        except Exception as e:
            logger.error("Application metrics collection failed", error=e)
            return {"error": str(e)}

    def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            str: Prometheus-formatted metrics
        """
        # This is a placeholder for Prometheus integration
        # In production, use prometheus_client library

        metrics = []

        # Example metrics
        metrics.append("# HELP astrogeo_up Service availability")
        metrics.append("# TYPE astrogeo_up gauge")
        metrics.append("astrogeo_up 1")

        metrics.append("# HELP astrogeo_info Service information")
        metrics.append("# TYPE astrogeo_info gauge")
        metrics.append(
            f'astrogeo_info{{version="{settings.APP_VERSION if hasattr(settings, "APP_VERSION") else "1.0.0"}"}} 1'
        )

        return "\n".join(metrics)

    async def check_service_availability(self, service_name: str) -> bool:
        """
        Check if a specific service is available.

        Args:
            service_name: Service name (database, redis, etc.)

        Returns:
            bool: True if service is available
        """
        if service_name == "database":
            result = await self.check_database_health()
            return result.get("status") == "healthy"

        elif service_name == "redis":
            result = await self.check_redis_health()
            return result.get("status") == "healthy"

        else:
            logger.warning(f"Unknown service: {service_name}")
            return False

    async def raise_if_unhealthy(self) -> None:
        """
        Raise exception if system is unhealthy.

        Raises:
            ServiceUnavailableError: If critical services are down
        """
        health = await self.get_health_status()

        if health["status"] != "healthy":
            unhealthy_components = [
                name
                for name, data in health["components"].items()
                if data.get("status") != "healthy"
            ]

            raise ServiceUnavailableError(
                message="System is unhealthy",
                details={"unhealthy_components": unhealthy_components, "health_status": health},
            )

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _process_health_result(self, result: Any) -> Dict[str, Any]:
        """
        Process health check result (handles exceptions).

        Args:
            result: Health check result or exception

        Returns:
            dict: Processed health status
        """
        if isinstance(result, Exception):
            return {"status": "unhealthy", "error": str(result)}
        elif isinstance(result, dict):
            return result
        else:
            return {"status": "unknown", "error": "Unexpected result type"}


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def get_monitoring_service() -> MonitoringService:
    """
    Get monitoring service instance (singleton).

    Returns:
        MonitoringService: Monitoring service singleton
    """
    return MonitoringService()


# Export
__all__ = ["MonitoringService", "get_monitoring_service"]
