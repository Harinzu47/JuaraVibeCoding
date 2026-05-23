from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import google.generativeai as genai
import json
import re
import os
import time
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(title="DapurProfit AI API", version="1.0")

# Store requests timestamp: {ip_address: [timestamps]}
ip_request_history = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only apply rate limiting to /api/chat endpoint
        if request.url.path == "/api/chat":
            client_ip = request.client.host if request.client else "unknown"
            now = time.time()
            
            # Clean up timestamps older than 60 seconds
            if client_ip in ip_request_history:
                ip_request_history[client_ip] = [
                    t for t in ip_request_history[client_ip] if now - t < 60
                ]
            else:
                ip_request_history[client_ip] = []
            
            # Check rate limit: max 45 requests per minute
            if len(ip_request_history[client_ip]) >= 45:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Terlalu banyak mengirim pesan. Silakan tunggu 1 menit ya, Bu!"}
                )
            
            ip_request_history[client_ip].append(now)
            
        response = await call_next(request)
        return response

app.add_middleware(RateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8081",
        "http://localhost:8082"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# API SETUP & CONFIGURATION
# =====================================================================
# Load environment variables dari .env secara manual jika ada
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

# Ambil API key dari environment variable
gemini_api_key = os.environ.get("GEMINI_API_KEY")

# =====================================================================
# DATA MODELS
# =====================================================================
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    chat_history: list[ChatMessage]
    fase_saat_ini: str
    total_belanja: int
    hpp_unit: int
    api_key_override: str | None = None  # Izinkan input manual dari UI jika env kosong

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

# =====================================================================
# ENDPOINT API CHAT
# =====================================================================
@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Tentukan API key yang akan digunakan
    active_api_key = request.api_key_override or gemini_api_key
    
    if not active_api_key:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key tidak dikonfigurasi. Silakan masukkan API Key di Pengaturan."
        )
        
    try:
        # 1. Definisikan System Prompt berdasarkan fase
        if request.fase_saat_ini == "PAGI_COSTING":
            system_prompt = (
                "Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
                "User akan menginput bahan belanjaan dan jumlah porsi masakan yang dibuat.\n"
                "Tugasmu:\n"
                "1. Hitung 'Total Belanja' (semua uang keluar).\n"
                "2. Hitung 'Modal Terpakai' (hanya nilai bahan yang benar-benar jadi makanan/terpakai).\n"
                "3. Hitung 'HPP per unit' (Modal Terpakai / jumlah porsi).\n"
                "4. Berikan saran harga jual (margin 30%-50%).\n"
                "Isi field 'response' dengan balasan bahasa Indonesia sehari-hari yang ramah, hangat, dan memotivasi. "
                "Jangan sertakan format XML atau tag di luar JSON. Tentukan nilai 'total_belanja', 'modal_terpakai', dan 'hpp_unit' secara akurat pada field yang bersangkutan."
            )
        else:  # SORE_REVENUE
            system_prompt = (
                f"Kamu adalah DapurProfit AI, asisten finansial ramah untuk ibu-ibu penjual makanan. "
                f"User akan melaporkan berapa jumlah makanan yang laku terjual dan berapa harga jual per porsinya.\n"
                f"Konteks Finansial Hari Ini:\n"
                f"- Total Belanja Tadi Pagi: Rp {request.total_belanja:,}\n"
                f"- HPP per unit: Rp {request.hpp_unit:,}\n"
                f"Tugasmu:\n"
                f"1. Hitung Total Pendapatan (jumlah laku x harga jual).\n"
                f"2. Hitung Laba Bersih (Total Pendapatan - (jumlah laku x HPP)).\n"
                f"3. Evaluasi apakah Total Pendapatan hari ini sudah lebih besar dari Total Belanja Tadi Pagi (Balik Modal).\n"
                f"Isi field 'response' dengan balasan bahasa Indonesia yang antusias, ramah, dan berikan rincian laba serta sisa nilai bahan baku jika ada. "
                f"Tentukan nilai 'porsi_terjual', 'harga_jual', 'total_pendapatan', 'laba_bersih', dan 'balik_modal' secara akurat pada field yang bersangkutan."
            )

        # 2. Skema Output Terstruktur JSON
        schema = {
            "type": "OBJECT",
            "properties": {
                "response": {
                    "type": "STRING",
                    "description": "Jawaban teks natural dalam Bahasa Indonesia yang ramah, santai, dan penuh empati untuk Ibu pelaku UMKM."
                },
                "total_belanja": {
                    "type": "INTEGER",
                    "description": "Total uang yang dikeluarkan untuk belanja bahan. Hanya diisi jika di fase pagi."
                },
                "modal_terpakai": {
                    "type": "INTEGER",
                    "description": "Nilai bahan baku yang benar-benar terpakai untuk masakan hari ini. Hanya diisi jika di fase pagi."
                },
                "hpp_unit": {
                    "type": "INTEGER",
                    "description": "Harga Pokok Penjualan (HPP) per porsi masakan. Hanya diisi jika di fase pagi."
                },
                "porsi_terjual": {
                    "type": "INTEGER",
                    "description": "Jumlah porsi makanan yang terjual. Hanya diisi jika di fase sore."
                },
                "harga_jual": {
                    "type": "INTEGER",
                    "description": "Harga jual per porsi makanan. Hanya diisi jika di fase sore."
                },
                "total_pendapatan": {
                    "type": "INTEGER",
                    "description": "Total omzet/pendapatan kotor. Hanya diisi jika di fase sore."
                },
                "laba_bersih": {
                    "type": "INTEGER",
                    "description": "Laba bersih operasional. Hanya diisi jika di fase sore."
                },
                "balik_modal": {
                    "type": "BOOLEAN",
                    "description": "Apakah total pendapatan sudah lebih besar dari total belanja pagi. Hanya diisi jika di fase sore."
                }
            },
            "required": ["response"]
        }

        # 3. Inisialisasi Model & Request-isolated Client untuk Thread Safety
        from google.ai.generativelanguage_v1beta import GenerativeServiceClient
        from google.api_core.client_options import ClientOptions
        
        c = GenerativeServiceClient(client_options=ClientOptions(api_key=active_api_key))
        
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_prompt
        )
        model._client = c  # Override client secara instansial agar thread-safe

        # 4. Rakit history untuk Gemini API format dengan context windowing (maksimal 8 pesan terakhir)
        max_history_len = 8
        history_window = request.chat_history[-max_history_len:] if len(request.chat_history) > max_history_len else request.chat_history

        gemini_contents = []
        for msg in history_window:
            role = "user" if msg.role == "user" else "model"
            gemini_contents.append({"role": role, "parts": [msg.content]})
            
        # Tambahkan pesan user saat ini ke list payload
        gemini_contents.append({"role": "user", "parts": [request.message]})

        # 5. Panggil Gemini dengan Structured Outputs
        response = model.generate_content(
            gemini_contents,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        
        # 6. Parse hasil JSON dari Gemini
        try:
            data = json.loads(response.text)
        except Exception as parse_err:
            raise ValueError(f"Gagal memproses keluaran terstruktur: {parse_err}. Response was: {response.text}")

        # 7. Nilai default dan ekstraksi dari hasil parsing
        new_total_belanja = request.total_belanja
        new_modal_terpakai = 0
        new_hpp_unit = request.hpp_unit
        new_fase = request.fase_saat_ini
        
        # Field sore
        total_pendapatan_val = data.get("total_pendapatan")
        laba_bersih_val = data.get("laba_bersih")
        porsi_terjual_val = data.get("porsi_terjual")
        harga_jual_val = data.get("harga_jual")
        balik_modal_val = data.get("balik_modal")

        if request.fase_saat_ini == "PAGI_COSTING":
            if "total_belanja" in data and data["total_belanja"] is not None:
                new_total_belanja = max(0, int(data["total_belanja"]))
            if "modal_terpakai" in data and data["modal_terpakai"] is not None:
                new_modal_terpakai = max(0, int(data["modal_terpakai"]))
            if "hpp_unit" in data and data["hpp_unit"] is not None:
                new_hpp_unit = max(0, int(data["hpp_unit"]))
                # Transisi fase otomatis jika HPP berhasil dihitung
                if new_hpp_unit > 0:
                    new_fase = "SORE_REVENUE"
        else:
            if porsi_terjual_val is not None: porsi_terjual_val = max(0, int(porsi_terjual_val))
            if harga_jual_val is not None: harga_jual_val = max(0, int(harga_jual_val))
            if total_pendapatan_val is not None: total_pendapatan_val = max(0, int(total_pendapatan_val))
            if laba_bersih_val is not None: laba_bersih_val = int(laba_bersih_val)
            if balik_modal_val is None and total_pendapatan_val is not None:
                balik_modal_val = total_pendapatan_val >= new_total_belanja

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
            balik_modal=balik_modal_val
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kendala menghubungi Google Gemini API: {str(e)}")

# =====================================================================
# FRONTEND SERVING & HEALTH CHECK
# =====================================================================
frontend_dist = "frontend/dist"
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets")
    
    @app.get("/")
    async def root():
        return FileResponse(f"{frontend_dist}/index.html")
else:
    @app.get("/")
    async def root():
        return {"status": "running", "service": "DapurProfit AI API (Frontend build not found)"}
