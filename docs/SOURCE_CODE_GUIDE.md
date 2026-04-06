# Source Code Repository Guide

## Author: Manish Kumar (<manishjnvk@gmail.com>)

## Repository: <https://github.com/manishjnv/IntelPulse>

## Branch: aws-migration

---

## Repository Structure

```
IntelPulse/
│
├── .kiro/                          # KIRO IDE Configuration
│   ├── specs/                      # Spec-driven development
│   │   └── aws-infrastructure-migration/
│   │       ├── requirements.md     # 12 functional requirements
│   │       ├── design.md           # 1,320-line design document
│   │       └── tasks.md            # 15 implementation tasks
│   ├── steering/                   # Context steering files
│   │   ├── tech.md                 # Technology stack reference
│   │   ├── product.md              # Product context & features
│   │   ├── coding-standards.md     # Code quality rules
│   │   └── aws-migration.md        # AWS migration rules
│   └── hooks/                      # Automation hooks
│       ├── security-scan.kiro.hook         # Scans for hardcoded secrets
│       ├── doc-update.kiro.hook            # Keeps docs in sync
│       ├── test-sync.kiro.hook             # Tests stay in sync
│       ├── lint-on-save.kiro.hook          # Ruff linter on save
│       └── verify-task-completion.kiro.hook # Post-task verification
│
├── api/                            # Backend (Python 3.12, FastAPI)
│   ├── app/
│   │   ├── core/                   # Configuration, database, logging, Redis
│   │   │   ├── config.py           # Pydantic settings with validation
│   │   │   ├── database.py         # Async SQLAlchemy engine
│   │   │   ├── redis.py            # Redis cache client
│   │   │   └── opensearch.py       # OpenSearch client
│   │   ├── routes/                 # API endpoints
│   │   │   ├── auth.py             # Google OAuth + OTP + demo mode
│   │   │   ├── dashboard.py        # Dashboard stats & insights
│   │   │   ├── search.py           # Search + agent-lookup endpoint
│   │   │   ├── intel.py            # Intel items CRUD
│   │   │   ├── iocs.py             # IOC database
│   │   │   ├── news.py             # Cyber news + AI enrichment
│   │   │   ├── techniques.py       # MITRE ATT&CK
│   │   │   ├── cases.py            # Case management
│   │   │   ├── reports.py          # Report generation
│   │   │   ├── enrichment.py       # Detection rules + enrichment
│   │   │   ├── demo.py             # Bedrock demo endpoint
│   │   │   └── ...                 # 16 route files total
│   │   ├── services/               # Business logic
│   │   │   ├── bedrock_adapter.py  # Amazon Bedrock (Nova + Claude)
│   │   │   ├── ai.py               # AI analysis service
│   │   │   ├── scoring.py          # Risk scoring engine
│   │   │   ├── news.py             # News feed aggregation
│   │   │   ├── live_lookup.py      # Live internet IOC lookup
│   │   │   └── feeds/              # 12 threat feed connectors
│   │   │       ├── base.py         # Base connector (fetch/normalize)
│   │   │       ├── nvd.py          # National Vulnerability Database
│   │   │       ├── kev.py          # CISA Known Exploited Vulns
│   │   │       ├── abuseipdb.py    # AbuseIPDB IP reputation
│   │   │       ├── virustotal.py   # VirusTotal malware intel
│   │   │       ├── shodan.py       # Shodan internet scanning
│   │   │       ├── otx.py          # AlienVault OTX
│   │   │       ├── threatfox.py    # ThreatFox IOCs
│   │   │       ├── urlhaus.py      # URLhaus malicious URLs
│   │   │       ├── malwarebazaar.py # MalwareBazaar samples
│   │   │       ├── mitre_attack.py # MITRE ATT&CK framework
│   │   │       ├── exploitdb.py    # Exploit-DB
│   │   │       └── cisa_advisories.py # CISA advisories
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   └── models.py          # 20+ models (656 lines)
│   │   ├── normalizers/            # Data normalization
│   │   │   ├── severity.py         # Severity classification
│   │   │   ├── confidence.py       # Confidence scoring
│   │   │   ├── stix.py             # STIX 2.1 export
│   │   │   ├── rules.py            # Sigma/YARA rule generation
│   │   │   └── ...                 # 14 normalizer files
│   │   ├── middleware/             # Auth, rate limiting, audit
│   │   │   ├── auth.py             # JWT + demo mode bypass
│   │   │   ├── rate_limit.py       # Request rate limiting
│   │   │   └── audit.py            # Audit logging
│   │   └── prompts.py             # AI prompt templates
│   ├── tests/                      # Test suite
│   │   ├── test_config.py          # Config validation tests
│   │   ├── test_normalizers.py     # Normalizer tests
│   │   ├── test_routes.py          # API route tests
│   │   └── test_services.py        # Service tests
│   └── pyproject.toml              # Python dependencies
│
├── ui/                             # Frontend (Next.js 14, TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── (app)/              # Authenticated pages
│   │   │   │   ├── dashboard/      # Main dashboard
│   │   │   │   ├── search/         # IOC search + live lookup
│   │   │   │   ├── news/           # Cyber news feed
│   │   │   │   ├── intel/          # Intel items browser
│   │   │   │   ├── iocs/           # IOC database
│   │   │   │   ├── techniques/     # MITRE ATT&CK matrix
│   │   │   │   ├── detections/     # Detection rules
│   │   │   │   ├── cases/          # Case management
│   │   │   │   ├── reports/        # Report builder
│   │   │   │   ├── investigate/    # Graph explorer
│   │   │   │   ├── geo/            # Geographic threat view
│   │   │   │   ├── analytics/      # Analytics dashboards
│   │   │   │   ├── feeds/          # Feed status monitor
│   │   │   │   ├── briefings/      # Threat briefings
│   │   │   │   ├── notifications/  # Alert notifications
│   │   │   │   └── settings/       # User settings
│   │   │   └── login/              # Login page
│   │   ├── components/             # Reusable UI components
│   │   ├── lib/                    # API client, utilities
│   │   │   └── api.ts              # Typed API client (950+ lines)
│   │   ├── store/                  # Zustand state management
│   │   └── middleware.ts           # Auth bypass for demo
│   └── next.config.js              # API proxy configuration
│
├── worker/                         # Background job processing
│   ├── tasks.py                    # Feed ingestion + IPinfo enrichment
│   ├── scheduler.py                # APScheduler cron jobs
│   └── worker.py                   # RQ worker process
│
├── infra/                          # AWS CDK Infrastructure
│   ├── lib/
│   │   ├── intelpulse-stack.ts     # Main CDK stack (800+ lines)
│   │   ├── bedrock-lambdas-construct.ts  # Lambda action groups
│   │   └── bedrock-agents-construct.ts   # Bedrock agent definitions
│   ├── lambdas/                    # Lambda function handlers
│   │   ├── virustotal_lookup/      # VirusTotal API integration
│   │   ├── abuseipdb_check/        # AbuseIPDB API integration
│   │   ├── otx_lookup/             # OTX API integration
│   │   └── shodan_lookup/          # Shodan API integration
│   ├── bin/intelpulse.ts           # CDK app entry point
│   └── package.json                # CDK dependencies
│
├── db/                             # Database
│   ├── schema.sql                  # Full PostgreSQL + TimescaleDB schema
│   └── migrations/                 # Database migrations
│
├── docker/                         # Dockerfiles
│   ├── Dockerfile.api              # API container
│   ├── Dockerfile.ui               # UI container
│   └── Dockerfile.worker           # Worker container
│
├── docs/                           # Documentation
│   ├── SUBMISSION.md               # Submission overview
│   ├── SUBMISSION_SLIDES.md        # PPT slide content
│   ├── ARCHITECTURE.md             # Technical architecture
│   ├── AMAZON_Q_USAGE_REPORT.md    # Q Developer usage report
│   ├── PRODUCTIVITY_METRICS.md     # Time savings & metrics
│   ├── SOURCE_CODE_GUIDE.md        # This file
│   └── DEMO_VIDEO_SCRIPT.md        # Demo video script
│
├── .github/workflows/ci.yml       # CI pipeline
├── docker-compose.yml              # Local development
├── docker-compose.demo.yml         # Demo deployment
├── setup_agents.py                 # Bedrock agent setup script
└── ruff.toml                       # Python linter config
```

