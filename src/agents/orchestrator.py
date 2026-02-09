"""
Agent Orchestrator
==================
Multi-agent orchestration for complex task coordination:
- Task decomposition
- Agent selection and coordination
- Parallel execution
- Result aggregation
- Error handling and retries

Author: Production Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import time

from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent
from src.agents.ml_agent import MLAgent
from src.agents.geo_agent import GeoAgent
from src.core.logging import get_logger
from src.core.exceptions import AgentExecutionError


logger = get_logger(__name__)


class AgentType(str, Enum):
    """Available agent types."""
    DATA = "data"
    ML = "ml"
    GEO = "geo"


class TaskComplexity(str, Enum):
    """Task complexity levels."""
    SIMPLE = "simple"  # Single agent
    MODERATE = "moderate"  # 2-3 agents
    COMPLEX = "complex"  # 3+ agents, coordination needed


class AgentOrchestrator:
    """
    Multi-agent orchestrator for complex task execution.
    
    Features:
    - Intelligent task decomposition
    - Automatic agent selection
    - Parallel execution
    - Result aggregation
    - Error handling
    - Performance tracking
    """
    
    def __init__(
        self,
        enable_parallel: bool = True,
        max_retries: int = 2,
        timeout: int = 600
    ):
        """
        Initialize orchestrator.
        
        Args:
            enable_parallel: Enable parallel agent execution
            max_retries: Maximum retry attempts per agent
            timeout: Total timeout in seconds
        """
        self.enable_parallel = enable_parallel
        self.max_retries = max_retries
        self.timeout = timeout
        
        # Initialize agents
        self.agents: Dict[AgentType, BaseAgent] = {
            AgentType.DATA: DataAgent(),
            AgentType.ML: MLAgent(),
            AgentType.GEO: GeoAgent()
        }
        
        logger.info(
            "Agent Orchestrator initialized",
            extra={
                "num_agents": len(self.agents),
                "parallel_enabled": enable_parallel,
                "timeout": timeout
            }
        )
    
    async def execute(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        required_agents: Optional[List[AgentType]] = None
    ) -> Dict[str, Any]:
        """
        Execute complex task with multi-agent coordination.
        
        Args:
            task: Task description
            context: Additional context
            required_agents: Specific agents to use (auto-detect if None)
            
        Returns:
            dict: Orchestration results
        """
        start_time = time.time()
        
        logger.info(
            "Starting multi-agent orchestration",
            extra={
                "task": task[:100],
                "required_agents": required_agents
            }
        )
        
        try:
            # Analyze task and determine agents
            if required_agents:
                selected_agents = required_agents
            else:
                selected_agents = self._select_agents(task, context)
            
            # Determine task complexity
            complexity = self._assess_complexity(task, selected_agents)
            
            # Decompose task into subtasks
            subtasks = self._decompose_task(task, selected_agents, context)
            
            # Execute agents
            if self.enable_parallel and len(subtasks) > 1:
                results = await self._execute_parallel(subtasks)
            else:
                results = await self._execute_sequential(subtasks)
            
            # Aggregate results
            final_result = self._aggregate_results(results, task)
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Prepare response
            response = {
                "status": "completed",
                "task": task,
                "complexity": complexity.value,
                "agents_used": [agent.value for agent in selected_agents],
                "num_subtasks": len(subtasks),
                "execution_mode": "parallel" if self.enable_parallel and len(subtasks) > 1 else "sequential",
                "agent_results": results,
                "final_result": final_result,
                "execution_time_seconds": round(execution_time, 2),
                "timestamp": time.time()
            }
            
            logger.info(
                "Multi-agent orchestration completed",
                extra={
                    "agents_used": len(selected_agents),
                    "execution_time": execution_time,
                    "success": True
                }
            )
            
            return response
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                "Multi-agent orchestration failed",
                error=e,
                extra={"execution_time": execution_time}
            )
            
            return {
                "status": "failed",
                "task": task,
                "error": str(e),
                "execution_time_seconds": round(execution_time, 2),
                "timestamp": time.time()
            }
    
    def _select_agents(
        self,
        task: str,
        context: Optional[Dict[str, Any]]
    ) -> List[AgentType]:
        """
        Intelligently select agents based on task.
        
        Args:
            task: Task description
            context: Additional context
            
        Returns:
            list: Selected agent types
        """
        task_lower = task.lower()
        selected = []
        
        # Data-related keywords
        data_keywords = [
            "data", "ingest", "load", "validate", "clean", "preprocess",
            "transform", "merge", "csv", "json", "dataset", "quality"
        ]
        if any(keyword in task_lower for keyword in data_keywords):
            selected.append(AgentType.DATA)
        
        # ML-related keywords
        ml_keywords = [
            "model", "train", "predict", "ml", "machine learning", "evaluate",
            "accuracy", "classification", "regression", "feature", "hyperparameter"
        ]
        if any(keyword in task_lower for keyword in ml_keywords):
            selected.append(AgentType.ML)
        
        # Geo-related keywords
        geo_keywords = [
            "location", "geocode", "map", "distance", "coordinates", "latitude",
            "longitude", "spatial", "gis", "geographic", "route", "nearby"
        ]
        if any(keyword in task_lower for keyword in geo_keywords):
            selected.append(AgentType.GEO)
        
        # If no agents selected, default to data agent
        if not selected:
            selected.append(AgentType.DATA)
        
        logger.info(
            "Agents selected for task",
            extra={"selected_agents": [a.value for a in selected]}
        )
        
        return selected
    
    def _assess_complexity(
        self,
        task: str,
        agents: List[AgentType]
    ) -> TaskComplexity:
        """
        Assess task complexity.
        
        Args:
            task: Task description
            agents: Required agents
            
        Returns:
            TaskComplexity: Complexity level
        """
        # Single agent = simple
        if len(agents) == 1:
            return TaskComplexity.SIMPLE
        
        # 2-3 agents = moderate
        elif len(agents) <= 3:
            return TaskComplexity.MODERATE
        
        # 4+ agents = complex
        else:
            return TaskComplexity.COMPLEX
    
    def _decompose_task(
        self,
        task: str,
        agents: List[AgentType],
        context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Decompose task into agent-specific subtasks.
        
        Args:
            task: Main task
            agents: Selected agents
            context: Additional context
            
        Returns:
            list: List of subtasks
        """
        subtasks = []
        
        # Create subtask for each agent
        for agent_type in agents:
            subtask = {
                "agent_type": agent_type,
                "task": self._generate_subtask(task, agent_type),
                "context": context or {},
                "priority": self._get_agent_priority(agent_type, agents)
            }
            subtasks.append(subtask)
        
        # Sort by priority (higher priority first)
        subtasks.sort(key=lambda x: x["priority"], reverse=True)
        
        logger.info(
            "Task decomposed into subtasks",
            extra={"num_subtasks": len(subtasks)}
        )
        
        return subtasks
    
    def _generate_subtask(
        self,
        main_task: str,
        agent_type: AgentType
    ) -> str:
        """
        Generate agent-specific subtask from main task.
        
        Args:
            main_task: Main task description
            agent_type: Agent type
            
        Returns:
            str: Subtask for specific agent
        """
        # Intelligent subtask generation based on agent type
        task_templates = {
            AgentType.DATA: f"Handle all data operations for: {main_task}",
            AgentType.ML: f"Handle all ML operations for: {main_task}",
            AgentType.GEO: f"Handle all geospatial operations for: {main_task}"
        }
        
        return task_templates.get(agent_type, main_task)
    
    def _get_agent_priority(
        self,
        agent_type: AgentType,
        all_agents: List[AgentType]
    ) -> int:
        """
        Determine agent execution priority.
        
        Args:
            agent_type: Agent type
            all_agents: All selected agents
            
        Returns:
            int: Priority (higher = execute first)
        """
        # Data should typically run first (priority 3)
        # GEO and ML can run in parallel (priority 2)
        priority_map = {
            AgentType.DATA: 3,
            AgentType.GEO: 2,
            AgentType.ML: 2
        }
        
        return priority_map.get(agent_type, 1)
    
    async def _execute_sequential(
        self,
        subtasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute subtasks sequentially.
        
        Args:
            subtasks: List of subtasks
            
        Returns:
            list: Execution results
        """
        results = []
        
        for subtask in subtasks:
            agent_type = subtask["agent_type"]
            agent = self.agents[agent_type]
            
            try:
                result = await agent.execute(
                    task=subtask["task"],
                    context=subtask["context"]
                )
                results.append({
                    "agent": agent_type.value,
                    "status": "success",
                    "result": result
                })
            
            except Exception as e:
                logger.error(
                    f"Agent {agent_type.value} failed",
                    error=e
                )
                results.append({
                    "agent": agent_type.value,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    async def _execute_parallel(
        self,
        subtasks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Execute subtasks in parallel.
        
        Args:
            subtasks: List of subtasks
            
        Returns:
            list: Execution results
        """
        tasks = []
        
        for subtask in subtasks:
            agent_type = subtask["agent_type"]
            agent = self.agents[agent_type]
            
            # Create async task
            task = asyncio.create_task(
                agent.execute(
                    task=subtask["task"],
                    context=subtask["context"]
                )
            )
            tasks.append((agent_type, task))
        
        # Wait for all tasks
        results = []
        for agent_type, task in tasks:
            try:
                result = await task
                results.append({
                    "agent": agent_type.value,
                    "status": "success",
                    "result": result
                })
            except Exception as e:
                logger.error(
                    f"Agent {agent_type.value} failed in parallel execution",
                    error=e
                )
                results.append({
                    "agent": agent_type.value,
                    "status": "failed",
                    "error": str(e)
                })
        
        return results
    
    def _aggregate_results(
        self,
        agent_results: List[Dict[str, Any]],
        original_task: str
    ) -> Dict[str, Any]:
        """
        Aggregate results from multiple agents.
        
        Args:
            agent_results: Results from agents
            original_task: Original task description
            
        Returns:
            dict: Aggregated final result
        """
        # Collect successful results
        successful_results = [
            r for r in agent_results
            if r["status"] == "success"
        ]
        
        # Collect failed results
        failed_results = [
            r for r in agent_results
            if r["status"] == "failed"
        ]
        
        # Aggregate
        aggregated = {
            "task": original_task,
            "total_agents": len(agent_results),
            "successful_agents": len(successful_results),
            "failed_agents": len(failed_results),
            "success_rate": len(successful_results) / len(agent_results) if agent_results else 0,
            "insights": [],
            "recommendations": [],
            "summary": ""
        }
        
        # Extract insights from successful results
        for result in successful_results:
            agent_name = result["agent"]
            agent_result = result["result"]
            
            # Add agent-specific insights
            aggregated["insights"].append({
                "agent": agent_name,
                "key_findings": f"Agent {agent_name} completed successfully"
            })
        
        # Generate summary
        if failed_results:
            aggregated["summary"] = (
                f"Task partially completed. {len(successful_results)}/{len(agent_results)} "
                f"agents succeeded. Review failed agents for issues."
            )
        else:
            aggregated["summary"] = (
                f"Task completed successfully with {len(successful_results)} agents. "
                f"All operations executed without errors."
            )
        
        return aggregated
    
    def get_agent(self, agent_type: AgentType) -> BaseAgent:
        """
        Get specific agent instance.
        
        Args:
            agent_type: Agent type
            
        Returns:
            BaseAgent: Agent instance
        """
        return self.agents[agent_type]


# Export
__all__ = ["AgentOrchestrator", "AgentType", "TaskComplexity"]