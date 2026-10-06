"""Checkout validation and server-side pricing, ported from the web repo's `server/orders.ts`
(`parseCheckoutInput` + the pricing loop in `createPendingOrder`). Pure; parity-tested.

The web code coerces values the JavaScript way (`String(x)`, `Number(x)`, `.trim()`), and the
parity fixtures pin those decisions (e.g. a quantity of "2" is accepted, 1.5 is not), so the
helpers at the bottom reproduce JS semantics deliberately.

Error messages are customer-facing and reuse the web copy verbatim.
"""

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from app.domain.catalog import Catalog, Product
from app.domain.pricing import FulfillmentMethod, delivery_fee

MAX_LINES = 50
MAX_QUANTITY = 20


class CheckoutInputError(Exception):
    """A customer-safe validation failure. `field` points at the offending input (snake_case)."""

    def __init__(self, message: str, field: str) -> None:
        super().__init__(message)
        self.message = message
        self.field = field


@dataclass(frozen=True, slots=True)
class ShippingAddress:
    first_name: str
    last_name: str
    email: str
    phone: str
    street_address: str
    suite_flat: str
    district: str
    delivery_notes: str
    state: str = "Lagos State"
    country: str = "Nigeria"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_web(self) -> dict[str, str]:
        """The web's `ShippingAddress` shape, as stored in `orders.shipping_address` (jsonb)."""
        return {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "streetAddress": self.street_address,
            "suiteFlat": self.suite_flat,
            "district": self.district,
            "state": self.state,
            "country": self.country,
            "deliveryNotes": self.delivery_notes,
        }


@dataclass(frozen=True, slots=True)
class RequestedItem:
    product_id: str
    selected_length: float  # JS Number: may be NaN or fractional until priced
    quantity: float


@dataclass(frozen=True, slots=True)
class CheckoutInput:
    fulfillment_method: FulfillmentMethod
    address: ShippingAddress
    items: tuple[RequestedItem, ...]


@dataclass(frozen=True, slots=True)
class PricedLine:
    product_id: str
    product_name: str
    sku: str
    category_label: str
    image: str
    selected_length: int
    quantity: int
    unit_price: int
    line_total: int


@dataclass(frozen=True, slots=True)
class PricedBasket:
    lines: tuple[PricedLine, ...]
    subtotal: int
    delivery_fee: int

    @property
    def total(self) -> int:
        return self.subtotal + self.delivery_fee


def parse_checkout_input(body: Any) -> CheckoutInput:
    """Validates untrusted checkout input (port of `parseCheckoutInput`), in the web's order."""
    b = body if isinstance(body, Mapping) else {}
    method: FulfillmentMethod = (
        "studio_pickup" if b.get("fulfillmentMethod") == "studio_pickup" else "courier_express"
    )
    raw = b.get("address")
    raw = raw if isinstance(raw, Mapping) else {}
    address = ShippingAddress(
        first_name=_text(raw.get("firstName"), 80),
        last_name=_text(raw.get("lastName"), 80),
        email=_text(raw.get("email"), 254),
        phone=_text(raw.get("phone"), 40),
        street_address=_text(raw.get("streetAddress")),
        suite_flat=_text(raw.get("suiteFlat"), 100),
        district=_text(raw.get("district"), 80),
        delivery_notes=_text(raw.get("deliveryNotes"), 500),
    )

    if not address.first_name or not address.last_name:
        field = "address.first_name" if not address.first_name else "address.last_name"
        raise CheckoutInputError("Please provide your full name", field)
    if not _EMAIL_RE.match(address.email):
        raise CheckoutInputError("A valid email address is required", "address.email")
    if len(re.sub(r"[^0-9]", "", address.phone)) < 7:
        raise CheckoutInputError("A valid phone number is required", "address.phone")
    if method == "courier_express" and not address.street_address:
        raise CheckoutInputError("Please provide a delivery address", "address.street_address")

    items = b.get("items")
    if not isinstance(items, list) or not items:
        raise CheckoutInputError("Your bag is empty", "items")
    if len(items) > MAX_LINES:
        raise CheckoutInputError("Too many items in your bag", "items")
    parsed = tuple(
        RequestedItem(
            product_id=_text(_get(i, "productId"), 100),
            selected_length=_js_number(_get(i, "selectedLength")),
            quantity=_js_number(_get(i, "quantity")),
        )
        for i in items
    )
    return CheckoutInput(fulfillment_method=method, address=address, items=parsed)


def price_items(
    catalog: Catalog, items: Sequence[RequestedItem], method: FulfillmentMethod
) -> PricedBasket:
    """Prices the bag from the catalog, never from the client (loop in `createPendingOrder`).

    Checks run per line in the web's order: availability, then quantity, then length.
    """
    lines: list[PricedLine] = []
    for index, item in enumerate(items):
        product = catalog.get(item.product_id)
        if product is None or not product.is_in_stock:
            raise CheckoutInputError(
                "An item in your bag is no longer available", f"items.{index}.product_id"
            )
        if not _is_js_integer(item.quantity) or not 1 <= item.quantity <= MAX_QUANTITY:
            raise CheckoutInputError("Invalid quantity in your bag", f"items.{index}.quantity")
        if item.selected_length not in product.lengths:  # NaN is never `in` (SameValueZero)
            raise CheckoutInputError(
                f"Invalid length selected for {product.name}", f"items.{index}.selected_length"
            )
        length, quantity = int(item.selected_length), int(item.quantity)
        price = product.price_at(length)
        lines.append(
            PricedLine(
                product_id=product.id,
                product_name=product.name,
                sku=product.sku,
                category_label=product.subtitle,
                image=product.images["main"],
                selected_length=length,
                quantity=quantity,
                unit_price=price,
                line_total=price * quantity,
            )
        )
    subtotal = sum(line.line_total for line in lines)
    fee = delivery_fee(subtotal, method)
    return PricedBasket(lines=tuple(lines), subtotal=subtotal, delivery_fee=fee)


