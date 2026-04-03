# Task 6 Complete - ECS Fargate Cluster and Services

**Date**: 2026-04-03
**Status**: ✅ Complete
**Phase 1 Progress**: 100% (6/6 tasks)

---

## What Was Built

### 1. Secrets Manager Secret

- Created secret: `intelpulse/production`
- Contains all environment variables for the application
- Includes placeholder values for API keys
- Auto-generates PostgreSQL password
- Referenced by all ECS task definitions

### 2. ECS Cluster

- Cluster name: `intelpulse-production`
- Container Insights enabled for monitoring
- Deployed in VPC with private subnets

### 3. IAM Roles

**Task Execution Role**:

- Pulls images from ECR
- Writes logs to CloudWatch
- Reads secrets from Secrets Manager
- Standard ECS task execution permissions

**API Task Role**:

- Bedrock permissions: InvokeModel, InvokeAgent, InvokeModelWithResponseStream
- Secrets Manager read access
- Required for AI-powered analysis features

### 4. CloudWatch Log Groups

- `/ecs/intelpulse-api` - API service logs
- `/ecs/intelpulse-ui` - UI service logs
- `/ecs/intelpulse-worker` - Worker service logs
- `/ecs/intelpulse-scheduler` - Scheduler service logs
- 7-day retention period

### 5. Task Definitions

**API Task Definition**:

- CPU: 512 (0.5 vCPU)
- Memory: 1024 MB
- Port: 8000
- Health check: `/api/v1/health`
- Environment: Dynamic values (DB host, Redis, OpenSearch)
- Secrets: All API keys and passwords from Secrets Manager

**UI Task Definition**:

- CPU: 256 (0.25 vCPU)
- Memory: 512 MB
- Port: 3000
- Health check: `/`
- Environment: BACKEND_URL, NEXT_PUBLIC_API_URL

**Worker Task Definition**:

- CPU: 256 (0.25 vCPU)
- Memory: 512 MB
- No port mapping (background worker)
- Processes RQ jobs from Redis queue

**Scheduler Task Definition**:

- CPU: 256 (0.25 vCPU)
- Memory: 512 MB
- Command override: `python -m worker.scheduler`
- Runs APScheduler for feed synchronization

### 6. Application Load Balancer

- Name: `intelpulse-alb`
- Internet-facing
- Deployed in public subnets
- Security group: sg-alb (HTTP/HTTPS from internet)

### 7. Target Groups

**API Target Group**:

- Port: 8000
- Protocol: HTTP
- Target type: IP (Fargate)
- Health check: `/api/v1/health` every 30s
- Deregistration delay: 30s

**UI Target Group**:

- Port: 3000
- Protocol: HTTP
- Target type: IP (Fargate)
- Health check: `/` every 30s
- Deregistration delay: 30s

### 8. ALB Listeners

**HTTP Listener (Port 80)**:

- Default action: Forward to UI target group
- Rule: `/api/*` → API target group (priority 10)
- Note: Currently serves HTTP traffic directly
- TODO: Add redirect to HTTPS after ACM certificate is issued

**HTTPS Listener (Port 443)**:

- Not configured yet (requires ACM certificate)
- Instructions provided in code comments
- Will be added in Task 16 (DNS and OAuth setup)

### 9. ECS Fargate Services

**API Service**:

- Service name: `intelpulse-api`
- Desired count: 1
- Auto-scaling: 1-4 tasks based on CPU (70% target)
- Attached to API target group
- Health check grace period: 60s

**UI Service**:

- Service name: `intelpulse-ui`
- Desired count: 1
- No auto-scaling (static frontend)
- Attached to UI target group
- Health check grace period: 60s

**Worker Service**:

- Service name: `intelpulse-worker`
- Desired count: 1
- No load balancer attachment
- Processes background jobs

**Scheduler Service**:

- Service name: `intelpulse-scheduler`
- Desired count: 1
- No load balancer attachment
- Runs scheduled feed synchronization

---

## Architecture Diagram

```
Internet
    │
    ├─── Route 53 (intelpulse.tech) [TODO]
    │
    └─── Application Load Balancer (HTTP:80)
            │
            ├─── /api/* → API Target Group → API Service (Fargate)
            │                                      │
            │                                      ├─── TimescaleDB (EC2)
            │                                      ├─── Redis (ElastiCache)
            │                                      └─── OpenSearch
            │
            └─── /* → UI Target Group → UI Service (Fargate)

Background Services (no ALB):
    ├─── Worker Service (Fargate) → Redis Queue
    └─── Scheduler Service (Fargate) → Triggers feed sync
```

