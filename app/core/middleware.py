"""Pure-ASGI middleware: request id + access log, request body limit, security headers.

Written as raw ASGI (not BaseHTTPMiddleware) so request bodies are streamed untouched; the Paystack
webhook needs the exact raw bytes for its signature check.
"""

import re
import time
import uuid

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import hash_id

log = structlog.get_logger("app.access")

MAX_BODY_BYTES = 1_048_576
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
_QUIET_PATHS = frozenset({"/healthz", "/readyz", "/metrics"})

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "Cross-Origin-Resource-Policy": "same-site",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
}
# The interactive docs load assets from a CDN, so they get the default (no) CSP.
_DOCS_PATHS = frozenset({"/docs", "/redoc", "/docs/oauth2-redirect"})


class RequestContextMiddleware:
    """Assigns `X-Request-ID`, binds it to structlog, writes one access-log line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, b"x-request-id")
        request_id = incoming if incoming and _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in SECURITY_HEADERS.items():
                    if name == "Content-Security-Policy" and scope["path"] in _DOCS_PATHS:
                        continue
                    headers.setdefault(name, value)
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = scope["path"]
            if path not in _QUIET_PATHS or status >= 400:
                route = scope.get("route")
                state = scope.get("state", {})
                log.info(
                    "request",
                    method=scope["method"],
                    route=getattr(route, "path", path),
                    status=status,
                    latency_ms=round((time.perf_counter() - start) * 1000, 1),
                    user_id=hash_id(state.get("user_id")),
                )
            structlog.contextvars.clear_contextvars()


class BodySizeLimitMiddleware:
    """Rejects request bodies over `max_bytes` with 413, by Content-Length or while streaming."""

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = _header(scope, b"content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_bytes):
            await _too_large(send)
            return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await _too_large(send)


class _BodyTooLarge(Exception):
    pass


async def _too_large(send: Send) -> None:
    body = b'{"error":{"code":"payload_too_large","message":"Request is too large"}}'
    await send(
        {
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return str(value.decode("latin-1"))
    return None
