# IntelPulse AWS Codethon — Complete Migration Plan
## KIRO-Ready Implementation Document

**Project**: IntelPulse Threat Intelligence Platform  
**Repo**: https://github.com/manishjnv/IntelPulse  
**Current Host**: Hostinger VPS · IntelPulse.in  
**Target**: AWS ap-south-1 (Mumbai) · intelpulse.tech  
**Codethon Theme**: Theme 3 — Intelligent Multi-Agent Domain Solutions  
**Tools**: KIRO IDE/CLI · Amazon Q Developer · Amazon Bedrock Agent Core · AWS Transform  

---

## 1. CURRENT SYSTEM — EXACT STATE

**Note**: Original system runs as IntelPulse on IntelPulse.in. AWS migration will rebrand to IntelPulse on intelpulse.tech.

### 1.1 Docker Compose Services (7 total)

```
Service         Image                                    Ports    Purpose
─────────────────────────────────────────────────────────────────────────────
postgres        timescale/timescaledb:latest-pg16         5432     Primary DB + TimescaleDB hypertables
redis           redis:7-alpine                           6379     Sessions (iw_session), RQ job queue
opensearch      opensearchproject/opensearch:2.13.0       9200     Full-text IOC search, analytics
api             docker/Dockerfile.api (FastAPI)           8000     Backend REST API
ui              docker/Dockerfile.ui (Next.js 14)         3000     Frontend SPA
worker          docker/Dockerfile.worker (Python RQ)      —        Background feed ingestion, AI enrichment
scheduler       docker/Dockerfile.worker (same image)     —        APScheduler cron for feed scheduling
caddy           caddy:2-alpine                           80,443   Reverse proxy, auto HTTPS via Let's Encrypt
```

### 1.2 Environment Variables (from docker-compose.yml)

```
# Shared across services (x-common-env anchor):
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ti_platform
POSTGRES_USER=ti
POSTGRES_PASSWORD=ti_secret
REDIS_URL=redis://:IntelPulse_R3dis_2026@redis:6379/0
OPENSEARCH_URL=http://opensearch:9200
LOG_LEVEL=INFO
ENVIRONMENT=production

# API-specific:
SECRET_KEY=${SECRET_KEY:-change-me-in-production}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-}
DOMAIN=${DOMAIN:-intelpulse.tech}
DOMAIN_UI=${DOMAIN_UI:-https://intelpulse.tech}
DOMAIN_API=${DOMAIN_API:-https://intelpulse.tech}
JWT_EXPIRE_MINUTES=${JWT_EXPIRE_MINUTES:-480}
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_FROM_NAME
EMAIL_OTP_ENABLED=${EMAIL_OTP_ENABLED:-false}

# External API keys (API + Worker share these):
NVD_API_KEY, ABUSEIPDB_API_KEY, OTX_API_KEY, VIRUSTOTAL_API_KEY, SHODAN_API_KEY
AI_API_URL, AI_API_KEY, AI_MODEL
CEREBRAS_API_KEY, HF_API_KEY

# UI-specific:
BACKEND_URL=http://api:8000
```

### 1.3 Volumes

```
pg_data       → /var/lib/postgresql/data
redis_data    → /data
os_data       → /usr/share/opensearch/data
caddy_data    → /data
caddy_config  → /config
```

### 1.4 Init Scripts

```
./db/schema.sql → mounted as /docker-entrypoint-initdb.d/01-schema.sql (read-only)
./caddy/Caddyfile → mounted as /etc/caddy/Caddyfile (read-only)
```

### 1.5 Repo Directory Structure

```
IntelPulse/
├── .github/          # GitHub Actions workflows
├── api/              # FastAPI backend (Python, async SQLAlchemy, Pydantic v2)
├── caddy/            # Caddyfile for reverse proxy
├── cloudflare/       # Deprecated tunnel config
├── db/               # schema.sql init
├── docker/           # Dockerfile.api, Dockerfile.ui, Dockerfile.worker
├── docs/             # ARCHITECTURE.md, TECHNOLOGY.md, INTEGRATION.md, WORKFLOW.md, ROADMAP.md
├── migrations/       # Database migration scripts
├── opensearch/       # Index templates/mappings
├── scripts/          # Utility scripts
├── ui/               # Next.js 14, TypeScript, Tailwind CSS, Recharts, Zustand
├── worker/           # Python RQ workers + APScheduler
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── instruction.md
└── ruff.toml
```

### 1.6 API Routes (for Bedrock Agent integration points)

