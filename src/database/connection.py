"""
Database Connection Management
==============================
Async database connection and session management.

Features:
- Async SQLAlchemy engine
- Connection pooling
- Session lifecycle management
- Dependency injection for FastAPI
- Health checks

Author: Production Team
Version: 1.0.0
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine,
    async_sessionmaker
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text

from src.core.config import settings
from src.core.logging import get_logger
from src.database.models import Base


logger = get_logger(__name__)


# ============================================================================
# DATABASE ENGINE
# ============================================================================

class DatabaseManager:
    """
    Database connection manager with async support.
    
    Features:
    - Async engine creation
    - Connection pooling
    - Session factory
    - Health checks
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize database manager."""
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker | None = None
        self._initialized = False
    
    async def initialize(self):
        """
        Initialize database engine and session factory.
        
        Creates async engine with connection pooling and
        session factory for dependency injection.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return
        
        try:
            # Get database URL from settings
            database_url = str(settings.DATABASE_URL)
            
            # Replace scheme for asyncpg
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://",
                    "postgresql+asyncpg://",
                    1
                )
            
            logger.info(
                "Initializing database connection",
                extra={
                    "host": settings.POSTGRES_HOST,
                    "port": settings.POSTGRES_PORT,
                    "database": settings.POSTGRES_DB
                }
            )
            
            # Create async engine
            self.engine = create_async_engine(
                database_url,
                echo=settings.DEBUG,
                pool_size=settings.DB_POOL_SIZE,
                max_overflow=settings.DB_MAX_OVERFLOW,
                pool_timeout=settings.DB_POOL_TIMEOUT,
                pool_recycle=settings.DB_POOL_RECYCLE,
                pool_pre_ping=True,  # Verify connections before using
                poolclass=QueuePool if settings.ENVIRONMENT == "production" else NullPool
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False
            )
            
            self._initialized = True
            
            logger.info("Database connection initialized successfully")
        
        except Exception as e:
            logger.error("Failed to initialize database", error=e)
            raise
    
    async def create_tables(self):
        """
        Create all database tables.
        
        WARNING: This should only be used in development.
        In production, use Alembic migrations.
        """
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        try:
            logger.info("Creating database tables")
            
            async with self.engine.begin() as conn:
                # Enable PostGIS extension
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                
                # Create all tables
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
        
        except Exception as e:
            logger.error("Failed to create tables", error=e)
            raise
    
    async def drop_tables(self):
        """
        Drop all database tables.
        
        WARNING: This is destructive and should only be used in testing.
        """
        if not self.engine:
            raise RuntimeError("Database not initialized")
        
        try:
            logger.warning("Dropping all database tables")
            
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
            
            logger.info("Database tables dropped")
        
        except Exception as e:
            logger.error("Failed to drop tables", error=e)
            raise
    
    async def health_check(self) -> bool:
        """
        Check database connection health.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return False
        
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            
            logger.debug("Database health check passed")
            return True
        
        except Exception as e:
            logger.error("Database health check failed", error=e)
            return False
    
    async def close(self):
        """Close database connections gracefully."""
        if self.engine:
            logger.info("Closing database connections")
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connections closed")
    
    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create a new database session (context manager).
        
        Yields:
            AsyncSession: Database session
            
        Example:
            async with db_manager.session() as session:
                result = await session.execute(query)
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Global database manager instance
db_manager = DatabaseManager()


# ============================================================================
# FASTAPI DEPENDENCY
# ============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.
    
    Yields:
        AsyncSession: Database session
        
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    if not db_manager.session_factory:
        raise RuntimeError("Database not initialized. Call db_manager.initialize() first.")
    
    async with db_manager.session() as session:
        yield session


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

async def init_db():
    """Initialize database on application startup."""
    await db_manager.initialize()
    logger.info("Database initialized on startup")


async def close_db():
    """Close database on application shutdown."""
    await db_manager.close()
    logger.info("Database closed on shutdown")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def check_db_connection() -> dict:
    """
    Check database connection and return status.
    
    Returns:
        dict: Connection status information
    """
    try:
        is_healthy = await db_manager.health_check()
        
        return {
            "database": "postgresql",
            "status": "healthy" if is_healthy else "unhealthy",
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "pool_size": settings.DB_POOL_SIZE,
            "initialized": db_manager._initialized
        }
    
    except Exception as e:
        logger.error("Database connection check failed", error=e)
        return {
            "database": "postgresql",
            "status": "error",
            "error": str(e),
            "initialized": db_manager._initialized
        }


# Export public API
__all__ = [
    "DatabaseManager",
    "db_manager",
    "get_db",
    "init_db",
    "close_db",
    "check_db_connection"
]
