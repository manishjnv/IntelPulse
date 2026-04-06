# Amazon Q Developer & KIRO IDE Usage Report

## Author: Manish Kumar (<manishjnvk@gmail.com>)

## Project: IntelPulse — Threat Intelligence Platform

## Challenge: Wipro × AWS Codeathon — Theme 3: Intelligent Multi-Agent Domain Solutions

---

## 1. KIRO IDE — Spec-Driven Development

### Specs Created

- **AWS Infrastructure Migration Spec** (`.kiro/specs/aws-infrastructure-migration/`)
  - `requirements.md` — 12 functional requirements covering VPC, ECS, Bedrock, CI/CD
  - `design.md` — 1,320-line comprehensive design document with:
    - Mermaid architecture diagrams (system, network, multi-agent)
    - Component interfaces with TypeScript/Python type definitions
    - Data models with validation rules
    - Algorithmic pseudocode with formal pre/post conditions
    - 4 detailed usage examples
  - `tasks.md` — 15 implementation tasks with acceptance criteria

### Steering Files (`.kiro/steering/`)

| File | Purpose |
|------|---------|
| `tech.md` | Technology stack reference (Python, FastAPI, Next.js, AWS services) |
| `product.md` | Product context (threat intel platform, SOC analysts, key features) |
| `coding-standards.md` | Code quality rules (ruff, strict TypeScript, CDK conventions) |
| `aws-migration.md` | Migration-specific rules (region, services, scope, branding) |

### Hooks (`.kiro/hooks/`)

| Hook | Trigger | Action |
|------|---------|--------|
| `security-scan` | User-triggered | Scans for hardcoded credentials, SQL injection, CORS misconfig |
| `doc-update` | File edited | Reminds to update documentation when code changes |
| `test-sync` | File edited | Ensures tests stay in sync with implementation |

### KIRO Autopilot Usage

- Used autopilot mode for multi-file code generation across:
  - CDK infrastructure stack (VPC, ECS, ALB, data services)
  - Bedrock adapter with Nova/Claude model support
  - Lambda action group handlers
  - API route modifications for demo mode
  - Auth middleware bypass for demo deployment
- Autopilot coordinated changes across 15+ files simultaneously

---

## 2. Amazon Q Developer — AI-Assisted Coding

### Inline Code Suggestions

- **Bedrock Adapter** (`api/app/services/bedrock_adapter.py`): Q suggested the Nova message format structure and response parsing logic
- **CDK Stack** (`infra/lib/intelpulse-stack.ts`): Q auto-completed security group rules, ECS task definitions, and ALB routing configuration
- **Lambda Handlers** (`infra/lambdas/`): Q generated boilerplate for VirusTotal, AbuseIPDB, OTX, and Shodan API integrations
- **Auth Middleware** (`api/app/middleware/auth.py`): Q suggested demo mode bypass pattern with user auto-creation

### Code Debugging

- Resolved asyncpg PostgreSQL enum casting issues (asset_type enum)
- Fixed SQLAlchemy async session management for feed ingestion
- Debugged Bedrock Nova vs Claude message format differences
- Identified and fixed CORS configuration for Cloudflare proxy

### Security Scanning

- Identified hardcoded credentials in early development
- Flagged missing input validation on API endpoints
- Recommended CORS tightening for production deployment
- Suggested Secrets Manager integration for API keys

### Code Transformation

- Migrated AI service from HTTP-based llama3 calls to boto3 Bedrock Runtime
- Adapted Bedrock adapter to support both Claude (Anthropic) and Amazon Nova message formats
- Converted synchronous worker tasks to support async database operations

---

## 3. Amazon Bedrock Agent Core

### Model Integration

- **Amazon Nova Lite** (`amazon.nova-lite-v1:0`) — Primary AI model for:
  - News article enrichment (threat actors, CVEs, MITRE techniques, risk scores)
  - Intel item AI summaries
  - Report content generation
  - IOC analysis

### Bedrock Adapter Architecture

- Unified adapter supporting both Claude and Nova models
- Automatic request/response format detection based on model ID
- Structured JSON parsing with markdown fence stripping
- Health check endpoint for monitoring

### Multi-Agent Design (Documented in Spec)

- **Supervisor Agent**: IntelPulse Threat Analyst (orchestrates analysis)
- **IOC Reputation Analyst**: Queries VirusTotal, AbuseIPDB, OTX, Shodan via Lambda
- **Threat Context Enricher**: Maps to MITRE ATT&CK knowledge base
- **Risk Scorer**: Aggregates findings into risk assessment

### Lambda Action Groups (Implemented)

- `virustotal_lookup` — IOC reputation check
- `abuseipdb_check` — IP abuse scoring
- `otx_lookup` — AlienVault OTX pulse search
- `shodan_lookup` — Internet exposure scan

---

## 4. AWS Transform — Legacy Modernization

### Assessment Performed

- Analyzed existing Docker Compose deployment (7 services on VPS)
- Identified modernization targets:
  - Caddy → ALB + ACM (managed HTTPS)
  - Self-hosted Redis → ElastiCache (managed)
  - Self-hosted OpenSearch → AWS OpenSearch Service (managed)
  - Self-hosted AI (llama3) → Amazon Bedrock (serverless)
  - Manual deployment → ECS Fargate (container orchestration)
  - No CI/CD → GitHub Actions + ECR (automated pipeline)

### Code Transformation

- Python API: Added boto3 Bedrock integration alongside existing HTTP AI calls
- Worker: Maintained backward compatibility with local development
- Infrastructure: Created CDK TypeScript stack from Docker Compose definitions
- Domain: Migrated from intelwatch.in → intelpulse.tech

---

## 5. Key Q Developer Interactions

### Example 1: Bedrock Nova Model Support

```
Prompt: "Update the Bedrock adapter to support Amazon Nova models alongside Claude"
Result: Q generated the _is_nova property, _build_request_body() with Nova message format,
        and _extract_text() for Nova response parsing — all in one suggestion
```

### Example 2: CDK Security Groups

```
Prompt: "Create least-privilege security groups for ECS, PostgreSQL, Redis, OpenSearch"
Result: Q generated 5 security groups with proper ingress rules allowing only
        necessary inter-service communication
```

### Example 3: Demo Mode Authentication

```
Prompt: "Add demo mode that bypasses authentication for codethon reviewers"
Result: Q suggested the demo_mode config flag, auto-user creation in auth middleware,
        and session endpoint modification — maintaining security for production
```

### Example 4: Feed Ingestion Pipeline

```
Prompt: "Create a feed ingestion script that stores data without OpenSearch dependency"
Result: Q generated the populate_intel.py script with proper dedup, scoring,
        and PostgreSQL-only storage path
```
