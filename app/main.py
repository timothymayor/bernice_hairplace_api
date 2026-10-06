"""App factory.

Local: `uvicorn app.main:create_app --factory`.
Container: gunicorn with `uvicorn_worker.UvicornWorker` (see Dockerfile).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version
from typing import Any

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1 import health
from app.core import metrics as _metrics  # noqa: F401 - registers business metrics
from app.core.config import Settings, get_settings
from app.core.container import Container
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging, scrub
from app.core.middleware import BodySizeLimitMiddleware, RequestContextMiddleware
from app.workers.inprocess import InProcessWorker

log = structlog.get_logger(__name__)

try:
    API_VERSION = version("bernice-hairplace-api")
except PackageNotFoundError:  # running from a source tree without an install
    API_VERSION = "0.0.0"


def _init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return

    def before_send(event: Any, _hint: Any) -> Any:
        return scrub(event)

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        release=API_VERSION,
        send_default_pii=False,
        traces_sample_rate=0.05,
        before_send=before_send,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, json=settings.app_env != "local")
    _init_sentry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        container = Container.build(settings)
        app.state.container = container
        log.info("startup", environment=settings.app_env, version=API_VERSION)
        worker = InProcessWorker(container.redis) if settings.run_worker_in_process else None
        if worker:
            worker.start()
        try:
            yield
        finally:
            if worker:
                await worker.stop()
            await container.aclose()
            log.info("shutdown")

    is_prod = settings.app_env == "production"
    app = FastAPI(
        title="Bernice Hairplace API",
        version=API_VERSION,
        description="Catalog, cart, checkout and Paystack payments for the Bernice Hairplace web "
        "store and mobile app.",
        lifespan=lifespan,
        docs_url=None if is_prod else "/docs",
        redoc_url=None,
        openapi_url=None if is_prod else "/openapi.json",
    )
    install_error_handlers(app)

    app.include_router(health.router)

    Instrumentator(
        excluded_handlers=["/healthz", "/readyz", "/metrics"],
        should_group_status_codes=True,
    ).instrument(app)

    # Starlette runs middleware in reverse order of registration: the last added is outermost.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
        max_age=600,
    )
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    return app
