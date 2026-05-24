import asyncio
import json
import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import date

import structlog
import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from google.genai import types
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database import get_db
from models import User, DailySession, ChatMessage
from auth import get_current_user
from routers import auth_router, session_router, export_router

# =====================================================================
# LOAD ENVIRONMENT VARIABLES
# =====================================================================
if os.path.exists(".env"):
    try:
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        os.environ[parts[0].strip()] = parts[1].strip()
    except Exception as e:
        print(f"Gagal memuat file .env: {e}")

# =====================================================================
# STRUCTURED LOGGING (structlog)
# =====================================================================
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

# =====================================================================
# S3-01: MODEL FALLBACK CHAIN
# =====================================================================
# Model preference chain — dicoba dari indeks 0, fallback ke berikutnya.
GEMINI_MODEL_CHAIN = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-flash-lite-latest",
]

# Variabel global yang di-set saat lifespan startup
active_gemini_model: str = GEMINI_MODEL_CHAIN[-1]  # default fallback

# =====================================================================
# S3-02: TIMEOUT CONFIGURATION
# =====================================================================
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("GEMINI_TIMEOUT_SECONDS", "30"))

# =====================================================================
# REDIS RATE LIMITING
# =====================================================================
redis_client: aioredis.Redis | None = None

RATE_LIMIT_MAX = 45
RATE_LIMIT_WINDOW = 60  # seconds


# =====================================================================
# S3-01: AUTO-DETECT MODEL
# =====================================================================
async def detect_available_model(api_key: str) -> str:
    """
    Mencoba setiap model di GEMINI_MODEL_CHAIN secara berurutan.
    Mengembalikan nama model pertama yang berhasil merespons.
    Menggunakan asyncio.to_thread agar tidak memblokir event loop.
    Raise RuntimeError jika semua model gagal.
    """
    client = genai.Client(api_key=api_key)

    for model_name in GEMINI_MODEL_CHAIN:
        try:
            # Gunakan asyncio.to_thread untuk probe ringan — tidak blokir event loop
            await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=model_name,
                    contents="ping",
                    config=types.GenerateContentConfig(
                        max_output_tokens=1,
                    ),
                ),
                timeout=10.0,  # timeout probe lebih singkat
            )
            logger.info("gemini_model_selected", model=model_name)
            return model_name
        except asyncio.TimeoutError:
            logger.warning("gemini_model_unavailable", model=model_name, reason="probe timeout")
            continue
        except Exception as e:
            logger.warning("gemini_model_unavailable", model=model_name, reason=str(e)[:120])
            continue

    raise RuntimeError(
        f"Semua model Gemini tidak tersedia: {GEMINI_MODEL_CHAIN}. "
        "Periksa API key dan quota."
    )


# =====================================================================
# LIFESPAN — startup + shutdown
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, active_gemini_model

    # Init Redis
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    try:
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        await redis_client.ping()
        logger.info("app_startup", redis_available=True)
    except Exception as e:
        print(f"WARNING: Redis tidak tersedia ({e}). Rate limiting dinonaktifkan.")
        redis_client = None
        logger.info("app_startup", redis_available=False)

    # S3-01: Auto-detect model Gemini terbaik yang tersedia
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            active_gemini_model = await detect_available_model(api_key)
        except RuntimeError as e:
            logger.error("gemini_model_detection_failed", error=str(e))
            # Tetap pakai fallback default — error muncul saat request pertama
    else:
        logger.warning("gemini_api_key_missing_at_startup")

    logger.info("app_startup_complete", active_model=active_gemini_model)

    yield

    # Graceful shutdown — Cloud Run kirim SIGTERM
    logger.info("app_shutdown_initiated")
    if redis_client:
        await redis_client.aclose()
    logger.info("app_shutdown_complete")


async def check_rate_limit(client_ip: str) -> bool:
    """
    Returns True if request is allowed, False if rate limit exceeded.
    Uses Redis sliding window. Fails open if Redis is unavailable.
    """
    if redis_client is None:
        return True

    key = f"rate_limit:{client_ip}"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    try:
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, RATE_LIMIT_WINDOW)
        results = await pipe.execute()
        request_count = results[2]
        return request_count <= RATE_LIMIT_MAX
    except Exception as e:
        print(f"WARNING: Gagal cek rate limit ({e}). Menggunakan fail-open.")
        return True