```
GET  /api/v1/health              → Service health check
GET  /api/v1/auth/config         → Auth method config
GET  /api/v1/auth/google/url     → Google OAuth redirect
GET  /api/v1/auth/google/callback → OAuth callback
POST /api/v1/auth/otp/send       → Email OTP
POST /api/v1/auth/otp/verify     → OTP verify
POST /api/v1/auth/logout         → Revoke session
GET  /api/v1/auth/session        → Session check
GET  /api/v1/me                  → Current user
GET  /api/v1/dashboard           → Dashboard stats
GET  /api/v1/intel               → Paginated intel items
GET  /api/v1/intel/{id}          → Single intel detail
GET  /api/v1/search              → Full-text IOC search ← BEDROCK AGENT TARGET
GET  /api/v1/feeds/status        → Feed health
POST /api/v1/feeds/{name}/trigger → Manual feed trigger
POST /api/v1/feeds/trigger-all   → Trigger all feeds
GET  /api/v1/setup/config        → Platform config
GET  /api/v1/setup/status        → Setup checklist
```

### 1.7 AI Integration Points (current llama3 calls to replace)

The API currently calls `AI_API_URL` with `AI_API_KEY` for:
1. **IOC analysis** — structured AI summaries when an IOC is searched
2. **Cyber news enrichment** — AI-generated relevance scoring and categorization
3. **Threat intel summarization** — structured intelligence cards
4. **Live Internet Lookup** — queries 12+ external sources (VT, AbuseIPDB, OTX, Shodan, NVD, etc.), then uses AI to synthesize findings

---

## 2. TARGET AWS ARCHITECTURE

### 2.1 Service Mapping

```
CURRENT (Docker Compose)          →  AWS TARGET
─────────────────────────────────────────────────────────────────
caddy (reverse proxy + TLS)       →  ALB + ACM certificate
                                     Route 53 for DNS (intelpulse.tech)
postgres (timescaledb:pg16)       →  EC2 t3.medium running same Docker image
                                     (RDS does NOT support TimescaleDB extension)
                                     EBS gp3 volume for /var/lib/postgresql/data
redis (redis:7-alpine)            →  ElastiCache Redis 7, cache.t3.micro
                                     Single-node, same connection string format
opensearch (opensearch:2.13.0)    →  AWS OpenSearch Service
                                     t3.small.search, single-node, no fine-grained security
api (FastAPI)                     →  ECS Fargate task (512 CPU, 1024 MiB)
ui (Next.js 14)                   →  ECS Fargate task (256 CPU, 512 MiB)
worker (Python RQ)                →  ECS Fargate task (256 CPU, 512 MiB)
scheduler (APScheduler)           →  ECS Fargate task (256 CPU, 512 MiB)
AI_API_URL (self-hosted llama3)   →  Amazon Bedrock Agent Core
                                     Supervisor + 3 collaborator agents
.env file                         →  AWS Secrets Manager
docker volumes                    →  EBS (EC2) + managed service storage
```

### 2.2 Network Architecture

```
VPC: 10.0.0.0/16 (ap-south-1)
├── Public Subnet A (10.0.1.0/24, ap-south-1a)
│   ├── ALB (internet-facing, ports 80/443)
│   └── NAT Gateway (for ECS outbound to threat feeds)
├── Public Subnet B (10.0.2.0/24, ap-south-1b)
│   └── ALB target (multi-AZ)
├── Private Subnet A (10.0.10.0/24, ap-south-1a)
│   ├── ECS Fargate tasks (ui, api, worker, scheduler)
│   ├── EC2 t3.medium (TimescaleDB)
│   └── ElastiCache Redis endpoint
├── Private Subnet B (10.0.20.0/24, ap-south-1b)
│   └── ECS Fargate tasks (multi-AZ redundancy)

Security Groups:
  sg-alb:        Inbound 80, 443 from 0.0.0.0/0
  sg-ecs:        Inbound 3000, 8000 from sg-alb
  sg-postgres:   Inbound 5432 from sg-ecs
  sg-redis:      Inbound 6379 from sg-ecs
  sg-opensearch: Inbound 9200 from sg-ecs
```

### 2.3 ALB Routing Rules

```
HTTPS:443 (ACM certificate for intelpulse.tech)
  ├── Path: /api/*     → Target Group: api-tg (port 8000)
  ├── Path: /*         → Target Group: ui-tg (port 3000)
  └── HTTP:80          → Redirect to HTTPS:443
```

