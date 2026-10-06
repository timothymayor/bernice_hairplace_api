# Build progress

This is the living tracker for the phases in AGENTS.md §15 and BP §10. Update it at every checkpoint.

Last updated: 2026-10-06

## Phases

| # | Phase | Status | Notes |
|---|---|---|---|
| 0 | Discovery and ADRs | **Done**; some ADRs still Proposed | [ADRs](decisions/). 0001 and 0002 are Accepted, 0003 is Deferred, and 0004–0006 are Proposed (see the open questions below) |
| 1 | Scaffold | **Code complete; checkpoint evidence pending** | App factory, health/readiness/metrics, DB session, middleware (request id, 1 MB body limit, security headers, CORS), JWT auth, Redis lock, arq worker heartbeat, Dockerfile, compose, Makefile, CI. 39 tests green; ruff and mypy --strict clean. Pending: `/readyz` green against real Postgres + Redis (needs Docker or Supabase CLI locally, or the first CI run) |
| 2 | Catalog, search and pricing (catalog in code, ADR 0002) | Not started | Parity fixtures have already been exported to `tests/fixtures/` |
| 3 | Cart, wishlist, profile, forms | Not started | |
| 4 | Checkout, Paystack, state machine, webhook, email, reconciliation | Not started | |
| 5 | Orders, admin, account deletion | Not started | Blocked on ADRs 0005 and 0006 for the migrations |
| 6 | Hardening and load test | Not started | |
| 7 | Staging integration (web and mobile) | Not started | Staging: Render free tier, Frankfurt (`render.yaml`, ADR 0003); waiting on the owner's Render sign-up (runbook). Production: Contabo (Phase 8) |
| 8 | Production cutover | Not started | |

## Open questions for the owner

1. **Hosting** (ADR 0003, decided): Render free for staging, Contabo for production. Supabase is in eu-west-1 (Ireland). Still needed: who controls DNS for `bernicehairplace.com`.
2. **Statuses** (ADR 0004). Should we confirm "no `refunded` status", with a refund shown as "Payment reversed"?
3. **Account deletion** (ADR 0005). We need:
   - the retention period (proposed: 6 years)
   - approval of the migration that makes `orders.user_id` nullable
   - a rule for undelivered orders
4. **Admin order management** (ADR 0006). Should we build an API endpoint, or keep Supabase Studio as the only tool? And should customers get an email when their order ships?
5. Is there a separate **staging Supabase project**, and who owns the Paystack and Mailgun accounts (BP §12)?

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
| Sort "Newest" (§11) | Products have no creation date | Not supported in v1 (the API rejects it). Supported sorts: featured, price_asc, price_desc |
| Search with SKU and category suggestions (§10) | In-memory search over name, SKU, description and category (ADR 0002) | Supported |
| "Complete the Look" (§31) | `GET /catalog/products/{slug}/related` | Supported |
| "Nearest landmark / delivery note" (§18) | `delivery_notes` (max 500 characters) is stored | Supported |
| Pending payment that refreshes automatically (§19) | Poll `GET /payments/{reference}`, which re-verifies until the state is final | Poll every 3–5 seconds, with backoff |
| Product images | Stored as web-relative paths (`/images/...`) | The API returns absolute URLs built from `SITE_URL` |
| Engineering alignment lists Next.js (§40) | This FastAPI service is the backend | Superseded |

## Known parity issues in the web code (not copied)

- `refund.processed` events carry `data.transaction_reference`, but the web handler reads `data.reference`, so it probably ignores refunds (ADR 0004). This will be confirmed with a test-mode refund in Phase 4.
