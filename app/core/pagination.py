"""Opaque cursors for `?cursor=&limit=` pagination (AGENTS.md §9)."""

import base64
import binascii

from app.core.errors import ValidationFailed

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def encode_offset(offset: int) -> str:
    return base64.urlsafe_b64encode(f"o:{offset}".encode()).decode().rstrip("=")


def decode_offset(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode()
        prefix, value = raw.split(":", 1)
        offset = int(value)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValidationFailed(fields={"cursor": "Invalid cursor"}) from exc
    if prefix != "o" or offset < 0:
        raise ValidationFailed(fields={"cursor": "Invalid cursor"})
    return offset