### 2.4 Secrets Manager Structure

```json
{
  "secret_name": "intelpulse/production",
  "values": {
    "SECRET_KEY": "<generated-with-openssl-rand-hex-32>",
    "POSTGRES_HOST": "<ec2-private-ip>",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "ti_platform",
    "POSTGRES_USER": "ti",
    "POSTGRES_PASSWORD": "<new-strong-password>",
    "REDIS_URL": "redis://<elasticache-endpoint>:6379/0",
    "OPENSEARCH_URL": "https://<opensearch-domain-endpoint>",
    "GOOGLE_CLIENT_ID": "<new-for-intelpulse>",
    "GOOGLE_CLIENT_SECRET": "<new-for-intelpulse>",
    "DOMAIN": "intelpulse.tech",
    "DOMAIN_UI": "https://intelpulse.tech",
    "DOMAIN_API": "https://intelpulse.tech",
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO",
    "JWT_EXPIRE_MINUTES": "480",
    "NVD_API_KEY": "<same>",
    "ABUSEIPDB_API_KEY": "<same>",
    "OTX_API_KEY": "<same>",
    "VIRUSTOTAL_API_KEY": "<same>",
    "SHODAN_API_KEY": "<same>",
    "AWS_REGION": "ap-south-1",
    "BEDROCK_SUPERVISOR_AGENT_ID": "<created-in-phase-3>",
    "BEDROCK_SUPERVISOR_ALIAS_ID": "<created-in-phase-3>"
  }
}
```

Note: ElastiCache Redis with no AUTH for codethon simplicity, or use an AUTH token also stored here.

---

## 3. KIRO PROJECT SETUP

### 3.1 Steering Files to Create

Place these in `.kiro/steering/` after opening the project in KIRO IDE.

**File: `.kiro/steering/product.md`**
```markdown
---
inclusion: always
---

# IntelPulse — Threat Intelligence Platform

## Purpose
IntelPulse is a production-grade, self-hosted threat intelligence aggregation and analysis
platform. It collects IOCs from 13+ external threat feeds, normalizes them, scores risk,
and provides SOC analysts with searchable, enriched intelligence through a web dashboard.

## Target Users
- SOC analysts performing IOC triage and investigation
- Threat intelligence teams tracking campaigns and threat actors
- Security engineers integrating threat feeds into detection pipelines

## Key Features
1. Live threat feed aggregation (NVD, AbuseIPDB, OTX, VirusTotal, Shodan, etc.)
2. Full-text IOC search with severity/type/date filters
3. Live Internet Lookup — queries 12+ sources in real-time for any IOC
4. AI-powered analysis (structured summaries, risk scoring, MITRE ATT&CK mapping)
5. Cyber news feed with AI enrichment and relevance scoring
6. Analytics dashboards (severity distribution, geo view, source reliability)
7. Google OAuth + Email OTP authentication
8. Feed health monitoring with manual trigger capability
```

**File: `.kiro/steering/tech.md`**
```markdown
---
inclusion: always
---

# Technology Stack

## Backend
- Python 3.12, FastAPI (async), SQLAlchemy (async), Pydantic v2
- Python RQ (Redis Queue) for background jobs
- APScheduler for cron-like feed scheduling
- Ruff for linting (see ruff.toml)

## Frontend
- Next.js 14, TypeScript, Tailwind CSS
- Recharts for charts, Zustand for state management
- Server-side rendering with API proxy via BACKEND_URL

## Data Layer
- PostgreSQL 16 + TimescaleDB extension (hypertables for time-series IOC data)
- OpenSearch 2.13 (full-text IOC search, analytics aggregations)
- Redis 7 (session store for iw_session cookie, RQ job queue)

## Infrastructure (current)
- Docker Compose (7 services) on Hostinger VPS
- Caddy 2 for reverse proxy + auto HTTPS
- Domain: IntelPulse.in (legacy)

## Infrastructure (AWS migration)
- Rebranded as IntelPulse
- Domain: intelpulse.tech

## Infrastructure (target — AWS codethon)
- ECS Fargate for 4 app services
- EC2 t3.medium for PostgreSQL+TimescaleDB (RDS lacks TimescaleDB support)
- AWS OpenSearch Service (managed)
- ElastiCache Redis 7 (managed)
- ALB + ACM for HTTPS, Route 53 for DNS
- Secrets Manager for env vars, ECR for container images
- Amazon Bedrock Agent Core for AI layer (replaces llama3)

## Conventions
- All Dockerfiles are in docker/
- DB init script: db/schema.sql
- API routes under api/routes/, services under api/services/
- Worker tasks under worker/
- Frontend pages under ui/src/app/(app)/
```

