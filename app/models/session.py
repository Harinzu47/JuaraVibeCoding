from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.message import ChatMessage
    from app.models.user import User


class DailySession(Base):
    """Daily session tracking the financial state and chat history of a user for a specific date."""

    __tablename__ = "daily_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    session_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Financial state - Morning Phase (Prep/Costing)
    current_phase: Mapped[str] = mapped_column(String(20), default="MORNING_COSTING")
    total_spending: Mapped[int] = mapped_column(Integer, default=0)
    used_capital: Mapped[int] = mapped_column(Integer, default=0)
    cogs_per_unit: Mapped[int] = mapped_column(Integer, default=0)

    # Financial state - Evening Phase (Sales/Revenue)
    total_revenue: Mapped[int | None] = mapped_column(Integer, nullable=True)
    net_profit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    portions_sold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selling_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    break_even: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
    )
