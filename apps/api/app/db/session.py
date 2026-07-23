from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    db_url = (settings.database_url or "").strip()
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if not db_url.startswith("postgresql+asyncpg://"):
        raise ValueError(
            f"Invalid DATABASE_URL: expected 'postgresql+asyncpg://...', received '{db_url[:20]}'. "
            "In Railway, click 'New Variable' -> 'Add Reference' and select your Postgres DATABASE_URL."
        )
    return create_async_engine(db_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def check_database_connection(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
