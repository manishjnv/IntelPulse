"""Test script for NVD enrichment, junk filtering, and cross-links.
Run inside the API container: docker exec ti-platform-api-1 python3 /tmp/test_enrichment.py
"""
import httpx
import json
import sys
import uuid
import asyncio

BASE = "http://localhost:8000/api/v1"

sys.path.insert(0, "/app")


def get_session_cookie():
    """Create a valid session cookie using the app's JWT + Redis session."""
    from app.services.auth import create_access_token
    from app.core.redis import redis_client

    session_id = str(uuid.uuid4())
    token = create_access_token({
        "sub": "test-admin",
        "email": "admin@intelwatch.in",
        "role": "admin",
        "name": "Admin",
        "sid": session_id,
    })

    async def _store():
        await redis_client.set(f"session:{session_id}", "test-admin", ex=300)

    asyncio.run(_store())
    return token


token = get_session_cookie()
cookies = {"iw_session": token}

print("=== 1. Vulnerable Products (all) ===")
r = httpx.get(f"{BASE}/news/vulnerable-products", params={"window": "all", "limit": "5"}, cookies=cookies)
if r.status_code != 200:
    print(f"FAILED: {r.status_code} {r.text[:300]}")
    sys.exit(1)
d = r.json()
print(f"Status: {r.status_code}, Total: {d['total']}")
for i in d["items"][:5]:
    rc = len(i.get("related_campaigns", []))
    actors = ", ".join(c["actor_name"] for c in i.get("related_campaigns", [])[:2])
    name = i["product_name"][:28].ljust(28)
    cve = str(i["cve_id"] or "--").ljust(18)
    cvss = str(i["cvss_score"]).ljust(5)
    epss = str(i["epss_score"]).ljust(5)
    kev = str(i["is_kev"]).ljust(5)
    expl = str(i["exploit_available"]).ljust(5)
    patch = str(i["patch_available"]).ljust(5)
    print(f"  {name} | CVE={cve} | CVSS={cvss} | EPSS={epss} | KEV={kev} | Exploit={expl} | Patch={patch} | Actors={rc} {actors}")

print()
print("=== 2. Vulnerable Products (24h) ===")
r = httpx.get(f"{BASE}/news/vulnerable-products", params={"window": "24h", "limit": "3"}, cookies=cookies)
d = r.json()
print(f"Status: {r.status_code}, Total: {d['total']}")

print()
print("=== 3. Threat Campaigns (all) ===")
r = httpx.get(f"{BASE}/news/threat-campaigns", params={"window": "all", "limit": "5"}, cookies=cookies)
d = r.json()
print(f"Status: {r.status_code}, Total: {d['total']}")
for i in d["items"][:5]:
    rp = len(i.get("related_products", []))
    prods = ", ".join(p["product_name"][:20] for p in i.get("related_products", [])[:2])
    cves = ", ".join(i.get("cves_exploited", [])[:2])
    actor = i["actor_name"][:22].ljust(22)
    camp = str(i.get("campaign_name") or "--")[:20].ljust(20)
    sev = i["severity"].ljust(8)
    cve_str = cves[:30].ljust(30)
    print(f"  {actor} | Campaign={camp} | Sev={sev} | CVEs={cve_str} | Products={rp} {prods}")

print()
print("=== 4. Threat Campaigns (7d) ===")
r = httpx.get(f"{BASE}/news/threat-campaigns", params={"window": "7d", "limit": "3"}, cookies=cookies)
d = r.json()
print(f"Status: {r.status_code}, Total: {d['total']}")

print()
print("=== 5. Extraction Stats ===")
r = httpx.get(f"{BASE}/news/extraction-stats", cookies=cookies)
d = r.json()
print(f"Status: {r.status_code}")
print(f"  Products: {d['vulnerable_products_count']}, Campaigns: {d['threat_campaigns_count']}")
print(f"  Last extraction: {d['last_extraction_at']}")

