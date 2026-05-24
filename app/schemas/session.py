from datetime import date
from typing import Optional

from pydantic import BaseModel

from app.schemas.chat import ChatMessageResponse


class DailySessionResponse(BaseModel):
    id: str
    session_date: date
    current_phase: str
    total_spending: int
    used_capital: int
    cogs_per_unit: int
    total_revenue: Optional[int] = None
    net_profit: Optional[int] = None
    portions_sold: Optional[int] = None
    selling_price: Optional[int] = None
    break_even: Optional[bool] = None

    model_config = {"from_attributes": True}


class SessionWithHistoryResponse(DailySessionResponse):
    messages: list[ChatMessageResponse] = []