# ───────────── JavaScript coercion helpers ─────────────

# Characters String.prototype.trim() removes (WhiteSpace + LineTerminator). Python's str.strip()
# differs: it also strips \x1c-\x1f and \x85, and keeps ﻿.
_JS_WHITESPACE = (
    "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003"
    "\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
)
# /^[^\s@]+@[^\s@]+\.[^\s@]+$/ with JavaScript's \s.
_NOT_SPACE_OR_AT = f"[^@{re.escape(_JS_WHITESPACE)}]+"
_EMAIL_RE = re.compile(rf"^{_NOT_SPACE_OR_AT}@{_NOT_SPACE_OR_AT}\.{_NOT_SPACE_OR_AT}$")
_JS_NUMERIC_RE = re.compile(
    r"^[+-]?(?:Infinity|(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)$|^0[xX][0-9a-fA-F]+$|^0[bB][01]+$"
    r"|^0[oO][0-7]+$"
)


def _get(item: Any, key: str) -> Any:
    """`i?.[key]`: anything that isn't an object yields undefined."""
    return item.get(key) if isinstance(item, Mapping) else None


def _js_trim(value: str) -> str:
    return value.strip(_JS_WHITESPACE)


def _js_string(value: Any) -> str:
    """`String(value ?? '')`."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return str(int(value)) if value.is_integer() and abs(value) < 1e21 else repr(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return ",".join("" if v is None else _js_string(v) for v in value)
    return "[object Object]"


def _text(value: Any, max_length: int = 200) -> str:
    """`String(value ?? '').trim().slice(0, max)`; slice counts UTF-16 code units like JS."""
    s = _js_trim(_js_string(value))
    encoded = s.encode("utf-16-le", "surrogatepass")
    if len(encoded) <= max_length * 2:
        return s
    # Never split a surrogate pair (JS would leave half an emoji, which Postgres can't store).
    return encoded[: max_length * 2].decode("utf-16-le", "ignore")


def _js_number(value: Any) -> float:
    """`Number(value)`. JSON never yields undefined, so a missing key (None here) is NaN."""
    if value is None:
        return math.nan
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, list):
        return _js_number_from_string(_js_string(value))
    if isinstance(value, str):
        return _js_number_from_string(value)
    return math.nan


def _js_number_from_string(value: str) -> float:
    s = _js_trim(value)
    if not s:
        return 0.0
    if not _JS_NUMERIC_RE.match(s):
        return math.nan
    if s[:2].lower() in ("0x", "0b", "0o"):
        return float(int(s, 0))
    return float(s.replace("Infinity", "inf"))


def _is_js_integer(value: float) -> bool:
    """`Number.isInteger(value)`."""
    return math.isfinite(value) and value.is_integer()


# ───────────── bag quotes ─────────────

QuoteStatus = Literal["ok", "unavailable", "invalid_length"]


@dataclass(frozen=True, slots=True)
class QuoteRequestLine:
    product_id: str
    selected_length: int
    quantity: int
    seen_unit_price: int | None = None


@dataclass(frozen=True, slots=True)
class QuoteLine:
    request: QuoteRequestLine
    status: QuoteStatus
    product: Product | None
    unit_price: int | None
    line_total: int | None

    @property
    def price_changed(self) -> bool:
        seen = self.request.seen_unit_price
        return self.status == "ok" and seen is not None and seen != self.unit_price


@dataclass(frozen=True, slots=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    subtotal: int
    delivery_fee: int

    @property
    def total(self) -> int:
        return self.subtotal + self.delivery_fee

    @property
    def has_issues(self) -> bool:
        return any(line.status != "ok" or line.price_changed for line in self.lines)


def quote_items(
    catalog: Catalog, requested: Sequence[QuoteRequestLine], method: FulfillmentMethod
) -> Quote:
    """Prices a bag for display. Unlike checkout, bad lines are flagged instead of failing the
    whole request, and only purchasable lines count toward the totals. `seen_unit_price` (the
    price the client last showed) only drives the `price_changed` flag; it is never charged."""
    lines: list[QuoteLine] = []
    for req in requested:
        product = catalog.get(req.product_id)
        if product is None or not product.is_in_stock:
            lines.append(QuoteLine(req, "unavailable", product, None, None))
        elif req.selected_length not in product.lengths:
            lines.append(QuoteLine(req, "invalid_length", product, None, None))
        else:
            price = product.price_at(req.selected_length)
            lines.append(QuoteLine(req, "ok", product, price, price * req.quantity))
    subtotal = sum(line.line_total or 0 for line in lines)
    # Nothing purchasable means nothing to deliver.
    fee = delivery_fee(subtotal, method) if any(ln.status == "ok" for ln in lines) else 0
    return Quote(lines=tuple(lines), subtotal=subtotal, delivery_fee=fee)
