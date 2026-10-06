"""arq worker: `arq app.workers.settings.WorkerSettings`.

Phase 1 only runs a heartbeat so the worker process can be deployed and monitored. Email,
reconciliation and account-deletion jobs are added in Phases 4-5.
"""

from typing import Any, ClassVar

import structlog
from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging

log = structlog.get_logger(__name__)


async def heartbeat(_ctx: dict[str, Any]) -> None:
    log.info("worker.heartbeat")


async def startup(_ctx: dict[str, Any]) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json=settings.app_env != "local")
    log.info("worker.startup", environment=settings.app_env)


async def shutdown(_ctx: dict[str, Any]) -> None:
    log.info("worker.shutdown")


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    functions: ClassVar[list[Any]] = [heartbeat]
    cron_jobs: ClassVar[list[Any]] = [
        cron(heartbeat, minute=set(range(0, 60, 5)), run_at_startup=True),  # type: ignore[arg-type]
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 60
    health_check_interval = 60
