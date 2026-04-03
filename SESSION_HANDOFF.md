# Session Handoff Document
**Date**: 2026-04-03
**Session Focus**: AWS Migration Planning & Config Security Hardening
**Project**: IntelPulse → IntelPulse AWS Migration

---

## What Was Accomplished This Session

### 1. Security Hardening - Config Validation ✅

**File Modified**: `api/app/core/config.py`

**Changes Made**:
- Added `__init__` method to `Settings` class with production secret validation
- Validates `SECRET_KEY` is not default values in production
- Validates `SECRET_KEY` is at least 32 characters long
- Validates `POSTGRES_PASSWORD` is not default values in production
- Validates CORS origins don't include wildcards in production

**Code Added**:
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)
    # Validate production secrets
    if self.environment == "production":
        if self.secret_key in ("change-me", "dev-secret-key-not-for-production", "dev-only-fallback-not-for-production"):
            raise ValueError("Production SECRET_KEY must be set to a secure value!")
        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long!")
        if self.postgres_password in ("changeme", "ti_secret", "change-me-strong-password"):
            raise ValueError("Production POSTGRES_PASSWORD must be set to a secure value!")
        # Validate CORS origins don't include wildcards with credentials
        if "*" in self.cors_origins:
            raise ValueError("CORS origins cannot include wildcards in production!")
