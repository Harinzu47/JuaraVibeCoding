from typing import Optional

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str


class ChatResponse(BaseModel):
    response: str
    total_spending: int
    used_capital: int
    cogs_per_unit: int
    current_phase: str
    total_revenue: Optional[int] = None
    net_profit: Optional[int] = None
    portions_sold: Optional[int] = None
    selling_price: Optional[int] = None
    break_even: Optional[bool] = None
    is_correction: bool = False
    correction_summary: Optional[str] = None


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
