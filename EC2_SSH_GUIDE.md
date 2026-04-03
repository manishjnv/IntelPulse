# EC2 SSH Connection Guide

**Last Updated**: 2026-04-03
**Instance**: TimescaleDB EC2 (t3.medium)
**Region**: us-east-1

---

## Important Note

⚠️ **The EC2 instance is NOT currently deployed.** The infrastructure deployment was cancelled during Session 4. You'll need to deploy the stack first before connecting to EC2.

---

## Deployment First

Before you can SSH to EC2, deploy the infrastructure:

```bash
cd infra
npm run cdk deploy -- --require-approval never --outputs-file outputs.json
```

**Deployment time**: 25-30 minutes

---

## Connection Methods

### Method 1: AWS Systems Manager (SSM) - RECOMMENDED ✅

**No SSH keys required!** The EC2 instance is configured with SSM access.

#### Step 1: Get Instance ID

After deployment completes:

```bash
# Get instance ID from CloudFormation outputs
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`TimescaleDbInstanceId`].OutputValue' \
  --output text)

echo "Instance ID: $INSTANCE_ID"
```

Or from the outputs file:

```bash
cat infra/outputs.json | grep TimescaleDbInstanceId
```

#### Step 2: Connect via SSM

```bash
# Start SSM session
aws ssm start-session --target $INSTANCE_ID
```

This opens an interactive shell on the EC2 instance.

#### Step 3: Verify TimescaleDB

Once connected:

```bash
# Check Docker is running
sudo docker ps

# Check TimescaleDB container
sudo docker logs timescaledb

# Get PostgreSQL password
sudo cat /root/.postgres_password

# Connect to PostgreSQL
sudo docker exec -it timescaledb psql -U intelpulse -d intelpulse
```

---

### Method 2: Traditional SSH (If Needed)

The CDK stack doesn't create an SSH key pair by default. If you need SSH access:

#### Option A: Add Key Pair to Existing Instance

