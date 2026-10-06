# Bernice Hairplace API

One FastAPI service behind the Bernice Hairplace web store (`bernice_hairplace_web`) and the Expo mobile app. It serves the catalog, cart, checkout and Paystack payments, and it replaces the web repo's Vercel functions in `api/paystack/*`.

- Rules for working here: [`AGENTS.md`](AGENTS.md)
- Scope and phases: [`docs/bernice_hairplace_backend_api_production_prompt.md`](docs/bernice_hairplace_backend_api_production_prompt.md)
- Where the build stands: [`docs/progress.md`](docs/progress.md)
- Decisions: [`docs/decisions/`](docs/decisions/)
- Operations: [`docs/runbook.md`](docs/runbook.md)

## Requirements

- Python 3.12 and [uv](https://docs.astral.sh/uv/) 0.12+
- Docker (for Redis locally and the image)
- [Supabase CLI](https://supabase.com/docs/guides/cli) for a local Postgres with the shared migrations
- Node 22.18+ only for `make parity` (it runs the web repo's TypeScript)

## Local setup

```bash
make setup                 # uv sync --all-groups + pre-commit hooks
cp .env.example .env       # fill in values; `supabase start` prints the local keys
supabase start             # local Postgres on :54322 with supabase/migrations applied
make dev                   # redis in Docker + API with reload on http://127.0.0.1:8000
make worker                # arq worker (separate terminal)
```

Open `http://127.0.0.1:8000/docs` for the interactive docs. They're disabled when `APP_ENV=production`.

To run everything in containers, use `make up` (api + worker + redis). Postgres still comes from `supabase start` on the host.

## Health and metrics

| Endpoint | Meaning |
|---|---|
| `GET /healthz` | Liveness. The process is serving; it never touches dependencies |
| `GET /readyz` | Readiness. 503 if Postgres is unreachable. If Redis is down it reports `degraded` but still returns 200, because the API runs without Redis (AGENTS.md §10) |
| `GET /metrics` | Prometheus metrics. Requires `Authorization: Bearer $METRICS_TOKEN` when that variable is set |

## Quality gates

Run these before any change is considered done:

```bash
make lint typecheck test   # ruff, mypy --strict, pytest
make openapi               # after touching schemas or routers; commit openapi.json
make parity                # after touching pricing, checkout or catalog code
```

`tests/contract` fails if `openapi.json` is stale. CI also fails a PR that makes a breaking change to it.

## Configuration

All configuration comes from environment variables, validated at startup by `app/core/config.py`. See [`.env.example`](.env.example). The API refuses to start with a live Paystack key outside production, or a test key in production.

## Docker image

One image runs both roles:

```bash
docker build -t bernice-hairplace-api .
docker run -p 8000:8000 --env-file .env --read-only --tmpfs /tmp bernice-hairplace-api   # API
docker run --env-file .env --read-only --tmpfs /tmp bernice-hairplace-api \
  arq app.workers.settings.WorkerSettings                                                  # worker
```

`WEB_CONCURRENCY` sets the number of gunicorn workers (default 2).

## CI/CD

`.github/workflows/ci.yml` runs the following jobs:

- **quality**: ruff, mypy and pytest.
- **openapi-diff**: on PRs, fails on breaking changes.
- **migrations-sync**: checks that migrations match the web repo. Needs the `WEB_REPO_TOKEN` secret.
- **smoke**: builds the image, runs a Trivy scan, then starts the API against Postgres and Redis and checks `/healthz` and `/readyz`, and checks that the worker starts.

Pushes to `main` and `v*` tags publish the image to GHCR. **Staging** runs on Render's free tier from [`render.yaml`](render.yaml): Render deploys `main` itself once these checks pass. **Production** will run on Contabo (Phase 8). See [ADR 0003](docs/decisions/0003-hosting-and-redis.md) and the [runbook](docs/runbook.md#render-first-time-setup-staging).

## Migrations

`supabase/migrations/` is shared with the web repo ([ADR 0001](docs/decisions/0001-shared-migrations.md)). Add new migrations to both repos, never edit an applied one, and keep every change backward-compatible with the live web store.
