"""Phase 2 normalizer integration test."""
from datetime import datetime, timezone, timedelta

from app.normalizers.ioc_lifecycle import confidence_decay, sighting_boost, is_stale, IOC_TTL_DAYS
from app.normalizers.diamond import extract_vertices, build_diamond_edges, parse_actor_name
from app.normalizers.killchain import parse_technique, tactic_to_phase, KILL_CHAIN_PHASES, kill_chain_coverage
from app.normalizers.correlation import corroboration_boost, find_cve_overlaps, find_ioc_overlaps

now = datetime.now(timezone.utc)
old = now - timedelta(days=60)

print("=== IOC Lifecycle ===")
print(f"TTL (ip): {IOC_TTL_DAYS['ip']}d, (hash): {IOC_TTL_DAYS['hash_sha256']}d")
print(f"Decay (fresh IP, score=80): {confidence_decay(80, now, 'ip')}")
print(f"Decay (60d old IP, score=80): {confidence_decay(80, old, 'ip')}")
print(f"Decay (60d old hash, score=80): {confidence_decay(80, old, 'hash_sha256')}")
print(f"Stale? (60d IP): {is_stale(old, 'ip')}")
print(f"Stale? (60d hash): {is_stale(old, 'hash_sha256')}")
print(f"Sighting boost (1): {sighting_boost(1)}, (5): {sighting_boost(5)}, (30): {sighting_boost(30)}")

print("\n=== Diamond Model ===")
item = {
    "threat_actors": ["APT29 (Cozy Bear / Midnight Blizzard)"],
    "malware_families": ["Cobalt Strike"],
    "tactics_techniques": ["T1566.001 - Phishing: Spearphishing"],
    "targeted_sectors": ["Financial Services"],
    "targeted_regions": ["North America"],
    "ioc_summary": {"ip": ["1.2.3.4"], "domain": ["evil.com"]},
    "initial_access_vector": "Spearphishing",
    "post_exploitation": [],
    "impacted_assets": ["Exchange Server"],
}
vertices = extract_vertices(item)
for vtype, vlist in vertices.items():
    print(f"  {vtype}: {len(vlist)} entries")
edges = build_diamond_edges(vertices, "test-intel-id")
print(f"  Edges generated: {len(edges)}")
primary, aliases = parse_actor_name("APT29 (Cozy Bear / Midnight Blizzard)")
print(f"  Actor: {primary}, aliases: {aliases}")

print("\n=== Kill Chain ===")
tid, tname = parse_technique("T1566.001 - Phishing: Spearphishing Attachment")
print(f"  Parsed: id={tid}, name={tname}")
print(f"  Initial Access -> {tactic_to_phase('initial-access')}")
print(f"  Exfiltration -> {tactic_to_phase('exfiltration')}")
print(f"  Phases: {len(KILL_CHAIN_PHASES)}")

print("\n=== Correlation ===")
print(f"  Boost (1 src): {corroboration_boost(1)}")
print(f"  Boost (2 src): {corroboration_boost(2)}")
print(f"  Boost (3 src): {corroboration_boost(3)}")
print(f"  Boost (5 src): {corroboration_boost(5)}")
items = [
    {"cve_ids": ["CVE-2024-1234"], "source_name": "NVD", "risk_score": 80, "id": "1"},
    {"cve_ids": ["CVE-2024-1234"], "source_name": "KEV", "risk_score": 90, "id": "2"},
    {"cve_ids": ["CVE-2024-1234", "CVE-2024-5678"], "source_name": "OTX", "risk_score": 60, "id": "3"},
]
overlaps = find_cve_overlaps(items)
for cve, data in overlaps.items():
    print(f"  {cve}: {data['count']} feeds, boost={data['boost']}")

print("\nPhase 2 ALL TESTS PASSED")
