"""Pricing rules, ported from the web repo's `src/lib/pricing.ts`. Pure; parity-tested.

Money is whole naira (`int`) everywhere. Kobo (`naira * 100`) exists only at the Paystack boundary.
"""

from typing import Literal

FulfillmentMethod = Literal["courier_express", "studio_pickup"]
FULFILLMENT_METHODS: tuple[FulfillmentMethod, ...] = ("courier_express", "studio_pickup")

CURRENCY: Literal["NGN"] = "NGN"
PRICE_PER_INCH_LONGER = 15_000
PRICE_PER_INCH_SHORTER = 10_000
EXPRESS_DELIVERY_FEE = 4_500
FREE_DELIVERY_THRESHOLD = 150_000


def unit_price(base: int, default_length: int, length: int) -> int:
    """Price at `length` inches: +₦15,000 per inch above the default, -₦10,000 per inch below."""
    diff = length - default_length
    adjustment = diff * PRICE_PER_INCH_LONGER if diff > 0 else diff * PRICE_PER_INCH_SHORTER
    return max(base + adjustment, 0)


def delivery_fee(subtotal: int, method: FulfillmentMethod) -> int:
    """Courier is ₦4,500, free from a ₦150,000 subtotal; studio pickup is free."""
    if method != "courier_express":
        return 0
    return 0 if subtotal >= FREE_DELIVERY_THRESHOLD else EXPRESS_DELIVERY_FEE
