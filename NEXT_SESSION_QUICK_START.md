# Next Session Quick Start

**Read this first when starting the next session!**

---

## What Happened Last Session

✅ **Security hardening completed** - Added production credential validation to `api/app/core/config.py`
✅ **Test coverage added** - Created 15 test cases in `api/tests/test_config.py`
✅ **Documentation reviewed** - Understood the complete migration plan
✅ **Session handoff created** - Full context documented in `SESSION_HANDOFF.md`

---

## Current State

### What Exists
- Working application on VPS (IntelPulse.in)
- Complete migration plan (16 tasks)
- KIRO spec files (requirements + tasks)
- Security validation in config

### What Doesn't Exist
- ❌ AWS infrastructure (no `infra/` directory)
- ❌ Bedrock integration code
- ❌ Lambda functions
- ❌ CI/CD pipeline

---

## Decision Needed: Which Phase to Start?

### Option A: Infrastructure First (Recommended)
**Start**: Create CDK stack for AWS resources
**Why**: Foundation needed before Bedrock can be deployed
**Time**: ~8 hours
**First Command**:
```bash
mkdir infra
cd infra
cdk init app --language typescript
```

### Option B: Bedrock Integration First
**Start**: Create Bedrock adapter and agents
**Why**: Can develop and test locally before AWS
**Time**: ~6 hours
**First Command**:
```bash
# Create bedrock adapter
touch api/services/bedrock_adapter.py
```

### Option C: Both in Parallel
**Start**: Scaffold both simultaneously
**Why**: Maximum velocity
**Risk**: Integration complexity

---

## Quick Commands Reference

### Read Full Context
```bash
# Read the complete session handoff
cat SESSION_HANDOFF.md

# Read the migration plan
cat docs/IntelPulse_AWS_Codethon_Plan.md

# Read the spec files
cat .kiro/specs/aws-infrastructure-migration/requirements.md
cat .kiro/specs/aws-infrastructure-migration/tasks.md
```

### Start Infrastructure (Option A)
```bash
# Create CDK project
mkdir infra
cd infra
cdk init app --language typescript

# Install dependencies
npm install @aws-cdk/aws-ec2 @aws-cdk/aws-ecs @aws-cdk/aws-elasticloadbalancingv2

# Create first construct
mkdir lib/constructs
touch lib/constructs/vpc-construct.ts
```

### Start Bedrock Integration (Option B)
```bash
# Create bedrock adapter
touch api/services/bedrock_adapter.py

# Create Lambda directories
mkdir -p infra/lambdas/virustotal_lookup
mkdir -p infra/lambdas/abuseipdb_check
mkdir -p infra/lambdas/otx_lookup
mkdir -p infra/lambdas/shodan_lookup

# Create handler files
touch infra/lambdas/virustotal_lookup/handler.py
touch infra/lambdas/abuseipdb_check/handler.py
touch infra/lambdas/otx_lookup/handler.py
touch infra/lambdas/shodan_lookup/handler.py
```

### Run Tests
```bash
cd api
pytest tests/test_config.py -v
```

---

## Key Files to Reference

### Must Read
1. `SESSION_HANDOFF.md` - Complete session context
2. `docs/IntelPulse_AWS_Codethon_Plan.md` - Full migration plan
3. `.kiro/specs/aws-infrastructure-migration/tasks.md` - Task checklist

### Reference as Needed
4. `QUICK_START.md` - 25-hour timeline
5. `MIGRATION_INSTRUCTIONS.md` - Repository rebranding
6. `.kiro/steering/aws-migration.md` - Migration rules
7. `.kiro/steering/tech.md` - Technology stack

---

## Important Context

### Region
**ap-south-1** (Mumbai) - Don't use any other region!

### Branding
- Old: IntelPulse / IntelPulse.in
- New: IntelPulse / intelpulse.tech

### TimescaleDB
**Must use EC2** - RDS doesn't support TimescaleDB extension

### Bedrock Models
- Supervisor: Claude 3.5 Sonnet
- Collaborators: Claude 3.5 Haiku

---

## Next Steps (Choose One Path)

### Path A: Infrastructure First
1. Create `infra/` directory
2. Initialize CDK TypeScript project
3. Create VPC construct (Task 2)
4. Create data tier constructs (Tasks 3-4)
5. Create ECS constructs (Tasks 5-6)

### Path B: Bedrock First
1. Create `api/services/bedrock_adapter.py` (Task 7)
2. Create Lambda functions (Task 8)
3. Test Bedrock API calls locally
4. Create agent configurations (Task 9)
5. Add API endpoint (Task 11)

### Path C: Both Parallel
1. Create both `infra/` and `api/services/bedrock_adapter.py`
2. Work on infrastructure and Bedrock code simultaneously
3. Integrate at the end

---

## Estimated Time Remaining

- **Phase 1 (Infrastructure)**: 8 hours
- **Phase 2 (Bedrock)**: 6 hours
- **Phase 3 (CI/CD)**: 4 hours
- **Documentation**: 11 hours
- **Total**: 29 hours

---

## Success Criteria

### Must Have
- [ ] Application deployed at intelpulse.tech
- [ ] Multi-agent system working
- [ ] Demo video recorded
- [ ] 5 high-priority deliverables completed

### Target Score
**97/100 points**

---

## Questions to Answer

1. **Which phase to start?** (A, B, or C)
2. **Repository migration timing?** (now or later)
3. **Testing approach?** (local first or AWS early)

---

**Ready to start? Pick a path and go!**

**Recommended**: Start with Path A (Infrastructure First)
