from datetime import date
from typing import Optional, Sequence

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import DailySession
from app.repositories.base import BaseRepository


class DailySessionRepository(BaseRepository[DailySession]):
    """Repository handling all CRUD database operations for the DailySession model."""

    def __init__(self):
        super().__init__(DailySession)

    async def get_by_date(
        self,
        db: AsyncSession,
        user_id: str,
        session_date: date,
        load_messages: bool = False,
    ) -> Optional[DailySession]:
        """Fetch a session for a specific date and user, optionally loading messages."""
        query = select(DailySession).where(
            DailySession.user_id == user_id, DailySession.session_date == session_date
        )
        if load_messages:
            query = query.options(selectinload(DailySession.messages))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def list_by_user(
        self, db: AsyncSession, user_id: str
    ) -> Sequence[DailySession]:
        """Fetch all daily sessions for a specific user, sorted from newest to oldest."""
        result = await db.execute(
            select(DailySession)
            .where(DailySession.user_id == user_id)
            .order_by(desc(DailySession.session_date))
        )
        return result.scalars().all()

    async def get_or_create_today_session(
        self, db: AsyncSession, user_id: str
    ) -> DailySession:
        """Retrieve today's session, or create a new one if it does not yet exist."""
        today = date.today()
        session = await self.get_by_date(db, user_id, today, load_messages=True)
        if not session:
            session = DailySession(
                user_id=user_id, session_date=today, current_phase="MORNING_COSTING"
            )
            session = await self.create(db, session)
        return session


session_repository = DailySessionRepository()
