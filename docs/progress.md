# Build progress

This is the living tracker for the phases in AGENTS.md §15 and BP §10. Update it at every checkpoint.

Last updated: 2026-10-06

## Phases

| # | Phase | Status | Notes |
|---|---|---|---|
| 0 | Discovery and ADRs | **Done**; some ADRs still Proposed | [ADRs](decisions/). 0001–0003 are Accepted; 0004–0006 are Proposed (see the open questions below) |
| 1 | Scaffold | **Done** (2026-10-06) | Checkpoint evidence: PR #2 CI. The image builds and passes Trivy; `/healthz` and `/readyz` are green against Postgres and Redis on a read-only root filesystem; the worker starts. PRs #1 and #2 are merged |
| 2 | Catalog, search and pricing (catalog in code, ADR 0002) | **Code complete**; checkpoint pending CI | **Parity suite: 1,030/1,030** (711 unit prices covering every product at lengths 0–60 plus its own lengths, 14 delivery fees, 220 priced baskets over both fulfilment methods, 33 validation cases, 51 storefront filter/search/sort queries, and a catalog-drift check). Endpoints: `/v1/catalog/{categories, products, products/{slug}, products/{slug}/related, search}` and `POST /v1/pricing/quote`. CI re-runs the web repo's code on every PR and fails on drift |
| 3 | Cart, wishlist, profile, forms | Not started | |
| 4 | Checkout, Paystack, state machine, webhook, email, reconciliation | Not started | |
| 5 | Orders, admin, account deletion | Not started | Blocked on ADRs 0005 and 0006 for the migrations |
| 6 | Hardening and load test | Not started | |
| 7 | Staging integration (web and mobile) | Not started | One repo, two environments: `main` → staging on Render (after CI passes); `v*` tags → production on Contabo (Phase 8). Waiting on the owner's Render setup (runbook) |
| 8 | Production cutover | Not started | |

## Open questions for the owner

1. **Hosting** (ADR 0003, decided): Render free for staging, Contabo for production. Supabase is in eu-west-1 (Ireland). Still needed: who controls DNS for `bernicehairplace.com`.
2. **Statuses** (ADR 0004). Should we confirm "no `refunded` status", with a refund shown as "Payment reversed"?
3. **Account deletion** (ADR 0005). We need:
   - the retention period (proposed: 6 years)
   - approval of the migration that makes `orders.user_id` nullable
   - a rule for undelivered orders
4. **Admin order management** (ADR 0006). Should we build an API endpoint, or keep Supabase Studio as the only tool? And should customers get an email when their order ships?
5. **Staging database.** Decided 2026-10-06: staging uses the current Supabase project (eu-west-1) for now. **Revisit before the Phase 3 PR merges**: from Phase 3, staging writes carts and profiles, and from Phase 4 test orders. A second free Supabase project for staging is recommended.
6. Who owns the Paystack and Mailgun accounts (BP §12)?

## How the UX spec maps onto the API

The UX spec (`bernice_hairplace_mobile_ui_ux_design_prompt.md`) predates the real backend. Where it disagrees with existing behaviour, AGENTS.md says existing behaviour wins. The table below shows what the API will do and what clients should show.

| UX spec says | API reality | Client guidance |
|---|---|---|
| Order number `ORD-XXXX` (§20, §23) | `BHP-YYYYMMDD-XXXXX` | Show the API value verbatim |
| Order status "Shipped"; payment `abandoned` / `refunded` (§41) | `in_transit`; normalized `abandoned`; no refunded state (ADR 0004) | Label `in_transit` as "Shipped" |
| Nigerian phone validation, +234 or 080 (§18) | Parity with the web: at least 7 digits | Clients may validate more strictly; the API accepts both formats |
| State dropdown of Nigerian states (§18) | Delivery is Lagos only; `state` is forced to "Lagos State" | Show Lagos as fixed text, not a dropdown |
| "Continue as guest" (§16) | Checkout requires sign-in; there is no guest checkout | Keep the guest bag on the device and call `POST /cart/merge` after sign-in |
| "Low Stock" badge (§9) | Only `is_in_stock` exists; there are no stock counts | Don't show "Low Stock". "Bestseller" (`is_bestseller`) and the `badge` field exist |
| Price or stock change flags in the bag (§15) | `/pricing/quote` and `/cart` return per-line flags | Clients may send the price they last displayed, used only to compute the flag, never for charging |
| Tax line (§17, §24) | No tax | Omit the tax line |
| Delivery timeframe (§17) | Not in the data | Use static copy shared with the web |
| Sort "Newest" (§11) | Products have no creation date. The storefront's "newest" is reverse product-id order, and the API matches it (parity) | Supported sorts: `featured`, `price_asc`, `price_desc`, `newest`, `rating`. Treat "Newest" as a display order, not a date |
| Search with SKU and category suggestions (§10) | `GET /v1/catalog/search`: the storefront's substring search over name, description, subtitle, texture, origin, SKU and specs, plus matching categories | Supported |
| "Complete the Look" (§31) | `GET /v1/catalog/products/{slug}/related`: the recommended pairing first, then the same category, then the same texture (in stock only). New behaviour; the storefront has no related logic | Supported |
| Length chips (§11) | `length` (exact inches) or `length_range` (storefront buckets: `16` = 14–18", `20` = 20–24", `26` = 26–30", `32` = 32"+) | Supported |
| Variant price on the product page (§12) | `length_prices` on product detail, computed on the server | Show these; never compute prices on the client |
| "Nearest landmark / delivery note" (§18) | `delivery_notes` (max 500 characters) is stored | Supported |
| Pending payment that refreshes automatically (§19) | Poll `GET /payments/{reference}`, which re-verifies until the state is final | Poll every 3–5 seconds, with backoff |
| Product images | Stored as web-relative paths (`/images/...`) | The API returns absolute URLs built from `SITE_URL` |
| Engineering alignment lists Next.js (§40) | This FastAPI service is the backend | Superseded |

## Known quirks in the web code

- **Recommended pairing** (mirrored): the storefront's cross-sell button adds the first frontal/closure product at a hard-coded 16", whatever `recommendedPairing` says. The API exposes the same product and length as `recommended_pairing.product_id` / `selected_length`, priced by the server.

- **Refund events** (not copied): `refund.processed` events carry `data.transaction_reference`, but the web handler reads `data.reference`, so it probably ignores refunds (ADR 0004). This will be confirmed with a test-mode refund in Phase 4.
