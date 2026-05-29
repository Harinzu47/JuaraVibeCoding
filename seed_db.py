import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.models.user import User
from app.core.security import hash_password
from app.db.base import Base
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as session:
        # Check if user exists
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'loadtest@aturmodal.com'")
        )
        if not result.scalar():
            user = User(
                email="loadtest@aturmodal.com",
                hashed_password=hash_password("password123"),
            )
            session.add(user)
            await session.commit()
            print("User seeded.")
        else:
            print("User already exists.")


if __name__ == "__main__":
    asyncio.run(seed())