**File: `.kiro/steering/aws-migration.md`**
```markdown
---
inclusion: always
---

# AWS Migration Rules

## Codethon Requirements
This migration MUST demonstrably use these AWS services:
1. KIRO IDE — specs, steering files, hooks, agentic chat for all development
2. Amazon Q Developer — security scans, inline code suggestions
3. Amazon Bedrock Agent Core — multi-agent system for IOC analysis
4. AWS Transform — modernization assessment of Python/Node.js code

## Architecture Decisions
- Region: ap-south-1 (Mumbai) — lowest latency from Bengaluru
- TimescaleDB runs on EC2 (NOT RDS) because RDS lacks the extension
- New brand: IntelPulse on intelpulse.tech (separate from IntelPulse production)
- Caddy is replaced by ALB + ACM — remove caddy service from AWS deployment
- No data migration needed — seed fresh data via POST /feeds/trigger-all
- Google OAuth: create new OAuth client for intelpulse.tech

## Code Changes Scope
ONLY these files need modification:
- api/services/ai.py → Replace HTTP calls to AI_API_URL with boto3 Bedrock adapter
- api/routes/search.py → Add POST /search/agent-lookup using Bedrock Agent Runtime
- ui/src/app/(app)/search/page.tsx → Add "AI Agent Analysis" button + result display
- .env.example → Add AWS_REGION, BEDROCK_SUPERVISOR_AGENT_ID, BEDROCK_SUPERVISOR_ALIAS_ID

NEW files to create:
- infra/ → CDK stack (VPC, ECS, ALB, data services, IAM roles)
- api/services/bedrock_agents.py → Multi-agent invocation code
- infra/lambdas/ → Action group Lambda functions for Bedrock agents
- .github/workflows/deploy-aws.yml → ECR build + ECS deploy pipeline

## DO NOT Change
- docker-compose.yml — must still work for local dev
- Existing API routes/signatures — only ADD new endpoints
- Authentication flow — keep Google OAuth + OTP as-is
- Frontend design system — keep existing Tailwind + Recharts styling

## Branding Changes
- All "IntelPulse" references → "IntelPulse"
- Domain: IntelPulse.in → intelpulse.tech
- Logo/favicon: Update with IntelPulse branding
- Page titles, meta tags, documentation
```

**File: `.kiro/steering/coding-standards.md`**
```markdown
---
inclusion: always
---

# Coding Standards

## Python (backend)
- Use ruff for linting (config in ruff.toml)
- Type hints on all function signatures
- Async functions for all database/network operations
- Pydantic v2 models for request/response schemas
- Error handling: raise HTTPException with appropriate status codes

## TypeScript (frontend)
- Strict TypeScript — no `any` types
- React Server Components where possible (Next.js 14 app router)
- Zustand for client state, SWR or fetch for server state
- Tailwind CSS only — no inline styles or CSS modules

## Infrastructure
- CDK (TypeScript) preferred over raw CloudFormation
- All IAM roles follow least-privilege principle
- Tag all AWS resources: Project=IntelPulse, Environment=codethon
- Use Secrets Manager references in ECS task definitions, never hardcode

## Git
- Branch: aws-codethon (off main)
- Commit messages: conventional commits (feat:, fix:, infra:, docs:)
- PR back to main only after codethon submission
```

### 3.2 Agent Hooks to Create

**File: `.kiro/hooks/test-sync.kiro.hook`**
```json
{
  "name": "Test Sync",
  "description": "Auto-generates or updates tests when Python files are saved",
  "version": "1",
  "when": {
    "type": "fileSaved",
    "patterns": ["api/**/*.py", "worker/**/*.py"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Check if tests exist for the saved file. If not, generate pytest tests following existing patterns in api/tests/. If tests exist, update them to cover any new or changed functions. Use async test patterns with httpx.AsyncClient for API route tests."
  }
}
```

**File: `.kiro/hooks/doc-update.kiro.hook`**
```json
{
  "name": "Documentation Update",
  "description": "Updates API docs when route files change",
  "version": "1",
  "when": {
    "type": "fileSaved",
    "patterns": ["api/routes/**/*.py"]
  },
  "then": {
    "type": "askAgent",
    "prompt": "Check if the API route changes affect the documentation in docs/. If new endpoints were added, update the API Reference section in README.md. Keep the existing table format."
  }
}
```

