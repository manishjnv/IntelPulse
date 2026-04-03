# IntelPulse CDK Deployment Guide

## Status: Task 1 Complete ✅

The CDK project scaffold has been successfully created and is ready for deployment.

## What's Been Completed

- ✅ CDK TypeScript project initialized in `infra/` directory
- ✅ IntelPulseStack class created with proper structure
- ✅ Stack configured for region: ap-south-1 (Mumbai)
- ✅ Tags configured: Project=IntelPulse, Environment=production, ManagedBy=CDK
- ✅ CDK dependencies added (aws-cdk-lib v2.246.0)
- ✅ Entry point created: bin/intelpulse.ts
- ✅ TypeScript compilation successful
- ✅ CDK synth generates valid CloudFormation template

## Prerequisites for Deployment

### 1. Install AWS CLI

```bash
# Windows (using Chocolatey)
choco install awscli

# Or download from: https://aws.amazon.com/cli/
```

### 2. Configure AWS Credentials

```bash
aws configure
# Enter:
# - AWS Access Key ID
# - AWS Secret Access Key
# - Default region: us-east-1
# - Default output format: json
```

### 3. Verify AWS Access

```bash
aws sts get-caller-identity
```

## Deployment Steps

### Step 1: Bootstrap CDK (First Time Only)

```bash
cd infra
npx cdk bootstrap aws://ACCOUNT-ID/us-east-1
```

Replace `ACCOUNT-ID` with your AWS account ID from `aws sts get-caller-identity`.

### Step 2: Build the Project

```bash
npm run build
```

### Step 3: Synthesize CloudFormation Template

```bash
npx cdk synth
```

This generates the CloudFormation template without deploying.

### Step 4: Deploy to AWS

```bash
npx cdk deploy IntelPulseStack --require-approval never
```

Or with manual approval for each change:

```bash
npx cdk deploy IntelPulseStack
```

### Step 5: Save Outputs

```bash
npx cdk deploy IntelPulseStack --outputs-file outputs.json
```

This saves resource endpoints (VPC ID, subnet IDs, etc.) to `outputs.json`.

## Current Stack Contents

The current stack is minimal and only includes:

- Stack metadata
- CDK bootstrap version parameter
- Resource tags (Project, Environment, ManagedBy)

## Next Steps (Upcoming Tasks)

### Task 2: VPC and Networking

- Create VPC with CIDR 10.0.0.0/16
- 2 Availability Zones (ap-south-1a, ap-south-1b)
- 2 public subnets + 2 private subnets
- Internet Gateway + NAT Gateway
- Security groups for ALB, ECS, databases

### Task 3: EC2 for TimescaleDB

- EC2 t3.medium instance
- EBS gp3 volume (50 GB)
- TimescaleDB container
- Database initialization script

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
- ACM certificate for HTTPS
- Auto-scaling configuration

## Useful Commands

```bash
# Watch for changes and recompile
npm run watch

# Run tests
npm test

# Show differences between deployed and local
npx cdk diff

# List all stacks
npx cdk list

# Destroy all resources (careful!)
npx cdk destroy IntelPulseStack
```

## Troubleshooting

### Error: "Need to perform AWS calls for account..."

**Solution**: Run `npx cdk bootstrap` first.

### Error: "Unable to resolve AWS account"

**Solution**: Configure AWS credentials with `aws configure`.

### Error: "Stack already exists"

**Solution**: Use `npx cdk deploy` to update, or `npx cdk destroy` to remove first.

### TypeScript compilation errors

**Solution**: Run `npm run build` to see detailed errors.

## Cost Estimation

Current stack (Task 1 only): **$0/month** (no resources deployed yet)

Estimated monthly cost after all tasks complete:

- EC2 t3.medium (TimescaleDB): ~$30
- ElastiCache Redis t3.micro: ~$12
- OpenSearch t3.small: ~$40
- ECS Fargate (4 services): ~$50
- NAT Gateway: ~$32
- ALB: ~$16
- Data transfer: ~$10

**Total estimated**: ~$190/month

## Security Notes

- All resources will be tagged for cost tracking
- Security groups follow least-privilege principle
- Secrets stored in AWS Secrets Manager (not in code)
- IAM roles use minimal required permissions
- VPC uses private subnets for data tier

## Support

For issues or questions:

1. Check CloudFormation console for deployment errors
2. Review CDK synth output for template validation
3. Check AWS CloudWatch logs for runtime errors
4. Refer to SESSION_HANDOFF.md for architecture decisions

---

**Last Updated**: 2026-04-03
**CDK Version**: 2.246.0
**Node Version**: 18+
**Region**: ap-south-1 (Mumbai)
