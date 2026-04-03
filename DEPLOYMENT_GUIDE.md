# IntelPulse AWS Deployment Guide

**Last Updated**: 2026-04-03
**Stack**: IntelPulseStack
**Region**: us-east-1
**Status**: Ready for deployment

---

## Prerequisites ✅

- [x] AWS CLI configured with credentials
- [x] AWS account: 604275788592
- [x] CDK bootstrapped in us-east-1
- [x] Docker installed (for building images)
- [x] Git repository: <https://github.com/manishjnv/IntelPulse>

---

## Architecture Overview

### Infrastructure Components

**Networking**:

- VPC: 10.0.0.0/16 (2 AZs)
- 2 Public subnets + 2 Private subnets
- 1 NAT Gateway
- 5 Security Groups

**Data Tier**:

- EC2 t3.medium (TimescaleDB)
- ElastiCache Redis 7.0
- OpenSearch 2.13

**Compute**:

- ECS Fargate cluster
- 4 services: API, UI, Worker, Scheduler
- Application Load Balancer

**Container Registry**:

- 3 ECR repositories

**Secrets**:

- Secrets Manager for environment variables

---

## Deployment Steps

### Step 1: Build and Push Docker Images

Before deploying the infrastructure, you need to build and push Docker images to ECR.

**Important**: The ECR repositories will be created during deployment, so you need to:

1. Deploy infrastructure first (without ECS services running)
2. Build and push images
3. Update ECS services to use the images

**OR** use the following approach:

```bash
# Option A: Deploy infrastructure, then build images
cd infra
npx cdk deploy IntelPulseStack

# Wait for deployment to complete, then:
cd ..
./scripts/ecr-push.sh

# Option B: Build placeholder images first (not recommended)
# This requires manually creating ECR repos first
```

### Step 2: Deploy Infrastructure

```bash
cd infra

# Review what will be deployed
npx cdk diff

# Deploy the stack
npx cdk deploy IntelPulseStack

# Or deploy with automatic approval (no prompts)
npx cdk deploy IntelPulseStack --require-approval never

# Save outputs to file
npx cdk deploy IntelPulseStack --outputs-file outputs.json
```

**Deployment Time**: ~20-25 minutes

**What gets created**:

- VPC and networking (~5 min)
- EC2 instance for TimescaleDB (~3 min)
- ElastiCache Redis (~10 min)
- OpenSearch domain (~15 min)
- ECR repositories (~1 min)
- ECS cluster (~1 min)
- ALB and target groups (~2 min)
- ECS services (~3 min)
- Secrets Manager secret (~1 min)

### Step 3: Update Secrets Manager

After deployment, update the Secrets Manager secret with actual values:

```bash
# Get the secret ARN from outputs
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AppSecretArn`].OutputValue' \
  --output text)

# Update secret with actual values
aws secretsmanager update-secret \
  --secret-id $SECRET_ARN \
  --secret-string '{
    "ENVIRONMENT": "production",
    "LOG_LEVEL": "INFO",
    "SECRET_KEY": "YOUR_RANDOM_32_CHAR_STRING_HERE",
    "DOMAIN": "intelpulse.tech",
    "DOMAIN_UI": "https://intelpulse.tech",
    "DOMAIN_API": "https://intelpulse.tech/api",
    "POSTGRES_DB": "intelpulse",
    "POSTGRES_USER": "intelpulse",
    "POSTGRES_PASSWORD": "RETRIEVE_FROM_SSM_PARAMETER_STORE",
    "OPENSEARCH_USER": "admin",
    "OPENSEARCH_VERIFY_CERTS": "false",
    "DEV_BYPASS_AUTH": "false",
    "JWT_EXPIRE_MINUTES": "480",
    "AI_API_URL": "bedrock",
    "AI_MODEL": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "AI_TIMEOUT": "30",
    "AI_ENABLED": "true",
    "NEXT_PUBLIC_APP_NAME": "IntelPulse",
    "NVD_API_KEY": "YOUR_NVD_API_KEY",
    "ABUSEIPDB_API_KEY": "YOUR_ABUSEIPDB_API_KEY",
    "OTX_API_KEY": "YOUR_OTX_API_KEY",
    "VIRUSTOTAL_API_KEY": "YOUR_VIRUSTOTAL_API_KEY",
    "SHODAN_API_KEY": "YOUR_SHODAN_API_KEY",
    "GOOGLE_CLIENT_ID": "YOUR_GOOGLE_CLIENT_ID"
  }'

