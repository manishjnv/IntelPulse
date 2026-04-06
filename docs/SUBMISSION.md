# IntelPulse — AWS Codeathon Submission

## Author: Manish Kumar (<manishjnvk@gmail.com>)

## Challenge: Wipro × AWS | Build Real Agentic AI Applications

## Theme: Theme 3 — Intelligent Multi-Agent Domain Solutions

---

## Access URLs

| Method | URL | Notes |
|--------|-----|-------|
| **Application (UI)** | <http://13.222.13.45:3000> | Full dashboard |
| **API Documentation** | <http://13.222.13.45:8000/api/docs> | Swagger UI |
| **API Root** | <http://13.222.13.45:8000> | Version info |
| **Demo Health** | <http://13.222.13.45:8000/api/v1/demo/health> | Bedrock status |
| **Demo Analysis** | `POST http://13.222.13.45:8000/api/v1/demo/analyze` | AI threat analysis |

---

## Deliverables Checklist

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working Application | ✅ | <http://13.222.13.45:3000> |
| Source Code Repository | ✅ | <https://github.com/manishjnv/IntelPulse> (branch: `aws-migration`) |
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
| **Amazon Bedrock** | Claude 3 Haiku for AI-powered threat analysis | `api/app/services/bedrock_adapter.py`, `api/app/routes/demo.py` |
| **AWS CDK** | Infrastructure as Code | `infra/lib/intelpulse-stack.ts` |
| **EC2** | Application hosting (t3.small, us-east-1) | Instance i-08e16a37688d50004 |
| **IAM** | BedrockAccessRole with least-privilege policies | Bedrock invoke + Marketplace permissions |

---

## Agent Architecture

### Bedrock AI Enrichment (Implemented)

Amazon Bedrock powers the AI layer with direct SDK integration:

- **Model**: Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- **Integration**: boto3 SDK via `BedrockAdapter` class
- **Authentication**: IAM role (no API keys)
- **Features**:
  - IOC threat analysis with risk scoring
  - MITRE ATT&CK technique mapping
  - Structured JSON output for automation
  - Natural language summaries for analysts
  - Actionable security recommendations

### Demo Endpoint

```bash
curl -X POST http://13.222.13.45:8000/api/v1/demo/analyze \
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
curl http://13.222.13.45:8000/api/v1/demo/health

# Analyze a threat
curl -X POST http://13.222.13.45:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}'
```

---

## Author

**Manish Kumar** — <manishjnvk@gmail.com>

Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions
