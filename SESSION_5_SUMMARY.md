# Session 5 Summary - Bedrock Agents Infrastructure

**Date**: 2026-04-03
**Duration**: ~45 minutes
**Branch**: aws-migration
**Status**: Task 9 infrastructure complete (manual agent creation required)

---

## Accomplishments

### ✅ Task 9: Bedrock Agents Infrastructure - PARTIAL COMPLETE

Created CDK infrastructure for Bedrock Agent Core multi-agent system:

#### 1. BedrockAgentsConstruct (`infra/lib/bedrock-agents-construct.ts`)

**Created Resources**:

- S3 bucket for MITRE ATT&CK data (`intelpulse-mitre-data-{ACCOUNT_ID}`)
- 4 IAM roles for Bedrock agents:
  - `intelpulse-bedrock-reputationanalyst` - With Lambda invoke permissions
  - `intelpulse-bedrock-contextenricher` - With S3 read permissions
  - `intelpulse-bedrock-riskscorer` - Basic Bedrock permissions
  - `intelpulse-bedrock-supervisor` - With agent invocation permissions

**IAM Permissions**:

- All roles: `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream`
- Reputation Analyst: Invoke all 4 Lambda functions
- Context Enricher: Read from MITRE data S3 bucket
- Supervisor: `bedrock:InvokeAgent` for all agents in account

**CloudFormation Outputs**:

- MitreDataBucketName
- ReputationAnalystRoleArn
- ContextEnricherRoleArn
- RiskScorerRoleArn
- SupervisorRoleArn
- ActionGroupLambdaArns (JSON with all 4 Lambda ARNs)
- BedrockAgentsSetupInstructions (reference to docs)

#### 2. Updated IntelPulseStack

- Added import for `BedrockAgentsConstruct`
- Instantiated construct with Lambda functions from Task 8
- Integrated with existing infrastructure

#### 3. Comprehensive Setup Documentation

Created `docs/BEDROCK_AGENTS_SETUP.md` with:

- Step-by-step CLI commands for creating all 4 agents
- Complete OpenAPI schema for action groups
- Agent instructions for each role
- MITRE ATT&CK data upload instructions
- Secrets Manager update commands
- Testing procedures
- Troubleshooting guide

---

## Why Manual Agent Creation?

**CDK Limitations**:

- Bedrock agents are relatively new (2024)
- CDK L1 constructs (`CfnAgent`, `CfnAgentActionGroup`) have limitations:
  - Action group OpenAPI schemas are complex to configure
  - Knowledge Base requires OpenSearch Serverless (separate complex setup)
  - Agent collaboration configuration is intricate
  - Limited examples and documentation

**What CDK Creates**:

- ✅ S3 bucket for data
- ✅ IAM roles with correct permissions
- ✅ Lambda functions (from Task 8)
- ✅ All supporting infrastructure

**What Requires Manual Setup**:

- ❌ Bedrock agents themselves
- ❌ Action group associations
- ❌ Knowledge Base (optional)
- ❌ Agent aliases

**Estimated Manual Setup Time**: 30-45 minutes

---

## Multi-Agent System Architecture

### Agent Hierarchy

```
┌─────────────────────────────────────────┐
│  IntelPulse Threat Analyst (Supervisor) │
│  Model: Claude 3.5 Sonnet               │
│  Role: Orchestrate analysis             │
└──────────────┬──────────────────────────┘
               │
       ┌───────┴───────┬───────────────┐
       │               │               │
       ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ IOC          │ │ Threat       │ │ Risk         │
│ Reputation   │ │ Context      │ │ Scorer       │
│ Analyst      │ │ Enricher     │ │              │
├──────────────┤ ├──────────────┤ ├──────────────┤
│ Claude 3.5   │ │ Claude 3.5   │ │ Claude 3.5   │
│ Haiku        │ │ Haiku        │ │ Haiku        │
├──────────────┤ ├──────────────┤ ├──────────────┤
│ Action       │ │ Knowledge    │ │ Risk         │
│ Groups:      │ │ Base:        │ │ Calculation  │
│ - VirusTotal │ │ - MITRE      │ │ - Score      │
│ - AbuseIPDB  │ │   ATT&CK     │ │ - Severity   │
│ - OTX        │ │              │ │ - Actions    │
│ - Shodan     │ │              │ │              │
└──────────────┘ └──────────────┘ └──────────────┘
```

### Workflow

1. **User Request** → Supervisor Agent
2. **Supervisor** → IOC Reputation Analyst
   - Queries VirusTotal, AbuseIPDB, OTX, Shodan
   - Returns aggregated reputation data
3. **Supervisor** → Threat Context Enricher
   - Maps to MITRE ATT&CK techniques
   - Identifies threat actors
