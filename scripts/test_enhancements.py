#!/usr/bin/env python3
"""Test all enhancement endpoints and verify data enrichment."""
import json
import urllib.request
import sys

API = "http://172.19.0.7:8000/api/v1"

def get(path):
    try:
        r = urllib.request.urlopen(f"{API}{path}", timeout=30)
        return json.loads(r.read())
    except Exception as e:
        return {"_error": str(e)}

def test(name, result, checks):
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    if "_error" in result:
        print(f"  FAIL: {result['_error']}")
        return False
    ok = True
    for label, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {label}: {detail}")
        if not passed:
            ok = False
    return ok

# --- Test 1: Dashboard Enrichment ---
d = get("/enrichment/dashboard")
test("Dashboard Enrichment", d, [
    ("Has keys", set(d.keys()) >= {"active_campaigns", "threat_velocity", "sector_threats", "trending_cves"},
     f"keys={list(d.keys())}"),
    ("Campaigns", len(d.get("active_campaigns", {}).get("campaigns", [])) > 0,
     f"{len(d.get('active_campaigns', {}).get('campaigns', []))} campaigns"),
    ("Velocity items", len(d.get("threat_velocity", {}).get("items", [])) > 0,
     f"{len(d.get('threat_velocity', {}).get('items', []))} items"),
    ("Sectors", len(d.get("sector_threats", {}).get("sectors", [])) > 0,
     f"{len(d.get('sector_threats', {}).get('sectors', []))} sectors"),
])

# --- Test 2: Threat Velocity - enriched fields ---
vel = d.get("threat_velocity", {}).get("items", [])
cve_items = [v for v in vel if v.get("entity_type") == "cve"]
actor_items = [v for v in vel if v.get("entity_type") == "actor"]
print(f"\n  Velocity breakdown: {len(cve_items)} CVEs, {len(actor_items)} actors")

has_product = any(v.get("product_name") for v in cve_items)
has_kev = any(v.get("is_kev") is not None for v in cve_items)
has_patch = any(v.get("patch_available") is not None for v in cve_items)
has_exploit = any(v.get("exploit_available") is not None for v in cve_items)
has_published = any(v.get("published_at") for v in cve_items)
has_headline = any(v.get("recent_headline") for v in actor_items)
has_sectors = any(v.get("targeted_sectors") for v in actor_items)

test("Threat Velocity Enrichment", d, [
    ("CVE product_name field", has_product, f"found={has_product}"),
    ("CVE is_kev field", has_kev, f"found={has_kev}"),
    ("CVE patch_available field", has_patch, f"found={has_patch}"),
    ("CVE exploit_available field", has_exploit, f"found={has_exploit}"),
    ("CVE published_at field", has_published, f"found={has_published}"),
    ("Actor recent_headline", has_headline, f"found={has_headline}"),
    ("Actor targeted_sectors", has_sectors, f"found={has_sectors}"),
])

# Print sample CVE item
if cve_items:
    print(f"\n  Sample CVE item: {json.dumps(cve_items[0], indent=2, default=str)}")
if actor_items:
    print(f"\n  Sample Actor item: {json.dumps(actor_items[0], indent=2, default=str)}")

# --- Test 3: Active Campaigns - enriched fields ---
camps = d.get("active_campaigns", {}).get("campaigns", [])
if camps:
    c = camps[0]
    test("Active Campaign Fields", d, [
        ("Has campaign_name", bool(c.get("campaign_name")), c.get("campaign_name", "")),
        ("Has actor_name", "actor_name" in c, c.get("actor_name", "N/A")),
        ("Has severity", "severity" in c, c.get("severity", "N/A")),
        ("Has cves_exploited", "cves_exploited" in c, f"{len(c.get('cves_exploited', []))} CVEs"),
        ("Has techniques_used", "techniques_used" in c, f"{len(c.get('techniques_used', []))} techniques"),
        ("Has targeted_sectors", "targeted_sectors" in c, f"{c.get('targeted_sectors', [])}"),
        ("Has targeted_regions", "targeted_regions" in c, f"{c.get('targeted_regions', [])}"),
    ])
    print(f"\n  Sample campaign: {json.dumps(c, indent=2, default=str)}")

# --- Test 4: Sector Threat Map ---
sectors = d.get("sector_threats", {}).get("sectors", [])
if sectors:
    s = sectors[0]
    test("Sector Threat Map", d, [
        ("Has sector", bool(s.get("sector")), s.get("sector")),
        ("Has actor_names", "actor_names" in s, f"{s.get('actor_names', [])}"),
        ("Has max_severity", "max_severity" in s, s.get("max_severity", "N/A")),
        ("Has campaign_count", "campaign_count" in s, s.get("campaign_count")),
    ])

# --- Test 5: Technique Campaign Usage ---
tech = get("/enrichment/technique-usage")
test("Technique Usage (Heatmap)", tech, [
    ("Not error", "_error" not in tech, "endpoint responded"),
    ("Has items", len(tech) > 0 if isinstance(tech, list) else bool(tech), f"type={type(tech).__name__}"),
])
if isinstance(tech, list) and tech:
    print(f"  Sample: {json.dumps(tech[0], indent=2, default=str)}")
