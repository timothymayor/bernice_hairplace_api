from app.core.logging import hash_id, mask_pii


def test_sensitive_keys_are_masked() -> None:
    out = mask_pii(
        None,
        "info",
        {
            "event": "checkout",
            "customer_email": "ada@example.com",
            "phone": "08012345678",
            "shipping_address": {"street": "1 Marina"},
            "authorization": "Bearer abc.def.ghi",
            "reference": "BHP-20261006-ABCDE",
        },
    )
    assert out["customer_email"] == "[masked]"
    assert out["phone"] == "[masked]"
    assert out["shipping_address"] == "[masked]"
    assert out["authorization"] == "[masked]"
    assert out["reference"] == "BHP-20261006-ABCDE"
    assert out["event"] == "checkout"


def test_inline_emails_and_bearer_tokens_are_scrubbed() -> None:
    out = mask_pii(
        None,
        "info",
        {
            "detail": "sent to ada@example.com with Bearer eyJhbGciOi.x.y",
            "nested": [{"token": "t"}],
        },
    )
    assert "ada@example.com" not in out["detail"]
    assert "eyJhbGciOi" not in out["detail"]
    assert out["nested"] == [{"token": "[masked]"}]


def test_hash_id_is_stable_and_not_reversible() -> None:
    assert hash_id("user-1") == hash_id("user-1")
    assert hash_id("user-1") != "user-1"
    assert hash_id(None) is None
