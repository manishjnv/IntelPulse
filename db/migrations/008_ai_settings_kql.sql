-- Add KQL generation columns to ai_settings (schema drift from ORM).
-- Safe to re-run: every ADD COLUMN uses IF NOT EXISTS.

ALTER TABLE ai_settings
    ADD COLUMN IF NOT EXISTS feature_kql_generation      BOOLEAN        NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS daily_limit_kql_generation  INTEGER        NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS prompt_kql_generation       TEXT,
    ADD COLUMN IF NOT EXISTS model_kql_generation        VARCHAR(200)   NOT NULL DEFAULT '';
