"""
Database Repositories
====================
Repository pattern for database operations:
- Base repository with CRUD operations
- Specialized repositories for each model
- Query optimization
- Transaction management

Author: Production Team
Version: 1.0.0
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.exceptions import DatabaseError, RecordNotFoundError
from src.core.logging import get_logger
from src.database.models import AgentExecution, Base, Location, MLModel, Prediction, User

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)


# ============================================================================
# BASE REPOSITORY
# ============================================================================


class BaseRepository(Generic[ModelType]):
    """
    Base repository with common CRUD operations.

    Features:
    - Create, Read, Update, Delete
    - Batch operations
    - Query optimization
    - Soft delete support
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            db: Database session
        """
        self.model = model
        self.db = db

    async def create(self, data: Optional[Dict[str, Any]] = None, **kwargs) -> ModelType:
        """
        Create new record.

        Args:
            data: Optional dict of model fields
            **kwargs: Model fields

        Returns:
            ModelType: Created record
        """
        try:
            payload: Dict[str, Any] = {}
            if data:
                payload.update(data)
            payload.update(kwargs)
            instance = self.model(**payload)
            self.db.add(instance)
            await self.db.commit()
            await self.db.refresh(instance)

            logger.info(f"Created {self.model.__name__}", extra={"model": self.model.__name__})

            return instance

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to create {self.model.__name__}", details={"error": str(e)}
            )

    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Get record by ID.

        Args:
            id: Record ID

        Returns:
            ModelType: Record or None
        """
        try:
            result = await self.db.execute(select(self.model).where(self.model.id == id))
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(
                f"Failed to get {self.model.__name__} by ID", error=e, extra={"id": str(id)}
            )
            raise DatabaseError(
                message=f"Failed to get {self.model.__name__}",
                details={"id": str(id), "error": str(e)},
            )

    async def get_all(
        self, limit: int = 100, offset: int = 0, order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        Get all records with pagination.

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            order_by: Field to order by

        Returns:
            list: List of records
        """
        try:
            query = select(self.model)

            # Add ordering
            if order_by and hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))

            # Add pagination
            query = query.limit(limit).offset(offset)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to get all {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to get {self.model.__name__} records", details={"error": str(e)}
            )

    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """
        Update record by ID.

        Args:
            id: Record ID
            **kwargs: Fields to update

        Returns:
            ModelType: Updated record or None
        """
        try:
            # Get existing record
            instance = await self.get_by_id(id)
            if not instance:
                return None

            # Update fields
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await self.db.commit()
            await self.db.refresh(instance)

            logger.info(f"Updated {self.model.__name__}", extra={"id": str(id)})

            return instance

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update {self.model.__name__}", error=e, extra={"id": str(id)})
            raise DatabaseError(
                message=f"Failed to update {self.model.__name__}",
                details={"id": str(id), "error": str(e)},
            )

    async def delete(self, id: UUID, soft: bool = True) -> bool:
        """
        Delete record by ID.

        Args:
            id: Record ID
            soft: Use soft delete if model supports it

        Returns:
            bool: True if deleted
        """
        try:
            instance = await self.get_by_id(id)
            if not instance:
                return False

            # Soft delete if supported
            if soft and hasattr(instance, "soft_delete"):
                instance.soft_delete()
                await self.db.commit()
            else:
                # Hard delete
                await self.db.delete(instance)
                await self.db.commit()

            logger.info(f"Deleted {self.model.__name__}", extra={"id": str(id), "soft": soft})

            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete {self.model.__name__}", error=e, extra={"id": str(id)})
            raise DatabaseError(
                message=f"Failed to delete {self.model.__name__}",
                details={"id": str(id), "error": str(e)},
            )

    async def count(self, **filters) -> int:
        """
        Count records with optional filters.

        Args:
            **filters: Filter conditions

        Returns:
            int: Record count
        """
        try:
            query = select(func.count()).select_from(self.model)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

            result = await self.db.execute(query)
            return int(result.scalar() or 0)

        except Exception as e:
            logger.error(f"Failed to count {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to count {self.model.__name__}", details={"error": str(e)}
            )

    async def exists(self, id: UUID) -> bool:
        """
        Check if record exists.

        Args:
            id: Record ID

        Returns:
            bool: True if exists
        """
        instance = await self.get_by_id(id)
        return instance is not None

    async def bulk_create(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Create multiple records in bulk.

        Args:
            items: List of dictionaries with model fields

        Returns:
            list: Created records

        Raises:
            DatabaseError: If bulk creation fails
        """
        try:
            instances = [self.model(**item) for item in items]
            self.db.add_all(instances)
            await self.db.commit()

            # Refresh all instances
            for instance in instances:
                await self.db.refresh(instance)

            logger.info(
                f"Bulk created {len(instances)} {self.model.__name__} records",
                extra={"count": len(instances)},
            )

            return instances

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk create {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to bulk create {self.model.__name__}",
                details={"count": len(items), "error": str(e)},
            )

    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Update multiple records in bulk.

        Args:
            updates: List of dicts with 'id' and fields to update

        Returns:
            int: Number of records updated

        Raises:
            DatabaseError: If bulk update fails
        """
        try:
            updated_count = 0

            for update_data in updates:
                record_id = update_data.pop("id")
                instance = await self.get_by_id(record_id)

                if instance:
                    for key, value in update_data.items():
                        if hasattr(instance, key):
                            setattr(instance, key, value)
                    updated_count += 1

            await self.db.commit()

            logger.info(
                f"Bulk updated {updated_count} {self.model.__name__} records",
                extra={"count": updated_count},
            )

            return updated_count

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk update {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to bulk update {self.model.__name__}", details={"error": str(e)}
            )

    async def bulk_delete(self, ids: List[UUID], soft: bool = True) -> int:
        """
        Delete multiple records in bulk.

        Args:
            ids: List of record IDs
            soft: Use soft delete if supported

        Returns:
            int: Number of records deleted

        Raises:
            DatabaseError: If bulk delete fails
        """
        try:
            deleted_count = 0

            for record_id in ids:
                success = await self.delete(record_id, soft=soft)
                if success:
                    deleted_count += 1

            logger.info(
                f"Bulk deleted {deleted_count} {self.model.__name__} records",
                extra={"count": deleted_count, "soft": soft},
            )

            return deleted_count

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to bulk delete {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to bulk delete {self.model.__name__}", details={"error": str(e)}
            )

    async def filter_by(self, **filters) -> List[ModelType]:
        """
        Filter records by dynamic criteria.

        Args:
            **filters: Field-value pairs for filtering

        Returns:
            list: Filtered records
        """
        try:
            query = select(self.model)

            for key, value in filters.items():
                if hasattr(self.model, key):
                    query = query.where(getattr(self.model, key) == value)

            result = await self.db.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to filter {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to filter {self.model.__name__}",
                details={"filters": filters, "error": str(e)},
            )

    async def search(
        self, query: str, fields: Optional[List[str]] = None, limit: int = 100
    ) -> List[ModelType]:
        """
        Search records by text query across multiple fields.

        Args:
            query: Search query
            fields: Fields to search in (optional)
            limit: Maximum results

        Returns:
            list: Matching records
        """
        try:
            from sqlalchemy import or_

            if fields is None:
                # Default to common text fields present on the model
                candidate_fields = ["name", "description", "title", "email", "username"]
                fields = [f for f in candidate_fields if hasattr(self.model, f)]

            conditions = []
            for field in fields:
                if hasattr(self.model, field):
                    # Use ILIKE for case-insensitive search
                    conditions.append(getattr(self.model, field).ilike(f"%{query}%"))

            if not conditions:
                return []

            stmt = select(self.model).where(or_(*conditions)).limit(limit)
            result = await self.db.execute(stmt)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Failed to search {self.model.__name__}", error=e)
            raise DatabaseError(
                message=f"Failed to search {self.model.__name__}",
                details={"query": query, "error": str(e)},
            )


# ============================================================================
# SPECIALIZED REPOSITORIES
# ============================================================================


class UserRepository(BaseRepository[User]):
    """Repository for User operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        try:
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by email", error=e)
            raise DatabaseError(
                message="Failed to get user", details={"email": email, "error": str(e)}
            )

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            result = await self.db.execute(select(User).where(User.username == username))
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get user by username", error=e)
            raise DatabaseError(
                message="Failed to get user", details={"username": username, "error": str(e)}
            )

    async def get_active_users(self, limit: int = 100) -> List[User]:
        """Get all active users."""
        try:
            result = await self.db.execute(
                select(User)
                .where(User.is_active == True)
                .where(User.is_deleted == False)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get active users", error=e)
            raise DatabaseError(message="Failed to get active users", details={"error": str(e)})


class LocationRepository(BaseRepository[Location]):
    """Repository for Location operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Location, db)

    async def get_by_country(self, country: str, limit: int = 100) -> List[Location]:
        """Get locations by country."""
        try:
            result = await self.db.execute(
                select(Location)
                .where(Location.country == country)
                .where(Location.is_deleted == False)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get locations by country", error=e)
            raise DatabaseError(
                message="Failed to get locations", details={"country": country, "error": str(e)}
            )

    async def get_by_type(self, location_type: str, limit: int = 100) -> List[Location]:
        """Get locations by type."""
        try:
            result = await self.db.execute(
                select(Location)
                .where(Location.location_type == location_type)
                .where(Location.is_deleted == False)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get locations by type", error=e)
            raise DatabaseError(
                message="Failed to get locations", details={"type": location_type, "error": str(e)}
            )


class MLModelRepository(BaseRepository[MLModel]):
    """Repository for MLModel operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(MLModel, db)

    async def get_by_status(self, status: str, limit: int = 100) -> List[MLModel]:
        """Get models by status."""
        try:
            result = await self.db.execute(
                select(MLModel).where(MLModel.status == status).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get models by status", error=e)
            raise DatabaseError(
                message="Failed to get models", details={"status": status, "error": str(e)}
            )

    async def get_production_models(self) -> List[MLModel]:
        """Get all production models."""
        return await self.get_by_status("production")

    async def get_by_name_and_version(self, name: str, version: str) -> Optional[MLModel]:
        """Get model by name and version."""
        try:
            result = await self.db.execute(
                select(MLModel).where(MLModel.name == name).where(MLModel.version == version)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error("Failed to get model by name and version", error=e)
            raise DatabaseError(
                message="Failed to get model",
                details={"name": name, "version": version, "error": str(e)},
            )


class PredictionRepository(BaseRepository[Prediction]):
    """Repository for Prediction operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(Prediction, db)

    async def get_by_model(self, model_id: UUID, limit: int = 100) -> List[Prediction]:
        """Get predictions by model ID."""
        try:
            result = await self.db.execute(
                select(Prediction).where(Prediction.model_id == model_id).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get predictions by model", error=e)
            raise DatabaseError(
                message="Failed to get predictions",
                details={"model_id": str(model_id), "error": str(e)},
            )

    async def get_by_user(self, user_id: UUID, limit: int = 100) -> List[Prediction]:
        """Get predictions by user ID."""
        try:
            result = await self.db.execute(
                select(Prediction).where(Prediction.user_id == user_id).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get predictions by user", error=e)
            raise DatabaseError(
                message="Failed to get predictions",
                details={"user_id": str(user_id), "error": str(e)},
            )


class AgentExecutionRepository(BaseRepository[AgentExecution]):
    """Repository for AgentExecution operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(AgentExecution, db)

    async def get_by_agent(self, agent_name: str, limit: int = 100) -> List[AgentExecution]:
        """Get executions by agent name."""
        try:
            result = await self.db.execute(
                select(AgentExecution).where(AgentExecution.agent_name == agent_name).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get executions by agent", error=e)
            raise DatabaseError(
                message="Failed to get executions", details={"agent": agent_name, "error": str(e)}
            )

    async def get_by_status(self, status: str, limit: int = 100) -> List[AgentExecution]:
        """Get executions by status."""
        try:
            result = await self.db.execute(
                select(AgentExecution).where(AgentExecution.status == status).limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error("Failed to get executions by status", error=e)
            raise DatabaseError(
                message="Failed to get executions", details={"status": status, "error": str(e)}
            )


# Export all repositories
__all__ = [
    "BaseRepository",
    "UserRepository",
    "LocationRepository",
    "MLModelRepository",
    "PredictionRepository",
    "AgentExecutionRepository",
]
