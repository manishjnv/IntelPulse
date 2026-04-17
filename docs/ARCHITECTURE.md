# IntelPulse — Technical Architecture

## Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions

---

## System Overview

IntelPulse is a production-grade threat intelligence platform that aggregates IOCs from 13+ external feeds, enriches them with AI analysis via Amazon Bedrock, and provides SOC analysts with searchable, actionable intelligence through a web dashboard. The platform was developed entirely using KIRO IDE and Amazon Q Developer.

## Architecture Diagram

```text
┌─────────────────────────────────────────────────────────────────┐
│                        Users / SOC Analysts                      │
│                    https://intelpulse.tech                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS (Caddy + Let's Encrypt)
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                    EC2 Instance (t3.small)                        │
│                    3.87.235.189 / us-east-1                       │
│                                                                   │
│  ┌───────────────────┐          ┌─────────────────────┐          │
│  │  Next.js UI :3000 │          │  FastAPI API :8000  │          │
│  │  TypeScript        │  ◄────► │  Python 3.12        │          │
│  │  Tailwind CSS      │          │  Async + Pydantic   │          │
│  │  Recharts + Zustand│          │  Bedrock Adapter    │          │
│  └───────────────────┘          │  + Agent Adapter    │          │
│            ▲                     └────────┬──────────-┘          │
│            │                              │                      │
│            │  Caddy :443 (TLS)            │                      │
│            │                              │                      │
│  ┌────────────────────────────────────────┼──────────────────┐   │
│  │              Docker Compose Services    │                  │   │
│  │  ┌──────────────────┐  ┌──────────────┐│                  │   │
│  │  │  PostgreSQL 16    │  │   Redis 7    ││                  │   │
│  │  │  + TimescaleDB    │  │  Sessions    ││                  │   │
│  │  │  (time-series DB) │  │  Cache, RQ   ││                  │   │
│  │  └──────────────────┘  └──────────────┘│                  │   │
│  └────────────────────────────────────────┘                  │   │
└───────────────────────────────────────────┼──────────────────────┘
                                            │ boto3 SDK (IMDS)
                                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        AWS Services                               │
│                                                                   │
│  ┌────────────────────────┐  ┌────────────────────────────────┐  │
│  │  Amazon Bedrock         │  │   IAM                          │  │
│  │  Runtime: Nova / Titan /│  │   BedrockAccessRole            │  │
│  │  Anthropic (invoke_model│  │   (least-privilege policies)   │  │
│  │  ) + Meta / Mistral /   │  │                                │  │
│  │  DeepSeek / Cohere /    │  │   IntelPulse-BedrockAgentRole  │  │
│  │  AI21 (Converse API)    │  │   (service principal)          │  │
│  │                         │  │                                │  │
│  │  Agents:                │  │   intelpulse-virustotal-lookup │  │
│  │  - Threat-Analyst       │  │   -role (Lambda exec)          │  │
│  │  - IOC-Analyst          │  │                                │  │
│  │  - Risk-Scorer          │  │                                │  │
│  │                         │  │                                │  │
│  │  Action Groups:         │  │                                │  │
│  │  - virustotal_lookup    │  │                                │  │
│  │    (AWS Lambda)         │  │                                │  │
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
| AI | Amazon Bedrock (Nova Lite + Bedrock Agents) | Threat analysis, IOC enrichment, multi-agent orchestration |
| Infra | Docker Compose on EC2 | Container orchestration |
| IaC | AWS CDK (TypeScript) | Infrastructure as Code |
| Dev Tools | KIRO IDE, KIRO CLI, Amazon Q Developer | AI-driven, spec-to-production development |

## AWS Services Integration

### Amazon Bedrock

The platform uses Amazon Bedrock for AI-powered threat analysis via two
complementary paths:

1. **Single-shot with tiered routing** — the default for most features. A
   `BedrockAdapter` dispatches `invoke_model` (Nova / Titan / Anthropic) or
   the unified **Converse API** (Meta Llama / Mistral / DeepSeek / Cohere /
   AI21). The model used is picked per feature via `model_<feature>` columns
   in `ai_settings` — see [Tiered routing §](#tiered-model-routing) below.
2. **Multi-agent Supervisor** — opt-in for news enrichment
   (`AI_USE_AGENTS=true`), on-by-default for IOC live lookup
   (`AI_USE_AGENTS_FOR_IOC=true`). A Supervisor agent routes to collaborators
   (IOC-Analyst with a VirusTotal action group, Risk-Scorer).

Authentication: IAM role on the EC2 instance (`BedrockAccessRole`) with
`bedrock:InvokeAgent` + `bedrock:InvokeModel` via IMDS. No long-lived keys.

Public endpoints:

- `POST https://intelpulse.tech/api/v1/demo/analyze` — IOC threat analysis
- `GET https://intelpulse.tech/api/v1/demo/health` — Bedrock health check
- `GET https://intelpulse.tech/api/v1/ai-settings/pipeline` — live routing matrix

