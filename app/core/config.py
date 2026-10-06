"""Application settings, read from the environment (and `.env` locally) and validated at startup."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

AppEnv = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    # env_ignore_empty: `KEY=` (as in .env.example, or a blank secret on the host) means "unset".
    # Without it an empty SUPABASE_JWT_SECRET would enable HS256 with an empty signing key.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_ignore_empty=True
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"
    # Comma-separated allowlist, e.g. "https://bernicehairplace.com,https://www.bernicehairplace.com".
    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Regex for extra allowed origins, e.g. Vercel previews: r"https://bernice-hairplace-.*\.vercel\.app".
    cors_origin_regex: str | None = None
    site_url: str = "https://bernicehairplace.com"
    payment_callback_url: str | None = None

    supabase_url: str = "http://127.0.0.1:54321"
    supabase_jwks_url: str | None = None
    supabase_jwt_secret: SecretStr | None = None
    supabase_service_role_key: SecretStr | None = None
    database_url: str = "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres"
    db_pool_size: int = Field(default=5, ge=1, le=50)

    redis_url: str = "redis://127.0.0.1:6379/0"

    paystack_secret_key: SecretStr | None = None
    paystack_base_url: str = "https://api.paystack.co"

    mailgun_api_key: SecretStr | None = None
    mailgun_domain: str | None = None
    mailgun_from_email: str | None = None
    mailgun_region: Literal["us", "eu"] = "us"
    store_notification_email: str | None = None

    sentry_dsn: str | None = None
    # When set, GET /metrics requires `Authorization: Bearer <token>`.
    metrics_token: SecretStr | None = None
    payment_pending_ttl_minutes: int = Field(default=60, ge=15)
    reconcile_interval_minutes: int = Field(default=5, ge=1, le=60)
    # Free-tier staging only (Render has no free worker service): run arq inside the API process.
    run_worker_in_process: bool = False

    @model_validator(mode="before")
    @classmethod
    def _split_origins(cls, data: dict[str, object]) -> dict[str, object]:
        for key in ("cors_origins", "CORS_ORIGINS"):
            raw = data.get(key)
            if isinstance(raw, str):
                data[key] = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
        return data

    @model_validator(mode="after")
    def _check_paystack_mode(self) -> "Settings":
        key = self.paystack_secret_key.get_secret_value() if self.paystack_secret_key else ""
        if self.app_env != "production" and key.startswith("sk_live_"):
            raise ValueError("Refusing to start: live Paystack key outside production")
        if self.app_env == "production" and key.startswith("sk_test_"):
            raise ValueError("Refusing to start: test Paystack key in production")
        if self.app_env == "production" and self.run_worker_in_process:
            raise ValueError("RUN_WORKER_IN_PROCESS is for staging only; run a separate worker")
        if "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS must be an explicit allowlist, not '*'")
        return self

    @property
    def jwks_url(self) -> str:
        return self.supabase_jwks_url or f"{self.supabase_url}/auth/v1/.well-known/jwks.json"

    @property
    def jwt_issuer(self) -> str:
        return f"{self.supabase_url}/auth/v1"

    @property
    def paystack_configured(self) -> bool:
        return self.paystack_secret_key is not None

    @property
    def mailgun_configured(self) -> bool:
        return bool(self.mailgun_api_key and self.mailgun_domain and self.mailgun_from_email)

    @property
    def mailgun_host(self) -> str:
        return "api.eu.mailgun.net" if self.mailgun_region == "eu" else "api.mailgun.net"


@lru_cache
def get_settings() -> Settings:
    return Settings()
