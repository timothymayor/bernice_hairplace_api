"""Catalog and pricing endpoints over HTTP."""

from typing import Any

import httpx
import pytest

from app.catalog import get_catalog

SITE = "https://bernicehairplace.com"
CAMBODIAN = "raw-cambodian-bone-straight"


async def get_json(client: httpx.AsyncClient, url: str, **params: Any) -> Any:
    r = await client.get(url, params=params)
    assert r.status_code == 200, r.text
    return r.json()


async def test_categories_only_lists_groups_with_products(client: httpx.AsyncClient) -> None:
    body = await get_json(client, "/v1/catalog/categories")
    assert [c["slug"] for c in body["items"]] == ["bundles", "wigs", "frontals", "care"]
    assert sum(c["product_count"] for c in body["items"]) == len(get_catalog().products)
    assert "Bone Straight" in body["textures"]


async def test_list_products_paginates_with_a_cursor(client: httpx.AsyncClient) -> None:
    first = await get_json(client, "/v1/catalog/products", limit=4)
    assert first["total"] == 11
    assert len(first["items"]) == 4
    seen = [p["id"] for p in first["items"]]
    cursor = first["next_cursor"]
    while cursor:
        page = await get_json(client, "/v1/catalog/products", limit=4, cursor=cursor)
        seen += [p["id"] for p in page["items"]]
        cursor = page["next_cursor"]
    assert seen == [p.id for p in get_catalog().products]


async def test_list_products_filters_and_sorts(client: httpx.AsyncClient) -> None:
    body = await get_json(
        client, "/v1/catalog/products", category="bundles", sort="price_asc", length_range="26"
    )
    prices = [p["price"] for p in body["items"]]
    assert prices == sorted(prices)
    assert all(p["category"] == "bundles" for p in body["items"])


async def test_product_summary_shape(client: httpx.AsyncClient) -> None:
    item = (await get_json(client, "/v1/catalog/products", limit=1))["items"][0]
    assert item["currency"] == "NGN"
    assert item["image"].startswith(f"{SITE}/images/")
    assert "description" not in item


@pytest.mark.parametrize(
    "params",
    [
        {"cursor": "garbage!"},
        {"min_price": 5, "max_price": 1},
        {"sort": "cheapest"},
        {"limit": 51},
        {"category": "closures"},
    ],
)
async def test_list_products_rejects_bad_params(
    client: httpx.AsyncClient, params: dict[str, Any]
) -> None:
    r = await client.get("/v1/catalog/products", params=params)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_failed"


async def test_product_detail_has_server_prices_per_length(client: httpx.AsyncClient) -> None:
    p = await get_json(client, f"/v1/catalog/products/{CAMBODIAN}")
    assert p["price"] == 185_000
    assert {lp["length"]: lp["price"] for lp in p["length_prices"]} == {
        18: 165_000, 20: 185_000, 22: 215_000, 26: 275_000, 30: 335_000,
    }  # fmt: skip
    assert p["full_specs"]["bleach_grade"].startswith("Grade 12A")
    assert all(url.startswith(SITE) for url in p["images"].values())
    pairing = p["recommended_pairing"]
    assert pairing["product_id"] == "prod-hd-swiss-closure-5x5"
    assert pairing["selected_length"] == 16
    assert pairing["price"] == 75_000


async def test_unknown_product_is_404(client: httpx.AsyncClient) -> None:
    for url in ("/v1/catalog/products/nope", "/v1/catalog/products/nope/related"):
        r = await client.get(url)
        assert r.status_code == 404
        assert r.json()["error"] == {
            "code": "not_found",
            "message": "We couldn't find that product",
        }


async def test_related_starts_with_the_pairing_and_excludes_itself(
    client: httpx.AsyncClient,
) -> None:
    items = await get_json(client, f"/v1/catalog/products/{CAMBODIAN}/related")
    ids = [p["id"] for p in items]
    assert ids[0] == "prod-hd-swiss-closure-5x5"
    assert "prod-cambodian-bone-straight" not in ids
    assert len(ids) == len(set(ids)) == 4


async def test_search_matches_sku_and_suggests_categories(client: httpx.AsyncClient) -> None:
    body = await get_json(client, "/v1/catalog/search", q="BHC-CAM")
    assert [p["id"] for p in body["items"]] == ["prod-cambodian-bone-straight"]
    body = await get_json(client, "/v1/catalog/search", q="wig")
    assert any(c["slug"] == "wigs" for c in body["categories"])


async def test_search_requires_a_term(client: httpx.AsyncClient) -> None:
    for q in ("", "   "):
        r = await client.get("/v1/catalog/search", params={"q": q})
        assert r.status_code == 400


async def test_catalog_responses_are_cacheable(client: httpx.AsyncClient) -> None:
    r = await client.get("/v1/catalog/categories")
    assert r.headers["cache-control"] == "public, max-age=300"
    assert r.headers["etag"].startswith('W/"')


async def test_quote_prices_on_the_server(client: httpx.AsyncClient) -> None:
    r = await client.post(
        "/v1/pricing/quote",
        json={
            "fulfillment_method": "courier_express",
            "items": [
                {"product_id": "prod-botanical-hair-elixir", "selected_length": 100, "quantity": 2},
                {
                    "product_id": "prod-cambodian-bone-straight",
                    "selected_length": 19,
                    "quantity": 1,
                },
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["currency"] == "NGN"
    assert [ln["status"] for ln in body["lines"]] == ["ok", "invalid_length"]
    assert (body["subtotal"], body["delivery_fee"], body["total"]) == (70_000, 4_500, 74_500)
    assert body["has_issues"] is True
    assert "cache-control" not in r.headers


@pytest.mark.parametrize(
    "body",
    [
        {"items": []},
        {"items": [{"product_id": "x", "selected_length": 18, "quantity": 21}]},
        {"items": [{"product_id": "x", "selected_length": 18, "quantity": 1.5}]},
        {
            "items": [{"product_id": "x", "selected_length": 18, "quantity": 1}],
            "fulfillment_method": "drone",
        },
        {
            "items": [{"product_id": "x", "selected_length": 18, "quantity": 1, "unit_price": 1}]
            * 51
        },
    ],
)
async def test_quote_validation(client: httpx.AsyncClient, body: dict[str, Any]) -> None:
    r = await client.post("/v1/pricing/quote", json=body)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_failed"
