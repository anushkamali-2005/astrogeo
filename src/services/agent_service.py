"""
Agent Service
==============
Production-level service for AI agent lifecycle management and orchestration.

Features:
- Agent instance management (factory pattern)
- Execution orchestration with error handling
- Result persistence and caching
- Performance tracking and analytics
- Multi-agent coordination

Author: Production Team
Version: 1.0.0
"""

from typing import Dict, Any, List, Optional, Type
from datetime import datetime, timedelta
from uuid import UUID
import time

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from src.agents.base_agent import BaseAgent
from src.agents.data_agent import DataAgent
from src.agents.ml_agent import MLAgent
from src.agents.geo_agent import GeoAgent
from src.agents.orchestrator import AgentOrchestrator, AgentType
from src.database.models import AgentExecution, User
from src.database.repositories import AgentExecutionRepository
from src.core.logging import get_logger
from src.core.exceptions import (
    AgentError,
    AgentExecutionError,
    ValidationError,
    RecordNotFoundError
)


logger = get_logger(__name__)


# ============================================================================
# AGENT SERVICE
# ============================================================================

class AgentService:
    """
    Production service for managing AI agent operations.
    
    Responsibilities:
    - Agent lifecycle management
    - Execution coordination
    - Performance tracking
    - Result persistence
    
    Design Pattern: Service Layer with Dependency Injection
    """
    
    # Agent registry (singleton instances)
    _agent_registry: Dict[str, BaseAgent] = {}
    _orchestrator: Optional[AgentOrchestrator] = None
    
    def __init__(self, db: AsyncSession):
        """
        Initialize agent service.
        
        Args:
            db: Database session for persistence
        """
        self.db = db
        self.repository = AgentExecutionRepository(db)
        
        # Initialize agent registry if not already done
        if not self._agent_registry:
            self._initialize_agents()
    
    @classmethod
    def _initialize_agents(cls) -> None:
        """
        Initialize agent registry (singleton pattern).
        
        Creates one instance of each agent type that can be reused.
        """
        try:
            cls._agent_registry = {
                "data": DataAgent(),
                "ml": MLAgent(),
                "geo": GeoAgent()
            }
            cls._orchestrator = AgentOrchestrator()
            
            logger.info(
                "Agent registry initialized",
                extra={"agent_count": len(cls._agent_registry)}
            )
        
        except Exception as e:
            logger.error("Failed to initialize agent registry", error=e)
            raise AgentError(
                message="Failed to initialize agent registry",
                details={"error": str(e)}
            )
    
    def get_agent(self, agent_type: str) -> BaseAgent:
        """
        Get agent instance by type (factory method).
        
        Args:
            agent_type: Agent type (data, ml, geo)
            
        Returns:
            BaseAgent: Agent instance
            
        Raises:
            ValidationError: If agent type is invalid
        """
        agent = self._agent_registry.get(agent_type)
        
        if not agent:
            raise ValidationError(
                message=f"Invalid agent type: {agent_type}",
                details={
                    "agent_type": agent_type,
                    "valid_types": list(self._agent_registry.keys())
                }
            )
        
        return agent
    
    async def execute_agent(
        self,
        agent_type: str,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[UUID] = None,
        save_to_database: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a single agent with full orchestration.
        
        Args:
            agent_type: Type of agent to execute
            task: Task description
            context: Additional context
            user_id: User ID for tracking
            save_to_database: Whether to persist execution
            
        Returns:
            dict: Execution result with metadata
            
        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()
        
        logger.info(
            "Starting agent execution",
            extra={
                "agent_type": agent_type,
                "task_preview": task[:100],
                "user_id": str(user_id) if user_id else None
            }
        )
        
        try:
            # Get agent instance
            agent = self.get_agent(agent_type)
            
            # Execute agent
            result = await agent.execute(task=task, context=context)
            
            # Calculate metrics
            execution_time = time.time() - start_time
            result["execution_time_seconds"] = round(execution_time, 4)
            result["agent_type"] = agent_type
            
            # Persist to database if requested
            if save_to_database:
                execution_record = await self._save_execution(
                    agent_name=agent_type,
                    task=task,
                    result=result,
                    user_id=user_id,
                    status="completed"
                )
                result["execution_id"] = str(execution_record.id)
            
            logger.info(
                "Agent execution completed",
                extra={
                    "agent_type": agent_type,
                    "execution_time_seconds": execution_time,
                    "status": "completed"
                }
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                "Agent execution failed",
                error=e,
                extra={
                    "agent_type": agent_type,
                    "execution_time_seconds": execution_time
                }
            )
            
            # Save failed execution
            if save_to_database:
                await self._save_execution(
                    agent_name=agent_type,
                    task=task,
                    result={"error": str(e)},
                    user_id=user_id,
                    status="failed",
                    error_message=str(e)
                )
            
            raise AgentExecutionError(
                agent_name=agent_type,
                details={
                    "task": task,
                    "error": str(e),
                    "execution_time_seconds": execution_time
                }
            )
    
    async def orchestrate_multi_agent(
        self,
        task: str,
        required_agents: Optional[List[str]] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute multi-agent orchestration.
        
        Args:
            task: Complex task requiring multiple agents
            required_agents: Specific agents to use (auto-detect if None)
            user_id: User ID for tracking
            
        Returns:
            dict: Orchestration result
        """
        start_time = time.time()
        
        logger.info(
            "Starting multi-agent orchestration",
            extra={
                "task_preview": task[:100],
                "required_agents": required_agents,
                "user_id": str(user_id) if user_id else None
            }
        )
        
        try:
            # Convert agent names to AgentType enum
            agent_types = None
            if required_agents:
                agent_types = [AgentType(agent) for agent in required_agents]
            
            # Execute orchestration
            result = await self._orchestrator.execute(
                task=task,
                required_agents=agent_types
            )
            
            # Add metrics
            execution_time = time.time() - start_time
            result["execution_time_seconds"] = round(execution_time, 4)
            result["orchestrator"] = "multi_agent"
            
            # Save orchestration result
            execution_record = await self._save_execution(
                agent_name="orchestrator",
                task=task,
                result=result,
                user_id=user_id,
                status="completed"
            )
            result["execution_id"] = str(execution_record.id)
            
            logger.info(
                "Multi-agent orchestration completed",
                extra={
                    "execution_time_seconds": execution_time,
                    "agents_used": len(result.get("agent_results", {}))
                }
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(
                "Multi-agent orchestration failed",
                error=e,
                extra={"execution_time_seconds": execution_time}
            )
            
            await self._save_execution(
                agent_name="orchestrator",
                task=task,
                result={"error": str(e)},
                user_id=user_id,
                status="failed",
                error_message=str(e)
            )
            
            raise AgentExecutionError(
                agent_name="orchestrator",
                details={"task": task, "error": str(e)}
            )
    
    async def get_execution_by_id(
        self,
        execution_id: UUID,
        user_id: Optional[UUID] = None
    ) -> AgentExecution:
        """
        Get execution details by ID.
        
        Args:
            execution_id: Execution ID
            user_id: User ID for authorization
            
        Returns:
            AgentExecution: Execution record
            
        Raises:
            RecordNotFoundError: If execution not found
        """
        execution = await self.repository.get_by_id(execution_id)
        
        if not execution:
            raise RecordNotFoundError("AgentExecution", execution_id)
        
        # Check authorization if user_id provided
        if user_id and execution.user_id != user_id:
            logger.warning(
                "Unauthorized execution access attempt",
                extra={
                    "execution_id": str(execution_id),
                    "requesting_user": str(user_id),
                    "owner_user": str(execution.user_id)
                }
            )
            raise RecordNotFoundError("AgentExecution", execution_id)
        
        return execution
    
    async def get_user_history(
        self,
        user_id: UUID,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get user's agent execution history.
        
        Args:
            user_id: User ID
            agent_name: Filter by agent name
            status: Filter by status
            limit: Results per page
            offset: Pagination offset
            
        Returns:
            dict: Paginated execution history
        """
        # Build query
        query = select(AgentExecution).where(AgentExecution.user_id == user_id)
        
        if agent_name:
            query = query.where(AgentExecution.agent_name == agent_name)
        if status:
            query = query.where(AgentExecution.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(AgentExecution).where(
            AgentExecution.user_id == user_id
        )
        if agent_name:
            count_query = count_query.where(AgentExecution.agent_name == agent_name)
        if status:
            count_query = count_query.where(AgentExecution.status == status)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(desc(AgentExecution.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        executions = result.scalars().all()
        
        return {
            "executions": executions,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }
    
    async def get_agent_metrics(
        self,
        agent_name: Optional[str] = None,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get agent performance metrics.
        
        Args:
            agent_name: Specific agent or all agents
            time_window_hours: Time window for metrics
            
        Returns:
            dict: Performance metrics
        """
        start_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        # Build query
        query = select(AgentExecution).where(
            AgentExecution.created_at >= start_time
        )
        
        if agent_name:
            query = query.where(AgentExecution.agent_name == agent_name)
        
        result = await self.db.execute(query)
        executions = result.scalars().all()
        
        # Calculate metrics
        total_executions = len(executions)
        successful = sum(1 for e in executions if e.status == "completed")
        failed = sum(1 for e in executions if e.status == "failed")
        avg_time = (
            sum(e.execution_time_ms for e in executions if e.execution_time_ms) / total_executions
            if total_executions > 0 else 0
        )
        
        return {
            "agent_name": agent_name or "all",
            "time_window_hours": time_window_hours,
            "total_executions": total_executions,
            "successful_executions": successful,
            "failed_executions": failed,
            "success_rate": round(successful / total_executions * 100, 2) if total_executions > 0 else 0,
            "average_execution_time_ms": round(avg_time, 2),
            "period_start": start_time.isoformat(),
            "period_end": datetime.utcnow().isoformat()
        }
    
    async def clear_agent_memory(self, agent_type: str) -> None:
        """
        Clear agent conversation memory.
        
        Args:
            agent_type: Agent type
        """
        agent = self.get_agent(agent_type)
        agent.clear_memory()
        
        logger.info(f"Agent memory cleared", extra={"agent_type": agent_type})
    
    def get_available_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available agents.
        
        Returns:
            dict: Agent information
        """
        return {
            name: agent.get_info()
            for name, agent in self._agent_registry.items()
        }
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    async def _save_execution(
        self,
        agent_name: str,
        task: str,
        result: Dict[str, Any],
        user_id: Optional[UUID] = None,
        status: str = "completed",
        error_message: Optional[str] = None
    ) -> AgentExecution:
        """
        Save agent execution to database.
        
        Args:
            agent_name: Agent name
            task: Task description
            result: Execution result
            user_id: User ID
            status: Execution status
            error_message: Error message if failed
            
        Returns:
            AgentExecution: Created record
        """
        execution_time_ms = result.get("execution_time_seconds", 0) * 1000
        
        execution = await self.repository.create(
            agent_name=agent_name,
            task=task,
            user_id=user_id,
            status=status,
            result=result.get("result"),
            execution_time_ms=execution_time_ms,
            error_message=error_message
        )
        
        logger.debug(
            "Agent execution saved",
            extra={"execution_id": str(execution.id), "agent_name": agent_name}
        )
        
        return execution


# Export
__all__ = ["AgentService"]
