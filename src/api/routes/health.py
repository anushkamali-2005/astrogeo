"""
Health Check API Routes
=======================
System health and status endpoints.

Endpoints:
- GET /health - Basic health check
- GET /health/detailed - Detailed system health
- GET /ping - Simple ping endpoint

Author: Production Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_db, check_db_connection
from src.core.config import settings
from src.core.logging import get_logger
from src.schemas.responses import SuccessResponse, HealthResponse, DetailedHealthResponse


logger = get_logger(__name__)
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/ping")
async def ping():
    """
    Simple ping endpoint for basic connectivity check.
    
    Returns:
        dict: Pong response
    """
    return {"status": "ok", "message": "pong"}


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        HealthResponse: Basic health status
    """
    return HealthResponse(
        status="healthy",
        service="astrogeo-api",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT
    )


@router.get("/detailed", response_model=SuccessResponse[DetailedHealthResponse])
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with component status.
    
    Args:
        db: Database session
        
    Returns:
        DetailedHealthResponse: Detailed health information
    """
    # Check database
    db_status = await check_db_connection()
    
    # Check Redis (mock for now)
    redis_status = {
        "status": "healthy",
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT
    }
    
    # Check MLflow (mock for now)
    mlflow_status = {
        "status": "healthy",
        "tracking_uri": settings.MLFLOW_TRACKING_URI
    }
    
    # Determine overall health
    overall_healthy = (
        db_status["status"] == "healthy" and
        redis_status["status"] == "healthy" and
        mlflow_status["status"] == "healthy"
    )
    
    response_data = DetailedHealthResponse(
        status="healthy" if overall_healthy else "degraded",
        service="astrogeo-api",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        components={
            "database": db_status,
            "redis": redis_status,
            "mlflow": mlflow_status
        }
    )
    
    return SuccessResponse(
        data=response_data,
        message="Health check completed"
    )


# Export router
__all__ = ["router"]
