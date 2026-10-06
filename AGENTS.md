# AGENTS.md — Bernice Hairplace API

Instructions for AI coding agents (and humans) working in this repository. Read this fully before writing code.

---

## 0. Mission

Build, test, containerize and deploy the **Bernice Hairplace API**. This is one FastAPI service that powers:

- the **web store**: `timothymayor/bernice_hairplace_web` (React 19 + Vite, on Vercel)
- the **mobile app**: Expo iOS/Android, plus the Appetize demo

It **replaces** the web repo's Vercel functions `api/paystack/{initialize,verify,webhook}.ts` and the server modules in `server/*`.

### Sources of truth

| Topic | Source |
|---|---|
| Scope, endpoints, phases, definition of done | `docs/bernice_hairplace_backend_api_production_prompt.md` (the **Backend Prompt**; references look like **[BP §N]**) |
| Current behaviour to preserve | Web repo: `supabase/migrations/*`, `server/orders.ts`, `server/paystack.ts`, `server/emails.ts`, `src/lib/pricing.ts`, `src/data/products.ts`, `src/types/index.ts` |
| UX states the API must support | `docs/bernice_hairplace_mobile_ui_ux_design_prompt.md` |
| Mobile client needs | Mobile `AGENTS.md` and `bernice_hairplace_mobile_app_production_prompt.md` |
| Rules for working in this repo | This file |

If they conflict: **this file > Backend Prompt > other docs**. Existing web behaviour wins over the docs unless an approved ADR says otherwise.

---

## 1. Golden rules

1. **Parity before change.** Port the web logic exactly, prove it with parity tests, and only then extend it.
2. **The server owns money.** Clients send `product_id`, `selected_length`, `quantity`, the address and the fulfilment method. Never accept a client price or total.
3. **Idempotent payments.** Each order is paid once and emailed once. Verify, webhook and reconcile can run concurrently and safely.
4. **Payment success is decided only by `GET /transaction/verify/:reference` at Paystack.** Never trust webhook bodies or client redirects.
5. **One migration system:** `supabase/migrations/`, shared with the web repo. **No Alembic.** Never edit an applied migration; add a new one.
6. **Backward-compatible schema changes** (expand → migrate → contract). The live web store must keep working at every step.
7. **No secrets** in code, images, logs, fixtures or the OpenAPI examples.
8. **Represent only real states.** New statuses need a migration, an ADR and human approval.
9. **Ask, don't guess** on anything listed in §16.
10. **Stop at each phase checkpoint** (§15) with a summary, deviations, open questions and test evidence.

---

## 2. Stack

| Concern | Choice |
|---|---|
| Language/runtime | Python **3.12+**, dependency management with **uv** |
| Framework | FastAPI, Pydantic v2, pydantic-settings |
| Server | Gunicorn + `uvicorn.workers.UvicornWorker` |
| Database | Supabase Postgres via **SQLAlchemy 2.0 async + asyncpg** |
| Auth | Supabase JWT verified with **PyJWT** against the project JWKS (cached in Redis); legacy HS256 fallback only if configured |
| Redis | `redis.asyncio` for cache, rate limits, locks and idempotency |
| Jobs | **arq** worker and cron (emails, reconciliation, account deletion) |
| HTTP | `httpx.AsyncClient` with explicit timeouts and bounded retries |
| Email | Mailgun HTTP API with Jinja2 templates (ported from `server/emails.ts`) |
| Observability | structlog (JSON), Sentry, `prometheus-fastapi-instrumentator`, optional OpenTelemetry |
| Quality | ruff (lint + format), mypy `--strict`, pytest, pytest-asyncio, respx, hypothesis (pricing), Testcontainers/Supabase CLI |
| Containers | Docker multi-stage, non-root; docker-compose for local |
| CI/CD | GitHub Actions; images in GHCR |

Pin versions in `pyproject.toml`; commit `uv.lock`.

---

## 3. Repository layout