**File: `.kiro/hooks/security-scan.kiro.hook`**
```json
{
  "name": "Security Validation",
  "description": "Pre-commit security scan",
  "version": "1",
  "when": {
    "type": "manual"
  },
  "then": {
    "type": "askAgent",
    "prompt": "Scan the codebase for: 1) Hardcoded credentials or API keys in source files, 2) SQL injection risks in database queries, 3) Missing input validation on API endpoints, 4) Unsafe eval() or exec() usage, 5) CORS misconfigurations. Report issues by severity (CRITICAL/HIGH/MEDIUM/LOW) with file locations and fix suggestions."
  }
}
```

---

## 4. IMPLEMENTATION PHASES — KIRO SPEC TASK SEQUENCE

Use these as the basis for your KIRO spec. When you create a spec in KIRO, you can reference this document for the requirements → design → tasks flow.

### Phase 1: AWS Infrastructure (Tasks 1–6)

**Task 1: Create CDK project scaffold**
```
Create infra/ directory with a CDK TypeScript project.
Stack name: IntelPulseStack
Include constructs for: VPC, ECS cluster, ALB, ECR repositories.
Tags: Project=IntelPulse, Environment=production
Region: ap-south-1
```

**Task 2: VPC + networking**
```
CDK construct: IntelPulseVpc
- VPC 10.0.0.0/16, 2 AZs (ap-south-1a, ap-south-1b)
- 2 public subnets (for ALB + NAT Gateway)
- 2 private subnets (for ECS + data tier)
- 1 NAT Gateway (single, cost savings for codethon)
- Security groups: sg-alb, sg-ecs, sg-postgres, sg-redis, sg-opensearch
  with rules as specified in section 2.2
```

**Task 3: Data tier — EC2 for TimescaleDB**
```
CDK construct: IntelPulseDatabase
- EC2 t3.medium in private subnet
- Amazon Linux 2023 AMI
- User data script to install Docker and run:
  docker run -d --name timescaledb \
    -e POSTGRES_USER=ti \
    -e POSTGRES_PASSWORD=$DB_PASSWORD \
    -e POSTGRES_DB=ti_platform \
    -v /data/postgres:/var/lib/postgresql/data \
    -p 5432:5432 \
    timescale/timescaledb:latest-pg16
- EBS gp3 volume (50 GB) mounted at /data/postgres
- Copy db/schema.sql to EC2 and run as init
- Security group: sg-postgres (inbound 5432 from sg-ecs only)
```

**Task 4: Data tier — managed services**
```
CDK constructs: IntelPulseCache, IntelPulseSearch
- ElastiCache Redis 7: cache.t3.micro, single-node, private subnet
  No AUTH for codethon simplicity (or use AUTH token in Secrets Manager)
- OpenSearch Service: t3.small.search, single-node
  Engine version 2.13, no fine-grained access control
  VPC access (private subnet), security group sg-opensearch
```

**Task 5: ECR repositories + image build script**
```
Create 3 ECR repositories:
- intelpulse/api
- intelpulse/ui
- intelpulse/worker (shared by worker + scheduler)

Create scripts/ecr-push.sh:
  - Login to ECR
  - Build each image using existing Dockerfiles in docker/
  - Tag with git SHA and 'latest'
  - Push to ECR
```

**Task 6: ECS Fargate cluster + services**
```
CDK construct: IntelPulseEcs
- ECS cluster: intelpulse-production
- 4 Fargate services, each with task definition:

  intelpulse-api:
    Image: ECR intelpulse/api:latest
    CPU: 512, Memory: 1024
    Port: 8000
    Health check: /api/v1/health
    Environment: from Secrets Manager ARN
    IAM role: allow bedrock:InvokeModel, bedrock:InvokeAgent,
              secretsmanager:GetSecretValue

  intelpulse-ui:
    Image: ECR intelpulse/ui:latest
    CPU: 256, Memory: 512
    Port: 3000
    Environment: BACKEND_URL=http://intelpulse-api.local:8000
    (Use Cloud Map for service discovery, or ALB internal URL)

  intelpulse-worker:
    Image: ECR intelpulse/worker:latest
    CPU: 256, Memory: 512
    No port mapping
    Environment: from Secrets Manager ARN

  intelpulse-scheduler:
    Image: ECR intelpulse/worker:latest
    CPU: 256, Memory: 512
    Command override: ["python", "-m", "worker.scheduler"]
    Environment: from Secrets Manager ARN

- ALB: internet-facing, HTTPS:443
  ACM certificate for intelpulse.tech
  Listener rules:
    /api/* → api target group (port 8000)
    /* → ui target group (port 3000)
```

