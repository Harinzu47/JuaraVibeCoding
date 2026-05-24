from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Repository handling all CRUD database operations for the ChatMessage model."""

    def __init__(self):
        super().__init__(ChatMessage)

    async def create_message(
        self, db: AsyncSession, session_id: str, role: str, content: str
    ) -> ChatMessage:
        """Create a new chat message associated with a session and save to the database."""
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        return await self.create(db, msg)


message_repository = ChatMessageRepository()
