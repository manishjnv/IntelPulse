# IntelPulse — Technical Architecture

## Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions

---

## System Overview

IntelPulse is a production-grade threat intelligence platform that aggregates IOCs from 13+ external feeds, enriches them with AI analysis via Amazon Bedrock, and provides SOC analysts with searchable, actionable intelligence through a web dashboard. The platform was developed entirely using KIRO IDE and Amazon Q Developer.

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Users / SOC Analysts                      │
│                    http://3.87.235.189:3000                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    EC2 Instance (t3.small)                        │
│                    3.87.235.189 / us-east-1                       │
│                                                                   │
│  ┌───────────────────┐          ┌───────────────────┐            │
│  │  Next.js UI :3000 │          │  FastAPI API :8000 │            │
│  │  TypeScript        │  ◄────► │  Python 3.12       │            │
│  │  Tailwind CSS      │          │  Async + Pydantic  │            │
│  │  Recharts + Zustand│          │  Bedrock Adapter   │            │
│  └───────────────────┘          └────────┬──────────┘            │
│                                           │                       │
│  ┌────────────────────────────────────────┼──────────────────┐   │
│  │              Docker Compose Services    │                  │   │
│  │  ┌──────────────────┐  ┌──────────────┐│                  │   │
│  │  │  PostgreSQL 16    │  │   Redis 7    ││                  │   │
│  │  │  + TimescaleDB    │  │  Sessions    ││                  │   │
│  │  │  (time-series DB) │  │  Cache, RQ   ││                  │   │
│  │  └──────────────────┘  └──────────────┘│                  │   │
│  └────────────────────────────────────────┘                  │   │
└───────────────────────────────────────────┼──────────────────────┘
                                            │ boto3 SDK
                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        AWS Services                               │
│                                                                   │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │   Amazon Bedrock        │  │   IAM                          │  │
│  │   Claude 3 Haiku        │  │   BedrockAccessRole            │  │
│  │   (AI threat analysis)  │  │   (least-privilege policies)   │  │
│  └────────────────────────┘  └────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │   AWS CDK               │  │   EC2                          │  │
│  │   Infrastructure as Code│  │   t3.small, us-east-1          │  │
│  └────────────────────────┘  └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    External Threat Feeds                          │
│  NVD, CISA KEV, AbuseIPDB, VirusTotal, Shodan, OTX,             │
│  ThreatFox, URLhaus, MalwareBazaar, MITRE ATT&CK,               │
│  ExploitDB, CISA Advisories                                      │
└──────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, Zustand | SOC analyst dashboard |
| Backend | Python 3.12, FastAPI (async), Pydantic v2 | REST API |
| Database | PostgreSQL 16 + TimescaleDB | Time-series intel storage |
| Cache | Redis 7 | Sessions, caching, job queue |
| AI | Amazon Bedrock (Claude 3 Haiku) | Threat analysis, IOC enrichment |
| Infra | Docker Compose on EC2 | Container orchestration |
| IaC | AWS CDK (TypeScript) | Infrastructure as Code |
| Dev Tools | KIRO IDE, Amazon Q Developer | AI-assisted development |

## AWS Services Integration

### Amazon Bedrock

The platform uses Amazon Bedrock for AI-powered threat analysis:

- **Model**: Claude 3 Haiku (`anthropic.claude-3-haiku-20240307-v1:0`)
- **Integration**: Direct boto3 SDK calls via `BedrockAdapter` class
- **Authentication**: IAM role (BedrockAccessRole) attached to EC2 instance
- **Endpoints**:
  - `POST /api/v1/demo/analyze` — IOC threat analysis
  - `GET /api/v1/demo/health` — Bedrock health check

### Bedrock Adapter Architecture

```text
API Request → BedrockAdapter → boto3.client('bedrock-runtime')
                                    │
                                    ▼
                            Amazon Bedrock
                            Claude 3 Haiku
                                    │
                                    ▼
                            Structured JSON Response
                            (risk_score, severity, MITRE techniques)
```

The adapter supports:

- Text generation (`ai_analyze`)
- Structured JSON generation (`ai_analyze_structured`)
- Health checks (`check_health`)
- Automatic response parsing with markdown fence stripping

### Multi-Agent Design

| Agent | Role | Implementation |
|-------|------|----------------|
| Supervisor | IntelPulse Threat Analyst — orchestrates analysis | Bedrock adapter |
| IOC Reputation Analyst | Queries VirusTotal, AbuseIPDB, OTX, Shodan | Lambda action groups |
| Threat Context Enricher | Maps findings to MITRE ATT&CK | Knowledge base |
| Risk Scorer | Aggregates into risk assessment | Scoring service |

### Lambda Action Groups (CDK)

