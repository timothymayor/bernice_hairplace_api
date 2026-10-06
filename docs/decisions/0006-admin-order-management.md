# 0006 — How admins manage orders

- **Status:** Proposed
- **Date:** 2026-10-06

## Context

Today the owner updates orders in Supabase Studio.

BP §5 offers `PATCH /admin/orders/{id}/status`, which records history and can send a status email. Recording history needs a new `order_status_history` table, and therefore a migration.

## Proposal

Build the admin endpoint in Phase 5:

- Admin means `app_metadata.role == "admin"`, which is set only through the service role.
- The endpoint allows only `paid → processing → in_transit → delivered`, plus setting `waybill_number`.
- Each change is recorded in a new `order_status_history` table (new migration).

Studio stays available but is discouraged for status changes, because it bypasses the history and the emails.

## Needed from the owner

- Whether to build the endpoint or keep Studio as the only tool.
- Whether customers get an email when their order moves to `in_transit`, with the waybill number.
