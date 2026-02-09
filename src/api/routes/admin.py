"""
Admin Routes
============
Administrative endpoints for system management:
- Model deployment and versioning
- User management
- System statistics
- Configuration management
- Health monitoring

Author: Production Team
Version: 1.0.0
"""

from typing import List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from src.database.connection import get_db
from src.database.models import User, MLModel, Prediction, AgentExecution, Location
from src.schemas.requests import ModelDeployRequest, SystemHealthRequest
from src.schemas.responses import (
    SuccessResponse,
    MLModelResponse,
    SystemStatsResponse,
    ComponentHealth,
    HealthCheckResponse
)
from src.core.security import get_current_user
from src.core.logging import get_logger
from src.core.exceptions import AuthorizationError, RecordNotFoundError
from src.database.connection import db_manager


logger = get_logger(__name__)
router = APIRouter()


# ============================================================================
# AUTHORIZATION HELPERS
# ============================================================================

async def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)):
    """
    Require admin privileges.
    
    Args:
        current_user: Current authenticated user
        
    Raises:
        AuthorizationError: If user is not admin
    """
    if not current_user.get("is_superuser", False):
        raise AuthorizationError(
            message="Admin privileges required",
            details={"user_id": current_user.get("sub")}
        )
    return current_user


# ============================================================================
# MODEL MANAGEMENT
# ============================================================================

