"""Liveness, readiness and Prometheus metrics. Mounted at the root, not under /v1."""

import asyncio
import hmac
import os
from collections.abc import Coroutine
from typing import Any, Literal

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    generate_latest,
    multiprocess,
)
from pydantic import BaseModel

from app.core.errors import Unauthorized
from app.core.redis import redis_ok
from app.db.session import db_ok

router = APIRouter(tags=["health"])

READY_CHECK_TIMEOUT = 3.0


class HealthOut(BaseModel):
    status: Literal["ok"]


class ReadyOut(BaseModel):
    status: Literal["ready", "degraded", "not_ready"]
    database: Literal["ok", "failed"]
    redis: Literal["ok", "degraded"]
    environment: str


@router.get("/healthz", response_model=HealthOut)
async def healthz() -> HealthOut:
    """Liveness: the process is up and serving. Never touches dependencies."""
    return HealthOut(status="ok")


@router.get(
    "/readyz",
    response_model=ReadyOut,
    responses={503: {"model": ReadyOut, "description": "Database unreachable"}},
)
async def readyz(request: Request) -> JSONResponse:
    """Readiness: Postgres is required; Redis is reported but only degrades (AGENTS.md §10)."""
    c = request.app.state.container

    async def bounded(check: Coroutine[Any, Any, bool]) -> bool:
        try:
            return await asyncio.wait_for(check, READY_CHECK_TIMEOUT)
        except TimeoutError:
            return False

    database, redis = await asyncio.gather(bounded(db_ok(c.engine)), bounded(redis_ok(c.redis)))
    status: Literal["ready", "degraded", "not_ready"]
    status = "not_ready" if not database else ("ready" if redis else "degraded")
    body = ReadyOut(
        status=status,
        database="ok" if database else "failed",
        redis="ok" if redis else "degraded",
        environment=c.settings.app_env,
    )
    return JSONResponse(body.model_dump(), status_code=200 if database else 503)


@router.get("/metrics", include_in_schema=False)
async def metrics(request: Request) -> Response:
    token = request.app.state.container.settings.metrics_token
    if token is not None:
        given = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if not hmac.compare_digest(given.encode(), token.get_secret_value().encode()):
            raise Unauthorized()
    registry: CollectorRegistry = REGISTRY
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        # Under gunicorn each worker keeps its own counters; aggregate them from the shared dir.
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)  # type: ignore[no-untyped-call]
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
