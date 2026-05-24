from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database import get_db
from models import User, DailySession
from auth import get_current_user
from jinja2 import Environment, FileSystemLoader
from datetime import date, datetime, timezone
import asyncio
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/sessions", tags=["export"])

# Inisialisasi Jinja2 — cari template di folder templates/
jinja_env = Environment(loader=FileSystemLoader("templates"), autoescape=True)


def format_rupiah(value: int | None) -> str:
    """Format integer ke string Rupiah. None ditampilkan sebagai '-'."""
    if value is None:
        return "-"
    return "Rp " + f"{value:,}".replace(",", ".")


def render_pdf_sync(html_string: str) -> bytes:
    """Render HTML ke PDF bytes. Dijalankan di thread pool agar tidak blokir event loop."""
    from weasyprint import HTML as WeasyHTML
    return WeasyHTML(string=html_string).write_pdf()


@router.get("/{session_date}/pdf", response_class=Response)
async def export_session_pdf(
    session_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate dan download laporan harian dalam format PDF.
    Hanya bisa mengakses sesi milik user yang sedang login.
    """
    # Ambil session dan messages dari DB
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
            detail=f"Tidak ada sesi untuk tanggal {session_date}."
        )

    # Format data untuk template — dilakukan di dalam greenlet
    generated_at = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
    session_date_str = session_date.strftime("%d %B %Y")
    has_revenue_data = session.total_pendapatan is not None

    messages_formatted = [
        {
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%H:%M") if msg.created_at else "",
        }
        for msg in (session.messages or [])
    ]

    # Snapshot semua data sebelum keluar scope DB
    session_data = {
        "session_id": session.id,
        "total_belanja": session.total_belanja,
        "modal_terpakai": session.modal_terpakai,
        "hpp_unit": session.hpp_unit,
        "total_pendapatan": session.total_pendapatan,
        "laba_bersih": session.laba_bersih,
        "porsi_terjual": session.porsi_terjual,
        "harga_jual": session.harga_jual,
        "balik_modal": session.balik_modal,
    }

    # Render template Jinja2 ke HTML string
    template = jinja_env.get_template("laporan_harian.html")
    html_string = template.render(
        session_date=session_date_str,
        generated_at=generated_at,
        user_email=current_user.email,
        total_belanja=format_rupiah(session_data["total_belanja"]),
        modal_terpakai=format_rupiah(session_data["modal_terpakai"]),
        hpp_unit=format_rupiah(session_data["hpp_unit"]),
        has_revenue_data=has_revenue_data,
        porsi_terjual=session_data["porsi_terjual"] or 0,
        harga_jual=format_rupiah(session_data["harga_jual"]),
        total_pendapatan=format_rupiah(session_data["total_pendapatan"]),
        laba_bersih=format_rupiah(session_data["laba_bersih"]),
        laba_bersih_raw=session_data["laba_bersih"] or 0,
        balik_modal=session_data["balik_modal"] or False,
        messages=messages_formatted,
    )

    # Render PDF di thread pool — WeasyPrint adalah sync I/O
    try:
        pdf_bytes = await asyncio.to_thread(render_pdf_sync, html_string)
    except Exception as e:
        logger.error("pdf_render_failed", session_id=session_data["session_id"], error=str(e))
        raise HTTPException(status_code=500, detail="Gagal membuat PDF. Coba lagi.")

    filename = f"laporan-dapurprofit-{session_date}.pdf"
    logger.info("pdf_exported", user_id=current_user.id, session_date=str(session_date))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
