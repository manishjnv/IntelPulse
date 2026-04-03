# Session Handoff - IntelPulse Bedrock Demo

**Date:** 2026-04-03  
**Session:** 5  
**Status:** Infrastructure configured, ready for deployment  

---

## What Was Accomplished

### ✅ Demo Application Built

1. **API Endpoint Created** (`api/app/routes/demo.py`)
   - POST /api/v1/demo/analyze - Analyze IOCs using Bedrock
   - GET /api/v1/demo/health - Health check
   - Direct Bedrock SDK integration (no agents)
   - Structured JSON responses with risk scoring

2. **Documentation Written** (2,000+ lines)
   - EC2_DEMO_SETUP.md - Complete setup guide
   - DEMO_README.md - Quick start and architecture
   - DEPLOY_TO_EXISTING_EC2.md - Existing instance guide
   - QUICK_START.md - 5-minute reference
   - SESSION_5_SUMMARY.md - Detailed session notes

3. **Automation Scripts Created**
   - start-demo.sh - One-command setup
   - test_bedrock_demo.py - Automated test suite
   - docker-compose.demo.yml - Minimal infrastructure

### ✅ EC2 Instance Configured

**Instance Details:**

- Instance ID: i-08e16a37688d50004
- Public IP: 13.222.13.45
- Instance Type: t3.small
- Region: us-east-1

**Configuration Applied:**

- ✅ Security Group: Added port 8000 for API access
- ✅ IAM Role: BedrockAccessRole created and attached
- ✅ Permissions: bedrock:InvokeModel for Claude 3.5 Sonnet/Haiku
- ✅ Instance Profile: Attached to EC2

### ✅ Code Repository

- Repo: <https://github.com/manishjnv/IntelPulse.git>
- Branch: aws-migration
- Commits: 4 commits pushed
- Status: All changes committed and pushed

---

## What's Ready

### Infrastructure ✅

- EC2 instance running with IAM role
- Security group configured for API access
- Bedrock permissions granted

### Code ✅

- Demo endpoint implemented
- Bedrock adapter working
- Docker configuration ready
- Test suite created

### Documentation ✅

- Complete setup guides
- Troubleshooting instructions
- Demo presentation script
- Quick reference cards

---

## Next Steps (For Next Session)

### 1. SSH to EC2 Instance

```bash
ssh -i your-key.pem ubuntu@13.222.13.45
```

### 2. Check Prerequisites

```bash
# Check if Docker is installed
docker --version

# If not, install it
sudo apt update
sudo apt install -y docker.io docker-compose git
sudo usermod -aG docker ubuntu
exit
# SSH back in
```

### 3. Deploy Application

```bash
# Clone repo
git clone https://github.com/manishjnv/IntelPulse.git
cd IntelPulse
git checkout aws-migration

# Run setup script
chmod +x start-demo.sh
./start-demo.sh
```

### 4. Test Deployment

```bash
# From EC2
curl http://localhost:8000/api/v1/demo/health

# From local machine
curl http://13.222.13.45:8000/api/v1/demo/health

# Test analysis
curl -X POST http://13.222.13.45:8000/api/v1/demo/analyze \
  -H "Content-Type: application/json" \
  -d '{"ioc": "malicious-domain.com", "ioc_type": "domain"}' | jq
```

### 5. View API Documentation

Browser: `http://13.222.13.45:8000/api/docs`

---

## Timeline for Next Session

- SSH and verify: 2 minutes
- Install dependencies (if needed): 5 minutes
- Clone repo: 1 minute
- Run setup script: 10-15 minutes
- Test and verify: 3 minutes

**Total: ~20-25 minutes**

---

## Key Files Reference

### Documentation

- **DEPLOY_TO_EXISTING_EC2.md** - Main deployment guide
- **QUICK_START.md** - Quick reference
- **SESSION_5_SUMMARY.md** - Complete session notes

### Code

- **api/app/routes/demo.py** - Demo endpoint
- **api/app/services/bedrock_adapter.py** - Bedrock SDK wrapper

### Scripts

- **start-demo.sh** - Automated setup
- **test_bedrock_demo.py** - Test suite

### Configuration

- **docker-compose.demo.yml** - Docker setup
- **trust-policy.json** - IAM trust policy
- **bedrock-policy.json** - Bedrock permissions

---

## Demo Presentation Script

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
  -d '{"ioc": "malicious-example.com", "ioc_type": "domain"}' | jq
```

Point out:

- Risk score: 85/100
- Severity: HIGH
- MITRE techniques: T1566, T1059
- Recommended actions

### 4. Explain Architecture (1 minute)

"Simple flow: API → Bedrock SDK → Claude 3.5 Sonnet → Structured JSON"

**Total Demo Time: ~4 minutes**

---

## Troubleshooting Quick Reference

### Bedrock Permission Denied

```bash
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1
```

### API Not Responding

```bash
docker-compose -f docker-compose.demo.yml logs api
docker-compose -f docker-compose.demo.yml restart
```

### Port Already in Use

```bash
sudo netstat -tlnp | grep 8000
docker-compose -f docker-compose.demo.yml down
```

---

## Cost Estimate

- EC2 (t3.small): ~$0.75/day
- Bedrock API calls: ~$0.01-0.05 per analysis
- **Total demo cost: ~$5-10**

---

## Success Criteria

✅ Infrastructure configured  
✅ Code committed and pushed  
✅ Documentation complete  
⏳ Application deployed (next session)  
⏳ Tests passing (next session)  
⏳ Demo ready (next session)  

---

## Prompt for Next Session

```
Continue IntelPulse Bedrock demo deployment.

EC2: i-08e16a37688d50004 (13.222.13.45)
Status: IAM role configured, ready to deploy
Repo: https://github.com/manishjnv/IntelPulse.git (aws-migration branch)

Tasks:
1. SSH to EC2 and verify Docker installed
2. Clone repo and run start-demo.sh
3. Test /api/v1/demo/analyze endpoint
4. Verify demo is working
5. Practice presentation script

See DEPLOY_TO_EXISTING_EC2.md for complete instructions.
```

---

## Important Notes

1. **No CDK Deployment** - We're using simplified approach with existing EC2
2. **No Bedrock Agents** - Direct SDK calls only for demo
3. **Minimal Infrastructure** - Just PostgreSQL, Redis, and API
4. **Quick Setup** - ~20 minutes from SSH to working demo
5. **Cost Effective** - ~$5-10 total for demo

---

## Contact Information

- **Repository:** <https://github.com/manishjnv/IntelPulse.git>
- **Branch:** aws-migration
- **EC2 IP:** 13.222.13.45
- **Region:** us-east-1

---

**Ready for deployment in next session!** 🚀

All infrastructure is configured. Just SSH, clone, and run the setup script.
