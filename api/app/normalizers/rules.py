"""Sigma rule generation from intelligence context.

Produces Sigma detection rules (YAML format) from enriched news items
and IOC data, enabling cross-SIEM portability (Splunk, Elastic,
Sentinel, QRadar, CrowdStrike LogScale).

Sigma specification: https://sigmahq.io/docs/basics/rules.html
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any

# ── Sigma status levels ──────────────────────────────────
SIGMA_STATUSES = ("experimental", "test", "stable")

# Severity → Sigma level
SEVERITY_TO_LEVEL: dict[str, str] = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
    "info": "informational",
    "unknown": "medium",
}

# IOC type → Sigma logsource + field mappings
_IOC_LOGSOURCE: dict[str, dict] = {
    "ip": {
        "category": "firewall",
        "fields": {"DestinationIp": None, "SourceIp": None},
    },
    "domain": {
        "category": "dns",
        "fields": {"QueryName": None},
    },
    "url": {
        "category": "proxy",
        "fields": {"c-uri": None, "cs-uri-stem": None},
    },
    "hash_sha256": {
        "category": "process_creation",
        "product": "windows",
        "fields": {"Hashes": None},
    },
    "hash_sha1": {
        "category": "process_creation",
        "product": "windows",
        "fields": {"Hashes": None},
    },
    "hash_md5": {
        "category": "process_creation",
        "product": "windows",
        "fields": {"Hashes": None},
    },
}

# ATT&CK tactic → Sigma logsource hint
_TACTIC_LOGSOURCE: dict[str, dict] = {
    "initial-access":       {"category": "process_creation", "product": "windows"},
    "execution":            {"category": "process_creation", "product": "windows"},
    "persistence":          {"category": "registry_event", "product": "windows"},
    "privilege-escalation": {"category": "process_creation", "product": "windows"},
    "defense-evasion":      {"category": "process_creation", "product": "windows"},
    "credential-access":    {"category": "process_creation", "product": "windows"},
    "discovery":            {"category": "process_creation", "product": "windows"},
    "lateral-movement":     {"category": "network_connection", "product": "windows"},
    "collection":           {"category": "file_event", "product": "windows"},
    "command-and-control":  {"category": "network_connection", "product": "windows"},
    "exfiltration":         {"category": "network_connection", "product": "windows"},
    "impact":               {"category": "process_creation", "product": "windows"},
}


def _yaml_str(value: str) -> str:
    """Escape a string for safe YAML embedding."""
    if any(c in value for c in (":", "#", "{", "}", "[", "]", "'", '"', "\n")):
        escaped = value.replace("'", "''")
        return f"'{escaped}'"
    return value


def _generate_sigma_id() -> str:
    """Generate a Sigma-compliant UUID."""
    return str(uuid.uuid4())


def ioc_to_sigma(
    ioc_type: str,
    values: list[str],
    *,
    title: str = "",
    description: str = "",
    severity: str = "medium",
    tags: list[str] | None = None,
    references: list[str] | None = None,
) -> str | None:
    """Generate a Sigma rule for a set of IOC values of the same type.

    Args:
        ioc_type: One of ip, domain, url, hash_md5, hash_sha1, hash_sha256.
        values: List of IOC values.
        title: Rule title override.
        description: Rule description.
        severity: Severity level.
        tags: ATT&CK tags (e.g., ["attack.initial_access", "attack.t1566"]).
        references: Reference URLs.

    Returns:
        Sigma rule as YAML string, or None if IOC type unsupported.
    """
    if not values or ioc_type not in _IOC_LOGSOURCE:
        return None

    config = _IOC_LOGSOURCE[ioc_type]
    level = SEVERITY_TO_LEVEL.get(severity, "medium")
    rule_title = title or f"IntelPulse - Malicious {ioc_type.upper()} Indicator"

    lines = [
        f"title: {_yaml_str(rule_title)}",
        f"id: {_generate_sigma_id()}",
        "status: experimental",
        f"description: {_yaml_str(description or f'Detects network activity involving known malicious {ioc_type} indicators from threat intelligence.')}",
    ]

    if references:
        lines.append("references:")
        for ref in references[:5]:
            lines.append(f"    - {_yaml_str(ref)}")

    lines.append(f"date: {datetime.now(timezone.utc).strftime('%Y/%m/%d')}")
    lines.append("author: IntelPulse (auto-generated)")

    # Tags
    sigma_tags = tags or []
    if not sigma_tags:
        sigma_tags = ["attack.command_and_control"]
    lines.append("tags:")
    for tag in sigma_tags[:10]:
        lines.append(f"    - {tag}")

    # Logsource
    lines.append("logsource:")
    lines.append(f"    category: {config['category']}")
    if "product" in config:
        lines.append(f"    product: {config['product']}")

    # Detection
    lines.append("detection:")
    lines.append("    selection:")

    fields = list(config["fields"].keys())

    if ioc_type in ("hash_md5", "hash_sha1", "hash_sha256"):
        # Hash matching uses contains with algorithm prefix
        hash_algo = {"hash_md5": "MD5", "hash_sha1": "SHA1", "hash_sha256": "SHA256"}[ioc_type]
        field = fields[0]
        lines.append(f"        {field}|contains:")
        for v in values[:50]:
            lines.append(f"            - {_yaml_str(v)}")
    elif len(fields) == 1:
        field = fields[0]
        if len(values) == 1:
            lines.append(f"        {field}: {_yaml_str(values[0])}")
        else:
            lines.append(f"        {field}:")
            for v in values[:50]:
                lines.append(f"            - {_yaml_str(v)}")
    else:
        # Multiple fields (e.g., SourceIp/DestinationIp) — use OR logic
        for i, field in enumerate(fields):
            selector = f"selection_{i}" if i > 0 else "selection"
            if i > 0:
                lines.append(f"    {selector}:")
            if len(values) == 1:
                lines.append(f"        {field}: {_yaml_str(values[0])}")
            else:
                lines.append(f"        {field}:")
                for v in values[:50]:
                    lines.append(f"            - {_yaml_str(v)}")

        # OR conditions
        if len(fields) > 1:
            cond_parts = ["selection"] + [f"selection_{i}" for i in range(1, len(fields))]
            lines.append(f"    condition: {' or '.join(cond_parts)}")
        else:
            lines.append("    condition: selection")
    if len(fields) <= 1:
        lines.append("    condition: selection")

    lines.append(f"level: {level}")
    lines.append("falsepositives:")
    lines.append("    - Legitimate traffic to the listed indicators")

    return "\n".join(lines) + "\n"


def news_item_to_sigma(item: dict) -> list[str]:
    """Generate Sigma rules from a NewsItem dict.

    Produces separate rules for each IOC type found in ioc_summary,
    with context from the news item (title, CVEs, techniques, actors).

    Returns:
        List of Sigma rule YAML strings.
    """
    rules: list[str] = []
    ioc_summary = item.get("ioc_summary") or {}
    severity = item.get("recommended_priority") or item.get("severity", "medium")
    headline = item.get("headline") or item.get("title", "Unknown Threat")
    source_url = item.get("source_url", "")
    references = [source_url] if source_url else []

    # Build ATT&CK tags from tactics_techniques
    sigma_tags = _build_attack_tags(item.get("tactics_techniques") or [])

    # Map ioc_summary keys to normalised IOC types
    key_map = {
        "ips": "ip", "domains": "domain",
        "urls": "url", "hashes": "hash_sha256",
    }

    for summary_key, ioc_type in key_map.items():
        values = ioc_summary.get(summary_key, [])
        if not values:
            continue

        rule = ioc_to_sigma(
            ioc_type=ioc_type,
            values=[str(v) for v in values],
            title=f"{headline[:200]} - {ioc_type.upper()} IOCs",
            description=_build_description(item, ioc_type),
            severity=severity,
            tags=sigma_tags,
            references=references,
        )
        if rule:
            rules.append(rule)

    return rules


def _build_attack_tags(tactics_techniques: list[str]) -> list[str]:
    """Extract Sigma-compatible ATT&CK tags from technique strings."""
    from app.normalizers.killchain import parse_technique

    tags: list[str] = []
    for tt in tactics_techniques:
        tid, _ = parse_technique(str(tt))
        if tid:
            tags.append(f"attack.{tid.lower()}")
    if not tags:
        tags.append("attack.command_and_control")
    return tags


def _build_description(item: dict, ioc_type: str) -> str:
    """Build a descriptive string for the Sigma rule."""
    parts = [f"Detects {ioc_type} indicators associated with:"]

    headline = item.get("headline") or item.get("title", "")
    if headline:
        parts.append(headline[:200])

    actors = item.get("threat_actors") or []
    if actors:
        parts.append(f"Threat Actors: {', '.join(str(a) for a in actors[:5])}")

    malware = item.get("malware_families") or []
    if malware:
        parts.append(f"Malware: {', '.join(str(m) for m in malware[:5])}")

    cves = item.get("cves") or item.get("cve_ids") or []
    if cves:
        parts.append(f"CVEs: {', '.join(str(c) for c in cves[:10])}")

    return " | ".join(parts)
