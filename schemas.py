from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter.")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class DailySessionResponse(BaseModel):
    id: str
    session_date: date
    fase_saat_ini: str
    total_belanja: int
    modal_terpakai: int
    hpp_unit: int
    total_pendapatan: Optional[int] = None
    laba_bersih: Optional[int] = None
    porsi_terjual: Optional[int] = None
    harga_jual: Optional[int] = None
    balik_modal: Optional[bool] = None

    model_config = {"from_attributes": True}


class ChatMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_model(cls, msg) -> "ChatMessageResponse":
        return cls(
            id=msg.id,
            role=msg.role,
            content=msg.content,
            created_at=msg.created_at.isoformat() if msg.created_at else "",
        )


class SessionWithHistoryResponse(DailySessionResponse):
    messages: list[ChatMessageResponse] = []
