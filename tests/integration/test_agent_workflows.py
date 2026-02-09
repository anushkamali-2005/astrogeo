"""
Integration Tests - Agent Workflows
====================================
End-to-end tests for agent execution and orchestration.

Author: Production Team
Version: 1.0.0
"""

from uuid import uuid4

import pytest

from src.database.connection import get_db
from src.database.models import AgentExecution
from src.services.agent_service import AgentService


@pytest.mark.asyncio
class TestAgentServiceIntegration:
    """Integration tests for AgentService."""

    @pytest.fixture
    async def db_session(self):
        """Get database session."""
        async for session in get_db():
            yield session

    @pytest.fixture
    def agent_service(self, db_session):
        """Create agent service."""
        return AgentService(db=db_session)

    async def test_complete_agent_execution_flow(self, agent_service, db_session):
        """Test complete agent execution and database persistence."""
        # Execute agent
        result = await agent_service.execute_agent(
            agent_type="data",
            task="Analyze test dataset",
            context={"dataset": "test.csv"},
            user_id=uuid4(),
            save_to_database=True,
        )

        # Verify result
        assert "execution_id" in result
        assert "agent_type" in result
        assert result["agent_type"] == "data"

        # Verify database persistence
        execution_id = result["execution_id"]
        execution = await agent_service.get_execution_by_id(execution_id=execution_id)

        assert execution is not None
        assert str(execution.id) == execution_id
        assert execution.agent_name == "data"

    async def test_multi_agent_workflow(self, agent_service):
        """Test multi-agent orchestration workflow."""
        result = await agent_service.orchestrate_multi_agent(
            task="Complete data analysis and ML model building",
            required_agents=["data", "ml"],
            user_id=uuid4(),
        )

        assert "execution_id" in result
        assert "orchestrator" in result
        assert result["orchestrator"] == "multi_agent"

    async def test_agent_metrics_collection(self, agent_service):
        """Test agent performance metrics."""
        # Execute a few agents
        for i in range(3):
            await agent_service.execute_agent(
                agent_type="data", task=f"Test task {i}", save_to_database=True
            )

        # Get metrics
        metrics = await agent_service.get_agent_metrics(agent_name="data", time_window_hours=1)

        assert "total_executions" in metrics
        assert metrics["total_executions"] >= 3
        assert "success_rate" in metrics

    async def test_agent_history_retrieval(self, agent_service):
        """Test retrieving execution history."""
        user_id = uuid4()

        # Create some executions
        for i in range(5):
            await agent_service.execute_agent(
                agent_type="data", task=f"History test {i}", user_id=user_id, save_to_database=True
            )

        # Get history
        history = await agent_service.get_user_history(user_id=user_id, limit=10)

        assert "executions" in history
        assert len(history["executions"]) >= 5
        assert history["total"] >= 5


@pytest.mark.asyncio
class TestAgentErrorHandling:
    """Test agent error handling and recovery."""

    @pytest.fixture
    def agent_service(self, db_session):
        """Create agent service."""
        return AgentService(db=db_session)

    async def test_invalid_agent_type_error(self, agent_service):
        """Test error handling for invalid agent type."""
        from src.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            await agent_service.execute_agent(
                agent_type="nonexistent_agent", task="Test task", save_to_database=False
            )

    async def test_execution_failure_recorded(self, agent_service):
        """Test that failed executions are recorded."""
        # This would need to trigger an actual failure
        # Placeholder for failure recording test
        pass
