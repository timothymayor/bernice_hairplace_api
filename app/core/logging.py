"""structlog JSON logging with a processor that masks personal data and credentials."""

import hashlib
import logging
import re
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

SENSITIVE_KEYS = (
    "email",
    "phone",
    "address",
    "authorization",
    "token",
    "secret",
    "password",
    "api_key",
    "customer_name",
)
_EMAIL_RE = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_BEARER_RE = re.compile(r"(?i)bearer\s+[a-z0-9._\-]+")


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(s in k for s in SENSITIVE_KEYS)


def scrub(value: Any) -> Any:
    """Masks sensitive keys and inline emails/bearer tokens, recursively."""
    if isinstance(value, str):
        return _BEARER_RE.sub("Bearer [masked]", _EMAIL_RE.sub("[email]", value))
    if isinstance(value, dict):
        return {k: "[masked]" if _is_sensitive(str(k)) else scrub(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [scrub(v) for v in value]
    return value


def mask_pii(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    for key in list(event_dict):
        if key in ("event", "timestamp", "level", "logger"):
            continue
        event_dict[key] = "[masked]" if _is_sensitive(key) else scrub(event_dict[key])
    return event_dict


def hash_id(value: str | None) -> str | None:
    """Stable, non-reversible identifier for logs (user ids are personal data)."""
    if not value:
        return None
    return hashlib.sha256(value.encode()).hexdigest()[:16]


def configure_logging(level: str = "INFO", *, json: bool = True) -> None:
    renderer: structlog.typing.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            mask_pii,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(level=level.upper(), stream=sys.stdout, format="%(message)s")