```

**Test Coverage Created**: `api/tests/test_config.py`
- 15 test cases covering all validation scenarios
- Tests for development/staging/production environments
- Tests for database URL generation (async and sync)
- Tests for settings caching behavior

**Impact**: Prevents accidental deployment with weak credentials in production

---

### 2. Documentation Review ✅

**Files Reviewed**:
- `QUICK_START.md` - 25-hour migration timeline
- `MIGRATION_INSTRUCTIONS.md` - Repository rebranding steps
- `docs/IntelPulse_AWS_Codethon_Plan.md` - Complete implementation plan (truncated, needs full read)
- `CODETHON_SUMMARY.md` - Current status and deliverables
- `.kiro/steering/tech.md` - Technology stack
- `.kiro/steering/product.md` - Product overview
- `.kiro/steering/coding-standards.md` - Code standards
- `.kiro/steering/aws-migration.md` - Migration rules

**Key Findings**:
- No AWS infrastructure code exists yet (`infra/` directory not created)
- No Bedrock integration code exists (no boto3 imports found)
- Migration plan is comprehensive with 16 tasks across 3 phases
- Target score: 97/100 points
- Estimated remaining work: 14 hours

---

## Current Project State

### Repository Structure
```
IntelPulse/  (current name, needs rebranding to IntelPulse)
├── api/                    # FastAPI backend (Python 3.12)
├── ui/                     # Next.js 14 frontend
├── worker/                 # Python RQ background jobs
├── docker/                 # Dockerfiles (api, ui, worker)
├── db/                     # schema.sql
├── docs/                   # Documentation
├── .kiro/
│   └── steering/          # 4 steering files (tech, product, coding-standards, aws-migration)
├── docker-compose.yml     # Current VPS deployment
└── .env.example           # Environment template
```

### What Exists
- ✅ Working application on Hostinger VPS (IntelPulse.in)
- ✅ Docker Compose setup (7 services)
- ✅ Complete migration plan documentation
- ✅ KIRO steering files (4 files)
- ✅ Security validation in config.py
- ✅ Test suite structure

### What Doesn't Exist Yet
- ❌ `infra/` directory (CDK code)
- ❌ AWS Bedrock integration code
- ❌ Lambda functions for Bedrock action groups
- ❌ Bedrock agents configuration
- ❌ GitHub Actions CI/CD workflow
- ❌ ECR repositories
- ❌ ECS task definitions
- ❌ New GitHub repository (IntelPulse)

---

## AWS Migration Plan Overview

### Phase 1: Infrastructure (Tasks 1-6)
**Status**: Not Started
**Estimated Time**: 8 hours

1. Create CDK project scaffold
2. VPC + networking (2 AZs, public/private subnets, NAT Gateway)
3. EC2 for TimescaleDB (RDS doesn't support TimescaleDB extension)
4. Managed services (ElastiCache Redis, OpenSearch)
5. ECR repositories (3: api, ui, worker)
6. ECS Fargate cluster + 4 services (api, ui, worker, scheduler)

**Key Decisions**:
- Region: ap-south-1 (Mumbai)
- TimescaleDB on EC2 t3.medium (not RDS)
- Single NAT Gateway (cost savings)
- ALB replaces Caddy for HTTPS

### Phase 2: Bedrock Integration (Tasks 7-12)
**Status**: Not Started
**Estimated Time**: 6 hours

7. Create `api/services/bedrock_adapter.py` (replace llama3 HTTP calls)
8. Create 4 Lambda functions (VirusTotal, AbuseIPDB, OTX, Shodan lookups)
9. Create 4 Bedrock agents:
   - Supervisor: "IntelPulse Threat Analyst"
   - Collaborator 1: "IOC Reputation Analyst"
   - Collaborator 2: "Threat Context Enricher"
   - Collaborator 3: "Risk Scorer"
10. Create `api/services/bedrock_agents.py` (agent invocation)
11. Add API endpoint: `POST /search/agent-lookup`
12. Update UI: Add "AI Agent Analysis" button

**Key Features**:
- Multi-agent orchestration
- MITRE ATT&CK knowledge base integration
- Structured JSON responses with risk scores
- Agent trace visibility

### Phase 3: CI/CD & Polish (Tasks 13-16)
**Status**: Not Started
**Estimated Time**: 4 hours

13. AWS Transform assessment
14. Amazon Q security scan
15. GitHub Actions workflow (ECR push + ECS deploy)
16. DNS (Route 53) + OAuth (new Google client for intelpulse.tech)

---

## Environment Configuration

### Current Credentials Location
- **Local Dev**: `.env` file (copied from `.env.example`)
- **Docker Compose**: Environment variables from `.env`
- **AWS Target**: AWS Secrets Manager (`intelpulse/production`)

### Required Secrets for AWS
```json
{
  "SECRET_KEY": "32+ character string",
  "POSTGRES_PASSWORD": "strong password",
  "REDIS_URL": "redis://<elasticache-endpoint>:6379/0",
  "OPENSEARCH_URL": "https://<opensearch-endpoint>",
  "GOOGLE_CLIENT_ID": "new OAuth client for intelpulse.tech",
  "GOOGLE_CLIENT_SECRET": "new OAuth secret",
  "NVD_API_KEY": "existing",
  "ABUSEIPDB_API_KEY": "existing",
  "OTX_API_KEY": "existing",
  "VIRUSTOTAL_API_KEY": "existing",
  "SHODAN_API_KEY": "existing",
  "AWS_REGION": "ap-south-1",
  "BEDROCK_SUPERVISOR_AGENT_ID": "to be created",
  "BEDROCK_SUPERVISOR_ALIAS_ID": "to be created"
}
```

---

## Key Technical Decisions

### 1. TimescaleDB on EC2 (Not RDS)
**Reason**: RDS PostgreSQL doesn't support TimescaleDB extension
**Implementation**: 
- EC2 t3.medium in private subnet
- Docker container running `timescale/timescaledb:latest-pg16`
- EBS gp3 volume (50 GB) for data persistence
- Security group: inbound 5432 from ECS only

### 2. Bedrock Multi-Agent Architecture
**Supervisor**: Claude 3.5 Sonnet (orchestration)
**Collaborators**: Claude 3.5 Haiku (cost-effective for specific tasks)
- IOC Reputation Analyst (queries threat feeds via Lambda)
- Threat Context Enricher (MITRE ATT&CK mapping)
- Risk Scorer (0-100 scale with severity levels)

### 3. Hybrid AI Approach
**Primary**: Bedrock Agent Core (multi-agent)
**Fallback**: Direct Bedrock API call (if agent fails)
**Local Dev**: Keep existing llama3 HTTP endpoint support

### 4. No Data Migration
**Decision**: Seed fresh data on AWS deployment
**Method**: `POST /feeds/trigger-all` after deployment
**Reason**: Simplifies migration, no downtime concerns

---

## Next Session Priorities

### Option A: Infrastructure First (Recommended)
**Start with**: CDK stack creation
**Why**: Foundation needed before Bedrock integration can be deployed
**First Steps**:
1. Create `infra/` directory
2. Initialize CDK TypeScript project
3. Create VPC construct
4. Create ECS construct
5. Create data tier constructs

### Option B: Bedrock Integration First
**Start with**: Bedrock adapter and agents
**Why**: Can develop and test locally before AWS deployment
**First Steps**:
1. Create `api/services/bedrock_adapter.py`
2. Create Lambda functions in `infra/lambdas/`
3. Test Bedrock API calls locally
4. Create agent configurations
5. Add new API endpoint

### Option C: Parallel Development
**Start with**: Both infrastructure and Bedrock code
**Why**: Maximize velocity, can work independently
**Risk**: Integration complexity at the end

---

## Important Files to Reference

### Migration Planning
- `QUICK_START.md` - 25-hour timeline with commands
- `MIGRATION_INSTRUCTIONS.md` - Repository rebranding steps
- `docs/IntelPulse_AWS_Codethon_Plan.md` - Complete 16-task plan
- `docs/HIGH_PRIORITY_DELIVERABLES.md` - 5 critical deliverables for scoring

### Current Architecture
- `docker-compose.yml` - Current service definitions
- `.env.example` - Environment variable template
- `db/schema.sql` - Database schema
- `api/app/core/config.py` - Configuration (just updated)

### Steering Files (KIRO Context)
- `.kiro/steering/tech.md` - Technology stack
- `.kiro/steering/product.md` - Product overview
- `.kiro/steering/aws-migration.md` - Migration rules
- `.kiro/steering/coding-standards.md` - Code standards

---

## Testing Strategy

### Current Test Coverage
- `api/tests/conftest.py` - Test fixtures (mock user, async client)
- `api/tests/test_services.py` - Service layer tests (scoring)
- `api/tests/test_config.py` - Config validation tests (NEW)
- `api/tests/test_routes.py` - API route tests
- `api/tests/test_normalizers.py` - Data normalization tests

### Tests to Add
- Bedrock adapter tests (mock boto3 calls)
- Agent invocation tests
- Lambda function tests
- CDK stack tests (snapshot testing)
- Integration tests for multi-agent flow

---

## Known Issues & Risks

### Technical Risks
1. **Bedrock Quotas**: May hit rate limits during testing
   - **Mitigation**: Implement fallback to direct API calls
   
2. **TimescaleDB on EC2**: Manual management required
   - **Mitigation**: Document backup/restore procedures
   
3. **Single NAT Gateway**: Single point of failure
   - **Mitigation**: Acceptable for demo, document production upgrade

### Timeline Risks
1. **14 hours remaining work**: Tight but achievable
   - **Mitigation**: Prioritize core features, defer nice-to-haves
   
2. **Bedrock agent creation**: May take longer than estimated
   - **Mitigation**: Start early, test incrementally

### Evaluation Risks
1. **Missing deliverables**: Need 5 high-priority docs
   - **Mitigation**: Templates provided in HIGH_PRIORITY_DELIVERABLES.md
   
2. **Demo video quality**: First impression matters
   - **Mitigation**: Script provided, practice run before recording

---

## Commands to Remember

### CDK Commands
```bash
# Initialize CDK project
cd infra
cdk init app --language typescript

