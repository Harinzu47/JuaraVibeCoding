import logging
import os
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.sessions import router as session_router
from app.core.config import settings
from app.db.session import get_db_session
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.gemini import gemini_service

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
# LIFESPAN — startup + shutdown
# =====================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Probe active Gemini model on startup
    if settings.GEMINI_API_KEY:
        try:
            await gemini_service.detect_active_model(settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error("gemini_model_detection_failed_at_startup", error=str(e))
    else:
        logger.warning("gemini_api_key_missing_at_startup")

    logger.info("app_startup_complete", active_model=gemini_service.active_model)

    yield

    logger.info("app_shutdown_initiated")
    logger.info("app_shutdown_complete")


# =====================================================================
# FASTAPI APP SETUP
# =====================================================================
app = FastAPI(
    title="DapurProfit AI API",
    description="Backend API for DapurProfit AI - Dynamic COGS & Revenue Tracker",
    version="3.0.0",
    lifespan=lifespan,
)

# Apply middlewares
app.add_middleware(
    RateLimitMiddleware,
    redis_url=settings.REDIS_URL,
    max_requests=45,
    window_seconds=60,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router)
app.include_router(session_router)
app.include_router(chat_router)


# =====================================================================
# HEALTH & DIAGNOSTICS ENDPOINTS
# =====================================================================
@app.get("/api/health", tags=["system"])
async def health_check(db: AsyncSession = Depends(get_db_session)):
    """Diagnostic endpoint: status of all system components."""
    redis_ok = False
    db_ok = False
    db_latency_ms = None

    # Check Redis connectivity
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        await client.close()
        redis_ok = True
    except Exception:
        pass

    # Check Database connectivity and measure latency
    try:
        t0 = time.monotonic()
        await db.execute(text("SELECT 1"))
        db_latency_ms = round((time.monotonic() - t0) * 1000, 1)
        db_ok = True
    except Exception:
        pass

    gemini_ok = bool(settings.GEMINI_API_KEY)
    all_ok = gemini_ok and db_ok
    overall = "ok" if all_ok else "degraded"

    return {
        "status": overall,
        "version": "3.0.0",
        "components": {
            "gemini": {
                "configured": gemini_ok,
                "active_model": gemini_service.active_model,
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


@app.get("/api/ready", tags=["system"])
async def readiness_probe(db: AsyncSession = Depends(get_db_session)):
    """Readiness probe for deployment health checks (e.g. Cloud Run, Kubernetes)."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready.",
        )

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini API Key is not configured.",
        )

    return {"ready": True, "active_model": gemini_service.active_model}


# =====================================================================
# FRONTEND STATIC FILES SERVING (Production Build)
# =====================================================================
frontend_dist = "frontend/dist"
if os.path.exists(frontend_dist):
    app.mount(
        "/assets", StaticFiles(directory=f"{frontend_dist}/assets"), name="assets"
    )

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
        return {
            "status": "running",
            "service": "DapurProfit AI API (Static files not built)",
        }
