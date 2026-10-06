"""Runs the arq worker inside the API process (`RUN_WORKER_IN_PROCESS=true`).

Only for free-tier staging, where a separate worker service isn't available (ADR 0003).
Production runs `arq app.workers.settings.WorkerSettings` as its own process; the settings
validator refuses this mode when APP_ENV=production.
"""

import asyncio
import contextlib
from typing import cast

import structlog
from arq.connections import ArqRedis
from arq.typing import WorkerSettingsBase
from arq.worker import Worker, create_worker
from redis.asyncio import Redis

log = structlog.get_logger(__name__)

MAX_RESTART_DELAY_S = 60.0


class InProcessWorker:
    def __init__(self, redis: Redis) -> None:
        # Imported here: the settings module reads the environment at import time.
        from app.workers.settings import WorkerSettings

        # Shares the API's connection pool; this wrapper must never close it.
        self._pool = ArqRedis(connection_pool=redis.connection_pool)
        self._worker: Worker = create_worker(
            cast("type[WorkerSettingsBase]", WorkerSettings),
            redis_pool=self._pool,
            handle_signals=False,
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="arq-in-process")
        log.info("worker.in_process_started")

    async def _run(self) -> None:
        # Restart with backoff: a Redis outage at boot (or later) must not leave the API running
        # without its worker until the next deploy. The API itself keeps serving throughout.
        delay = 1.0
        while True:
            try:
                await self._worker.main()
                return
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("worker.in_process_crashed", restart_in_s=delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, MAX_RESTART_DELAY_S)

    async def stop(self) -> None:
        # arq's Worker.close() signals itself with SIGUSR1, which doesn't exist on Windows, so
        # cancel directly. Interrupted jobs stay queued and are retried (arq retry_jobs).
        if self._task is None:
            return
        self._task.cancel()
        running = [t for t in self._worker.tasks.values() if not t.done()]
        for t in running:
            t.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(self._task, *running, return_exceptions=True)
        log.info("worker.in_process_stopped")
