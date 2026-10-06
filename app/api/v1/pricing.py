"""POST /v1/pricing/quote: server-priced bag with price/stock change flags (BP §5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.catalog import get_catalog
from app.domain.catalog import Catalog
from app.domain.checkout import QuoteRequestLine, quote_items
from app.schemas.pricing import QuoteIn, QuoteOut

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.post("/quote", response_model=QuoteOut)
async def quote(
    body: QuoteIn, request: Request, catalog: Annotated[Catalog, Depends(get_catalog)]
) -> QuoteOut:
    """Prices the bag on the server. Public: guests see totals before signing in."""
    lines = [
        QuoteRequestLine(
            product_id=i.product_id,
            selected_length=i.selected_length,
            quantity=i.quantity,
            seen_unit_price=i.seen_unit_price,
        )
        for i in body.items
    ]
    result = quote_items(catalog, lines, body.fulfillment_method)
    site_url = request.app.state.container.settings.site_url
    return QuoteOut.from_domain(result, body.fulfillment_method, site_url)
