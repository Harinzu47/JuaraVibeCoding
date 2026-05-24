import asyncio
import logging
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader

from app.models.session import DailySession

logger = logging.getLogger("app.pdf")


class PDFService:
    """Service to handle Jinja2 HTML rendering and conversion to PDF using WeasyPrint."""

    def __init__(self):
        # Initialize Jinja2 environment looking for templates folder
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates"), autoescape=True
        )

    @staticmethod
    def format_rupiah(value: int | None) -> str:
        """Format an integer value to a Rupiah string format."""
        if value is None:
            return "-"
        return "Rp " + f"{value:,}".replace(",", ".")

    @staticmethod
    def _render_pdf_sync(html_string: str) -> bytes:
        """Synchronously render HTML string to PDF bytes using WeasyPrint."""
        from weasyprint import HTML as WeasyHTML  # type: ignore

        return WeasyHTML(string=html_string).write_pdf()

    async def generate_session_pdf(
        self, session: DailySession, user_email: str
    ) -> bytes:
        """
        Prepare daily session data, render HTML using Jinja2,
        and generate PDF bytes in a thread pool.
        """
        generated_at = datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC")
        session_date_str = session.session_date.strftime("%d %B %Y")
        has_revenue_data = session.total_revenue is not None

        # Format chat history for the template
        messages_formatted = [
            {
                "role": msg.role,
                "content": msg.content,
                "created_at": (
                    msg.created_at.strftime("%H:%M") if msg.created_at else ""
                ),
            }
            for msg in (session.messages or [])
        ]

        # Render HTML string via Jinja2 template
        template = self.jinja_env.get_template("laporan_harian.html")
        html_string = template.render(
            session_date=session_date_str,
            generated_at=generated_at,
            user_email=user_email,
            # Map database English columns to Indonesian variables expected by the HTML template
            total_belanja=self.format_rupiah(session.total_spending),
            modal_terpakai=self.format_rupiah(session.used_capital),
            hpp_unit=self.format_rupiah(session.cogs_per_unit),
            has_revenue_data=has_revenue_data,
            porsi_terjual=session.portions_sold or 0,
            harga_jual=self.format_rupiah(session.selling_price),
            total_pendapatan=self.format_rupiah(session.total_revenue),
            laba_bersih=self.format_rupiah(session.net_profit),
            laba_bersih_raw=session.net_profit or 0,
            balik_modal=session.break_even or False,
            messages=messages_formatted,
        )

        # Offload CPU-heavy WeasyPrint render task to a thread pool
        try:
            return await asyncio.to_thread(self._render_pdf_sync, html_string)
        except Exception as e:
            logger.error(f"Error during WeasyPrint rendering: {e}")
            raise e


pdf_service = PDFService()
