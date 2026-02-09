"""
FastAPI Main Application
========================
Main entry point for the AstroGeo AI MLOps API.

Author: Production Team
Version: 1.0.0
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from src.api.routes import admin, agents, health
from src.api.routes.predictions import router as predictions_router
from src.core.config import settings
from src.core.logging import get_logger
from src.database.connection import close_db, init_db

logger = get_logger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting AstroGeo AI API")
    await init_db()
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down AstroGeo AI API")
    await close_db()
    logger.info("Application shutdown complete")


# ============================================================================
# APPLICATION INITIALIZATION
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)


# ============================================================================
# ROUTES
# ============================================================================


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "running",
        "docs": "/docs",
    }


# Register routers
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(agents.router, prefix=settings.API_V1_PREFIX)
app.include_router(predictions_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.API_WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
    )
