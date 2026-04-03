# IntelPulse AWS Infrastructure

This directory contains the AWS CDK infrastructure code for the IntelPulse threat intelligence platform.

## Overview

The CDK stack provisions the following AWS resources:
- VPC with 2 AZs, public/private subnets, NAT Gateway
- EC2 instance for TimescaleDB (PostgreSQL 16)
- ElastiCache Redis 7 cluster
- AWS OpenSearch Service domain
- ECR repositories for container images
- ECS Fargate cluster with 4 services (API, UI, Worker, Scheduler)
- Application Load Balancer with ACM certificate
- Route 53 DNS records

## Configuration

- **Region**: ap-south-1 (Mumbai)
- **Stack Name**: IntelPulseStack
- **Tags**: Project=IntelPulse, Environment=production, ManagedBy=CDK

## Prerequisites

- Node.js 18+ and npm
- AWS CLI configured with credentials
- AWS CDK CLI: `npm install -g aws-cdk`

## Useful Commands

- `npm run build` - Compile TypeScript to JavaScript
- `npm run watch` - Watch for changes and compile
- `npm run test` - Run Jest unit tests
- `npx cdk synth` - Synthesize CloudFormation template
- `npx cdk deploy` - Deploy stack to AWS
- `npx cdk diff` - Compare deployed stack with current state
- `npx cdk destroy` - Remove all resources

## Bootstrap

Before first deployment, bootstrap the CDK in your AWS account:

```bash
npx cdk bootstrap aws://ACCOUNT-ID/ap-south-1
```

## Deployment

```bash
# Synthesize CloudFormation template
npx cdk synth

# Deploy to AWS
npx cdk deploy IntelPulseStack --require-approval never

# Save outputs to file
npx cdk deploy IntelPulseStack --outputs-file outputs.json
```

## Project Structure

```
infra/
├── bin/
│   └── intelpulse.ts       # CDK app entry point
├── lib/
│   └── intelpulse-stack.ts # Main stack definition
├── test/
│   └── infra.test.ts       # Stack tests
├── cdk.json                # CDK configuration
├── package.json            # Node.js dependencies
└── tsconfig.json           # TypeScript configuration
```

## Development

The infrastructure is organized into logical components that will be implemented in subsequent tasks:

1. **Task 2**: VPC and networking
2. **Task 3**: EC2 for TimescaleDB
3. **Task 4**: ElastiCache Redis and OpenSearch
4. **Task 5**: ECR repositories
5. **Task 6**: ECS Fargate cluster and services

Each component will be added to the `IntelPulseStack` class in `lib/intelpulse-stack.ts`.
