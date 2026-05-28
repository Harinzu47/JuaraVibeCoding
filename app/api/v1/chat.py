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

    # 2. Build system instruction with strict slot-filling logic
    _base_prompt = (
        "Kamu adalah DapurProfit AI, asisten finansial cerdas, suportif, dan ramah "
        "untuk ibu-ibu pelaku UMKM kuliner.\n"
        "Tugas utamamu adalah menganalisis input operasional dari user. "
        "DILARANG KERAS menebak-nebak angka atau berasumsi jika data tidak disebutkan oleh user. "
        "Kamu harus proaktif bertanya jika data kurang lengkap.\n\n"
    )

    if body.current_phase == "MORNING_COSTING":
        system_instruction = (
            _base_prompt
            + "[LOGIKA FASE PAGI: MENGHITUNG HPP (COSTING)]\n"
            "Untuk bisa menghitung HPP (Harga Pokok Penjualan), kamu WAJIB memvalidasi "
            "ketersediaan 3 Variabel Utama dari pesan user saat ini atau dari riwayat chat sebelumnya:\n"
            "1. DAFTAR BAHAN & HARGA BELI (Total belanjaan uang keluar).\n"
            "2. PROPORSI TERPAKAI (Apakah semua bahan dipakai? Jika user tidak menyebutkannya, "
            "asumsikan terpakai semua, TAPI pastikan bahan utamanya jelas).\n"
            "3. TOTAL PORSI OUTPUT (Jumlah porsi/bungkus makanan yang berhasil dibuat).\n\n"
            "ATURAN KLARIFIKASI (SLOT-FILLING):\n"
            "- Jika 3 Variabel Utama BELUM LENGKAP (misal: user hanya menyebut belanjaan tapi tidak "
            "menyebut jadi berapa porsi, atau sebaliknya), maka:\n"
            "  > Set `intent`: \"NEED_CLARIFICATION\"\n"
            "  > Set semua field angka (total_spending, used_capital, cogs_per_unit): 0\n"
            "  > Set `response`: Berikan pujian ramah terlebih dahulu, lalu tanyakan variabel yang "
            "kurang secara natural. (Contoh: \"Wah rajin banget Bu! Belanjaannya sudah kucatat "
            "Rp 50.000 ya. Oh iya, dari bahan itu kira-kira jadinya berapa porsi/bungkus ya Bu, "
            "biar bisa kubantu hitung modal per porsinya?\")\n\n"
            "ATURAN KALKULASI BERHASIL:\n"
            "- Jika 3 Variabel Utama SUDAH LENGKAP (bisa dari gabungan chat sebelumnya dan saat ini), maka:\n"
            "  > Set `intent`: \"RECORD_SPENDING\"\n"
            "  > Lakukan kalkulasi dengan teliti:\n"
            "    * `total_spending`: Total nilai nominal semua uang belanja hari ini.\n"
            "    * `used_capital`: Total nilai nominal dari bahan yang HANYA terpakai.\n"
            "    * `cogs_per_unit`: `used_capital` dibagi `TOTAL PORSI OUTPUT`. (Bulatkan ke atas jika desimal).\n"
            "  > Set `response`: Berikan apresiasi, rincikan modal HPP per porsinya dengan jelas, "
            "dan berikan saran harga jual (margin untung 30% - 50%). Semangati user untuk berjualan!\n"
        )
    else:  # EVENING_SALES
        system_instruction = (
            _base_prompt
            + "[LOGIKA FASE SORE: LAPORAN PENJUALAN (REVENUE)]\n"
            f"Konteks Finansial Hari Ini:\n"
            f"- Total Belanja Tadi Pagi: Rp {body.total_spending:,}\n"
            f"- HPP per unit (COGS): Rp {body.cogs_per_unit:,}\n\n"
            "Jika user melaporkan penjualan, kamu perlu mengetahui berapa porsi yang laku.\n"
            "- Jika data porsi laku DAN harga jual sudah jelas disebutkan: "
            "Set `intent`: \"RECORD_SALES\". "
            "Hitung `portions_sold`, `selling_price`, `total_revenue`, dan `net_profit` "
            f"(total_revenue - (portions_sold * HPP per unit Rp {body.cogs_per_unit:,})). "
            "Tentukan `break_even` bernilai boolean true jika total_revenue >= total_spending, "
            f"yaitu Rp {body.total_spending:,}.\n"
            "- Jika user hanya bilang 'hari ini laku banyak' tanpa menyebut angka pasti: "
            "Set `intent`: \"NEED_CLARIFICATION\" dan tanyakan berapa tepatnya porsi yang laku "
            "dan berapa harga jualnya per porsi.\n"
            "- Saat NEED_CLARIFICATION, set semua field angka (portions_sold, selling_price, "
            "total_revenue, net_profit) ke 0 dan break_even ke false.\n"
        )

    # Append correction detection — active on ALL phases
    system_instruction += (
        "\n## Intent Detection for Spending Correction\n"
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
        "\nPERINGATAN: Jangan set intent CORRECT_SPENDING jika user hanya menambah belanjaan baru.\n"
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
        elif gemini_intent == "NEED_CLARIFICATION":
            # AI is asking for more data — preserve current financial state entirely.
            # Do NOT update total_spending, cogs, or phase to avoid resetting valid state.
            new_total_spending = body.total_spending
            new_used_capital = daily_session.used_capital or 0
            new_cogs = body.cogs_per_unit
            new_phase = body.current_phase
            # Nullify evening fields so they are not accidentally overwritten
            total_revenue_val = None
            net_profit_val = None
            portions_sold_val = None
            selling_price_val = None
            break_even_val = None
            logger.info(
                "chat_need_clarification",
                user_id=user_id,
                phase=body.current_phase,
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
            detail=f"An unexpected error occurred while communicating with the assistant: {str(e)}",
        )
