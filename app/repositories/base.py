from typing import Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic Base Repository class implementing common async CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: str) -> Optional[ModelType]:
        """Fetch a single record by its primary key ID."""
        result = await db.execute(
            select(self.model).where(getattr(self.model, "id") == id)
        )
        return result.scalar_one_or_none()

    async def get_all(self, db: AsyncSession) -> Sequence[ModelType]:
        """Fetch all records of this model type."""
        result = await db.execute(select(self.model))
        return result.scalars().all()

    async def create(self, db: AsyncSession, obj: ModelType) -> ModelType:
        """Add a new object to the database session and flush."""
        db.add(obj)
        await db.flush()
        return obj

    async def delete(self, db: AsyncSession, obj: ModelType) -> None:
        """Remove an object from the database session."""
        await db.delete(obj)
