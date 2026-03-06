-- =============================================
-- Migration 007: Automated Intelligence Extraction Tables
-- Adds vulnerable_products + threat_campaigns derived from
-- AI-enriched cyber news articles.
-- =============================================

-- =============================================
-- Vulnerable Products (rolling 48h window)
-- =============================================
CREATE TABLE IF NOT EXISTS intel_vulnerable_products (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_name    VARCHAR(300) NOT NULL,
    vendor          VARCHAR(200),
    cve_id          VARCHAR(30),
    cvss_score      REAL,
    epss_score      REAL,
    severity        VARCHAR(20) NOT NULL DEFAULT 'unknown',
    is_kev          BOOLEAN NOT NULL DEFAULT FALSE,
    exploit_available BOOLEAN NOT NULL DEFAULT FALSE,
    patch_available BOOLEAN NOT NULL DEFAULT FALSE,
    affected_versions TEXT,
    targeted_sectors TEXT[] NOT NULL DEFAULT '{}',
    targeted_regions TEXT[] NOT NULL DEFAULT '{}',
    source_count    INT NOT NULL DEFAULT 1,
    source_news_ids UUID[] NOT NULL DEFAULT '{}',
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confidence      VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ivp_product_cve UNIQUE NULLS NOT DISTINCT (product_name, cve_id)
);

CREATE INDEX IF NOT EXISTS idx_ivp_severity ON intel_vulnerable_products(severity);
CREATE INDEX IF NOT EXISTS idx_ivp_cvss ON intel_vulnerable_products(cvss_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ivp_epss ON intel_vulnerable_products(epss_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_ivp_kev ON intel_vulnerable_products(is_kev) WHERE is_kev = TRUE;
CREATE INDEX IF NOT EXISTS idx_ivp_last_seen ON intel_vulnerable_products(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_ivp_product_trgm ON intel_vulnerable_products USING GIN(product_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ivp_cve ON intel_vulnerable_products(cve_id) WHERE cve_id IS NOT NULL;

-- =============================================
-- Threat Actors & Campaigns (rolling 7d window)
-- =============================================
CREATE TABLE IF NOT EXISTS intel_threat_campaigns (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_name      VARCHAR(300) NOT NULL,
    campaign_name   VARCHAR(300),
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    severity        VARCHAR(20) NOT NULL DEFAULT 'unknown',
    targeted_sectors TEXT[] NOT NULL DEFAULT '{}',
    targeted_regions TEXT[] NOT NULL DEFAULT '{}',
    malware_used    TEXT[] NOT NULL DEFAULT '{}',
    techniques_used TEXT[] NOT NULL DEFAULT '{}',
    cves_exploited  TEXT[] NOT NULL DEFAULT '{}',
    source_count    INT NOT NULL DEFAULT 1,
    source_news_ids UUID[] NOT NULL DEFAULT '{}',
    confidence      VARCHAR(10) NOT NULL DEFAULT 'medium',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_itc_actor_campaign UNIQUE NULLS NOT DISTINCT (actor_name, campaign_name)
);

CREATE INDEX IF NOT EXISTS idx_itc_last_seen ON intel_threat_campaigns(last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_itc_severity ON intel_threat_campaigns(severity);
CREATE INDEX IF NOT EXISTS idx_itc_actor_trgm ON intel_threat_campaigns USING GIN(actor_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_itc_techniques ON intel_threat_campaigns USING GIN(techniques_used);
CREATE INDEX IF NOT EXISTS idx_itc_cves ON intel_threat_campaigns USING GIN(cves_exploited);
CREATE INDEX IF NOT EXISTS idx_itc_malware ON intel_threat_campaigns USING GIN(malware_used);
