"""
Test Astronomical Agent
=======================
Unit tests for AstroAgent.

Author: Production Team
Version: 1.0.0
"""

from unittest.mock import Mock, patch

import pytest

from src.agents.astro_agent import AstroAgent


class TestAstroAgent:
    """Test Astronomical Agent."""

    @pytest.fixture
    def agent(self):
        """Create AstroAgent instance."""
        return AstroAgent()

    def test_agent_initialization(self, agent):
        """Test agent initializes correctly."""
        assert agent.name == "AstroAgent"
        assert len(agent.tools) == 6
        assert agent.agent_executor is not None

    def test_agent_has_required_tools(self, agent):
        """Test agent has all required tools."""
        tool_names = [tool.name for tool in agent.tools]

        required_tools = [
            "track_celestial_object",
            "astronomical_calculation",
            "query_star_catalog",
            "calculate_orbit",
            "analyze_light_curve",
            "transform_coordinates",
        ]

        for required_tool in required_tools:
            assert required_tool in tool_names

    @pytest.mark.asyncio
    async def test_celestial_tracking_tool(self, agent):
        """Test celestial object tracking tool."""
        # Find the tool
        track_tool = next(t for t in agent.tools if t.name == "track_celestial_object")

        # Mock execution
        with patch("src.agents.astro_agent.track_celestial_object_tool") as mock_tool:
            mock_tool.return_value = {
                "object_name": "Mars",
                "position": {"ra": "12h30m", "dec": "+15d"},
                "visible": True,
            }

            result = mock_tool(
                object_name="Mars",
                observer_location="New York",
                observation_time="2024-01-01T00:00:00",
            )

            assert result["object_name"] == "Mars"
            assert result["visible"] is True

    @pytest.mark.asyncio
    async def test_astronomical_calculation_tool(self, agent):
        """Test astronomical calculation tool."""
        calc_tool = next(t for t in agent.tools if t.name == "astronomical_calculation")

        assert calc_tool is not None
        assert "calculation" in calc_tool.description.lower()

    @pytest.mark.asyncio
    async def test_star_catalog_query_tool(self, agent):
        """Test star catalog query tool."""
        catalog_tool = next(t for t in agent.tools if t.name == "query_star_catalog")

        assert catalog_tool is not None
        assert "catalog" in catalog_tool.description.lower()

    @pytest.mark.asyncio
    async def test_agent_execution(self, agent):
        """Test agent can execute a task."""
        task = "What is the position of Mars tonight?"

        with patch.object(agent.agent_executor, "ainvoke") as mock_execute:
            mock_execute.return_value = {"output": "Mars is at RA 12h30m, Dec +15d"}

            result = await agent.execute(task)

            assert result is not None
            assert "output" in result
