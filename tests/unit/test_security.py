"""Supabase JWT verification (BP §11 Auth).

Expired, wrong-audience and tampered tokens are rejected.
"""

import json
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import fakeredis
import httpx
import jwt
import pytest
import respx
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI

from app.core.config import Settings
from app.core.errors import Unauthorized
from app.core.security import Admin, JwksCache, User, verify_token
from tests.conftest import JWT_SECRET, SUPABASE_URL, make_settings

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_URL}/auth/v1"


class KeyPair:
    def __init__(self, kid: str) -> None:
        self.kid = kid
        self.private = ec.generate_private_key(ec.SECP256R1())

    def jwk(self) -> dict[str, Any]:
        public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(self.private.public_key()))
        return {**public, "kid": self.kid, "alg": "ES256", "use": "sig"}


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    base: dict[str, Any] = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": ISSUER,
        "iat": now,
        "exp": now + 3600,
        "email": "ada@example.com",
        "app_metadata": {"provider": "google"},
        "user_metadata": {"role": "admin"},  # must never grant admin
    }
    base.update(overrides)
    return base


def sign(key: KeyPair, **overrides: Any) -> str:
    return jwt.encode(claims(**overrides), key.private, algorithm="ES256", headers={"kid": key.kid})


@pytest.fixture
def key() -> KeyPair:
    return KeyPair("kid-1")


@pytest.fixture
def jwks_route(key: KeyPair) -> Any:
    with respx.mock(assert_all_called=False) as mock:
        yield mock.get(JWKS_URL).mock(return_value=httpx.Response(200, json={"keys": [key.jwk()]}))


@pytest.fixture
async def jwks(settings: Settings) -> AsyncIterator[JwksCache]:
    async with httpx.AsyncClient() as http:
        yield JwksCache(settings, http, fakeredis.FakeAsyncRedis())


@pytest.mark.usefixtures("jwks_route")
async def test_valid_es256_token(key: KeyPair, settings: Settings, jwks: JwksCache) -> None:
    sub = str(uuid.uuid4())
    user = await verify_token(sign(key, sub=sub), settings, jwks)
    assert str(user.id) == sub
    assert user.email == "ada@example.com"
    assert not user.is_admin  # user_metadata.role is ignored


@pytest.mark.usefixtures("jwks_route")
@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},
        {"aud": "anon"},
        {"iss": "https://other.supabase.co/auth/v1"},
        {"sub": "not-a-uuid"},
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "bad-sub"],
)
async def test_invalid_claims_rejected(
    key: KeyPair, settings: Settings, jwks: JwksCache, overrides: dict[str, Any]
) -> None:
    with pytest.raises(Unauthorized):
        await verify_token(sign(key, **overrides), settings, jwks)


@pytest.mark.usefixtures("jwks_route")
async def test_tampered_token_rejected(key: KeyPair, settings: Settings, jwks: JwksCache) -> None:
    header, _payload, signature = sign(key).split(".")
    forged = jwt.utils.base64url_encode(
        json.dumps(claims(app_metadata={"role": "admin"})).encode()
    ).decode()
    with pytest.raises(Unauthorized):
        await verify_token(f"{header}.{forged}.{signature}", settings, jwks)


@pytest.mark.usefixtures("jwks_route")
async def test_token_signed_by_unknown_key_rejected(settings: Settings, jwks: JwksCache) -> None:
    with pytest.raises(Unauthorized):
        await verify_token(sign(KeyPair("kid-unknown")), settings, jwks)


async def test_alg_none_rejected(settings: Settings, jwks: JwksCache) -> None:
    token = jwt.encode(claims(), key="", algorithm="none")
    with pytest.raises(Unauthorized):
        await verify_token(token, settings, jwks)


async def test_garbage_rejected(settings: Settings, jwks: JwksCache) -> None:
    with pytest.raises(Unauthorized):
        await verify_token("not.a.jwt", settings, jwks)


