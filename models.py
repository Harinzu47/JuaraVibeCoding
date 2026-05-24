from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions: Mapped[list["DailySession"]] = relationship(
        "DailySession", back_populates="user"
    )


class DailySession(Base):
    """Satu record per user per tanggal. Menyimpan state finansial harian."""

    __tablename__ = "daily_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    session_date: Mapped[Date] = mapped_column(Date, nullable=False)

    # Financial state — semua field dari ChatResponse
    fase_saat_ini: Mapped[str] = mapped_column(String(20), default="PAGI_COSTING")
    total_belanja: Mapped[int] = mapped_column(Integer, default=0)
    modal_terpakai: Mapped[int] = mapped_column(Integer, default=0)
    hpp_unit: Mapped[int] = mapped_column(Integer, default=0)

    # Evening phase fields — nullable karena hanya terisi di fase sore
    total_pendapatan: Mapped[int | None] = mapped_column(Integer, nullable=True)
    laba_bersih: Mapped[int | None] = mapped_column(Integer, nullable=True)
    porsi_terjual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    harga_jual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    balik_modal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",  # wajib untuk DELETE /api/sessions/today
    )


class ChatMessage(Base):
    """Satu record per pesan. Menyimpan riwayat obrolan per sesi harian."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("daily_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" atau "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["DailySession"] = relationship("DailySession", back_populates="messages")
