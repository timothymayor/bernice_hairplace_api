"""The product catalog and its queries. Pure; parity-tested against the storefront.

The catalog stays in code for v1 (ADR 0002): `app/catalog/products.json` is exported from the web
repo's `src/data/products.ts`. Filtering, search and sorting mirror `CatalogView.tsx` exactly
(fixtures: tests/fixtures/parity_catalog.json).
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from app.domain.pricing import unit_price

Sort = Literal["featured", "price_asc", "price_desc", "newest", "rating"]
LengthRange = Literal["16", "20", "26", "32"]

# Storefront category groups (CatalogView): "frontals" also covers "closures".
CATEGORY_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "bundles": "Bundles",
        "wigs": "Wigs",
        "frontals": "Frontals & Closures",
        "care": "Hair Care",
    }
)
_CATEGORY_MEMBERS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "bundles": frozenset({"bundles"}),
        "wigs": frozenset({"wigs"}),
        "frontals": frozenset({"frontals", "closures"}),
        "care": frozenset({"care"}),
    }
)
# Length-filter buckets as the storefront defines them (inclusive inches).
LENGTH_RANGES: Mapping[str, tuple[int, int | None]] = MappingProxyType(
    {"16": (14, 18), "20": (20, 24), "26": (26, 30), "32": (32, None)}
)
# The storefront's cross-sell ("Add the recommended closure") always adds this length.
PAIRING_LENGTH = 16


@dataclass(frozen=True, slots=True)
class Pairing:
    name: str
    specs: str
    price: int
    image: str


@dataclass(frozen=True, slots=True)
class Product:
    id: str
    slug: str
    name: str
    subtitle: str
    category: str
    texture: str
    origin: str
    price: int
    original_price: int | None
    rating: float
    review_count: int
    sku: str
    description: str
    full_specs: Mapping[str, str]
    lengths: tuple[int, ...]
    default_length: int
    images: Mapping[str, str]
    badge: str | None
    secondary_badge: str | None
    is_bestseller: bool
    is_new_arrival: bool
    is_in_stock: bool
    in_stock_location: str | None
    donor_shade: str
    pairing: Pairing | None

    @classmethod
    def from_web(cls, raw: Mapping[str, Any]) -> "Product":
        """Builds a product from the web repo's `Product` shape (camelCase)."""
        pairing = raw.get("recommendedPairing")
        return cls(
            id=raw["id"],
            slug=raw["slug"],
            name=raw["name"],
            subtitle=raw["subtitle"],
            category=raw["category"],
            texture=raw["texture"],
            origin=raw["origin"],
            price=int(raw["price"]),
            original_price=raw.get("originalPrice"),
            rating=float(raw["rating"]),
            review_count=int(raw["reviewCount"]),
            sku=raw["sku"],
            description=raw["description"],
            full_specs=MappingProxyType(dict(raw["fullSpecs"])),
            lengths=tuple(int(n) for n in raw["lengths"]),
            default_length=int(raw["defaultLength"]),
            images=MappingProxyType(dict(raw["images"])),
            badge=raw.get("badge"),
            secondary_badge=raw.get("secondaryBadge"),
            is_bestseller=bool(raw.get("isBestseller", False)),
            is_new_arrival=bool(raw.get("isNewArrival", False)),
            is_in_stock=bool(raw["isInStock"]),
            in_stock_location=raw.get("inStockLocation"),
            donor_shade=raw["donorShade"],
            pairing=Pairing(**pairing) if pairing else None,
        )

    def price_at(self, length: int) -> int:
        return unit_price(self.price, self.default_length, length)

    @property
    def category_group(self) -> str:
        return next((g for g, m in _CATEGORY_MEMBERS.items() if self.category in m), self.category)

    def matches(self, query: str) -> bool:
        """Storefront search: case-insensitive substring over these fields (CatalogView)."""
        q = query.strip().lower()
        if not q:
            return True
        fields = (
            self.name,
            self.description,
            self.subtitle,
            self.texture,
            self.origin,
            self.sku,
            self.full_specs.get("origin", ""),
            self.full_specs.get("texture", ""),
            self.full_specs.get("bleachGrade", ""),
        )
        return any(q in f.lower() for f in fields)