```text
app/
  main.py                    # create_app(): middleware, routers, exception handlers, lifespan
  core/
    config.py                # Settings (pydantic-settings), validated at startup
    logging.py               # structlog config, PII masking processor
    security.py              # JWT verification, CurrentUser dependency, admin guard
    errors.py                # AppError hierarchy → {"error": {...}}
    ratelimit.py             # Redis sliding-window limiter dependency
    idempotency.py           # Idempotency-Key middleware/dependency
    redis.py                 # pool, lock helper
  db/
    session.py               # async engine (pooler-safe), session dependency
    models.py                # SQLAlchemy models mirroring supabase/migrations
    repositories/            # catalog.py, orders.py, carts.py, profiles.py, payments.py
  domain/                    # PURE logic (no I/O): pricing.py, checkout.py, payment_state.py, order_number.py
  integrations/
    paystack.py              # initialize, verify, signature check
    mailgun.py
  api/v1/
    catalog.py  pricing.py  cart.py  wishlist.py  checkout.py  payments.py
    orders.py   me.py       forms.py admin.py     webhooks.py  health.py
  schemas/                   # Pydantic request/response models (one module per router)
  services/                  # orchestration: checkout_service.py, payment_service.py, account_service.py
  workers/
    settings.py              # arq WorkerSettings, cron jobs
    tasks.py                 # send_order_email, reconcile_pending_payments, delete_account
  templates/emails/
tests/
  unit/  parity/  integration/  contract/  fixtures/
supabase/migrations/         # shared with web repo (see §6)
scripts/
  seed_catalog.py            # imports products.ts export → Postgres
  export_ts_fixtures.mjs     # emits parity fixtures from the web repo's TS code
  seed_demo.py               # staging-only demo data
docs/
  bernice_hairplace_backend_api_production_prompt.md
  bernice_hairplace_mobile_ui_ux_design_prompt.md
  decisions/                 # ADRs: NNNN-title.md
  runbook.md
Dockerfile  docker-compose.yml  Makefile  pyproject.toml  uv.lock  .env.example
```

Layering rule: `api` → `services` → (`domain`, `db/repositories`, `integrations`). `domain` imports nothing from `db`, `api` or `integrations`. Routers contain no business logic.

---

## 4. Commands

```bash
make setup        # uv sync --all-extras && pre-commit install
make dev          # docker compose up redis && uvicorn app.main:create_app --factory --reload
make worker       # arq app.workers.settings.WorkerSettings
make up           # docker compose up --build  (api + worker + redis)
make lint         # ruff check . && ruff format --check .
make fmt          # ruff format . && ruff check --fix .
make typecheck    # mypy app tests
make test         # pytest -q
make test-int     # pytest -m integration (needs `supabase start` or Testcontainers)
make parity       # node scripts/export_ts_fixtures.mjs && pytest tests/parity
make openapi      # python -m app.scripts.dump_openapi > openapi.json
make migrate      # supabase db push   (staging/prod only through CI, see §13)
make seed         # python scripts/seed_catalog.py
```

Before declaring any task done, run `make lint typecheck test`. Also run `make parity` if you touched pricing, checkout or catalog code, and `make openapi` if you touched schemas or routers.

---

## 5. Behaviour to preserve (ported from the web repo)

### Pricing (`domain/pricing.py`)

```python
PRICE_PER_INCH_LONGER = 15_000
PRICE_PER_INCH_SHORTER = 10_000
EXPRESS_DELIVERY_FEE = 4_500
FREE_DELIVERY_THRESHOLD = 150_000

def unit_price(base: int, default_length: int, length: int) -> int:
    diff = length - default_length
    adj = diff * PRICE_PER_INCH_LONGER if diff > 0 else diff * PRICE_PER_INCH_SHORTER
    return max(base + adj, 0)

def delivery_fee(subtotal: int, method: Literal["courier_express", "studio_pickup"]) -> int:
    if method != "courier_express":
        return 0
    return 0 if subtotal >= FREE_DELIVERY_THRESHOLD else EXPRESS_DELIVERY_FEE
```

- Money is **whole-naira `int`** everywhere. Kobo = `naira * 100`, computed only at the Paystack boundary. **Never use floats.**
- Once the catalog moves to Postgres, the constants come from `pricing_rules`. The function signatures and the parity tests stay the same.

### Checkout validation (mirror `parseCheckoutInput`)

- Strip all strings and cap their lengths: firstName/lastName 80, email 254, phone 40, streetAddress 200, suiteFlat 100, district 80, deliveryNotes 500.
- `state` is forced to `"Lagos State"` and `country` to `"Nigeria"`.
- Fulfilment is `studio_pickup`, otherwise defaults to `courier_express`. `streetAddress` is required for courier delivery.
- Email must match the regex; phone must have at least 7 digits.
- Items: between 1 and 50 lines; `quantity` is an int from 1 to 20; `selected_length` must be in the product's `lengths`; the product must exist and be `is_in_stock`.
- Error messages are customer-safe and reuse the web copy (e.g. "Your bag is empty", "An item in your bag is no longer available").

