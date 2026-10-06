"""AppError hierarchy and the handlers that serialize every error as {"error": {...}}."""

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = structlog.get_logger(__name__)


class AppError(Exception):
    status_code = 400
    code = "bad_request"
    message = "Something went wrong with your request"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        fields: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.fields = fields
        self.headers = headers
        super().__init__(self.message)

    def body(self) -> dict[str, Any]:
        err: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            err["fields"] = self.fields
        return {"error": err}


class ValidationFailed(AppError):
    status_code = 400
    code = "validation_failed"
    message = "Please check the highlighted fields"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Please sign in to continue"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"
    message = "You don't have access to this"


class NotFound(AppError):
    status_code = 404
    code = "not_found"
    message = "We couldn't find that"


class Conflict(AppError):
    status_code = 409
    code = "conflict"
    message = "This request conflicts with the current state"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests. Please wait a moment and try again."

    def __init__(self, retry_after: int) -> None:
        super().__init__(headers={"Retry-After": str(retry_after)})


class UpstreamError(AppError):
    status_code = 502
    code = "upstream_error"
    message = "A service we depend on is unavailable. Please try again."


class NotConfigured(AppError):
    status_code = 503
    code = "not_configured"
    message = "This feature is not available right now"


def _loc_to_field(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(parts) or "body"


async def _app_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(exc.body(), status_code=exc.status_code, headers=exc.headers)


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    fields: dict[str, str] = {}
    for err in exc.errors():
        fields.setdefault(_loc_to_field(tuple(err.get("loc", ()))), str(err.get("msg", "Invalid")))
    return JSONResponse(ValidationFailed(fields=fields).body(), status_code=400)


_HTTP_CODES = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(
        {"error": {"code": code, "message": message}},
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
    )


async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled_error", error_type=type(exc).__name__)
    return JSONResponse(
        {"error": {"code": "internal_error", "message": "Something went wrong. Please try again."}},
        status_code=500,
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled)
