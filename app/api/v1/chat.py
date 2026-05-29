import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.models.message import ChatMessage
from app.repositories.session import session_repository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini import gemini_service
from app.services.calculator import FinancialCalculator

logger = structlog.get_logger()
router = APIRouter(prefix="/api/chat", tags=["chat"])

def build_system_prompt(fase: str, session) -> str:
    base_context = f"""
Kamu adalah AturModal, asisten finansial AI yang ramah untuk ibu-ibu penjual makanan UMKM Indonesia.
Gunakan bahasa Indonesia sehari-hari yang hangat, singkat, dan memotivasi.

KONTEKS USER HARI INI:
- Fase: {fase}
- Total belanja tercatat: Rp {session.total_spending:,}
- HPP per porsi: Rp {session.cogs_per_unit:,}
"""
    if fase == "MORNING_COSTING":
        return base_context + """
TUGASMU (FASE PAGI):
Bantu user mencatat belanjaan hari ini.
PENTING: Kamu hanya MENGEKSTRAK data mentah dari user.
JANGAN menghitung total — biarkan sistem backend yang menghitung.

Jika informasi kurang lengkap (tidak ada jumlah porsi, atau harga tidak jelas),
tanyakan dengan ramah dan spesifik sebelum melanjutkan.

Respons harus mencakup:
- Konfirmasi item yang berhasil dicatat
- Pertanyaan lanjutan jika ada yang kurang
- Motivasi singkat
"""
    else:
        return base_context + f"""
TUGASMU (FASE SORE):
User akan melaporkan jumlah yang terjual dan harga jualnya.
Modal hari ini sudah tercatat: Rp {session.total_spending:,}
HPP: Rp {session.cogs_per_unit:,} per porsi

JANGAN menghitung omzet/laba — biarkan backend yang menghitung.
Kamu hanya perlu mengekstrak: berapa yang laku dan harga jualnya.
"""