print()
print("=== 6. Enrichment Coverage ===")
r = httpx.get(f"{BASE}/news/vulnerable-products", params={"window": "all", "limit": "200"}, cookies=cookies)
d = r.json()
items = d["items"]
with_cvss = sum(1 for i in items if i["cvss_score"] is not None)
with_epss = sum(1 for i in items if i["epss_score"] is not None)
with_kev = sum(1 for i in items if i["is_kev"])
with_exploit = sum(1 for i in items if i["exploit_available"])
with_patch = sum(1 for i in items if i["patch_available"])
with_linked = sum(1 for i in items if len(i.get("related_campaigns", [])) > 0)
print(f"  Total items: {len(items)}")
print(f"  With CVSS:       {with_cvss}/{len(items)}")
print(f"  With EPSS:       {with_epss}/{len(items)}")
print(f"  CISA KEV:        {with_kev}/{len(items)}")
print(f"  Exploit avail:   {with_exploit}/{len(items)}")
print(f"  Patch avail:     {with_patch}/{len(items)}")
print(f"  Linked actors:   {with_linked}/{len(items)}")

print()
r = httpx.get(f"{BASE}/news/threat-campaigns", params={"window": "all", "limit": "200"}, cookies=cookies)
d = r.json()
items = d["items"]
with_linked = sum(1 for i in items if len(i.get("related_products", [])) > 0)
with_cves = sum(1 for i in items if len(i.get("cves_exploited", [])) > 0)
null_names = sum(1 for i in items if i.get("campaign_name") in (None, "", "null", "Unknown"))
print(f"  Campaigns total:      {len(items)}")
print(f"  With CVEs:            {with_cves}/{len(items)}")
print(f"  With linked products: {with_linked}/{len(items)}")
print(f"  Null/junk names:      {null_names}/{len(items)}")

print()
print("=== 7. Schema Validation ===")
product_fields = [
    "id", "product_name", "vendor", "cve_id", "cvss_score", "epss_score",
    "severity", "is_kev", "exploit_available", "patch_available",
    "affected_versions", "targeted_sectors", "targeted_regions",
    "source_count", "source_news_ids", "source_articles",
    "related_campaigns", "first_seen", "last_seen", "confidence",
]
campaign_fields = [
    "id", "actor_name", "campaign_name", "first_seen", "last_seen",
    "severity", "targeted_sectors", "targeted_regions", "malware_used",
    "techniques_used", "cves_exploited", "source_count", "source_news_ids",
    "source_articles", "related_products", "confidence",
]

r = httpx.get(f"{BASE}/news/vulnerable-products", params={"window": "all", "limit": "1"}, cookies=cookies)
item = r.json()["items"][0]
missing_p = [f for f in product_fields if f not in item]
extra_p = [f for f in item if f not in product_fields]
print(f"  Product fields missing: {missing_p or 'none'}")
print(f"  Product fields extra:   {extra_p or 'none'}")

# Validate related_campaigns shape
if item.get("related_campaigns"):
    rc = item["related_campaigns"][0]
    rc_fields = ["id", "actor_name", "campaign_name", "severity"]
    missing_rc = [f for f in rc_fields if f not in rc]
    print(f"  RelatedCampaignBrief fields missing: {missing_rc or 'none'}")
else:
    print("  (no related_campaigns to validate shape)")

r = httpx.get(f"{BASE}/news/threat-campaigns", params={"window": "all", "limit": "1"}, cookies=cookies)
item = r.json()["items"][0]
missing_c = [f for f in campaign_fields if f not in item]
extra_c = [f for f in item if f not in campaign_fields]
print(f"  Campaign fields missing: {missing_c or 'none'}")
print(f"  Campaign fields extra:   {extra_c or 'none'}")

# Validate related_products shape
if item.get("related_products"):
    rp = item["related_products"][0]
    rp_fields = ["id", "product_name", "vendor", "cve_id", "cvss_score", "severity"]
    missing_rp = [f for f in rp_fields if f not in rp]
    print(f"  RelatedProductBrief fields missing: {missing_rp or 'none'}")
else:
    print("  (no related_products to validate shape)")

print()
errors = []
if missing_p:
    errors.append(f"Product missing fields: {missing_p}")
if missing_c:
    errors.append(f"Campaign missing fields: {missing_c}")

if errors:
    print("=== FAILURES ===")
    for e in errors:
        print(f"  FAIL: {e}")
else:
    print("=== ALL TESTS PASSED ===")
