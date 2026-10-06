# Bernice Hairplace Backend API — Production Build Prompt

## Role

Act as a senior backend engineer and platform engineer working in Python, FastAPI, PostgreSQL/Supabase, Redis, Docker, payments and CI/CD. Design, build, test, containerize and deploy the **Bernice Hairplace API**. This one service powers the **web store** and the **iOS/Android app**, and it replaces the web repo's Vercel payment functions.

## Inputs

| Source | Use it for |
|---|---|
| Web repo `timothymayor/bernice_hairplace_web` | **Current behaviour to preserve**: the schema, pricing rules, order and payment logic, the webhook, and the email template |
| `bernice_hairplace_mobile_ui_ux_design_prompt.md` | The UX states and flows the API must support (payment states, cart persistence, order history, error copy) |
| `AGENTS.md` and `bernice_hairplace_mobile_app_production_prompt.md` | What mobile needs from the API: hosted Paystack checkout, Google and Apple sign-in, account deletion, demo/staging environments |

The mobile documents assumed a Next.js backend. The **actual** web store is React 19 + Vite, with Vercel functions in `api/paystack/*` and server modules in `server/*`. This API becomes the backend those documents refer to.

## What exists today (keep it working, then migrate it)

- **Supabase**: Postgres with RLS, set up by `supabase/migrations/20261006120000_initial_schema.sql`.
  - Tables: `profiles` (created by a trigger on `auth.users`), `orders`, `order_items`, `cart_items` (plus the `replace_cart(jsonb)` RPC), `wishlist_items`, `custom_wig_requests`, `newsletter_subscribers`.
  - Orders and order items are written **only by the service role**.
- **Catalog**: lives in code at `src/data/products.ts`. Each product has `id, slug, sku, category, texture, price, defaultLength, lengths[], images{…}, isInStock, …`.
- **Pricing** (`src/lib/pricing.ts`):
  - Unit price = base price + ₦15,000 per inch above `defaultLength`, or − ₦10,000 per inch below it (never below 0).
  - `courier_express` delivery costs ₦4,500, and is free from a ₦150,000 subtotal upwards. `studio_pickup` is free.
  - Delivery is Lagos only, in NGN only, with whole-naira integers. Paystack amounts are in kobo (naira × 100).
- **Order numbering**: `BHP-YYYYMMDD-XXXXX`, which is also the Paystack `reference`.
- **Statuses** (enforced by DB check constraints):
  - `orders.status`: `pending_payment, paid, processing, in_transit, delivered, payment_failed, payment_reversed, cancelled`
  - `orders.payment_status`: `initialized, pending, success, failed, reversed`
- **Payment flow**:
  1. `initialize` (requires a signed-in user) prices the bag on the server, inserts a `pending_payment` order with its items, saves the address to the profile, and returns the Paystack `access_code`. The web uses the Paystack Inline popup.
  2. `verify` and the `webhook` both re-fetch the transaction from Paystack.
  3. **Amount and currency are checked against the order.** Updates are conditional and idempotent (a paid order is never downgraded, except by a reversal).
  4. The Mailgun confirmation email is sent **exactly once**, using a claim on `confirmation_email_sent_at`. The claim is released if sending fails.
  5. The webhook checks an HMAC-SHA512 signature over the **raw body**, and handles `charge.success` and `refund.processed`.

---

## 1. Non-negotiables

1. **Behavioural parity first.** Before replacing anything, port the pricing, validation, order and payment logic with **parity tests** against the TypeScript behaviour.
2. **Server-authoritative money.** Clients send product ids, lengths, quantities, address and fulfilment method only. The API never trusts a client-sent price or total.
3. **Idempotency everywhere.** Each order is paid once and emailed once, and a client retry never causes a double charge. Verify and webhook may race safely.
4. **Payment success is decided only by verifying with Paystack.** Never trust event bodies or client callbacks.
5. **One schema, one migration system.** `supabase/migrations` is the source of truth, shared with the web repo. Don't add Alembic.
6. **Secrets stay server-side**, in a secrets manager or platform env. No secrets in images, logs or the repo. Test keys for staging, live keys for production only.
7. **The UI only shows states the backend can represent.** Any new status needs a migration, an ADR and approval.
8. Work in the phases in §10 and **stop at each checkpoint**.

