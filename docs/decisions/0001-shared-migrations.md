# 0001 — Migrations are shared with the web repo by mirroring

- **Status:** Accepted (approved in Phase 0; this ADR was reconstructed on 2026-10-06 after a lost session)
- **Date:** 2026-10-06

## Context

AGENTS.md §6 and BP §1.5 require one migration system, `supabase/migrations/`, shared by this API and `bernice_hairplace_web`. The options were a git submodule, a third "schema" repo, or mirrored copies.

## Decision

Mirror the directory. The web repo is upstream for the files that already exist. Every new migration is committed to **both** repos in paired PRs with the same filename.

`supabase db push` runs only from this repo's CI, in the tag pipeline with manual approval. That gives one place that applies migrations to staging and production.

CI fails if a file present in both repos differs (a checksum step in the PR workflow).

## Consequences

- No submodule friction for Vercel builds or for contributors.
- Drift is possible between paired PRs. The checksum check and the "sync from web before adding a migration" rule (AGENTS.md §6) contain it.
- As of 2026-10-06, `20261006120000_initial_schema.sql` is byte-identical in both repos.
