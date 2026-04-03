# Deployment Failure Analysis

**Date**: 2026-04-03
**Stack**: IntelPulseStack
**Status**: DELETE_IN_PROGRESS (rollback after failure)

---

## 🔴 Root Cause Identified

### Primary Failure: EC2 Instance Type Not Free Tier Eligible

**Failed Resource**: `TimescaleDbInstanceE100262F691bbd6ddacab746`

**Error Message**:

```
The specified instance type is not eligible for Free Tier. 
For a list of Free Tier instance types, run 'describe-instance-types' 
with the filter 'free-tier-eligible=true'.
(Service: Ec2, Status Code: 400, Request ID: 3d00e586-23c4-4df0-918c-fa4ce7e6ed5a)
```

**What Happened**:

- The CDK stack tried to create an EC2 t3.medium instance for TimescaleDB
- AWS rejected it because t3.medium is NOT eligible for Free Tier
- Your AWS account appears to be a Free Tier account
- This caused the entire stack to fail and rollback

---

## 📋 Failed Resources

All these resources failed due to the EC2 failure (cascade effect):

1. ❌ **TimescaleDbInstanceE100262F691bbd6ddacab746** - EC2 instance (PRIMARY FAILURE)
2. ❌ **OpenSearchDomain85D65221** - OpenSearch domain (cancelled)
3. ❌ **RedisCluster** - ElastiCache Redis (cancelled)
4. ❌ **ApplicationLoadBalancerFD56DEE1** - ALB (cancelled)
5. ❌ **IntelPulseVpcPublicSubnet1NATGateway4359AAA0** - NAT Gateway (cancelled)

**Note**: Resources 2-5 were cancelled because resource 1 failed first.

---

## 🛠️ Solution Options

### Option 1: Use Free Tier Eligible Instance (Recommended for Testing)

**Change**: t3.medium → t2.micro (Free Tier eligible)

**Pros**:

- ✅ Free for 12 months (750 hours/month)
- ✅ No cost during testing
- ✅ Sufficient for demo/testing

**Cons**:

- ⚠️ Limited resources (1 vCPU, 1 GB RAM)
- ⚠️ May be slow for production workloads
- ⚠️ TimescaleDB may struggle with large datasets

**Code Change**:

```typescript
// In infra/lib/intelpulse-stack.ts
const timescaleDbInstance = new ec2.Instance(this, 'TimescaleDbInstance', {
  vpc,
  instanceType: ec2.InstanceType.of(
    ec2.InstanceClass.T2,  // Change from T3
    ec2.InstanceSize.MICRO // Change from MEDIUM
  ),
  // ... rest of config
});
```

### Option 2: Use t3.small (Cheaper than t3.medium)

**Change**: t3.medium → t3.small

**Pros**:

- ✅ Better performance than t2.micro (2 vCPU, 2 GB RAM)
- ✅ Cheaper than t3.medium (~$15/month vs ~$30/month)
- ✅ Sufficient for small-scale production

**Cons**:

- ❌ Not Free Tier eligible
- ❌ Costs ~$15/month

**Code Change**:

```typescript
const timescaleDbInstance = new ec2.Instance(this, 'TimescaleDbInstance', {
  vpc,
  instanceType: ec2.InstanceType.of(
    ec2.InstanceClass.T3,
    ec2.InstanceSize.SMALL // Change from MEDIUM
  ),
  // ... rest of config
});
```

### Option 3: Keep t3.medium (Original Plan)

**No Change**: Keep t3.medium

**Pros**:

- ✅ Best performance (2 vCPU, 4 GB RAM)
- ✅ Suitable for production workloads
- ✅ As originally designed

**Cons**:

- ❌ Not Free Tier eligible
- ❌ Costs ~$30/month
- ❌ Requires upgrading AWS account or waiting for Free Tier to expire

---

## 💰 Cost Comparison

| Instance Type | vCPU | RAM | Cost/Month | Free Tier |
|---------------|------|-----|------------|-----------|
| t2.micro | 1 | 1 GB | $0 (Free Tier) | ✅ Yes |
| t3.small | 2 | 2 GB | ~$15 | ❌ No |
| t3.medium | 2 | 4 GB | ~$30 | ❌ No |

---

## 🎯 Recommended Action

### For Demo/Testing: Use t2.micro (Option 1)

**Why**:

- Free for 12 months
- Sufficient for codethon demo
- Can upgrade later for production

**Steps**:

1. Update `infra/lib/intelpulse-stack.ts`
2. Change instance type to t2.micro
3. Redeploy: `cdk deploy`

### For Production: Use t3.small (Option 2)

**Why**:

- Better performance than t2.micro
- Cheaper than t3.medium
- Good balance of cost and performance

---

## 📝 Code Fix

