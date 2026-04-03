# Session 3 Progress - AWS Infrastructure Migration

**Date**: 2026-04-03
**Duration**: ~30 minutes
**Branch**: aws-migration
**Region**: us-east-1

---

## Completed Tasks ✅

### 1. CDK Bootstrap

- Successfully bootstrapped CDK in us-east-1 region
- Created CDKToolkit CloudFormation stack with:
  - S3 staging bucket for CDK assets
  - ECR repository for container assets
  - IAM roles for deployment, file publishing, image publishing
  - SSM parameter for bootstrap version

### 2. Task 3: EC2 for TimescaleDB ✅

**Status**: Complete

**Implementation**:

- Created EC2 t3.medium instance in private subnet
- Amazon Linux 2023 AMI with Docker pre-installed
- 50 GB EBS gp3 volume (encrypted, preserved on termination)
- User data script that:
  - Installs Docker
  - Runs TimescaleDB container (timescale/timescaledb:latest-pg16)
  - Generates secure random PostgreSQL password
  - Stores password in SSM Parameter Store: `/intelpulse/production/postgres-password`
  - Configures database: `intelpulse` user and database
- IAM role with SSM managed instance core + SSM PutParameter permissions
- Security group: sg-postgres (port 5432 from ECS tasks only)

**Outputs**:

- TimescaleDB Instance ID
- TimescaleDB Private IP
- Connection string template

### 3. Task 4: ElastiCache Redis and OpenSearch ✅

**Status**: Complete

**Redis Implementation**:

- ElastiCache Redis 7.0 cluster
- Single-node cache.t3.micro instance
- Deployed in private subnets with subnet group
- Security group: sg-redis (port 6379 from ECS tasks only)
- Automated snapshots: daily at 03:00-04:00, 5-day retention
- Maintenance window: Sunday 05:00-06:00

**OpenSearch Implementation**:

- OpenSearch 2.13 domain
- Single-node t3.small.search instance
- 20 GB EBS gp3 volume
- Deployed in private subnet (first AZ)
- Security group: sg-opensearch (port 443 from ECS tasks only)
- Encryption: HTTPS enforced, node-to-node encryption, encryption at rest
- VPC-based security (no fine-grained access control)
- Multi-AZ explicitly disabled for T3 instance compatibility

**Outputs**:

- Redis endpoint address and port
- OpenSearch domain endpoint and ARN

### 4. Task 5: ECR Repositories ✅

**Status**: Complete

**Implementation**:

- Created 3 ECR repositories:
  - `intelpulse/api` - FastAPI backend
  - `intelpulse/ui` - Next.js frontend
  - `intelpulse/worker` - Python RQ worker
- Image scanning enabled on push
- Mutable image tags
- Lifecycle policy: keep last 10 images
- Removal policy: DESTROY (for development)

**Outputs**:

- API repository URI
- UI repository URI
- Worker repository URI

**ECR Push Script**:

- Created `scripts/ecr-push.sh` for building and pushing images
- Features:
  - ECR login with AWS CLI
  - Builds all 3 Docker images using existing Dockerfiles
  - Tags with git SHA and 'latest'
  - Pushes to ECR repositories
  - Displays image URIs for deployment

---

## Infrastructure Summary

### Resources Created (Tasks 1-5)

**Networking** (Task 2):

- 1 VPC (10.0.0.0/16)
- 2 Public subnets (10.0.0.0/24, 10.0.1.0/24)
- 2 Private subnets (10.0.2.0/24, 10.0.3.0/24)
- 1 Internet Gateway
- 1 NAT Gateway
- 5 Security Groups (ALB, ECS, PostgreSQL, Redis, OpenSearch)

**Data Tier** (Tasks 3-4):

- 1 EC2 t3.medium (TimescaleDB)
- 1 ElastiCache Redis cluster (cache.t3.micro)
- 1 OpenSearch domain (t3.small.search)

**Container Registry** (Task 5):

- 3 ECR repositories (API, UI, Worker)

**Total CloudFormation Resources**: ~60 resources

---

## Next Steps

### Task 6: ECS Fargate Cluster and Services

**Estimated Time**: 2-3 hours

**Subtasks**:

1. Create ECS cluster
2. Create Secrets Manager secret with all environment variables
3. Create IAM task execution role (ECR, CloudWatch Logs, Secrets Manager)
4. Create IAM task role for API (Bedrock permissions)
5. Create 4 task definitions:
   - API service (512 CPU, 1024 MB, port 8000)
   - UI service (256 CPU, 512 MB, port 3000)
   - Worker service (256 CPU, 512 MB, no port)
   - Scheduler service (256 CPU, 512 MB, command override)
