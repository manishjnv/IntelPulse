# Next Session Quick Start Prompt

Copy and paste this prompt to continue the AWS migration in your next session:

---

## Prompt for Next Session

```
Continue IntelPulse AWS migration. 

Current Status:
- ✅ Phase 0: Security hardening complete
- ✅ Task 1: CDK project scaffold complete
- ✅ Task 2: VPC and networking complete
- ✅ Region configured: us-east-1 (for Bedrock support)
- ✅ AWS credentials configured
- ✅ Git configured and pushing to GitHub

Next Steps:
1. Bootstrap CDK in us-east-1: `cd infra && npx cdk bootstrap aws://604275788592/us-east-1`
2. Continue with Task 3: EC2 for TimescaleDB
3. Or deploy current infrastructure first

Read REGION_CHANGE_SUMMARY.md and AWS_CREDENTIALS_CONFIGURED.md for context.

Workspace: E:\code\IntelPulse\ti-platform
Branch: aws-migration
Spec: .kiro/specs/aws-infrastructure-migration/
```

---

## Alternative: If You Want to Deploy First

```
Continue IntelPulse AWS migration. Bootstrap CDK and deploy current infrastructure (VPC + networking).

Current Status:
- ✅ Tasks 1-2 complete (CDK scaffold + VPC/networking)
- ✅ Region: us-east-1
- ✅ AWS credentials configured

Actions needed:
1. Bootstrap CDK: `cd infra && npx cdk bootstrap aws://604275788592/us-east-1`
2. Deploy stack: `npx cdk deploy IntelPulseStack`
3. Verify deployment and save outputs

Then continue with Task 3 (EC2 TimescaleDB).

Workspace: E:\code\IntelPulse\ti-platform
```

---

## Alternative: If You Want to Continue Building

```
Continue IntelPulse AWS migration. Skip deployment for now, continue building infrastructure.

Current Status:
- ✅ Tasks 1-2 complete (CDK + VPC)
- Region: us-east-1

Next: Execute Task 3 - EC2 for TimescaleDB
- Create EC2 t3.medium instance
- Configure TimescaleDB container
- Set up database initialization

Workspace: E:\code\IntelPulse\ti-platform
Spec: .kiro/specs/aws-infrastructure-migration/tasks.md
```

---

## Quick Context Files to Reference

If Kiro needs context, point to these files:

- `SESSION_HANDOFF.md` - Previous session summary
- `REGION_CHANGE_SUMMARY.md` - Why we changed to us-east-1
- `AWS_CREDENTIALS_CONFIGURED.md` - AWS setup details
- `.kiro/specs/aws-infrastructure-migration/tasks.md` - Task list
- `.kiro/specs/aws-infrastructure-migration/design.md` - Architecture design

---

## Session Checklist

Before starting:

- [ ] Workspace: `E:\code\IntelPulse\ti-platform`
- [ ] Branch: `aws-migration`
- [ ] AWS credentials configured (check with `aws sts get-caller-identity`)
- [ ] Git credentials working (check with `git status`)

---

**Recommended Prompt**: Use the first one (gives Kiro flexibility to choose next action)
