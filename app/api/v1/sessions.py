from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.session import session_repository
from app.schemas.chat import ChatMessageResponse
from app.schemas.session import (DailySessionResponse,
                                 SessionWithHistoryResponse)
from app.services.pdf import pdf_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get(
    "/",
    response_model=list[DailySessionResponse],
    summary="List all daily sessions for the current user",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve all financial daily sessions for the authenticated user, newest first."""
    sessions = await session_repository.list_by_user(db, current_user.id)
    return [DailySessionResponse.model_validate(s) for s in sessions]


@router.get(
    "/today",
    response_model=SessionWithHistoryResponse,
    summary="Get today's session, creating one if not exists",
)
async def get_today_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch today's financial tracking session along with conversation history."""
    session = await session_repository.get_or_create_today_session(db, current_user.id)
    try:
        messages = [ChatMessageResponse.from_orm_model(m) for m in session.messages]
    except Exception:
        messages = []
    base_resp = DailySessionResponse.model_validate(session)
    resp = SessionWithHistoryResponse(**base_resp.model_dump(), messages=messages)

    await db.commit()  # Persist new session creation if it occurred
    return resp


@router.delete(
    "/today",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Reset/delete today's session (idempotent)",
)
async def reset_today_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Delete today's session data and associated message history. Idempotent operation."""
    today = date.today()
    session = await session_repository.get_by_date(db, current_user.id, today)
    if session:
        await session_repository.delete(db, session)
        await db.commit()


@router.get(
    "/{session_date}",
    response_model=SessionWithHistoryResponse,
    summary="Get session details for a specific date (YYYY-MM-DD)",
)
async def get_session_by_date(
    session_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Fetch the daily session and chat logs for the specified date."""
    session = await session_repository.get_by_date(
        db, current_user.id, session_date, load_messages=True
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No session found for date {session_date}.",
        )

    messages = [ChatMessageResponse.from_orm_model(m) for m in (session.messages or [])]

    resp = SessionWithHistoryResponse.model_validate(session)
    resp.messages = messages
    return resp


@router.get(
    "/{session_date}/pdf",
    response_class=Response,
    summary="Download daily financial report as PDF",
)
async def export_session_pdf(
    session_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate and return a PDF daily report for the specified date."""
    session = await session_repository.get_by_date(
        db, current_user.id, session_date, load_messages=True
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No session found for date {session_date}.",
        )

    try:
        pdf_bytes = await pdf_service.generate_session_pdf(session, current_user.email)
    except Exception as e:
        logger.error("pdf_export_failed", session_id=session.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF report. Please try again.",
        )

    filename = f"daily-report-aturmodal-{session_date}.pdf"
    logger.info("pdf_exported", user_id=current_user.id, session_date=str(session_date))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/export/csv",
    summary="Download daily financial sessions as CSV",
)
async def export_sessions_csv(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """Generate and return a CSV file containing all financial sessions for the user."""
    import csv
    import io

    sessions = await session_repository.list_by_user(db, current_user.id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Tanggal", "Total Belanja", "Modal Terpakai", "HPP per Unit", 
        "Total Pendapatan", "Laba Bersih", "Porsi Terjual", "Harga Jual", "Balik Modal"
    ])
    
    for s in sessions:
        writer.writerow([
            s.session_date,
            s.total_spending,
            s.used_capital,
            s.cogs_per_unit,
            s.total_revenue or 0,
            s.net_profit or 0,
            s.portions_sold or 0,
            s.selling_price or 0,
            "Ya" if s.break_even else "Tidak"
        ])
    
    filename = f"aturmodal_riwayat_{date.today()}.csv"
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