> **Note**: Anthropic Claude models (`anthropic.claude-*`) return
> `INVALID_PAYMENT_INSTRUMENT` on this AWS account. The adapter still
> supports the Anthropic family — swap `primary_model` if a different
> account has Marketplace access.

### Tiered model routing

Each feature is mapped to one of four tiers. Defaults are empirically
verified via [`scripts/probe_bedrock_models.py`](../scripts/probe_bedrock_models.py).

| Tier | Features | Default model | Why |
| ---- | -------- | ------------- | --- |
| Classifier | `news_enrichment`, `intel_summary`, `kql_generation` | `us.meta.llama4-scout-17b-instruct-v1:0` | Fast, MoE, clean JSON; ~400 ms p50. |
| Correlator | `intel_enrichment`, `live_lookup` | `amazon.nova-pro-v1:0` | Native Bedrock Agent support + action-group tool calling. |
| Narrative | `briefing_gen`, `report_gen` | `mistral.mistral-large-2402-v1:0` | Best prose; quality over speed. |
| Fallback | auto-retry on refusal | `us.meta.llama3-3-70b-instruct-v1:0` | Permissive on cybersec content. |

Seed on a fresh environment:

```bash
ssh intelpulse2 "docker cp /opt/IntelPulse/scripts/. intelpulse-api-1:/tmp/scripts/ \
  && docker exec intelpulse-api-1 python /tmp/scripts/apply_tiered_model_routing.py"
```

### Bedrock Adapter Architecture

```text
API Request → BedrockAdapter.ai_analyze(model_id=<tier>)
                     │
                     ├──►  _model_family_for(model_id) → family dispatch
                     │
                     ├──►  Nova / Titan / Anthropic  → invoke_model
                     │
                     └──►  Meta / Mistral / DeepSeek → converse
                           / Cohere / AI21
                                    │
                                    ▼
                             Structured JSON Response
                             (risk_score, severity, MITRE techniques)
```

The single-shot adapter supports:

- Text generation (`ai_analyze`) — with per-call `model_id` override for tiered routing
- Structured JSON generation (`ai_analyze_structured`)
- Health checks (`check_health`)
- Automatic response parsing with markdown fence stripping
- DeepSeek R1 `<think>` trace stripping

### Multi-Agent Design

**LIVE as of 2026-04-17 (commit 6b768a6).** The platform provisions and routes through a supervisor-router + collaborator pattern using Bedrock Agents.

#### Live Agent Catalog

| Agent | Agent ID | Alias ID | Foundation Model | Mode |
| ----- | -------- | -------- | ---------------- | ---- |
| **IntelPulse-Threat-Analyst** (Supervisor) | `FQBSERZQMP` | `HLSRFAFL42` (`live-v2`) | `amazon.nova-lite-v1:0` | `SUPERVISOR_ROUTER` |
| **IOC-Analyst** | `UX0RYONP98` | `SFDO1GO27Y` (`live`) | `amazon.nova-lite-v1:0` | Collaborator |
| **Risk-Scorer** | `WH4N4SUKMB` | `BP6KQNKDUB` (`live`) | `amazon.nova-lite-v1:0` | Collaborator |

Collaborator wiring: Supervisor → IOC-Analyst (`TO_COLLABORATOR`), Supervisor → Risk-Scorer (`TO_COLLABORATOR`).

**Deferred (follow-up PR):** Threat Context Enricher (requires Bedrock Knowledge Base + MITRE ATT&CK data upload to S3).

#### Lambda Action Groups (Live)

