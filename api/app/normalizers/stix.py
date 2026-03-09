"""STIX 2.1 bundle export — converts internal intelligence into STIX JSON.

Transforms IntelItems, IOCs, NewsItems (threat actors, malware, campaigns),
and relationships into STIX 2.1 SDOs (STIX Domain Objects) and SROs
(STIX Relationship Objects) for sharing with MISP, OpenCTI, and other
CTI platforms.

Produces valid STIX 2.1 JSON bundles per the OASIS specification:
https://docs.oasis-open.org/cti/stix/v2.1/os/stix-v2.1-os.html
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

# ── STIX 2.1 Constants ──────────────────────────────────

STIX_SPEC_VERSION = "2.1"

# TLP → STIX TLP marking-definition IDs (OASIS standard)
TLP_MARKING_IDS: dict[str, str] = {
    "TLP:CLEAR":        "marking-definition--613f2e26-407d-48c7-9eca-b8e91df99dc9",
    "TLP:GREEN":        "marking-definition--34098fce-860f-48ae-8e50-ebd3cc5e41da",
    "TLP:AMBER":        "marking-definition--f88d31f6-486f-44da-b317-01333bde0b82",
    "TLP:AMBER+STRICT": "marking-definition--826578e1-40a3-4b46-a8d8-b9931b7a7643",
    "TLP:RED":          "marking-definition--5e57c739-391a-4eb3-b6be-7d15ca92d5ed",
}

# IOC type → STIX SCO (STIX Cyber Observable) type + property
IOC_TYPE_MAP: dict[str, tuple[str, str]] = {
    "ip":           ("ipv4-addr",       "value"),
    "domain":       ("domain-name",     "value"),
    "url":          ("url",             "value"),
    "hash_md5":     ("file",            "hashes.MD5"),
    "hash_sha1":    ("file",            "hashes.SHA-1"),
    "hash_sha256":  ("file",            "hashes.SHA-256"),
    "email":        ("email-addr",      "value"),
}

# Severity → STIX confidence (0-100)
_SEVERITY_TO_CONFIDENCE: dict[str, int] = {
    "critical": 95, "high": 80, "medium": 60,
    "low": 35, "info": 15, "unknown": 0,
}

PLATFORM_IDENTITY_ID = "identity--" + str(
    uuid.uuid5(uuid.NAMESPACE_URL, "ti-platform")
)


def _deterministic_id(stix_type: str, *key_parts: str) -> str:
    """Generate a deterministic STIX ID from type + key parts."""
    raw = "|".join(str(p) for p in key_parts)
    ns = uuid.UUID("00abedb4-aa42-466c-9c01-fed23315a9b7")  # platform namespace
    return f"{stix_type}--{uuid.uuid5(ns, raw)}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _dt_iso(dt: datetime | str | None) -> str:
    if not dt:
        return _now_iso()
    if isinstance(dt, str):
        return dt
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ── Identity (the platform itself) ──────────────────────

def platform_identity() -> dict:
    """Return the STIX Identity SDO representing this TI platform."""
    return {
        "type": "identity",
        "spec_version": STIX_SPEC_VERSION,
        "id": PLATFORM_IDENTITY_ID,
        "created": "2025-01-01T00:00:00.000Z",
        "modified": _now_iso(),
        "name": "TI Platform",
        "identity_class": "system",
    }


# ── Indicator (IOC) ─────────────────────────────────────

def ioc_to_indicator(ioc: dict) -> dict:
    """Convert an IOC dict to a STIX Indicator SDO.

    Args:
        ioc: Dict with keys: value, ioc_type, risk_score, first_seen,
             last_seen, tags, source_names, context.
    """
    ioc_type = ioc.get("ioc_type", "")
    value = ioc.get("value", "")

    # Build STIX pattern
    pattern = _build_stix_pattern(ioc_type, value)
    if not pattern:
        return {}

    sid = _deterministic_id("indicator", ioc_type, value)
    confidence = min(100, ioc.get("risk_score", 50))

    indicator: dict = {
        "type": "indicator",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _dt_iso(ioc.get("first_seen")),
        "modified": _dt_iso(ioc.get("last_seen")),
        "name": f"{ioc_type.upper()}: {value}",
        "pattern": pattern,
        "pattern_type": "stix",
        "valid_from": _dt_iso(ioc.get("first_seen")),
        "confidence": confidence,
        "created_by_ref": PLATFORM_IDENTITY_ID,
        "labels": ioc.get("tags", [])[:10] or ["malicious-activity"],
    }

    tlp = ioc.get("tlp", "TLP:CLEAR")
    if tlp in TLP_MARKING_IDS:
        indicator["object_marking_refs"] = [TLP_MARKING_IDS[tlp]]

    return indicator


def _build_stix_pattern(ioc_type: str, value: str) -> str | None:
    """Build a STIX 2.1 pattern string from IOC type and value."""
    patterns = {
        "ip":          f"[ipv4-addr:value = '{value}']",
        "domain":      f"[domain-name:value = '{value}']",
        "url":         f"[url:value = '{value}']",
        "hash_md5":    f"[file:hashes.MD5 = '{value}']",
        "hash_sha1":   f"[file:hashes.'SHA-1' = '{value}']",
        "hash_sha256": f"[file:hashes.'SHA-256' = '{value}']",
        "email":       f"[email-addr:value = '{value}']",
    }
    return patterns.get(ioc_type)


# ── Threat Actor ─────────────────────────────────────────

def actor_to_stix(name: str, aliases: list[str] | None = None, **extra) -> dict:
    """Convert a threat actor to a STIX Threat Actor SDO."""
    sid = _deterministic_id("threat-actor", name)
    obj: dict = {
        "type": "threat-actor",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _now_iso(),
        "modified": _now_iso(),
        "name": name,
        "created_by_ref": PLATFORM_IDENTITY_ID,
    }
    if aliases:
        obj["aliases"] = aliases
    if extra.get("motivation"):
        obj["primary_motivation"] = extra["motivation"]
    if extra.get("nation_state"):
        obj["description"] = f"Nation-state: {extra['nation_state']}"
    return obj


# ── Malware ──────────────────────────────────────────────

def malware_to_stix(name: str) -> dict:
    """Convert a malware family name to a STIX Malware SDO."""
    sid = _deterministic_id("malware", name)
    return {
        "type": "malware",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _now_iso(),
        "modified": _now_iso(),
        "name": name,
        "is_family": True,
        "created_by_ref": PLATFORM_IDENTITY_ID,
    }


# ── Vulnerability (CVE) ─────────────────────────────────

def cve_to_vulnerability(cve_id: str, **extra) -> dict:
    """Convert a CVE ID to a STIX Vulnerability SDO."""
    sid = _deterministic_id("vulnerability", cve_id)
    obj: dict = {
        "type": "vulnerability",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _now_iso(),
        "modified": _now_iso(),
        "name": cve_id,
        "created_by_ref": PLATFORM_IDENTITY_ID,
        "external_references": [
            {
                "source_name": "cve",
                "external_id": cve_id,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            }
        ],
    }
    if extra.get("description"):
        obj["description"] = extra["description"]
    return obj


# ── Attack Pattern (MITRE technique) ────────────────────

def technique_to_attack_pattern(technique_id: str, technique_name: str = "") -> dict:
    """Convert a MITRE ATT&CK technique to a STIX Attack Pattern SDO."""
    sid = _deterministic_id("attack-pattern", technique_id)
    return {
        "type": "attack-pattern",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _now_iso(),
        "modified": _now_iso(),
        "name": technique_name or technique_id,
        "created_by_ref": PLATFORM_IDENTITY_ID,
        "external_references": [
            {
                "source_name": "mitre-attack",
                "external_id": technique_id,
                "url": f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/",
            }
        ],
    }


# ── Report (intel item / news item) ─────────────────────

def intel_to_report(item: dict, object_refs: list[str] | None = None) -> dict:
    """Convert an intel/news item to a STIX Report SDO."""
    item_id = str(item.get("id", uuid.uuid4()))
    sid = _deterministic_id("report", item_id)

    severity = item.get("severity", "unknown")
    confidence = _SEVERITY_TO_CONFIDENCE.get(severity, 50)

    obj: dict = {
        "type": "report",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _dt_iso(item.get("published_at") or item.get("ingested_at")),
        "modified": _dt_iso(item.get("updated_at")),
        "name": item.get("title") or item.get("headline", "Unknown"),
        "published": _dt_iso(item.get("published_at") or item.get("ingested_at")),
        "confidence": confidence,
        "created_by_ref": PLATFORM_IDENTITY_ID,
        "object_refs": object_refs or [],
    }

    desc = item.get("summary") or item.get("description", "")
    if desc:
        obj["description"] = desc

    labels = item.get("tags", [])[:10]
    if labels:
        obj["labels"] = labels

    tlp = item.get("tlp", "TLP:CLEAR")
    if tlp in TLP_MARKING_IDS:
        obj["object_marking_refs"] = [TLP_MARKING_IDS[tlp]]

    source_url = item.get("source_url")
    if source_url:
        obj["external_references"] = [{
            "source_name": item.get("source_name", "unknown"),
            "url": source_url,
        }]

    return obj


# ── Relationship (SRO) ──────────────────────────────────

def stix_relationship(
    source_ref: str,
    relationship_type: str,
    target_ref: str,
) -> dict:
    """Create a STIX Relationship SRO."""
    sid = _deterministic_id("relationship", source_ref, relationship_type, target_ref)
    return {
        "type": "relationship",
        "spec_version": STIX_SPEC_VERSION,
        "id": sid,
        "created": _now_iso(),
        "modified": _now_iso(),
        "relationship_type": relationship_type,
        "source_ref": source_ref,
        "target_ref": target_ref,
        "created_by_ref": PLATFORM_IDENTITY_ID,
    }


# ── Bundle builder ───────────────────────────────────────

def build_bundle(objects: list[dict]) -> dict:
    """Wrap a list of STIX objects into a STIX 2.1 Bundle."""
    # Deduplicate by ID
    seen: set[str] = set()
    unique: list[dict] = []
    for obj in objects:
        if not obj:
            continue
        oid = obj.get("id", "")
        if oid and oid not in seen:
            seen.add(oid)
            unique.append(obj)

    return {
        "type": "bundle",
        "id": f"bundle--{uuid.uuid4()}",
        "objects": [platform_identity()] + unique,
    }


def news_item_to_bundle(item: dict) -> dict:
    """Convert a single NewsItem (dict) into a complete STIX 2.1 Bundle.

    Extracts threat actors, malware, CVEs, techniques, IOCs from the news
    item and creates a Report SDO linking to all extracted entities.
    """
    objects: list[dict] = []
    report_refs: list[str] = []

    # Threat actors
    from app.normalizers.diamond import parse_actor_name
    for actor_raw in item.get("threat_actors") or []:
        primary, aliases = parse_actor_name(str(actor_raw))
        if primary:
            sdo = actor_to_stix(primary, aliases)
            objects.append(sdo)
            report_refs.append(sdo["id"])

    # Malware families
    for malware in item.get("malware_families") or []:
        sdo = malware_to_stix(str(malware))
        objects.append(sdo)
        report_refs.append(sdo["id"])

    # CVEs
    for cve in item.get("cves") or item.get("cve_ids") or []:
        sdo = cve_to_vulnerability(str(cve).upper())
        objects.append(sdo)
        report_refs.append(sdo["id"])

    # Techniques
    from app.normalizers.killchain import parse_technique
    for tt in item.get("tactics_techniques") or []:
        tid, tname = parse_technique(str(tt))
        if tid:
            sdo = technique_to_attack_pattern(tid, tname or tid)
            objects.append(sdo)
            report_refs.append(sdo["id"])

    # IOCs from ioc_summary
    ioc_summary = item.get("ioc_summary") or {}
    ioc_type_map = {
        "ips": "ip", "domains": "domain",
        "urls": "url", "hashes": "hash_sha256",
    }
    for summary_key, mapped_type in ioc_type_map.items():
        for val in ioc_summary.get(summary_key, []):
            ind = ioc_to_indicator({
                "value": str(val), "ioc_type": mapped_type,
                "risk_score": 50, "tags": item.get("tags", []),
            })
            if ind:
                objects.append(ind)
                report_refs.append(ind["id"])

    # Relationships: actor → uses → malware, actor → targets → vulnerability
    actor_ids = [o["id"] for o in objects if o.get("type") == "threat-actor"]
    malware_ids = [o["id"] for o in objects if o.get("type") == "malware"]
    vuln_ids = [o["id"] for o in objects if o.get("type") == "vulnerability"]
    indicator_ids = [o["id"] for o in objects if o.get("type") == "indicator"]

    for aid in actor_ids:
        for mid in malware_ids:
            objects.append(stix_relationship(aid, "uses", mid))
        for vid in vuln_ids:
            objects.append(stix_relationship(aid, "targets", vid))
        for iid in indicator_ids:
            objects.append(stix_relationship(iid, "indicates", aid))

    # Malware → exploits → vulnerability
    for mid in malware_ids:
        for vid in vuln_ids:
            objects.append(stix_relationship(mid, "exploits", vid))

    # Report SDO
    report = intel_to_report(item, object_refs=report_refs)
    objects.append(report)

    return build_bundle(objects)


def ioc_list_to_bundle(iocs: list[dict]) -> dict:
    """Convert a list of IOC dicts into a STIX 2.1 Bundle of Indicators."""
    indicators = [ioc_to_indicator(ioc) for ioc in iocs]
    return build_bundle([i for i in indicators if i])
