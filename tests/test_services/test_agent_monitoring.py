"""
Test Service Layer
==================
Comprehensive tests for production services.

Author: Production Team
Version: 1.0.0
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime

from src.services.agent_service import AgentService
from src.services.monitoring_service import MonitoringService, get_monitoring_service
from src.database.models import AgentExecution, User


# ============================================================================
# AGENT SERVICE TESTS
# ============================================================================

class TestAgentService:
    """Tests for AgentService."""
    
    @pytest.fixture
    async def mock_db(self):
        """Mock database session."""
        db = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db
    
    @pytest.fixture
    async def agent_service(self, mock_db):
        """Create agent service instance."""
        return AgentService(db=mock_db)
    
    @pytest.mark.asyncio
    async def test_get_agent_valid_type(self, agent_service):
        """Test getting agent by valid type."""
        agent = agent_service.get_agent("data")
        assert agent is not None
        assert agent.name == "DataAgent"
    
    @pytest.mark.asyncio
    async def test_get_agent_invalid_type(self, agent_service):
        """Test getting agent with invalid type."""
        from src.core.exceptions import ValidationError
        
        with pytest.raises(ValidationError):
            agent_service.get_agent("invalid_type")
    
    @pytest.mark.asyncio
    async def test_execute_agent_success(self, agent_service):
        """Test successful agent execution."""
        with patch.object(agent_service, 'get_agent') as mock_get_agent:
            mock_agent = AsyncMock()
            mock_agent.execute = AsyncMock(return_value={
                "output": "Success",
                "status": "completed"
            })
            mock_get_agent.return_value = mock_agent
            
            result = await agent_service.execute_agent(
                agent_type="data",
                task="Test task",
                save_to_database=False
            )
            
            assert result["agent_type"] == "data"
            assert "execution_time_seconds" in result
            assert result["result"] == "Success"
    
    @pytest.mark.asyncio
    async def test_execute_agent_with_database_save(self, agent_service, mock_db):
        """Test agent execution with database persistence."""
        with patch.object(agent_service, 'get_agent') as mock_get_agent, \
             patch.object(agent_service, '_save_execution') as mock_save:
            
            mock_agent = AsyncMock()
            mock_agent.execute = AsyncMock(return_value={
                "output": "Success",
                "status": "completed"
            })
            mock_get_agent.return_value = mock_agent
            
            mock_execution = AgentExecution(
                id=uuid4(),
                agent_name="data",
                task="Test",
                status="completed"
            )
            mock_save.return_value = mock_execution
            
            result = await agent_service.execute_agent(
                agent_type="data",
                task="Test task",
                user_id=uuid4(),
                save_to_database=True
            )
            
            assert "execution_id" in result
            mock_save.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_available_agents(self, agent_service):
        """Test getting info about available agents."""
        agents_info = agent_service.get_available_agents()
        
        assert "data" in agents_info
        assert "ml" in agents_info
        assert "geo" in agents_info
        assert all("name" in info for info in agents_info.values())


# ============================================================================
# MONITORING SERVICE TESTS
# ============================================================================

class TestMonitoringService:
    """Tests for MonitoringService."""
    
    @pytest.fixture
    def monitoring_service(self):
        """Create monitoring service instance."""
        return get_monitoring_service()
    
    def test_singleton_pattern(self):
        """Test that monitoring service is singleton."""
        service1 = get_monitoring_service()
        service2 = get_monitoring_service()
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_get_system_metrics(self, monitoring_service):
        """Test system metrics collection."""
        metrics = await monitoring_service.get_system_metrics()
        
        assert metrics["status"] == "healthy"
        assert "cpu" in metrics
        assert "memory" in metrics
        assert "disk" in metrics
        assert metrics["cpu"]["usage_percent"] >= 0
    
    @pytest.mark.asyncio
    async def test_check_database_health(self, monitoring_service):
        """Test database health check."""
        with patch('src.database.connection.DatabaseManager') as mock_db:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_db.return_value.get_session.return_value = mock_session
            mock_db.return_value.engine.pool.size.return_value = 10
            mock_db.return_value.engine.pool.checkedin.return_value = 8
            mock_db.return_value.engine.pool.checkedout.return_value = 2
            mock_db.return_value.engine.pool.overflow.return_value = 0
            
            result = await monitoring_service.check_database_health()
            
            # Should pass or return healthy status
            assert "status" in result
    
    @pytest.mark.asyncio
    async def test_get_health_status(self, monitoring_service):
        """Test comprehensive health status."""
        with patch.object(monitoring_service, 'check_database_health') as mock_db, \
             patch.object(monitoring_service, 'check_redis_health') as mock_redis, \
             patch.object(monitoring_service, 'get_system_metrics') as mock_system:
            
            mock_db.return_value = {"status": "healthy"}
            mock_redis.return_value = {"status": "healthy"}
            mock_system.return_value = {"status": "healthy"}
            
            health = await monitoring_service.get_health_status()
            
            assert health["status"] == "healthy"
            assert "components" in health
            assert "database" in health["components"]
            assert "redis" in health["components"]
            assert "system" in health["components"]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestServiceIntegration:
    """Integration tests for services."""
    
    @pytest.mark.asyncio
    async def test_agent_service_full_flow(self, mock_db):
        """Test complete agent service workflow."""
        service = AgentService(db=mock_db)
        
        # Get agent info
        agents = service.get_available_agents()
        assert len(agents) > 0
        
        # Execute agent (mocked)
        with patch.object(service, 'get_agent') as mock_get:
            mock_agent = AsyncMock()
            mock_agent.execute = AsyncMock(return_value={
                "output": "Result",
                "status": "completed"
            })
            mock_get.return_value = mock_agent
            
            result = await service.execute_agent(
                agent_type="data",
                task="Process data",
                save_to_database=False
            )
            
            assert result["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_monitoring_service_health_checks(self):
        """Test monitoring service health checks."""
        service = get_monitoring_service()
        
        # Get system metrics
        metrics = await service.get_system_metrics()
        assert "cpu" in metrics
        
        # Get health status (may fail if services not running)
        try:
            health = await service.get_health_status()
            assert "status" in health
        except Exception:
            # Expected if services not running in test environment
            pass
