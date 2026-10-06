"""Business metrics (RED metrics per route come from prometheus-fastapi-instrumentator)."""

from prometheus_client import Counter, Gauge

payments_verified_total = Counter(
    "payments_verified_total", "Paystack verifications by result", ["source", "result"]
)
payment_amount_mismatch_total = Counter(
    "payment_amount_mismatch_total", "Successful Paystack transactions whose amount/currency differ"
)
webhook_events_total = Counter(
    "webhook_events_total", "Paystack webhook deliveries", ["event", "outcome"]
)
emails_sent_total = Counter("emails_sent_total", "Transactional emails", ["kind", "result"])
pending_orders_older_than_10m = Gauge(
    "pending_orders_older_than_10m",
    "Orders awaiting payment for more than 10 minutes",
    multiprocess_mode="max",
)
reconciled_orders_total = Counter(
    "reconciled_orders_total", "Orders touched by reconciliation", ["outcome"]
)
