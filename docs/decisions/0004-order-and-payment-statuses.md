# 0004 — No new order or payment statuses in v1

- **Status:** Proposed (the build follows this default, which needs no schema change)
- **Date:** 2026-10-06

## Context

The UX spec (§41) lists states the database can't represent: payment `abandoned` and `refunded`, and order `shipped` and `refunded`.

BP §4.3 makes `refunded` and a separate abandoned state optional, "only if approved". It also says to keep today's mapping for abandoned payments unless told otherwise.

## Decision

Keep the existing check constraints unchanged and map the UX states as follows.

| UX state | Represented as |
|---|---|
| Order "Shipped" | `orders.status = 'in_transit'` |
| Payment "Payment not completed" (abandoned at Paystack) | `cancelled` / `failed`, with normalized client state `abandoned` |
| Payment expired by the reconciliation TTL | `cancelled` / `failed`, with normalized state `abandoned` ("Your bag is saved") |
| Payment or order "Refunded" | Not represented. After a full refund, Paystack reports the transaction as `reversed`, so `refund.processed` triggers a re-verify that lands on `payment_reversed` / `reversed` ("Payment reversed") |

The normalized client state enum is `awaiting_payment | processing_payment | paid | failed | abandoned | reversed`, with no `refunded`.

## Consequences

- Clients show "Payment reversed" for refunds.
- Partial refunds aren't represented: the order stays `paid`. They're rare, and the owner handles them manually.
- Adding `refunded` later means an additive migration (widening the check constraint) plus a new enum value. The new enum value is a breaking OpenAPI change for strict clients, so it needs a version note.

## Parity note

The web webhook reads `data.reference` for every event. Paystack's `refund.processed` payload carries the transaction reference in `data.transaction_reference`, so the web store probably ignores refund events today.

The API reads `transaction_reference` for refund events. This still needs to be confirmed against Paystack's docs and a test-mode refund in Phase 4.