4. **Supervisor** → Risk Scorer
   - Calculates risk score (0-100)
   - Assigns severity (CRITICAL/HIGH/MEDIUM/LOW/INFO)
   - Generates recommended actions
5. **Supervisor** → Synthesizes comprehensive report

---

## Git Commit

**Commit Hash**: `9438713`
**Message**: "feat: add Bedrock agents infrastructure (Task 9 - partial)"

**Files Changed**:

- `infra/lib/bedrock-agents-construct.ts` (new, 189 lines)
- `infra/lib/intelpulse-stack.ts` (updated, +3 lines)
- `docs/BEDROCK_AGENTS_SETUP.md` (new, 662 lines)

**Total**: 851 insertions, 1 deletion

---

## Task Progress

### Phase 2: Bedrock Agent Core

- [x] **Task 7**: Bedrock adapter (100%) ✅
- [x] **Task 8**: Lambda action groups (100%) ✅
- [x] **Task 9**: Create Bedrock agents (50%) ⚠️
  - [x] 9.1: S3 bucket for MITRE data ✅
  - [ ] 9.2: Bedrock Knowledge Base (manual)
  - [ ] 9.3-9.5: IOC Reputation Analyst (manual)
  - [ ] 9.6-9.8: Threat Context Enricher (manual)
  - [ ] 9.9-9.10: Risk Scorer (manual)
  - [ ] 9.11-9.13: Supervisor agent (manual)
  - [ ] 9.14: Agent alias (manual)
  - [ ] 9.15-9.16: Testing (manual)
  - [ ] 9.17: Add IDs to Secrets Manager (manual)
- [ ] **Task 10**: Agent invocation service (0%)
- [ ] **Task 11**: Agent-lookup API endpoint (0%)
- [ ] **Task 12**: Update search UI (0%)

**Phase 2 Progress**: 42% (2.5/6 tasks complete)

### Overall Progress

- Phase 0: 100% ✅
- Phase 1: 100% ✅ (code complete, not deployed)
- Phase 2: 42% (2.5/6 tasks)
- Phase 3: 0%
- Phase 4: 0%

**Total**: ~45% complete

---

## Next Steps

### Option A: Complete Manual Agent Setup (Recommended)

Follow `docs/BEDROCK_AGENTS_SETUP.md` to:

1. Upload MITRE ATT&CK data to S3 (5 min)
2. Create 4 Bedrock agents via CLI (20 min)
3. Configure action groups (10 min)
4. Test multi-agent system (5 min)
5. Update Secrets Manager (2 min)

**Total Time**: ~45 minutes

### Option B: Continue with Code Tasks

Skip manual agent setup for now and continue with:

- Task 10: Agent invocation service (api/services/bedrock_agents.py)
- Task 11: Agent-lookup API endpoint
- Task 12: Update search UI

**Note**: Tasks 10-12 require agent IDs from manual setup to test properly.

### Option C: Deploy Infrastructure

Deploy the CDK stack to AWS:

```bash
cd infra
npm run cdk deploy -- --require-approval never --outputs-file outputs.json
```

**Duration**: 25-30 minutes
**Cost**: ~$196/month (see DEPLOYMENT_STATUS.md)

---

## Key Decisions

### 1. Simplified CDK Construct

**Decision**: Create IAM roles and S3 bucket only, not actual agents
**Reason**: CDK L1 constructs too limited for complex agent configuration
**Impact**: Requires manual setup but provides more control

### 2. Comprehensive Documentation

**Decision**: Create detailed CLI-based setup guide
**Reason**: Easier to follow than AWS Console screenshots
**Impact**: Reproducible, scriptable, version-controlled

### 3. Action Group Design

**Decision**: Single action group with 4 operations (VirusTotal, AbuseIPDB, OTX, Shodan)
**Reason**: Simpler than 4 separate action groups
**Impact**: Easier to manage, single Lambda routing point

### 4. Knowledge Base Optional

**Decision**: Make MITRE ATT&CK Knowledge Base optional
**Reason**: OpenSearch Serverless adds complexity and cost
**Impact**: Context Enricher uses model knowledge instead

---

## Testing Strategy

### Unit Tests (Not Yet Implemented)

- Test IAM role permissions
- Test S3 bucket configuration
- Test Lambda function integration

### Integration Tests (Manual)

1. **Agent Creation**: Verify all 4 agents created successfully
2. **Action Groups**: Test each Lambda function independently
3. **Agent Invocation**: Test supervisor with sample IOC
4. **Agent Trace**: Verify all collaborators invoked
5. **Response Format**: Validate JSON structure

### End-to-End Test

