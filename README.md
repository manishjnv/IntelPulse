# IntelPulse — Threat Intelligence Platform

> **Wipro × AWS Codeathon** — Theme 3: Intelligent Multi-Agent Domain Solutions

A production-grade threat intelligence aggregation and analysis platform powered by **Amazon Bedrock**, **FastAPI**, **Next.js 14**, **PostgreSQL/TimescaleDB**, and **Redis**. Built entirely using **KIRO IDE** and **Amazon Q Developer**.

![AWS](https://img.shields.io/badge/Amazon_Bedrock-FF9900?style=flat&logo=amazonaws&logoColor=white)
![KIRO](https://img.shields.io/badge/KIRO_IDE-232F3E?style=flat&logo=amazonaws&logoColor=white)
![Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/Next.js_14-000000?style=flat&logo=next.js&logoColor=white)
![Stack](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Stack](https://img.shields.io/badge/TimescaleDB-FDB515?style=flat&logo=timescale&logoColor=black)
![Stack](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)
![Stack](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![Stack](https://img.shields.io/badge/AWS_CDK-FF9900?style=flat&logo=amazonaws&logoColor=white)

---

## Live Demo

| Access | URL |
|--------|-----|
| Application (UI) | <http://13.222.13.45:3000> |
| API Documentation | <http://13.222.13.45:8000/api/docs> |
| API Root | <http://13.222.13.45:8000> |
| Source Code | <https://github.com/manishjnv/IntelPulse> (branch: `aws-migration`) |

---

## AWS Services Used (Codethon Requirements)

| Service | Usage |
|---------|-------|
| **KIRO IDE** | Spec-driven development, steering files, agent hooks, autopilot mode |
| **Amazon Q Developer** | Inline code suggestions, security scans, code transformation |
| **Amazon Bedrock** | Claude 3 Haiku / Nova Lite for AI-powered threat analysis |
| **AWS CDK** | Infrastructure as Code (VPC, ECS, ALB, data services) |
| **EC2** | Application hosting (t3.small, us-east-1) |
| **IAM** | BedrockAccessRole with least-privilege policies |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    Users / SOC Analysts                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  EC2 Instance (t3.small)                      │
│                  13.222.13.45 / us-east-1                     │
│                                                               │
│  ┌──────────────────┐     ┌──────────────────┐               │
│  │ Next.js UI :3000 │     │ FastAPI API :8000 │               │
│  │ TypeScript        │     │ Python 3.12       │               │
│  │ Tailwind+Recharts │     │ Async + Pydantic  │               │
│  └──────────────────┘     └────────┬─────────┘               │
│                                     │                         │
│  ┌──────────────┐  ┌──────────────┐│                         │
│  │ PostgreSQL 16│  │   Redis 7    ││                         │
│  │ + TimescaleDB│  │ Sessions, RQ ││                         │
│  └──────────────┘  └──────────────┘│                         │
└─────────────────────────────────────┼────────────────────────┘
                                      │ boto3 SDK
                                      ▼
                    ┌─────────────────────────────┐
                    │      Amazon Bedrock          │
                    │  Claude 3 Haiku / Nova Lite  │
                    │  (AI threat analysis)        │
                    └─────────────────────────────┘
```

| Service | Technology | Port |
|---------|-----------|------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, Zustand | 3000 |
| Backend API | Python 3.12, FastAPI (async), Pydantic v2 | 8000 |
| Database | PostgreSQL 16 + TimescaleDB | 5432 |
| Cache/Queue | Redis 7 (sessions, caching, job queue) | 6379 |
| AI Engine | Amazon Bedrock (Claude 3 Haiku) | — |
| IaC | AWS CDK (TypeScript) | — |

---

## Key Features

| Feature | Description |
|---------|-------------|
| 13+ Threat Feed Sources | NVD, CISA KEV, AbuseIPDB, VirusTotal, Shodan, OTX, ThreatFox, URLhaus, MalwareBazaar, MITRE ATT&CK, ExploitDB |
| AI-Powered Analysis | Amazon Bedrock for IOC risk scoring, MITRE ATT&CK mapping, structured threat summaries |
| Full-Text IOC Search | Search by IP, domain, hash, URL with severity/type/date filters |
| Live Internet Lookup | Real-time queries to 12+ sources for any IOC |
| Analytics Dashboard | Severity distribution, geo view, source reliability, trend charts |
| Cyber News Feed | 19 RSS sources with AI enrichment and relevance scoring |
| Case Management | Incident response, investigation, and threat hunting workflows |
| Detection Rules | Auto-generated YARA, KQL, Sigma rules from threat intelligence |
| MITRE ATT&CK Mapping | 803 techniques with automated intel-technique linking |

---

## Pages & Routes

| Page | Route | Description |
|------|-------|-------------|
| Dashboard | `/dashboard` | KPI cards, threat level bar, severity/category charts, top risks |
| Threat Feed | `/threats` | Severity filter, risk-sorted threat list, asset type breakdown |
| Cyber News | `/news` | AI-enriched cyber news feed with category widgets |
| IOC Search | `/search` | Full-text search with Live Internet Lookup and AI analysis |
| IOC Database | `/iocs` | Browse all IOCs with type filters and distribution charts |
| Analytics | `/analytics` | Severity charts, category donut, geo/industry rankings |
| Geo View | `/geo` | Geographic threat distribution with region drill-down |
| Cases | `/cases` | Incident management and investigation workflows |
| Reports | `/reports` | AI-generated threat intelligence reports |
| Feed Status | `/feeds` | Feed health monitor with status badges and error display |
| Settings | `/settings` | Platform configuration and API key management |

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- AWS account with Bedrock access (for AI features)

### Deploy

```bash
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse
git checkout aws-migration
cp .env.example .env
# Edit .env with your configuration
docker compose up -d --build
```

### Verify

```bash
# API health check
curl http://localhost:8000/api/v1/health

# Demo endpoint (Bedrock AI analysis)
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}'

# Open UI
open http://localhost:3000
```

---

## Bedrock AI Integration

### Demo Endpoint

```bash
POST /api/v1/demo/analyze
Content-Type: application/json

{
  "ioc": "45.142.212.61",
  "ioc_type": "ip"
}
```

Returns structured threat analysis:

- Risk score (0-100)
- Severity level (CRITICAL/HIGH/MEDIUM/LOW)
- MITRE ATT&CK technique mapping
- Recommended security actions
- Natural language analysis

### Multi-Agent Design

| Agent | Role |
|-------|------|
| Supervisor | IntelPulse Threat Analyst — orchestrates IOC analysis |
| IOC Reputation Analyst | Queries VirusTotal, AbuseIPDB, OTX, Shodan via Lambda |
| Threat Context Enricher | Maps findings to MITRE ATT&CK knowledge base |
| Risk Scorer | Aggregates findings into risk assessment |

---

## KIRO IDE Features Used

| Feature | Details |
|---------|---------|
| Specs | 1 spec with requirements, design (1,320 lines), and 15 tasks |
| Steering | 4 files (tech, product, coding-standards, aws-migration) |
| Hooks | 3 hooks (security-scan, doc-update, test-sync) |
| Autopilot | Multi-file coordination for CDK, API, and UI changes |

---

## Productivity Impact

| Metric | Value |
|--------|-------|
| Time savings | 76% (17 hours vs 70 hours traditional) |
| Lines generated/modified | 5,850 with KIRO + Q assistance |
| Requirement-to-code time | 15 minutes avg (vs 2 hours traditional) |
| Type errors in production | Zero (caught inline by Q) |

---

## Repository Structure

```text
IntelPulse/
├── .kiro/                    # KIRO IDE configuration
│   ├── specs/                # Spec-driven development
│   ├── steering/             # Context steering files
│   └── hooks/                # Automation hooks
├── api/                      # FastAPI backend (Python 3.12)
│   ├── app/routes/           # API endpoints (including demo)
│   ├── app/services/         # Business logic + Bedrock adapter
│   ├── app/models/           # SQLAlchemy ORM models
│   └── app/normalizers/      # Data normalization
├── ui/                       # Next.js 14 frontend (TypeScript)
├── worker/                   # Background job processing
├── infra/                    # AWS CDK infrastructure
│   ├── lib/                  # CDK stack definitions
│   └── lambdas/              # Bedrock agent Lambda handlers
├── db/                       # Database schema + migrations
├── docker/                   # Dockerfiles (API, UI, Worker)
├── docs/                     # Documentation
│   ├── ARCHITECTURE.md       # Technical architecture
│   ├── SUBMISSION.md         # Codethon submission details
│   ├── AMAZON_Q_USAGE_REPORT.md  # Q Developer usage report
│   └── PRODUCTIVITY_METRICS.md   # Productivity measurements
└── .github/workflows/        # CI/CD pipeline
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [docs/SUBMISSION.md](docs/SUBMISSION.md) | Codethon submission details and deliverables |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture and data flow |
| [docs/AMAZON_Q_USAGE_REPORT.md](docs/AMAZON_Q_USAGE_REPORT.md) | KIRO + Amazon Q usage report |
| [docs/PRODUCTIVITY_METRICS.md](docs/PRODUCTIVITY_METRICS.md) | Development productivity metrics |
| [docs/TECHNOLOGY.md](docs/TECHNOLOGY.md) | Full technology stack details |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | Feed integration documentation |

---

## Author

**Manish Kumar** — <manishjnvk@gmail.com>

Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions

---

## License

Private — All rights reserved.