### File: `infra/lib/intelpulse-stack.ts`

**Find this line** (around line 150-200):

```typescript
instanceType: ec2.InstanceType.of(
  ec2.InstanceClass.T3,
  ec2.InstanceSize.MEDIUM
),
```

**Replace with** (for Free Tier):

```typescript
instanceType: ec2.InstanceType.of(
  ec2.InstanceClass.T2,
  ec2.InstanceSize.MICRO
),
```

**OR Replace with** (for better performance):

```typescript
instanceType: ec2.InstanceType.of(
  ec2.InstanceClass.T3,
  ec2.InstanceSize.SMALL
),
```

---

## 🚀 Next Steps

### 1. Wait for Deletion to Complete

Current status: DELETE_IN_PROGRESS

**Estimated time**: 10-15 minutes

Check status:

```bash
aws cloudformation describe-stacks --stack-name IntelPulseStack --query 'Stacks[0].StackStatus'
```

Wait for: `DELETE_COMPLETE` or stack not found

### 2. Update CDK Code

```bash
# Open the file
code infra/lib/intelpulse-stack.ts

# Find and update the instance type
# (See code fix above)
```

### 3. Redeploy

```bash
cd infra
cdk deploy --require-approval never
```

**Estimated time**: 20-25 minutes

---

## ⚠️ Other Potential Issues

### Free Tier Limits

If you're on Free Tier, be aware of these limits:

| Service | Free Tier Limit | Stack Usage | Status |
|---------|----------------|-------------|--------|
| EC2 | 750 hours/month (t2.micro) | 1 instance | ✅ OK with t2.micro |
| EBS | 30 GB | 50 GB | ⚠️ Exceeds (costs ~$4/month) |
| NAT Gateway | Not included | 1 NAT | ❌ Costs ~$32/month |
| ElastiCache | Not included | 1 cluster | ❌ Costs ~$12/month |
| OpenSearch | Not included | 1 domain | ❌ Costs ~$40/month |
| ALB | Not included | 1 ALB | ❌ Costs ~$16/month |

**Total Monthly Cost** (even with t2.micro): ~$104/month

**Note**: Only EC2 and EBS have Free Tier. Other services will incur charges.

---

## 💡 Cost Optimization Tips

### For Demo/Testing Only

1. **Use t2.micro** for EC2 (Free Tier)
2. **Reduce EBS** to 30 GB (Free Tier)
3. **Consider**: Deploy only when needed, destroy after demo
4. **Alternative**: Use LocalStack for local testing (no AWS costs)

### For Production

1. Keep current architecture
2. Monitor costs with AWS Cost Explorer
3. Set up billing alerts
4. Use Reserved Instances for long-term savings

---

## 📊 Deployment Timeline

### Current Status

- ✅ Phase 0: Preparation (Complete)
- ✅ Phase 1: Infrastructure code (Complete)
- ❌ Phase 1: Infrastructure deployment (Failed - fixing)
- ⏳ Phase 2: Bedrock (Pending)
- ⏳ Phase 3: CI/CD (Pending)
- ⏳ Phase 4: Documentation (Pending)

### After Fix

1. Update instance type: 5 minutes
2. Wait for deletion: 10-15 minutes
3. Redeploy: 20-25 minutes
4. **Total**: ~40 minutes

---

## ✅ Verification Checklist

After redeployment:

- [ ] Stack status: CREATE_COMPLETE
- [ ] EC2 instance running
- [ ] ElastiCache Redis available
- [ ] OpenSearch domain active
- [ ] ALB healthy
- [ ] ECS services running
- [ ] No errors in CloudWatch logs

---

## 📞 Support

### Check Free Tier Usage

```bash
# Check EC2 Free Tier eligibility
aws ec2 describe-instance-types \
  --filters "Name=free-tier-eligible,Values=true" \
  --query 'InstanceTypes[*].InstanceType' \
  --output table
```

### Check Account Limits

```bash
# Check EC2 limits
aws service-quotas list-service-quotas \
  --service-code ec2 \
  --query 'Quotas[?QuotaName==`Running On-Demand Standard (A, C, D, H, I, M, R, T, Z) instances`]'
```

---

## 🎓 Lessons Learned

1. **Always check Free Tier eligibility** before deploying
2. **Start with smaller instances** for testing
3. **Monitor costs** from day one
4. **Use CDK context** to switch between dev/prod configs
5. **Test deployments** in stages (VPC first, then data tier, etc.)

---

**Status**: Root cause identified ✅
**Fix**: Change instance type to t2.micro or t3.small
**Next**: Wait for deletion, update code, redeploy

---

**Last Updated**: 2026-04-03
**Document**: DEPLOYMENT_FAILURE_ANALYSIS.md
