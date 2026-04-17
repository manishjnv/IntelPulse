# IntelPulse — AWS Codeathon Submission

## Author: Manish Kumar (<manishjnvk@gmail.com>)

## Challenge: Wipro × AWS | Build Real Agentic AI Applications

## Theme: Theme 3 — Intelligent Multi-Agent Domain Solutions

---

## Access URLs

Public endpoints served over HTTPS via Caddy + Let's Encrypt. The raw EC2
ports (`:3000`, `:8000`) are firewalled — only the domain is reachable.

| Method | URL | Notes |
| ------ | --- | ----- |
| **Application (UI)** | <https://intelpulse.tech/dashboard> | Full dashboard |
| **Threat Feed** | <https://intelpulse.tech/threats> | Filterable intel feed |
| **Cyber News** | <https://intelpulse.tech/news> | AI-enriched news |
| **Threat Briefings** | <https://intelpulse.tech/briefings> | 3 enriched sample briefings |
| **AI Configuration** | <https://intelpulse.tech/settings?section=ai> | Tiered routing + pipeline panel |
| **API Documentation** | <https://intelpulse.tech/api/docs> | Swagger UI |
| **API Root** | <https://intelpulse.tech/api> | Version info |
| **Demo Health** | <https://intelpulse.tech/api/v1/demo/health> | Bedrock status |
| **Demo Analysis** | `POST https://intelpulse.tech/api/v1/demo/analyze` | IOC threat analysis |
| **Pipeline JSON** | <https://intelpulse.tech/api/v1/ai-settings/pipeline> | Live routing matrix |

---

## Deliverables Checklist

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working Application | ✅ | <https://intelpulse.tech/dashboard> |
| Source Code Repository | ✅ | <https://github.com/manishjnv/IntelPulse> (branch: `main`) |
| Amazon Q Usage Report | ✅ | `docs/AMAZON_Q_USAGE_REPORT.md` |
| Productivity Metrics | ✅ | `docs/PRODUCTIVITY_METRICS.md` |
| Technical Architecture | ✅ | `docs/ARCHITECTURE.md` |
| Demo Video | 📹 | `docs/DEMO_VIDEO_SCRIPT.md` |

---

## AWS Services Utilized

| Service | Usage | Evidence |
|---------|-------|----------|
| **KIRO IDE** | Specs, steering files, hooks, autopilot development | `.kiro/specs/`, `.kiro/steering/`, `.kiro/hooks/` |
| **Amazon Q Developer** | Inline code suggestions, debugging, security scans | `docs/AMAZON_Q_USAGE_REPORT.md` |
| **Amazon Bedrock** | Tiered multi-model routing (Nova / Llama / Mistral) + Supervisor-led Agents with a VirusTotal action group | `api/app/services/bedrock_adapter.py`, `api/app/services/bedrock_agent_adapter.py`, `api/app/routes/demo.py`, `scripts/probe_bedrock_models.py` |
| **AWS CDK** | Infrastructure as Code | `infra/lib/intelpulse-stack.ts` |
| **EC2** | Application hosting (t3.small, us-east-1) | Instance i-08e16a37688d50004 |
| **IAM** | BedrockAccessRole with least-privilege policies | Bedrock invoke + Marketplace permissions |

---

## Agent Architecture

### Bedrock AI Enrichment (Implemented)

Amazon Bedrock powers the AI layer through two complementary paths — both
share the same `BedrockAdapter` instance:

- **Tiered single-shot routing** (default for most features):
  - Classifier → `us.meta.llama4-scout-17b-instruct-v1:0`
  - Correlator → `amazon.nova-pro-v1:0`
  - Narrative → `mistral.mistral-large-2402-v1:0`
  - Fallback → `us.meta.llama3-3-70b-instruct-v1:0`
- **Multi-agent Supervisor collaboration** — Supervisor (`IntelPulse-Threat-Analyst`) + IOC-Analyst (with `virustotal_lookup` Lambda action group) + Risk-Scorer.
- **Dispatch**: `BedrockAdapter.ai_analyze(model_id=...)` — handles Nova / Titan / Anthropic via `invoke_model`, and Meta Llama / Mistral / DeepSeek / Cohere / AI21 via the unified **Converse API**.
- **Authentication**: EC2 IAM role `BedrockAccessRole` via IMDS — no API keys.
- **Routing transparency**: <https://intelpulse.tech/api/v1/ai-settings/pipeline> returns the live feature → path → model mapping.
- **Features**:
  - Tier-appropriate IOC analysis, news enrichment, briefing generation
  - MITRE ATT&CK mapping
  - Structured JSON extraction with refusal fallback
  - Executive narratives + analyst-ready summaries
  - Actionable recommendations

