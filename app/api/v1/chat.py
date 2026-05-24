import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.repositories.message import message_repository
from app.repositories.session import session_repository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.gemini import gemini_service

logger = structlog.get_logger()
router = APIRouter(prefix="/api/chat", tags=["chat"])


def apply_spending_correction(
    current_total_spending: int,
    current_cogs_per_unit: int,
    portions_made: int,
    old_price: int,
    new_price: int,
) -> tuple[int, int]:
    """Calculate the updated total spending and COGS after correcting an item's price."""
    diff = new_price - old_price
    new_total_spending = max(0, current_total_spending + diff)

    if portions_made > 0:
        new_cogs = new_total_spending // portions_made
    else:
        new_cogs = current_cogs_per_unit

    return new_total_spending, new_cogs


def calculate_morning_metrics(
    raw_total_spending: int | None,
    raw_used_capital: int | None,
    raw_cogs_per_unit: int | None,
    current_total_spending: int,
    current_cogs_per_unit: int,
) -> tuple[int, int, int, str]:
    """Validate and clamp financial inputs for the morning phase, returning updated values."""
    new_total_spending = current_total_spending
    new_used_capital = 0
    new_cogs = current_cogs_per_unit
    new_phase = "MORNING_COSTING"

    if raw_total_spending is not None:
        new_total_spending = max(0, int(raw_total_spending))
    if raw_used_capital is not None:
        new_used_capital = max(0, int(raw_used_capital))
        # Clamping used capital to not exceed total spending
        new_used_capital = min(new_used_capital, new_total_spending)
    if raw_cogs_per_unit is not None:
        new_cogs = max(0, int(raw_cogs_per_unit))

    # Transition to evening sales phase only if COGS is successfully computed
    if new_cogs > 0:
        new_phase = "EVENING_SALES"

    return new_total_spending, new_used_capital, new_cogs, new_phase


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
    Main chat interaction endpoint.
    Maintains financial state, runs intent checks, and calculates COGS / profits.
    """
    user_id = current_user.id
    client_ip = request.client.host if request.client else "unknown"

    active_api_key = request.headers.get("X-Gemini-Key")
    # Let's resolve the API key securely. We look at header first, then settings
    from app.core.config import settings

    api_key = active_api_key or settings.GEMINI_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API Key is not configured on the server.",
        )

    logger.info(
        "chat_request_received",
        user_id=user_id,
        client_ip=client_ip,
        phase=body.current_phase,
        model=gemini_service.active_model,
    )

    # 1. Fetch or create the daily financial tracking session
    daily_session = await session_repository.get_or_create_today_session(db, user_id)

    # 2. Formulate the system instruction prompt
    if body.current_phase == "MORNING_COSTING":
        system_instruction = (
            "Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
            "User akan menginput bahan belanjaan dan jumlah porsi masakan yang dibuat.\n"
            "Tugasmu:\n"
            "1. Hitung 'total_spending' (semua uang keluar).\n"
            "2. Hitung 'used_capital' (hanya nilai bahan yang benar-benar jadi makanan/terpakai).\n"
            "3. Hitung 'cogs_per_unit' (used_capital / jumlah porsi).\n"
            "4. Berikan saran harga jual (margin 30%-50%).\n"
            "Isi field 'response' dengan balasan bahasa Indonesia sehari-hari yang ramah, hangat, dan memotivasi. "
            "Tentukan nilai 'total_spending', 'used_capital', dan 'cogs_per_unit' secara akurat."
        )
    else:  # EVENING_SALES
        system_instruction = (
            f"Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
            f"User akan melaporkan berapa jumlah makanan yang laku terjual dan berapa harga jual per porsinya.\n"
            f"Konteks Finansial Hari Ini:\n"
            f"- Total Belanja Tadi Pagi: Rp {body.total_spending:,}\n"
            f"- HPP per unit (COGS): Rp {body.cogs_per_unit:,}\n"
            f"Tugasmu:\n"
            f"1. Hitung 'total_revenue' (jumlah laku x harga jual).\n"
            f"2. Hitung 'net_profit' (total_revenue - (jumlah laku x COGS)).\n"
            f"3. Evaluasi apakah total_revenue >= total_spending pagi (break_even).\n"
            f"Isi field 'response' dengan balasan bahasa Indonesia yang antusias, ramah, dan berikan rincian laba. "
            f"Tentukan nilai 'portions_sold', 'selling_price', 'total_revenue', 'net_profit', dan 'break_even' secara akurat."
        )

    # Inject intent check for correction
    system_instruction += (
        "\n\n## Intent Detection for Spending Correction\n"
        "Jika user menyebut bahwa data belanja sebelumnya salah dan ingin dikoreksi "
        "(contoh: 'eh tadi salah', 'ralat', 'harusnya', 'bukan segitu', 'koreksi'), "
        "maka:\n"
        "- Tetapkan intent = 'CORRECT_SPENDING'\n"
        "- Isi 'correction_item' dengan nama bahan yang dikoreksi (huruf kecil, tanpa satuan)\n"
        "- Isi 'correction_old_price' dengan harga yang salah (integer Rupiah)\n"
        "- Isi 'correction_new_price' dengan harga yang benar (integer Rupiah)\n"
        "- Jika user hanya menyebut harga baru tanpa harga lama, isi correction_old_price = 0\n"
        "\nContoh:\n"
        "User: 'tadi ayam saya tulis 40rb, sebenarnya cuma 35rb'\n"
        "→ intent: 'CORRECT_SPENDING', correction_item: 'ayam', "
        "correction_old_price: 40000, correction_new_price: 35000\n"
    )

    try:
        # 3. Call the Gemini service with fallback mechanism
        data = await gemini_service.generate_content(
            api_key=api_key,
            system_instruction=system_instruction,
            chat_history=body.chat_history,
            message=body.message,
        )

        # 4. Extract outputs and compute formulas
        new_total_spending = body.total_spending
        new_used_capital = 0
        new_cogs = body.cogs_per_unit
        new_phase = body.current_phase

        total_revenue_val = data.get("total_revenue")
        net_profit_val = data.get("net_profit")
        portions_sold_val = data.get("portions_sold")
        selling_price_val = data.get("selling_price")
        break_even_val = data.get("break_even")

        gemini_intent = data.get("intent", "OTHER")
        is_correction = gemini_intent == "CORRECT_SPENDING"
        correction_summary = None

        if is_correction:
            correction_item = data.get("correction_item", "")
            old_price = int(data.get("correction_old_price") or 0)
            new_price = int(data.get("correction_new_price") or 0)

            # Use client body state or DB session state
            current_spending = body.total_spending or daily_session.total_spending
            current_cogs = body.cogs_per_unit or daily_session.cogs_per_unit
            current_used_capital = daily_session.used_capital or current_spending

            # Estimate portions made if not directly set
            portions_made = daily_session.portions_sold or 0
            if portions_made == 0 and current_cogs > 0:
                portions_made = current_used_capital // current_cogs

            new_total_spending, new_cogs = apply_spending_correction(
                current_total_spending=current_spending,
                current_cogs_per_unit=current_cogs,
                portions_made=portions_made,
                old_price=old_price,
                new_price=new_price,
            )

            if correction_item:
                correction_summary = (
                    f"Harga {correction_item} dikoreksi: "
                    f"Rp {old_price:,.0f} → Rp {new_price:,.0f}".replace(",", ".")
                )

            logger.info(
                "spending_correction_applied",
                user_id=user_id,
                item=correction_item,
                old_price=old_price,
                new_price=new_price,
                total_spending_after=new_total_spending,
                cogs_after=new_cogs,
            )
        elif body.current_phase == "MORNING_COSTING":
            (
                new_total_spending,
                new_used_capital,
                new_cogs,
                new_phase,
            ) = calculate_morning_metrics(
                raw_total_spending=data.get("total_spending"),
                raw_used_capital=data.get("used_capital"),
                raw_cogs_per_unit=data.get("cogs_per_unit"),
                current_total_spending=body.total_spending,
                current_cogs_per_unit=body.cogs_per_unit,
            )
        else:  # EVENING_SALES
            if portions_sold_val is not None:
                portions_sold_val = max(0, int(portions_sold_val))
            if selling_price_val is not None:
                selling_price_val = max(0, int(selling_price_val))
            if total_revenue_val is not None:
                total_revenue_val = max(0, int(total_revenue_val))
            if net_profit_val is not None:
                net_profit_val = int(net_profit_val)
            if break_even_val is None and total_revenue_val is not None:
                break_even_val = total_revenue_val >= new_total_spending

        # 5. Save chat log & update session state in the database
        await message_repository.create_message(
            db, daily_session.id, "user", body.message
        )
        await message_repository.create_message(
            db, daily_session.id, "assistant", data.get("response", "")
        )

        daily_session.current_phase = new_phase
        daily_session.total_spending = new_total_spending
        daily_session.used_capital = new_used_capital
        daily_session.cogs_per_unit = new_cogs

        if body.current_phase == "EVENING_SALES":
            daily_session.total_revenue = total_revenue_val
            daily_session.net_profit = net_profit_val
            daily_session.portions_sold = portions_sold_val
            daily_session.selling_price = selling_price_val
            daily_session.break_even = break_even_val

        await db.commit()

        logger.info(
            "chat_request_success",
            user_id=user_id,
            phase=body.current_phase,
            new_phase=new_phase,
            cogs_per_unit=new_cogs,
        )

        return ChatResponse(
            response=data.get("response", ""),
            total_spending=new_total_spending,
            used_capital=new_used_capital,
            cogs_per_unit=new_cogs,
            current_phase=new_phase,
            total_revenue=total_revenue_val,
            net_profit=net_profit_val,
            portions_sold=portions_sold_val,
            selling_price=selling_price_val,
            break_even=break_even_val,
            is_correction=is_correction,
            correction_summary=correction_summary,
        )

    except TimeoutError as e:
        logger.error("chat_request_timeout", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="AI took too long to respond. Please try sending your message again.",
        )
    except ValueError as e:
        logger.error("chat_request_value_error", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process calculation outputs: {str(e)}",
        )
    except Exception as e:
        await db.rollback()
        logger.error("chat_request_failed", user_id=user_id, error=str(e))

        # Check quota-related error strings
        err_msg = str(e).lower()
        if "quota" in err_msg or "resource_exhausted" in err_msg or "429" in err_msg:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Google AI studio quota has been exhausted. Please try again later.",
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while communicating with the assistant.",
        )