## 2. Stack

| Concern | Choice |
|---|---|
| Runtime | Python 3.12+, managed with `uv` |
| Framework | FastAPI with Pydantic v2 and `pydantic-settings` |
| Server | Uvicorn workers under Gunicorn (or `uvicorn --workers`) |
| Database | Supabase Postgres via **SQLAlchemy 2.0 async + asyncpg** (Core/ORM). Connect through the Supabase pooler; in transaction mode set `statement_cache_size=0` |
| Auth | Supabase Auth. Verify access JWTs against the project **JWKS** (`/auth/v1/.well-known/jwks.json`, cached), falling back to the legacy HS256 secret only if the project still uses it. Check `exp`, `aud=authenticated` and `iss` |
| Cache, rate limiting, locks, jobs | Redis 7 with `redis-py` asyncio; background jobs with **arq** (Redis-backed) |
| HTTP client | `httpx.AsyncClient` with timeouts, retries and a circuit breaker for Paystack and Mailgun |
| Email | Mailgun HTTP API (US/EU region by configuration), templates ported from `server/emails.ts` |
| Observability | `structlog` JSON logs with request ids, Sentry, Prometheus `/metrics`, OpenTelemetry (optional) |
| Quality | ruff, mypy (strict), pytest + pytest-asyncio, respx (HTTP mocks), Testcontainers or the Supabase CLI local stack |
| Containers | Docker (multi-stage, slim, non-root) and docker-compose for local development |
| CI/CD | GitHub Actions, images in GHCR |

## 3. Architecture

```text
Web (Vite) ─┐                            ┌─► Supabase Postgres (RLS + service role)
Mobile app ─┼─► FastAPI  (/v1, stateless)┼─► Redis (cache, rate limits, locks, idempotency, job queue)
Paystack ───┘   (webhooks)               ├─► Paystack API
                     │                   └─► Mailgun API
                     └─► arq worker ─────► email sending, payment reconciliation, cleanup
```

Repo layout (new repo `bernice_hairplace_api`):

```text
app/
  main.py               # app factory, middleware, routers, lifespan
  core/                 # settings, logging, security (JWT), errors, rate limiting
  db/                   # engine/session, models, queries
  domain/               # pricing.py, orders.py, payments.py, catalog.py (pure, no I/O where possible)
  integrations/         # paystack.py, mailgun.py
  api/v1/               # routers: catalog, cart, wishlist, checkout, payments, orders, me, forms, admin, webhooks
  schemas/              # Pydantic request/response models
  workers/              # arq tasks + cron
  templates/emails/
tests/                  # unit, parity, integration, contract
supabase/migrations/    # synced with the web repo (or a shared submodule)
scripts/                # seed_catalog.py (from products.ts), seed_demo.py
Dockerfile  docker-compose.yml  .env.example  pyproject.toml
```

## 4. Data changes (migrations, each with an ADR and approval)

1. **Move the catalog into Postgres.** Web and mobile must share one catalog.
   - Tables: `products`, `product_lengths` (or a computed length list), `product_images`, `categories` and optionally `collections`.
   - Public read access through RLS. Writes are service-role or admin only.
   - Seed from `products.ts` with `scripts/seed_catalog.py`, keeping the same `id`, `sku` and `slug` so existing `cart_items`, `wishlist_items` and `order_items` stay valid.
   - Pricing rules move into a `pricing_rules` configuration (per-inch deltas, delivery fee, free-delivery threshold), and parity tests are kept.
2. **Payments audit table.** `payment_events` records each Paystack event and verification: reference, event, raw payload hash, status, amount and received_at, with a unique key for deduplication.
3. **Optional status additions** (only if approved, because the design spec references them):
   - `refunded` on `orders.status`, so that `refund.processed` has a target.
   - `abandoned` handling. Today an abandoned payment maps to `cancelled` with `payment_status=failed`; keep that unless you're told otherwise.
   - The UI label "Shipped" maps to `in_transit`.
4. **Account deletion**, which both app stores require. `orders.user_id` is `on delete restrict`, so deleting a user must **anonymise** their orders (keep the financial records, remove personal data) before deleting the `auth.users` row through the Admin API.
5. **Sign in with Apple** needs Supabase provider configuration only; no schema change.

