# Task 1 Updated/app/db/connection.py
"""
db/connection.py  –  Single source of truth for the database connection.
All other files that need a DB session import from here.

All connection details come from the project-root .env file ONLY.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load the .env that sits at the project root (Task 1 Updated/.env)
_ROOT_ENV = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_ROOT_ENV if _ROOT_ENV.exists() else None)

# ── Build connection URL from env ──────────────────────────────────────────────
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "healthchecker")
DB_USER = os.getenv("DB_USER", "healthchecker_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

DATABASE_URL = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ── Engine ─────────────────────────────────────────────────────────────────────
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# ── Session factory ────────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
