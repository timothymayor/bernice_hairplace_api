# 0002 — The catalog stays in code for v1

- **Status:** Accepted (approved in Phase 0; this ADR was reconstructed on 2026-10-06 after a lost session)
- **Date:** 2026-10-06
- **Deviates from:** BP §4.1 (move the catalog into Postgres)

## Context

The catalog lives in the web repo's `src/data/products.ts` (11 products). BP §4.1 recommends moving it into Postgres (`products`, `product_lengths`, `product_images`, `categories`, `pricing_rules`), and BP §12 says to ask first.

Nobody edits the catalog except through code today, and there is no admin UI that needs a database.

## Decision

For v1, the API serves the catalog from `app/catalog/products.json`. `scripts/export_ts_fixtures.mjs` generates that file by running the web repo's own `products.ts`.

Pricing constants live in `app/domain/pricing.py`. There is no catalog migration in v1.

## Consequences

- Web and mobile still share one catalog, because both read it through the API.
- There is no `pricing_rules` table. Constants change through a code release, as they do today, and parity tests guard them.
- `/catalog/search` runs in memory over about 11 products instead of using Postgres full-text and trigram search. That's fine at this size; revisit when the catalog moves to Postgres.
- Catalog writes (BP §5 "admin catalog create/update") are **out of scope** for v1.
- `scripts/seed_catalog.py` isn't needed in v1.
- Drift risk: the web repo could change `products.ts` without re-exporting. From Phase 2, CI re-runs the exporter against the web repo and fails on any diff.
- Product ids, SKUs and slugs are unchanged, so a later move to Postgres keeps `cart_items`, `wishlist_items` and `order_items` valid.
