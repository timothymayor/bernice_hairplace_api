# Runbook

This runbook is filled in as each phase lands. Sections marked *(Phase N)* describe behaviour that doesn't exist yet.

## Health checks

- `/healthz` failing means the process is down or wedged. The platform restarts it.
- `/readyz` returning 503 means Postgres is unreachable. Check the Supabase status page, the pooler connection string (`DATABASE_URL`, port 6543) and the pool size against the plan's connection limit.
- `/readyz` reporting `"redis": "degraded"` means the API is running without caching, rate limits and per-order locks. Correctness is kept by the SQL guards. Restore Redis; no data needs repairing.

## Rollback

Migrations are backward-compatible (expand, then contract), so a rollback never needs a down-migration.

- **Staging (Render):** Dashboard → `bernice-hairplace-api-staging` → **Events**. Pick the last good deploy and choose **Rollback**. Or revert the commit on `main`; it redeploys once checks pass.
- **Production (Contabo):** redeploy the previous image tag *(Phase 8)*.

## Render: first-time setup (staging)

This is done once, by hand. After that, every push to `main` deploys automatically once the GitHub checks pass (ADR 0003).

1. Push this repo to GitHub, then sign up at render.com with GitHub (no card needed).
2. Go to **New → Blueprint**, pick the repo, and Render reads `render.yaml`. It creates `bernice-hairplace-api-staging` (web) and `bernice-hairplace-redis-staging` (Key Value), both in Frankfurt.
3. Render asks for each `sync: false` secret. Leave the optional ones blank; blank means unset.
   - `DATABASE_URL`: Supabase dashboard → **Connect** → **Transaction pooler** (port 6543). Change the scheme to `postgresql+asyncpg://`. Don't use the direct connection: it's IPv6-only.
   - `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`: Supabase → Project Settings → API. Set `SUPABASE_JWT_SECRET` only if the project still uses legacy HS256 tokens.
   - `PAYSTACK_SECRET_KEY`: **`sk_test_...` only**. The app refuses to start with a live key outside production.
   - `CORS_ORIGINS`: the web staging origin(s), comma-separated.
   - `SITE_URL` and `PAYMENT_CALLBACK_URL`: the web staging site and its checkout callback page.
   - `MAILGUN_*` and `SENTRY_DSN`: from those accounts. These can stay blank until Phase 4.
4. Wait for the first deploy, then check: `curl https://bernice-hairplace-api-staging.onrender.com/readyz`. Expect `"status":"ready"`. The logs should show `worker.in_process_started` and `worker.heartbeat`.
5. **Keep it awake.** Create a free UptimeRobot (or Better Stack) HTTP monitor on `https://bernice-hairplace-api-staging.onrender.com/healthz`, every 5 minutes, with email alerts. Without it the service sleeps after 15 minutes idle, and the first request after that takes about a minute.
6. Later, for a custom domain: Render → Settings → Custom Domains → `api-staging.bernicehairplace.com`, then create the DNS record it shows.

Secrets can be changed later under Dashboard → service → **Environment**; saving triggers a redeploy. The generated `METRICS_TOKEN` is there too.

## Logs

- **Staging:** Render dashboard → service → **Logs**. Lines are JSON, with a `request_id` on every request.

## Customer paid but the order is not confirmed *(Phase 4)*

## Reconciliation re-run *(Phase 4)*

## Paystack webhook secret rotation *(Phase 4)*

## Email not received *(Phase 4)*
