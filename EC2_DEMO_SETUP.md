# EC2 Demo Setup Guide - Simplified Approach

This guide shows how to run IntelPulse on a single EC2 instance for AWS Codethon demo.

**What we're doing:**

- Running the app on EC2 with Docker Compose
- Using Amazon Bedrock SDK directly (no agents, no complex infrastructure)
- Simple API endpoint: input IOC → Bedrock analysis → JSON response
- Minimal dependencies: just PostgreSQL, Redis, and the API

**What we're NOT doing:**

- No CDK deployment
- No Bedrock agents or action groups
- No OpenSearch (optional)
- No complex multi-agent systems

---

## Prerequisites

1. **EC2 Instance**: t3.medium or larger (Ubuntu 22.04 or Amazon Linux 2023)
2. **AWS Credentials**: IAM role or credentials with Bedrock access
3. **Security Group**: Allow inbound on port 80, 443, 8000 (for testing)

---

## Step 1: Launch EC2 Instance

### Option A: Using AWS Console

1. Go to EC2 Console → Launch Instance
2. Choose AMI: **Ubuntu Server 22.04 LTS** or **Amazon Linux 2023**
3. Instance type: **t3.medium** (2 vCPU, 4 GB RAM)
4. Key pair: Create or select existing
5. Security group: Allow SSH (22), HTTP (80), HTTPS (443), Custom TCP (8000)
6. Storage: 30 GB gp3
7. **IAM Role**: Attach role with Bedrock permissions (see below)
8. Launch instance

### Option B: Using AWS CLI

```bash
# Create security group
aws ec2 create-security-group \
  --group-name intelpulse-demo \
  --description "IntelPulse demo security group"

# Get security group ID
SG_ID=$(aws ec2 describe-security-groups \
  --group-names intelpulse-demo \
  --query 'SecurityGroups[0].GroupId' \
  --output text)

# Allow inbound traffic
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 8000 --cidr 0.0.0.0/0

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.medium \
  --key-name YOUR_KEY_NAME \
  --security-group-ids $SG_ID \
  --iam-instance-profile Name=BedrockAccessRole \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3}' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=intelpulse-demo}]'
```

---

## Step 2: Create IAM Role for Bedrock Access

The EC2 instance needs permissions to call Amazon Bedrock.

### Create IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    }
  ]
}
```

### Create Role via Console

1. Go to IAM → Roles → Create Role
2. Trusted entity: **AWS service** → **EC2**
3. Create policy with JSON above, name it `BedrockInvokeModelPolicy`
4. Attach policy to role
5. Name role: `BedrockAccessRole`
6. Attach role to EC2 instance

### Create Role via CLI

```bash
# Create trust policy
cat > trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create role
aws iam create-role \
  --role-name BedrockAccessRole \
  --assume-role-policy-document file://trust-policy.json

# Create policy
cat > bedrock-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0",
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-haiku-20241022-v1:0"
      ]
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name BedrockInvokeModelPolicy \
  --policy-document file://bedrock-policy.json

# Attach policy to role
POLICY_ARN=$(aws iam list-policies \
  --query 'Policies[?PolicyName==`BedrockInvokeModelPolicy`].Arn' \
  --output text)

aws iam attach-role-policy \
  --role-name BedrockAccessRole \
  --policy-arn $POLICY_ARN

# Create instance profile
aws iam create-instance-profile --instance-profile-name BedrockAccessRole
aws iam add-role-to-instance-profile \
  --instance-profile-name BedrockAccessRole \
  --role-name BedrockAccessRole
```

---

## Step 3: Connect to EC2 Instance

### Get Instance Public IP

```bash
INSTANCE_ID=i-xxxxxxxxxxxxx  # Your instance ID

