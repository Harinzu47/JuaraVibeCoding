from fastapi import APIRouter, Depends, HTTPException, status as http_status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, DailySession
from auth import get_current_user
from schemas import DailySessionResponse, SessionWithHistoryResponse
from datetime import date

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _session_to_dict(session: DailySession, include_messages: bool = False) -> dict:
    """
    Konversi ORM DailySession ke dict — dilakukan DALAM greenlet async agar
    tidak terjadi MissingGreenlet saat serialisasi Pydantic di luar context.
    """
    d = {
        "id": session.id,
        "session_date": session.session_date,
        "fase_saat_ini": session.fase_saat_ini,
        "total_belanja": session.total_belanja,
        "modal_terpakai": session.modal_terpakai,
        "hpp_unit": session.hpp_unit,
        "total_pendapatan": session.total_pendapatan,
        "laba_bersih": session.laba_bersih,
        "porsi_terjual": session.porsi_terjual,
        "harga_jual": session.harga_jual,
        "balik_modal": session.balik_modal,
    }
    if include_messages:
        d["messages"] = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat() if m.created_at else "",
            }
            for m in (session.messages or [])
        ]
    return d


@router.get(
    "/",
    response_model=list[DailySessionResponse],
    summary="Riwayat semua sesi harian",
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ambil semua sesi harian milik user, diurutkan terbaru dulu."""
    result = await db.execute(
        select(DailySession)
        .where(DailySession.user_id == current_user.id)
        .order_by(desc(DailySession.session_date))
    )
    sessions = result.scalars().all()
    # Konversi ke dict DALAM greenlet
    return [_session_to_dict(s) for s in sessions]


@router.get(
    "/today",
    response_model=SessionWithHistoryResponse,
    summary="Sesi hari ini (buat baru jika belum ada)",
)
async def get_today_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ambil sesi hari ini lengkap dengan chat history. Buat baru jika belum ada."""
    today = date.today()
    result = await db.execute(
        select(DailySession)
        .options(selectinload(DailySession.messages))
        .where(DailySession.user_id == current_user.id)
        .where(DailySession.session_date == today)
    )
    session = result.scalar_one_or_none()

    if not session:
        session = DailySession(user_id=current_user.id, session_date=today)
        db.add(session)
        await db.commit()
        # Jangan refresh lalu akses relationship — langsung bangun dict dengan messages kosong
        result_dict = _session_to_dict(session, include_messages=False)
        result_dict["messages"] = []
        return result_dict

    # Konversi ke dict DALAM greenlet sebelum keluar scope async
    return _session_to_dict(session, include_messages=True)


@router.delete(
    "/today",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Reset sesi hari ini (idempotent)",
)
async def reset_today_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hapus seluruh data sesi hari ini: pesan dan state finansial.
    Chat messages terhapus otomatis via CASCADE (FK + relationship cascade).
    Mengembalikan 204 meski session tidak ada — idempotent.
    """
    today = date.today()
    result = await db.execute(
        select(DailySession)
        .where(DailySession.user_id == current_user.id)
        .where(DailySession.session_date == today)
    )
    session = result.scalar_one_or_none()
    if session:
        await db.delete(session)
        await db.commit()
    # Kembalikan 204 meski tidak ada session (idempotent)


@router.get(
    "/{session_date}",
    response_model=SessionWithHistoryResponse,
    summary="Sesi untuk tanggal tertentu (YYYY-MM-DD)",
)
async def get_session_by_date(
    session_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ambil sesi untuk tanggal tertentu beserta chat history-nya."""
    result = await db.execute(
        select(DailySession)
        .options(selectinload(DailySession.messages))
        .where(DailySession.user_id == current_user.id)
        .where(DailySession.session_date == session_date)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Tidak ada sesi untuk tanggal {session_date}.",
        )
    return _session_to_dict(session, include_messages=True)