### Order number and reference

`BHP-YYYYMMDD-XXXXX` (5 uppercase base-36 characters), also used as the Paystack `reference`. Generate it with `secrets`, not `random`. On a unique-violation, retry up to 3 times.

### Statuses (DB check constraints; do not change without an ADR)

```text
orders.status:          pending_payment | paid | processing | in_transit | delivered
                        | payment_failed | payment_reversed | cancelled
orders.payment_status:  initialized | pending | success | failed | reversed
```

The UI label "Shipped" maps to `in_transit`. `refunded` and a distinct "abandoned" status do **not** exist yet ([BP §4]).

---

## 6. Database & migrations

- `supabase/migrations/` mirrors the web repo. Sync **from** the web repo before adding a migration. New migrations land in **both** repos (or in a shared submodule, decided in the Phase 0 ADR).
- Naming: `YYYYMMDDHHMMSS_short_description.sql`. Each migration is idempotent where feasible, includes RLS policies for new tables, and comes with an ADR.
- Planned migrations ([BP §4]):
  - `catalog`: `products`, `product_lengths`, `product_images`, `categories`, `pricing_rules`. Public read through RLS; seeded from `products.ts` with the **same ids, skus and slugs**.
  - `payment_events`: audit log plus dedupe, `unique(reference, event, payload_sha256)`.
  - `order_status_history`: admin and system transitions.
  - Account deletion support (anonymise orders; `orders.user_id` is `on delete restrict`).
  - Optional, **only if approved**: `refunded` status.
- Models in `db/models.py` must match the migrations exactly. An integration test compares reflected DB columns to the models.

**Connection (Supabase pooler):**

```python
engine = create_async_engine(
    settings.database_url,             # postgresql+asyncpg://...pooler.supabase.com:6543/postgres
    pool_size=settings.db_pool_size, max_overflow=5, pool_pre_ping=True,
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
)
```

The API connects with service-level DB credentials. **Every user-scoped query must filter by `user_id = current_user.id` in code.** RLS is a second line of defence, not the only one.

---

## 7. Auth

```python
async def get_current_user(token = Depends(bearer)) -> CurrentUser:
    # 1) get signing key from cached JWKS (Redis, TTL 1h; refetch once on kid miss)
    # 2) jwt.decode(token, key, algorithms=["ES256","RS256"], audience="authenticated",
    #               issuer=f"{SUPABASE_URL}/auth/v1", options={"require": ["exp","sub","aud"]})
    # 3) fallback HS256 with SUPABASE_JWT_SECRET only if configured
    # → CurrentUser(id=sub, email=..., role=app_metadata.role)
```

- Missing or invalid token → 401 `{"error":{"code":"unauthorized","message":"Please sign in to continue"}}`.
- Admin endpoints require `app_metadata.role == "admin"` (set only through the service role). Never use `user_metadata` for authorization.
- Google and Apple sign-in are configured in Supabase. The API has no OAuth code.

---

## 8. Payments (the critical path)

### Initialize (`POST /v1/checkout`, requires `Idempotency-Key`)

1. Validate input (§5). Price from the DB catalog.
2. In **one transaction**, insert `orders` (`pending_payment`/`initialized`) and `order_items`, and update the profile's phone, name and default address.
3. Call Paystack `transaction/initialize` with `email`, `amount = total*100`, `reference`, `currency=NGN`, `callback_url = PAYMENT_CALLBACK_URL` and `metadata` (order_id, order_number, user_id, custom_fields as in the web code).
4. If Paystack fails: mark the order `cancelled`/`failed` and return 502 "Could not start payment. Please try again."
5. Return `{order_number, reference, subtotal, delivery_fee, total, access_code, authorization_url}`.

### Verify / webhook / reconcile all call one function

```python
async def apply_paystack_result(reference: str) -> Order:
    async with redis_lock(f"lock:order:{reference}", timeout=30):
        order = await orders.get_by_reference(reference)
        tx = await paystack.verify(reference)          # always re-fetch
        await payment_events.record(reference, source, tx)
        new = payment_state.transition(order, tx)      # pure function, see table
        if new: order = await orders.conditional_update(order.id, new)   # SQL WHERE guards
        if order.payment_status == "success":
            await queue.enqueue("send_order_email", order.id, _job_id=f"email:{order.id}")
        return order
```

