"""AI enrichment → DB field mapping — single source of truth.

Eliminates the duplicated 30-field mapping that previously appeared in
both enrich_news_batch() and re_enrich_fallback_news() in worker/tasks.py.
"""

from __future__ import annotations

from app.normalizers.categories import normalize_category
from app.normalizers.confidence import normalize_confidence


def apply_news_enrichment(item, enrichment: dict) -> None:
    """Apply an AI enrichment dict to a NewsItem ORM instance.

    Validates category and confidence; clamps relevance_score to 1-100.
    Mutates ``item`` in place — does NOT flush or commit.
    """
    raw_cat = enrichment.get("category", item.category or "active_threats")
    item.category = normalize_category(raw_cat, item.category or "active_threats")
    item.summary = enrichment.get("summary")
    item.executive_brief = enrichment.get("executive_brief")
    item.risk_assessment = enrichment.get("risk_assessment")
    item.attack_narrative = enrichment.get("attack_narrative")
    item.recommended_priority = enrichment.get("recommended_priority", "medium")
    item.why_it_matters = enrichment.get("why_it_matters", [])
    item.tags = enrichment.get("tags", [])
    item.threat_actors = enrichment.get("threat_actors", [])
    item.malware_families = enrichment.get("malware_families", [])
    item.campaign_name = enrichment.get("campaign_name")
    item.cves = enrichment.get("cves", [])
    item.vulnerable_products = enrichment.get("vulnerable_products", [])
    item.tactics_techniques = enrichment.get("tactics_techniques", [])
    item.initial_access_vector = enrichment.get("initial_access_vector")
    item.post_exploitation = enrichment.get("post_exploitation", [])
    item.targeted_sectors = enrichment.get("targeted_sectors", [])
    item.targeted_regions = enrichment.get("targeted_regions", [])
    item.impacted_assets = enrichment.get("impacted_assets", [])
    item.ioc_summary = enrichment.get("ioc_summary", {})
    item.timeline = enrichment.get("timeline", [])
    item.detection_opportunities = enrichment.get("detection_opportunities", [])
    item.mitigation_recommendations = enrichment.get("mitigation_recommendations", [])
    item.notable_campaigns = enrichment.get("notable_campaigns", [])
    item.exploitation_info = enrichment.get("exploitation_info", {})
    item.related_cves = enrichment.get("related_cves", [])
    item.confidence = normalize_confidence(enrichment.get("confidence"))
    item.relevance_score = max(1, min(100, enrichment.get("relevance_score", 50)))