@dataclass(frozen=True, slots=True)
class CategorySummary:
    slug: str
    label: str
    product_count: int


@dataclass(frozen=True, slots=True)
class ProductQuery:
    category: str | None = None
    search: str | None = None
    texture: str | None = None
    length: int | None = None
    length_range: LengthRange | None = None
    min_price: int | None = None
    max_price: int | None = None
    in_stock: bool | None = None
    sort: Sort = "featured"


class Catalog:
    """Immutable, in-memory catalog. Order of `products` is the storefront's "featured" order."""

    def __init__(self, products: Iterable[Product], *, version: str) -> None:
        self.products: tuple[Product, ...] = tuple(products)
        self.version = version
        self._by_id = {p.id: p for p in self.products}
        self._by_slug = {p.slug: p for p in self.products}
        if len(self._by_id) != len(self.products) or len(self._by_slug) != len(self.products):
            raise ValueError("Catalog ids and slugs must be unique")

    def get(self, product_id: str) -> Product | None:
        return self._by_id.get(product_id)

    def by_slug(self, slug: str) -> Product | None:
        return self._by_slug.get(slug)

    def textures(self) -> list[str]:
        return sorted({p.texture for p in self.products})

    def categories(self) -> list[CategorySummary]:
        """Category groups that actually have products ("only show filters backed by data")."""
        out = []
        for slug, label in CATEGORY_LABELS.items():
            count = sum(1 for p in self.products if p.category_group == slug)
            if count:
                out.append(CategorySummary(slug=slug, label=label, product_count=count))
        return out

    def query(self, q: ProductQuery) -> list[Product]:
        found = [p for p in self.products if _keep(p, q)]
        return _sort(found, q.sort)

    def recommended_pairing(self, product: Product) -> Product | None:
        """The product the storefront's cross-sell adds: the first frontal/closure."""
        if product.pairing is None:
            return None
        return next((p for p in self.products if p.category_group == "frontals"), None)

    def related(self, product: Product, limit: int = 4) -> list[Product]:
        """ "Complete the Look": the recommended pairing first, then in-stock products in the same
        category group, then the same texture. Not in the storefront today (new in the API)."""
        picks: list[Product] = []
        pairing = self.recommended_pairing(product)
        candidates: Sequence[Product | None] = (
            pairing,
            *(p for p in self.products if p.category_group == product.category_group),
            *(p for p in self.products if p.texture == product.texture),
        )
        seen = {product.id}
        for p in candidates:
            if p is None or p.id in seen or not p.is_in_stock:
                continue
            seen.add(p.id)
            picks.append(p)
            if len(picks) == limit:
                break
        return picks


def _keep(p: Product, q: ProductQuery) -> bool:
    if q.category and p.category_group != q.category:
        return False
    if q.search and not p.matches(q.search):
        return False
    if q.min_price is not None and p.price < q.min_price:
        return False
    if q.max_price is not None and p.price > q.max_price:
        return False
    if q.texture and p.texture != q.texture:
        return False
    if q.length is not None and q.length not in p.lengths:
        return False
    if q.length_range:
        low, high = LENGTH_RANGES[q.length_range]
        if not any(n >= low and (high is None or n <= high) for n in p.lengths):
            return False
    return not (q.in_stock and not p.is_in_stock)


def _sort(products: list[Product], sort: Sort) -> list[Product]:
    # Python's sort is stable, like Array.prototype.sort: ties keep catalog order.
    if sort == "price_asc":
        return sorted(products, key=lambda p: p.price)
    if sort == "price_desc":
        return sorted(products, key=lambda p: -p.price)
    if sort == "newest":
        # Storefront: b.id.localeCompare(a.id). Products have no dates, so "newest" is reverse
        # id order; equal to plain string order for the ids in use (pinned by parity fixtures).
        return sorted(products, key=lambda p: p.id, reverse=True)
    if sort == "rating":
        return sorted(products, key=lambda p: -p.rating)
    return list(products)