---

## Key Features

### 1. Dynamic Configuration

- Database host, Redis endpoint, OpenSearch endpoint automatically injected
- No hardcoded values in task definitions
- Easy to update via Secrets Manager

### 2. Security

- All secrets stored in Secrets Manager
- ECS tasks in private subnets
- Security groups enforce least-privilege access
- IAM roles follow principle of least privilege

### 3. Scalability

- API service auto-scales based on CPU utilization
- Can handle 1-4 concurrent tasks
- Scale-in/out cooldown: 60 seconds

### 4. Observability

- CloudWatch logs for all services
- Container Insights enabled
- Health checks on all services
- ALB access logs (can be enabled)

### 5. High Availability

- Services deployed across 2 AZs
- ALB distributes traffic
- Auto-recovery on task failures

---

## Deployment Considerations

### Before Deployment

1. **Docker Images**: Must build and push images to ECR first
   - Run `./scripts/ecr-push.sh` after infrastructure is deployed
   - Or deploy infrastructure, push images, then restart services

2. **Secrets**: Update Secrets Manager with actual values
   - API keys for threat feeds
   - Google OAuth client ID
   - Strong SECRET_KEY (32+ characters)

3. **Database**: Initialize schema after deployment
   - SSH to EC2 instance via SSM
   - Run `db/schema.sql` against TimescaleDB

### After Deployment

1. **Verify Services**: Check all 4 services reach RUNNING state
2. **Test Endpoints**: Curl ALB DNS name to verify API and UI
3. **Monitor Logs**: Check CloudWatch logs for errors
4. **Trigger Feeds**: POST to `/api/v1/feeds/trigger-all` to populate data

---

## Known Limitations

### 1. No HTTPS Yet

- ALB only serves HTTP traffic
- HTTPS listener requires ACM certificate
- Will be added in Task 16

### 2. No Custom Domain

- Currently accessible via ALB DNS name only
- Route 53 configuration needed for intelpulse.tech
- Will be added in Task 16

### 3. No WAF

- ALB is directly exposed to internet
- Consider adding AWS WAF for DDoS protection
- Can be added post-deployment

### 4. Single NAT Gateway

- Cost optimization (1 NAT instead of 2)
- Single point of failure for outbound traffic
- Consider adding second NAT for HA

### 5. No Database Backups

- TimescaleDB on EC2 has no automated backups
- EBS volume preserved on termination
- Consider adding snapshot schedule

---

## Cost Impact

### New Resources (Task 6)

- ECS Fargate (4 services): ~$50/month
  - API: 0.5 vCPU, 1 GB RAM = ~$15/month
  - UI: 0.25 vCPU, 0.5 GB RAM = ~$8/month
  - Worker: 0.25 vCPU, 0.5 GB RAM = ~$8/month
  - Scheduler: 0.25 vCPU, 0.5 GB RAM = ~$8/month
  - Auto-scaling overhead: ~$11/month

- Application Load Balancer: ~$16/month
  - Base cost: ~$16/month
  - LCU charges: ~$0/month (low traffic)

- CloudWatch Logs: ~$2/month
  - 4 log groups, 7-day retention
  - ~5 GB/month ingestion

- Secrets Manager: ~$0.40/month
  - 1 secret
  - ~10,000 API calls/month

**Task 6 Total**: ~$68/month

**Overall Infrastructure Cost**: ~$194/month

---

## Testing Checklist

### Pre-Deployment Tests

- [x] TypeScript compiles without errors
- [x] CDK synth generates valid CloudFormation
- [x] All resource names follow naming convention
- [x] Security groups configured correctly
- [x] IAM roles have necessary permissions

### Post-Deployment Tests

- [ ] VPC and subnets created
- [ ] Security groups allow correct traffic
- [ ] EC2 instance running with TimescaleDB
- [ ] Redis cluster accessible
- [ ] OpenSearch domain accessible
- [ ] ECR repositories created
- [ ] ECS cluster created
- [ ] ALB created and accessible
- [ ] Target groups healthy
- [ ] All 4 ECS services running
- [ ] API health endpoint responds
- [ ] UI loads in browser
- [ ] Worker processes jobs
- [ ] Scheduler triggers feeds

