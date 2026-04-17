"""Application configuration via environment variables."""

from __future__ import annotations

import warnings
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# Known-weak SECRET_KEY values. Any of these in a non-dev environment
# means the app boots with a forgeable JWT signing key — refuse to start.
_WEAK_SECRET_KEYS: frozenset[str] = frozenset(
    {
        "",
        "change-me",
        "change-me-in-production",
        "changeme",
        "dev-secret-key-not-for-production",
        "dev-only-fallback-not-for-production",
        "secret",
        "secret-key",
        "default",
        "insecure",
        "not-a-real-secret",
        "test",
        "testing",
    }
)

_WEAK_POSTGRES_PASSWORDS: frozenset[str] = frozenset(
    {
        "",
        "changeme",
        "ti_secret",
        "change-me-strong-password",
        "password",
        "postgres",
        "admin",
    }
)

_MIN_SECRET_KEY_LEN = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # General
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "https://IntelPulse.in"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        env = (self.environment or "").strip().lower()
        secret_is_weak = (
            self.secret_key in _WEAK_SECRET_KEYS
            or len(self.secret_key) < _MIN_SECRET_KEY_LEN
        )
        if env in ("production", "staging"):
            env_label = env.upper()
            if self.secret_key in _WEAK_SECRET_KEYS:
                raise ValueError(
                    f"{env_label} SECRET_KEY must be set to a secure value "
                    f"(not a known-weak default)!"
                )
            if len(self.secret_key) < _MIN_SECRET_KEY_LEN:
                raise ValueError(
                    f"{env_label} SECRET_KEY must be at least "
                    f"{_MIN_SECRET_KEY_LEN} characters long!"
                )
            if self.postgres_password in _WEAK_POSTGRES_PASSWORDS:
                raise ValueError(
                    f"{env_label} POSTGRES_PASSWORD must be set to a secure value!"
                )
            # Validate CORS origins don't include wildcards with credentials
            if "*" in self.cors_origins:
                raise ValueError(
                    f"CORS origins cannot include wildcards in {env}!"
                )
        elif secret_is_weak:
            warnings.warn(
                f"SECRET_KEY is using a weak/default value in "
                f"environment={env!r}. Set SECRET_KEY to a strong random "
                f"{_MIN_SECRET_KEY_LEN}+ character string via env var.",
                stacklevel=2,
            )

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "threat_intel"
    postgres_user: str = "ti_user"
    postgres_password: str = "changeme"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenSearch
    opensearch_url: str = "https://localhost:9200"
    opensearch_user: str = "admin"
    opensearch_password: str = "admin"
    opensearch_verify_certs: bool = False
    opensearch_index: str = "intel-items"

    # Feed keys
    nvd_api_key: str = ""
    abuseipdb_api_key: str = ""
    otx_api_key: str = ""
    virustotal_api_key: str = ""
    shodan_api_key: str = ""
    ipinfo_token: str = ""  # IPinfo Lite — free tier (50k/month)

    # AI — OpenAI-compatible endpoint (Groq, Google Gemini, OpenAI, etc.)
    ai_api_url: str = "https://api.groq.com/openai/v1/chat/completions"
    ai_api_key: str = ""
    ai_model: str = "llama-3.3-70b-versatile"
    ai_timeout: int = 30
    ai_enabled: bool = True

    # AWS Bedrock (for AWS deployment)
    aws_region: str = "us-east-1"

    # AWS Bedrock Agents — multi-agent enrichment path for news.
    # When ai_use_agents=True, enrich_news_item routes through the Supervisor
    # agent (which collaborates with IOC-Analyst + Risk-Scorer and invokes
    # the VirusTotal action group Lambda). Default off so the single-shot
    # invoke_model path stays the primary.
    ai_use_agents: bool = False
    bedrock_supervisor_agent_id: str = "FQBSERZQMP"
    bedrock_supervisor_alias_id: str = "HLSRFAFL42"  # "live-v2"
    bedrock_agent_timeout: int = 120

    # AI fallback providers (free tiers for rate-limit resilience)
    cerebras_api_key: str = ""   # Cerebras — fast inference, free tier
    hf_api_key: str = ""         # HuggingFace Inference API — free tier

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email OTP (SMTP)
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@IntelPulse.in"
    smtp_from_name: str = "IntelPulse"
    email_otp_enabled: bool = False

    # Domain configuration
    domain: str = "IntelPulse.in"
    domain_ui: str = "https://IntelPulse.in"
    domain_api: str = "https://IntelPulse.in"

    # Auth / Session
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # Open Access Mode (bypasses login — auto-creates admin session for platform access)
    demo_mode: bool = False
    demo_user_email: str = "admin@intelpulse.tech"
    demo_user_name: str = "Admin"

    # Cache TTLs (seconds)
    cache_ttl_search: int = 300
    cache_ttl_dashboard: int = 60
    cache_ttl_ai_summary: int = 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
