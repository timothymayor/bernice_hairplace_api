from collections.abc import AsyncIterator
from typing import Any

import fakeredis
import httpx
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI

from app.core import container as container_module
from app.core.config import Settings
from app.main import create_app

SUPABASE_URL = "https://testproject.supabase.co"
JWT_SECRET = "test-legacy-hs256-secret-at-least-32-bytes"


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "app_env": "test",
        "supabase_url": SUPABASE_URL,
        "supabase_jwt_secret": JWT_SECRET,
        "cors_origins": "https://bernicehairplace.com",
        "database_url": "postgresql+asyncpg://u:p@127.0.0.1:1/db",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def fake_redis() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis()


@pytest.fixture
async def app(
    settings: Settings, fake_redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[FastAPI]:
    monkeypatch.setattr(container_module, "create_redis", lambda _url: fake_redis)
    application = create_app(settings)
    async with LifespanManager(application, startup_timeout=10, shutdown_timeout=10):
        yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
