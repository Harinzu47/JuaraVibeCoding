from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling all CRUD database operations for the User model."""

    def __init__(self):
        super().__init__(User)

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Retrieve a user from the database by email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(
        self, db: AsyncSession, email: str, password_raw: str, full_name: str | None = None
    ) -> User:
        """Create and hash password for a new user, then save to the database."""
        user = User(email=email, hashed_password=hash_password(password_raw), full_name=full_name)
        return await self.create(db, user)


user_repository = UserRepository()