### Transition table (`domain/payment_state.py`, exhaustively unit-tested)

| Paystack `status` | Guard | New `status` / `payment_status` |
|---|---|---|
| `success`, amount == total×100, currency NGN | `payment_status <> 'success'` | `paid` / `success` (+ `paid_at`, `payment_channel`, `paystack_transaction_id`) |
| `success`, amount or currency mismatch | — | **no change**; log `payment.amount_mismatch` at error level and alert |
| `failed` | `payment_status <> 'success'` | `payment_failed` / `failed` |
| `abandoned` | `payment_status <> 'success'` | `cancelled` / `failed` |
| `reversed` | none | `payment_reversed` / `reversed` |
| other | `payment_status <> 'success'` | `pending_payment` / `pending` |

The guards are enforced **in SQL** (`UPDATE … WHERE id=:id AND payment_status <> 'success' RETURNING *`), not just in Python.

### Email exactly once (port of `sendConfirmationOnce`)

```sql
UPDATE orders SET confirmation_email_sent_at = now()
WHERE id = :id AND confirmation_email_sent_at IS NULL
RETURNING id;
```

Only the caller that gets a row back sends the email. If the send fails, set `confirmation_email_sent_at = NULL` again and let arq retry with backoff. BCC `STORE_NOTIFICATION_EMAIL` if it's set.

### Webhook (`POST /v1/webhooks/paystack`)

```python
raw = await request.body()                                   # raw bytes, before any parsing
expected = hmac.new(PAYSTACK_SECRET_KEY.encode(), raw, hashlib.sha512).hexdigest()
if not hmac.compare_digest(expected, request.headers.get("x-paystack-signature", "")):
    raise Unauthorized
```

- Handle `charge.success` and `refund.processed`; acknowledge every other event with 200.
- An unknown reference returns 200 `{received: true}`.
- Processing errors return **500**, so Paystack retries.
- Respond fast: verify the signature, record the event, process under the lock, and leave slow work (email) to the queue.
- No auth, no rate limit, and excluded from CORS.

### Reconciliation (arq cron, every `RECONCILE_INTERVAL_MINUTES`)

Re-verify orders in `pending_payment` with `payment_status IN ('initialized','pending')` that are older than 10 minutes. Expire orders older than `PAYMENT_PENDING_TTL_MINUTES` to `cancelled`/`failed`, but only after a final verify.

### Normalized client state (`GET /v1/payments/{reference}`)

`awaiting_payment | processing_payment | paid | failed | abandoned | reversed`. Map from the DB pair in one function, and share it with the OpenAPI enum. Clients poll this endpoint; it re-verifies only when the state isn't final.

---

## 9. API conventions

