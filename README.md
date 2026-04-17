# IntelPulse — Threat Intelligence Platform

> **Wipro × AWS Codeathon** | Theme 3: Intelligent Multi-Agent Domain Solutions
>
> An AI-powered Threat Intelligence Platform built with **Amazon Bedrock**, **KIRO IDE**, and **Amazon Q Developer** — demonstrating multi-agent orchestration for cybersecurity.

![AWS](https://img.shields.io/badge/Amazon_Bedrock-FF9900?style=flat&logo=amazonaws&logoColor=white)
![KIRO](https://img.shields.io/badge/KIRO_IDE-232F3E?style=flat&logo=amazonaws&logoColor=white)
![Q](https://img.shields.io/badge/Amazon_Q_Developer-232F3E?style=flat&logo=amazonaws&logoColor=white)
![Stack](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Stack](https://img.shields.io/badge/Next.js_14-000000?style=flat&logo=next.js&logoColor=white)
![Stack](https://img.shields.io/badge/PostgreSQL-4169E1?style=flat&logo=postgresql&logoColor=white)
![Stack](https://img.shields.io/badge/TimescaleDB-FDB515?style=flat&logo=timescale&logoColor=black)
![Stack](https://img.shields.io/badge/Redis-DC382D?style=flat&logo=redis&logoColor=white)
![Stack](https://img.shields.io/badge/AWS_CDK-FF9900?style=flat&logo=amazonaws&logoColor=white)

---

## Live Demo

| Access | URL |
|--------|-----|
| Application (Dashboard) | <http://3.87.235.189:3000> |
| API Documentation (Swagger) | <http://3.87.235.189:8000/api/docs> |
| Bedrock Health Check | <http://3.87.235.189:8000/api/v1/demo/health> |
| Source Code | <https://github.com/manishjnv/IntelPulse> (branch: `aws-migration`) |

---

## What IntelPulse Does

IntelPulse is a production-grade Threat Intelligence Platform that:

1. **Aggregates** IOCs (Indicators of Compromise) from 13+ external threat feeds in real time
2. **Analyzes** threats using Amazon Bedrock multi-agent AI — risk scoring, MITRE ATT&CK mapping, structured summaries
3. **Enriches** cyber news with AI-extracted threat actors, CVEs, techniques, and relevance scores
4. **Provides** SOC analysts with searchable, actionable intelligence through a web dashboard

---

> ### **NEW — Multi-agent Bedrock enrichment is live**
>
> News enrichment can now route through a **three-agent Bedrock collaboration** — a Supervisor (`SUPERVISOR_ROUTER` mode) that delegates to an IOC Reputation Analyst and a Risk Scorer, and which invokes a real AWS Lambda action group (`virustotal_lookup`) to pull VirusTotal reputation data. The whole chain runs on `amazon.nova-lite-v1:0`.
>
> **What it does differently vs. the single-shot path:**
> - The Supervisor **plans** which specialist to involve per article instead of one-shot prompting
> - The IOC-Analyst **uses a tool** — it calls the VirusTotal Lambda via a Bedrock action group and reasons over the returned reputation payload
> - Multiple agents **collaborate** — their outputs are aggregated by the Supervisor before the final structured JSON is returned
>
> **How to enable** (opt-in per environment; off by default):
> ```bash
> ssh intelpulse2 "echo 'AI_USE_AGENTS=true' >> /home/ubuntu/IntelPulse/.env && \
>                  cd /home/ubuntu/IntelPulse && docker compose restart worker scheduler"
> # Verify it's routing through agents:
> ssh intelpulse2 "docker logs intelpulse-worker-1 --tail 200 | grep bedrock_invoke_agent_request"
> ```
>
> See **[docs/MULTI_AGENT.md](docs/MULTI_AGENT.md)** for the deep-dive — agent catalog, action-group contract, request flow, cost/latency, failure modes, rollback.

---

## AWS Services Utilized

| AWS Service | How It's Used |
|-------------|---------------|
| **Amazon Bedrock Agents** | Supervisor + specialist collaboration — `SUPERVISOR_ROUTER` mode with `TO_COLLABORATOR` wiring. 3 agents live (Threat-Analyst, IOC-Analyst, Risk-Scorer); a 4th (Context Enricher with MITRE KB) is scoped for follow-up. |
| **Amazon Bedrock Agent Runtime** | `invoke_agent` EventStream, consumed synchronously by the worker for news enrichment. Trace events surface action-group and collaborator invocations for observability. |
| **Amazon Bedrock (Runtime)** | Single-shot `invoke_model` on `amazon.nova-lite-v1:0` for IOC demo, health checks, reports, and intel enrichment. Anthropic models are blocked on this account (`INVALID_PAYMENT_INSTRUMENT`), so Nova is the production model. |
| **AWS Lambda** | `intelpulse-virustotal-lookup` (Python 3.12, stdlib urllib — no pip deps). Dual event shape: legacy `{ioc, ioc_type}` for direct invoke + Bedrock action-group envelope. |
| **AWS Secrets Manager** | `intelpulse/virustotal` — stores the VirusTotal API key; Lambda falls back to deterministic stub data when the secret is empty so the agent flow is demo-ready from day one. |
| **Amazon CloudWatch Logs** | `/aws/lambda/intelpulse-virustotal-lookup` with 14-day retention; Bedrock Agent traces are also emitted for debugging collaborator + action-group invocations. |
| **AWS IAM** | `BedrockAccessRole` (EC2 instance profile) + `intelpulse-virustotal-lookup-role` (Lambda exec) + `IntelPulse-BedrockAgentRole` (agent service principal). Least-privilege policies. |
| **AWS CDK** | `bedrock-agents-construct.ts` + `bedrock-lambdas-construct.ts` describe the infra. Agents + Lambda were provisioned programmatically via [`infra/scripts/provision_bedrock_action_group.py`](infra/scripts/provision_bedrock_action_group.py) using boto3 (idempotent). |
| **KIRO IDE** | Specs → guided → autonomous (autopilot) development with multi-file coordination and production focus. 4 steering files for consistent context; 3 agent hooks for automation. |
| **KIRO CLI** | Automates tasks, infra (IaC), CI/CD, and AWS operations via natural language. Drove provisioning of the Bedrock agents + the VirusTotal Lambda action group. |
| **Amazon Q Developer** | AI coding, debugging, security scans, docs, and smart code suggestions inside IDEs. Security scanning fixed 12 issues; drove HTTP-to-boto3 Bedrock transformation. |
| **EC2** | Application hosting (t3.small, us-east-1) with instance profile for IMDS-based AWS credentials — no long-lived secrets on the box. |

---

## Multi-Agent Architecture (Amazon Bedrock)

IntelPulse uses a supervisor-led multi-agent pattern for comprehensive IOC analysis:

```text
                    ┌─────────────────────────┐
                    │   SOC Analyst Request    │
                    │   "Analyze 45.142.212.61"│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      SUPERVISOR          │
                    │  IntelPulse Threat       │
                    │  Analyst Agent           │
                    │  (Orchestrates analysis) │
                    └──┬─────────┬─────────┬──┘
                       │         │         │
          ┌────────────▼──┐  ┌──▼────────┐ │  ┌──────────────┐
          │ IOC Reputation │  │ Threat    │ └─►│ Risk Scorer  │
          │ Analyst        │  │ Context   │    │              │
          │                │  │ Enricher  │    │ Aggregates   │
          │ Queries:       │  │           │    │ findings →   │
          │ • VirusTotal   │  │ Maps to   │    │ risk score   │
          │ • AbuseIPDB    │  │ MITRE     │    │ (0-100)      │
          │ • OTX          │  │ ATT&CK    │    │              │
          │ • Shodan       │  │ framework │    │ Severity:    │
          │ (via Lambda)   │  │           │    │ CRITICAL/    │
          └────────────────┘  └───────────┘    │ HIGH/MED/LOW │
                                                └──────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Structured Response    │
                    │   • Risk Score: 85/100   │
                    │   • Severity: HIGH       │
                    │   • MITRE: T1566, T1059  │
                    │   • Actions: Block, Log  │
                    │   • Analysis: Summary    │
                    └─────────────────────────┘
```

### Agent Responsibilities

| Agent | What It Does | Inputs | Outputs |
|-------|-------------|--------|---------|
| **Supervisor** (IntelPulse Threat Analyst) | Orchestrates the full analysis workflow, delegates to specialists, aggregates results | IOC value + type | Complete threat assessment |
| **IOC Reputation Analyst** | Queries external threat intelligence sources for reputation data | IOC value | Reputation scores, blocklist status, abuse reports |
| **Threat Context Enricher** | Maps findings to MITRE ATT&CK framework, identifies TTPs | Reputation data | Technique IDs, tactic categories, campaign context |
| **Risk Scorer** | Aggregates all findings into a quantified risk assessment | All agent outputs | Risk score (0-100), severity level, confidence % |

### Orchestration Logic

- **Task Routing**: Supervisor receives IOC → delegates to all three specialist agents in parallel
- **Collaboration**: IOC Reputation Analyst feeds results to Threat Context Enricher for MITRE mapping
- **Aggregation**: Risk Scorer combines all outputs into a single structured assessment
- **Error Handling**: If any agent fails, Supervisor returns partial results with confidence adjustment

### Lambda Action Groups

| Lambda | Data Source | Returns |
|--------|------------|---------|
| `virustotal_lookup` | VirusTotal API | Detection ratio, community score, scan results |
| `abuseipdb_check` | AbuseIPDB | Abuse confidence score, report count, categories |
| `otx_lookup` | AlienVault OTX | Pulse count, related indicators, tags |
| `shodan_lookup` | Shodan | Open ports, services, vulnerabilities, ISP info |

---

## Tiered Bedrock Model Routing

Instead of serving every AI call from one model, IntelPulse routes each agent
role to the Bedrock model best suited for the job. The adapter in
[api/app/services/bedrock_adapter.py](api/app/services/bedrock_adapter.py)
dispatches across the Amazon Nova (`invoke_model`), Anthropic Claude
(`invoke_model`), Titan (`invoke_model`), and Meta Llama / Mistral / DeepSeek /
Cohere / AI21 families (Bedrock **Converse API**) from one interface.

| Tier | Role | Default Model | Why |
| ---- | ---- | ------------- | --- |
| **Classifier** | `news_enrichment`, `intel_summary`, `kql_generation` | `us.meta.llama4-scout-17b-instruct-v1:0` | High-volume, fast, MoE — cheapest path for category + CVE extraction. |
| **Correlator** | `intel_enrichment`, `live_lookup` | `amazon.nova-pro-v1:0` | Native Bedrock Agent support + VirusTotal action-group tool calling; strict JSON. |
| **Narrative** | `briefing_gen`, `report_gen` | `mistral.mistral-large-2402-v1:0` | Best prose for weekly briefings and executive reports — low volume, quality-over-speed. |
| **Fallback** | auto-retry when primary refuses | `us.meta.llama3-3-70b-instruct-v1:0` | Permissive on cybersec content; 497 ms in benchmark. |

All four models are **empirically verified** — see
[scripts/probe_bedrock_models.py](scripts/probe_bedrock_models.py). The probe
runs inside `intelpulse-api-1` with the `BedrockAccessRole` IAM role, tests
each candidate with a cybersec JSON-extraction prompt, and produces a matrix
of latency / JSON-mode / content-filter behaviour.

**How the routing is wired.** Each call site (e.g. `chat_completion_json` in
[api/app/services/ai.py](api/app/services/ai.py)) passes a `caller` and optional
`feature`. `resolve_bedrock_model(feature, caller)` looks up
`model_<feature>` in the `ai_settings` Postgres row; if present, it's passed
into the Bedrock adapter as a per-call `model_id` override. If empty, the
adapter falls back to the globally-configured `primary_model` (currently
`amazon.nova-lite-v1:0`).

**Surface this in the UI.** Settings → AI Configuration → **Tiered Routing**
shows all four tiers as editable cards — change a tier's model and it
propagates to every feature in that tier. The "Apply Recommended to All"
button fills every tier with the empirically-verified default.

**Seed the defaults on a fresh environment:**

```bash
ssh intelpulse2 \
  "docker cp /opt/IntelPulse/scripts/. intelpulse-api-1:/tmp/scripts/ \
   && docker exec intelpulse-api-1 python /tmp/scripts/apply_tiered_model_routing.py"
```

The script is idempotent — only fills in empty `model_<feature>` columns
unless `--force` is passed.

**Why Claude is blocked.** Every Anthropic model on this Bedrock account
returns `INVALID_PAYMENT_INSTRUMENT`. The adapter still supports the
`anthropic` family (via `invoke_model`) — it's just not reachable on
production without an AWS Marketplace fix.

---

## AI-Powered Features

Every major feature in IntelPulse is backed by Amazon Bedrock AI:

| Feature | AI Role | How Bedrock Is Used |
|---------|---------|---------------------|
| **IOC Threat Analysis** | Risk assessment for any IP, domain, hash, or URL | Bedrock analyzes IOC context, assigns risk score, maps to MITRE ATT&CK |
| **Cyber News Enrichment** | Extracts structured intelligence from news articles | Bedrock identifies threat actors, CVEs, techniques, assigns relevance scores |
| **Live Internet Lookup** | Real-time multi-source IOC investigation | Bedrock synthesizes results from 12+ sources into actionable summary |
| **Report Generation** | Automated Threat Intelligence reports | Bedrock generates executive summaries, technical details, recommendations |
| **Detection Rules** | Auto-generated YARA, KQL, Sigma rules | Bedrock creates detection signatures from threat intelligence |
| **Intel Summaries** | Structured summaries for high-risk items | Bedrock produces analyst-ready summaries with key findings |

### Demo Endpoint

```bash
curl -X POST http://3.87.235.189:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "45.142.212.61", "ioc_type": "ip"}'
```

---

## Platform Features

| Feature | Description |
|---------|-------------|
| **13+ Threat Feed Sources** | NVD, CISA KEV, AbuseIPDB, VirusTotal, Shodan, OTX, ThreatFox, URLhaus, MalwareBazaar, MITRE ATT&CK, ExploitDB |
| **19 Cyber News RSS Sources** | The Hacker News, Krebs on Security, Dark Reading, BleepingComputer, Mandiant, CISA Alerts |
| **Full-Text IOC Search** | Search by IP, domain, hash, URL with severity/type/date filters |
| **Live Internet Lookup** | Real-time queries to 12+ sources for any IOC |
| **Analytics Dashboard** | Severity distribution, geo view, source reliability, trend charts |
| **Case Management** | Incident response, investigation, and threat hunting workflows |
| **MITRE ATT&CK Mapping** | 803 techniques with automated intel-technique linking |
| **Detection Rules** | Auto-generated YARA, KQL, Sigma rules from Threat Intelligence |

---

## AI-Driven Development — KIRO + Amazon Q Developer

> **KIRO + Q → Build faster** — spec-driven, end-to-end software delivery.

| Tool | Role |
|------|------|
| **KIRO IDE** | Specs → guided → autonomous (autopilot) development with multi-file coordination and production focus |
| **KIRO CLI** | Automates tasks, infra (IaC), CI/CD, and AWS operations via natural language |
| **Amazon Q Developer** | AI coding, debugging, security scans, docs, and smart code suggestions inside IDEs |

IntelPulse was designed and built end-to-end with this toolchain: KIRO's spec-driven workflow (requirements → design → tasks → autopilot implementation) plus Amazon Q Developer for inline code assistance, security scanning, and AWS-aware suggestions. KIRO CLI drove AWS operations — Bedrock agent provisioning, Lambda action-group wiring, and CI/CD configuration — via natural-language commands.

### KIRO IDE — Spec-Driven Workflow

### Specs

- **Requirements**: 12 functional requirements covering infrastructure, Bedrock, and CI/CD
- **Design**: 1,320-line design document with architecture diagrams, interfaces, pseudocode
- **Tasks**: 15 implementation tasks with acceptance criteria

### Steering Files

| File | Purpose |
|------|---------|
| `tech.md` | Technology stack reference |
| `product.md` | Threat Intelligence Platform context for SOC analysts |
| `coding-standards.md` | Code quality rules (ruff, strict TypeScript, CDK conventions) |
| `aws-migration.md` | AWS-specific rules (region, services, scope) |

### Agent Hooks

| Hook | Trigger | Action |
|------|---------|--------|
| `security-scan` | User-triggered | Scans for hardcoded credentials, SQL injection, CORS misconfig |
| `doc-update` | File edited | Reminds to update documentation when code changes |
| `test-sync` | File edited | Ensures tests stay in sync with implementation |

---

## Productivity Metrics

| Metric | Traditional | With KIRO + Q | Savings |
|--------|------------|---------------|---------|
| Total development time | 70 hours | 17 hours | **76%** |
| Requirement-to-code | 2 hours | 15 minutes | **88%** |
| Debugging per issue | 30 minutes | 5 minutes | **83%** |
| New API endpoint | 45 minutes | 10 minutes | **78%** |
| Security issues found | Post-review | Real-time | **12 issues caught** |
| Lines generated/modified | — | 5,850 | With KIRO + Q |

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                    SOC Analysts / Users                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  EC2 Instance (us-east-1)                     │
│  ┌──────────────────┐     ┌──────────────────┐               │
│  │ Next.js UI :3000 │◄──►│ FastAPI API :8000 │               │
│  └──────────────────┘     └────────┬─────────┘               │
│  ┌──────────────┐  ┌──────────────┐│                         │
│  │ PostgreSQL 16│  │   Redis 7    ││                         │
│  │ + TimescaleDB│  │ Sessions, RQ ││                         │
│  └──────────────┘  └──────────────┘│                         │
└─────────────────────────────────────┼────────────────────────┘
              ┌───────────────────────┼───────────────────────┐
              │         Amazon Bedrock + Lambda                │
              │  ┌─────────────────────────────┐              │
              │  │  Supervisor Agent (Claude 3) │              │
              │  └──────┬──────┬──────┬────────┘              │
              │  ┌──────▼┐ ┌──▼────┐ ┌▼───────┐              │
              │  │VT     │ │Abuse  │ │OTX/    │              │
              │  │Lookup  │ │IPDB   │ │Shodan  │              │
              │  └───────┘ └───────┘ └────────┘              │
              └────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse && git checkout aws-migration
cp .env.example .env
docker compose up -d --build

# Test Bedrock AI analysis
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}'
```

---

## Repository Structure

```text
IntelPulse/
├── .kiro/                        # KIRO IDE (specs, steering, hooks)
├── api/                          # FastAPI backend
│   ├── app/routes/demo.py        # Bedrock AI demo endpoint
│   ├── app/services/bedrock_adapter.py  # Amazon Bedrock integration
│   └── app/services/             # Feed connectors, scoring, enrichment
├── ui/                           # Next.js 14 frontend
├── infra/                        # AWS CDK + Lambda action groups
├── db/                           # Database schema
├── docker/                       # Dockerfiles
└── docs/                         # Documentation
```

---

## Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working Application | ✅ | <http://3.87.235.189:3000> |
| Source Code Repository | ✅ | <https://github.com/manishjnv/IntelPulse> |
| Amazon Q Usage Report | ✅ | `docs/AMAZON_Q_USAGE_REPORT.md` |
| Productivity Metrics | ✅ | `docs/PRODUCTIVITY_METRICS.md` |
| Technical Documentation | ✅ | `docs/ARCHITECTURE.md` |
| Demo Video | 📹 | `docs/DEMO_VIDEO_SCRIPT.md` |

---

**Author**: Manish Kumar — <manishjnvk@gmail.com>
**Challenge**: Wipro × AWS Codeathon | Theme 3: Intelligent Multi-Agent Domain Solutions
