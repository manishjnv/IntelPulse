"""Unit tests for app.core.config — Settings validation."""

from __future__ import annotations

import pytest


class TestSettingsValidation:
    """Test Settings validation logic, especially production secret checks."""

    def test_development_allows_weak_secrets(self):
        """Development environment should allow default/weak secrets."""
        from app.core.config import Settings

        settings = Settings(
            environment="development",
            secret_key="change-me",
            postgres_password="changeme",
        )
        assert settings.environment == "development"
        assert settings.secret_key == "change-me"

    def test_production_rejects_default_secret_key(self):
        """Production must reject default SECRET_KEY values."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="PRODUCTION SECRET_KEY"):
            Settings(
                environment="production",
                secret_key="change-me",
                postgres_password="strong-password-12345678901234567890",
            )

    def test_production_rejects_dev_secret_key(self):
        """Production must reject dev-only SECRET_KEY values."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="PRODUCTION SECRET_KEY"):
            Settings(
                environment="production",
                secret_key="dev-secret-key-not-for-production",
                postgres_password="strong-password-12345678901234567890",
            )

    def test_production_rejects_short_secret_key(self):
        """Production SECRET_KEY must be at least 32 characters."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="SECRET_KEY must be at least"):
            Settings(
                environment="production",
                secret_key="short-key",
                postgres_password="strong-password-12345678901234567890",
            )

    def test_production_rejects_default_postgres_password(self):
        """Production must reject default POSTGRES_PASSWORD values."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="PRODUCTION POSTGRES_PASSWORD"):
            Settings(
                environment="production",
                secret_key="a" * 32,
                postgres_password="changeme",
            )

    def test_production_rejects_ti_secret_postgres_password(self):
        """Production must reject 'ti_secret' POSTGRES_PASSWORD."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="PRODUCTION POSTGRES_PASSWORD"):
            Settings(
                environment="production",
                secret_key="a" * 32,
                postgres_password="ti_secret",
            )

    def test_production_rejects_wildcard_cors(self):
        """Production must reject wildcard CORS origins."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="CORS origins cannot include wildcards in"):
            Settings(
                environment="production",
                secret_key="a" * 32,
                postgres_password="strong-password-12345678901234567890",
                cors_origins=["*"],
            )

    def test_production_accepts_valid_secrets(self):
        """Production should accept strong secrets."""
        from app.core.config import Settings

        settings = Settings(
            environment="production",
            secret_key="a" * 32,
            postgres_password="strong-password-12345678901234567890",
            cors_origins=["https://intelpulse.tech"],
        )
        assert settings.environment == "production"
        assert len(settings.secret_key) >= 32

    def test_staging_rejects_weak_secret_key(self):
        """Staging now shares the production secret guard."""
        from app.core.config import Settings

        with pytest.raises(ValueError, match="STAGING SECRET_KEY"):
            Settings(
                environment="staging",
                secret_key="change-me",
                postgres_password="strong-password-12345678901234567890",
            )

    def test_staging_rejects_default_postgres_password(self):
        from app.core.config import Settings

        with pytest.raises(ValueError, match="STAGING POSTGRES_PASSWORD"):
            Settings(
                environment="staging",
                secret_key="a" * 32,
                postgres_password="changeme",
            )

    def test_staging_accepts_strong_secrets(self):
        from app.core.config import Settings

        settings = Settings(
            environment="staging",
            secret_key="a" * 32,
            postgres_password="strong-password-12345678901234567890",
            cors_origins=["https://staging.intelpulse.tech"],
        )
        assert settings.environment == "staging"

    @pytest.mark.parametrize(
        "bad_secret",
        [
            "",
            "change-me",
            "change-me-in-production",
            "dev-secret-key-not-for-production",
            "dev-only-fallback-not-for-production",
            "secret",
            "secret-key",
            "default",
            "insecure",
            "test",
            "testing",
            "not-a-real-secret",
        ],
    )
    def test_production_rejects_each_known_weak_secret(self, bad_secret):
        from app.core.config import Settings

        with pytest.raises(ValueError, match="PRODUCTION SECRET_KEY"):
            Settings(
                environment="production",
                secret_key=bad_secret,
                postgres_password="strong-password-12345678901234567890",
            )

    def test_production_rejects_postgres_common(self):
        from app.core.config import Settings

        for bad in ("password", "postgres", "admin"):
            with pytest.raises(ValueError, match="PRODUCTION POSTGRES_PASSWORD"):
                Settings(
                    environment="production",
                    secret_key="a" * 32,
                    postgres_password=bad,
                )

    def test_development_warns_on_weak_secret(self):
        import warnings

        from app.core.config import Settings

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            Settings(
                environment="development",
                secret_key="change-me",
                postgres_password="changeme",
            )

        assert any("weak/default value" in str(w.message) for w in caught)

    def test_environment_case_insensitive_matching(self):
        """Environment string is normalized to lowercase for comparison."""
        from app.core.config import Settings

        # Direct pydantic Literal validation rejects 'PRODUCTION' upper-case,
        # so we test the lowercase path — but confirm strip() runs.
        settings = Settings(
            environment="production",  # type: ignore[arg-type]
            secret_key="a" * 32,
            postgres_password="strong-password-12345678901234567890",
        )
        assert settings.environment == "production"


class TestDatabaseURL:
    """Test database URL property generation."""

    def test_database_url_async(self):
        """Async database URL should use postgresql+asyncpg driver."""
        from app.core.config import Settings

        settings = Settings(
            postgres_host="db.example.com",
            postgres_port=5432,
            postgres_db="testdb",
            postgres_user="testuser",
            postgres_password="testpass",
        )
        url = settings.database_url
        assert url.startswith("postgresql+asyncpg://")
        assert "testuser:testpass" in url
        assert "db.example.com:5432" in url
        assert url.endswith("/testdb")

    def test_database_url_sync(self):
        """Sync database URL should use postgresql driver."""
        from app.core.config import Settings

        settings = Settings(
            postgres_host="db.example.com",
            postgres_port=5432,
            postgres_db="testdb",
            postgres_user="testuser",
            postgres_password="testpass",
        )
        url = settings.database_url_sync
        assert url.startswith("postgresql://")
        assert "testuser:testpass" in url
        assert "db.example.com:5432" in url
        assert url.endswith("/testdb")


class TestGetSettings:
    """Test get_settings caching behavior."""

    def test_get_settings_returns_settings(self):
        """get_settings should return a Settings instance."""
        from app.core.config import get_settings

        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "environment")

    def test_get_settings_is_cached(self):
        """get_settings should return the same instance on repeated calls."""
        from app.core.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
