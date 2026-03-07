-- ============================================================
-- Per-feature AI model overrides
-- Allows admins to assign different models to different AI features.
-- Empty string = use primary model.
-- ============================================================

ALTER TABLE ai_settings
  ADD COLUMN IF NOT EXISTS model_intel_summary     VARCHAR(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS model_intel_enrichment  VARCHAR(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS model_news_enrichment   VARCHAR(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS model_live_lookup       VARCHAR(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS model_report_gen        VARCHAR(200) NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS model_briefing_gen      VARCHAR(200) NOT NULL DEFAULT '';