### Phase 2: Bedrock Agent Core (Tasks 7–12)

**Task 7: Create Bedrock adapter — replace llama3**
```
File: api/services/bedrock_adapter.py

Create a drop-in replacement for the existing AI HTTP calls:

import boto3, json

bedrock_runtime = boto3.client("bedrock-runtime", region_name="ap-south-1")

async def ai_analyze(prompt: str, system: str = "", model: str = "anthropic.claude-3-5-haiku-20241022") -> str:
    messages = [{"role": "user", "content": prompt}]
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2048,
        "messages": messages
    }
    if system:
        body["system"] = system
    response = bedrock_runtime.invoke_model(modelId=model, body=json.dumps(body))
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]

async def ai_analyze_structured(prompt: str, system: str = "") -> dict:
    """Returns parsed JSON from AI response"""
    text = await ai_analyze(prompt, system)
    # Parse JSON from response, handle code blocks
    ...

Update api/services/ai.py to import and use bedrock_adapter instead of HTTP calls.
Detect which backend to use via env var: if AI_API_URL is "bedrock" or empty, use Bedrock.
This ensures docker-compose local dev still works with the old llama3 endpoint.
```

**Task 8: Create Lambda action groups for Bedrock agents**
```
Directory: infra/lambdas/

Lambda 1: virustotal_lookup/handler.py
  - Input: {"ioc": "...", "ioc_type": "ip|domain|hash|url"}
  - Calls VT API v3: /api/v3/ip_addresses/{ip}, /api/v3/domains/{domain}, etc.
  - Returns: {"detections": N, "total_engines": M, "malicious": bool, "details": {...}}
  - API key from Secrets Manager

Lambda 2: abuseipdb_check/handler.py
  - Input: {"ip": "..."}
  - Calls AbuseIPDB /api/v2/check
  - Returns: {"abuse_confidence": N, "total_reports": N, "country": "...", "isp": "..."}

Lambda 3: otx_lookup/handler.py
  - Input: {"ioc": "...", "ioc_type": "..."}
  - Calls OTX DirectConnect API
  - Returns: {"pulses": [...], "related_indicators": [...]}

Lambda 4: shodan_lookup/handler.py
  - Input: {"ip": "..."}
  - Calls Shodan /shodan/host/{ip}
  - Returns: {"ports": [...], "vulns": [...], "org": "...", "os": "..."}

Each Lambda:
  - Runtime: Python 3.12
  - Timeout: 30s
  - Memory: 256 MB
  - VPC: NOT in VPC (needs internet access to external APIs)
  - IAM: secretsmanager:GetSecretValue for API keys
```

**Task 9: Create Bedrock agents**
```
File: infra/bedrock_agents.py (or CDK construct)

Agent 1 — Supervisor: "IntelPulse Threat Analyst"
  Model: anthropic.claude-3-5-sonnet-20241022
  Instruction: |
    You are IntelPulse Threat Analyst, a supervisor agent for threat intelligence analysis.
    When given an IOC (IP address, domain name, URL, or file hash):
    1. Identify the IOC type
    2. Delegate to IOC Reputation Analyst for detection data
    3. Delegate to Threat Context Enricher for MITRE ATT&CK mapping
    4. Delegate to Risk Scorer for final severity assessment
    5. Synthesize all results into a structured JSON report:
       {
         "ioc": "...",
         "ioc_type": "...",
         "risk_score": 0-100,
         "severity": "critical|high|medium|low|info",
         "confidence": 0-100,
         "detections": {...},
         "mitre_techniques": [...],
         "threat_actors": [...],
         "recommended_actions": [...],
         "agent_trace": [...]
       }
  Collaboration: SUPERVISOR

Agent 2 — Collaborator: "IOC Reputation Analyst"
  Model: anthropic.claude-3-5-haiku-20241022
  Instruction: |
    You analyze IOC reputation using threat intelligence databases.
    Use your action groups to query VirusTotal, AbuseIPDB, OTX, and Shodan.
    Synthesize results into a reputation assessment with detection counts,
    malicious verdicts, first-seen dates, and associated malware families.
  Collaboration: COLLABORATOR
  Action Groups: virustotal_lookup, abuseipdb_check, otx_lookup, shodan_lookup

Agent 3 — Collaborator: "Threat Context Enricher"
  Model: anthropic.claude-3-5-haiku-20241022
  Instruction: |
    You provide threat context and MITRE ATT&CK mapping for IOCs.
    Map indicators to known techniques, tactics, and procedures.
    Identify associated threat actors, campaigns, and APT groups.
    Provide geolocation and network attribution for IP-based IOCs.
  Collaboration: COLLABORATOR
  Knowledge Base: MITRE ATT&CK STIX bundle (upload enterprise-attack.json to S3,
                  create Bedrock Knowledge Base with OpenSearch Serverless)

Agent 4 — Collaborator: "Risk Scorer"
  Model: anthropic.claude-3-5-haiku-20241022
  Instruction: |
    You produce final risk assessments for threat intelligence IOCs.
    Given reputation data and threat context from other analysts:
    1. Calculate risk score (0-100) based on detection ratio, source diversity, recency
    2. Determine severity level using IntelPulse scale:
       - critical (80-100): active exploitation, multiple detections
       - high (60-79): confirmed malicious, limited detections
       - medium (40-59): suspicious, needs investigation
       - low (20-39): minor concern, monitor
       - info (0-19): clean or insufficient data
    3. Set confidence (0-100) based on source agreement and data freshness
    4. Generate 3-5 prioritized recommended actions for SOC analysts
  Collaboration: COLLABORATOR

Associate all 3 collaborators with the supervisor agent.
Create agent aliases for deployment.
```