elif isinstance(tech, dict) and "techniques" in tech:
    items = tech["techniques"]
    if items:
        print(f"  Sample: {json.dumps(items[0], indent=2, default=str)}")

# --- Test 6: Detection Rules ---
rules = get("/enrichment/detection-rules?limit=5")
test("Detection Rules", rules, [
    ("Not error", "_error" not in rules, "endpoint responded"),
    ("Has rules", isinstance(rules, list) and len(rules) > 0, f"{len(rules) if isinstance(rules, list) else 0} rules"),
])
if isinstance(rules, list) and rules:
    r = rules[0]
    print(f"  Rule: {r.get('name')} | type={r.get('rule_type')} | sev={r.get('severity')}")
    print(f"  Has content: {bool(r.get('content'))} ({len(r.get('content', ''))} chars)")

# --- Test 7: Detection Coverage ---
cov = get("/enrichment/detection-coverage")
test("Detection Coverage", cov, [
    ("Not error", "_error" not in cov, "endpoint responded"),
    ("total_rules", (cov.get("total_rules", 0) if isinstance(cov, dict) else 0) >= 0, 
     f"{cov.get('total_rules', 0) if isinstance(cov, dict) else 'N/A'}"),
])
if isinstance(cov, dict):
    print(f"  Coverage: total={cov.get('total_rules')} yara={cov.get('yara_count')} sigma={cov.get('sigma_count')} kql={cov.get('kql_count')}")

# --- Test 8: Briefings ---
briefs = get("/enrichment/briefings?limit=5")
test("Briefings", briefs, [
    ("Not error", "_error" not in briefs, "endpoint responded"),
    ("Has data", isinstance(briefs, list) or isinstance(briefs, dict), f"type={type(briefs).__name__}"),
])
if isinstance(briefs, list) and briefs:
    b = briefs[0]
    print(f"  Title: {b.get('title')}")
    print(f"  Has executive_summary: {bool(b.get('executive_summary'))}")
    print(f"  Has key_campaigns: {bool(b.get('key_campaigns'))}")
    print(f"  Has key_vulnerabilities: {bool(b.get('key_vulnerabilities'))}")
    print(f"  Has key_actors: {bool(b.get('key_actors'))}")
    print(f"  Has recommendations: {bool(b.get('recommendations'))}")

# --- Test 9: Org Exposure ---
import urllib.parse
params = urllib.parse.urlencode({"sectors": "Technology,Finance", "regions": "North America", "tech_stack": "Apache,Windows"})
expo = get(f"/enrichment/org-exposure?{params}")
test("Org Exposure", expo, [
    ("Not error", "_error" not in expo, "endpoint responded"),
    ("Has exposure_score", "exposure_score" in expo if isinstance(expo, dict) else False,
     f"score={expo.get('exposure_score') if isinstance(expo, dict) else 'N/A'}"),
    ("Has stats", "stats" in expo if isinstance(expo, dict) else False,
     f"{expo.get('stats') if isinstance(expo, dict) else 'N/A'}"),
    ("Has targeting_campaigns", "targeting_campaigns" in expo if isinstance(expo, dict) else False,
     f"{len(expo.get('targeting_campaigns', [])) if isinstance(expo, dict) else 0} campaigns"),
    ("Has vulnerable_products", "vulnerable_products" in expo if isinstance(expo, dict) else False,
     f"{len(expo.get('vulnerable_products', [])) if isinstance(expo, dict) else 0} products"),
])

# --- Test 10: Intel Batch Enrichment ---
# Get some intel item IDs first
intel = get("/intel?limit=3")
if isinstance(intel, dict) and "items" in intel:
    ids = [i["id"] for i in intel["items"][:3] if "id" in i]
elif isinstance(intel, list):
    ids = [i["id"] for i in intel[:3] if "id" in i]
else:
    ids = []

if ids:
    id_params = "&".join(f"ids={i}" for i in ids)
    batch = get(f"/enrichment/intel-batch?{id_params}")
    test("Intel Batch Enrichment (badges)", batch, [
        ("Not error", "_error" not in batch, "endpoint responded"),
        ("Has data", isinstance(batch, dict) and len(batch) > 0, f"{len(batch) if isinstance(batch, dict) else 0} items enriched"),
    ])
    if isinstance(batch, dict):
        for item_id, enrichment in list(batch.items())[:2]:
            camps = enrichment.get("campaigns", [])
            actors = enrichment.get("actors", [])
            print(f"  ID {item_id[:8]}...: {len(camps)} campaigns (violet badges), {len(actors)} actors (red badges)")
else:
    print("\n  SKIP: No intel items to test batch enrichment")

print(f"\n{'='*60}")
print("ALL TESTS COMPLETE")
print(f"{'='*60}")
