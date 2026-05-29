import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.models.user import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


# Override the database session dependency
app.dependency_overrides[get_db_session] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create seed users for integration tests
    async with TestingSessionLocal() as session:
        user1 = User(
            email="testuser@aturmodal.com",
            hashed_password=hash_password("password123"),
        )
        user2 = User(
            email="test@aturmodal.com", hashed_password=hash_password("password123")
        )
        session.add(user1)
        session.add(user2)
        await session.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
