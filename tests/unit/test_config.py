import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_live_paystack_key_refused_outside_production() -> None:
    with pytest.raises(ValidationError, match="live Paystack key outside production"):
        make_settings(app_env="staging", paystack_secret_key="sk_live_abc")


def test_test_paystack_key_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="test Paystack key in production"):
        make_settings(app_env="production", paystack_secret_key="sk_test_abc")


def test_matching_paystack_keys_accepted() -> None:
    assert make_settings(app_env="staging", paystack_secret_key="sk_test_abc").paystack_configured
    assert make_settings(
        app_env="production", paystack_secret_key="sk_live_abc"
    ).paystack_configured


def test_cors_wildcard_refused() -> None:
    with pytest.raises(ValidationError, match="explicit allowlist"):
        make_settings(cors_origins="*")


def test_cors_origins_split_and_normalized() -> None:
    s = make_settings(cors_origins=" https://a.com/ , https://b.com,,")
    assert s.cors_origins == ["https://a.com", "https://b.com"]


def test_derived_supabase_urls() -> None:
    s = make_settings()
    assert s.jwks_url == "https://testproject.supabase.co/auth/v1/.well-known/jwks.json"
    assert s.jwt_issuer == "https://testproject.supabase.co/auth/v1"


def test_empty_env_values_mean_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    monkeypatch.setenv("SUPABASE_JWT_SECRET", "")
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "")
    monkeypatch.setenv("MAILGUN_API_KEY", "")
    s = Settings(_env_file=None)
    assert s.supabase_jwt_secret is None  # no HS256 fallback with an empty key
    assert not s.paystack_configured
    assert not s.mailgun_configured