# Retrieve PostgreSQL password from SSM
POSTGRES_PASSWORD=$(aws ssm get-parameter \
  --name "/intelpulse/production/postgres-password" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)

echo "PostgreSQL Password: $POSTGRES_PASSWORD"
```

### Step 4: Initialize Database Schema

SSH into the TimescaleDB EC2 instance and initialize the database:

```bash
# Get instance ID
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`TimescaleDbInstanceId`].OutputValue' \
  --output text)

# Connect via SSM Session Manager
aws ssm start-session --target $INSTANCE_ID

# Inside the instance:
# 1. Copy schema.sql to the instance
# 2. Run the schema initialization
docker exec -i timescaledb psql -U intelpulse -d intelpulse < /path/to/schema.sql
```

**Alternative**: Use a one-time ECS task to run migrations.

### Step 5: Build and Push Docker Images

```bash
# Make script executable
chmod +x scripts/ecr-push.sh

# Build and push all images
./scripts/ecr-push.sh

# This will:
# 1. Login to ECR
# 2. Build API, UI, Worker images
# 3. Tag with git SHA and 'latest'
# 4. Push to ECR repositories
```

**Build Time**: ~10-15 minutes (depending on your machine)

### Step 6: Restart ECS Services

After pushing images, restart ECS services to pull the new images:

```bash
# Restart API service
aws ecs update-service \
  --cluster intelpulse-production \
  --service intelpulse-api \
  --force-new-deployment

# Restart UI service
aws ecs update-service \
  --cluster intelpulse-production \
  --service intelpulse-ui \
  --force-new-deployment

# Restart Worker service
aws ecs update-service \
  --cluster intelpulse-production \
  --service intelpulse-worker \
  --force-new-deployment

# Restart Scheduler service
aws ecs update-service \
  --cluster intelpulse-production \
  --service intelpulse-scheduler \
  --force-new-deployment

# Wait for services to stabilize
aws ecs wait services-stable \
  --cluster intelpulse-production \
  --services intelpulse-api intelpulse-ui intelpulse-worker intelpulse-scheduler
```

### Step 7: Verify Deployment

```bash
# Get ALB DNS name
ALB_DNS=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`AlbDnsName`].OutputValue' \
  --output text)

echo "Application URL: http://$ALB_DNS"

# Test API health endpoint
curl http://$ALB_DNS/api/v1/health

# Test UI
curl http://$ALB_DNS/

# Check ECS service status
aws ecs describe-services \
  --cluster intelpulse-production \
  --services intelpulse-api intelpulse-ui intelpulse-worker intelpulse-scheduler \
  --query 'services[*].[serviceName,status,runningCount,desiredCount]' \
  --output table
```

### Step 8: Configure DNS (Optional)

If you have the domain `intelpulse.tech`:

```bash
# Create Route 53 hosted zone (if not exists)
aws route53 create-hosted-zone \
  --name intelpulse.tech \
  --caller-reference $(date +%s)

# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name intelpulse.tech \
  --query 'HostedZones[0].Id' \
  --output text)

# Create A record pointing to ALB
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "intelpulse.tech",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "'$ALB_DNS'",
          "EvaluateTargetHealth": false
        }
      }
    }]
  }'
```

### Step 9: Request ACM Certificate (Optional)

For HTTPS support:

```bash
# Request certificate
CERT_ARN=$(aws acm request-certificate \
  --domain-name intelpulse.tech \
  --validation-method DNS \
  --query 'CertificateArn' \
  --output text)

# Get DNS validation records
aws acm describe-certificate \
  --certificate-arn $CERT_ARN \
  --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Add the CNAME record to Route 53 for validation
# Then wait for certificate to be issued

# Update ALB listener to use HTTPS (requires code change in CDK stack)
```

---

## Post-Deployment Tasks

### 1. Trigger Initial Feed Sync

```bash
# Trigger all feeds to populate initial data
curl -X POST http://$ALB_DNS/api/v1/feeds/trigger-all
```

### 2. Create Admin User

```bash
# Create admin user via API
curl -X POST http://$ALB_DNS/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@intelpulse.tech",
    "name": "Admin User",
    "role": "admin"
  }'
```

### 3. Monitor Services

```bash
# View API logs
aws logs tail /ecs/intelpulse-api --follow

# View UI logs
aws logs tail /ecs/intelpulse-ui --follow

# View Worker logs
aws logs tail /ecs/intelpulse-worker --follow

