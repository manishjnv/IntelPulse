-- ============================================================
-- AI Settings table — platform-wide AI configuration
-- Singleton row (key='default') stores all admin-controlled AI settings.
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_settings (
    key           VARCHAR(50) PRIMARY KEY DEFAULT 'default',
    -- Global toggle
    ai_enabled    BOOLEAN NOT NULL DEFAULT TRUE,

    -- Primary provider
    primary_provider   VARCHAR(100) NOT NULL DEFAULT 'groq',
    primary_api_url    TEXT NOT NULL DEFAULT 'https://api.groq.com/openai/v1/chat/completions',
    primary_api_key    TEXT NOT NULL DEFAULT '',
    primary_model      VARCHAR(200) NOT NULL DEFAULT 'llama-3.3-70b-versatile',
    primary_timeout    INTEGER NOT NULL DEFAULT 30,

    -- Fallback providers (JSONB array of {name, url, key, model, timeout, enabled})
    fallback_providers JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Per-feature toggles
    feature_intel_summary     BOOLEAN NOT NULL DEFAULT TRUE,
    feature_intel_enrichment  BOOLEAN NOT NULL DEFAULT TRUE,
    feature_news_enrichment   BOOLEAN NOT NULL DEFAULT TRUE,
    feature_live_lookup       BOOLEAN NOT NULL DEFAULT TRUE,
    feature_report_gen        BOOLEAN NOT NULL DEFAULT TRUE,
    feature_briefing_gen      BOOLEAN NOT NULL DEFAULT TRUE,

    -- Daily limits (0 = unlimited)
    daily_limit_intel_summary     INTEGER NOT NULL DEFAULT 0,
    daily_limit_intel_enrichment  INTEGER NOT NULL DEFAULT 0,
    daily_limit_news_enrichment   INTEGER NOT NULL DEFAULT 0,
    daily_limit_live_lookup       INTEGER NOT NULL DEFAULT 0,
    daily_limit_report_gen        INTEGER NOT NULL DEFAULT 0,
    daily_limit_briefing_gen      INTEGER NOT NULL DEFAULT 0,

    -- Custom prompts per feature (NULL = use system default)
    prompt_intel_summary     TEXT,
    prompt_intel_enrichment  TEXT,
    prompt_news_enrichment   TEXT,
    prompt_live_lookup       TEXT,
    prompt_report_gen        TEXT,
    prompt_briefing_gen      TEXT,

    -- Global generation parameters
    default_temperature  REAL NOT NULL DEFAULT 0.3,
    default_max_tokens   INTEGER NOT NULL DEFAULT 800,

    -- Rate limiting
    requests_per_minute  INTEGER NOT NULL DEFAULT 30,
    batch_delay_ms       INTEGER NOT NULL DEFAULT 1000,

    -- Cache TTLs (seconds)
    cache_ttl_summary     INTEGER NOT NULL DEFAULT 3600,
    cache_ttl_enrichment  INTEGER NOT NULL DEFAULT 21600,
    cache_ttl_lookup      INTEGER NOT NULL DEFAULT 300,

    -- Audit
    updated_by  UUID,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Insert the default singleton row if it doesn't exist
INSERT INTO ai_settings (key) VALUES ('default') ON CONFLICT (key) DO NOTHING;
