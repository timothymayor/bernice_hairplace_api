"""Pricing properties (the exact values are covered by tests/parity)."""

from hypothesis import given
from hypothesis import strategies as st

from app.domain.pricing import (
    EXPRESS_DELIVERY_FEE,
    FREE_DELIVERY_THRESHOLD,
    delivery_fee,
    unit_price,
)

prices = st.integers(min_value=0, max_value=5_000_000)
lengths = st.integers(min_value=0, max_value=100)


@given(base=prices, default=lengths, length=lengths)
def test_unit_price_is_never_negative(base: int, default: int, length: int) -> None:
    assert unit_price(base, default, length) >= 0


@given(base=prices, default=lengths, length=lengths)
def test_unit_price_never_decreases_with_length(base: int, default: int, length: int) -> None:
    assert unit_price(base, default, length + 1) >= unit_price(base, default, length)


@given(base=prices, default=lengths)
def test_default_length_costs_the_base_price(base: int, default: int) -> None:
    assert unit_price(base, default, default) == base


@given(subtotal=st.integers(min_value=0, max_value=10_000_000))
def test_delivery_fee_rules(subtotal: int) -> None:
    assert delivery_fee(subtotal, "studio_pickup") == 0
    expected = 0 if subtotal >= FREE_DELIVERY_THRESHOLD else EXPRESS_DELIVERY_FEE
    assert delivery_fee(subtotal, "courier_express") == expected
