"""Intel items endpoints — feed listing, detail, export, enrichment."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select, or_, and_, cast, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Text as SAText

from app.core.database import get_db
from app.core.redis import cache_key, get_cached, set_cached
from app.core.config import get_settings
from app.core.logging import get_logger
from app.middleware.auth import get_current_user, require_viewer
from app.models.models import IntelItem, User, IOC, IntelIOCLink
from app.schemas import IntelItemListResponse, IntelItemResponse, IntelStatsResponse
from app.services import database as db_service
from app.services.ai import chat_completion_json
from app.services.export import export_to_excel

router = APIRouter(prefix="/intel", tags=["intel"])
settings = get_settings()
logger = get_logger("intel")


@router.get("", response_model=IntelItemListResponse)
async def list_intel_items(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: str | None = None,
    feed_type: str | None = None,
    source_name: str | None = None,
    asset_type: str | None = None,
    is_kev: bool | None = None,
    exploit_available: bool | None = None,
    query: str | None = Query(None, max_length=200),
    geo: str | None = Query(None, max_length=100),
    industry: str | None = Query(None, max_length=200),
    sort_by: str = Query("ingested_at", pattern="^(ingested_at|risk_score|severity|published_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List intel items with pagination and filters."""
    ck = cache_key("intel_list", page, page_size, severity, feed_type, source_name, asset_type, is_kev, exploit_available, query, geo, industry, sort_by, sort_order)
    cached = await get_cached(ck)
    if cached:
        return cached

    items, total = await db_service.get_intel_items(
        db,
        page=page,
        page_size=page_size,
        severity=severity,
        feed_type=feed_type,
        source_name=source_name,
        asset_type=asset_type,
        is_kev=is_kev,
        exploit_available=exploit_available,
        search=query,
        geo=geo,
        industry=industry,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    pages = max(1, (total + page_size - 1) // page_size)
    response = IntelItemListResponse(
        items=[IntelItemResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )

    await set_cached(ck, response.model_dump(), ttl=30)
    return response


@router.get("/export")
async def export_intel(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    severity: str | None = None,
    feed_type: str | None = None,
    page_size: int = Query(500, ge=1, le=5000),
):
    """Export intel items to Excel."""
    items, _ = await db_service.get_intel_items(
        db, page=1, page_size=page_size, severity=severity, feed_type=feed_type
    )

    item_dicts = [
        IntelItemResponse.model_validate(i).model_dump() for i in items
    ]
    excel_bytes = export_to_excel(item_dicts)

    filename = f"threat_intel_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=excel_bytes.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stats", response_model=IntelStatsResponse)
async def intel_stats(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Global stats for the Active Threats feed."""
    ck = cache_key("intel_stats")
    cached = await get_cached(ck)
    if cached:
        return cached

    from datetime import timedelta, timezone

    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    # Single aggregate query
    row = (await db.execute(
        select(
            func.count().label("total"),
            func.count().filter(IntelItem.ingested_at >= day_ago).label("today"),
            func.count().filter(IntelItem.severity == text("'critical'::severity_level")).label("critical"),
            func.count().filter(IntelItem.severity == text("'high'::severity_level")).label("high"),
            func.count().filter(IntelItem.severity == text("'medium'::severity_level")).label("medium"),
            func.count().filter(IntelItem.severity == text("'low'::severity_level")).label("low"),
            func.count().filter(IntelItem.severity == text("'info'::severity_level")).label("info"),
            func.count().filter(IntelItem.is_kev.is_(True)).label("kev_count"),
            func.count().filter(IntelItem.exploit_available.is_(True)).label("exploit_count"),
            func.coalesce(func.avg(IntelItem.risk_score), 0).label("avg_risk"),
            func.count(func.distinct(IntelItem.source_name)).label("sources"),
            func.count().filter(IntelItem.ai_summary.isnot(None)).label("ai_enriched"),
        )
    )).one()

    # Top sources
    src_rows = (await db.execute(
        select(IntelItem.source_name, func.count().label("cnt"))
        .group_by(IntelItem.source_name)
        .order_by(desc("cnt"))
        .limit(10)
    )).all()
    top_sources = [{"name": r.source_name, "count": r.cnt} for r in src_rows]

    # Top tags (unnest array)
    tag_rows = (await db.execute(
        select(
            func.unnest(IntelItem.tags).label("tag"),
            func.count().label("cnt")
        ).group_by("tag").order_by(desc("cnt")).limit(15)
    )).all()
    top_tags = [r.tag for r in tag_rows]

    # Top CVEs
    cve_rows = (await db.execute(
        select(
            func.unnest(IntelItem.cve_ids).label("cve"),
            func.count().label("cnt")
        ).group_by("cve").order_by(desc("cnt")).limit(10)
    )).all()
    top_cves = [r.cve for r in cve_rows]

    # Feed type distribution
    ft_rows = (await db.execute(
        select(
            cast(IntelItem.feed_type, SAText).label("ft"),
            func.count().label("cnt"),
        ).group_by(IntelItem.feed_type)
    )).all()
    feed_type_counts = {r.ft: r.cnt for r in ft_rows}

    # Asset type distribution
    at_rows = (await db.execute(
        select(
            cast(IntelItem.asset_type, SAText).label("at"),
            func.count().label("cnt"),
        ).group_by(IntelItem.asset_type)
    )).all()
    asset_type_counts = {r.at: r.cnt for r in at_rows}

    response = IntelStatsResponse(
        total=row.total,
        today=row.today,
        critical=row.critical,
        high=row.high,
        medium=row.medium,
        low=row.low,
        info=row.info,
        kev_count=row.kev_count,
        exploit_count=row.exploit_count,
        avg_risk=int(row.avg_risk),
        sources=row.sources,
        ai_enriched=row.ai_enriched,
        top_sources=top_sources,
        top_tags=top_tags,
        top_cves=top_cves,
        feed_type_counts=feed_type_counts,
        asset_type_counts=asset_type_counts,
    )
    await set_cached(ck, response.model_dump(), ttl=60)
    return response


@router.get("/{item_id}", response_model=IntelItemResponse)
async def get_intel_item(
    item_id: uuid.UUID,
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single intel item by ID."""
    item = await db_service.get_intel_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intel item not found")
    return IntelItemResponse.model_validate(item)


# ─── Enrichment ──────────────────────────────────────────

_ENRICHMENT_PROMPT_VERSION = "B-2.0"

_ENRICHMENT_SYSTEM_PROMPT = """You are a senior cyber threat intelligence analyst at a Fortune 100 SOC. You write for two audiences: a CISO who needs business-impact framing in ≤60 seconds, and a SOC analyst who needs detection rules and IOC-actionable details.

Given an intel item (vulnerability, threat, advisory, or indicator), produce a structured JSON enrichment analysis.

## QUALITY RULES — READ CAREFULLY

**BANNED PHRASES (never use these — they are meaningless filler):**
- "timely patching is crucial", "apply patches and updates", "keep software up to date"
- "monitor for suspicious/unusual activity", "implement robust security controls"
- "organizations should prioritize security", "stay vigilant"
- Any sentence that could apply to ANY intel item generically is FILLER — delete it.

**REQUIRED QUALITY: every bullet/sentence must contain at least ONE of:**
- A specific technology, CVE, tool name, or protocol
- A concrete SIEM query, log source, or EDR detection
- A measurable action with a clear owner (e.g., "IAM team should audit OAuth app grants in Entra ID within 48h")
- A named threat group, malware hash, or campaign identifier
- A quantified business impact (dollar amount, number of records, downtime hours)

**EXAMPLES — BAD vs GOOD:**

executive_summary BAD: "This vulnerability highlights the importance of timely patching."
executive_summary GOOD: "CVE-2024-3400 allows unauthenticated RCE in PAN-OS GlobalProtect (10.2/11.0/11.1). Volexity confirmed active exploitation since March 26 by UTA0218. CISA added it to KEV with a federal patch deadline of April 19. Any org with internet-facing Palo Alto firewalls faces full device compromise risk."

detection_opportunities BAD: "Monitor for suspicious network activity."
detection_opportunities GOOD: "Hunt for POST requests to /ssl-vpn/hipreport.php with shell metacharacters in the SESSID cookie — create a Suricata rule on content:\"/ssl-vpn/hipreport.php\"; pcre:\"/SESSID=.*[;|`$]/\""

remediation guidance BAD: "Apply the latest security patches."
remediation guidance GOOD: "Apply PAN-OS hotfix 10.2.9-h1, 11.0.4-h1, or 11.1.2-h3. If patching requires a maintenance window, immediately enable Threat Prevention signature 95187 and disable device telemetry as an interim measure."

## JSON SCHEMA — return ONLY valid JSON, no markdown fences:
{
  "executive_summary": "4-6 sentences structured as: (1) What is this threat/vuln with specific names/dates, (2) Technical mechanism in 1-2 sentences, (3) Scope of impact with numbers if available, (4) What this means for the organization. NEVER use filler.",
  "threat_actors": [{"name": "APT group or actor name", "aliases": ["other names"], "motivation": "financial/espionage/hacktivism/unknown", "confidence": "high/medium/low", "description": "1 sentence about this actor's involvement"}],
  "attack_techniques": [{"technique_id": "T1xxx or T1xxx.xxx", "technique_name": "Name", "tactic": "tactic-name", "description": "How this technique relates to this threat", "mitigations": ["specific mitigation action"]}],
  "attack_narrative": "4-6 sentences describing the technical attack chain step-by-step. Name specific tools, protocols, and techniques at each stage. If this is a vulnerability without a known attack chain, describe the most likely exploitation scenario.",
  "initial_access_vector": "Specific vector: 'Exploitation of internet-facing PAN-OS', 'Phishing with ISO attachment', 'Supply chain compromise via npm package', or null",
  "post_exploitation": ["Name specific tools & actions: 'LSASS credential dump via Nanodump', 'Lateral movement using WMI and PSExec'. 2-5 items. Empty [] if not applicable."],
  "affected_versions": [{"product": "Product Name", "vendor": "Vendor", "versions_affected": "< 5.2.1 or specific range", "fixed_version": "5.2.1 or null if unknown", "patch_url": "URL or null", "cpe": "cpe string or null"}],
  "timeline_events": [{"date": "YYYY-MM-DD or null", "event": "Event title", "description": "What happened", "type": "disclosure/publication/patch/exploit/kev/advisory/update"}],
  "notable_campaigns": [{"name": "Campaign or breach name", "date": "YYYY or approximate", "description": "Brief description", "impact": "Impact description"}],
  "exploitation_info": {"epss_estimate": 0.0, "exploit_maturity": "none/poc/weaponized/unknown", "in_the_wild": true, "ransomware_use": false, "description": "Brief exploitation context"},
  "detection_opportunities": ["3-5 items. Each MUST name a log source, query pattern, or signature ID. Examples: 'Sigma rule for regsvr32 loading DLL from user temp folder', 'Snort SID 300125 for CobaltStrike beacon HTTP profile', 'Windows Event 4688 + CommandLine containing certutil -urlcache'. No vague 'monitor for anomalies'."],
  "ioc_summary": {"domains": [], "ips": [], "hashes": [], "urls": []},
  "targeted_sectors": ["Specific sectors: 'Government — Defense', 'Financial Services — Banking'. Always at least 1."],
  "targeted_regions": ["Specific regions: 'South Korea', 'Western Europe', 'United States — Federal'. Always at least 1."],
  "impacted_assets": ["Specific asset types: 'Palo Alto GlobalProtect VPN appliances', 'Chrome browser on Windows/Mac/Linux'. Not generic 'endpoints'."],
  "remediation": {"priority": "critical/high/medium/low", "guidance": ["Step 1 — must name specific fix: patch version, config change, GPO setting", "Step 2"], "workarounds": ["Workaround if no patch — must be specific"], "references": [{"title": "Reference name", "url": "URL"}]},
  "related_cves": ["CVE-YYYY-NNNNN — include co-exploited or chained CVEs"],
  "tags_suggested": ["tag1", "tag2"],
  "recommended_priority": "critical/high/medium/low",
  "confidence": "high/medium/low",
  "source_reliability": "authoritative/credible/speculative/unknown"
}

Rules:
- Only include data you are confident about. Leave arrays empty if unsure.
- For CVEs, base analysis on known vulnerability data. Include NVD publication, vendor advisory, and exploit dates when known.
- For threat actors, only name those with documented associations.
- Be specific with version info. If unknown, set fixed_version to null.
- EPSS estimate: provide your best estimate of exploitation probability (0-1 scale).
- Return ONLY the JSON object, no markdown, no explanation."""


@router.get("/{item_id}/enrichment")
async def get_intel_enrichment(
    item_id: uuid.UUID,
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """AI-powered enrichment analysis for an intel item."""
    # Check cache first
    ck = cache_key("intel_enrichment", str(item_id))
    cached = await get_cached(ck)
    if cached:
        return cached

    # Get item
    item = await db_service.get_intel_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intel item not found")

    # Build prompt
    parts = [
        f"Title: {item.title}",
        f"Severity: {item.severity}",
        f"Risk Score: {item.risk_score}/100",
        f"Source: {item.source_name}",
        f"Feed Type: {item.feed_type}",
        f"Published: {item.published_at.isoformat() if item.published_at else 'N/A'}",
    ]
    if item.description:
        parts.append(f"Description: {item.description[:2000]}")
    if item.cve_ids:
        parts.append(f"CVE IDs: {', '.join(item.cve_ids[:10])}")
    if item.affected_products:
        parts.append(f"Affected Products: {', '.join(item.affected_products[:10])}")
    if item.tags:
        parts.append(f"Tags: {', '.join(item.tags[:15])}")
    if item.is_kev:
        parts.append("This vulnerability is in CISA KEV (Known Exploited Vulnerabilities)")
    if item.exploit_available:
        parts.append("Exploits are known to be available")
    if item.exploitability_score is not None:
        parts.append(f"CVSS/Exploitability Score: {item.exploitability_score}")
    if item.geo:
        parts.append(f"Geographic context: {', '.join(item.geo[:10])}")
    if item.industries:
        parts.append(f"Industries: {', '.join(item.industries[:10])}")
    if item.ai_summary:
        parts.append(f"AI Summary: {item.ai_summary[:500]}")

    user_prompt = "\n".join(parts)

    # Call AI with JSON validation and retry
    enrichment = await chat_completion_json(
        system_prompt=_ENRICHMENT_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        max_tokens=3000,
        temperature=0.2,
        required_keys=["executive_summary", "threat_actors", "attack_techniques"],
        caller="intel_enrichment",
        feature="intel_enrichment",
    )

    if not enrichment:
        enrichment = _empty_enrichment()
    else:
        enrichment["_prompt_version"] = _ENRICHMENT_PROMPT_VERSION

    # Cache for 6 hours
    await set_cached(ck, enrichment, ttl=21600)
    return enrichment


def _empty_enrichment() -> dict:
    return {
        "executive_summary": None,
        "threat_actors": [],
        "attack_techniques": [],
        "attack_narrative": None,
        "initial_access_vector": None,
        "post_exploitation": [],
        "affected_versions": [],
        "timeline_events": [],
        "notable_campaigns": [],
        "exploitation_info": {
            "epss_estimate": None,
            "exploit_maturity": "unknown",
            "in_the_wild": False,
            "ransomware_use": False,
            "description": None,
        },
        "detection_opportunities": [],
        "ioc_summary": {"domains": [], "ips": [], "hashes": [], "urls": []},
        "targeted_sectors": [],
        "targeted_regions": [],
        "impacted_assets": [],
        "remediation": {
            "priority": None,
            "guidance": [],
            "workarounds": [],
            "references": [],
        },
        "related_cves": [],
        "tags_suggested": [],
        "recommended_priority": None,
        "confidence": None,
        "source_reliability": None,
        "_prompt_version": _ENRICHMENT_PROMPT_VERSION,
    }


# ─── Related Intel (DB-based) ─────────────────────────────

@router.get("/{item_id}/related")
async def get_related_intel(
    item_id: uuid.UUID,
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=50),
):
    """Find related intel items based on shared CVEs, tags, and products."""
    ck = cache_key("intel_related", str(item_id), limit)
    cached = await get_cached(ck)
    if cached:
        return cached

    item = await db_service.get_intel_item_by_id(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Intel item not found")

    # Build overlap conditions using PostgreSQL && operator
    conditions = []
    if item.cve_ids:
        conditions.append(IntelItem.cve_ids.op("&&")(cast(item.cve_ids, ARRAY(SAText))))
    if item.tags:
        conditions.append(IntelItem.tags.op("&&")(cast(item.tags, ARRAY(SAText))))
    if item.affected_products:
        conditions.append(IntelItem.affected_products.op("&&")(cast(item.affected_products, ARRAY(SAText))))

    if not conditions:
        return []

    query = (
        select(IntelItem)
        .where(
            and_(
                IntelItem.id != item.id,
                or_(*conditions),
            )
        )
        .order_by(IntelItem.risk_score.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    related = []
    for r in rows:
        # Determine relationship type
        rel_type = "related"
        shared_cves = set(r.cve_ids or []) & set(item.cve_ids or [])
        shared_tags = set(r.tags or []) & set(item.tags or [])
        shared_products = set(r.affected_products or []) & set(item.affected_products or [])

        if shared_cves:
            rel_type = "shared_cve"
        elif shared_products:
            rel_type = "shared_product"
        elif shared_tags:
            rel_type = "shared_tag"

        # Calculate confidence based on overlap
        overlap_score = len(shared_cves) * 40 + len(shared_products) * 30 + len(shared_tags) * 10
        confidence = min(95, max(20, overlap_score))

        related.append({
            "id": str(r.id),
            "title": r.title,
            "severity": r.severity,
            "risk_score": r.risk_score,
            "source_name": r.source_name,
            "feed_type": r.feed_type,
            "ingested_at": r.ingested_at.isoformat(),
            "relationship_type": rel_type,
            "confidence": confidence,
            "shared_cves": list(shared_cves)[:5],
            "shared_tags": list(shared_tags)[:5],
            "shared_products": list(shared_products)[:3],
        })

    # Sort by confidence desc
    related.sort(key=lambda x: x["confidence"], reverse=True)

    await set_cached(ck, related, ttl=300)
    return related


# ─── Linked IOCs ─────────────────────────────────────────

@router.get("/{item_id}/iocs")
async def get_intel_iocs(
    item_id: uuid.UUID,
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=200),
):
    """Get IOCs linked to this intel item."""
    ck = cache_key("intel_iocs", str(item_id), limit)
    cached = await get_cached(ck)
    if cached:
        return cached

    query = (
        select(IOC, IntelIOCLink.relationship)
        .join(IntelIOCLink, IOC.id == IntelIOCLink.ioc_id)
        .where(IntelIOCLink.intel_id == item_id)
        .order_by(desc(IOC.risk_score), desc(IOC.last_seen))
        .limit(limit)
    )
    rows = (await db.execute(query)).all()

    iocs = []
    for r in rows:
        ioc = r.IOC
        internetdb = (ioc.context or {}).get("internetdb", {})
        epss = (ioc.context or {}).get("epss", {})
        iocs.append({
            "id": str(ioc.id),
            "value": ioc.value,
            "ioc_type": ioc.ioc_type,
            "risk_score": ioc.risk_score,
            "first_seen": ioc.first_seen.isoformat() if ioc.first_seen else None,
            "last_seen": ioc.last_seen.isoformat() if ioc.last_seen else None,
            "sighting_count": ioc.sighting_count,
            "tags": ioc.tags or [],
            "geo": ioc.geo or [],
            "source_names": ioc.source_names or [],
            "relationship": r.relationship,
            # IPinfo
            "country_code": ioc.country_code,
            "country": ioc.country,
            "asn": ioc.asn,
            "as_name": ioc.as_name,
            # InternetDB
            "ports": internetdb.get("ports", []),
            "vulns": internetdb.get("vulns", []),
            "cpes": internetdb.get("cpes", []),
            "hostnames": internetdb.get("hostnames", []),
            "internetdb_tags": internetdb.get("tags", []),
            # EPSS
            "epss_score": epss.get("score"),
            "epss_percentile": epss.get("percentile"),
        })

    await set_cached(ck, iocs, ttl=120)
    return iocs
