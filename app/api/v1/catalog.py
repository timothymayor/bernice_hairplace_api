"""Public catalog: categories, product list/detail, related products, search (BP §5)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, Response

from app.catalog import get_catalog
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import DEFAULT_LIMIT, MAX_LIMIT, decode_offset, encode_offset
from app.domain.catalog import Catalog, LengthRange, ProductQuery, Sort
from app.schemas.catalog import (
    CategoriesOut,
    CategoryOut,
    CategorySlug,
    ProductOut,
    ProductPage,
    ProductSummaryOut,
    SearchOut,
)

router = APIRouter(prefix="/catalog", tags=["catalog"])

CatalogDep = Annotated[Catalog, Depends(get_catalog)]
# The catalog only changes with a deploy (ADR 0002), so short public caching is safe.
CACHE_CONTROL = "public, max-age=300"
NOT_FOUND = "We couldn't find that product"


def _site_url(request: Request) -> str:
    return str(request.app.state.container.settings.site_url)


def _cache(response: Response, catalog: Catalog) -> None:
    response.headers["Cache-Control"] = CACHE_CONTROL
    response.headers["ETag"] = f'W/"{catalog.version[:16]}"'


@router.get("/categories", response_model=CategoriesOut)
async def list_categories(catalog: CatalogDep, response: Response) -> CategoriesOut:
    _cache(response, catalog)
    return CategoriesOut(
        items=[CategoryOut.from_domain(c) for c in catalog.categories()],
        textures=catalog.textures(),
    )


@router.get("/products", response_model=ProductPage)
async def list_products(
    request: Request,
    response: Response,
    catalog: CatalogDep,
    category: CategorySlug | None = None,
    texture: Annotated[str | None, Query(max_length=60)] = None,
    length: Annotated[int | None, Query(ge=1, le=100, description="Exact length in inches")] = None,
    length_range: Annotated[
        LengthRange | None,
        Query(description="Storefront buckets: 16 = 14-18in, 20 = 20-24, 26 = 26-30, 32 = 32+"),
    ] = None,
    min_price: Annotated[int | None, Query(ge=0)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    in_stock: bool | None = None,
    sort: Annotated[
        Sort,
        Query(description="`newest` matches the storefront: reverse product-id order"),
    ] = "featured",
    cursor: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> ProductPage:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise ValidationFailed(fields={"min_price": "Must not be greater than max_price"})
    offset = decode_offset(cursor)
    found = catalog.query(
        ProductQuery(
            category=category,
            texture=texture,
            length=length,
            length_range=length_range,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            sort=sort,
        )
    )
    page = found[offset : offset + limit]
    site_url = _site_url(request)
    _cache(response, catalog)
    return ProductPage(
        items=[ProductSummaryOut.from_domain(p, site_url) for p in page],
        next_cursor=encode_offset(offset + limit) if offset + limit < len(found) else None,
        total=len(found),
    )


@router.get("/search", response_model=SearchOut)
async def search(
    request: Request,
    response: Response,
    catalog: CatalogDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
) -> SearchOut:
    """Storefront search: name, description, subtitle, texture, origin, SKU and specs."""
    term = q.strip()
    if not term:
        raise ValidationFailed(fields={"q": "Enter something to search for"})
    found = catalog.query(ProductQuery(search=term))
    needle = term.lower()
    categories = [
        CategoryOut.from_domain(c)
        for c in catalog.categories()
        if needle in c.label.lower() or needle in c.slug
    ]
    site_url = _site_url(request)
    _cache(response, catalog)
    return SearchOut(
        items=[ProductSummaryOut.from_domain(p, site_url) for p in found[:limit]],
        total=len(found),
        categories=categories,
    )


SlugPath = Annotated[str, Path(min_length=1, max_length=120)]


@router.get("/products/{slug}", response_model=ProductOut, responses={404: {}})
async def get_product(
    slug: SlugPath, request: Request, response: Response, catalog: CatalogDep
) -> ProductOut:
    product = catalog.by_slug(slug)
    if product is None:
        raise NotFound(NOT_FOUND)
    _cache(response, catalog)
    return ProductOut.from_catalog(product, catalog, _site_url(request))


@router.get("/products/{slug}/related", response_model=list[ProductSummaryOut], responses={404: {}})
async def related_products(
    slug: SlugPath,
    request: Request,
    response: Response,
    catalog: CatalogDep,
    limit: Annotated[int, Query(ge=1, le=8)] = 4,
) -> list[ProductSummaryOut]:
    """ "Complete the Look": recommended pairing, then same category, then same texture."""
    product = catalog.by_slug(slug)
    if product is None:
        raise NotFound(NOT_FOUND)
    site_url = _site_url(request)
    _cache(response, catalog)
    return [ProductSummaryOut.from_domain(p, site_url) for p in catalog.related(product, limit)]
