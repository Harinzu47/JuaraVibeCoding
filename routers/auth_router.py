from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database import get_db
from models import User
from auth import hash_password, verify_password, create_access_token
from schemas import RegisterRequest, LoginRequest, TokenResponse
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Daftar akun baru",
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Buat akun baru. Mengembalikan JWT langsung agar user bisa langsung aktif."""
    # Cek apakah email sudah terdaftar
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.email)
    logger.info("user_registered", user_id=user.id, email=user.email)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login dan dapatkan JWT",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login dengan email + password. Mengembalikan JWT."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    # Selalu jalankan verify_password meski user tidak ada — cegah timing attack
    dummy_hash = "$2b$12$dummyhashtopreventtimingattackleakage000000000000000000"
    input_hash = user.hashed_password if user else dummy_hash
    password_ok = verify_password(payload.password, input_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email atau password salah.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun dinonaktifkan. Hubungi administrator.",
        )

    token = create_access_token(user.id, user.email)
    logger.info("user_logged_in", user_id=user.id)
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
    )