# =====================================================================
# FASTAPI APP
# =====================================================================
app = FastAPI(title="DapurProfit AI API", version="3.0.0", lifespan=lifespan)

app.include_router(auth_router.router)
app.include_router(session_router.router)
app.include_router(export_router.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8081",
        "http://localhost:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# DATA MODELS
# =====================================================================
class ChatMessageSchema(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessageSchema]
    fase_saat_ini: str
    total_belanja: int
    hpp_unit: int


class ChatResponse(BaseModel):
    response: str
    total_belanja: int
    modal_terpakai: int
    hpp_unit: int
    fase_saat_ini: str
    total_pendapatan: int | None = None
    laba_bersih: int | None = None
    porsi_terjual: int | None = None
    harga_jual: int | None = None
    balik_modal: bool | None = None
    is_koreksi: bool = False
    koreksi_summary: str | None = None


# =====================================================================
# S3-05: HEALTH CHECK FINAL (akan diupdate di S3-05)
# =====================================================================
@app.get("/api/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db)):
    """Diagnostic endpoint: status semua komponen sistem."""
    redis_ok = False
    db_ok = False
    db_latency_ms = None

    if redis_client:
        try:
            await redis_client.ping()
            redis_ok = True
        except Exception:
            pass

    try:
        t0 = time.monotonic()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        db_ok = True
    except Exception:
        pass

    gemini_ok = bool(os.environ.get("GEMINI_API_KEY"))
    all_ok = gemini_ok and db_ok
    overall = "ok" if all_ok else "degraded"

    return {
        "status": overall,
        "version": "3.0.0",
        "components": {
            "gemini": {
                "configured": gemini_ok,
                "active_model": active_gemini_model,
            },
            "redis": {
                "connected": redis_ok,
                "note": "Rate limiting inactive" if not redis_ok else None,
            },
            "database": {
                "connected": db_ok,
                "latency_ms": db_latency_ms,
            },
        },
    }


# =====================================================================
# S3-05: READINESS PROBE
# =====================================================================
@app.get("/api/ready", tags=["system"])
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe untuk Cloud Run / load balancer.
    200 = siap melayani traffic. 503 = belum siap.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database tidak siap.")

    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(status_code=503, detail="Gemini API key belum dikonfigurasi.")

    return {"ready": True, "active_model": active_gemini_model}


# =====================================================================
# S4-01: FUNGSI KOREKSI BELANJA
# =====================================================================
def apply_koreksi_belanja(
    current_total_belanja: int,
    current_hpp_unit: int,
    porsi_dibuat: int,
    harga_lama: int,
    harga_baru: int,
) -> tuple[int, int]:
    """
    Menghitung ulang total_belanja dan hpp_unit setelah koreksi satu item.

    Args:
        current_total_belanja: total belanja sebelum koreksi (Rupiah)
        current_hpp_unit: HPP per porsi sebelum koreksi (Rupiah)
        porsi_dibuat: jumlah porsi yang dibuat hari ini
        harga_lama: harga item yang salah (Rupiah)
        harga_baru: harga item yang benar (Rupiah)

    Returns:
        Tuple (new_total_belanja, new_hpp_unit)
    """
    selisih = harga_baru - harga_lama
    new_total_belanja = max(0, current_total_belanja + selisih)

    if porsi_dibuat > 0:
        new_hpp_unit = new_total_belanja // porsi_dibuat
    else:
        # Porsi belum dicatat — HPP belum bisa dihitung, pertahankan nilai lama
        new_hpp_unit = current_hpp_unit

    return new_total_belanja, new_hpp_unit


def calculate_pagi_metrics(
    raw_total_belanja: int | None,
    raw_modal_terpakai: int | None,
    raw_hpp_unit: int | None,
    current_total_belanja: int,
    current_hpp_unit: int,
) -> tuple[int, int, int, str]:
    """
    Validasi dan kalkulasi metrics fase pagi.
    Returns: (total_belanja, modal_terpakai, hpp_unit, new_fase)
    """
    new_total_belanja = current_total_belanja
    new_modal_terpakai = 0
    new_hpp_unit = current_hpp_unit
    new_fase = "PAGI_COSTING"

    if raw_total_belanja is not None:
        new_total_belanja = max(0, int(raw_total_belanja))
    if raw_modal_terpakai is not None:
        new_modal_terpakai = max(0, int(raw_modal_terpakai))
        new_modal_terpakai = min(new_modal_terpakai, new_total_belanja)
    if raw_hpp_unit is not None:
        new_hpp_unit = max(0, int(raw_hpp_unit))

    if new_hpp_unit > 0:
        new_fase = "SORE_REVENUE"

    return new_total_belanja, new_modal_terpakai, new_hpp_unit, new_fase


# =====================================================================
# CHAT ENDPOINT — S3-01 (active_gemini_model) + S3-02 (async + timeout)
# =====================================================================
@app.post("/api/chat", response_model=ChatResponse, tags=["chat"])
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    user_id = current_user.id

    # Rate limiting
    if not await check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Terlalu banyak pesan dalam 1 menit. Silakan tunggu sebentar ya, Bu!",
        )

    active_api_key = os.environ.get("GEMINI_API_KEY")
    if not active_api_key:
        raise HTTPException(
            status_code=503,
            detail="Server tidak terkonfigurasi dengan benar. Hubungi administrator.",
        )

    logger.info(
        "chat_request_received",
        user_id=user_id,
        client_ip=client_ip,
        fase=body.fase_saat_ini,
        model=active_gemini_model,
        message_length=len(body.message),
    )

    # ------------------------------------------------------------------
    # Ambil atau buat DailySession untuk hari ini
    # ------------------------------------------------------------------
    today = date.today()
    session_result = await db.execute(
        select(DailySession)
        .options(selectinload(DailySession.messages))
        .where(DailySession.user_id == user_id)
        .where(DailySession.session_date == today)
    )
    daily_session = session_result.scalar_one_or_none()

    if not daily_session:
        daily_session = DailySession(
            user_id=user_id,
            session_date=today,
            fase_saat_ini=body.fase_saat_ini,
            total_belanja=body.total_belanja,
            hpp_unit=body.hpp_unit,
        )
        db.add(daily_session)
        await db.flush()  # dapat daily_session.id tanpa commit

    try:
        # 1. System Prompt berdasarkan fase — TIDAK DIUBAH (logika bisnis)
        if body.fase_saat_ini == "PAGI_COSTING":
            system_prompt = (
                "Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
                "User akan menginput bahan belanjaan dan jumlah porsi masakan yang dibuat.\n"
                "Tugasmu:\n"
                "1. Hitung 'Total Belanja' (semua uang keluar).\n"
                "2. Hitung 'Modal Terpakai' (hanya nilai bahan yang benar-benar jadi makanan/terpakai).\n"
                "3. Hitung 'HPP per unit' (Modal Terpakai / jumlah porsi).\n"
                "4. Berikan saran harga jual (margin 30%-50%).\n"
                "Isi field 'response' dengan balasan bahasa Indonesia sehari-hari yang ramah, hangat, dan memotivasi. "
                "Tentukan nilai 'total_belanja', 'modal_terpakai', dan 'hpp_unit' secara akurat."
            )
        else:  # SORE_REVENUE
            system_prompt = (
                f"Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
                f"User akan melaporkan berapa jumlah makanan yang laku terjual dan berapa harga jual per porsinya.\n"
                f"Konteks Finansial Hari Ini:\n"
                f"- Total Belanja Tadi Pagi: Rp {body.total_belanja:,}\n"
                f"- HPP per unit: Rp {body.hpp_unit:,}\n"
                f"Tugasmu:\n"
                f"1. Hitung Total Pendapatan (jumlah laku x harga jual).\n"
                f"2. Hitung Laba Bersih (Total Pendapatan - (jumlah laku x HPP)).\n"
                f"3. Evaluasi apakah Total Pendapatan >= Total Belanja Tadi Pagi (Balik Modal).\n"
                f"Isi field 'response' dengan balasan bahasa Indonesia yang antusias, ramah, dan berikan rincian laba. "
                f"Tentukan nilai 'porsi_terjual', 'harga_jual', 'total_pendapatan', 'laba_bersih', dan 'balik_modal' secara akurat."
            )
            
        system_prompt += (
            "\n\n## Deteksi Intent Koreksi Belanja\n"
            "Jika user menyebut bahwa data belanja sebelumnya salah dan ingin dikoreksi "
            "(contoh: 'eh tadi salah', 'ralat', 'harusnya', 'bukan segitu', 'koreksi'), "
            "maka:\n"
            "- Tetapkan intent = 'KOREKSI_BELANJA'\n"
            "- Isi koreksi_item dengan nama bahan yang dikoreksi (huruf kecil, tanpa satuan)\n"
            "- Isi koreksi_harga_lama dengan harga yang salah (integer Rupiah, tanpa titik/koma)\n"
            "- Isi koreksi_harga_baru dengan harga yang benar (integer Rupiah, tanpa titik/koma)\n"
            "- Jika user hanya menyebut harga baru tanpa harga lama, isi koreksi_harga_lama = 0\n"
            "\nContoh:\n"
            "User: 'tadi ayam saya tulis 40rb, sebenarnya cuma 35rb'\n"
            "→ intent: 'KOREKSI_BELANJA', koreksi_item: 'ayam', "
            "koreksi_harga_lama: 40000, koreksi_harga_baru: 35000\n"
        )

        # 2. JSON Schema untuk Structured Outputs — TIDAK DIUBAH
        schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "response": types.Schema(
                    type=types.Type.STRING,
                    description="Jawaban teks natural Bahasa Indonesia yang ramah dan penuh empati.",
                ),
                "intent": types.Schema(
                    type=types.Type.STRING,
                    enum=[
                        "CATAT_BELANJA",
                        "KOREKSI_BELANJA",
                        "LAPOR_JUALAN",
                        "TANYA_INFO",
                        "LAINNYA",
                    ],
                    description="Klasifikasi intent utama dari pesan user."
                ),
                "koreksi_item": types.Schema(
                    type=types.Type.STRING,
                    description="Nama item yang dikoreksi. Diisi HANYA jika intent == KOREKSI_BELANJA. Contoh: 'ayam', 'cabe'.",
                ),
                "koreksi_harga_lama": types.Schema(
                    type=types.Type.INTEGER,
                    description="Harga item yang salah (nilai lama), dalam Rupiah. Diisi HANYA jika intent == KOREKSI_BELANJA.",
                ),
                "koreksi_harga_baru": types.Schema(
                    type=types.Type.INTEGER,
                    description="Harga item yang benar (nilai baru), dalam Rupiah. Diisi HANYA jika intent == KOREKSI_BELANJA.",
                ),
                "total_belanja": types.Schema(
                    type=types.Type.INTEGER,
                    description="Total uang dikeluarkan untuk belanja bahan. Hanya fase pagi.",
                ),
                "modal_terpakai": types.Schema(
                    type=types.Type.INTEGER,
                    description="Nilai bahan baku yang benar-benar terpakai. Hanya fase pagi.",
                ),
                "hpp_unit": types.Schema(
                    type=types.Type.INTEGER,
                    description="HPP per porsi masakan. Hanya fase pagi.",
                ),
                "porsi_terjual": types.Schema(
                    type=types.Type.INTEGER,
                    description="Jumlah porsi makanan yang terjual. Hanya fase sore.",
                ),
                "harga_jual": types.Schema(
                    type=types.Type.INTEGER,
                    description="Harga jual per porsi makanan. Hanya fase sore.",
                ),
                "total_pendapatan": types.Schema(
                    type=types.Type.INTEGER,
                    description="Total omzet/pendapatan kotor. Hanya fase sore.",
                ),
                "laba_bersih": types.Schema(
                    type=types.Type.INTEGER,
                    description="Laba bersih operasional. Hanya fase sore.",
                ),
                "balik_modal": types.Schema(
                    type=types.Type.BOOLEAN,
                    description="Apakah total pendapatan >= total belanja pagi. Hanya fase sore.",
                ),
            },
            required=["response"],
        )

        # 3. Inisialisasi google-genai client (thread-safe per-request)
        client = genai.Client(api_key=active_api_key)

        # 4. Rakit history (context window: 8 pesan terakhir)
        max_history_len = 8
        history_window = (
            body.chat_history[-max_history_len:]
            if len(body.chat_history) > max_history_len
            else body.chat_history
        )

        contents = []
        for msg in history_window:
            role = "user" if msg.role == "user" else "model"
            contents.append(types.Content(role=role, parts=[types.Part(text=msg.content)]))
        contents.append(types.Content(role="user", parts=[types.Part(text=body.message)]))

        # 5. S3-01 + S3-02: Panggil Gemini ASYNC dengan active_gemini_model + timeout
        try:
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    client.models.generate_content,
                    model=active_gemini_model,   # S3-01: pakai model dari fallback chain
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        response_mime_type="application/json",
                        response_schema=schema,
                    ),
                ),
                timeout=GEMINI_TIMEOUT_SECONDS,  # S3-02: timeout per request
            )
        except asyncio.TimeoutError:
            await db.rollback()
            raise HTTPException(
                status_code=503,
                detail=f"AI tidak merespons dalam {int(GEMINI_TIMEOUT_SECONDS)} detik. Silakan coba lagi.",
            )

        # 6. Parse hasil JSON — TIDAK DIUBAH
        data = json.loads(response.text)

        # 7. Ekstraksi nilai dan defaults
        new_total_belanja = body.total_belanja
        new_modal_terpakai = 0
        new_hpp_unit = body.hpp_unit
        new_fase = body.fase_saat_ini

        total_pendapatan_val = data.get("total_pendapatan")
        laba_bersih_val = data.get("laba_bersih")
        porsi_terjual_val = data.get("porsi_terjual")
        harga_jual_val = data.get("harga_jual")
        balik_modal_val = data.get("balik_modal")

        gemini_intent = data.get("intent", "LAINNYA")
        is_koreksi = gemini_intent == "KOREKSI_BELANJA"
        koreksi_summary = None

        if gemini_intent == "KOREKSI_BELANJA":
            koreksi_item = data.get("koreksi_item", "")
            harga_lama = int(data.get("koreksi_harga_lama") or 0)
            harga_baru = int(data.get("koreksi_harga_baru") or 0)

            # Ambil porsi_dibuat dari DailySession — default 0 jika belum dicatat
            porsi_dibuat = daily_session.porsi_terjual or 0

            new_total_belanja, new_hpp_unit = apply_koreksi_belanja(
                current_total_belanja=daily_session.total_belanja,
                current_hpp_unit=daily_session.hpp_unit,
                porsi_dibuat=porsi_dibuat,
                harga_lama=harga_lama,
                harga_baru=harga_baru,
            )

            if is_koreksi and koreksi_item:
                koreksi_summary = (
                    f"Harga {koreksi_item} dikoreksi: "
                    f"Rp {harga_lama:,.0f} → Rp {harga_baru:,.0f}".replace(",", ".")
                )

            logger.info(
                "koreksi_belanja_applied",
                user_id=user_id,
                item=koreksi_item,
                harga_lama=harga_lama,
                harga_baru=harga_baru,
                total_belanja_before=daily_session.total_belanja,
                total_belanja_after=new_total_belanja,
                hpp_before=daily_session.hpp_unit,
                hpp_after=new_hpp_unit,
            )
        elif body.fase_saat_ini == "PAGI_COSTING":
            (
                new_total_belanja,
                new_modal_terpakai,
                new_hpp_unit,
                new_fase,
            ) = calculate_pagi_metrics(
                raw_total_belanja=data.get("total_belanja"),
                raw_modal_terpakai=data.get("modal_terpakai"),
                raw_hpp_unit=data.get("hpp_unit"),
                current_total_belanja=body.total_belanja,
                current_hpp_unit=body.hpp_unit,
            )
        else:  # SORE_REVENUE
            if porsi_terjual_val is not None:
                porsi_terjual_val = max(0, int(porsi_terjual_val))
            if harga_jual_val is not None:
                harga_jual_val = max(0, int(harga_jual_val))
            if total_pendapatan_val is not None:
                total_pendapatan_val = max(0, int(total_pendapatan_val))
            if laba_bersih_val is not None:
                laba_bersih_val = int(laba_bersih_val)
            if balik_modal_val is None and total_pendapatan_val is not None:
                balik_modal_val = total_pendapatan_val >= new_total_belanja

        # 8. Simpan pesan dan update state ke DB — TIDAK DIUBAH
        db.add(ChatMessage(
            session_id=daily_session.id,
            role="user",
            content=body.message,
        ))
        db.add(ChatMessage(
            session_id=daily_session.id,
            role="assistant",
            content=data.get("response", ""),
        ))

        daily_session.fase_saat_ini = new_fase
        daily_session.total_belanja = new_total_belanja
        daily_session.modal_terpakai = new_modal_terpakai
        daily_session.hpp_unit = new_hpp_unit
        if body.fase_saat_ini == "SORE_REVENUE":
            daily_session.total_pendapatan = total_pendapatan_val
            daily_session.laba_bersih = laba_bersih_val
            daily_session.porsi_terjual = porsi_terjual_val
            daily_session.harga_jual = harga_jual_val
            daily_session.balik_modal = balik_modal_val

        await db.commit()

        logger.info(
            "chat_request_success",
            user_id=user_id,
            fase=body.fase_saat_ini,
            new_fase=new_fase,
            hpp_unit=new_hpp_unit,
            model=active_gemini_model,
        )

        return ChatResponse(
            response=data.get("response", ""),
            total_belanja=new_total_belanja,
            modal_terpakai=new_modal_terpakai,
            hpp_unit=new_hpp_unit,
            fase_saat_ini=new_fase,
            total_pendapatan=total_pendapatan_val,
            laba_bersih=laba_bersih_val,
            porsi_terjual=porsi_terjual_val,
            harga_jual=harga_jual_val,
            balik_modal=balik_modal_val,
            is_koreksi=is_koreksi,
            koreksi_summary=koreksi_summary,
        )

    except json.JSONDecodeError as e:
        await db.rollback()
        logger.error("chat_request_failed", user_id=user_id, error_type="JSONDecodeError", error_detail=str(e))
        raise HTTPException(
            status_code=422,
            detail="Format respons dari AI tidak valid. Silakan kirim ulang pesan Anda.",
        )
    except ValueError as e:
        await db.rollback()
        logger.error("chat_request_failed", user_id=user_id, error_type="ValueError", error_detail=str(e))
        raise HTTPException(
            status_code=422,
            detail=f"Gagal memproses kalkulasi: {str(e)}",
        )
    except HTTPException:
        raise  # re-raise HTTPException (timeout, dll.) tanpa wrap
    except Exception as e:
        await db.rollback()
        logger.error("chat_request_failed", user_id=user_id, error_type=type(e).__name__, error_detail=str(e))
        error_str = str(e).lower()
        if "quota" in error_str or "resource_exhausted" in error_str or "429" in error_str:
            raise HTTPException(
                status_code=429,
                detail="Kuota Google AI hari ini sudah habis. Coba lagi besok ya, Bu!",
            )
        elif "timeout" in error_str or "deadline" in error_str:
            raise HTTPException(
                status_code=503,
                detail="AI sedang sibuk. Silakan kirim ulang pesan Anda dalam beberapa detik.",
            )
        elif "invalid" in error_str and "key" in error_str:
            raise HTTPException(
                status_code=401,
                detail="Konfigurasi API Key tidak valid. Hubungi administrator.",
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Terjadi kesalahan internal. Tim kami sudah notifikasi.",
            )


# =====================================================================
# FRONTEND STATIC FILES (production build)
# =====================================================================
frontend_dist = "frontend/dist"
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def root():
        return FileResponse(f"{frontend_dist}/index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def catch_all(full_path: str):
        file_path = f"{frontend_dist}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(f"{frontend_dist}/index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"status": "running", "service": "DapurProfit AI API v3.0.0"}