@router.post(
    "/",
    response_model=ChatResponse,
    summary="Send a chat message to the financial assistant",
)
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Main chat interaction endpoint (Unary).
    Fetches session from DB, extracts entities via Gemini, calculates metrics in Python.
    """
    user_id = current_user.id
    client_ip = request.client.host if request.client else "unknown"

    active_api_key = request.headers.get("X-Gemini-Key")
    from app.core.config import settings
    api_key = active_api_key or settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API Key is not configured on the server.",
        )

    # 1. Fetch the daily financial tracking session using session_id
    daily_session = await session_repository.get_session_by_id(
        db, body.session_id, user_id, load_messages=True
    )
    if not daily_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session tidak ditemukan",
        )

    logger.info(
        "chat_request_received",
        user_id=user_id,
        client_ip=client_ip,
        phase=daily_session.current_phase,
        session_id=daily_session.id,
    )

    # Ensure chat history only passes the latest messages to save token context
    chat_history = daily_session.messages[-8:] if daily_session.messages else []

    # 2. Build system instruction
    system_instruction = build_system_prompt(daily_session.current_phase, daily_session)

    # 3. Save User message to DB
    user_message = ChatMessage(
        session_id=daily_session.id,
        role="user",
        content=body.message,
    )
    db.add(user_message)
    await db.flush()

    # 4. Extract entities using Gemini
    extraction = await gemini_service.extract_entities(
        api_key=api_key,
        system_instruction=system_instruction,
        chat_history=chat_history,
        current_message=body.message,
    )

    intent = extraction.get("intent", "GENERAL_CHAT")
    needs_clarification = extraction.get("needs_clarification", False)

    # 5. Execute Python-based math calculation depending on Intent
    if intent == "RECORD_SPENDING" and not needs_clarification:
        metrics = FinancialCalculator.calculate_morning_metrics(
            items=extraction.get("items_extracted", []),
            servings=extraction.get("servings"),
            existing_total=daily_session.total_spending,
        )
        daily_session.total_spending = metrics["total_spending"]
        daily_session.used_capital = metrics["used_capital"]
        daily_session.cogs_per_unit = metrics["cogs_per_unit"]

        # Advance to Evening phase automatically if COGS is successfully computed
        if daily_session.cogs_per_unit > 0:
            daily_session.current_phase = "EVENING_SALES"

    elif intent == "RECORD_SALES" and not needs_clarification:
        metrics = FinancialCalculator.calculate_evening_metrics(
            units_sold=extraction.get("units_sold"),
            selling_price=extraction.get("selling_price"),
            cogs_per_unit=daily_session.cogs_per_unit,
            total_spending=daily_session.total_spending,
        )
        daily_session.total_revenue = metrics["total_revenue"]
        daily_session.net_profit = metrics["net_profit"]
        daily_session.portions_sold = metrics["portions_sold"]
        daily_session.selling_price = metrics["selling_price"]
        daily_session.break_even = metrics["break_even"]

    # 6. Save Assistant response to DB
    response_text = extraction.get("response_text", "Maaf, ada yang bisa saya bantu?")
    assistant_message = ChatMessage(
        session_id=daily_session.id,
        role="model",
        content=response_text,
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(daily_session)

    # 7. Return the updated Single Source of Truth to the client
    return ChatResponse(
        response=response_text,
        total_spending=daily_session.total_spending,
        used_capital=daily_session.used_capital,
        cogs_per_unit=daily_session.cogs_per_unit,
        current_phase=daily_session.current_phase,
        total_revenue=daily_session.total_revenue,
        net_profit=daily_session.net_profit,
        portions_sold=daily_session.portions_sold,
        selling_price=daily_session.selling_price,
        break_even=daily_session.break_even,
        is_correction=False,
        correction_summary=None,
    )

import json
import asyncio
from fastapi.responses import StreamingResponse

@router.post(
    "/stream",
    summary="Stream chat message response",
)
async def chat_stream_endpoint(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Streaming chat endpoint. Yields SSE events.
    """
    user_id = current_user.id
    daily_session = await session_repository.get_session_by_id(
        db, body.session_id, user_id, load_messages=True
    )
    if not daily_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session tidak ditemukan",
        )

    active_api_key = request.headers.get("X-Gemini-Key")
    from app.core.config import settings
    api_key = active_api_key or settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API Key is not configured on the server.",
        )

    # Save User message to DB
    user_message = ChatMessage(
        session_id=daily_session.id,
        role="user",
        content=body.message,
    )
    db.add(user_message)
    await db.commit()
    await db.refresh(daily_session)

    chat_history = daily_session.messages[-8:] if daily_session.messages else []
    system_instruction = build_system_prompt(daily_session.current_phase, daily_session)

    async def event_generator():
        yield f"data: {json.dumps({'type': 'thinking'})}\\n\\n"

        full_json_str = ""
        try:
            async for chunk in gemini_service.stream_extract_entities(
                api_key=api_key,
                system_instruction=system_instruction,
                chat_history=chat_history,
                current_message=body.message,
            ):
                full_json_str += chunk
                # Yield raw chunk for frontend to buffer if needed
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\\n\\n"
                await asyncio.sleep(0)
            
            # Now stream is done, parse full JSON
            try:
                extraction = json.loads(full_json_str)
            except json.JSONDecodeError:
                extraction = {"intent": "GENERAL_CHAT", "response_text": "Maaf, sistem tidak dapat memproses data."}
            
            # Calculate metrics
            intent = extraction.get("intent", "GENERAL_CHAT")
            needs_clarification = extraction.get("needs_clarification", False)

            if intent == "RECORD_SPENDING" and not needs_clarification:
                metrics = FinancialCalculator.calculate_morning_metrics(
                    items=extraction.get("items_extracted", []),
                    servings=extraction.get("servings"),
                    existing_total=daily_session.total_spending,
                )
                daily_session.total_spending = metrics["total_spending"]
                daily_session.used_capital = metrics["used_capital"]
                daily_session.cogs_per_unit = metrics["cogs_per_unit"]
                if daily_session.cogs_per_unit > 0:
                    daily_session.current_phase = "EVENING_SALES"

            elif intent == "RECORD_SALES" and not needs_clarification:
                metrics = FinancialCalculator.calculate_evening_metrics(
                    units_sold=extraction.get("units_sold"),
                    selling_price=extraction.get("selling_price"),
                    cogs_per_unit=daily_session.cogs_per_unit,
                    total_spending=daily_session.total_spending,
                )
                daily_session.total_revenue = metrics["total_revenue"]
                daily_session.net_profit = metrics["net_profit"]
                daily_session.portions_sold = metrics["portions_sold"]
                daily_session.selling_price = metrics["selling_price"]
                daily_session.break_even = metrics["break_even"]

            response_text = extraction.get("response_text", "Maaf, ada yang bisa saya bantu?")
            assistant_message = ChatMessage(
                session_id=daily_session.id,
                role="model",
                content=response_text,
            )
            db.add(assistant_message)
            await db.commit()
            await db.refresh(daily_session)

            final_state = {
                "response": response_text,
                "total_spending": daily_session.total_spending,
                "used_capital": daily_session.used_capital,
                "cogs_per_unit": daily_session.cogs_per_unit,
                "current_phase": daily_session.current_phase,
                "total_revenue": daily_session.total_revenue,
                "net_profit": daily_session.net_profit,
                "portions_sold": daily_session.portions_sold,
                "selling_price": daily_session.selling_price,
                "break_even": daily_session.break_even,
                "is_correction": False,
            }

            yield f"data: {json.dumps({'type': 'done', 'session_state': final_state})}\\n\\n"
        except Exception as e:
            logger.error("stream_error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\\n\\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