# View Scheduler logs
aws logs tail /ecs/intelpulse-scheduler --follow
```

---

## Troubleshooting

### ECS Services Not Starting

**Symptom**: Services stuck in "PENDING" state

**Solutions**:

1. Check if Docker images exist in ECR
2. Verify Secrets Manager secret has all required keys
3. Check security group rules allow ECS tasks to reach data services
4. Review CloudWatch logs for error messages

```bash
# Check task status
aws ecs describe-tasks \
  --cluster intelpulse-production \
  --tasks $(aws ecs list-tasks --cluster intelpulse-production --service-name intelpulse-api --query 'taskArns[0]' --output text)
```

### Database Connection Issues

**Symptom**: API logs show "Connection refused" to PostgreSQL

**Solutions**:

1. Verify TimescaleDB container is running on EC2
2. Check security group allows port 5432 from ECS security group
3. Verify PostgreSQL password in Secrets Manager matches SSM parameter

```bash
# Check TimescaleDB container
aws ssm start-session --target $INSTANCE_ID
docker ps
docker logs timescaledb
```

### Redis Connection Issues

**Symptom**: API logs show "Connection refused" to Redis

**Solutions**:

1. Verify Redis cluster is in "available" state
2. Check security group allows port 6379 from ECS security group
3. Verify Redis endpoint in environment variables

```bash
# Check Redis status
aws elasticache describe-cache-clusters \
  --cache-cluster-id intelpulse-redis \
  --show-cache-node-info
```

### OpenSearch Connection Issues

**Symptom**: API logs show "Connection refused" to OpenSearch

**Solutions**:

1. Verify OpenSearch domain is in "Active" state
2. Check security group allows port 443 from ECS security group
3. Verify OpenSearch endpoint in environment variables

```bash
# Check OpenSearch status
aws opensearch describe-domain \
  --domain-name intelpulse-opensearch
```

---

## Rollback

If deployment fails or you need to rollback:

```bash
# Delete the stack
npx cdk destroy IntelPulseStack

# Or rollback to previous version
aws cloudformation cancel-update-stack --stack-name IntelPulseStack
```

---

## Cost Optimization

### Current Monthly Costs

- NAT Gateway: ~$32/month
- EC2 t3.medium: ~$30/month
- EBS gp3 50 GB: ~$4/month
- ElastiCache Redis: ~$12/month
- OpenSearch t3.small: ~$40/month
- ECS Fargate (4 services): ~$50/month
- ALB: ~$16/month
- Data transfer: ~$10/month

**Total**: ~$194/month

### Cost Reduction Options

1. **Use Spot Instances for Worker**: Save ~70% on worker costs
2. **Reduce NAT Gateway**: Use VPC endpoints for AWS services
3. **Downsize OpenSearch**: Use t3.micro instead of t3.small
4. **Reduce ECS Task Count**: Scale down during off-hours
5. **Use Reserved Instances**: Save ~40% on EC2 costs

---

## Monitoring and Alerts

### CloudWatch Dashboards

Create a dashboard to monitor:

- ECS service CPU/Memory utilization
- ALB request count and latency
- RDS/Redis/OpenSearch metrics
- API error rates

### CloudWatch Alarms

Set up alarms for:

- ECS service unhealthy tasks
- ALB 5xx error rate > 5%
- API response time > 2s
- Database CPU > 80%
- Redis memory > 80%

---

## Security Checklist

- [x] All data services in private subnets
- [x] Security groups follow least-privilege principle
- [x] Secrets stored in Secrets Manager
- [x] EBS volumes encrypted
- [x] OpenSearch encryption at rest enabled
- [x] CloudWatch logs enabled for all services
- [ ] HTTPS enabled (requires ACM certificate)
- [ ] WAF rules configured on ALB
- [ ] VPC Flow Logs enabled
- [ ] GuardDuty enabled

---

## Next Steps

1. **Add HTTPS Support**: Request ACM certificate and update ALB listener
2. **Configure DNS**: Point intelpulse.tech to ALB
3. **Set up CI/CD**: GitHub Actions workflow for automated deployments
4. **Add Monitoring**: CloudWatch dashboards and alarms
5. **Implement Bedrock Agents**: Phase 2 of migration
6. **Run Security Scan**: Amazon Q security scan
7. **Performance Testing**: Load test the application
8. **Backup Strategy**: Automated snapshots for data services

---

## Support

For issues or questions:

- GitHub: <https://github.com/manishjnv/IntelPulse>
- Documentation: docs/
- AWS Support: <https://console.aws.amazon.com/support/>

---

**Deployment Status**: Ready ✅
**Last Tested**: 2026-04-03
**CDK Version**: 2.x
**Region**: us-east-1
