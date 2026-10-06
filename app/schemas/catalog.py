"""Catalog response models. Prices are server-computed whole naira; clients never derive them."""

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.catalog import PAIRING_LENGTH, Catalog, CategorySummary, Product
from app.domain.pricing import CURRENCY

CategorySlug = Literal["bundles", "wigs", "frontals", "care"]


def absolute_url(site_url: str, path: str) -> str:
    """Catalog images are web-relative (`/images/...`); clients need absolute URLs."""
    if path.startswith(("http://", "https://")):
        return path
    return f"{site_url.rstrip('/')}/{path.lstrip('/')}"


class CategoryOut(BaseModel):
    slug: CategorySlug
    label: str
    product_count: int

    @classmethod
    def from_domain(cls, c: CategorySummary) -> "CategoryOut":
        return cls(slug=c.slug, label=c.label, product_count=c.product_count)


class CategoriesOut(BaseModel):
    items: list[CategoryOut]
    textures: list[str] = Field(description="Texture filter values that have products")


class ProductSummaryOut(BaseModel):
    id: str
    slug: str
    name: str
    subtitle: str
    category: CategorySlug
    texture: str
    sku: str
    price: int = Field(description="Price at default_length, in whole naira")
    original_price: int | None
    currency: Literal["NGN"] = CURRENCY
    rating: float
    review_count: int
    image: str
    badge: str | None
    is_bestseller: bool
    is_new_arrival: bool
    is_in_stock: bool
    lengths: list[int]
    default_length: int

    @classmethod
    def from_domain(cls, p: Product, site_url: str) -> "ProductSummaryOut":
        return cls(**_summary_fields(p, site_url))


class ImagesOut(BaseModel):
    main: str
    luster: str
    weft: str
    cuticle: str
    styled: str


class FullSpecsOut(BaseModel):
    origin: str
    texture: str
    weight: str
    weft: str
    lifespan: str
    bleach_grade: str


class LengthPriceOut(BaseModel):
    length: int
    price: int


class PairingOut(BaseModel):
    name: str
    specs: str
    image: str
    product_id: str | None = Field(description="Add this product to the bag to buy the pairing")
    selected_length: int | None
    price: int = Field(description="Server price of product_id at selected_length")


class ProductOut(ProductSummaryOut):
    description: str
    origin: str
    full_specs: FullSpecsOut
    images: ImagesOut
    length_prices: list[LengthPriceOut]
    secondary_badge: str | None
    in_stock_location: str | None
    donor_shade: str
    recommended_pairing: PairingOut | None

    @classmethod
    def from_catalog(cls, p: Product, catalog: Catalog, site_url: str) -> "ProductOut":
        specs = p.full_specs
        return cls(
            **_summary_fields(p, site_url),
            description=p.description,
            origin=p.origin,
            full_specs=FullSpecsOut(
                origin=specs["origin"],
                texture=specs["texture"],
                weight=specs["weight"],
                weft=specs["weft"],
                lifespan=specs["lifespan"],
                bleach_grade=specs["bleachGrade"],
            ),
            images=ImagesOut(**{k: absolute_url(site_url, v) for k, v in p.images.items()}),
            length_prices=[LengthPriceOut(length=n, price=p.price_at(n)) for n in p.lengths],
            secondary_badge=p.secondary_badge,
            in_stock_location=p.in_stock_location,
            donor_shade=p.donor_shade,
            recommended_pairing=_pairing(p, catalog, site_url),
        )


def _summary_fields(p: Product, site_url: str) -> dict[str, object]:
    return {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "subtitle": p.subtitle,
        "category": p.category_group,
        "texture": p.texture,
        "sku": p.sku,
        "price": p.price,
        "original_price": p.original_price,
        "rating": p.rating,
        "review_count": p.review_count,
        "image": absolute_url(site_url, p.images["main"]),
        "badge": p.badge,
        "is_bestseller": p.is_bestseller,
        "is_new_arrival": p.is_new_arrival,
        "is_in_stock": p.is_in_stock,
        "lengths": list(p.lengths),
        "default_length": p.default_length,
    }


def _pairing(p: Product, catalog: Catalog, site_url: str) -> PairingOut | None:
    if p.pairing is None:
        return None
    target = catalog.recommended_pairing(p)
    buyable = target is not None and target.is_in_stock and PAIRING_LENGTH in target.lengths
    return PairingOut(
        name=p.pairing.name,
        specs=p.pairing.specs,
        image=absolute_url(site_url, p.pairing.image),
        product_id=target.id if buyable and target else None,
        selected_length=PAIRING_LENGTH if buyable else None,
        price=target.price_at(PAIRING_LENGTH) if buyable and target else p.pairing.price,
    )


class ProductPage(BaseModel):
    items: list[ProductSummaryOut]
    next_cursor: str | None
    total: int = Field(description="Number of products matching the filters")


class SearchOut(BaseModel):
    items: list[ProductSummaryOut]
    total: int
    categories: list[CategoryOut] = Field(description="Categories whose name matches the query")