---

## Key Files by Feature

### Amazon Bedrock Integration

| File | Purpose |
|------|---------|
| `api/app/services/bedrock_adapter.py` | Unified adapter for Nova + Claude models |
| `api/app/routes/search.py` | `/search/agent-lookup` multi-agent endpoint |
| `api/app/routes/demo.py` | Bedrock health check endpoint |
| `setup_agents.py` | Creates 3 Bedrock agents (supervisor + 2 collaborators) |
| `infra/lambdas/` | 4 Lambda action group handlers |

### KIRO IDE

| File | Purpose |
|------|---------|
| `.kiro/specs/aws-infrastructure-migration/` | Full spec (requirements → design → tasks) |
| `.kiro/steering/*.md` | 4 context steering files |
| `.kiro/hooks/*.kiro.hook` | 5 automation hooks |

### Threat Intelligence Pipeline

| File | Purpose |
|------|---------|
| `api/app/services/feeds/*.py` | 12 feed connectors |
| `api/app/services/news.py` | 19 RSS news sources + AI enrichment |
| `worker/tasks.py` | Feed ingestion + IPinfo enrichment |
| `api/app/services/scoring.py` | Risk scoring engine |

### Infrastructure as Code

| File | Purpose |
|------|---------|
| `infra/lib/intelpulse-stack.ts` | CDK stack: VPC, ECS, ALB, data services |
| `infra/lib/bedrock-lambdas-construct.ts` | Lambda functions for Bedrock agents |
| `infra/lib/bedrock-agents-construct.ts` | Bedrock agent definitions |

---

## How to Run Locally

```bash
# Clone
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse
git checkout aws-migration

# Copy environment
cp .env.example .env
# Edit .env with your API keys

# Start all services
docker-compose up -d

# Access
# UI: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/api/docs
```

---

## Code Statistics

| Metric | Count |
|--------|-------|
| Total files | 150+ |
| Python files (backend) | 60+ |
| TypeScript files (frontend) | 40+ |
| CDK/Infrastructure files | 15+ |
| Test files | 6 |
| Documentation files | 10+ |
| Lines of code (estimated) | 25,000+ |
