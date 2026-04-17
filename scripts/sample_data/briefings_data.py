"""Sample ThreatBriefing seed data — three enriched briefings showing
multi-agent correlation across the news feed + IOC database.

Each entry is a plain dict mirroring the ThreatBriefing ORM columns
(period, title, executive_summary, key_campaigns, …). The seed script
fills in period_start / period_end relative to "now" so the timeline
always looks fresh.

Design notes
------------
- ``executive_summary`` is plain text with section headers; the UI
  renders it with ``whitespace-pre-wrap`` so newlines are preserved.
  Structure each summary so an executive can read the first three
  paragraphs and stop, while a technical reader gets the deep-dive
  underneath.
- ``raw_data`` carries structured "sections" + "key_findings" that
  the API returns on generation — we pre-populate them so the
  download-to-HTML/PDF export looks complete.
- IOCs and actor names are drawn from the live IntelPulse prod DB so
  the samples feel real and cross-link back into the IOC database /
  search pages.
"""

from __future__ import annotations


SAMPLE_BRIEFINGS: list[dict] = [
    # ──────────────────────────────────────────────────────────────
    # 1. Weekly — ransomware + infostealer infrastructure
    # ──────────────────────────────────────────────────────────────
    {
        "period": "weekly",
        "days_back": 7,
        "title": "Weekly Threat Brief — Ransomware & Infostealer Infrastructure",
        "executive_summary": (
            "EXECUTIVE OVERVIEW\n"
            "Over the past seven days IntelPulse correlated a surge in infostealer "
            "distribution infrastructure with renewed activity from two of the "
            "most financially-motivated ransomware affiliates in the ecosystem — "
            "Akira and BlackBasta. A cluster of 14 sinkhole-adjacent domains on "
            "the '.in.net' TLD (ryunt.in.net, xel7morax.in.net, rebutrew0rk.in.net, "
            "media-gate.in.net, plus 10 siblings) together received 112 sightings "
            "this week and fan out to three resolvers that also host the Akira "
            "leak-site mirrors. The same infrastructure was referenced by a Dark "
            "Reading piece ('Harmless Global Adware Transforms Into an AV Killer') "
            "where an adware family pivots to disabling EDR — confirming that the "
            "'loader-as-a-service' layer continues to be the choke point of "
            "enterprise compromise.\n\n"
            "BUSINESS RISK\n"
            "Initial access via infostealer credential theft now accounts for "
            "~71% of the ransomware incidents observed by our enrichment "
            "pipeline. Stolen session cookies bypass MFA, and the median dwell "
            "time from first credential capture to ransomware detonation "
            "contracted to 4.2 days. Organisations with SSO into SaaS (Okta, "
            "Azure AD, Snowflake) are disproportionately exposed because a "
            "single stolen token yields data across the entire tenant.\n\n"
            "TECHNICAL DEEP-DIVE\n"
            "• Infrastructure: The '.in.net' cluster resolves to 176.65.150.25, "
            "204.76.203.162, and 176.65.148.55 — all three IPs appear in 12-13 "
            "separate intel items this week, AS 200557 (UAB Host Baltic) and "
            "AS 209588 (Flyservers S.A.). Rotating subdomain pattern "
            "(<2-3 syllables>.in.net) suggests DGA with a ~24h TTL.\n"
            "• TTPs (MITRE ATT&CK): T1566.002 Phishing: Spearphishing Link → "
            "T1204.002 User Execution → T1055 Process Injection → T1003.001 "
            "LSASS Memory → T1021.001 RDP → T1486 Data Encrypted for Impact.\n"
            "• Payloads: Lumma Stealer and Redline both observed fetching "
            "second-stage cobaltstrike beacons from the cluster. SHA-256 "
            "samples cross-listed on VirusTotal with 38-54 engine hits.\n"
            "• Akira affiliates: 3 new victim posts on the leak site this week "
            "— manufacturing (US), legal services (UK), regional hospital group "
            "(NL). Negotiator persona 'Vatcraft' continues to dominate.\n\n"
            "MULTI-SOURCE CORRELATION\n"
            "News feed ↔ IOC database ↔ campaign tracker crosswalk for this "
            "briefing:\n"
            " • 4 news articles referenced infrastructure already tagged in the "
            "IOC database (auto-linked by the IOC Correlator agent).\n"
            " • 2 IOCs (176.65.150.25, xel7morax.in.net) appeared in both the "
            "Akira and BlackBasta campaign bundles — suggesting shared "
            "access-broker tenancy.\n"
            " • 7 Sigma detection rules were auto-synthesised by the Narrative "
            "Builder agent from the observed TTPs; all 7 are published under "
            "'Detection Rules → Auto-Generated'.\n\n"
            "RECOMMENDED ACTIONS — read with context in the Recommendations "
            "panel below."
        ),
        "key_campaigns": [
            {
                "campaign_name": "Akira Ransomware — Q2 Wave",
                "actor_name": "Akira",
                "severity": "critical",
                "targeted_sectors": ["manufacturing", "legal", "healthcare"],
                "description": (
                    "Triple-extortion campaign; leverages stolen SSO sessions "
                    "from Lumma/Redline infostealers. 3 new victims this week."
                ),
            },
            {
                "campaign_name": "BlackBasta Resurgence",
                "actor_name": "BlackBasta",
                "severity": "critical",
                "targeted_sectors": ["finance", "technology", "retail"],
                "description": (
                    "Re-emerged after a 6-week operational lull; now sharing "
                    "initial-access brokers with Akira affiliates."
                ),
            },
            {
                "campaign_name": "Lumma / Redline Loader Cluster",
                "actor_name": "Traffic Loader Syndicate",
                "severity": "high",
                "targeted_sectors": ["cross-sector"],
                "description": (
                    "14-domain '.in.net' DGA cluster delivering stealers via "
                    "fake-CAPTCHA and SEO-poisoned download pages."
                ),
            },
            {
                "campaign_name": "Adware-to-EDR-Killer Pivot",
                "actor_name": "Unattributed",
                "severity": "high",
                "targeted_sectors": ["consumer", "SMB"],
                "description": (
                    "Formerly benign adware family now disables Defender/EDR "
                    "via BYOVD, laying groundwork for ransomware."
                ),
            },
        ],
        "key_vulnerabilities": [
            {"cve_id": "CVE-2024-3400", "is_kev": True, "is_exploited": True,
             "cvss": 10.0, "product": "PAN-OS GlobalProtect"},
            {"cve_id": "CVE-2024-1709", "is_kev": True, "is_exploited": True,
             "cvss": 10.0, "product": "ConnectWise ScreenConnect"},
            {"cve_id": "CVE-2024-21887", "is_kev": True, "is_exploited": True,
             "cvss": 9.1, "product": "Ivanti Connect Secure"},
            {"cve_id": "CVE-2026-6494", "is_kev": False, "is_exploited": True,
             "cvss": 8.8, "product": "Observed in fresh intel this week"},
            {"cve_id": "CVE-2026-23778", "is_kev": False, "is_exploited": False,
             "cvss": 7.8, "product": "Observed in fresh intel this week"},
        ],
        "key_actors": [
            {"name": "Akira", "mentions": 11, "category": "ransomware",
             "origin": "Eastern Europe", "attribution": "medium-high"},
            {"name": "BlackBasta", "mentions": 8, "category": "ransomware",
             "origin": "Russia", "attribution": "high"},
            {"name": "Scattered Spider", "mentions": 5,
             "category": "access broker", "origin": "North America / UK",
             "attribution": "high"},
            {"name": "Traffic Loader Syndicate", "mentions": 14,
             "category": "initial access", "origin": "unknown",
             "attribution": "low"},
        ],
        "sector_threats": {
            "sectors": [
                {"name": "Manufacturing", "count": 23, "severity": "critical"},
                {"name": "Healthcare", "count": 18, "severity": "critical"},
                {"name": "Legal Services", "count": 11, "severity": "high"},
                {"name": "Finance", "count": 15, "severity": "high"},
                {"name": "SMB / Consumer", "count": 34, "severity": "medium"},
            ]
        },
        "stats": {
            "articles_processed": 412,
            "articles_enriched": 287,
            "iocs_correlated": 642,
            "campaigns_active": 7,
            "new_cves": 19,
            "ai_enrichment_coverage_pct": 69,
            "multi_agent_runs": 287,
        },
        "recommendations": [
            "Block the 14 '.in.net' loader domains and the 3 resolver IPs at "
            "the perimeter — they are pre-synced into the IOC database tagged "
            "'loader-cluster-q2'.",
            "Rotate SSO session cookies and enforce device-bound session "
            "tokens (WebAuthn, Okta FastPass) on any user flagged by the "
            "infostealer watchlist.",
            "Deploy the 7 auto-generated Sigma rules from /detections tagged "
            "'akira-2026-wave'; they cover T1003.001 (LSASS access) and "
            "T1486 (file-encryption primitives).",
            "Patch ConnectWise ScreenConnect (CVE-2024-1709) and Ivanti "
            "Connect Secure (CVE-2024-21887 / CVE-2023-46805) — both continue "
            "to appear as initial-access vectors for Akira affiliates.",
            "Run the 'Akira IOC Hunt' playbook in /search — prebuilt to "
            "query endpoint telemetry for the hash-256 list in this brief.",
        ],
        "raw_data_sections": [
            {
                "heading": "Executive Overview",
                "content": (
                    "Infostealer-to-ransomware pipeline remained the dominant "
                    "theme this week. Akira and BlackBasta both drew initial "
                    "access from a shared 14-domain loader cluster — meaning "
                    "a single blocklist push materially reduces exposure to "
                    "two of the three most prolific RaaS brands."
                ),
            },
            {
                "heading": "Technical Deep-Dive",
                "content": (
                    "Kill-chain: infostealer → session cookie theft → SSO "
                    "replay → SaaS data exfil → on-prem pivot via "
                    "ScreenConnect / Ivanti → Cobalt Strike beacon → LSASS "
                    "dump → Akira encryption. Median dwell 4.2 days. Primary "
                    "ATT&CK IDs: T1566.002, T1204.002, T1055, T1003.001, "
                    "T1021.001, T1486."
                ),
            },
            {
                "heading": "IOC / News Correlation",
                "content": (
                    "4 news articles this week referenced infrastructure "
                    "already tagged in the IOC DB (auto-linked by the "
                    "multi-agent IOC Correlator). Two IOCs — 176.65.150.25 "
                    "and xel7morax.in.net — appeared in BOTH the Akira and "
                    "BlackBasta campaign bundles."
                ),
            },
        ],
        "raw_data_findings": [
            "14-domain '.in.net' loader cluster shared between Akira and "
            "BlackBasta — single blocklist covers both.",
            "Median infostealer-to-ransomware dwell time has compressed to "
            "4.2 days (down from 6.1 last month).",
            "7 Sigma detection rules auto-synthesised from this week's "
            "observed TTPs are live in /detections.",
            "Adware-to-EDR-killer pivot observed in the wild — BYOVD driver "
            "abuse is becoming the 'unlock' for ransomware deployment.",
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # 2. Weekly — nation-state + critical infrastructure
    # ──────────────────────────────────────────────────────────────
    {
        "period": "weekly",
        "days_back": 7,
        "title": "Weekly Threat Brief — Nation-State Espionage & Critical Infrastructure",
        "executive_summary": (
            "EXECUTIVE OVERVIEW\n"
            "State-aligned activity dominated our feed this week, led by "
            "Russian (APT28 Forest Blizzard, APT29 Midnight Blizzard, APT44 "
            "Sandworm), Chinese (BRICKSTORM operators) and North Korean "
            "(Contagious Interview / UNC1069) operators. IntelPulse correlated "
            "three separate news sources covering the ZionSiphon malware "
            "targeting water-treatment SCADA with seven IOCs the IOC Correlator "
            "agent has also seen in earlier Volt Typhoon ('living-off-the-land' "
            "at US utilities) telemetry. The U.S. Department of Justice also "
            "sentenced two U.S. nationals this week for assisting North "
            "Korea's laptop-farm IT-worker scheme — the employment-fraud "
            "vector has matured from tradecraft curiosity to a structural "
            "insider threat for any company hiring remote engineers.\n\n"
            "BUSINESS RISK\n"
            "Water, energy and telecom operators remain the top targets for "
            "long-dwell state-level access operations. For enterprise buyers "
            "of managed SCADA services, the supply chain IS the attack surface "
            "— Volt Typhoon's 2023-2025 campaign taught us that adversaries "
            "pre-position in utility networks for contingency disruption, not "
            "immediate extortion. Any organisation that has onboarded a "
            "remote engineer in the last 18 months should review whether the "
            "interview, device-shipment, and paycheck-routing chain could "
            "conceal a DPRK IT-worker placement.\n\n"
            "TECHNICAL DEEP-DIVE\n"
            "• ZionSiphon (news correlation): Payload designed to manipulate "
            "hydraulic pressure + chlorine dosing on Schneider Modicon PLCs. "
            "Currently dormant due to a flawed encryption routine, but the "
            "framework is production-grade. TTPs: T0807 Command-Line "
            "Interface, T0855 Unauthorized Command Message, T0836 Modify "
            "Parameter.\n"
            "• BRICKSTORM (China): Go-based backdoor, signed with stolen "
            "certs, targets VMware ESXi and network appliances. Observed in "
            "3 articles this week pivoting from appliance → vCenter → domain "
            "controller.\n"
            "• APT28 / APT29 infrastructure overlap: The Correlator agent "
            "identified shared hosting (Hetzner AS 24940) between two "
            "phishing domains this week and the historical 2024 SolarWinds "
            "cluster — not attribution, but a tenancy overlap worth hunting.\n"
            "• DPRK IT-worker scheme: Laptop-farms route earnings through US "
            "shell LLCs; recruitment uses stolen US identities + deepfake "
            "interview audio.\n\n"
            "MULTI-SOURCE CORRELATION\n"
            " • 6 news stories this week mapped to the 'critical-infrastructure' "
            "category by the Classifier agent.\n"
            " • 22 IOCs shared between this week's ZionSiphon reporting and "
            "the 2024 Volt Typhoon dataset already in the IOC DB.\n"
            " • 1 DPRK-linked GitHub-namespace IOC ('Contagious Interview' "
            "npm packages) cross-referenced against /intel → 4 enterprise "
            "customers observed pulls in the last 30 days.\n\n"
            "RECOMMENDED ACTIONS — see the Recommendations panel below."
        ),
        "key_campaigns": [
            {
                "campaign_name": "ZionSiphon — Water Utility Targeting",
                "actor_name": "Unattributed (CyberAv3ngers overlap)",
                "severity": "critical",
                "targeted_sectors": ["water", "utilities", "government"],
                "description": (
                    "SCADA-aware malware for Schneider Modicon PLCs — "
                    "dormant due to a crypto flaw, but framework is "
                    "weaponisable."
                ),
            },
            {
                "campaign_name": "Volt Typhoon — Long-Dwell Utility Access",
                "actor_name": "Volt Typhoon",
                "severity": "critical",
                "targeted_sectors": ["energy", "water", "telecom", "transportation"],
                "description": (
                    "Living-off-the-land persistence at US/EU utilities; "
                    "22 IOCs shared with this week's ZionSiphon reporting."
                ),
            },
            {
                "campaign_name": "Midnight Blizzard — Cloud Identity Attacks",
                "actor_name": "APT29 (Cozy Bear / Midnight Blizzard)",
                "severity": "high",
                "targeted_sectors": ["technology", "government", "think-tanks"],
                "description": (
                    "OAuth consent phishing + service-principal abuse; "
                    "continues to target M365 tenants via device-code flow."
                ),
            },
            {
                "campaign_name": "Contagious Interview — DPRK IT-Worker Scheme",
                "actor_name": "Contagious Interview (UNC1069 / BlueNoroff)",
                "severity": "high",
                "targeted_sectors": ["technology", "crypto", "finance"],
                "description": (
                    "DPRK operatives impersonate remote SWEs; malicious npm "
                    "packages + deepfake interviews; laptop-farm payroll laundering."
                ),
            },
            {
                "campaign_name": "BRICKSTORM — Appliance-to-Hypervisor Pivot",
                "actor_name": "Chinese state-aligned",
                "severity": "critical",
                "targeted_sectors": ["government", "defense", "telecom"],
                "description": (
                    "Go backdoor on VMware/ESXi and network appliances; "
                    "stolen code-signing certs; stealthy hypervisor pivot."
                ),
            },
        ],
        "key_vulnerabilities": [
            {"cve_id": "CVE-2024-3400", "is_kev": True, "is_exploited": True,
             "cvss": 10.0, "product": "PAN-OS GlobalProtect"},
            {"cve_id": "CVE-2024-21887", "is_kev": True, "is_exploited": True,
             "cvss": 9.1, "product": "Ivanti Connect Secure"},
            {"cve_id": "CVE-2023-46805", "is_kev": True, "is_exploited": True,
             "cvss": 8.2, "product": "Ivanti Connect Secure (auth bypass)"},
            {"cve_id": "CVE-2024-20353", "is_kev": True, "is_exploited": True,
             "cvss": 8.6, "product": "Cisco ASA / FTD"},
            {"cve_id": "CVE-2026-40002", "is_kev": False, "is_exploited": True,
             "cvss": 8.1, "product": "SCADA HMI, observed in intel this week"},
        ],
        "key_actors": [
            {"name": "Volt Typhoon", "mentions": 9, "category": "nation-state",
             "origin": "China (PRC)", "attribution": "high"},
            {"name": "APT29 (Cozy Bear / Midnight Blizzard)", "mentions": 7,
             "category": "nation-state", "origin": "Russia (SVR)",
             "attribution": "high"},
            {"name": "APT28 (Forest Blizzard)", "mentions": 6,
             "category": "nation-state", "origin": "Russia (GRU)",
             "attribution": "high"},
            {"name": "APT44 (Sandworm)", "mentions": 4,
             "category": "nation-state", "origin": "Russia (GRU Unit 74455)",
             "attribution": "high"},
            {"name": "Contagious Interview (UNC1069 / BlueNoroff)",
             "mentions": 5, "category": "nation-state",
             "origin": "North Korea (Lazarus subgroup)", "attribution": "high"},
            {"name": "BRICKSTORM", "mentions": 3, "category": "nation-state",
             "origin": "China", "attribution": "medium-high"},
        ],
        "sector_threats": {
            "sectors": [
                {"name": "Energy / Utilities", "count": 31, "severity": "critical"},
                {"name": "Water", "count": 12, "severity": "critical"},
                {"name": "Government", "count": 24, "severity": "high"},
                {"name": "Defense", "count": 17, "severity": "high"},
                {"name": "Technology", "count": 28, "severity": "high"},
                {"name": "Telecom", "count": 19, "severity": "high"},
            ]
        },
        "stats": {
            "articles_processed": 398,
            "articles_enriched": 263,
            "iocs_correlated": 541,
            "campaigns_active": 9,
            "new_cves": 14,
            "nation_state_stories": 37,
            "ai_enrichment_coverage_pct": 66,
            "multi_agent_runs": 263,
        },
        "recommendations": [
            "Treat every remote-engineering hire in the last 18 months as in-scope "
            "for a DPRK IT-worker review — verify laptop-shipment address vs. "
            "tax/bank records and run identity attestation on code-signing certs.",
            "Sinkhole or block the 22 IOCs shared between ZionSiphon and the "
            "historical Volt Typhoon dataset — they are tagged "
            "'critical-infra-prepo' in the IOC database and safe to block in "
            "utility-sector networks.",
            "Patch the Ivanti Connect Secure + Cisco ASA appliances in your "
            "edge — CVE-2024-21887 / CVE-2023-46805 / CVE-2024-20353 are all "
            "actively used in nation-state initial access.",
            "Audit device-code and OAuth consent grants in M365 / Azure AD "
            "tenants for the APT29 phishing pattern; revoke any legacy app "
            "consent older than 12 months.",
            "Hunt for the BRICKSTORM indicators on VMware ESXi (stolen-cert "
            "signed Go binaries in /tmp or /var) — playbook available via "
            "/search → 'BRICKSTORM hunt'.",
        ],
        "raw_data_sections": [
            {
                "heading": "Executive Overview",
                "content": (
                    "Nation-state tempo held steady but the targeting shifted "
                    "toward operational-technology and identity — ZionSiphon "
                    "at water utilities, APT29 at M365 tenants, and a DPRK "
                    "employment-fraud pipeline that turns every remote hire "
                    "into a due-diligence item."
                ),
            },
            {
                "heading": "Technical Deep-Dive",
                "content": (
                    "ZionSiphon manipulates Schneider Modicon PLC parameters "
                    "(T0836). BRICKSTORM backdoor pivots appliance→ESXi→DC. "
                    "APT29 continues device-code + consent phishing. DPRK "
                    "IT-worker scheme uses laptop-farms + deepfake interviews."
                ),
            },
            {
                "heading": "IOC / News Correlation",
                "content": (
                    "22 IOCs from this week's ZionSiphon coverage already "
                    "existed in the IOC DB tagged to the 2024 Volt Typhoon "
                    "cluster. 1 DPRK-linked npm namespace was pulled by 4 "
                    "enterprise customers in the last 30 days."
                ),
            },
        ],
        "raw_data_findings": [
            "State-aligned activity across Russia, China, DPRK all visible in "
            "a single week — each with distinct access vectors and dwell "
            "objectives.",
            "Water / utilities targeting is no longer theoretical; ZionSiphon "
            "is a production SCADA framework kept offline only by a crypto bug.",
            "Remote-hire process is now a credible nation-state risk surface.",
            "M365 device-code and consent-phishing remain APT29's lowest-friction "
            "entry point.",
        ],
    },

    # ──────────────────────────────────────────────────────────────
    # 3. Daily — zero-day watch + emergent exploits
    # ──────────────────────────────────────────────────────────────
    {
        "period": "daily",
        "days_back": 1,
        "title": "Daily Threat Brief — Zero-Day Watch & Emergent Exploits",
        "executive_summary": (
            "EXECUTIVE OVERVIEW\n"
            "Today's feed is dominated by a newly published zero-day PoC for "
            "Microsoft Defender ('RedSun' / CVE-2026-33825) that grants "
            "SYSTEM privileges on Windows 10/11 and Windows Server through a "
            "local privilege-escalation flaw in the endpoint-protection "
            "driver. Separately, Unit 42 documented a renewed Mirai-variant "
            "exploitation wave against end-of-life TP-Link routers "
            "(CVE-2023-33538) — the routers themselves are beyond patching, "
            "so the mitigation is replacement or network isolation. On the "
            "disruption side, Europol's Operation PowerOFF identified 75,000 "
            "DDoS-for-hire customers and took down 53 booter domains, "
            "including one that appeared in our IOC database 11 times over "
            "the last 90 days.\n\n"
            "BUSINESS RISK\n"
            "RedSun is the bigger immediate exposure for enterprise: a "
            "working PoC for an EDR-killer on Windows means the next "
            "ransomware deployment that chains through a stolen SSO token "
            "will probably ship RedSun as the 'pre-encryption' step. Any "
            "endpoint where Defender is the primary EDR should be considered "
            "degraded until the patch lands. For consumer-grade networks "
            "(remote workers, branch offices, IoT), the TP-Link activity is "
            "a reminder that EoL hardware is a live initial-access vector.\n\n"
            "TECHNICAL DEEP-DIVE\n"
            "• CVE-2026-33825 'RedSun': LPE via IOCTL handler in the "
            "MpKslDrv.sys mini-filter driver. PoC author 'Chaotic Eclipse' "
            "published working code on X + GitHub. Exploitation requires a "
            "local low-priv account (common post-phish). Patch not yet "
            "available — Microsoft advisory is in draft status.\n"
            "• CVE-2023-33538 (TP-Link): RCE through the parental-controls "
            "CGI handler. Default creds + internet-exposed admin panel "
            "combine to make 10,000+ routers trivially owned. Mirai "
            "variant 'GorillaBot' wraps the exploit with lateral-movement "
            "and DDoS payload.\n"
            "• Foxit Reader + LibRaw: Cisco Talos disclosed 7 memory-corruption "
            "CVEs — low individual impact but LibRaw ships in camera-vendor "
            "tooling used in creative/journalism workflows.\n"
            "• Operation PowerOFF: 53 domains seized, 4 individuals arrested. "
            "75,000 customer records will drive follow-on abuse-referral "
            "traffic. One seized domain (media-gate.in.net) has 11 sightings "
            "in our IOC database — see IOC Correlation below.\n\n"
            "MULTI-SOURCE CORRELATION\n"
            " • The RedSun PoC author 'Chaotic Eclipse' appears in 2 news "
            "stories today and shares handle-reuse with an earlier 'Harmless "
            "Global Adware → AV Killer' Dark Reading attribution.\n"
            " • media-gate.in.net (Operation PowerOFF takedown) is already "
            "in the IOC DB with 11 sightings and crosslinks to the same "
            "Akira loader cluster covered in this week's RaaS briefing.\n"
            " • Mirai+TP-Link telemetry shares 3 C2 IPs (AS 209588) with "
            "earlier Gafgyt activity — one botnet operator evolving the "
            "tooling rather than a new group.\n\n"
            "RECOMMENDED ACTIONS — see the Recommendations panel below."
        ),
        "key_campaigns": [
            {
                "campaign_name": "RedSun — Defender LPE Zero-Day",
                "actor_name": "Chaotic Eclipse (PoC author)",
                "severity": "critical",
                "targeted_sectors": ["cross-sector"],
                "description": (
                    "Public PoC for CVE-2026-33825 grants SYSTEM via IOCTL "
                    "bug in Defender's MpKslDrv.sys. No patch yet."
                ),
            },
            {
                "campaign_name": "GorillaBot — TP-Link Mirai Variant",
                "actor_name": "Mirai ecosystem operator",
                "severity": "high",
                "targeted_sectors": ["telecom", "SMB", "consumer"],
                "description": (
                    "Active exploitation of CVE-2023-33538 on EoL TP-Link "
                    "routers. Mitigation is replacement, not patch."
                ),
            },
            {
                "campaign_name": "Operation PowerOFF — DDoS-for-Hire Takedown",
                "actor_name": "Europol coalition (defender)",
                "severity": "low",
                "targeted_sectors": ["booter-customers"],
                "description": (
                    "53 domains seized, 4 arrests, 75k customer records; "
                    "one seized domain crosslinks to our Akira loader cluster."
                ),
            },
            {
                "campaign_name": "Foxit + LibRaw Memory Corruption Wave",
                "actor_name": "Unattributed",
                "severity": "medium",
                "targeted_sectors": ["media", "journalism", "creative"],
                "description": (
                    "7 Talos-disclosed CVEs in document + RAW-image tooling; "
                    "weaponisation likely via phishing attachments."
                ),
            },
        ],
        "key_vulnerabilities": [
            {"cve_id": "CVE-2026-33825", "is_kev": False, "is_exploited": False,
             "cvss": 7.8, "product": "Microsoft Defender (RedSun LPE)"},
            {"cve_id": "CVE-2023-33538", "is_kev": True, "is_exploited": True,
             "cvss": 8.8, "product": "TP-Link (EoL, Mirai variant)"},
            {"cve_id": "CVE-2026-6494", "is_kev": False, "is_exploited": True,
             "cvss": 8.8, "product": "Observed in today's feed"},
            {"cve_id": "CVE-2026-23778", "is_kev": False, "is_exploited": False,
             "cvss": 7.8, "product": "Foxit Reader memory corruption"},
            {"cve_id": "CVE-2026-23775", "is_kev": False, "is_exploited": False,
             "cvss": 7.1, "product": "LibRaw memory corruption"},
            {"cve_id": "CVE-2026-6441", "is_kev": False, "is_exploited": False,
             "cvss": 6.5, "product": "Foxit Reader secondary"},
        ],
        "key_actors": [
            {"name": "Chaotic Eclipse", "mentions": 3,
             "category": "PoC author / researcher", "origin": "unknown",
             "attribution": "low"},
            {"name": "Mirai ecosystem operator", "mentions": 2,
             "category": "botnet", "origin": "distributed",
             "attribution": "low"},
            {"name": "Europol coalition", "mentions": 4,
             "category": "defender (LE)", "origin": "EU",
             "attribution": "high"},
            {"name": "Akira (indirect crosslink)", "mentions": 1,
             "category": "ransomware", "origin": "Eastern Europe",
             "attribution": "medium"},
        ],
        "sector_threats": {
            "sectors": [
                {"name": "Cross-Sector (Defender users)", "count": 56, "severity": "critical"},
                {"name": "SMB / Consumer", "count": 22, "severity": "high"},
                {"name": "Telecom", "count": 9, "severity": "high"},
                {"name": "Media / Journalism", "count": 4, "severity": "medium"},
            ]
        },
        "stats": {
            "articles_processed": 68,
            "articles_enriched": 47,
            "iocs_correlated": 112,
            "campaigns_active": 4,
            "new_cves": 8,
            "zero_day_mentions": 3,
            "ai_enrichment_coverage_pct": 69,
            "multi_agent_runs": 47,
        },
        "recommendations": [
            "Flag Microsoft Defender-only endpoints as 'degraded EDR' until "
            "the RedSun patch ships; compensate by tightening application "
            "allow-listing and requiring admin-approval for new drivers.",
            "Retire or segment EoL TP-Link routers exposed to the internet — "
            "patch is not available. Replace or air-gap with firewall ACL.",
            "Block the 53 seized DDoS-booter domains from Operation PowerOFF; "
            "they are already tagged 'booter-takedown-2026-04' in the IOC DB.",
            "Monitor for the 'Chaotic Eclipse' PoC exploitation pattern: "
            "MpKslDrv.sys IOCTL sequence preceded by a low-priv shell — "
            "Sigma rule 'defender-redsun-lpe' is live in /detections.",
            "Treat Foxit Reader + LibRaw CVEs as routine patch-Tuesday; "
            "prioritise endpoints in media/creative teams where RAW-processing "
            "tooling is a daily workflow.",
        ],
        "raw_data_sections": [
            {
                "heading": "Executive Overview",
                "content": (
                    "A working PoC for a Defender LPE (RedSun / CVE-2026-33825) "
                    "is the most important item today — it is the missing "
                    "piece between a stolen SSO session and a full "
                    "ransomware deployment on a Defender-only endpoint."
                ),
            },
            {
                "heading": "Technical Deep-Dive",
                "content": (
                    "RedSun: IOCTL bug in MpKslDrv.sys mini-filter driver. "
                    "TP-Link: CGI RCE in parental controls on EoL hardware. "
                    "Foxit / LibRaw: memory corruption in document + RAW "
                    "parsers. Operation PowerOFF: 53 domains seized, 4 "
                    "arrests, and one domain crosslinked to the Akira "
                    "loader cluster."
                ),
            },
            {
                "heading": "IOC / News Correlation",
                "content": (
                    "media-gate.in.net (seized today) already sat in the IOC "
                    "DB with 11 sightings — the IOC Correlator agent surfaced "
                    "the crosslink automatically. PoC-author handle reuse "
                    "('Chaotic Eclipse') ties today's RedSun article to "
                    "earlier adware-to-EDR-killer reporting."
                ),
            },
        ],
        "raw_data_findings": [
            "RedSun PoC materially closes the gap between initial access "
            "and ransomware deployment on Defender-only estates.",
            "One Operation-PowerOFF seized domain is already a known "
            "Akira loader node — law-enforcement action partially blunts "
            "ransomware initial access as a side-effect.",
            "EoL TP-Link hardware remains a major consumer / SMB attack "
            "surface that patching will not fix.",
            "Chaotic Eclipse handle reuse suggests a single actor publishing "
            "both research and loader-tooling, worth watching for future TTPs.",
        ],
    },
]


__all__ = ["SAMPLE_BRIEFINGS"]
