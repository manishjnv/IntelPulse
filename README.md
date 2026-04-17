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

Public HTTPS endpoints (Caddy + Let's Encrypt, no login required — demo mode):

| Access | URL |
| ------ | --- |
| Application (Dashboard) | <https://intelpulse.tech/dashboard> |
| Threat Feed | <https://intelpulse.tech/threats> |
| Cyber News | <https://intelpulse.tech/news> |
| Threat Briefings | <https://intelpulse.tech/briefings> |
| Settings → AI Configuration | <https://intelpulse.tech/settings?section=ai> |
| API Documentation (Swagger) | <https://intelpulse.tech/api/docs> |
| Bedrock Health Check | <https://intelpulse.tech/api/v1/demo/health> |
| Multi-Agent Pipeline (JSON) | <https://intelpulse.tech/api/v1/ai-settings/pipeline> |
| Source Code | <https://github.com/manishjnv/IntelPulse> (branch: `main`) |

> The raw EC2 IP endpoints (`http://3.87.235.189:3000` / `:8000`) are **no
> longer public** — Caddy fronts everything through `intelpulse.tech` with
> TLS. Use the HTTPS URLs above.

---

## What IntelPulse Does

IntelPulse is a production-grade Threat Intelligence Platform that:

1. **Aggregates** IOCs (Indicators of Compromise) from 13+ external threat feeds in real time
2. **Analyzes** threats using Amazon Bedrock multi-agent AI — risk scoring, MITRE ATT&CK mapping, structured summaries
3. **Enriches** cyber news with AI-extracted threat actors, CVEs, techniques, and relevance scores
4. **Provides** SOC analysts with searchable, actionable intelligence through a web dashboard

---

> ### **Multi-agent Bedrock enrichment + tiered routing — live**
>
> IntelPulse routes AI work through two complementary layers:
>
> 1. **Tiered single-shot routing** (on by default). Each feature is mapped
>    to a specific Bedrock model empirically picked for its role — Classifier
>    (Llama 4 Scout 17B), Correlator (Nova Pro), Narrative (Mistral Large),
>    Fallback (Llama 3.3 70B). See the [Tiered Bedrock Model Routing
>    section](#tiered-bedrock-model-routing) below and Settings → AI
>    Configuration → Tiered Routing.
>
> 2. **Three-agent Bedrock collaboration**. A Supervisor (`SUPERVISOR_ROUTER`
>    mode) delegates to an IOC Reputation Analyst and a Risk Scorer, and
>    invokes a real AWS Lambda action group (`virustotal_lookup`) for
>    IOC enrichment. `AI_USE_AGENTS_FOR_IOC=true` by default; `AI_USE_AGENTS`
>    (news enrichment via agents) is opt-in.
>
> **What the agent path does differently:**
>
> - The Supervisor **plans** which specialist to involve per article.
> - The IOC-Analyst **uses a tool** — calls the VirusTotal Lambda via a
>   Bedrock action group and reasons over the returned reputation payload.
> - Agents **collaborate** — their outputs are aggregated by the Supervisor
>   before the final structured JSON is returned.
>
> **Enable news-enrichment agent path** (opt-in; off by default):
> ```bash
> ssh intelpulse2 "echo 'AI_USE_AGENTS=true' >> /home/ubuntu/IntelPulse/.env && \
>                  cd /home/ubuntu/IntelPulse && docker compose restart worker scheduler"
> # Verify:
> ssh intelpulse2 "docker logs intelpulse-worker-1 --tail 200 | grep bedrock_invoke_agent_request"
> ```
>
> See **[docs/MULTI_AGENT.md](docs/MULTI_AGENT.md)** for the deep-dive.

---

## AWS Services Utilized

| AWS Service | How It's Used |
|-------------|---------------|
| **Amazon Bedrock Agents** | Supervisor + specialist collaboration — `SUPERVISOR_ROUTER` mode with `TO_COLLABORATOR` wiring. 3 agents live (Threat-Analyst, IOC-Analyst, Risk-Scorer); a 4th (Context Enricher with MITRE KB) is scoped for follow-up. |
| **Amazon Bedrock Agent Runtime** | `invoke_agent` EventStream, consumed synchronously by the worker for news enrichment. Trace events surface action-group and collaborator invocations for observability. |
| **Amazon Bedrock (Runtime)** | Multi-model runtime. Adapter dispatches Nova / Titan / Anthropic via `invoke_model`, and Meta Llama / Mistral / DeepSeek / Cohere / AI21 via the unified **Converse API**. Tiered routing (see below) picks the model per feature. Anthropic models blocked on this account (`INVALID_PAYMENT_INSTRUMENT`). |
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

IntelPulse runs two complementary AI paths. Each feature picks the one that
fits its latency / quality / tool-use profile. Both share the same Bedrock
adapter, so swapping a tier's model is a single DB update.

```text
 ┌──────────────────────────────────────────────────────────────────────────┐
 │                        IntelPulse call sites                              │
 │ (worker, API routes — chat_completion_json with caller + feature hints)   │
 └───────────────────────────────┬──────────────────────────────────────────┘
                                 │
                     resolve_bedrock_model(feature, caller)
                     reads model_<feature> from ai_settings
                                 │
              ┌──────────────────┴────────────────────┐
              │                                        │
    ┌─────────▼──────────┐                 ┌──────────▼──────────────────┐
    │ SINGLE-SHOT PATH   │                 │  MULTI-AGENT PATH           │
    │ (tiered routing)   │                 │  (SUPERVISOR_ROUTER)        │
    │                    │                 │                             │
    │ invoke_model /     │                 │  invoke_agent EventStream   │
    │ converse per-call  │                 │  Supervisor → Collaborators │
    │                    │                 │  + VirusTotal action group  │
    └─────────┬──────────┘                 └──────────┬──────────────────┘
              │                                        │
      ┌───────┼────────┬──────────┐             ┌────┴───────────────┐
      ▼       ▼        ▼          ▼             ▼                    ▼
 ┌────────┐ ┌────┐ ┌────────┐ ┌────────┐   ┌──────────────┐  ┌──────────────┐
 │Classif │ │Cor │ │Narrat  │ │Fallback│   │ IntelPulse-  │  │ IntelPulse-  │
 │Llama 4 │ │Nova│ │Mistral │ │Llama3.3│   │ Threat-      │  │ IOC-Analyst  │
 │Scout   │ │Pro │ │Large   │ │70B     │   │ Analyst      │  │ (tool caller │
 │17B MoE │ │    │ │2402    │ │        │   │ (supervisor) │  │  → VT Lambda)│
 └────────┘ └────┘ └────────┘ └────────┘   └──────┬───────┘  └──────────────┘
     │                                             │                 │
     └────── news_enrichment, intel_summary,       └─► routes to ────┘
             briefing_gen, report_gen, …              collaborators
                                                      │         │
                                         ┌────────────▼──┐ ┌───▼────────────┐
                                         │IntelPulse-    │ │VirusTotal      │
                                         │Risk-Scorer    │ │Action Group    │
                                         │(PREPARED)     │ │(Lambda)        │
                                         └───────────────┘ └────────────────┘
```

### When each path runs

| Feature | Path (today) | Flag | Default model(s) |
| ------- | ------------ | ---- | ---------------- |
| News enrichment | single-shot (tiered) | `AI_USE_AGENTS=false` | Classifier tier — Llama 4 Scout |
| IOC live lookup | agent + single-shot fallback | `AI_USE_AGENTS_FOR_IOC=true` | Supervisor + IOC-Analyst (Nova Pro via agent) |
| Intel summary / enrichment | single-shot (tiered) | — | Classifier / Correlator tier |
| Briefing + report generation | single-shot (tiered) | — | Narrative tier — Mistral Large |
| KQL / Sigma rule generation | single-shot (tiered) | — | Classifier tier |

The live `/api/v1/ai-settings/pipeline` endpoint (also rendered inside
Settings → AI Configuration) returns this mapping at runtime so operators
can see exactly what model a given feature invokes.

### Agent Responsibilities (multi-agent path)

| Agent | What It Does | Inputs | Outputs |
|-------|-------------|--------|---------|
| **Supervisor** (`IntelPulse-Threat-Analyst`, `FQBSERZQMP`) | Orchestrates the full analysis workflow, delegates to specialists, aggregates results. | IOC value + type | Complete threat assessment (JSON) |
| **IOC Reputation Analyst** (`IntelPulse-IOC-Analyst`, `UX8RYONP98`) | Uses the `virustotal_lookup` action group to pull reputation data and reasons over it. | IOC value | Reputation scores, blocklist status, community votes |
| **Risk Scorer** (`IntelPulse-Risk-Scorer`, `WH4N4SUKMB`) | Aggregates all findings into a quantified risk assessment. | Agent outputs | Risk score (0-100), severity, confidence % |

All three agents are in the `PREPARED` state on prod (verified live via the
Multi-Agent Pipeline panel). Status + alias IDs are pulled from the Bedrock
control plane every 60 s and cached in Redis.

### Orchestration Logic

- **Task Routing** — Supervisor receives an IOC, delegates to the IOC Analyst and Risk Scorer. Collaboration uses `TO_COLLABORATOR` wiring with `SUPERVISOR_ROUTER` mode.
- **Tool Use** — IOC Analyst invokes the `virustotal_lookup` Bedrock action group (Lambda). The agent parses the returned JSON and factors it into its reasoning.
- **Aggregation** — Risk Scorer combines all outputs into a single structured assessment with severity + confidence fields.
- **Error Handling** — If an action group or collaborator fails, the Supervisor returns a partial result with confidence adjusted downward. The worker still raises on total failure so RQ's failed-job registry catches it (per `rca_rq_tasks_must_raise`).

### Lambda Action Groups

| Lambda | Data Source | State | Returns |
| ------ | ----------- | ----- | ------- |
| `virustotal_lookup` | VirusTotal API v3 | Live / `ENABLED` | Detection ratio, community score, scan results, vendor votes |
| `abuseipdb_check` | AbuseIPDB | Planned | Abuse confidence score, report count, categories |
| `otx_lookup` | AlienVault OTX | Planned | Pulse count, related indicators, tags |
| `shodan_lookup` | Shodan | Planned | Open ports, services, vulnerabilities, ISP info |

The VirusTotal Lambda is stdlib-only (Python 3.12, `urllib`) and dual-shaped —
accepts both the legacy `{ioc, ioc_type}` payload for direct invoke and the
Bedrock action-group envelope. CDK in `infra/lib/bedrock-*.ts`; one-shot
provisioning in [`infra/scripts/provision_bedrock_action_group.py`](infra/scripts/provision_bedrock_action_group.py).

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
