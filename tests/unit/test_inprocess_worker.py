"""RUN_WORKER_IN_PROCESS: the arq worker runs inside the API (free-tier staging, ADR 0003)."""

import asyncio

import arq.worker
import fakeredis
import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core import container as container_module
from app.core.config import Settings
from app.main import create_app
from tests.conftest import make_settings

HEALTH_KEY = "arq:queue:health-check"


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    # fakeredis doesn't implement INFO, which arq only logs at startup.
    async def no_info(*_args: object) -> None:
        return None

    monkeypatch.setattr(arq.worker, "log_redis_info", no_info)
    return make_settings(run_worker_in_process=True)


async def test_worker_runs_inside_the_api(
    app: FastAPI, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    # arq writes its health-check key on its first poll.
    for _ in range(50):
        if await fake_redis.exists(HEALTH_KEY):
            break
        await asyncio.sleep(0.1)
    assert await fake_redis.exists(HEALTH_KEY)


async def test_worker_off_by_default(fake_redis: fakeredis.FakeAsyncRedis) -> None:
    assert make_settings().run_worker_in_process is False
    assert not await fake_redis.exists(HEALTH_KEY)


def test_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="staging only"):
        make_settings(app_env="production", run_worker_in_process=True)


async def test_worker_restarts_after_a_crash(
    monkeypatch: pytest.MonkeyPatch, fake_redis: fakeredis.FakeAsyncRedis
) -> None:
    calls = 0

    async def flaky_info(*_args: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RedisConnectionError("redis not up yet")

    monkeypatch.setattr(arq.worker, "log_redis_info", flaky_info)
    monkeypatch.setattr(container_module, "create_redis", lambda _url: fake_redis)
    app = create_app(make_settings(run_worker_in_process=True))
    async with LifespanManager(app, startup_timeout=10, shutdown_timeout=10):
        for _ in range(50):
            if await fake_redis.exists(HEALTH_KEY):
                break
            await asyncio.sleep(0.1)
    assert calls == 2
    assert await fake_redis.exists(HEALTH_KEY)