| Lambda | Action Group | Status |
|--------|-------------|--------|
| `intelpulse-virustotal-lookup` | `virustotal_lookup` on IOC-Analyst | **LIVE** — Python 3.12, stdlib urllib only; stub mode active (no API key yet) |
| `abuseipdb_check` | — | Coded in `infra/lambdas/` but **not deployed** |
| `otx_lookup` | — | Coded in `infra/lambdas/` but **not deployed** |
| `shodan_lookup` | — | Coded in `infra/lambdas/` but **not deployed** |

IAM role for the live Lambda: `intelpulse-virustotal-lookup-role` (Lambda trust + CloudWatch Logs + `secretsmanager:GetSecretValue` on `intelpulse/virustotal`).

CloudWatch log group: `/aws/lambda/intelpulse-virustotal-lookup` (14-day retention).

#### News Enrichment Flow

```mermaid
sequenceDiagram
    participant W as enrich_news_batch<br/>(RQ worker)
    participant A as BedrockAgentAdapter
    participant BR as bedrock-agent-runtime<br/>InvokeAgent
    participant SUP as Supervisor<br/>FQBSERZQMP/HLSRFAFL42
    participant IOC as IOC-Analyst<br/>UX0RYONP98/SFDO1GO27Y
    participant LMB as Lambda<br/>intelpulse-virustotal-lookup
    participant SM as Secrets Manager<br/>intelpulse/virustotal

    W->>A: ai_analyze_structured_via_agent(prompt, required_keys)
    A->>BR: InvokeAgent(agentId=FQBSERZQMP, agentAliasId=HLSRFAFL42)
    BR->>SUP: route prompt
    SUP->>IOC: delegate (TO_COLLABORATOR)
    IOC->>LMB: invoke action group virustotal_lookup.lookup_ioc
    LMB->>SM: GetSecretValue (VIRUSTOTAL_API_KEY)
    SM-->>LMB: key (or empty → stub mode)
    LMB-->>IOC: stub/real reputation data
    IOC-->>SUP: structured IOC assessment
    SUP-->>BR: final completion (EventStream)
    BR-->>A: EventStream chunks
    A->>A: strip markdown fences, parse JSON,<br/>validate required_keys
    A-->>W: dict with enrichment fields
    W->>W: write fields to news_items table
```

#### Concrete Smoke-Test Results

Direct invoke to IOC-Analyst `live` — prompt `"Analyze IOC 8.8.8.8"`:
- 1 action group invocation (`virustotal_lookup.lookup_ioc`)
- Stub reputation data returned from Lambda
- Agent produced: `{"ioc": "8.8.8.8", "ioc_type": "ip", "reputation": "...", ...}`

Supervisor `live-v2` — prompt `"Check IP 185.220.101.45 in VirusTotal"`:
- 1 action group invocation through collaboration tree
- Final output: structured JSON with `reputation: malicious`

#### Known Caveats

- **Output cap**: Agent inference config caps output at 1024 tokens. The full 30-field news-enrichment JSON may truncate; only `category`, `summary`, and `executive_brief` are strictly required. Bumping to 4096 requires overriding the full agent prompt template — deferred.
- **Nova content filter**: Refuses approximately 20% of threat-intel content. Failed items are retried by the `re_enrich_fallback_news` scheduled task.
- **Latency**: Agent path is 3–5x slower than single-shot `invoke_model`.
- **Cost**: Roughly 5–8x per article (1 supervisor call + 1–2 collaborator rounds + up to 1 Lambda action-group call).

#### Enabling the Agent Path

The agent path is off by default (`AI_USE_AGENTS=false`). To enable on EC2:

```bash
echo 'AI_USE_AGENTS=true' >> /home/ubuntu/IntelPulse/.env
docker compose -f /home/ubuntu/IntelPulse/docker-compose.yml restart worker scheduler
# Verify:
docker logs intelpulse-worker-1 --tail 200 | grep bedrock_invoke_agent_request
```

See [`docs/MULTI_AGENT.md`](MULTI_AGENT.md) for the full deep-dive reference.

## Data Flow

### 1. Feed Ingestion Pipeline

```text
External Feed → Feed Connector → Normalize → Score → Store (PostgreSQL)
                                                    → Index (search)
```