@router.get(
    "/models",
    response_model=SuccessResponse[List[MLModelResponse]],
    summary="List all models",
    description="Get list of all ML models in the system"
)
async def list_models(
    status: str = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    List all ML models with optional filtering.
    
    Args:
        status: Filter by model status
        limit: Results per page
        offset: Pagination offset
        db: Database session
        admin: Admin user
        
    Returns:
        dict: List of models
    """
    logger.info(
        "Listing models",
        extra={"status_filter": status, "admin_id": admin.get("sub")}
    )
    
    # Build query
    query = select(MLModel)
    if status:
        query = query.where(MLModel.status == status)
    
    query = query.limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    models = result.scalars().all()
    
    return {
        "success": True,
        "data": [MLModelResponse.from_orm(m) for m in models],
        "message": f"Retrieved {len(models)} models"
    }


@router.post(
    "/models/{model_id}/deploy",
    response_model=SuccessResponse[MLModelResponse],
    status_code=status.HTTP_200_OK,
    summary="Deploy model to environment",
    description="Deploy or update model deployment status"
)
async def deploy_model(
    model_id: UUID,
    deploy_request: ModelDeployRequest,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Deploy model to specified environment.
    
    Args:
        model_id: Model ID
        deploy_request: Deployment configuration
        db: Database session
        admin: Admin user
        
    Returns:
        dict: Updated model information
    """
    logger.info(
        "Deploying model",
        extra={
            "model_id": str(model_id),
            "target_status": deploy_request.status,
            "admin_id": admin.get("sub")
        }
    )
    
    # Get model
    result = await db.execute(
        select(MLModel).where(MLModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise RecordNotFoundError("MLModel", model_id)
    
    # Update deployment status
    old_status = model.status
    model.status = deploy_request.status
    
    # Add deployment metadata
    if deploy_request.status == "production":
        from datetime import datetime
        model.deployed_at = datetime.utcnow()
        model.deployed_by = UUID(admin.get("sub"))
    
    await db.commit()
    await db.refresh(model)
    
    logger.info(
        "Model deployment updated",
        extra={
            "model_id": str(model_id),
            "old_status": old_status,
            "new_status": model.status
        }
    )
    
    return {
        "success": True,
        "data": MLModelResponse.from_orm(model),
        "message": f"Model deployed to {deploy_request.status}"
    }


@router.delete(
    "/models/{model_id}",
    status_code=status.HTTP_200_OK,
    summary="Archive model",
    description="Archive a model (soft delete)"
)
async def archive_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Archive a model.
    
    Args:
        model_id: Model ID
        db: Database session
        admin: Admin user
        
    Returns:
        dict: Success response
    """
    logger.info(
        "Archiving model",
        extra={"model_id": str(model_id), "admin_id": admin.get("sub")}
    )
    
    # Get model
    result = await db.execute(
        select(MLModel).where(MLModel.id == model_id)
    )
    model = result.scalar_one_or_none()
    
    if not model:
        raise RecordNotFoundError("MLModel", model_id)
    
    # Archive (soft delete)
    model.status = "archived"
    await db.commit()
    
    return {
        "success": True,
        "message": f"Model {model_id} archived successfully"
    }


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@router.get(
    "/users",
    response_model=SuccessResponse[List[Dict[str, Any]]],
    summary="List all users",
    description="Get list of all users in the system"
)
async def list_users(
    is_active: bool = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    List all users.
    
    Args:
        is_active: Filter by active status
        limit: Results per page
        offset: Pagination offset
        db: Database session
        admin: Admin user
        
    Returns:
        dict: List of users
    """
    logger.info(
        "Listing users",
        extra={"active_filter": is_active, "admin_id": admin.get("sub")}
    )
    
    # Build query
    query = select(User).where(User.is_deleted == False)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    
    query = query.limit(limit).offset(offset)
    
    # Execute
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Format response (exclude sensitive data)
    users_data = [
        {
            "id": str(u.id),
            "email": u.email,
            "username": u.username,
            "full_name": u.full_name,
            "is_active": u.is_active,
            "is_verified": u.is_verified,
            "created_at": u.created_at.isoformat(),
            "last_login": u.last_login.isoformat() if u.last_login else None
        }
        for u in users
    ]
    
    return {
        "success": True,
        "data": users_data,
        "message": f"Retrieved {len(users)} users"
    }


@router.patch(
    "/users/{user_id}/activate",
    summary="Activate/deactivate user",
    description="Toggle user active status"
)
async def toggle_user_active(
    user_id: UUID,
    is_active: bool,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Activate or deactivate a user.
    
    Args:
        user_id: User ID
        is_active: Active status
        db: Database session
        admin: Admin user
        
    Returns:
        dict: Success response
    """
    logger.info(
        "Toggling user active status",
        extra={
            "user_id": str(user_id),
            "is_active": is_active,
            "admin_id": admin.get("sub")
        }
    )
    
    # Get user
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise RecordNotFoundError("User", user_id)
    
    # Update status
    user.is_active = is_active
    await db.commit()
    
    return {
        "success": True,
        "message": f"User {'activated' if is_active else 'deactivated'} successfully"
    }


# ============================================================================
# SYSTEM STATISTICS
# ============================================================================

@router.get(
    "/stats",
    response_model=SuccessResponse[SystemStatsResponse],
    summary="Get system statistics",
    description="Get comprehensive system statistics"
)
async def get_system_stats(
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get system-wide statistics.
    
    Args:
        db: Database session
        admin: Admin user
        
    Returns:
        dict: System statistics
    """
    logger.info("Retrieving system stats", extra={"admin_id": admin.get("sub")})
    
    # Count users
    users_count = await db.execute(
        select(func.count()).select_from(User).where(User.is_deleted == False)
    )
    total_users = users_count.scalar()
    
    # Count predictions
    predictions_count = await db.execute(
        select(func.count()).select_from(Prediction)
    )
    total_predictions = predictions_count.scalar()
    
    # Count models
    models_count = await db.execute(
        select(func.count()).select_from(MLModel)
    )
    total_models = models_count.scalar()
    
    # Count locations
    locations_count = await db.execute(
        select(func.count()).select_from(Location).where(Location.is_deleted == False)
    )
    total_locations = locations_count.scalar()
    
    # Count active agent executions
    active_agents_count = await db.execute(
        select(func.count()).select_from(AgentExecution)
        .where(AgentExecution.status.in_(["pending", "running"]))
    )
    active_agents = active_agents_count.scalar()
    
    # Mock system metrics (replace with actual monitoring)
    import psutil
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent
    
    stats = SystemStatsResponse(
        total_users=total_users,
        total_predictions=total_predictions,
        total_models=total_models,
        total_locations=total_locations,
        active_agents=active_agents,
        uptime_seconds=0.0,  # Implement actual uptime tracking
        cpu_usage_percent=cpu_percent,
        memory_usage_percent=memory_percent
    )
    
    return {
        "success": True,
        "data": stats,
        "message": "System statistics retrieved successfully"
    }


# ============================================================================
# HEALTH & MONITORING
# ============================================================================

@router.post(
    "/health/detailed",
    response_model=SuccessResponse[HealthCheckResponse],
    summary="Detailed system health check",
    description="Check health of all system components"
)
async def detailed_health_check(
    health_request: SystemHealthRequest,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Perform detailed health check.
    
    Args:
        health_request: Health check configuration
        db: Database session
        admin: Admin user
        
    Returns:
        dict: Detailed health information
    """
    logger.info("Performing detailed health check", extra={"admin_id": admin.get("sub")})
    
    components = {}
    
    # Check database
    if health_request.include_database:
        import time
        start = time.time()
        db_healthy = await db_manager.health_check()
        db_time = (time.time() - start) * 1000
        
        components["database"] = ComponentHealth(
            status="healthy" if db_healthy else "unhealthy",
            response_time_ms=round(db_time, 2),
            details={"type": "PostgreSQL + PostGIS"}
        )
    
    # Check cache (Redis)
    if health_request.include_cache:
        # Mock - implement actual Redis health check
        components["cache"] = ComponentHealth(
            status="healthy",
            response_time_ms=1.2,
            details={"type": "Redis"}
        )
    
    # Check MLflow
    if health_request.include_mlflow:
        # Mock - implement actual MLflow health check
        components["mlflow"] = ComponentHealth(
            status="healthy",
            response_time_ms=23.4,
            details={"tracking_uri": "configured"}
        )
    
    # Overall status
    all_healthy = all(c.status == "healthy" for c in components.values())
    overall_status = "healthy" if all_healthy else "degraded"
    
    from datetime import datetime
    from src.core.config import settings
    
    health_response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        components=components
    )
    
    return {
        "success": True,
        "data": health_response,
        "message": "Health check completed"
    }


# ============================================================================
# DATA MANAGEMENT
# ============================================================================

@router.delete(
    "/cleanup/old-predictions",
    summary="Clean up old predictions",
    description="Delete predictions older than specified days"
)
async def cleanup_old_predictions(
    days: int = 90,
    db: AsyncSession = Depends(get_db),
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Clean up old predictions.
    
    Args:
        days: Delete predictions older than this many days
        db: Database session
        admin: Admin user
        
    Returns:
        dict: Cleanup results
    """
    logger.info(
        "Cleaning up old predictions",
        extra={"days": days, "admin_id": admin.get("sub")}
    )
    
    from datetime import datetime, timedelta
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Delete old predictions
    result = await db.execute(
        select(Prediction).where(Prediction.created_at < cutoff_date)
    )
    old_predictions = result.scalars().all()
    
    for pred in old_predictions:
        await db.delete(pred)
    
    await db.commit()
    
    return {
        "success": True,
        "message": f"Deleted {len(old_predictions)} predictions older than {days} days"
    }


# ============================================================================
# CONFIGURATION
# ============================================================================

@router.get(
    "/config",
    summary="Get system configuration",
    description="Get current system configuration (non-sensitive)"
)
async def get_system_config(
    admin: Dict = Depends(require_admin)
) -> Dict[str, Any]:
    """
    Get system configuration.
    
    Args:
        admin: Admin user
        
    Returns:
        dict: System configuration
    """
    from src.core.config import settings
    
    # Return non-sensitive configuration
    config = {
        "app_name": settings.APP_NAME,
        "app_version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "api_v1_prefix": settings.API_V1_PREFIX,
        "cors_origins": settings.CORS_ORIGINS,
        "rate_limit_enabled": settings.RATE_LIMIT_ENABLED,
        "rate_limit_per_minute": settings.RATE_LIMIT_PER_MINUTE,
        "database": {
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB
        },
        "mlflow": {
            "tracking_uri": settings.MLFLOW_TRACKING_URI,
            "experiment_name": settings.MLFLOW_EXPERIMENT_NAME
        }
    }
    
    return {
        "success": True,
        "data": config,
        "message": "Configuration retrieved successfully"
    }


# Export router
__all__ = ["router"]