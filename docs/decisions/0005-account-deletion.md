# 0005 — Account deletion and retention

- **Status:** Proposed (needs the owner's decision on the retention period and the migration)
- **Date:** 2026-10-06

## Context

Both app stores require in-app account deletion. `orders.user_id` is `on delete restrict`, so orders must be dealt with before the `auth.users` row can be deleted (BP §4.4).

Nigerian tax and accounting practice expects financial records to be kept for several years.

## Proposal

`DELETE /v1/me` requires an Idempotency-Key, returns 202, and enqueues `delete_account`. In one transaction, that job:

1. Anonymises the user's orders.
   - `customer_name` becomes `'Deleted customer'`.
   - `customer_email` and `customer_phone` are replaced with non-identifying placeholders.
   - `shipping_address` is reduced to `{"state", "country"}`.
   - Order numbers, items and amounts are kept.
2. Deletes `cart_items`, `wishlist_items` and the `profiles` row, and sets `custom_wig_requests.user_id` to NULL.
3. Sets `orders.user_id` to NULL. This needs a migration that makes `orders.user_id` nullable. The migration is expand-only and backward-compatible, because the web code never writes NULL.

After that transaction, the job deletes the `auth.users` row through the Supabase Admin API.

Orders still in `pending_payment` are verified and expired first, so no payment can land unseen on an anonymised order.

## Needed from the owner

- The retention period for anonymised orders. Proposed: 6 years, then purge.
- Approval of the migration that makes `orders.user_id` nullable (AGENTS.md §16 requires approval for any schema change).
- Whether paid orders that haven't been delivered block deletion. Proposed: yes, with the message "You have an order in progress. Please contact us to delete your account."
