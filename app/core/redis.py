"""Redis connection and the per-order lock.

Redis is a cache and coordinator, never the source of truth: every helper here degrades to a
no-op (with a warning) when Redis is unreachable, and correctness falls back to SQL guards.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from redis.asyncio import Redis
from redis.exceptions import LockError, RedisError

log = structlog.get_logger(__name__)


def create_redis(url: str) -> Redis:
    client: Redis = Redis.from_url(
        url,
        socket_timeout=2,
        socket_connect_timeout=2,
        health_check_interval=30,
        retry_on_timeout=False,
    )
    return client


@asynccontextmanager
async def redis_lock(
    redis: Redis, name: str, *, ttl: float = 30, blocking_timeout: float = 15
) -> AsyncIterator[bool]:
    """Serializes work on one key across API and worker processes.

    Yields True when the lock is held. If Redis is down or the lock can't be acquired in time,
    yields False and the caller proceeds anyway, relying on its conditional SQL updates.
    """
    lock = redis.lock(name, timeout=ttl, blocking_timeout=blocking_timeout)
    try:
        acquired = bool(await lock.acquire())
    except RedisError as exc:
        log.warning("redis.lock_unavailable", lock=name, error=type(exc).__name__)
        acquired = False
    if not acquired:
        log.warning("redis.lock_not_acquired", lock=name)
    try:
        yield acquired
    finally:
        if acquired:
            try:
                await lock.release()
            except (LockError, RedisError) as exc:
                log.warning("redis.lock_release_failed", lock=name, error=type(exc).__name__)


async def redis_ok(redis: Redis) -> bool:
    try:
        return bool(await redis.ping())
    except RedisError:
        return False