```bash
# Test with known malicious IP
aws bedrock-agent-runtime invoke-agent \
  --agent-id "$SUPERVISOR_AGENT_ID" \
  --agent-alias-id "$SUPERVISOR_ALIAS_ID" \
  --session-id "test-$(date +%s)" \
  --input-text "Analyze this IOC: 1.2.3.4 (IP address)" \
  --enable-trace \
  output.txt
```

---

## Known Issues & Limitations

### 1. Manual Agent Creation Required

**Issue**: CDK cannot create Bedrock agents with action groups
**Workaround**: Follow docs/BEDROCK_AGENTS_SETUP.md
**Impact**: 45 minutes additional setup time

### 2. Knowledge Base Not Implemented

**Issue**: OpenSearch Serverless setup is complex
**Workaround**: Context Enricher uses model knowledge
**Impact**: Less accurate MITRE ATT&CK mapping

### 3. No Automated Testing

**Issue**: Bedrock agents difficult to test in CI/CD
**Workaround**: Manual testing with sample IOCs
**Impact**: Slower validation cycle

### 4. Region Limitations

**Issue**: Bedrock agents only available in select regions
**Workaround**: Use us-east-1 or us-west-2
**Impact**: May increase latency for Mumbai deployment

---

## Cost Analysis

### Additional Costs from Task 9

**S3 Bucket**:

- Storage: ~$0.023/GB/month
- MITRE data: ~50 MB = $0.001/month
- Requests: Negligible

**Bedrock Agents** (when created):

- Model invocation: Pay per token
- Claude 3.5 Haiku: $0.25/MTok input, $1.25/MTok output
- Claude 3.5 Sonnet: $3/MTok input, $15/MTok output
- Estimated: $10-50/month depending on usage

**Lambda Invocations** (from Task 8):

- Already accounted for in previous estimate

**Total Additional**: ~$10-50/month

---

## Documentation Updates

### Created

- `docs/BEDROCK_AGENTS_SETUP.md` - Complete manual setup guide

### Updated

- `infra/lib/intelpulse-stack.ts` - Added Bedrock agents construct
- `SESSION_4_SUMMARY.md` - Referenced in context

### Needed

- Update `.env.example` with `BEDROCK_SUPERVISOR_AGENT_ID` and `BEDROCK_SUPERVISOR_ALIAS_ID`
- Update `DEPLOYMENT_GUIDE.md` with Bedrock agents section
- Create `BEDROCK_AGENTS_TESTING.md` with test cases

---

## Lessons Learned

### 1. CDK Limitations

**Learning**: Not all AWS services have mature CDK support
**Action**: Check CDK construct maturity before planning
**Impact**: Adjust timeline for manual setup

### 2. Documentation First

**Learning**: Comprehensive docs reduce setup friction
**Action**: Write detailed CLI commands, not just concepts
**Impact**: Faster onboarding, reproducible setup

### 3. Incremental Complexity

**Learning**: Start simple, add complexity later
**Action**: Make Knowledge Base optional, not required
**Impact**: Faster initial deployment

---

## Recommendations

### For Next Session

**Recommended Path**: Complete manual agent setup first

1. Deploy infrastructure (25-30 min)
2. Follow BEDROCK_AGENTS_SETUP.md (45 min)
3. Test multi-agent system (10 min)
4. Continue with Task 10 (agent invocation service)

**Alternative Path**: Continue with code

1. Task 10: Agent invocation service (1 hour)
2. Task 11: Agent-lookup API endpoint (30 min)
3. Task 12: Update search UI (1 hour)
4. Deploy everything together

### For Production

1. **Automate Agent Creation**: Create CloudFormation custom resource
2. **Add Knowledge Base**: Implement OpenSearch Serverless
3. **Add Monitoring**: CloudWatch dashboards for agent metrics
4. **Add Cost Controls**: Set budget alerts for Bedrock usage

---

## Files Summary

### Created

- `infra/lib/bedrock-agents-construct.ts` (189 lines)
  - S3 bucket for MITRE data
  - 4 IAM roles for agents
  - CloudFormation outputs

- `docs/BEDROCK_AGENTS_SETUP.md` (662 lines)
  - Step-by-step CLI commands
  - OpenAPI schema for action groups
  - Agent instructions
  - Testing procedures

### Modified

- `infra/lib/intelpulse-stack.ts` (+3 lines)
  - Import BedrockAgentsConstruct
  - Instantiate with Lambda functions

### Total

- 3 files changed
- 851 insertions
- 1 deletion

---

**Session Status**: Task 9 Infrastructure Complete ✅
**Manual Setup**: Required (45 minutes)
**Git**: Committed and pushed ✅
**Next**: Manual agent creation OR Task 10
