# IntelPulse Bedrock Demo - Quick Start

**5-minute setup for AWS Codethon demo**

---

## Prerequisites

- AWS Account with Bedrock access
- EC2 instance (t3.medium, Ubuntu 22.04)
- IAM role with Bedrock permissions

---

## Setup

### 1. Launch EC2 Instance

```bash
# Via AWS Console:
# - AMI: Ubuntu Server 22.04 LTS
# - Type: t3.medium
# - Security Group: Allow ports 22, 80, 443, 8000
# - IAM Role: BedrockAccessRole (see below)
# - Storage: 30 GB gp3
```

### 2. Create IAM Role

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
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-5-sonnet-20241022-v2:0"
    }
  ]
}
```

Attach this role to your EC2 instance.

### 3. SSH and Setup

```bash
# SSH to instance
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Install Docker
sudo apt update
sudo apt install -y docker.io docker-compose git
sudo usermod -aG docker ubuntu
exit

# SSH back in
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Clone repo
git clone https://github.com/YOUR_USERNAME/ti-platform.git
cd ti-platform
git checkout aws-migration

# Run setup script
chmod +x start-demo.sh
./start-demo.sh
```

**That's it!** The script will:

- Create .env file with secure passwords
- Create docker-compose.demo.yml
- Build Docker images
- Start services
- Show you the next steps

---

## Test

### Health Check

```bash
curl http://localhost:8000/api/v1/demo/health
```

### Analyze a Threat

```bash
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-domain.com",
    "ioc_type": "domain"
  }' | jq
```

### View API Docs

Open in browser: `http://YOUR_EC2_IP:8000/api/docs`

---

## Demo Script

### 1. Show Infrastructure (30 seconds)

```bash
docker-compose -f docker-compose.demo.yml ps
```

### 2. Show API Docs (30 seconds)

Browser: `http://YOUR_EC2_IP:8000/api/docs`

### 3. Live Analysis (2 minutes)

```bash
curl -X POST http://YOUR_EC2_IP:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "45.142.212.61",
    "ioc_type": "ip"
  }' | jq
```

Point out in response:

- `risk_score`: 85/100
- `severity`: "HIGH"
- `mitre_techniques`: ["T1566", "T1059"]
- `recommended_actions`: [...]

### 4. Explain (1 minute)

"Simple flow: API → Bedrock SDK → Claude 3.5 Sonnet → Structured JSON"

**Total: ~4 minutes**

---

## Troubleshooting

### Bedrock Permission Denied

```bash
# Check IAM role
aws sts get-caller-identity

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### API Not Responding

```bash
# Check logs
docker-compose -f docker-compose.demo.yml logs api

# Restart
docker-compose -f docker-compose.demo.yml restart
```

---

## Cleanup

```bash
# Stop services
docker-compose -f docker-compose.demo.yml down

# Terminate EC2 instance
aws ec2 terminate-instances --instance-ids i-xxxxxxxxxxxxx
```

---

## Cost

- EC2 (t3.medium): ~$1/day
- Bedrock API calls: ~$0.01-0.05 per analysis
- **Total demo cost: ~$10-15**

---

## Documentation

- **Complete Setup:** EC2_DEMO_SETUP.md
- **Architecture:** DEMO_README.md
- **Details:** DEMO_SUMMARY.md

---

**Demo Ready in 5 Minutes! 🚀**