**Task 10: Create agent invocation service**
```
File: api/services/bedrock_agents.py

import boto3
from uuid import uuid4

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name="ap-south-1")

SUPERVISOR_AGENT_ID = os.getenv("BEDROCK_SUPERVISOR_AGENT_ID")
SUPERVISOR_ALIAS_ID = os.getenv("BEDROCK_SUPERVISOR_ALIAS_ID")

async def invoke_threat_analysis(ioc: str, ioc_type: str) -> dict:
    """Invoke the multi-agent supervisor for IOC analysis"""
    response = bedrock_agent_runtime.invoke_agent(
        agentId=SUPERVISOR_AGENT_ID,
        agentAliasId=SUPERVISOR_ALIAS_ID,
        sessionId=str(uuid4()),
        inputText=f"Analyze this {ioc_type} IOC: {ioc}. "
                  f"Query all available threat intelligence sources and provide "
                  f"a comprehensive risk assessment."
    )
    
    # Parse streaming response
    result_text = ""
    for event in response["completion"]:
        if "chunk" in event:
            result_text += event["chunk"]["bytes"].decode("utf-8")
    
    # Parse JSON from agent response
    return parse_agent_response(result_text)
```

**Task 11: Add agent-lookup API endpoint**
```
File: api/routes/search.py — ADD new endpoint (don't modify existing)

from api.services.bedrock_agents import invoke_threat_analysis

@router.post("/search/agent-lookup")
async def agent_lookup(request: AgentLookupRequest):
    """Multi-agent IOC analysis using Bedrock Agent Core"""
    try:
        result = await invoke_threat_analysis(
            ioc=request.ioc,
            ioc_type=request.ioc_type
        )
        return {
            "status": "success",
            "analysis": result,
            "engine": "bedrock-multi-agent"
        }
    except Exception as e:
        # Fallback to direct Bedrock call (non-agent)
        from api.services.bedrock_adapter import ai_analyze_structured
        fallback = await ai_analyze_structured(
            f"Analyze this {request.ioc_type}: {request.ioc}",
            system="You are a threat intelligence analyst..."
        )
        return {
            "status": "fallback",
            "analysis": fallback,
            "engine": "bedrock-direct"
        }
```

**Task 12: Update search UI for agent analysis**
```
File: ui/src/app/(app)/search/page.tsx

Add an "AI Agent Analysis" button alongside existing "Live Internet Lookup".
When clicked:
  - Call POST /api/v1/search/agent-lookup with the current IOC
  - Show loading state with "Analyzing with multi-agent system..."
  - Display results in a structured card:
    - Risk score gauge (0-100, color-coded)
    - Severity badge (critical/high/medium/low/info)
    - Confidence percentage
    - MITRE ATT&CK technique chips (clickable, link to attack.mitre.org)
    - Agent trace timeline (which agents were invoked, in what order)
    - Recommended actions list
  - Use existing Tailwind + Recharts design patterns from the dashboard
```

