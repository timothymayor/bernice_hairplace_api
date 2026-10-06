"""Checkout domain details not covered by the parity fixtures: JS coercion edges, error fields,
quotes."""

import math

import pytest

from app.catalog import get_catalog
from app.domain.checkout import (
    CheckoutInputError,
    QuoteRequestLine,
    _js_number,
    _text,
    parse_checkout_input,
    quote_items,
)

ADDRESS = {
    "firstName": "Ada",
    "lastName": "Okafor",
    "email": "ada@example.com",
    "phone": "08012345678",
    "streetAddress": "12 Admiralty Way",
    "district": "Lekki",
}
CAMBODIAN = "prod-cambodian-bone-straight"  # default 20in, ₦185,000; lengths 18-30


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, math.nan),
        (True, 1.0),
        ("", 0.0),
        ("  18 ", 18.0),
        ("0x12", 18.0),
        ("1e1", 10.0),
        (".5", 0.5),
        ("-Infinity", -math.inf),
        ("1_000", math.nan),
        ("18in", math.nan),
        ([], 0.0),
        ([18], 18.0),
        ([1, 2], math.nan),
        ({"a": 1}, math.nan),
    ],
)
def test_js_number(value: object, expected: float) -> None:
    got = _js_number(value)
    assert (math.isnan(got) and math.isnan(expected)) or got == expected


def test_text_trims_like_js_and_truncates_by_utf16_units() -> None:
    assert _text(" \ufeffAda\u00a0 ") == "Ada"
    assert _text("\x1cAda") == "\x1cAda"  # JS trim keeps it; Python's strip() would not
    assert _text("ab" + "😀" * 3, 4) == "ab😀"  # an emoji is 2 UTF-16 units
    assert _text("abc😀", 4) == "abc"  # never half an emoji
    assert _text(12.0) == "12"
    assert _text(False) == "false"


@pytest.mark.parametrize(
    ("patch", "field"),
    [
        ({"firstName": ""}, "address.first_name"),
        ({"lastName": " "}, "address.last_name"),
        ({"email": "ada@x"}, "address.email"),
        ({"phone": "123"}, "address.phone"),
        ({"streetAddress": ""}, "address.street_address"),
    ],
)
def test_errors_point_at_the_field(patch: dict[str, str], field: str) -> None:
    body = {"address": {**ADDRESS, **patch}, "items": [{"productId": "x"}]}
    with pytest.raises(CheckoutInputError) as exc:
        parse_checkout_input(body)
    assert exc.value.field == field


def test_email_with_js_whitespace_is_rejected() -> None:
    body = {"address": {**ADDRESS, "email": "ada\u3000x@example.com"}, "items": [{}]}
    with pytest.raises(CheckoutInputError, match="valid email"):
        parse_checkout_input(body)


def test_address_is_stored_in_the_web_shape() -> None:
    parsed = parse_checkout_input(
        {"address": {**ADDRESS, "state": "Abuja"}, "items": [{"productId": CAMBODIAN}]}
    )
    stored = parsed.address.to_web()
    assert stored["state"] == "Lagos State"
    assert stored["country"] == "Nigeria"
    assert set(stored) == {
        "firstName", "lastName", "email", "phone", "streetAddress",
        "suiteFlat", "district", "state", "country", "deliveryNotes",
    }  # fmt: skip


def test_quote_flags_lines_instead_of_failing() -> None:
    q = quote_items(
        get_catalog(),
        [
            QuoteRequestLine(CAMBODIAN, 22, 1, seen_unit_price=200_000),  # now 215,000
            QuoteRequestLine(CAMBODIAN, 19, 1),
            QuoteRequestLine("prod-gone", 20, 1),
        ],
        "courier_express",
    )
    assert [line.status for line in q.lines] == ["ok", "invalid_length", "unavailable"]
    assert q.lines[0].unit_price == 215_000
    assert q.lines[0].price_changed
    assert (q.subtotal, q.delivery_fee, q.total) == (215_000, 0, 215_000)
    assert q.has_issues


def test_quote_with_nothing_purchasable_charges_no_delivery() -> None:
    q = quote_items(get_catalog(), [QuoteRequestLine("prod-gone", 20, 1)], "courier_express")
    assert (q.subtotal, q.delivery_fee, q.total) == (0, 0, 0)