# Bootstrap (first time only)
cdk bootstrap

# Deploy
cdk deploy IntelPulseStack --require-approval never

# Save outputs
cdk deploy IntelPulseStack --outputs-file outputs.json
```

### Docker Commands
```bash
# Build images
docker build -f docker/Dockerfile.api -t intelpulse/api:latest .
docker build -f docker/Dockerfile.ui -t intelpulse/ui:latest .
docker build -f docker/Dockerfile.worker -t intelpulse/worker:latest .

# ECR login
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  ACCOUNT-ID.dkr.ecr.ap-south-1.amazonaws.com
```

### Testing Commands
```bash
# Run all tests
cd api
pytest tests/ -v

# Run specific test file
pytest tests/test_config.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### AWS CLI Commands
```bash
# Create secret
aws secretsmanager create-secret \
  --name intelpulse/production \
  --secret-string file://secrets.json \
  --region ap-south-1

# Test Bedrock agent
aws bedrock-agent-runtime invoke-agent \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --session-id test-session \
  --input-text "Analyze IP: 8.8.8.8"
```

---

## Questions for Next Session

1. **Which phase to start with?**
   - Infrastructure (CDK stack)
   - Bedrock integration (agents + adapter)
   - Both in parallel

2. **Repository migration timing?**
   - Do it now (before AWS work)
   - Do it later (after AWS work)
   - Skip it (keep current repo name)

