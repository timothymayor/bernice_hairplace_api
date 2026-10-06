"""App factory behaviour: health, readiness, error shape, middleware, metrics."""

import fakeredis
import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel, Field
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api.v1 import health


@pytest.fixture
def db_up(monkeypatch: pytest.MonkeyPatch) -> None:
    async def ok(_engine: object) -> bool:
        return True

    monkeypatch.setattr(health, "db_ok", ok)


async def test_healthz(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.usefixtures("db_up")
async def test_readyz_ready(client: httpx.AsyncClient) -> None:
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": "ok", "redis": "ok", "environment": "test"}


@pytest.mark.usefixtures("db_up")
async def test_readyz_degraded_when_redis_down(
    client: httpx.AsyncClient, fake_redis: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def down() -> bool:
        raise RedisConnectionError("down")

    monkeypatch.setattr(fake_redis, "ping", down)
    r = await client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"
    assert r.json()["redis"] == "degraded"


async def test_readyz_not_ready_when_db_down(client: httpx.AsyncClient) -> None:
    # The test DATABASE_URL points at a closed port, so the real check fails.
    r = await client.get("/readyz")
    assert r.status_code == 503
    assert r.json()["status"] == "not_ready"
    assert r.json()["database"] == "failed"


async def test_unknown_route_uses_error_shape(client: httpx.AsyncClient) -> None:
    r = await client.get("/v1/nope")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


class _ItemIn(BaseModel):
    quantity: int = Field(ge=1, le=20)


async def test_validation_errors_are_400_with_fields(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    @app.post("/_test/items")
    async def _create(item: _ItemIn) -> dict[str, int]:
        return {"quantity": item.quantity}

    r = await client.post("/_test/items", json={"quantity": 99})
    assert r.status_code == 400
    body = r.json()["error"]
    assert body["code"] == "validation_failed"
    assert "quantity" in body["fields"]


async def test_unhandled_errors_are_safe_500(app: FastAPI, client: httpx.AsyncClient) -> None:
    @app.get("/_test/boom")
    async def _boom() -> None:
        raise RuntimeError("SELECT secret FROM table")

    r = await client.get("/_test/boom")
    assert r.status_code == 500
    assert r.json() == {
        "error": {"code": "internal_error", "message": "Something went wrong. Please try again."}
    }
    assert "secret" not in r.text


async def test_request_id_generated_and_security_headers_set(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz")
    assert len(r.headers["x-request-id"]) == 32
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


async def test_valid_request_id_echoed_and_invalid_replaced(client: httpx.AsyncClient) -> None:
    r = await client.get("/healthz", headers={"X-Request-ID": "abc-123"})
    assert r.headers["x-request-id"] == "abc-123"
    r = await client.get("/healthz", headers={"X-Request-ID": "bad id\nwith newline"})
    assert r.headers["x-request-id"] != "bad id\nwith newline"


async def test_oversized_body_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post("/healthz", content=b"x" * (1_048_576 + 1))
    assert r.status_code == 413
    assert r.json()["error"]["code"] == "payload_too_large"


async def test_cors_allowlist(client: httpx.AsyncClient) -> None:
    preflight = {"Access-Control-Request-Method": "GET"}
    ok = await client.options(
        "/healthz", headers={"Origin": "https://bernicehairplace.com", **preflight}
    )
    assert ok.headers["access-control-allow-origin"] == "https://bernicehairplace.com"
    bad = await client.options("/healthz", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in bad.headers


async def test_metrics_exposed(client: httpx.AsyncClient) -> None:
    r = await client.get("/metrics")
    assert r.status_code == 200
    assert "payments_verified_total" in r.text


async def test_metrics_token_required_when_configured(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pydantic import SecretStr

    monkeypatch.setattr(app.state.container.settings, "metrics_token", SecretStr("m-token"))
    assert (await client.get("/metrics")).status_code == 401
    ok = await client.get("/metrics", headers={"Authorization": "Bearer m-token"})
    assert ok.status_code == 200
