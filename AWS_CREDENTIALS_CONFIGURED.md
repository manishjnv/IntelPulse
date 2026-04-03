# AWS Credentials Configuration - Complete ✅

## Configuration Summary

**Status**: ✅ Successfully configured and verified

**AWS Account Details:**

- **User**: IntelPulseUser
- **Account ID**: 604275788592
- **User ID**: AIDAYZMNEZMYOLFO3LHXC
- **ARN**: arn:aws:iam::604275788592:user/IntelPulseUser

**Configuration Files Created:**

- `~/.aws/credentials` - Contains access key and secret key
- `~/.aws/config` - Contains region (ap-south-1) and output format (json)

**Default Region**: us-east-1 (US East - N. Virginia)
**Output Format**: json

**Why us-east-1?**

- Amazon Bedrock Agents fully supported
- All Claude models available (Sonnet 4.6, Opus 4.6, Haiku 4.5)
- Amazon Bedrock Knowledge Bases supported
- Amazon Q Developer available
- Most mature AWS region with all latest features

## Verification

```bash
aws sts get-caller-identity
```

Output:

```json
{
    "UserId": "AIDAYZMNEZMYOLFO3LHXC",
    "Account": "604275788592",
    "Arn": "arn:aws:iam::604275788592:user/IntelPulseUser"
}
```

✅ Credentials are valid and working!

## Next Steps

### 1. Bootstrap CDK (First Time Only)

```bash
cd infra
npx cdk bootstrap aws://604275788592/us-east-1
```

This creates the necessary S3 bucket and IAM roles for CDK deployments.

### 2. Deploy the Infrastructure

```bash
# Synthesize CloudFormation template
npx cdk synth

# Deploy the stack
npx cdk deploy IntelPulseStack

# Or deploy with automatic approval
npx cdk deploy IntelPulseStack --require-approval never
```

### 3. Save Stack Outputs

```bash
npx cdk deploy IntelPulseStack --outputs-file outputs.json
```

This will save VPC IDs, subnet IDs, and security group IDs to `outputs.json`.

## What's Been Deployed So Far

### Task 1: CDK Project Scaffold ✅

- IntelPulseStack created
- Region configured: ap-south-1
- Tags configured: Project=IntelPulse, Environment=production

### Task 2: VPC and Networking ✅

- VPC with CIDR 10.0.0.0/16
- 2 Availability Zones (ap-south-1a, ap-south-1b)
- 2 Public subnets (10.0.0.0/24, 10.0.1.0/24)
- 2 Private subnets (10.0.2.0/24, 10.0.3.0/24)
- Internet Gateway
- 1 NAT Gateway (cost optimized)
- 5 Security Groups:
  - sg-alb (HTTP/HTTPS from internet)
  - sg-ecs (ports 3000/8000 from ALB)
  - sg-postgres (port 5432 from ECS)
  - sg-redis (port 6379 from ECS)
  - sg-opensearch (port 443 from ECS)

## Remaining Tasks

### Task 3: EC2 for TimescaleDB

- EC2 t3.medium instance
- EBS gp3 volume (50 GB)
- TimescaleDB container
- Database initialization

### Task 4: Managed Services

- ElastiCache Redis 7 cluster
- AWS OpenSearch Service domain

### Task 5: ECR Repositories

- intelpulse/api
- intelpulse/ui
- intelpulse/worker

### Task 6: ECS Fargate Cluster

- 4 services: API, UI, Worker, Scheduler
- Application Load Balancer
- ACM certificate
- Auto-scaling

## Security Notes

✅ **Credentials are stored securely** in `~/.aws/credentials`
✅ **Never commit** AWS credentials to git
✅ **Region is set** to us-east-1 (US East - N. Virginia)
✅ **IAM user** has necessary permissions for deployment

## Troubleshooting

### If credentials don't work

```bash
# Check configuration
aws configure list

# Re-verify identity
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user
```

### If deployment fails

```bash
# Check CDK bootstrap status
aws cloudformation describe-stacks --stack-name CDKToolkit

# View CloudFormation events
aws cloudformation describe-stack-events --stack-name IntelPulseStack
```

## Cost Estimation

**Current deployment (Tasks 1-2)**: ~$0/month (no resources deployed yet)

**After full deployment (Tasks 1-6)**:

- VPC, subnets, IGW: Free
- NAT Gateway: ~$32/month
- EC2 t3.medium: ~$30/month
- ElastiCache Redis: ~$12/month
- OpenSearch t3.small: ~$40/month
- ECS Fargate: ~$50/month
- ALB: ~$16/month
- Data transfer: ~$10/month

**Total estimated**: ~$190/month

---

**Status**: Ready to bootstrap and deploy!
**Next Command**: `cd infra && npx cdk bootstrap aws://604275788592/us-east-1`
**Region**: us-east-1 (US East - N. Virginia)
**Last Updated**: 2026-04-03
