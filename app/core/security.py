"""Supabase access-token verification and the CurrentUser / admin dependencies."""

import json
import time
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

import httpx
import jwt
import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings
from app.core.errors import Forbidden, Unauthorized

log = structlog.get_logger(__name__)

ASYMMETRIC_ALGS = ("ES256", "RS256")
JWKS_TTL_SECONDS = 3600
KID_MISS_REFETCH_INTERVAL = 60


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: UUID
    email: str | None
    role: str | None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class JwksCache:
    """JWKS cached in-process and in Redis (`jwks:{project}`, TTL 1h).

    Refetched once on an unknown `kid` (at most once a minute).
    """

    def __init__(self, settings: Settings, http: httpx.AsyncClient, redis: Redis) -> None:
        self._url = settings.jwks_url
        self._redis_key = f"jwks:{settings.supabase_url.split('//')[-1].split('.')[0]}"
        self._http = http
        self._redis = redis
        self._keys: dict[str, jwt.PyJWK] = {}
        self._loaded_at = 0.0
        # None = never refetched. Not 0.0: monotonic() counts from boot, which can be < 60s ago.
        self._last_forced: float | None = None

    async def get(self, kid: str | None) -> jwt.PyJWK:
        if not self._keys or time.monotonic() - self._loaded_at > JWKS_TTL_SECONDS:
            await self._load(force=False)
        throttled = (
            self._last_forced is not None
            and time.monotonic() - self._last_forced < KID_MISS_REFETCH_INTERVAL
        )
        if kid not in self._keys and not throttled:
            self._last_forced = time.monotonic()
            await self._load(force=True)
        key = self._keys.get(kid or "")
        if key is None:
            raise Unauthorized()
        return key

    async def _load(self, *, force: bool) -> None:
        raw: str | None = None
        if not force:
            try:
                cached = await self._redis.get(self._redis_key)
                raw = cached.decode() if cached else None
            except RedisError:
                log.warning("jwks.redis_unavailable")
        if raw is None:
            try:
                resp = await self._http.get(self._url, timeout=5)
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                log.error("jwks.fetch_failed", error=type(exc).__name__)
                if self._keys:
                    return
                raise Unauthorized() from exc
            raw = resp.text
            try:
                await self._redis.set(self._redis_key, raw, ex=JWKS_TTL_SECONDS)
            except RedisError:
                log.warning("jwks.redis_unavailable")
        keys: dict[str, jwt.PyJWK] = {}
        for jwk in json.loads(raw).get("keys", []):
            if jwk.get("alg") in ASYMMETRIC_ALGS and jwk.get("kid"):
                try:
                    keys[jwk["kid"]] = jwt.PyJWK(jwk)
                except jwt.PyJWTError:
                    log.warning("jwks.bad_key", kid=jwk.get("kid"))
        self._keys = keys
        self._loaded_at = time.monotonic()


async def verify_token(token: str, settings: Settings, jwks: JwksCache) -> CurrentUser:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise Unauthorized() from exc
    alg = header.get("alg")
    key: Any
    if alg in ASYMMETRIC_ALGS:
        jwk = await jwks.get(header.get("kid"))
        if jwk.algorithm_name != alg:
            raise Unauthorized()
        key = jwk.key
    elif alg == "HS256" and settings.supabase_jwt_secret is not None:
        key = settings.supabase_jwt_secret.get_secret_value()
    else:
        raise Unauthorized()
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[alg],
            audience="authenticated",
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
            leeway=10,
        )
        user_id = UUID(str(claims["sub"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise Unauthorized() from exc
    app_metadata = claims.get("app_metadata") or {}
    role = app_metadata.get("role") if isinstance(app_metadata, dict) else None
    email = claims.get("email")
    return CurrentUser(id=user_id, email=email if isinstance(email, str) else None, role=role)


bearer = HTTPBearer(auto_error=False, description="Supabase access token")


async def get_optional_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> CurrentUser | None:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        return None
    c = request.app.state.container
    user = await verify_token(creds.credentials, c.settings, c.jwks)
    request.state.user_id = str(user.id)
    return user


async def get_current_user(
    user: Annotated[CurrentUser | None, Depends(get_optional_user)],
) -> CurrentUser:
    if user is None:
        raise Unauthorized()
    return user


async def require_admin(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
    # app_metadata is only writable with the service role; user_metadata is never trusted.
    if not user.is_admin:
        raise Forbidden()
    return user


User = Annotated[CurrentUser, Depends(get_current_user)]
OptionalUser = Annotated[CurrentUser | None, Depends(get_optional_user)]
Admin = Annotated[CurrentUser, Depends(require_admin)]
