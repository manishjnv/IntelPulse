"""News category normalisation — single source of truth.

Canonical enum values, fallback mapping for AI hallucinations,
and keyword-based detection for initial RSS ingestion.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Canonical category values (must match PostgreSQL enum + schema) ────

VALID_NEWS_CATEGORIES: set[str] = {
    "active_threats",
    "exploited_vulnerabilities",
    "ransomware_breaches",
    "nation_state",
    "cloud_identity",
    "ot_ics",
    "security_research",
    "tools_technology",
    "policy_regulation",
    "general_news",
    "geopolitical_cyber",
}

# ── Fallback map: common AI-hallucinated → valid ─────────

CATEGORY_FALLBACK_MAP: dict[str, str] = {
    "security_operations": "active_threats",
    "cyber_operations": "active_threats",
    "data_breach": "ransomware_breaches",
    "data_breaches": "ransomware_breaches",
    "malware": "active_threats",
    "phishing": "active_threats",
    "supply_chain": "active_threats",
    "vulnerability": "exploited_vulnerabilities",
    "vulnerabilities": "exploited_vulnerabilities",
    "zero_day": "exploited_vulnerabilities",
    "apt": "nation_state",
    "espionage": "nation_state",
    "iot": "ot_ics",
    "iot_security": "ot_ics",
    "cloud_security": "cloud_identity",
    "identity": "cloud_identity",
    "regulation": "policy_regulation",
    "compliance": "policy_regulation",
    "research": "security_research",
    "tools": "tools_technology",
    "technology": "tools_technology",
    "general": "general_news",
    "general_cybersecurity": "general_news",
    "general_cybersecurity_news": "general_news",
    "geopolitical": "geopolitical_cyber",
    "geopolitical_cyber_development": "geopolitical_cyber",
    "geopolitical_development": "geopolitical_cyber",
    "cyber_diplomacy": "geopolitical_cyber",
    "sanctions": "geopolitical_cyber",
}


def normalize_category(raw: str, fallback: str = "active_threats") -> str:
    """Validate and normalise an AI-returned category to a valid enum value."""
    if raw in VALID_NEWS_CATEGORIES:
        return raw
    mapped = CATEGORY_FALLBACK_MAP.get(raw)
    if mapped:
        logger.info("category_remapped: raw=%s mapped=%s", raw, mapped)
        return mapped
    logger.warning("category_invalid_fallback: raw=%s fallback=%s", raw, fallback)
    return fallback


def detect_category(title: str, description: str) -> str:
    """Keyword-based category detection for initial RSS ingestion.

    AI enrichment refines the category later.
    """
    text = f"{title} {description}".lower()

    if any(k in text for k in ("ransomware", "breach", "leak", "stolen data", "extortion")):
        return "ransomware_breaches"
    if any(k in text for k in ("exploit", "vulnerability", "cve-", "zero-day", "0-day", "patch", "kev")):
        return "exploited_vulnerabilities"
    if any(k in text for k in ("apt", "nation-state", "nation state", "china", "russia", "iran", "north korea", "espionage")):
        return "nation_state"
    if any(k in text for k in ("cloud", "saas", "azure", "aws", "identity", "oauth", "sso", "credential")):
        return "cloud_identity"
    if any(k in text for k in ("ics", "ot ", "scada", "plc", "industrial", "operational technology")):
        return "ot_ics"
    if any(k in text for k in ("tool", "framework", "open source", "github", "release", "platform")):
        return "tools_technology"
    if any(k in text for k in ("policy", "regulation", "compliance", "gdpr", "law", "legislation", "executive order")):
        return "policy_regulation"
    if any(k in text for k in ("research", "analysis", "report", "study", "paper", "findings")):
        return "security_research"

    return "active_threats"
