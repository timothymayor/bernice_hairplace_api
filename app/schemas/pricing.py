"""POST /v1/pricing/quote models."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.checkout import Quote, QuoteLine, QuoteStatus
from app.domain.pricing import CURRENCY, FulfillmentMethod
from app.schemas.catalog import absolute_url


class QuoteItemIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=100)
    selected_length: int = Field(ge=1, le=100)
    quantity: int = Field(ge=1, le=20)
    seen_unit_price: int | None = Field(
        default=None,
        ge=0,
        description="Unit price the client last displayed. Only used to flag price changes; "
        "never charged.",
    )


class QuoteIn(BaseModel):
    items: list[QuoteItemIn] = Field(min_length=1, max_length=50)
    fulfillment_method: FulfillmentMethod = "courier_express"


class QuoteLineOut(BaseModel):
    product_id: str
    selected_length: int
    quantity: int
    status: QuoteStatus = Field(
        description="ok | unavailable (unknown or out of stock) | invalid_length"
    )
    name: str | None
    sku: str | None
    image: str | None
    unit_price: int | None
    line_total: int | None
    price_changed: bool
    previous_unit_price: int | None

    @classmethod
    def from_domain(cls, line: QuoteLine, site_url: str) -> "QuoteLineOut":
        req, product = line.request, line.product
        return cls(
            product_id=req.product_id,
            selected_length=req.selected_length,
            quantity=req.quantity,
            status=line.status,
            name=product.name if product else None,
            sku=product.sku if product else None,
            image=absolute_url(site_url, product.images["main"]) if product else None,
            unit_price=line.unit_price,
            line_total=line.line_total,
            price_changed=line.price_changed,
            previous_unit_price=req.seen_unit_price if line.price_changed else None,
        )


class QuoteOut(BaseModel):
    currency: Literal["NGN"] = CURRENCY
    fulfillment_method: FulfillmentMethod
    lines: list[QuoteLineOut]
    subtotal: int = Field(description="Sum of lines with status ok")
    delivery_fee: int
    total: int
    has_issues: bool = Field(description="True if any line is unavailable or changed price")

    @classmethod
    def from_domain(cls, q: Quote, method: FulfillmentMethod, site_url: str) -> "QuoteOut":
        return cls(
            fulfillment_method=method,
            lines=[QuoteLineOut.from_domain(line, site_url) for line in q.lines],
            subtotal=q.subtotal,
            delivery_fee=q.delivery_fee,
            total=q.total,
            has_issues=q.has_issues,
        )