3. **Testing approach?**
   - Test locally first (mock AWS services)
   - Deploy to AWS early (test in real environment)
   - Hybrid (local unit tests, AWS integration tests)

4. **Documentation priority?**
   - Write as we go (slower but complete)
   - Write at the end (faster but may forget details)
   - Hybrid (key decisions now, details later)

---

## Session Metrics

- **Duration**: ~1 hour
- **Files Modified**: 1 (`api/app/core/config.py`)
- **Files Created**: 2 (`api/tests/test_config.py`, `SESSION_HANDOFF.md`)
- **Files Reviewed**: 10+ (documentation)
- **Lines of Code Added**: ~150 (config validation + tests)
- **Tests Added**: 15 test cases
- **Security Issues Fixed**: 1 (production credential validation)

---

## Recommended Next Actions

### Immediate (Next Session Start)
1. ✅ Read this handoff document
2. ⏳ Decide on phase priority (Infrastructure vs Bedrock vs Both)
3. ⏳ Create `infra/` directory structure
4. ⏳ Initialize CDK project
5. ⏳ Create first construct (VPC or Bedrock adapter)

### Short-term (This Week)
6. ⏳ Complete Phase 1 (Infrastructure) - 8 hours
7. ⏳ Complete Phase 2 (Bedrock) - 6 hours
8. ⏳ Deploy to AWS and test
9. ⏳ Run security scans
10. ⏳ Start documentation

### Before Submission
11. ⏳ Create 5 high-priority deliverables
12. ⏳ Record demo video
13. ⏳ Final testing and polish
14. ⏳ Submit to codethon platform

---

## Contact & Resources

### Documentation
- Main Plan: `docs/IntelPulse_AWS_Codethon_Plan.md`
- Quick Start: `QUICK_START.md`
- Migration: `MIGRATION_INSTRUCTIONS.md`
- Deliverables: `docs/HIGH_PRIORITY_DELIVERABLES.md`

### External Resources
- AWS CDK Docs: https://docs.aws.amazon.com/cdk/
- Bedrock Agent Core: https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html
- TimescaleDB: https://docs.timescale.com/
- MITRE ATT&CK: https://attack.mitre.org/

---

## Session End Checklist

- [x] Config validation implemented
- [x] Tests created and documented
- [x] Documentation reviewed
- [x] Current state assessed
- [x] Migration plan understood
- [x] Next steps identified
- [x] Handoff document created
- [x] All changes committed (pending)

---

**Status**: Ready for next session
**Next Session Focus**: AWS Infrastructure (CDK) or Bedrock Integration
**Blocker**: None
**Confidence**: High (clear plan, good foundation)

---

**End of Session Handoff**
