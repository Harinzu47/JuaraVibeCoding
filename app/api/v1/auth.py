import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, verify_password
from app.db.session import get_db_session
from app.repositories.user import user_repository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = structlog.get_logger()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest, db: AsyncSession = Depends(get_db_session)
):
    """Create a new user account. Returns a JWT access token immediately."""
    existing_user = await user_repository.get_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered."
        )

    user = await user_repository.create_user(db, payload.email, payload.password, payload.full_name)
    await db.commit()

    token = create_access_token(user.id, user.email)
    logger.info("user_registered", user_id=user.id, email=user.email)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Log in and obtain a JWT access token",
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    """Authenticate with email and password. Returns a JWT access token."""
    user = await user_repository.get_by_email(db, payload.email)

    # Always verify password to mitigate timing attacks even if user does not exist
    dummy_hash = "$2b$12$dummyhashtopreventtimingattackleakage000000000000000000"
    input_hash = user.hashed_password if user else dummy_hash
    password_ok = verify_password(payload.password, input_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact support.",
        )

    token = create_access_token(user.id, user.email)
    logger.info("user_logged_in", user_id=user.id)

    return TokenResponse(
        access_token=token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
    )
