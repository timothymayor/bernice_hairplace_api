"""Loads the packaged catalog (`products.json`, exported from the web repo; ADR 0002)."""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from app.domain.catalog import Catalog, Product

CATALOG_PATH = Path(__file__).with_name("products.json")


def catalog_sha256(raw: object) -> str:
    """Same digest as the exporter's `sha256(JSON.stringify(PRODUCTS))`; pins fixture parity."""
    compact = json.dumps(raw, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(compact.encode()).hexdigest()


@lru_cache(maxsize=1)
def get_catalog() -> Catalog:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    return Catalog((Product.from_web(p) for p in raw), version=catalog_sha256(raw))