PUBLIC_IP=$(aws ec2 describe-instances \
  --instance-ids $INSTANCE_ID \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

echo "Public IP: $PUBLIC_IP"
```

### SSH to Instance

```bash
ssh -i your-key.pem ubuntu@$PUBLIC_IP
# or for Amazon Linux:
# ssh -i your-key.pem ec2-user@$PUBLIC_IP
```

---

## Step 4: Install Dependencies on EC2

Once connected to EC2, run these commands:

### For Ubuntu 22.04

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# Install Git
sudo apt install -y git

# Install AWS CLI (if not already installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
sudo apt install -y unzip
unzip awscliv2.zip
sudo ./aws/install

# Verify installations
docker --version
docker-compose --version
git --version
aws --version

# Log out and back in for docker group to take effect
exit
```

### For Amazon Linux 2023

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Git
sudo yum install -y git

# AWS CLI is pre-installed on Amazon Linux 2023

# Verify installations
docker --version
docker-compose --version
git --version
aws --version

# Log out and back in for docker group to take effect
exit
```

---

## Step 5: Clone Repository and Setup

SSH back into the instance:

```bash
ssh -i your-key.pem ubuntu@$PUBLIC_IP
```

Clone the repository:

```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/ti-platform.git
cd ti-platform

# Switch to demo branch (if you created one)
git checkout aws-migration
```

---

## Step 6: Create Minimal Environment File

Create a `.env` file with minimal configuration:

```bash
cat > .env <<'EOF'
# Database
POSTGRES_USER=ti
POSTGRES_PASSWORD=change-me-secure-password-here
POSTGRES_DB=ti_platform

# Redis
REDIS_PASSWORD=change-me-redis-password

# OpenSearch (optional - can disable)
OPENSEARCH_PASSWORD=change-me-opensearch-password

# Application
SECRET_KEY=change-me-to-random-32-char-string-for-jwt
ENVIRONMENT=production
LOG_LEVEL=INFO

# AWS Bedrock Configuration
AWS_REGION=us-east-1
AI_API_URL=bedrock
AI_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
AI_TIMEOUT=30
AI_ENABLED=true

# Domain (use EC2 public IP for demo)
DOMAIN=localhost
DOMAIN_UI=http://localhost
DOMAIN_API=http://localhost:8000

# Auth (optional for demo)
DEV_BYPASS_AUTH=true
JWT_EXPIRE_MINUTES=480

# API Keys (optional - not needed for basic demo)
NVD_API_KEY=
ABUSEIPDB_API_KEY=
OTX_API_KEY=
VIRUSTOTAL_API_KEY=
SHODAN_API_KEY=
EOF

# Generate secure passwords
sed -i "s/change-me-secure-password-here/$(openssl rand -base64 32)/" .env
sed -i "s/change-me-redis-password/$(openssl rand -base64 32)/" .env
sed -i "s/change-me-opensearch-password/$(openssl rand -base64 32)/" .env
sed -i "s/change-me-to-random-32-char-string-for-jwt/$(openssl rand -base64 32)/" .env

echo "Environment file created with secure passwords"
```

---

## Step 7: Create Simplified Docker Compose

For the demo, we can use a minimal setup without OpenSearch:

```bash
cat > docker-compose.demo.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-ti}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB:-ti_platform}
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-ti}"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
      POSTGRES_DB: ${POSTGRES_DB:-ti_platform}
      POSTGRES_USER: ${POSTGRES_USER:-ti}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      AWS_REGION: ${AWS_REGION:-us-east-1}
      AI_API_URL: bedrock
      AI_MODEL: ${AI_MODEL}
      AI_ENABLED: "true"
      ENVIRONMENT: production
      LOG_LEVEL: INFO
      DEV_BYPASS_AUTH: "true"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  pg_data:
  redis_data:
EOF

echo "Simplified docker-compose.demo.yml created"
```

---

## Step 8: Build and Start the Application

```bash
# Build images (this will take 5-10 minutes)
docker-compose -f docker-compose.demo.yml build

# Start services
docker-compose -f docker-compose.demo.yml up -d

# Check status
docker-compose -f docker-compose.demo.yml ps

# View logs
docker-compose -f docker-compose.demo.yml logs -f api
```

---

## Step 9: Test the Demo Endpoint

### Test from EC2 Instance

```bash
# Health check
curl http://localhost:8000/api/v1/demo/health

# Analyze a threat (example malicious IP)
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "1.2.3.4",
    "ioc_type": "ip"
  }'