1. **Create a key pair** (if you don't have one):

```bash
aws ec2 create-key-pair \
  --key-name intelpulse-timescaledb \
  --query 'KeyMaterial' \
  --output text > intelpulse-timescaledb.pem

chmod 400 intelpulse-timescaledb.pem
```

1. **Get instance details**:

```bash
# Get instance ID
INSTANCE_ID=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`TimescaleDbInstanceId`].OutputValue' \
  --output text)

# Get private IP (instance is in private subnet)
PRIVATE_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

echo "Private IP: $PRIVATE_IP"
```

1. **Problem**: Instance is in a private subnet with no public IP!

You would need:

- A bastion host in the public subnet, OR
- VPN connection to the VPC, OR
- Use SSM Session Manager (Method 1) ✅

#### Option B: Modify CDK Stack to Add Key Pair

Update `infra/lib/intelpulse-stack.ts`:

```typescript
// In createTimescaleDbInstance() method
const instance = new ec2.Instance(this, 'TimescaleDbInstance', {
  // ... existing config ...
  keyName: 'intelpulse-timescaledb', // Add this line
});
```

Then redeploy. But you still can't SSH directly because it's in a private subnet.

---

## Common Tasks

### Initialize Database Schema

```bash
# 1. Connect via SSM
aws ssm start-session --target $INSTANCE_ID

# 2. Copy schema to instance (from your local machine, in another terminal)
aws s3 cp db/schema.sql s3://YOUR-BUCKET/schema.sql

# 3. Back in SSM session, download and run schema
aws s3 cp s3://YOUR-BUCKET/schema.sql /tmp/schema.sql
sudo docker exec -i timescaledb psql -U intelpulse -d intelpulse < /tmp/schema.sql
```

Or paste the schema directly:

```bash
# In SSM session
sudo docker exec -i timescaledb psql -U intelpulse -d intelpulse << 'EOF'
-- Paste your schema.sql content here
EOF
```

### Check PostgreSQL Connection

```bash
# Get password from SSM Parameter Store
POSTGRES_PASSWORD=$(aws ssm get-parameter \
  --name "/intelpulse/production/postgres-password" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text)

echo "Password: $POSTGRES_PASSWORD"

# Get private IP
PRIVATE_IP=$(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`TimescaleDbPrivateIp`].OutputValue' \
  --output text)

echo "Connection string: postgresql://intelpulse:$POSTGRES_PASSWORD@$PRIVATE_IP:5432/intelpulse"
```

### View TimescaleDB Logs

```bash
# Connect via SSM
aws ssm start-session --target $INSTANCE_ID

# View logs
sudo docker logs timescaledb

# Follow logs
sudo docker logs -f timescaledb

# Last 100 lines
sudo docker logs --tail 100 timescaledb
```

### Restart TimescaleDB

```bash
# Connect via SSM
aws ssm start-session --target $INSTANCE_ID

# Restart container
sudo docker restart timescaledb

# Or stop and start
sudo docker stop timescaledb
sudo docker start timescaledb
```

### Check Disk Usage

```bash
# Connect via SSM
aws ssm start-session --target $INSTANCE_ID

# Check disk space
df -h

# Check PostgreSQL data directory
sudo du -sh /data/postgres
```

---

## Troubleshooting

### SSM Session Won't Connect

**Problem**: `TargetNotConnected` error

**Solution**:

1. Wait 2-3 minutes after instance launch
2. Check instance is running:

   ```bash
   aws ec2 describe-instances --instance-ids $INSTANCE_ID \
     --query 'Reservations[0].Instances[0].State.Name'
   ```

3. Check SSM agent status:

   ```bash
   aws ssm describe-instance-information \
     --filters "Key=InstanceIds,Values=$INSTANCE_ID"
   ```

### TimescaleDB Container Not Running

**Problem**: `docker ps` shows no containers

**Solution**:

```bash
# Check if container exists but stopped
sudo docker ps -a

# Check Docker logs
sudo journalctl -u docker

# Restart Docker
sudo systemctl restart docker

# Manually start TimescaleDB
sudo docker start timescaledb
```

### Can't Connect to PostgreSQL

**Problem**: Connection refused

**Solution**:

```bash
# Check container is running
sudo docker ps | grep timescaledb

# Check PostgreSQL logs
sudo docker logs timescaledb

# Check port is listening
sudo netstat -tlnp | grep 5432

# Try connecting from within container
sudo docker exec -it timescaledb psql -U intelpulse -d intelpulse
```

---

## Security Notes

### IAM Permissions Required

To use SSM Session Manager, your IAM user/role needs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:StartSession",
        "ssm:TerminateSession",
        "ssm:ResumeSession",
        "ssm:DescribeSessions",
        "ssm:GetConnectionStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

### Instance IAM Role

The EC2 instance has these permissions:

- `AmazonSSMManagedInstanceCore` (for SSM access)
- `ssm:PutParameter` (to store PostgreSQL password)

### Network Security

- Instance is in **private subnet** (no public IP)
- Security group allows:
  - Inbound: Port 5432 from ECS security group only
  - Outbound: None (restricted)
- Cannot be accessed from internet
- Only accessible via:
  - SSM Session Manager
  - ECS tasks in the same VPC

---

## Quick Reference

### Get All Connection Info

```bash
# After deployment, run this to get all details:
aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?contains(OutputKey, `TimescaleDb`)]' \
  --output table
```

### One-Line Connect

```bash
# Get instance ID and connect in one command
aws ssm start-session --target $(aws cloudformation describe-stacks \
  --stack-name IntelPulseStack \
  --query 'Stacks[0].Outputs[?OutputKey==`TimescaleDbInstanceId`].OutputValue' \
  --output text)
```

### Get PostgreSQL Password

```bash
# From SSM Parameter Store
aws ssm get-parameter \
  --name "/intelpulse/production/postgres-password" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text
```

---

## Next Session Checklist

Before connecting to EC2:

- [ ] Deploy infrastructure: `cd infra && npm run cdk deploy`
- [ ] Wait for deployment to complete (~25-30 minutes)
- [ ] Verify stack status: `aws cloudformation describe-stacks --stack-name IntelPulseStack`
- [ ] Get instance ID from outputs
- [ ] Connect via SSM: `aws ssm start-session --target $INSTANCE_ID`
- [ ] Verify TimescaleDB is running: `sudo docker ps`
- [ ] Get PostgreSQL password from SSM Parameter Store
- [ ] Initialize database schema (if needed)

---

## Additional Resources

- **AWS SSM Session Manager**: <https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html>
- **TimescaleDB Docs**: <https://docs.timescale.com/>
- **PostgreSQL Docs**: <https://www.postgresql.org/docs/16/>

---

**Last Updated**: 2026-04-03
**Status**: Infrastructure not deployed yet
**Next**: Deploy stack, then use SSM Session Manager to connect