### Demo Endpoint

```bash
curl -X POST https://intelpulse.tech/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "45.142.212.61", "ioc_type": "ip"}'
```

Returns:

```json
{
  "ioc": "45.142.212.61",
  "ioc_type": "ip",
  "risk_score": 85,
  "severity": "HIGH",
  "confidence": 90,
  "mitre_techniques": ["T1566", "T1059", "T1071"],
  "recommended_actions": [
    "Block IP at firewall level",
    "Review logs for connections to this IP",
    "Check for indicators of compromise"
  ],
  "analysis": "This IP shows characteristics associated with malicious activity..."
}
```

### Multi-Agent Design

| Agent | Role |
|-------|------|
| **Supervisor** | IntelPulse Threat Analyst — orchestrates IOC analysis |
| **IOC Reputation Analyst** | Queries VirusTotal, AbuseIPDB, OTX, Shodan via Lambda |
| **Threat Context Enricher** | Maps findings to MITRE ATT&CK knowledge base |
| **Risk Scorer** | Aggregates findings into risk assessment |

### Lambda Action Groups (Implemented in CDK)

- `virustotal_lookup` — IOC reputation check
- `abuseipdb_check` — IP abuse scoring
- `otx_lookup` — AlienVault OTX pulse search
- `shodan_lookup` — Internet exposure scan

---

## Platform Features

| Feature | Description |
|---------|-------------|
| 13+ Threat Feed Sources | NVD, CISA KEV, AbuseIPDB, VirusTotal, Shodan, OTX, ThreatFox, URLhaus |
| AI-Powered Analysis | Amazon Bedrock for risk scoring, MITRE mapping, threat summaries |
| Full-Text IOC Search | Search by IP, domain, hash, URL with filters |
| Live Internet Lookup | Real-time queries to 12+ sources |
| Analytics Dashboard | Severity distribution, geo view, source reliability |
| Cyber News Feed | 19 RSS sources with AI enrichment |
| Case Management | Incident response and investigation workflows |
| Detection Rules | Auto-generated YARA, KQL, Sigma rules |
| MITRE ATT&CK | 803 techniques with automated linking |

---

## KIRO Features Used

| Feature | Details |
|---------|---------|
| **Specs** | 1 spec with requirements, design (1,320 lines), and 15 tasks |
| **Steering** | 4 files (tech, product, coding-standards, aws-migration) |
| **Hooks** | 3 hooks (security-scan, doc-update, test-sync) |
| **Autopilot** | Multi-file coordination for CDK, API, and UI changes |

---

## Productivity Impact

| Metric | Value |
|--------|-------|
| Time savings | 76% (17 hours vs 70 hours traditional) |
| Lines generated/modified | 5,850 with KIRO + Q assistance |
| Requirement-to-code time | 15 minutes avg (vs 2 hours traditional) |
| Type errors in production | Zero (caught inline by Q) |
| Security issues found/fixed | 12 (8 CRITICAL, 4 HIGH) |

---

## Repository Structure

```text
IntelPulse/
├── .kiro/                    # KIRO IDE configuration
│   ├── specs/                # Spec-driven development
│   ├── steering/             # Context steering files (4 files)
│   └── hooks/                # Automation hooks (3 hooks)
├── api/                      # FastAPI backend (Python 3.12)
│   ├── app/routes/           # API endpoints (including demo)
│   ├── app/services/         # Business logic + Bedrock adapter
│   ├── app/models/           # SQLAlchemy ORM models
│   └── app/normalizers/      # Data normalization (14 normalizers)
├── ui/                       # Next.js 14 frontend (TypeScript)
│   └── src/app/(app)/        # Dashboard, search, analytics pages
├── worker/                   # Background job processing
├── infra/                    # AWS CDK infrastructure
│   ├── lib/                  # CDK stack definitions
│   └── lambdas/              # Bedrock agent Lambda handlers
├── db/                       # Database schema + migrations
├── docker/                   # Dockerfiles (API, UI, Worker)
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Technical architecture
│   ├── SUBMISSION.md         # This file
│   ├── AMAZON_Q_USAGE_REPORT.md  # Q Developer usage report
│   └── PRODUCTIVITY_METRICS.md   # Productivity measurements
└── .github/workflows/        # CI/CD pipeline
```

---

## How to Run

### Quick Start

```bash
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse
git checkout aws-migration
cp .env.example .env
docker compose up -d --build
```

### Test Bedrock Integration

```bash
# Health check
curl https://intelpulse.tech/api/v1/demo/health

# Analyze a threat
curl -X POST https://intelpulse.tech/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}'
```

---

## Author

**Manish Kumar** — <manishjnvk@gmail.com>

Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions
