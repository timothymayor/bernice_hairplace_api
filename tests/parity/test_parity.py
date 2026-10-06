"""Parity with the web store's TypeScript (AGENTS.md §12, BP §11).

Fixtures are produced by running the web repo's own code: `make parity` regenerates them with
scripts/export_ts_fixtures.mjs. Every case must match exactly.
"""

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from app.catalog import CATALOG_PATH, catalog_sha256, get_catalog
from app.domain.catalog import Catalog, ProductQuery
from app.domain.checkout import CheckoutInputError, parse_checkout_input, price_items
from app.domain.pricing import delivery_fee, unit_price

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return data


PRICING = load("parity_pricing.json")
CHECKOUT = load("parity_checkout.json")
CATALOG_QUERIES = load("parity_catalog.json")


def test_catalog_matches_the_fixtures_source() -> None:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    digest = catalog_sha256(raw)
    for fixture in (PRICING, CHECKOUT, CATALOG_QUERIES):
        assert fixture["catalog_sha256"] == digest, "re-run `make parity` (catalog drifted)"
    assert get_catalog().version == digest


@pytest.mark.parametrize(
    "case", PRICING["unit_prices"], ids=lambda c: f"{c['product_id']}@{c['length']}"
)
def test_unit_price(case: dict[str, Any]) -> None:
    product = get_catalog().get(case["product_id"])
    assert product is not None
    assert unit_price(product.price, product.default_length, case["length"]) == case["unit_price"]


@pytest.mark.parametrize(
    "case", PRICING["delivery_fees"], ids=lambda c: f"{c['method']}-{c['subtotal']}"
)
def test_delivery_fee(case: dict[str, Any]) -> None:
    assert delivery_fee(case["subtotal"], case["method"]) == case["fee"]


def run_checkout(body: Any, catalog: Catalog) -> dict[str, Any]:
    """Python twin of the exporter's `runCheckout` (same output shape)."""
    try:
        parsed = parse_checkout_input(body)
        basket = price_items(catalog, parsed.items, parsed.fulfillment_method)
    except CheckoutInputError as exc:
        return {"ok": False, "error": exc.message}
    return {
        "ok": True,
        "fulfillment_method": parsed.fulfillment_method,
        "address": parsed.address.to_web(),
        "subtotal": basket.subtotal,
        "delivery_fee": basket.delivery_fee,
        "total": basket.total,
        "lines": [
            {
                "product_id": line.product_id,
                "selected_length": line.selected_length,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
                "line_total": line.line_total,
            }
            for line in basket.lines
        ],
    }


def with_out_of_stock(catalog: Catalog, ids: list[str]) -> Catalog:
    if not ids:
        return catalog
    products = (
        dataclasses.replace(p, is_in_stock=False) if p.id in ids else p for p in catalog.products
    )
    return Catalog(products, version=catalog.version)


@pytest.mark.parametrize("index", range(len(PRICING["baskets"])))
def test_basket_pricing(index: int) -> None:
    case = PRICING["baskets"][index]
    address = CHECKOUT["cases"][0]["body"]["address"]
    body = {
        "fulfillmentMethod": case["fulfillment_method"],
        "address": address,
        "items": case["items"],
    }
    assert run_checkout(body, get_catalog()) == case["expected"]


@pytest.mark.parametrize("case", CHECKOUT["cases"], ids=lambda c: c["name"])
def test_checkout_validation(case: dict[str, Any]) -> None:
    catalog = with_out_of_stock(get_catalog(), case["out_of_stock"])
    assert run_checkout(case["body"], catalog) == case["expected"]


_SORTS = {"price-asc": "price_asc", "price-desc": "price_desc"}


def to_product_query(q: dict[str, Any]) -> ProductQuery:
    category = q.get("activeCategory", "all")
    return ProductQuery(
        category=None if category == "all" else category,
        search=q.get("searchQuery") or None,
        texture=q.get("selectedTexture") or None,
        length_range=q.get("selectedLengthRange") or None,
        min_price=q.get("minPrice"),
        max_price=q.get("maxPrice"),
        in_stock=q.get("inStockOnly") or None,
        sort=_SORTS.get(q.get("sortBy", "featured"), q.get("sortBy", "featured")),
    )


@pytest.mark.parametrize(
    "case", CATALOG_QUERIES["queries"], ids=lambda c: json.dumps(c["query"], sort_keys=True)
)
def test_catalog_query(case: dict[str, Any]) -> None:
    found = get_catalog().query(to_product_query(case["query"]))
    assert [p.id for p in found] == case["expected_ids"]
