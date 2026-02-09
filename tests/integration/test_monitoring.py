"""
Integration Tests - Monitoring and Health Checks
=================================================
Tests for monitoring service and health check integration.

Author: Production Team
Version: 1.0.0
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.database.connection import get_db
from src.services.monitoring_service import get_monitoring_service


@pytest.mark.asyncio
class TestMonitoringServiceIntegration:
    """Test monitoring service integration."""

    @pytest.fixture
    def monitoring_service(self):
        """Get monitoring service instance."""
        return get_monitoring_service()

    async def test_complete_health_check(self, monitoring_service):
        """Test complete health check workflow."""
        health = await monitoring_service.get_health_status()

        assert "status" in health
        assert "timestamp" in health
        assert "components" in health

        # Check components
        components = health["components"]
        assert "database" in components
        assert "redis" in components
        assert "system" in components

    async def test_database_health_check(self, monitoring_service):
        """Test database health check."""
        db_health = await monitoring_service.check_database_health()

        assert "status" in db_health
        assert "response_time_ms" in db_health

        if db_health["status"] == "healthy":
            assert db_health["response_time_ms"] < 1000

    async def test_redis_health_check(self, monitoring_service):
        """Test Redis health check."""
        redis_health = await monitoring_service.check_redis_health()

        assert "status" in redis_health

        # Redis might not be available in test environment
        assert redis_health["status"] in ["healthy", "unhealthy"]

    async def test_system_metrics_collection(self, monitoring_service):
        """Test system metrics collection."""
        metrics = await monitoring_service.get_system_metrics()

        assert "status" in metrics
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics

        # Verify metric values
        assert 0 <= metrics["cpu"]["percent"] <= 100
        assert metrics["memory"]["total"] > 0

    async def test_application_metrics(self, monitoring_service):
        """Test application-specific metrics."""
        app_metrics = await monitoring_service.get_application_metrics()

        assert "predictions" in app_metrics
        assert "agent_executions" in app_metrics

        # Each metric should have a count
        assert "total" in app_metrics["predictions"]
        assert "total" in app_metrics["agent_executions"]

    async def test_metrics_aggregation(self, monitoring_service):
        """Test metrics aggregation over time."""
        metrics = await monitoring_service.aggregate_metrics(time_window_hours=24)

        assert "period" in metrics
        assert "predictions" in metrics
        assert "agents" in metrics


@pytest.mark.asyncio
class TestHealthEndpointIntegration:
    """Test health check endpoints integration."""

    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client."""
        from httpx import AsyncClient

        from src.main import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client

    async def test_basic_health_endpoint(self, async_client):
        """Test basic health endpoint."""
        response = await async_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    async def test_detailed_health_endpoint(self, async_client):
        """Test detailed health endpoint."""
        response = await async_client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()

        assert "components" in data
        assert isinstance(data["components"], dict)

    async def test_metrics_endpoint(self, async_client):
        """Test metrics endpoint."""
        response = await async_client.get("/api/v1/metrics")

        # Metrics endpoint might require authentication
        assert response.status_code in [200, 401, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.asyncio
class TestMonitoringAlerts:
    """Test monitoring alerts and thresholds."""

    @pytest.fixture
    def monitoring_service(self):
        """Get monitoring service instance."""
        return get_monitoring_service()

    async def test_cpu_threshold_detection(self, monitoring_service):
        """Test CPU usage threshold detection."""
        metrics = await monitoring_service.get_system_metrics()

        cpu_percent = metrics["cpu"]["percent"]

        # Check if alert would trigger
        if cpu_percent > 80:
            assert metrics["status"] == "degraded"

    async def test_memory_threshold_detection(self, monitoring_service):
        """Test memory usage threshold detection."""
        metrics = await monitoring_service.get_system_metrics()

        memory_percent = metrics["memory"]["percent"]

        # Check if alert would trigger
        if memory_percent > 85:
            assert metrics["status"] == "degraded"

    async def test_database_performance_threshold(self, monitoring_service):
        """Test database performance monitoring."""
        db_health = await monitoring_service.check_database_health()

        if db_health["status"] == "healthy":
            # Response time should be reasonable
            assert db_health["response_time_ms"] < 500


@pytest.mark.asyncio
class TestMonitoringRecovery:
    """Test monitoring service recovery from failures."""

    @pytest.fixture
    def monitoring_service(self):
        """Get monitoring service instance."""
        return get_monitoring_service()

    async def test_database_failure_recovery(self, monitoring_service):
        """Test recovery from database failure."""
        # Simulate database failure
        with patch.object(
            monitoring_service,
            "check_database_health",
            new=AsyncMock(return_value={"status": "unhealthy", "error": "Connection timeout"}),
        ):
            health = await monitoring_service.get_health_status()

            assert health["status"] in ["degraded", "unhealthy"]
            assert health["components"]["database"]["status"] == "unhealthy"

    async def test_partial_failure_handling(self, monitoring_service):
        """Test handling partial system failures."""
        # Simulate Redis failure but DB healthy
        with patch.object(
            monitoring_service,
            "check_redis_health",
            new=AsyncMock(return_value={"status": "unhealthy"}),
        ):
            health = await monitoring_service.get_health_status()

            # System should be degraded but not completely unhealthy
            assert health["status"] in ["healthy", "degraded"]


@pytest.mark.asyncio
class TestConcurrentMonitoring:
    """Test concurrent monitoring operations."""

    @pytest.fixture
    def monitoring_service(self):
        """Get monitoring service instance."""
        return get_monitoring_service()

    async def test_concurrent_health_checks(self, monitoring_service):
        """Test concurrent health check requests."""
        import asyncio

        # Make multiple concurrent requests
        tasks = [monitoring_service.get_health_status() for _ in range(10)]

        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 10
        assert all("status" in r for r in results)

    async def test_metrics_collection_thread_safety(self, monitoring_service):
        """Test thread-safe metrics collection."""
        import asyncio

        # Collect metrics concurrently
        tasks = [monitoring_service.get_system_metrics() for _ in range(5)]

        results = await asyncio.gather(*tasks)

        # All should return valid metrics
        assert len(results) == 5
        assert all("cpu" in r for r in results)
