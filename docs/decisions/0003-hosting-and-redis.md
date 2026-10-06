# 0003 — Hosting, region and Redis provider

- **Status:** Accepted (owner, 2026-10-06)
- **Date:** 2026-10-06

## Decision

| Environment | Platform | Region | Redis | Worker |
|---|---|---|---|---|
| **Staging** | Render free web service (Docker) | `frankfurt` | Render Key Value free (25 MB, private) | In-process (`RUN_WORKER_IN_PROCESS=true`) |
| **Production** | Contabo VPS (Cloud VPS 10 or larger), docker compose | Closest to Supabase `eu-west-1` (Ireland): **Portsmouth (UK)**, to be confirmed at purchase | `redis:7-alpine` on the same VPS | Separate `worker` container |

The Supabase project is in **eu-west-1 (Ireland)**. Every request makes database round-trips, so the API runs as close to Ireland as each platform allows. Render has no UK or Ireland region; Frankfurt is the closest.

## How we got here (October 2026)

| Option | Outcome |
|---|---|
| Oracle Cloud Always Free | Sign-up failed: card rejected |
| Fly.io | Free trial is only 2 machine-hours, with machines stopping after 5 minutes; continuing needs a card, which the owner declined for now |
| Vercel (Hobby) | Non-commercial use only; no background worker; scheduled jobs at most once a day; 60-second function limit |
| Koyeb free, Northflank sandbox | Both ask for a card at sign-up |
| Upstash Redis free | 500K commands a month; arq polls about twice a second (about 5M a month) |
| **Render free** | No card needed; runs our Docker image unchanged; free Key Value has no command limit. Chosen for staging |
| **Contabo** | About $5 a month, always on, full control. Chosen by the owner for production |

## Staging on Render (`render.yaml`)

- **Same image as production.** Render builds the repo's `Dockerfile`, and only environment variables differ. Render deploys only after the GitHub Actions checks on the commit pass (`autoDeployTrigger: checksPass`).
- **Worker in-process.** Render's free plan has no background workers, so the arq worker runs as a task inside the API process (`app/workers/inprocess.py`), with `WEB_CONCURRENCY=1` so there's exactly one. It restarts itself with backoff if Redis fails. The settings validator refuses this mode in production.
- **Free services sleep** after 15 minutes without traffic, and take about a minute to wake. An external monitor (UptimeRobot free, every 5 minutes) calls `/healthz`. That keeps the service awake and also alerts us when it's down. One always-on service fits within Render's 750 free instance-hours a month.
- **Key Value:** private (empty `ipAllowList`), with `maxmemoryPolicy: noeviction` so arq jobs are never evicted. It doesn't persist data.
- **Database:** `DATABASE_URL` must be Supabase's **transaction pooler** (port 6543), because the direct connection is IPv6-only.

### Accepted limitations (staging only)

- 0.1 CPU and 512 MB: fine for integration testing and the web and mobile demos. **The Phase 6 load test doesn't run here.**
- Render may restart or sleep the service despite the monitor. Paystack retries webhooks, and reconciliation catches missed payments.
- Restarting Redis loses queued jobs. Phase 4 must make reconciliation re-enqueue the confirmation email for `paid` orders whose `confirmation_email_sent_at` is NULL. The DB claim still guarantees the email is sent exactly once.
- Render builds the image itself, so staging doesn't run the exact artifact CI scanned. Production on Contabo will deploy the GHCR image CI scanned.

## Production on Contabo (Phase 8)

To be detailed in Phase 8:

- docker compose with `api`, `worker`, `redis` and Caddy (HTTPS for `api.bernicehairplace.com`)
- deployed from the scanned GHCR image over SSH, behind manual approval
- unattended security upgrades, a firewall allowing only 22, 80 and 443, the Contabo auto-backup add-on, and external uptime monitoring

Contabo support is ticket-only and can be slow, so recovery must not depend on it. The runbook will cover rebuilding the server from scratch.

## Consequences

- Rate limiting (Phase 6) must take the client IP from the proxy's forwarded header on each platform: `X-Forwarded-For` behind Render's router and behind Caddy.
- Staging and production differ in how the worker runs (in-process versus a separate container). Both run the same code (`app.workers.settings.WorkerSettings`).
