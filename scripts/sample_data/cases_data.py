"""Rich sample cases used by `scripts/seed_sample_data.py`.

Each entry represents a realistic SOC / IR workflow scenario, including:
  - Case metadata (type, priority, severity, TLP, tags)
  - Linked items (intel, IOCs, techniques) with descriptive metadata
  - Timeline of activities (status changes, comments, artefact additions)

The data is intentionally self-contained — IDs for linked items are free-form
strings because in a live system these would point to real rows; the seed
script stores them as-is so they remain navigable in the UI even against a
fresh DB with no upstream intel/IOC records.
"""

from __future__ import annotations


# ─── Case scenarios ─────────────────────────────────────────
#
# Order controls created_at offset (newest first). Each case spans a
# different scenario so the UI demo exercises filters (type, status,
# priority, severity, TLP) without duplicates.

SAMPLE_CASES: list[dict] = [
    # 1. Active critical IR — currently in progress
    {
        "title": "IR-2026-041: Volt Typhoon Living-off-the-Land Campaign",
        "description": (
            "Detected anomalous PowerShell activity on three domain controllers consistent "
            "with Volt Typhoon TTPs — credential dumping via `ntdsutil`, WMI lateral "
            "movement, and proxy pivoting through a compromised SOHO device. "
            "CISA AA24-038A advisory indicators matched on DC01 (hostname: NYC-DC01) at "
            "03:17 UTC. Investigation is live; containment in progress."
        ),
        "case_type": "incident_response",
        "status": "in_progress",
        "priority": "critical",
        "severity": "critical",
        "tlp": "TLP:AMBER+STRICT",
        "tags": ["volt-typhoon", "apt", "china", "living-off-the-land", "critical-infra"],
        "items": [
            {
                "item_type": "intel",
                "item_id": "cve-2024-3400",
                "item_title": "CVE-2024-3400 — Palo Alto GlobalProtect command injection",
                "item_metadata": {
                    "severity": "critical", "cvss": 10.0, "kev": True,
                    "source": "NVD", "feed": "nvd",
                },
                "notes": "Likely initial access vector — firewall logs show pattern match.",
            },
            {
                "item_type": "ioc",
                "item_id": "45.77.156.23",
                "item_title": "Suspected C2 IP — Vultr VPS",
                "item_metadata": {
                    "ioc_type": "ip", "asn": "AS20473", "country": "US",
                    "confidence": 85, "first_seen": "2026-02-28T09:15:00Z",
                },
                "notes": "Observed in outbound connections from DC01 on port 443.",
            },
            {
                "item_type": "ioc",
                "item_id": "d4f5b6c7e8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5",
                "item_title": "SHA256 of suspicious ntdsutil-wrapper.ps1",
                "item_metadata": {
                    "ioc_type": "hash_sha256", "confidence": 95,
                    "filename": "ntdsutil-wrapper.ps1", "size_bytes": 48204,
                },
                "notes": "Wraps ntdsutil IFM export — classic DCSync precursor.",
            },
            {
                "item_type": "technique",
                "item_id": "T1003.003",
                "item_title": "OS Credential Dumping: NTDS",
                "item_metadata": {"tactic": "credential-access", "confidence": 90},
                "notes": "Dumped NTDS.dit via `ntdsutil IFM create full` on DC01.",
            },
            {
                "item_type": "technique",
                "item_id": "T1021.006",
                "item_title": "Remote Services: Windows Remote Management",
                "item_metadata": {"tactic": "lateral-movement", "confidence": 75},
                "notes": "WinRM logons from NYC-DC01 to two file servers.",
            },
            {
                "item_type": "technique",
                "item_id": "T1090.003",
                "item_title": "Proxy: Multi-hop Proxy",
                "item_metadata": {"tactic": "command-and-control", "confidence": 80},
                "notes": "Traffic to C2 routed through compromised ASUS router (ISP: Comcast).",
            },
        ],
        "activities": [
            {"action": "created", "detail": "Case opened from SOC alert SOC-2026-00891 (EDR: Volt Typhoon behavioural signature match)"},
            {"action": "assigned", "detail": "Assigned to @tier3-ir (lead: Priya K.)"},
            {"action": "item_added", "detail": "Linked CVE-2024-3400 as suspected initial access vector"},
            {"action": "updated", "detail": "priority: high → critical (CISA advisory match confirmed)"},
            {"action": "comment", "detail": "Isolated DC01 and DC02 from production VLAN at 06:42 UTC. DC03 shows no IOCs yet; leaving online under heightened monitoring. — @priyak"},
            {"action": "item_added", "detail": "Added SHA256 of ntdsutil-wrapper.ps1"},
            {"action": "comment", "detail": "Mandiant IR retainer activated. ETA 4h for onsite team. — @cisoteam"},
            {"action": "updated", "detail": "status: new → in_progress"},
            {"action": "comment", "detail": "Containment milestone: credential rotation started for all tier-0 accounts. Expected completion 18:00 UTC. — @idm-lead"},
        ],
    },

    # 2. Ransomware post-mortem — resolved
    {
        "title": "IR-2026-033: Akira Ransomware — Citrix NetScaler Compromise",
        "description": (
            "Akira ransomware operators exploited CVE-2023-3519 on externally-facing "
            "NetScaler appliance (edge-02), established persistence, exfiltrated ~12GB "
            "of HR and finance data over 9 days, then encrypted 47 file servers. "
            "Decryptor obtained via backup restore; no ransom paid. This is the "
            "full post-mortem case used to drive the 90-day hardening plan."
        ),
        "case_type": "incident_response",
        "status": "resolved",
        "priority": "critical",
        "severity": "critical",
        "tlp": "TLP:AMBER",
        "tags": ["ransomware", "akira", "cve-2023-3519", "netscaler", "post-mortem"],
        "items": [
            {
                "item_type": "intel",
                "item_id": "cve-2023-3519",
                "item_title": "CVE-2023-3519 — Citrix ADC/Gateway unauth RCE",
                "item_metadata": {"severity": "critical", "cvss": 9.8, "kev": True},
                "notes": "Root cause — unpatched appliance ran version 13.1-48.47.",
            },
            {
                "item_type": "ioc",
                "item_id": "185.220.101.42",
                "item_title": "Akira C2 — Tor exit node",
                "item_metadata": {"ioc_type": "ip", "confidence": 95, "tags": ["akira", "c2"]},
            },
            {
                "item_type": "ioc",
                "item_id": "akira-decryptor-v2.exe",
                "item_title": "Akira decryptor sample recovered from netscaler",
                "item_metadata": {
                    "ioc_type": "file", "confidence": 100,
                    "sha256": "8a54fc3b2f7d0c1e8e9a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e",
                },
            },
            {
                "item_type": "technique",
                "item_id": "T1190",
                "item_title": "Exploit Public-Facing Application",
                "item_metadata": {"tactic": "initial-access", "confidence": 100},
            },
            {
                "item_type": "technique",
                "item_id": "T1486",
                "item_title": "Data Encrypted for Impact",
                "item_metadata": {"tactic": "impact", "confidence": 100},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Opened after Veeam ransomware canary alert fired on FS-NY-07"},
            {"action": "updated", "detail": "status: new → in_progress; priority: high → critical"},
            {"action": "comment", "detail": "47 file servers confirmed encrypted. Rebuild from immutable backups commencing. — @ir-lead"},
            {"action": "comment", "detail": "Law enforcement notification filed (FBI IC3: I-2026-03-081234)"},
            {"action": "comment", "detail": "Coveware engaged for negotiation posture — recommendation: do not pay. Backups are clean at T-14d."},
            {"action": "item_added", "detail": "Linked decryptor binary recovered during forensic imaging"},
            {"action": "updated", "detail": "status: in_progress → resolved"},
            {"action": "comment", "detail": "All systems restored. Hardening roadmap opened as CASE IR-2026-034."},
        ],
    },

    # 3. Threat hunt — pending
    {
        "title": "HUNT-2026-012: Proactive Hunt for MITRE T1098.001 Additional Cloud Credentials",
        "description": (
            "Proactive hunt across AWS, Azure, and GCP tenants for anomalous creation of "
            "IAM access keys, service principals, and managed identities following the "
            "Snowflake-adjacent breach patterns from Q4 2025. Hunt covers the last 30 "
            "days of CloudTrail, Azure AD AuditLogs, and GCP Audit Logs. Six "
            "candidate findings documented; awaiting owner confirmation to rule out "
            "legitimate change."
        ),
        "case_type": "hunt",
        "status": "pending",
        "priority": "medium",
        "severity": "medium",
        "tlp": "TLP:GREEN",
        "tags": ["threat-hunt", "cloud", "aws", "azure", "iam", "snowflake-lessons"],
        "items": [
            {
                "item_type": "technique",
                "item_id": "T1098.001",
                "item_title": "Account Manipulation: Additional Cloud Credentials",
                "item_metadata": {"tactic": "persistence"},
            },
            {
                "item_type": "technique",
                "item_id": "T1078.004",
                "item_title": "Valid Accounts: Cloud Accounts",
                "item_metadata": {"tactic": "defense-evasion"},
            },
            {
                "item_type": "intel",
                "item_id": "news-snowflake-breach-lessons-2026",
                "item_title": "Post-Snowflake Breach: Cloud Credential Abuse Patterns",
                "item_metadata": {"source": "internal-research", "severity": "medium"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Hunt initiated per Q1 2026 threat hunt calendar"},
            {"action": "assigned", "detail": "Lead hunter: @mariod (cloud-sec team)"},
            {"action": "comment", "detail": "Hunt query scope: CreateAccessKey, ServicePrincipalCreate, iam.serviceAccountKeys.create (30-day window)"},
            {"action": "comment", "detail": "Initial pass: 6 candidates requiring owner confirmation. Detailed findings in hunt-notebook. — @mariod"},
            {"action": "updated", "detail": "status: in_progress → pending (awaiting owner responses)"},
        ],
    },

    # 4. Phishing investigation — closed
    {
        "title": "INV-2026-027: Spear-phishing Campaign Targeting Finance Approvers",
        "description": (
            "Multi-stage spear-phishing campaign targeting 14 finance approvers "
            "using spoofed vendor invoices. Two users clicked; EDR isolated both "
            "endpoints within 11 minutes. No credential compromise or lateral "
            "movement. Campaign attributed to FIN7-adjacent actor based on "
            "shared infrastructure with Symphonic's May 2026 report. Case "
            "closed with awareness training rolled out to targeted users."
        ),
        "case_type": "investigation",
        "status": "closed",
        "priority": "high",
        "severity": "high",
        "tlp": "TLP:AMBER",
        "tags": ["phishing", "fin7", "bec", "finance", "training-driven"],
        "items": [
            {
                "item_type": "ioc",
                "item_id": "invoicing-partners-llc[.]com",
                "item_title": "Phishing domain (homoglyph)",
                "item_metadata": {"ioc_type": "domain", "confidence": 95, "registrar": "NameCheap"},
            },
            {
                "item_type": "ioc",
                "item_id": "smtp.relay.invoicing-partners-llc[.]com",
                "item_title": "Mail relay for phishing infra",
                "item_metadata": {"ioc_type": "domain", "confidence": 90},
            },
            {
                "item_type": "ioc",
                "item_id": "invoice-jan-2026.xlsm",
                "item_title": "Weaponised Excel — macro-based downloader",
                "item_metadata": {
                    "ioc_type": "file", "confidence": 100,
                    "sha256": "c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2",
                },
            },
            {
                "item_type": "technique",
                "item_id": "T1566.001",
                "item_title": "Phishing: Spearphishing Attachment",
                "item_metadata": {"tactic": "initial-access"},
            },
            {
                "item_type": "technique",
                "item_id": "T1204.002",
                "item_title": "User Execution: Malicious File",
                "item_metadata": {"tactic": "execution"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Opened from email-security gateway alert (Proofpoint TAP campaign match)"},
            {"action": "assigned", "detail": "Assigned to @email-threats"},
            {"action": "comment", "detail": "14 recipients, 2 clicks, 0 credential submissions. Both endpoints isolated by CrowdStrike in under 12 min."},
            {"action": "item_added", "detail": "Linked weaponised Excel attachment"},
            {"action": "item_added", "detail": "Mapped to T1566.001 and T1204.002"},
            {"action": "comment", "detail": "Blocked sender domain and all homoglyph variants at SEG. Mailboxes purged."},
            {"action": "updated", "detail": "status: in_progress → resolved"},
            {"action": "comment", "detail": "Targeted awareness training assigned to 14 users. Completion target: 48h. — @hr-security"},
            {"action": "updated", "detail": "status: resolved → closed"},
        ],
    },

    # 5. RFI (Request for Information) — new
    {
        "title": "RFI-2026-009: Infra Exposure to Ivanti Connect Secure Vulnerabilities",
        "description": (
            "The VP of Infrastructure has requested a comprehensive assessment of "
            "our exposure to the active Ivanti Connect Secure vulnerabilities "
            "(CVE-2024-21887, CVE-2023-46805) across all subsidiaries. Scope: "
            "software inventory, patch status, network exposure, detection coverage. "
            "Deliverable: briefing deck for the 2026-04-22 CIO review."
        ),
        "case_type": "rfi",
        "status": "new",
        "priority": "high",
        "severity": "high",
        "tlp": "TLP:GREEN",
        "tags": ["rfi", "ivanti", "cve-2024-21887", "cve-2023-46805", "exec-brief"],
        "items": [
            {
                "item_type": "intel",
                "item_id": "cve-2024-21887",
                "item_title": "CVE-2024-21887 — Ivanti Connect Secure command injection",
                "item_metadata": {"severity": "critical", "cvss": 9.1, "kev": True},
            },
            {
                "item_type": "intel",
                "item_id": "cve-2023-46805",
                "item_title": "CVE-2023-46805 — Ivanti auth bypass",
                "item_metadata": {"severity": "high", "cvss": 8.2, "kev": True},
            },
        ],
        "activities": [
            {"action": "created", "detail": "RFI from VP Infrastructure (requested by: Sam R.)"},
            {"action": "assigned", "detail": "Assigned to @vuln-mgmt"},
            {"action": "comment", "detail": "Deliverable: CIO review deck by 2026-04-22. Scope confirmed with requester."},
        ],
    },

    # 6. Supply chain investigation — in progress
    {
        "title": "INV-2026-022: Build Pipeline Integrity — Post-tj-actions Review",
        "description": (
            "Following the tj-actions/changed-files compromise (Mar 2026), conduct "
            "a complete audit of every third-party GitHub Action used across the "
            "organisation's 284 repositories. Identify actions without version "
            "pinning, pinned to floating tags, or sourced from non-verified "
            "publishers. Remediation plan and enforced policy via repo rulesets."
        ),
        "case_type": "investigation",
        "status": "in_progress",
        "priority": "high",
        "severity": "medium",
        "tlp": "TLP:GREEN",
        "tags": ["supply-chain", "github-actions", "tj-actions", "sdlc"],
        "items": [
            {
                "item_type": "intel",
                "item_id": "cve-2025-30066",
                "item_title": "CVE-2025-30066 — tj-actions/changed-files secret exfiltration",
                "item_metadata": {"severity": "high", "cvss": 8.6, "kev": False},
            },
            {
                "item_type": "technique",
                "item_id": "T1195.002",
                "item_title": "Supply Chain Compromise: Compromise Software Supply Chain",
                "item_metadata": {"tactic": "initial-access"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Opened after tj-actions advisory published by Endor Labs"},
            {"action": "assigned", "detail": "Assigned to @appsec-team"},
            {"action": "comment", "detail": "Inventory complete: 284 repos, 1,207 distinct action refs. 342 unpinned (28%). — @appseclead"},
            {"action": "comment", "detail": "Running OpenSSF scorecard + StepSecurity Harden-Runner pilots on 12 critical pipelines."},
        ],
    },

    # 7. Low-severity incident — closed quickly
    {
        "title": "IR-2026-045: Credential Leak — Public GitHub Gist",
        "description": (
            "Automated secret scanning (TruffleHog + GitGuardian) detected an AWS "
            "access key for an internal dev account leaked in a public gist by "
            "a new hire. The key had read-only access to a single non-prod S3 "
            "bucket containing synthetic test data. Key rotated within 9 minutes "
            "of detection. No unauthorised API calls observed in CloudTrail."
        ),
        "case_type": "incident_response",
        "status": "closed",
        "priority": "low",
        "severity": "low",
        "tlp": "TLP:CLEAR",
        "tags": ["credential-leak", "aws", "github", "low-impact"],
        "items": [
            {
                "item_type": "technique",
                "item_id": "T1552.001",
                "item_title": "Unsecured Credentials: Credentials In Files",
                "item_metadata": {"tactic": "credential-access"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Alert from GitGuardian integration (internal-dev-rw AWS key)"},
            {"action": "comment", "detail": "Gist deleted by author. Key rotated via IAM automation. No CloudTrail anomalies in the exposure window."},
            {"action": "updated", "detail": "status: new → resolved"},
            {"action": "comment", "detail": "New hire enrolled in secret-management training (module: `aws-secrets-101`)."},
            {"action": "updated", "detail": "status: resolved → closed"},
        ],
    },

    # 8. Hunt — resolved (validated detection)
    {
        "title": "HUNT-2026-008: Detection Validation for T1059.001 PowerShell Abuse",
        "description": (
            "Validated detection coverage for suspicious PowerShell patterns "
            "(encoded commands, downloads from non-Microsoft domains, AMSI "
            "bypass attempts) across Windows fleet. Red team emulated four "
            "Atomic Red Team tests; blue team detection hit rate was 100% "
            "post-tuning. Two new Sentinel analytic rules deployed."
        ),
        "case_type": "hunt",
        "status": "resolved",
        "priority": "medium",
        "severity": "info",
        "tlp": "TLP:GREEN",
        "tags": ["detection-engineering", "powershell", "atomic-red-team", "sentinel"],
        "items": [
            {
                "item_type": "technique",
                "item_id": "T1059.001",
                "item_title": "Command and Scripting Interpreter: PowerShell",
                "item_metadata": {"tactic": "execution"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Q1 detection-engineering backlog item"},
            {"action": "assigned", "detail": "Lead: @detection-eng"},
            {"action": "comment", "detail": "Atomic tests T1059.001-1/2/3/5 executed in lab. 3/4 detected pre-tuning; 4/4 detected post-tuning."},
            {"action": "comment", "detail": "Deployed Sentinel rules: PowerShellEncodedCommand_Suspicious + PowerShellAmsiBypass"},
            {"action": "updated", "detail": "status: in_progress → resolved"},
        ],
    },

    # 9. Active BEC investigation — in progress
    {
        "title": "INV-2026-031: Business Email Compromise — Spoofed CFO Wire Request",
        "description": (
            "AP clerk received a wire transfer request ($148,500) appearing to come "
            "from the CFO. Request passed authority sniff test on first read but "
            "sender header analysis revealed a lookalike domain "
            "(c0mpany-finance[.]com). Funds had not been sent. Thread analysed "
            "for related infrastructure; three adjacent targets at peer firms "
            "notified via industry ISAC."
        ),
        "case_type": "investigation",
        "status": "in_progress",
        "priority": "high",
        "severity": "high",
        "tlp": "TLP:AMBER",
        "tags": ["bec", "wire-fraud", "isac-shared", "finance"],
        "items": [
            {
                "item_type": "ioc",
                "item_id": "c0mpany-finance[.]com",
                "item_title": "BEC lookalike domain",
                "item_metadata": {
                    "ioc_type": "domain", "confidence": 100,
                    "registrar": "NameSilo", "registered": "2026-03-28",
                },
            },
            {
                "item_type": "ioc",
                "item_id": "cfo-wire-approval.pdf",
                "item_title": "Weaponised PDF with fake signature",
                "item_metadata": {"ioc_type": "file", "confidence": 100},
            },
            {
                "item_type": "technique",
                "item_id": "T1566.003",
                "item_title": "Phishing: Spearphishing via Service",
                "item_metadata": {"tactic": "initial-access"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Opened after AP clerk reported suspicious wire request to security"},
            {"action": "assigned", "detail": "Assigned to @email-threats"},
            {"action": "comment", "detail": "Wire never initiated — bank verification callback is standard procedure. Policy worked."},
            {"action": "item_added", "detail": "Linked lookalike domain c0mpany-finance[.]com"},
            {"action": "comment", "detail": "ISAC shareable indicators submitted to FS-ISAC under reference 2026-BEC-441."},
        ],
    },

    # 10. Low-priority hunt — new
    {
        "title": "HUNT-2026-014: Cloud CostAnomaly as Proxy for Cryptomining",
        "description": (
            "Exploratory hunt: correlate AWS CostAnomaly alerts with CloudTrail "
            "patterns indicative of cryptomining (e.g. sudden EC2 instance-type "
            "upgrades, GPU instance creation in unused regions, spot fleet spikes). "
            "Low-priority research project — deliverable is a detection pattern "
            "document, not a live incident."
        ),
        "case_type": "hunt",
        "status": "new",
        "priority": "low",
        "severity": "low",
        "tlp": "TLP:GREEN",
        "tags": ["cloud", "aws", "cryptomining", "cost-anomaly", "research"],
        "items": [
            {
                "item_type": "technique",
                "item_id": "T1496",
                "item_title": "Resource Hijacking",
                "item_metadata": {"tactic": "impact"},
            },
        ],
        "activities": [
            {"action": "created", "detail": "Research hunt scheduled for Q2 2026 detection R&D"},
            {"action": "comment", "detail": "Proposed outputs: KQL / SQL patterns, CostAnomaly threshold study, unit-econ analysis."},
        ],
    },
]
