# Region Configuration Change Summary

## Change Made

**From**: ap-south-1 (Asia Pacific - Mumbai)  
**To**: us-east-1 (US East - N. Virginia)

## Reason for Change

Amazon Bedrock Agents and full Claude model support (Sonnet 4.6, Opus 4.6, Haiku 4.5) are only available in us-east-1. Since the IntelPulse AWS migration project requires:

- Amazon Bedrock Agents for multi-agent orchestration
- Amazon Bedrock Knowledge Bases for MITRE ATT&CK data
- Amazon Q Developer for security scans
- Full Claude model availability

The region must be us-east-1 to ensure all required services are available.

## Files Updated

### Infrastructure Code

- ✅ `infra/bin/intelpulse.ts` - CDK stack region
- ✅ `infra/lib/intelpulse-stack.ts` - VPC availability zones (us-east-1a, us-east-1b)
- ✅ `infra/README.md` - Documentation
- ✅ `infra/DEPLOYMENT.md` - Deployment guide

### AWS Configuration

- ✅ `~/.aws/config` - AWS CLI default region
- ✅ `AWS_CREDENTIALS_CONFIGURED.md` - Credentials documentation

### Verification

- ✅ TypeScript compilation successful
- ✅ CDK synth generates valid CloudFormation template
- ✅ VPC now uses us-east-1a and us-east-1b availability zones
- ✅ All 31 EC2 resources configured correctly
- ✅ Security groups configured for us-east-1

## Trade-offs

### Advantages ✅

- Full Amazon Bedrock Agents support
- All Claude models available
- Amazon Bedrock Knowledge Bases supported
- Amazon Q Developer available
- Most mature AWS region (newest features launch here first)
- Best for codethon demonstration

### Disadvantages ❌

- Higher latency from India (~200-250ms vs ~50ms for ap-south-1)
- Slightly higher data transfer costs for India-based users

## Impact on Project

### No Impact

- All infrastructure code works identically
- VPC CIDR blocks unchanged (10.0.0.0/16)
- Subnet configuration unchanged
- Security group rules unchanged
- Cost estimates unchanged

### Positive Impact

- ✅ Bedrock Agents will work (critical for Phase 2)
- ✅ Multi-agent orchestration possible
- ✅ MITRE ATT&CK knowledge base integration possible
- ✅ Amazon Q security scans available

## Next Steps

### 1. Bootstrap CDK in us-east-1

```bash
cd infra
npx cdk bootstrap aws://604275788592/us-east-1
```

### 2. Deploy Infrastructure

```bash
npx cdk deploy IntelPulseStack
```

### 3. Continue with Remaining Tasks

- Task 3: EC2 for TimescaleDB
- Task 4: ElastiCache Redis and OpenSearch
- Task 5: ECR repositories
- Task 6: ECS Fargate cluster

## Verification Commands

```bash
# Check AWS CLI region
aws configure get region
# Expected: us-east-1

# Check CDK stack region
cd infra && npx cdk synth | grep "us-east-1"
# Should show us-east-1a and us-east-1b availability zones

# Verify AWS credentials
aws sts get-caller-identity
# Should return account 604275788592
```

## Git Commits

1. **8db6df7** - infra: initialize CDK TypeScript project for AWS infrastructure
2. **8ab0857** - docs: add CDK deployment guide with prerequisites and steps
3. **cfe4b67** - config: change region from ap-south-1 to us-east-1 for Bedrock support ← Current

All changes pushed to: `https://github.com/manishjnv/IntelPulse/tree/aws-migration`

---

**Status**: Region configuration complete ✅  
**Current Region**: us-east-1 (US East - N. Virginia)  
**Ready for**: CDK bootstrap and deployment  
**Last Updated**: 2026-04-03
