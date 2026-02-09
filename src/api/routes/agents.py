"""
Agent Routes
============
Endpoints for AI agent execution and orchestration:
- Single agent execution
- Multi-agent orchestration
- Agent status and history
- Real-time agent monitoring

Author: Production Team
Version: 1.0.0
"""

from typing import List, Dict, Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from src.database.connection import get_db
from src.database.models import AgentExecution, User
from src.schemas.requests import AgentExecutionRequest, MultiAgentRequest
from src.schemas.responses import (
    SuccessResponse,
    AgentExecutionResponse,
    PaginatedResponse
)
from src.agents.data_agent import DataAgent
from src.agents.ml_agent import MLAgent
from src.agents.geo_agent import GeoAgent
from src.agents.orchestrator import AgentOrchestrator, AgentType
from src.core.security import get_current_user
from src.core.logging import get_logger
from src.core.exceptions import AgentExecutionError, RecordNotFoundError
from datetime import datetime


logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# AGENT INSTANCES (Singleton)
# ============================================================================

# Initialize agents once
data_agent = DataAgent()
ml_agent = MLAgent()
geo_agent = GeoAgent()
orchestrator = AgentOrchestrator()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def save_agent_execution(
    db: AsyncSession,
    agent_name: str,
    task: str,
    result: Dict[str, Any],
    user_id: Optional[UUID] = None
) -> AgentExecution:
    """
    Save agent execution to database.
    
    Args:
        db: Database session
        agent_name: Agent name
        task: Task description
        result: Execution result
        user_id: User ID
        
    Returns:
        AgentExecution: Created record
    """
    execution = AgentExecution(
        agent_name=agent_name,
        task=task,
        user_id=user_id,
        status=result.get("status", "completed"),
        result=result.get("result"),
        execution_time_ms=result.get("execution_time_seconds", 0) * 1000
    )
    
    if result.get("status") == "failed":
        execution.error_message = result.get("error")
    
    db.add(execution)
    await db.commit()
    await db.refresh(execution)
    
    return execution


def get_agent_by_type(agent_type: str):
    """
    Get agent instance by type.
    
    Args:
        agent_type: Agent type (data, ml, geo)
        
    Returns:
        Agent instance
    """
    agents = {
        "data": data_agent,
        "ml": ml_agent,
        "geo": geo_agent
    }
    return agents.get(agent_type)


# ============================================================================
# AGENT EXECUTION ENDPOINTS
# ============================================================================