Every migration must be backward-compatible with the live web store (expand, then contract) and tested on staging first.

## 5. API surface (`/v1`, JSON, OpenAPI is the contract)

Authentication is `Authorization: Bearer <supabase access token>` unless marked public.

| Area | Endpoints |
|---|---|
| Health | `GET /healthz` (liveness), `GET /readyz` (DB + Redis), `GET /metrics` (internal only) |
| Catalog (public, cached) | `GET /catalog/categories` · `GET /catalog/products?category=&texture=&length=&min_price=&max_price=&in_stock=&sort=featured\|newest\|price_asc\|price_desc&cursor=&limit=` · `GET /catalog/products/{slug}` · `GET /catalog/search?q=` (name, SKU, description; Postgres full-text plus trigram) · `GET /catalog/products/{slug}/related` |
| Pricing (public) | `POST /pricing/quote` takes items and a fulfilment method and returns server-priced lines, subtotal, delivery fee, total, and price/stock change flags |
| Cart | `GET /cart` · `PUT /cart` (replace, atomic) · `POST /cart/merge` (merges a guest cart on sign-in: sums quantities, caps at 20 per line, drops unavailable items, returns change flags) · `PATCH/DELETE /cart/items/{product_id}/{length}` |
| Wishlist | `GET /wishlist` · `PUT /wishlist/{product_id}` · `DELETE /wishlist/{product_id}` |
| Checkout & payments | `POST /checkout` (requires an `Idempotency-Key` header) validates input, prices the bag, creates the `pending_payment` order and its items, saves the profile address, initializes Paystack and returns `{order_number, reference, subtotal, delivery_fee, total, access_code, authorization_url}`. Web uses `access_code` (Inline popup); mobile uses `authorization_url` with `callback_url = PAYMENT_CALLBACK_URL` · `GET /payments/{reference}` re-verifies with Paystack when not final, applies the result idempotently and returns the normalized state · `POST /payments/{reference}/retry` starts a new attempt for a failed or cancelled order (new reference, same items, repriced) |
| Webhooks (public, signed) | `POST /webhooks/paystack` checks the raw-body HMAC-SHA512 against `x-paystack-signature`, deduplicates on `payment_events`, re-fetches from Paystack, applies the result and returns 2xx quickly (heavy work is queued) |
| Orders | `GET /orders?cursor=` · `GET /orders/{order_number}` (owner only; never expose raw Paystack data) |
| Me | `GET/PATCH /me` (profile, phone, default address) · `DELETE /me` (account deletion: anonymise, then delete; returns 202) |
| Forms (public, rate-limited) | `POST /custom-wig-requests` · `POST /newsletter` |
| Admin (role `admin` claim or allowlist) | `PATCH /admin/orders/{id}/status` (moves `paid → processing → in_transit → delivered`, sets `waybill_number`, records history, can trigger a status email) · catalog create/update |

Contract rules:
- Errors use one shape, `{"error": {"code", "message", "fields?"}}`, with customer-safe messages (copy from the design spec) and no stack traces.
- Pagination is cursor-based, money values are integers in NGN, and timestamps are ISO-8601 UTC.
- Publish `openapi.json` on every release, and generate typed clients for the web (TypeScript) and mobile (TypeScript) with `openapi-typescript`.

## 6. Payment state machine

Ported from `applyPaystackResult`, and serialized per order with a Redis lock (`lock:order:{reference}`) **plus** conditional SQL updates.

| Paystack result | `orders.status` / `payment_status` | Rule |
|---|---|---|
| `success` with amount = total × 100 and currency NGN | `paid` / `success`, plus `paid_at`, `payment_channel`, `paystack_transaction_id` | Update only if `payment_status <> 'success'`, then queue the confirmation email (claim-once) |
| `success` but the amount or currency doesn't match | unchanged | Log and alert; never mark the order paid |
| `failed` | `payment_failed` / `failed` | Never downgrade a paid order |
| `abandoned` | `cancelled` / `failed` | Never downgrade a paid order |
| `reversed` | `payment_reversed` / `reversed` | Allowed even after a payment succeeded |
| anything else | `pending_payment` / `pending` | — |