async def test_hs256_fallback_when_secret_configured(settings: Settings, jwks: JwksCache) -> None:
    token = jwt.encode(claims(app_metadata={"role": "admin"}), JWT_SECRET, algorithm="HS256")
    user = await verify_token(token, settings, jwks)
    assert user.is_admin


async def test_hs256_rejected_without_secret(jwks: JwksCache) -> None:
    settings = make_settings(supabase_jwt_secret=None)
    token = jwt.encode(claims(), JWT_SECRET, algorithm="HS256")
    with pytest.raises(Unauthorized):
        await verify_token(token, settings, jwks)


async def test_kid_miss_refetches_jwks_once(settings: Settings, jwks: JwksCache) -> None:
    old, new = KeyPair("kid-old"), KeyPair("kid-new")
    with respx.mock() as mock:
        route = mock.get(JWKS_URL)
        route.side_effect = [
            httpx.Response(200, json={"keys": [old.jwk()]}),
            httpx.Response(200, json={"keys": [old.jwk(), new.jwk()]}),
        ]
        await verify_token(sign(old), settings, jwks)
        await verify_token(sign(new), settings, jwks)  # rotated key: one refetch
        assert route.call_count == 2


async def test_jwks_served_from_redis_cache(key: KeyPair, settings: Settings) -> None:
    redis = fakeredis.FakeAsyncRedis()
    with respx.mock() as mock:
        route = mock.get(JWKS_URL).mock(
            return_value=httpx.Response(200, json={"keys": [key.jwk()]})
        )
        async with httpx.AsyncClient() as http:
            await verify_token(sign(key), settings, JwksCache(settings, http, redis))
            await verify_token(sign(key), settings, JwksCache(settings, http, redis))
        assert route.call_count == 1


# ---- dependencies through the app ----


@pytest.fixture
def protected_app(app: FastAPI) -> FastAPI:
    @app.get("/_test/me")
    async def _me(user: User) -> dict[str, str]:
        return {"id": str(user.id)}

    @app.get("/_test/admin")
    async def _admin(user: Admin) -> dict[str, str]:
        return {"id": str(user.id)}

    return app


@pytest.mark.usefixtures("protected_app")
async def test_missing_token_is_401_with_error_shape(client: httpx.AsyncClient) -> None:
    r = await client.get("/_test/me")
    assert r.status_code == 401
    assert r.json() == {"error": {"code": "unauthorized", "message": "Please sign in to continue"}}


@pytest.mark.usefixtures("protected_app")
async def test_admin_requires_app_metadata_role(client: httpx.AsyncClient) -> None:
    customer = jwt.encode(claims(), JWT_SECRET, algorithm="HS256")
    admin = jwt.encode(claims(app_metadata={"role": "admin"}), JWT_SECRET, algorithm="HS256")
    auth = {"Authorization": f"Bearer {customer}"}
    assert (await client.get("/_test/me", headers=auth)).status_code == 200
    assert (await client.get("/_test/admin", headers=auth)).status_code == 403
    r = await client.get("/_test/admin", headers={"Authorization": f"Bearer {admin}"})
    assert r.status_code == 200


async def test_kid_miss_refetches_on_a_freshly_booted_machine(
    settings: Settings, jwks: JwksCache, monkeypatch: pytest.MonkeyPatch
) -> None:
    # time.monotonic() counts from machine boot. A CI runner or a new VM can be < 60s old; the
    # first kid-miss refetch must not depend on that (this flaked CI on a fresh runner).
    started = time.perf_counter()
    monkeypatch.setattr(
        "app.core.security.time.monotonic", lambda: 30.0 + time.perf_counter() - started
    )
    old, new = KeyPair("kid-old"), KeyPair("kid-new")
    with respx.mock() as mock:
        route = mock.get(JWKS_URL)
        route.side_effect = [
            httpx.Response(200, json={"keys": [old.jwk()]}),
            httpx.Response(200, json={"keys": [old.jwk(), new.jwk()]}),
        ]
        await verify_token(sign(old), settings, jwks)
        await verify_token(sign(new), settings, jwks)
        assert route.call_count == 2
