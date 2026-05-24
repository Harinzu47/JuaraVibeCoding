import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from models import User
from auth import hash_password
from database import Base

DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "postgres")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "dapurprofit")

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async with SessionLocal() as session:
        # Check if user exists
        result = await session.execute(text("SELECT id FROM users WHERE email = 'loadtest@dapurprofit.com'"))
        if not result.scalar():
            user = User(
                email="loadtest@dapurprofit.com",
                hashed_password=hash_password("password123"),
            )
            session.add(user)
            await session.commit()
            print("User seeded.")
        else:
            print("User already exists.")

if __name__ == "__main__":
    asyncio.run(seed())