**Reconciliation** (an arq cron every 5 minutes) re-verifies orders stuck in `pending_payment` or `pending` for 10 minutes or more. Orders that are never confirmed are expired to `cancelled` after a configurable TTL.

Normalized state returned to clients: `awaiting_payment | processing_payment | paid | failed | abandoned | reversed | refunded?`, mapped exactly as in the design spec's payment and order state tables.

## 7. Redis usage

- **Rate limits** (sliding window): checkout 10/min per user, forms 5/min per IP, search 60/min per IP, webhook not limited (signature-gated).
- **Idempotency**: store the `Idempotency-Key` and request hash with the response for 24h; a replay returns the same response.
- **Caches**: JWKS (TTL 1h), catalog list/detail/search (TTL 5–10 min, invalidated on admin writes), pricing rules.
- **Locks**: per order reference for verify/webhook/reconcile.
- **Queue**: arq for emails (retry with backoff, dead-letter logging), reconciliation and account deletion.
- **Rules**: Redis is a cache and coordinator, never the source of truth. The API must degrade gracefully if Redis is down (skip caching, fall back to DB constraints for idempotency).

## 8. Security, privacy, reliability

- CORS allowlist covering the web domains, Vercel previews and Appetize/mobile (no browser origin needed).
- Security headers. Request size limits. Pydantic validation with strict string lengths, mirroring `parseCheckoutInput`.
- Every query is scoped to the authenticated user. Use the service role only inside the server.
- Never log raw tokens, card data, full addresses or phone numbers; mask personal data in logs and in Sentry.
- Timeouts on all outbound calls (Paystack 10s, Mailgun 10s). Retries are idempotent only.
- Graceful shutdown. Health and readiness probes. Database connection pool sized to the Supabase plan.
- Dependency scanning and container image scanning (Trivy) in CI.

## 9. Docker, environments, deployment

**Dockerfile**: a multi-stage `python:3.12-slim` build using `uv`, running as a non-root user, read-only filesystem where possible, with a `HEALTHCHECK` on `/healthz`. One image runs both roles:
- API: `gunicorn -k uvicorn.workers.UvicornWorker`
- Worker: `arq app.workers.WorkerSettings`

**docker-compose.yml** (local): `api`, `worker`, `redis:7-alpine`, plus the Supabase local stack via `supabase start` (or point at the staging project). Use `.env` for configuration.

**Environments**

| Env | Supabase | Paystack | Redis | Used by |
|---|---|---|---|---|
| local | Supabase CLI local stack | test | compose | developers |
| staging | staging project | test | managed | web previews, mobile demo/preview, Appetize |
| production | production project | **live** | managed | web production, store apps |

**Configuration** (`.env.example`):

```text
APP_ENV, LOG_LEVEL, CORS_ORIGINS, SITE_URL, PAYMENT_CALLBACK_URL
SUPABASE_URL, SUPABASE_JWKS_URL, SUPABASE_JWT_SECRET (legacy, optional), SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL
REDIS_URL
PAYSTACK_SECRET_KEY
MAILGUN_API_KEY, MAILGUN_DOMAIN, MAILGUN_FROM_EMAIL, MAILGUN_REGION, STORE_NOTIFICATION_EMAIL
SENTRY_DSN, PAYMENT_PENDING_TTL_MINUTES, RECONCILE_INTERVAL_MINUTES
```

