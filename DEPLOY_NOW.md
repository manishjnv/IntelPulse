# Deploy IntelPulse Bedrock Demo - Step by Step

**EC2 IP:** 3.87.235.189  
**Time Required:** ~20 minutes  

---

## Step 1: SSH to EC2 (1 minute)

Open your terminal and run:

```bash
ssh -i your-key.pem ubuntu@3.87.235.189
```

Replace `your-key.pem` with your actual SSH key file.

If you get "Permission denied", try:

```bash
ssh -i your-key.pem ec2-user@3.87.235.189
```

---

## Step 2: Check Docker (1 minute)

Once connected, check if Docker is installed:

```bash
docker --version
```

### If Docker is NOT installed

```bash
# Update system
sudo apt update

# Install Docker and Docker Compose
sudo apt install -y docker.io docker-compose git

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group
sudo usermod -aG docker ubuntu

# Log out and back in
exit
ssh -i your-key.pem ubuntu@3.87.235.189
```

---

## Step 3: Clone Repository (1 minute)

```bash
# Clone the repo
git clone https://github.com/manishjnv/IntelPulse.git

# Enter directory
cd IntelPulse

# Switch to demo branch
git checkout aws-migration

# Verify you're on the right branch
git branch
# Should show: * aws-migration
```

---

## Step 4: Run Setup Script (10-15 minutes)

```bash
# Make script executable
chmod +x start-demo.sh

# Run the setup
./start-demo.sh
```

**What the script does:**

1. ✅ Creates .env file with secure passwords
2. ✅ Creates docker-compose.demo.yml
3. ✅ Checks AWS credentials (should work with IAM role)
4. ✅ Verifies Bedrock access
5. ✅ Builds Docker images (this takes 5-10 minutes)
6. ✅ Starts services
7. ✅ Shows you test commands

**Wait for it to complete.** You'll see:

```
✅ Demo is ready!
```

---

## Step 5: Test from EC2 (2 minutes)

### Health Check

```bash
curl http://localhost:8000/api/v1/demo/health
```

Expected output:

```json
{
  "status": "healthy",
  "bedrock": {
    "healthy": true,
    "provider": "bedrock",
    "region": "us-east-1",
    "model": "anthropic.claude-3-5-sonnet-20241022-v2:0"
  },
  "demo_endpoint": "operational"
}
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

Expected output:

```json
{
  "ioc": "malicious-domain.com",
  "ioc_type": "domain",
  "analysis": "Full AI-generated analysis...",
  "risk_score": 85,
  "severity": "HIGH",
  "confidence": 90,
  "mitre_techniques": ["T1566", "T1059"],
  "recommended_actions": [...]
}
```

---

## Step 6: Test from Your Local Machine (1 minute)

Open a NEW terminal on your local machine (not on EC2):

```bash
# Health check
curl http://3.87.235.189:8000/api/v1/demo/health

# Analyze threat
curl -X POST http://3.87.235.189:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "45.142.212.61",
    "ioc_type": "ip"
  }' | jq
```

---

## Step 7: View API Documentation (30 seconds)

Open in your browser:

```
http://3.87.235.189:8000/api/docs
```

You should see the Swagger UI with the demo endpoints.

---

## Step 8: Run Automated Tests (2 minutes)

Back on EC2:

```bash
# Install test dependencies
pip3 install httpx

# Run test suite
python3 test_bedrock_demo.py
```

Expected output:

```
🔍 Testing health endpoint...
✅ Health check passed

🔍 Testing analysis for ip: 192.168.1.100
✅ Analysis completed

🔍 Testing analysis for domain: malicious-domain.com
✅ Analysis completed

🔍 Testing analysis for hash: 44d88612fea8a8f36de82e1278abb02f
✅ Analysis completed

✅ Passed: 3/3
🎉 All tests passed! Demo is ready.
```

---

## ✅ Success! Demo is Ready

If all tests pass, your demo is working!

### Quick Commands

```bash
# View logs
docker-compose -f docker-compose.demo.yml logs -f api

# Restart services
docker-compose -f docker-compose.demo.yml restart

# Stop services
docker-compose -f docker-compose.demo.yml down

# Start services
docker-compose -f docker-compose.demo.yml up -d

# Check status
docker-compose -f docker-compose.demo.yml ps
```

---

## Troubleshooting

### Problem: "Permission denied" when running Docker

**Solution:**

```bash
# Add yourself to docker group
sudo usermod -aG docker $USER

# Log out and back in
exit
ssh -i your-key.pem ubuntu@3.87.235.189
```

### Problem: "Bedrock permission denied"

**Solution:**

```bash
# Check IAM role
aws sts get-caller-identity

# Should show: arn:aws:sts::604275788592:assumed-role/BedrockAccessRole/...

# If not, the IAM role might not be attached yet (wait 1-2 minutes)
```

### Problem: "Port 8000 already in use"

**Solution:**

```bash
# Check what's using port 8000
sudo netstat -tlnp | grep 8000

# Kill the process or stop existing containers
docker-compose -f docker-compose.demo.yml down
```

### Problem: Docker build fails with "No space left on device"

**Solution:**

```bash
# Check disk space
df -h

# Clean up Docker
docker system prune -a

# Try again
./start-demo.sh
```

### Problem: API returns 500 error

**Solution:**

```bash
# Check logs
docker-compose -f docker-compose.demo.yml logs api

# Look for errors and fix them
# Common issues:
# - Database not ready (wait 30 seconds)
# - Redis not ready (wait 30 seconds)
# - Bedrock permissions (check IAM role)
```

---

## Demo Presentation Script

Once everything is working, use this for your demo:

### 1. Show Infrastructure (30 seconds)

```bash
docker-compose -f docker-compose.demo.yml ps
```

### 2. Show API Docs (30 seconds)

Browser: `http://3.87.235.189:8000/api/docs`

### 3. Live Analysis (2 minutes)

```bash
curl -X POST http://3.87.235.189:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-example.com",
    "ioc_type": "domain"
  }' | jq
```

Point out:

- ✅ Risk score: 85/100
- ✅ Severity: HIGH
- ✅ MITRE techniques: T1566, T1059
- ✅ Recommended actions

### 4. Explain (1 minute)

"Simple architecture: API → Bedrock SDK → Claude 3.5 Sonnet → Structured JSON"

**Total: ~4 minutes**

---

## What to Expect

### During Docker Build (5-10 minutes)

You'll see:

```
Building api...
Step 1/10 : FROM python:3.12-slim
...
Successfully built abc123def456
Successfully tagged intelpulse/api:latest
```

### When Services Start

You'll see:

```
Creating network "intelpulse_default" with the default driver
Creating intelpulse_postgres_1 ... done
Creating intelpulse_redis_1    ... done
Creating intelpulse_api_1      ... done
```

### When Everything is Ready

```
✅ Demo is ready!

📚 API Documentation: http://3.87.235.189:8000/api/docs

🧪 Test the demo endpoint:
   curl -X POST http://3.87.235.189:8000/api/v1/demo/analyze \
     -H 'Content-Type: application/json' \
     -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}'
```

---

## Timeline

- ⏱️ SSH to EC2: 1 minute
- ⏱️ Check Docker: 1 minute
- ⏱️ Clone repo: 1 minute
- ⏱️ Run setup: 10-15 minutes
- ⏱️ Test: 3 minutes

**Total: ~20 minutes**

---

**Ready? Start with Step 1!** 🚀

Open your terminal and SSH to: `3.87.235.189`
