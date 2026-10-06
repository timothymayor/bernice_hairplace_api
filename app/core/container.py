"""Process-wide clients, built once in the app lifespan and shared through `app.state.container`."""

from dataclasses import dataclass

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.core.redis import create_redis
from app.core.security import JwksCache
from app.db.session import create_engine, create_sessionmaker


@dataclass(slots=True)
class Container:
    settings: Settings
    http: httpx.AsyncClient
    redis: Redis
    engine: AsyncEngine
    sessionmaker: async_sessionmaker[AsyncSession]
    jwks: JwksCache

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        http = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            headers={"User-Agent": "bernice-hairplace-api"},
        )
        redis = create_redis(settings.redis_url)
        engine = create_engine(settings)
        return cls(
            settings=settings,
            http=http,
            redis=redis,
            engine=engine,
            sessionmaker=create_sessionmaker(engine),
            jwks=JwksCache(settings, http, redis),
        )

    async def aclose(self) -> None:
        await self.http.aclose()
        await self.redis.aclose()
        await self.engine.dispose()