**Hosting**: a container platform running an always-on API and worker in a region close to the Supabase project. The default is Fly.io or Render; Railway or Cloud Run (with min instances above 0) are alternatives. Use managed Redis (Upstash or the platform's own). Confirm the choice in Phase 0. Custom domain: `api.bernicehairplace.com` with TLS.

**CI/CD** (GitHub Actions):
1. On every PR: ruff, mypy, pytest (unit, parity, integration), Docker build, Trivy scan, and an OpenAPI diff (breaking changes fail).
2. On push to `main`: build, push to GHCR, **deploy to staging**, run smoke tests and a Paystack test-mode end-to-end checkout.
3. On `v*` tags: run migrations through `supabase db push`, gated by manual approval, then **deploy to production** (rolling or blue-green) and run smoke tests. Rollback means redeploying the previous image tag.

**Cutover from the Vercel functions** (zero downtime):
1. Deploy the API to staging. Point the **test-mode** Paystack webhook at `https://api-staging…/v1/webhooks/paystack`.
2. Switch the web repo's checkout calls to the API behind an env flag (`VITE_API_BASE_URL`). Accept `access_code` unchanged so the Inline popup keeps working.
3. In production, switch the web to the API, then move the **live** webhook URL to the API. Both implementations are idempotent on the same rows, so overlap is safe.
4. Keep the Vercel functions for one release as a fallback, then remove them.

## 10. Phases & checkpoints

| # | Phase | Checkpoint |
|---|---|---|
| 0 | Discovery: read the web repo, list behaviours, choose hosting, finalise the gap list and ADRs | Approval of the migrations in §4 and of hosting |
| 1 | Scaffold: app factory, settings, logging, errors, JWT auth, Redis, Docker/compose, CI | `/healthz` and `/readyz` green locally and in CI |
| 2 | Catalog in Postgres, seeded from `products.ts`; catalog and search endpoints; pricing with parity tests | Parity report (100% match on all products × lengths × fulfilment methods) |
| 3 | Cart, wishlist, profile, forms | Cart merge tests; RLS and ownership tests |
| 4 | Checkout, Paystack initialize/verify/webhook/retry, state machine, email worker, reconciliation | Race test showing verify + webhook concurrently → one `paid` update and one email; amount-mismatch test |
| 5 | Orders, admin status updates, account deletion | Owner-only access tests; anonymisation test |
| 6 | Hardening: rate limits, idempotency keys, observability, load test (k6: 50 RPS catalog, 5 RPS checkout, p95 under 300ms excluding Paystack) | Load and security report |
| 7 | Staging deploy, web integration behind a flag, mobile/Appetize pointed at staging | Full web and mobile test-card purchase on staging |
| 8 | Production migrations, deploy, webhook cutover, removal of the Vercel functions | Live smoke test, monitoring dashboards, runbook |

At each checkpoint, give a summary, any deviations, open questions, and test evidence.

## 11. Testing (what must be proven)

- **Pricing parity**: every catalog product × every length × both fulfilment methods equals the TypeScript output.
- **Checkout validation**: mirrors `parseCheckoutInput`, covering missing names, invalid email or phone, an empty bag, more than 50 lines, quantity outside 1–20, an invalid length, and an out-of-stock item.
- **Payments**: success, failure, abandoned, reversed, amount mismatch, unknown reference, invalid signature, duplicate webhook, verify/webhook race, a failed email that later retries and succeeds, and an idempotency-key replay.
- **Auth**: expired, wrong-audience and tampered tokens are rejected; one user can never read another user's order.
- **Account deletion**: personal data is removed, financial records are kept, and the user can no longer sign in.
- **Contract**: the OpenAPI schema is snapshotted, and the generated clients compile in the web and mobile repos.

## 12. Ask, don't guess

- Whether the catalog moves to Postgres now (recommended) or stays in code for v1.
- Which new statuses to add (`refunded`, a separate abandoned state).
- Hosting provider and region, plus the Redis provider.
- Whether a separate staging Supabase project exists, and who owns the Paystack and Mailgun accounts.
- How admins manage orders: through the API admin endpoints or through Supabase Studio (today's approach).
- Account-deletion retention policy (how long anonymised orders are kept).

## 13. Definition of done

1. The API runs in staging and production behind `api.bernicehairplace.com`, with health checks, metrics, Sentry and alerts (failed payments, webhook errors, amount mismatches, queue backlog).
2. The web store and the mobile app (including the Appetize demo) complete purchases through the API: test mode on staging, live mode in production.
3. Pricing parity is proven, payment idempotency is proven under concurrency, and every order is emailed exactly once.
4. The Vercel payment functions are retired, and the live Paystack webhook points to the API.
5. The OpenAPI contract is published, typed clients are generated, and CI/CD gates are green.
6. The README and runbook cover local setup, environments, migrations, deployment and rollback, webhook rotation, reconciliation, and incident steps for "customer paid but the order is not confirmed".