- `virustotal_lookup` — IOC reputation check
- `abuseipdb_check` — IP abuse scoring
- `otx_lookup` — AlienVault OTX pulse search
- `shodan_lookup` — Internet exposure scan

## Data Flow

### 1. Feed Ingestion Pipeline

```text
External Feed → Feed Connector → Normalize → Score → Store (PostgreSQL)
                                                    → Index (search)
```

12 feed connectors fetch data from external sources, normalize it into a common schema, calculate risk scores, and store in PostgreSQL with TimescaleDB hypertables.

### 2. AI Enrichment Pipeline

```text
IOC/News Item → Bedrock Adapter → Claude 3 Haiku → Structured Analysis
                                                  → Risk Score
                                                  → MITRE Techniques
                                                  → Recommendations
```

Amazon Bedrock enriches threat data with:

- Structured threat summaries
- Risk scoring (0-100)
- MITRE ATT&CK technique mapping
- Actionable security recommendations

### 3. User Query Flow

```text
SOC Analyst → UI Dashboard → API → PostgreSQL → Aggregated Results
           → IOC Search → API → Full-text Search → Filtered Results
           → AI Analysis → API → Bedrock → Threat Assessment
```

## Database Schema

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `intel_items` | Threat intelligence items | title, description, severity, risk_score, feed_source |
| `iocs` | Indicators of Compromise | value, type (ip/domain/hash/url), severity |
| `news_articles` | Cyber news with AI enrichment | title, content, ai_summary, risk_score |
| `mitre_techniques` | MITRE ATT&CK framework | technique_id, name, tactic, description |
| `cases` | Incident management | title, status, priority, assignee |
| `users` | Authentication | email, name, role, google_id |

### TimescaleDB Hypertables

IOC data uses TimescaleDB hypertables for efficient time-series queries:

- Automatic partitioning by time
- Compression for historical data
- Continuous aggregates for dashboard metrics

## Security Architecture

### Authentication

| Method | Description |
|--------|-------------|
| Google OAuth 2.0 | Primary SSO authentication |
| Email OTP | Secondary authentication via SMTP |
| Demo Mode | `DEV_BYPASS_AUTH=true` for codethon reviewers |

### IAM Policies

- **BedrockAccessRole**: Least-privilege IAM role with `bedrock:InvokeModel` permission
- **MarketplaceAccess**: AWS Marketplace subscription permissions for model access
- Scoped to specific model ARNs (`anthropic.claude-*`)

### Network Security

- Security groups with minimal port exposure (22, 3000, 8000)
- Docker network isolation between services
- Redis password authentication
- PostgreSQL password authentication

## Deployment Architecture

### Current (EC2 Demo)

```text
EC2 Instance (t3.small, us-east-1)
├── Docker Compose
│   ├── PostgreSQL + TimescaleDB (:5432)
│   ├── Redis 7 (:6379)
│   ├── FastAPI API (:8000)
│   └── Next.js UI (:3000)
└── IAM Role: BedrockAccessRole
    └── Amazon Bedrock (Claude 3 Haiku)
```

### Target (AWS Managed Services)

```text
AWS (us-east-1)
├── ECS Fargate
│   ├── API Service (FastAPI)
│   ├── UI Service (Next.js)
│   ├── Worker Service (Python RQ)
│   └── Scheduler Service (APScheduler)
├── EC2 t3.medium (PostgreSQL + TimescaleDB)
├── ElastiCache Redis 7
├── AWS OpenSearch Service
├── ALB + ACM (HTTPS)
├── Route 53 (DNS)
├── Secrets Manager (env vars)
├── ECR (container images)
└── Amazon Bedrock (AI layer)
```

## KIRO IDE Development Workflow

### Spec-Driven Development

```text
Requirements (12) → Design (1,320 lines) → Tasks (15) → Implementation
```

### Steering Files

| File | Purpose |
|------|---------|
| `tech.md` | Technology stack reference |
| `product.md` | Product context for SOC analysts |
| `coding-standards.md` | Code quality rules |
| `aws-migration.md` | Migration-specific constraints |

### Agent Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| `security-scan` | User-triggered | Scans for hardcoded credentials, SQL injection |
| `doc-update` | File edited | Reminds to update documentation |
| `test-sync` | File edited | Ensures tests stay in sync |

## Access URLs

| Access | URL |
|--------|-----|
| UI Dashboard | <http://3.87.235.189:3000> |
| API Documentation | <http://3.87.235.189:8000/api/docs> |
| API Root | <http://3.87.235.189:8000> |
| Demo Health | <http://3.87.235.189:8000/api/v1/demo/health> |
| Demo Analysis | `POST http://3.87.235.189:8000/api/v1/demo/analyze` |