# Analyze a domain
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-domain.com",
    "ioc_type": "domain"
  }'

# Analyze a file hash
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "44d88612fea8a8f36de82e1278abb02f",
    "ioc_type": "hash"
  }'
```

### Test from Your Local Machine

```bash
# Replace with your EC2 public IP
PUBLIC_IP=1.2.3.4

# Health check
curl http://$PUBLIC_IP:8000/api/v1/demo/health

# Analyze threat
curl -X POST http://$PUBLIC_IP:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "192.168.1.100",
    "ioc_type": "ip"
  }'
```

---

## Step 10: Access API Documentation

Open in your browser:

```
http://YOUR_EC2_PUBLIC_IP:8000/api/docs
```

This shows the interactive Swagger UI where you can test the `/api/v1/demo/analyze` endpoint.

---

## Demo Flow

**Input → Processing → Output:**

1. **Input**: Send IOC (IP, domain, or hash) via POST request
2. **Processing**:
   - API receives request
   - Calls Amazon Bedrock SDK directly
   - Uses Claude 3.5 Sonnet for analysis
   - Extracts structured data from response
3. **Output**: JSON response with:
   - Risk score (0-100)
   - Severity level (CRITICAL, HIGH, MEDIUM, LOW, INFO)
   - Confidence percentage
   - MITRE ATT&CK techniques
   - Recommended actions
   - Full analysis text

---

## Troubleshooting

### Docker Build Fails

```bash
# Check Docker is running
sudo systemctl status docker

# Check disk space
df -h

# Clean up old images
docker system prune -a
```

### Bedrock Permission Denied

```bash
# Verify IAM role is attached
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1

# Test Bedrock directly
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"test"}]}' \
  --region us-east-1 \
  output.json
```

### API Not Responding

```bash
# Check container logs
docker-compose -f docker-compose.demo.yml logs api

# Check if port is listening
sudo netstat -tlnp | grep 8000

# Restart services
docker-compose -f docker-compose.demo.yml restart
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose -f docker-compose.demo.yml ps postgres

# Check logs
docker-compose -f docker-compose.demo.yml logs postgres

# Connect to database manually
docker-compose -f docker-compose.demo.yml exec postgres psql -U ti -d ti_platform
```

---

## Cleanup

When done with the demo:

```bash
# Stop services
docker-compose -f docker-compose.demo.yml down

# Remove volumes (deletes data)
docker-compose -f docker-compose.demo.yml down -v

# Terminate EC2 instance
aws ec2 terminate-instances --instance-ids $INSTANCE_ID
```

---

## Demo Script for Presentation

**1. Show the setup:**

```bash
ssh ubuntu@$PUBLIC_IP
cd ti-platform
docker-compose -f docker-compose.demo.yml ps
```

**2. Show API documentation:**

- Open browser: `http://$PUBLIC_IP:8000/api/docs`
- Navigate to `/api/v1/demo/analyze` endpoint

**3. Live demo - analyze a threat:**

```bash
curl -X POST http://$PUBLIC_IP:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-example.com",
    "ioc_type": "domain"
  }' | jq
```

**4. Show the response:**

- Risk score
- Severity level
- MITRE ATT&CK techniques
- Recommended actions

**5. Explain the architecture:**

- Simple EC2 instance
- Docker containers (PostgreSQL, Redis, API)
- Direct Bedrock SDK integration
- No complex infrastructure needed

---

## Cost Estimate

**EC2 Instance (t3.medium):**

- $0.0416/hour × 24 hours = ~$1/day
- For demo: ~$5-10 total

**Bedrock API Calls:**

- Claude 3.5 Sonnet: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
- 100 demo requests: ~$1-2

**Total Demo Cost: ~$10-15**

---

## Next Steps

After successful demo:

1. Add authentication (disable DEV_BYPASS_AUTH)
2. Add HTTPS with Let's Encrypt
3. Add monitoring and logging
4. Scale to production infrastructure
5. Add more AI features

---

**Demo Ready!** 🚀

You now have a working IntelPulse demo on EC2 with Amazon Bedrock integration.
