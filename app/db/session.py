"""Async engine (Supabase pooler-safe) and the per-request session dependency."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    # The Supabase transaction pooler (port 6543) can't hold prepared statements across
    # transactions, so asyncpg's statement caches must be off.
    return create_async_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=5,
        pool_pre_ping=True,
        pool_recycle=1800,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "command_timeout": 10,
            "server_settings": {"application_name": "bernice-hairplace-api"},
        },
    )


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def db_ok(engine: AsyncEngine) -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("select 1"))
    except Exception:  # noqa: BLE001 - readiness reports any DB failure as "not ready"
        return False
    return True


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.container.sessionmaker() as session:
        yield session


Session = Annotated[AsyncSession, Depends(get_session)]