### Phase 3: AWS Transform + CI/CD (Tasks 13–16)

**Task 13: Run AWS Transform assessment**
```
Use atx CLI (AWS Transform custom) in KIRO terminal:

# For Python backend
atx
> "Assess and upgrade Python dependencies in the api/ directory.
   Modernize FastAPI patterns, update SQLAlchemy async usage,
   ensure Pydantic v2 best practices, upgrade any deprecated imports."

# For Node.js frontend  
atx
> "Assess and upgrade Node.js dependencies in the ui/ directory.
   Update Next.js to latest stable, modernize TypeScript patterns,
   upgrade Tailwind CSS configuration."

Capture the transformation plan and report for codethon submission.
Apply recommended changes if they don't break existing functionality.
```

**Task 14: Amazon Q security scan**
```
In KIRO with Amazon Q Developer extension:
1. Open command palette → "Amazon Q: Run Security Scan"
2. Review all findings
3. Fix CRITICAL and HIGH severity issues
4. Document findings and fixes for submission
```

**Task 15: GitHub Actions CI/CD**
```
File: .github/workflows/deploy-aws.yml

Trigger: push to aws-codethon branch
Steps:
  1. Checkout code
  2. Configure AWS credentials (from GitHub secrets)
  3. Login to ECR
  4. Build 3 Docker images (api, ui, worker) with git SHA tag
  5. Push to ECR
  6. Update ECS services with force-new-deployment
  7. Wait for services to stabilize
  8. Run smoke test: curl health endpoint
```

**Task 16: DNS + OAuth setup**
```
Manual steps (not automatable):
1. Route 53: Create hosted zone for intelpulse.tech
   Add A record → ALB DNS name (alias)
2. ACM: Request certificate for intelpulse.tech
   DNS validation via Route 53
3. Google Cloud Console: Create new OAuth client for IntelPulse
   Add https://intelpulse.tech/api/v1/auth/google/callback as authorized redirect URI
4. Update Secrets Manager with final domain values
```

---

## 5. DEPLOYMENT CHECKLIST

```
□ CDK deployed (VPC, ALB, ECS, ECR, data services)
□ EC2 TimescaleDB running with schema initialized
□ ElastiCache Redis endpoint reachable from ECS
□ OpenSearch domain active and healthy
□ Secrets Manager populated with all env vars
□ ECR images pushed (api, ui, worker)
□ ECS services running (all 4 tasks healthy)
□ ALB routing working (/ → UI, /api/* → API)
□ ACM certificate active for codethon.IntelPulse.in
□ Route 53 A record pointing to ALB
□ Google OAuth redirect URI added
□ Health check passing: GET /api/v1/health returns all true
□ Bedrock agents created and aliases deployed
□ Lambda action groups functional
□ Agent lookup endpoint working: POST /api/v1/search/agent-lookup
□ Feed ingestion triggered: POST /api/v1/feeds/trigger-all
□ Dashboard populating with real data
□ Amazon Q security scan completed
□ AWS Transform assessment saved
□ GitHub Actions pipeline deploying on push
```

---

## 6. DEMO SCRIPT (3–5 minutes)

1. **Problem statement** (30s): "IntelPulse is a threat intelligence platform running on a VPS. I'm migrating it to AWS and adding multi-agent AI analysis using only KIRO, Amazon Q, Bedrock Agent Core, and AWS Transform."

2. **KIRO specs** (30s): Show `.kiro/specs/` — requirements.md, design.md, tasks.md. "KIRO's spec-driven development gave me a structured migration plan before writing a single line of code."

3. **Architecture walkthrough** (45s): Quick tour of ECS console — 4 running tasks, ALB, OpenSearch domain, ElastiCache. "Same 7-service architecture, now on managed AWS infrastructure."

4. **Star demo — multi-agent IOC analysis** (90s): 
   - Open IntelPulse search page
   - Enter a known malicious IP (e.g., 185.220.101.x — Tor exit node)
   - Click "AI Agent Analysis"
   - Show the supervisor agent routing to IOC Reputation (VT + AbuseIPDB results), Threat Context (MITRE mapping), Risk Scorer (final assessment)
   - Highlight the agent trace showing orchestration flow

5. **Amazon Q + Transform** (30s): Show Q security scan results. Show Transform modernization report.

6. **Close** (15s): "Theme 3 — Intelligent Multi-Agent Domain Solutions applied to cybersecurity threat intelligence, built entirely with KIRO, Bedrock, Q, and Transform."
