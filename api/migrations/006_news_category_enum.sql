-- Migration 006: Add missing news_category enum values
-- Fixes 3-way drift between schema (9 values), tasks.py (11), and prompts.py (11)

ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'general_news';
ALTER TYPE news_category ADD VALUE IF NOT EXISTS 'geopolitical_cyber';