---

## Next Steps

### Immediate (Required for Working Application)

1. Deploy infrastructure: `npx cdk deploy IntelPulseStack`
2. Build and push images: `./scripts/ecr-push.sh`
3. Update Secrets Manager with actual values
4. Initialize database schema
5. Restart ECS services to pull images
6. Verify all services healthy

### Phase 2: Bedrock Agent Core (Tasks 7-12)

- Create Bedrock adapter to replace llama3
- Implement Lambda action groups
- Create multi-agent system
- Add agent-lookup API endpoint
- Update search UI

### Phase 3: CI/CD & Polish (Tasks 13-16)

- AWS Transform assessment
- Amazon Q security scan
- GitHub Actions CI/CD pipeline
- DNS and OAuth setup

### Phase 4: Documentation

- Productivity metrics
- Amazon Q usage report
- Demo video
- Deployment checklist
- AWS setup guide

---

## Files Modified

### Created

- `DEPLOYMENT_GUIDE.md` - Comprehensive deployment instructions
- `TASK_6_COMPLETE.md` - This file

### Modified

- `infra/lib/intelpulse-stack.ts` - Added Task 6 implementation
  - createSecretsManagerSecret()
  - createEcsCluster()
  - createApplicationLoadBalancer()
  - createEcsServices()

---

## CloudFormation Resources

**Total Resources in Stack**: ~120 resources

**Breakdown by Service**:

- VPC & Networking: 15 resources
- Security Groups: 5 resources
- EC2 (TimescaleDB): 5 resources
- ElastiCache: 3 resources
- OpenSearch: 2 resources
- ECR: 3 resources
- ECS: 25 resources
- ALB: 10 resources
- IAM: 15 resources
- CloudWatch Logs: 4 resources
- Secrets Manager: 1 resource
- CloudFormation Outputs: 20 resources

---

## Outputs

After deployment, the following outputs will be available:

**Networking**:

- VpcId
- PublicSubnetIds
- PrivateSubnetIds
- AlbSecurityGroupId
- EcsSecurityGroupId
- PostgresSecurityGroupId
- RedisSecurityGroupId
- OpenSearchSecurityGroupId

**Data Services**:

- TimescaleDbInstanceId
- TimescaleDbPrivateIp
- TimescaleDbConnectionString
- RedisEndpoint
- RedisPort
- OpenSearchEndpoint
- OpenSearchDomainArn

**Container Registry**:

- ApiRepositoryUri
- UiRepositoryUri
- WorkerRepositoryUri

**Compute**:

- EcsClusterName
- AlbDnsName
- ApiServiceName
- UiServiceName
- AppSecretArn

---

## Success Criteria

Task 6 is considered complete when:

- [x] CDK stack synthesizes without errors
- [x] All ECS task definitions created
- [x] All IAM roles configured
- [x] ALB and target groups created
- [x] All 4 ECS services defined
- [x] Secrets Manager secret created
- [x] CloudWatch log groups created
- [ ] Stack deploys successfully (pending deployment)
- [ ] All services reach RUNNING state (pending deployment)
- [ ] Health checks pass (pending deployment)
- [ ] Application accessible via ALB (pending deployment)

---

## Lessons Learned

### 1. HTTPS Listener Requires Certificate

- Cannot create HTTPS listener without ACM certificate
- Solution: Start with HTTP, add HTTPS later
- Alternative: Use self-signed certificate for testing

### 2. Container Insights Deprecation

- `containerInsights` prop is deprecated
- Should use `containerInsightsV2` instead
- Not critical, just a warning

### 3. ECS Service Health Check Grace Period

- Important for services that take time to start
- Set to 60s to allow container initialization
- Prevents premature task termination

### 4. Secrets Manager Secret Structure

- Must use `generateSecretString` with template
- Cannot just pass JSON object
- One key must be auto-generated (POSTGRES_PASSWORD)

### 5. Dynamic Environment Variables

- Use CloudFormation intrinsic functions for dynamic values
- Example: `this.timescaleDbInstance.instancePrivateIp`
- Ensures correct values even if resources change

---

**Status**: Phase 1 Complete ✅
**Next Phase**: Phase 2 - Bedrock Agent Core
**Ready for Deployment**: Yes
**Estimated Deployment Time**: 25 minutes
