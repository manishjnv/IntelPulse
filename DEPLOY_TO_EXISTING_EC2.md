# Deploy to Existing EC2 Instance

**Instance ID:** i-08e16a37688d50004  
**Public IP:** 13.222.13.45  
**Instance Type:** t3.small  

---

## ✅ Setup Complete

I've already configured:

- ✅ Security group: Added port 8000 for API access
- ✅ IAM role: Created and attached BedrockAccessRole
- ✅ Bedrock permissions: InvokeModel access granted

---

## Step 1: SSH to Your Instance

```bash
# Replace with your key file
ssh -i your-key.pem ubuntu@13.222.13.45

# Or if using Amazon Linux:
# ssh -i your-key.pem ec2-user@13.222.13.45
```

---

## Step 2: Check What's Already Installed

```bash
# Check if Docker is installed
docker --version

# Check if Git is installed
git --version

# Check if AWS CLI is installed
aws --version
```

---

## Step 3: Install Missing Dependencies (if needed)

### If Docker is NOT installed

```bash
# For Ubuntu
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ubuntu

# For Amazon Linux
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Log out and back in for docker group
exit
ssh -i your-key.pem ubuntu@13.222.13.45
```

### If Git is NOT installed

```bash
# For Ubuntu
sudo apt install -y git

# For Amazon Linux
sudo yum install -y git
```

### If Docker Compose is NOT installed

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## Step 4: Clone Repository

```bash
# Clone the repo
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse

# Switch to demo branch
git checkout aws-migration

# Verify you're on the right branch
git branch
```

---

## Step 5: Run Setup Script

```bash
# Make script executable
chmod +x start-demo.sh

# Run setup
./start-demo.sh
```

The script will:

1. Check prerequisites
2. Create .env file with secure passwords
3. Create docker-compose.demo.yml
4. Verify AWS credentials
5. Check Bedrock access
6. Build Docker images (5-10 minutes)
7. Start services
8. Show you test commands

---

## Step 6: Test the Demo

### From EC2 instance

```bash
# Health check
curl http://localhost:8000/api/v1/demo/health

# Analyze a threat
curl -X POST http://localhost:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-domain.com",
    "ioc_type": "domain"
  }' | jq
```

### From your local machine

```bash
# Health check
curl http://13.222.13.45:8000/api/v1/demo/health

# Analyze threat
curl -X POST http://13.222.13.45:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "45.142.212.61",
    "ioc_type": "ip"
  }' | jq
```

### View API docs in browser

```
http://13.222.13.45:8000/api/docs
```

---

## Step 7: Verify Everything Works

Run the automated test suite:

```bash
# Install test dependencies
pip3 install httpx

# Run tests
python3 test_bedrock_demo.py
```

Expected output:

```
✅ Health check passed
✅ Analysis completed for IP
✅ Analysis completed for domain
✅ Analysis completed for hash
🎉 All tests passed! Demo is ready.
```

---

## Troubleshooting

### If Bedrock returns permission denied

```bash
# Check IAM role is attached
aws sts get-caller-identity

# Should show: arn:aws:sts::604275788592:assumed-role/BedrockAccessRole/...

# Verify Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### If API doesn't respond

```bash
# Check if containers are running
docker-compose -f docker-compose.demo.yml ps

# Check logs
docker-compose -f docker-compose.demo.yml logs api

# Restart services
docker-compose -f docker-compose.demo.yml restart
```

### If Docker build fails

```bash
# Check disk space
df -h

# If low on space, clean up
docker system prune -a

# Try building again
docker-compose -f docker-compose.demo.yml build --no-cache
```

### If port 8000 is already in use

```bash
# Check what's using port 8000
sudo netstat -tlnp | grep 8000

# Kill the process or change the port in docker-compose.demo.yml
```

---

## Quick Commands

```bash
# Start services
docker-compose -f docker-compose.demo.yml up -d

# Stop services
docker-compose -f docker-compose.demo.yml down

# View logs
docker-compose -f docker-compose.demo.yml logs -f api

# Restart services
docker-compose -f docker-compose.demo.yml restart

# Check status
docker-compose -f docker-compose.demo.yml ps
```

---

## Demo Presentation

### 1. Show Infrastructure (30 seconds)

```bash
docker-compose -f docker-compose.demo.yml ps
```

### 2. Show API Docs (30 seconds)

Browser: `http://13.222.13.45:8000/api/docs`

### 3. Live Analysis (2 minutes)

```bash
curl -X POST http://13.222.13.45:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "ioc": "malicious-example.com",
    "ioc_type": "domain"
  }' | jq
```

Point out:

- Risk score: 85/100
- Severity: HIGH
- MITRE techniques: T1566, T1059
- Recommended actions

### 4. Explain (1 minute)

"Simple flow: API → Bedrock SDK → Claude 3.5 Sonnet → Structured JSON"

---

## What's Configured

✅ **EC2 Instance:** i-08e16a37688d50004 (t3.small)  
✅ **Public IP:** 13.222.13.45  
✅ **Security Group:** Port 22 (SSH) + Port 8000 (API)  
✅ **IAM Role:** BedrockAccessRole with InvokeModel permissions  
✅ **Region:** us-east-1  

---

## Next Steps

1. **SSH to instance:** `ssh -i your-key.pem ubuntu@13.222.13.45`
2. **Clone repo:** `git clone https://github.com/manishjnv/IntelPulse.git`
3. **Run setup:** `cd IntelPulse && git checkout aws-migration && ./start-demo.sh`
4. **Test:** `curl http://localhost:8000/api/v1/demo/health`
5. **Demo:** Follow presentation script above

---

**You're ready to deploy! 🚀**

Just SSH to the instance and run the setup script.