6. Create Application Load Balancer (internet-facing)
7. Request ACM certificate for intelpulse.tech
8. Create ALB listeners (HTTP:80 redirect, HTTPS:443)
9. Create target groups (API, UI)
10. Create listener rules (/api/*→ API, /* → UI)
11. Create 4 Fargate services with auto-scaling
12. Verify services reach RUNNING state

**Blockers**:

- Need to populate Secrets Manager with actual values
- Need ACM certificate (requires DNS validation)
- Need to build and push Docker images to ECR first

---

## Deployment Strategy

### Option 1: Deploy Infrastructure First (Recommended)

```bash
cd infra
npx cdk deploy IntelPulseStack
```

**Pros**:

- Creates all infrastructure resources
- Validates networking and security groups
- Provisions data services (TimescaleDB, Redis, OpenSearch)
- Creates ECR repositories

**Cons**:

- Cannot deploy ECS services yet (no images in ECR)
- Need to add Task 6 code first

### Option 2: Complete Task 6, Then Deploy

```bash
# 1. Add ECS Fargate code to CDK stack
# 2. Build and push images to ECR
./scripts/ecr-push.sh
# 3. Deploy full stack
cd infra
npx cdk deploy IntelPulseStack
```

**Pros**:

- Single deployment with all resources
- ECS services start immediately

**Cons**:

- Longer initial deployment time
- More complex troubleshooting if issues arise

---

## Cost Estimate (Current State)

**Monthly Costs** (Tasks 1-5):

- VPC, subnets, IGW: Free
- NAT Gateway: ~$32/month
- EC2 t3.medium (TimescaleDB): ~$30/month
- EBS gp3 50 GB: ~$4/month
- ElastiCache Redis (cache.t3.micro): ~$12/month
- OpenSearch (t3.small.search): ~$40/month
- ECR storage: ~$1/month (for 10 images)

**Subtotal**: ~$119/month

**After Task 6** (ECS Fargate):

- ECS Fargate (4 services): ~$50/month
- ALB: ~$16/month
- Data transfer: ~$10/month

**Total Estimated**: ~$195/month

---

## Files Modified

### Created

- `scripts/ecr-push.sh` - ECR image build and push script

### Modified

- `infra/lib/intelpulse-stack.ts` - Added Tasks 3, 4, 5 implementations

---

## Git Status

**Branch**: aws-migration
**Commits Ready**:

1. `infra: add EC2 TimescaleDB instance with automated setup`
2. `infra: add ElastiCache Redis and OpenSearch Service`
3. `infra: add ECR repositories and push script`

**Next Commit**: After Task 6 completion

---

## Testing Checklist

### Before Deployment

- [x] CDK bootstrap successful
- [x] TypeScript compiles without errors
- [x] CDK synth generates valid CloudFormation
- [ ] Review synthesized template for security issues
- [ ] Verify all resource names follow naming convention

### After Deployment

- [ ] VPC and subnets created
- [ ] Security groups configured correctly
- [ ] EC2 instance running with TimescaleDB container
- [ ] PostgreSQL password stored in SSM Parameter Store
- [ ] Redis cluster endpoint accessible from VPC
- [ ] OpenSearch domain endpoint accessible from VPC
- [ ] ECR repositories created and accessible

---

## Known Issues

### 1. OpenSearch Multi-AZ Configuration

**Issue**: T3 instance types don't support Multi-AZ with standby
**Resolution**: Explicitly set `multiAzWithStandbyEnabled: false`
**Status**: ✅ Fixed

### 2. Database Schema Initialization

**Issue**: User data script doesn't initialize database schema
**Resolution**: Need to manually run `db/schema.sql` after deployment
**Status**: ⚠️ To be addressed in Task 6 or post-deployment

### 3. Secrets Management

**Issue**: PostgreSQL password generated randomly, need to retrieve from SSM
**Resolution**: Document retrieval process in deployment guide
**Status**: ⚠️ To be documented

---

## Documentation Updates Needed

1. Update `infra/DEPLOYMENT.md` with:
   - Bootstrap instructions ✅ (already done)
   - Task 3-5 deployment steps
   - Post-deployment verification steps
   - Database initialization instructions

2. Update `PROGRESS_TRACKER.md`:
   - Mark Tasks 3, 4, 5 as complete
   - Update Phase 1 progress to 83% (5/6 tasks)
   - Update overall progress to ~30%

3. Create `docs/AWS_INFRASTRUCTURE_GUIDE.md`:
   - Architecture diagram
   - Resource inventory
   - Networking topology
   - Security group rules
   - Cost breakdown

---

## Recommendations

### Immediate Next Steps

1. **Commit current progress** to git
2. **Choose deployment strategy** (Option 1 or 2)
3. **Start Task 6** (ECS Fargate) if continuing infrastructure work
4. **OR switch to Phase 2** (Bedrock Agent Core) if infrastructure can wait

### Priority Considerations

- **Infrastructure-first approach**: Validates networking and data services early
- **Bedrock-first approach**: Demonstrates AI capabilities sooner for codethon
- **Parallel approach**: One developer on infrastructure, another on Bedrock

### Risk Mitigation

- Test TimescaleDB connectivity before deploying ECS services
- Verify Redis and OpenSearch endpoints are accessible
- Document all manual steps for reproducibility
- Create rollback plan for each deployment phase

---

**Session End Time**: 2026-04-03 ~3:15 PM
**Next Session**: Continue with Task 6 (ECS Fargate) or Phase 2 (Bedrock)
**Status**: Infrastructure 83% complete (5/6 tasks), ready for deployment or Task 6