12 feed connectors fetch data from external sources, normalize it into a common schema, calculate risk scores, and store in PostgreSQL with TimescaleDB hypertables.

### 2. AI Enrichment Pipeline

```text
IOC/News Item → resolve_bedrock_model(feature) → BedrockAdapter / AgentAdapter
                                                  → Tier model (Llama 4 Scout,
                                                    Nova Pro, Mistral Large,
                                                    Llama 3.3 70B)
                                                  → Structured Analysis
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

- **BedrockAccessRole** (EC2 instance profile): `bedrock:InvokeModel`, `bedrock:Converse`, `bedrock-agent-runtime:InvokeAgent`.
- **IntelPulse-BedrockAgentRole** (Bedrock service principal): scoped to the three agent ARNs + `lambda:InvokeFunction` for the `virustotal_lookup` action group.
- **intelpulse-virustotal-lookup-role** (Lambda exec role): `secretsmanager:GetSecretValue` on `intelpulse/virustotal` + CloudWatch Logs write.
- **MarketplaceAccess**: would be needed for Anthropic Claude — currently blocked on this account, so unused.

### Network Security

- Caddy (public :443) terminates TLS with Let's Encrypt and reverse-proxies to the UI (:3000) and API (:8000).
- Security groups expose only 22 (SSH restricted) and 443 (public HTTPS).
- UI :3000 and API :8000 are firewalled from the internet — reachable only via the Caddy reverse proxy.
- Docker network isolation between services.
- Redis password authentication.
- PostgreSQL password authentication.

## Deployment Architecture

### Current (EC2 Demo)

```text
EC2 Instance (t3.small, us-east-1)
├── Docker Compose (8 services)
│   ├── Caddy (:443, TLS, reverse proxy)
│   ├── Next.js UI (:3000, internal)
│   ├── FastAPI API (:8000, internal)
│   ├── Worker (RQ, Python)
│   ├── Scheduler (APScheduler)
│   ├── PostgreSQL + TimescaleDB (:5432)
│   ├── Redis 7 (:6379)
│   └── OpenSearch 2 (:9200)
└── IAM Role: BedrockAccessRole
    ├── Amazon Bedrock (Nova / Meta / Mistral / DeepSeek — tiered routing)
    └── Amazon Bedrock Agents (Supervisor + IOC-Analyst + Risk-Scorer)
        └── AWS Lambda: virustotal_lookup
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

## AI-Driven Development — KIRO + Amazon Q Developer

**KIRO + Q → Build faster.** Spec-driven, end-to-end software delivery.

| Tool | Role |
|------|------|
| **KIRO IDE** | Specs → guided → autonomous (autopilot) development with multi-file coordination and production focus |
| **KIRO CLI** | Automates tasks, infra (IaC), CI/CD, and AWS operations via natural language |
| **Amazon Q Developer** | AI coding, debugging, security scans, docs, and smart code suggestions inside IDEs |

IntelPulse was designed and built end-to-end with this toolchain. KIRO's spec-driven workflow (requirements → design → tasks → autopilot implementation) produced the application and infra code; Amazon Q Developer provided inline suggestions, security scanning, and the boto3/Bedrock code transformations; KIRO CLI drove natural-language AWS operations — Bedrock agent provisioning, Lambda action-group wiring, and CI/CD configuration.

### KIRO IDE Workflow

#### Spec-Driven Development

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

Public endpoints (HTTPS via Caddy + Let's Encrypt). The raw EC2 ports
(`:3000`, `:8000`) are firewalled from the internet.

| Access | URL |
| ------ | --- |
| UI Dashboard | <https://intelpulse.tech/dashboard> |
| Threat Feed | <https://intelpulse.tech/threats> |
| Cyber News | <https://intelpulse.tech/news> |
| Threat Briefings | <https://intelpulse.tech/briefings> |
| Settings → AI Configuration | <https://intelpulse.tech/settings?section=ai> |
| API Documentation | <https://intelpulse.tech/api/docs> |
| API Root | <https://intelpulse.tech/api> |
| Demo Health | <https://intelpulse.tech/api/v1/demo/health> |
| Demo Analysis | `POST https://intelpulse.tech/api/v1/demo/analyze` |
| Pipeline JSON | <https://intelpulse.tech/api/v1/ai-settings/pipeline> |