@router.post(
    "/execute",
    response_model=SuccessResponse[AgentExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute single agent",
    description="Execute a specific AI agent with a task"
)
async def execute_agent(
    request: AgentExecutionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute a single AI agent.
    
    Args:
        request: Agent execution request
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Execution result
    """
    logger.info(
        "Executing agent",
        extra={
            "agent_type": request.agent_type,
            "task": request.task[:100],
            "user_id": current_user.get("sub")
        }
    )
    
    # Get agent
    agent = get_agent_by_type(request.agent_type)
    if not agent:
        raise AgentExecutionError(
            agent_name=request.agent_type,
            details={"reason": "Unknown agent type"}
        )
    
    try:
        # Execute agent
        result = await agent.execute(
            task=request.task,
            context=request.context
        )
        
        # Save to database if requested
        if request.save_to_database:
            user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
            execution = await save_agent_execution(
                db=db,
                agent_name=request.agent_type,
                task=request.task,
                result=result,
                user_id=user_id
            )
            
            response_data = AgentExecutionResponse.from_orm(execution)
        else:
            # Create response without saving
            response_data = AgentExecutionResponse(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                agent_name=request.agent_type,
                task=request.task,
                status="completed",
                result=result.get("result"),
                execution_time_ms=result.get("execution_time_seconds", 0) * 1000,
                created_at=datetime.utcnow()
            )
        
        return {
            "success": True,
            "data": response_data,
            "message": f"Agent '{request.agent_type}' executed successfully"
        }
    
    except Exception as e:
        logger.error(
            f"Agent execution failed",
            error=e,
            extra={"agent_type": request.agent_type}
        )
        
        # Save failed execution
        if request.save_to_database:
            user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
            await save_agent_execution(
                db=db,
                agent_name=request.agent_type,
                task=request.task,
                result={"status": "failed", "error": str(e)},
                user_id=user_id
            )
        
        raise AgentExecutionError(
            agent_name=request.agent_type,
            details={"error": str(e)}
        )


@router.post(
    "/orchestrate",
    response_model=SuccessResponse[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Multi-agent orchestration",
    description="Execute multiple agents in coordination"
)
async def orchestrate_agents(
    request: MultiAgentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Execute multi-agent orchestration.
    
    Args:
        request: Multi-agent request
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Orchestration result
    """
    logger.info(
        "Starting multi-agent orchestration",
        extra={
            "task": request.task[:100],
            "agents": request.agents,
            "user_id": current_user.get("sub")
        }
    )
    
    try:
        # Convert agent names to AgentType enum
        required_agents = None
        if request.agents:
            required_agents = [AgentType(agent) for agent in request.agents]
        
        # Execute orchestration
        result = await orchestrator.execute(
            task=request.task,
            required_agents=required_agents
        )
        
        # Save orchestration to database
        user_id = UUID(current_user.get("sub")) if current_user.get("sub") else None
        execution = await save_agent_execution(
            db=db,
            agent_name="orchestrator",
            task=request.task,
            result=result,
            user_id=user_id
        )
        
        return {
            "success": True,
            "data": result,
            "message": "Multi-agent orchestration completed successfully"
        }
    
    except Exception as e:
        logger.error(
            "Multi-agent orchestration failed",
            error=e
        )
        raise AgentExecutionError(
            agent_name="orchestrator",
            details={"error": str(e)}
        )


# ============================================================================
# AGENT HISTORY & STATUS
# ============================================================================

@router.get(
    "/history",
    response_model=PaginatedResponse[AgentExecutionResponse],
    summary="Get agent execution history",
    description="Retrieve history of agent executions"
)
async def get_agent_history(
    agent_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get agent execution history.
    
    Args:
        agent_name: Filter by agent name
        status: Filter by status
        limit: Results per page
        offset: Pagination offset
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Paginated execution history
    """
    logger.info(
        "Retrieving agent history",
        extra={
            "agent_name": agent_name,
            "status": status,
            "user_id": current_user.get("sub")
        }
    )
    
    # Build query
    user_id = UUID(current_user.get("sub"))
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
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(desc(AgentExecution.created_at))
    query = query.limit(limit).offset(offset)
    
    result = await db.execute(query)
    executions = result.scalars().all()
    
    return {
        "success": True,
        "data": [AgentExecutionResponse.from_orm(e) for e in executions],
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }


@router.get(
    "/history/{execution_id}",
    response_model=SuccessResponse[AgentExecutionResponse],
    summary="Get agent execution details",
    description="Get detailed information about a specific execution"
)
async def get_execution_details(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get execution details.
    
    Args:
        execution_id: Execution ID
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        dict: Execution details
    """
    logger.info(
        "Retrieving execution details",
        extra={"execution_id": str(execution_id)}
    )
    
    # Get execution
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    
    if not execution:
        raise RecordNotFoundError("AgentExecution", execution_id)
    
    # Check ownership
    user_id = UUID(current_user.get("sub"))
    if execution.user_id != user_id:
        from src.core.exceptions import AuthorizationError
        raise AuthorizationError(
            message="Not authorized to view this execution"
        )
    
    return {
        "success": True,
        "data": AgentExecutionResponse.from_orm(execution),
        "message": "Execution details retrieved successfully"
    }


# ============================================================================
# AGENT INFORMATION
# ============================================================================

@router.get(
    "/info",
    summary="Get available agents",
    description="List all available agents and their capabilities"
)
async def get_agents_info(
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get information about available agents.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Agents information
    """
    agents_info = {
        "data_agent": data_agent.get_info(),
        "ml_agent": ml_agent.get_info(),
        "geo_agent": geo_agent.get_info()
    }
    
    return {
        "success": True,
        "data": agents_info,
        "message": "Retrieved information for 3 agents"
    }


@router.get(
    "/info/{agent_type}",
    summary="Get specific agent info",
    description="Get detailed information about a specific agent"
)
async def get_agent_info(
    agent_type: str,
    current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get specific agent information.
    
    Args:
        agent_type: Agent type
        current_user: Current authenticated user
        
    Returns:
        dict: Agent information
    """
    agent = get_agent_by_type(agent_type)
    if not agent:
        raise AgentExecutionError(
            agent_name=agent_type,
            details={"reason": "Unknown agent type"}
        )
    
    return {
        "success": True,
        "data": agent.get_info(),
        "message": f"Retrieved information for {agent_type} agent"
    }


# Import for count function
from sqlalchemy import func


# Export router
__all__ = ["router"]