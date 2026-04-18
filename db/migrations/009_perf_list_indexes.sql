-- Performance indexes for the hottest list-view ORDER BY columns.
-- Each list endpoint (news / intel / iocs) sorts by a timestamp column
-- and currently does a Seq Scan + top-N heapsort — fine at today's
-- volumes (news_items=447 rows) but turns into a pain beyond ~50k rows.
-- Safe to re-run: every CREATE INDEX uses IF NOT EXISTS.

-- /api/v1/news?sort_by=published_at (default). Secondary created_at for
-- tie-break stability.
CREATE INDEX IF NOT EXISTS idx_news_items_published_at_desc
    ON news_items (published_at DESC NULLS LAST, created_at DESC);

-- /api/v1/intel?sort_by=ingested_at (default) — also used by the
-- notable_campaigns widget and the cross-enrichment job.
CREATE INDEX IF NOT EXISTS idx_intel_items_ingested_at_desc
    ON intel_items (ingested_at DESC);

-- /api/v1/intel?sort_by=risk_score — "Highest Risk" sort on the Threat
-- Feed page.
CREATE INDEX IF NOT EXISTS idx_intel_items_risk_score_desc
    ON intel_items (risk_score DESC);

-- /api/v1/iocs?sort_by=last_seen (default). risk_score DESC is also used
-- by the Critical/High card drill-down.
CREATE INDEX IF NOT EXISTS idx_iocs_last_seen_desc
    ON iocs (last_seen DESC);
CREATE INDEX IF NOT EXISTS idx_iocs_risk_score_desc
    ON iocs (risk_score DESC);
CREATE INDEX IF NOT EXISTS idx_iocs_sighting_count_desc
    ON iocs (sighting_count DESC);

-- Filter indexes — country_code + asn show up in the Geo View drill-down
-- and every per-country IOC listing.
CREATE INDEX IF NOT EXISTS idx_iocs_country_code
    ON iocs (country_code) WHERE country_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_iocs_asn
    ON iocs (asn) WHERE asn IS NOT NULL;