- Prefix: `/v1`. Resource names are plural nouns; JSON fields are `snake_case`.
- Money: integers in NGN, with `currency: "NGN"` on order and quote payloads.
- Timestamps: ISO-8601 UTC.
- Pagination: `?cursor=&limit=` (default 20, max 50) → `{items, next_cursor}`.
- Errors: always `{"error": {"code": "snake_case", "message": "Customer-safe text", "fields": {...}?}}`. Raise `AppError` subclasses; one exception handler serializes them. Never leak stack traces, SQL or Paystack raw responses.
- Status codes: 400 validation, 401 unauthenticated, 403 forbidden, 404 not found (also for another user's resources), 409 conflict or idempotency mismatch, 422 never (map Pydantic errors to 400 with `fields`), 429 rate limited (with `Retry-After`), 502 upstream failure, 503 not configured or not ready.
- Idempotency: `POST /checkout`, `POST /payments/{ref}/retry` and `DELETE /me` require `Idempotency-Key` (a UUID). Store `{key, user_id, request_sha256, status, body}` in Redis for 24h. The same key with a different body → 409.
- Every response carries `X-Request-ID` (generated if not received).
- Endpoint list: [BP §5]. Don't add endpoints outside it without noting them in the checkpoint.

---

## 10. Redis

| Use | Key pattern | TTL |
|---|---|---|
| JWKS cache | `jwks:{project}` | 1h |
| Catalog cache | `cat:v{n}:list:{hash}`, `cat:v{n}:product:{slug}` | 5–10 min; bump `v{n}` on admin write |
| Rate limit | `rl:{scope}:{id}:{window}` | window |
| Idempotency | `idem:{user}:{key}` | 24h |
| Order lock | `lock:order:{reference}` | 30s |
| Jobs | arq default queue | — |

Limits: checkout 10/min per user, search 60/min per IP, forms 5/min per IP, everything else 120/min per IP.

**If Redis is down:** skip the cache, allow requests through the limiter with a warning log, keep idempotency through DB uniqueness (`payment_reference`) and the SQL guards, and run without the lock (the SQL guards still protect correctness). `/readyz` reports Redis as degraded, not failed.

---

## 11. Security & privacy checklist (every PR)

- [ ] New user-scoped queries filter by `current_user.id`
- [ ] Inputs have Pydantic length/range limits; request body ≤ 1 MB
- [ ] No secrets or personal data in logs (the structlog processor masks `email`, `phone`, `address`, `authorization`, `token`)
- [ ] Outbound calls have timeouts; retries only on idempotent operations
- [ ] CORS stays an allowlist (`CORS_ORIGINS`); no `*` with credentials
- [ ] Admin routes are guarded by role
- [ ] Paystack raw payloads are never returned to clients
- [ ] New env vars added to `Settings`, `.env.example` and the deploy config

---

## 12. Testing

| Suite | Must cover |
|---|---|
| `unit/` | pricing, checkout validation, order-number format, the payment transition table (every row), normalized state mapping, error serialization |
| `parity/` | Fixtures generated from the web repo's TypeScript (`scripts/export_ts_fixtures.mjs`): every product × length × fulfilment → identical unit price, delivery fee and total; the validation cases produce the same accept/reject decisions |
| `integration/` | real Postgres + Redis: checkout creates the order and items atomically; **verify + webhook race → one `paid` update and one email**; amount mismatch → no change; invalid signature → 401; duplicate webhook → no-op; email failure then retry → sent once; idempotency replay; reconciliation; cart merge; owner-only order access; account deletion anonymises the data |
| `contract/` | OpenAPI snapshot; a breaking diff fails CI unless the version is bumped |

Mock Paystack and Mailgun with **respx**; never call live services in tests. Mark slow tests `@pytest.mark.integration`. Hypothesis is used for pricing bounds (price is never negative).

---

## 13. Docker, environments, CI/CD

### Dockerfile (pattern)

```dockerfile
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
RUN uv sync --frozen --no-dev

FROM python:3.12-slim
RUN useradd -r -u 10001 app
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/healthz')"
CMD ["gunicorn","app.main:create_app()","-k","uvicorn.workers.UvicornWorker","-b","0.0.0.0:8000","--graceful-timeout","30"]
```

The worker uses the same image: `arq app.workers.settings.WorkerSettings`.

### docker-compose (local)

Services: `api`, `worker`, `redis:7-alpine`. Postgres comes from `supabase start` (local stack) or the staging project, set through `.env`.

### Environments

| Env | Supabase | Paystack | Notes |
|---|---|---|---|
| local | Supabase CLI | test | `.env` |
| staging | staging project | **test** | web previews, mobile demo, Appetize |
| production | production project | **live** | web production, store apps |

The settings validator **refuses to start** if `APP_ENV != production` and the Paystack key starts with `sk_live_`, or if `APP_ENV == production` and it starts with `sk_test_`.

### Required env (`.env.example`)

```text
APP_ENV LOG_LEVEL CORS_ORIGINS SITE_URL PAYMENT_CALLBACK_URL
SUPABASE_URL SUPABASE_JWKS_URL SUPABASE_JWT_SECRET SUPABASE_SERVICE_ROLE_KEY DATABASE_URL DB_POOL_SIZE
REDIS_URL
PAYSTACK_SECRET_KEY
MAILGUN_API_KEY MAILGUN_DOMAIN MAILGUN_FROM_EMAIL MAILGUN_REGION STORE_NOTIFICATION_EMAIL
SENTRY_DSN PAYMENT_PENDING_TTL_MINUTES RECONCILE_INTERVAL_MINUTES
```

### CI/CD (GitHub Actions)

- **PR:** lint, typecheck, unit, parity, integration (services: postgres via the Supabase CLI, redis), Docker build, Trivy scan, OpenAPI diff.
- **Push to `main`:** push the image `ghcr.io/<org>/bernice-hairplace-api:<sha>`, deploy to **staging**, run smoke tests and an end-to-end test-mode checkout.
- **Tag `v*`:** manual approval → `supabase db push` (production) → deploy to **production** (rolling) → smoke tests. Rollback = redeploy the previous tag. Migrations must be backward-compatible, so a rollback never needs a down-migration.
- **Hosting:** a container platform with an always-on API and worker near the Supabase region (default Fly.io or Render, decided in the Phase 0 ADR) and managed Redis. Domain: `api.bernicehairplace.com`.

### Cutover from Vercel ([BP §9])

1. Deploy to staging and point the **test-mode** Paystack webhook at `/v1/webhooks/paystack` on staging.
2. Have the web repo call the API behind `VITE_API_BASE_URL`. The `access_code` response keeps the Paystack Inline popup working.
3. In production, switch web traffic to the API, then move the **live** webhook URL. The old and new handlers are idempotent on the same rows, so overlap is safe.
4. Remove the Vercel functions one release later.

---

## 14. Observability

- Logs: JSON with `request_id`, `user_id` (hashed), `route`, `status`, `latency_ms`. Payment logs include `reference` and `transition`.
- Metrics: RED metrics per route; counters for `payments_verified_total{result}`, `payment_amount_mismatch_total`, `webhook_events_total{event,outcome}`, `emails_sent_total{result}`; gauges for `pending_orders_older_than_10m` and queue depth.
- Alerts:
  - any amount mismatch
  - webhook 5xx rate above 1% over 10 min
  - pending orders older than 30 min
  - email failures after all retries
  - `/readyz` failing
- Sentry on the API and worker, with personal data scrubbed.

---

## 15. Phases & checkpoints

| # | Phase | Done when |
|---|---|---|
| 0 | Discovery: read the web repo, write ADRs (catalog to Postgres, migration sharing, hosting, Redis provider, statuses, deletion policy) | ADRs approved by a human |
| 1 | Scaffold: config, logging, errors, auth, Redis, health, Docker, CI | `/healthz` and `/readyz` green locally and in CI |
| 2 | Catalog migration and seed, catalog/search/pricing endpoints | Parity suite 100% green |
| 3 | Cart, wishlist, profile, forms | Cart-merge and ownership tests green |
| 4 | Checkout, Paystack, state machine, webhook, email worker, reconciliation | Race and mismatch tests green; staging test-card purchase succeeds |
| 5 | Orders, admin status updates, account deletion | Access and anonymisation tests green |
| 6 | Hardening: rate limits, idempotency, observability, k6 load test (p95 < 300ms excluding Paystack) | Load and security report attached |
| 7 | Staging integration with web (behind a flag) and mobile (Appetize) | End-to-end purchase from both clients on staging |
| 8 | Production migrations, deploy, webhook cutover, retire the Vercel functions | Live smoke test passed; runbook complete |

Checkpoint message format:

```text
Phase N — <name>
Done: …
Evidence: test summary, coverage of critical paths, screenshots/logs
Deviations from BP: … (why)
Open questions: …
Next: …
```

---

## 16. Ask before acting

- Any schema change, new status, or change to pricing values
- Moving the catalog to Postgres versus keeping it in code for v1
- Hosting provider and region, Redis provider, domain/DNS
- Anything touching **live** Paystack keys, the live webhook URL, or production data
- The account-deletion retention policy
- How admins manage orders (API endpoints or Supabase Studio)
- Deleting or rewriting the web repo's Vercel functions

---

## 17. Conventions

- Python style: ruff defaults with a 100-character line length; type hints everywhere (`mypy --strict`); no bare `except`; `async` throughout for I/O.
- Naming: modules `snake_case`, Pydantic models `XxxIn` / `XxxOut`, repositories return domain objects, not ORM rows.
- Commits use Conventional Commits; branches are named `feat/<area>-<desc>` or `fix/<area>-<desc>`.
- Every PR states what changed, how it was tested, whether there's a migration (and whether it's backward-compatible), and whether there are env changes.
- Documentation: update `README.md` (setup, run, deploy), `docs/runbook.md` (incidents: "customer paid but order not confirmed", webhook secret rotation, reconciliation re-run, rollback) and the ADRs as you go.

---

## 18. Definition of done

1. The API is live at `api.bernicehairplace.com` (production) and on staging, with health checks, metrics, Sentry and alerts.
2. The web store and mobile app (including Appetize) complete purchases through the API: test mode on staging, live mode in production.
3. Pricing parity is proven, payment idempotency is proven under concurrency, and every order is emailed exactly once.
4. The live Paystack webhook points to the API, and the Vercel payment functions are retired.
5. `openapi.json` is published, and generated clients compile in the web and mobile repos.
6. CI/CD gates are green, and the README and runbook are complete.
