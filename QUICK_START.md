# IntelPulse AWS Codethon - Quick Start Guide

## 🚀 Fast Track to Submission

This guide gets you from current state to submission-ready in the shortest time possible.

---

## ⏱️ Time Estimate: 25 hours total

- **Repository Migration**: 2 hours
- **AWS Deployment**: 8 hours
- **Documentation**: 11 hours
- **Demo Video**: 2 hours
- **Testing & Polish**: 2 hours

---

## 📋 Phase 1: Repository Setup (2 hours)

### Step 1: Create New GitHub Repository (5 min)
```bash
# Via GitHub CLI
gh repo create manishjnv/IntelPulse --public \
  --description "Production-grade threat intelligence platform powered by AWS Bedrock Agent Core"

# Or via web: https://github.com/new
```

### Step 2: Clone and Rebrand (30 min)
```bash
# Clone current repo with new name
cd E:/code
git clone https://github.com/manishjnv/IntelPulse.git IntelPulse
cd IntelPulse

# Remove old remote
git remote remove origin

# Add new remote
git remote add origin https://github.com/manishjnv/IntelPulse.git

# Run rebranding script
pwsh scripts/rebrand-to-intelpulse.ps1
# Answer 'yes' to both prompts

# Verify changes
git status
git diff
```

### Step 3: Manual Updates (30 min)
```bash
# Update package.json
# Update pyproject.toml
# Update README.md
# Update favicon/logo (if available)
# See MIGRATION_INSTRUCTIONS.md for details
```

### Step 4: Push to GitHub (5 min)
```bash
# Create aws-migration branch
git checkout -b aws-migration

# Push both branches
git push -u origin main
git push -u origin aws-migration

# Verify on GitHub
```

### Step 5: Create KIRO Files (50 min)
```bash
# Create steering files
mkdir -p .kiro/steering
# Copy content from IntelPulse_AWS_Codethon_Plan.md section 3.1

# Create hooks
mkdir -p .kiro/hooks
# Copy content from IntelPulse_AWS_Codethon_Plan.md section 3.2

# Commit
git add .kiro/
git commit -m "feat: add KIRO steering files and hooks"
git push
```

---

## 📋 Phase 2: AWS Deployment (8 hours)

### Step 1: Prerequisites (30 min)
```bash
# Install tools
npm install -g aws-cdk
# Install AWS CLI (if not already)
# Install Docker (if not already)

# Configure AWS
aws configure
# Enter credentials, region: ap-south-1

# Request Bedrock access
# AWS Console → Bedrock → Model access
# Request: Claude 3.5 Sonnet, Claude 3.5 Haiku
```

### Step 2: Create Secrets (15 min)
```bash
# Generate passwords
export DB_PASSWORD=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -hex 32)

# Create secrets.json from template
# See AWS_SETUP_GUIDE.md in HIGH_PRIORITY_DELIVERABLES.md

# Create secret
aws secretsmanager create-secret \
  --name intelpulse/production \
  --secret-string file://secrets.json \
  --region ap-south-1
```

### Step 3: Deploy CDK Stack (3 hours)
```bash
# Create infra directory
mkdir infra
cd infra
cdk init app --language typescript

# Copy CDK code from plan
# See IntelPulse_AWS_Codethon_Plan.md Phase 1

# Bootstrap (first time only)
cdk bootstrap

# Deploy
cdk deploy IntelPulseStack --require-approval never
# Takes ~25 minutes

# Save outputs
cdk deploy IntelPulseStack --outputs-file outputs.json
```

### Step 4: Build and Push Images (1 hour)
```bash
# Login to ECR
aws ecr get-login-password --region ap-south-1 | \
  docker login --username AWS --password-stdin \
  ACCOUNT-ID.dkr.ecr.ap-south-1.amazonaws.com

# Build images
docker build -f docker/Dockerfile.api -t intelpulse/api:latest .
docker build -f docker/Dockerfile.ui -t intelpulse/ui:latest .
docker build -f docker/Dockerfile.worker -t intelpulse/worker:latest .

# Tag and push
# See scripts/ecr-push.sh
```

### Step 5: Deploy Bedrock Agents (2 hours)
```bash
# Create Lambda functions
cd infra/lambdas
# Implement 4 Lambda functions
# See IntelPulse_AWS_Codethon_Plan.md Task 8

# Deploy Lambdas
./deploy-lambdas.sh

# Create Bedrock agents via Console or CDK
# See IntelPulse_AWS_Codethon_Plan.md Task 9

# Test agents
aws bedrock-agent-runtime invoke-agent \
  --agent-id <AGENT_ID> \
  --agent-alias-id <ALIAS_ID> \
  --session-id test-session \
  --input-text "Analyze IP: 8.8.8.8"
```

### Step 6: Configure DNS & SSL (1 hour)
```bash
# Route 53: Create hosted zone
# ACM: Request certificate
# Update ALB listener
# See AWS_SETUP_GUIDE.md Step 8-9
```

### Step 7: Verify Deployment (30 min)
```bash
# Health check
curl https://intelpulse.tech/api/v1/health

# Test login
open https://intelpulse.tech/login

# Test IOC search
# Test AI Agent Analysis
```

---

## 📋 Phase 3: Documentation (11 hours)

### Priority 1: Productivity Metrics (2 hours)
```bash
# Create docs/PRODUCTIVITY_METRICS.md
# Use template from HIGH_PRIORITY_DELIVERABLES.md section 1
# Fill in actual numbers from your development
# Include screenshots of time tracking
```

### Priority 2: Amazon Q Usage Report (3 hours)
```bash
# Create docs/AMAZON_Q_USAGE_REPORT.md
# Use template from HIGH_PRIORITY_DELIVERABLES.md section 2
# Capture screenshots:
#   - KIRO spec with 16 tasks
#   - Steering files in action
#   - Hook automation (test-sync)
#   - Security scan results
#   - Code suggestions
#   - KIRO CLI commands
```

### Priority 3: Demo Video Script (2 hours)
```bash
# Create docs/DEMO_VIDEO_SCRIPT.md
# Use template from HIGH_PRIORITY_DELIVERABLES.md section 3
# Add specific details:
#   - Actual IOC to search
#   - Actual agent response
#   - Actual AWS Console screenshots
#   - Actual metrics from your deployment
```

### Priority 4: Deployment Checklist (1 hour)
```bash
# Create docs/DEPLOYMENT_CHECKLIST.md
# Use template from HIGH_PRIORITY_DELIVERABLES.md section 4
# Check off completed items
# Add any additional steps you encountered
```

### Priority 5: AWS Setup Guide (3 hours)
```bash
# Create docs/AWS_SETUP_GUIDE.md
# Use template from HIGH_PRIORITY_DELIVERABLES.md section 5
# Update with actual:
#   - Account IDs
#   - Region-specific details
#   - Troubleshooting you encountered
#   - Actual time taken per step
```

---

## 📋 Phase 4: Demo Video (2 hours)

### Step 1: Prepare (30 min)
```bash
# Review script
# Prepare demo environment
# Test all features
# Prepare AWS Console views
# Prepare KIRO IDE views
```

### Step 2: Record (1 hour)
```bash
# Use OBS Studio or similar
# Follow script exactly
# Record in 1080p
# Keep under 5 minutes
# Include:
#   - Problem statement (30s)
#   - Solution overview (1m)
#   - Live demo (1m)
#   - AWS architecture (1m)
#   - KIRO/Q usage (1m)
#   - Impact & results (30s)
```

### Step 3: Edit & Upload (30 min)
```bash
# Basic editing (trim, transitions)
# Add title cards
# Add captions
# Export as MP4
# Upload to YouTube (unlisted)
# Add to submission
```

---

## 📋 Phase 5: Testing & Polish (2 hours)

### Step 1: Functional Testing (1 hour)
```bash
# Test all features:
- [ ] Login (Google OAuth)
- [ ] Dashboard loads
- [ ] Feed status shows data
- [ ] IOC search works
- [ ] AI Agent Analysis works
- [ ] Multi-agent trace visible
- [ ] Risk score displayed
- [ ] MITRE techniques shown
- [ ] Recommendations shown
```

### Step 2: Load Testing (30 min)
```bash
# Use Apache Bench or similar
ab -n 100 -c 10 https://intelpulse.tech/api/v1/health

# Test IOC search under load
# Document results in PRODUCTIVITY_METRICS.md
```

### Step 3: Security Scan (30 min)
```bash
# Run Amazon Q security scan
# Fix any CRITICAL/HIGH issues
# Document in AMAZON_Q_USAGE_REPORT.md
```

---

## 📋 Submission Checklist

### Before Submitting
- [ ] Application deployed at https://intelpulse.tech
- [ ] GitHub repository public: https://github.com/manishjnv/IntelPulse
- [ ] All 5 high-priority deliverables complete
- [ ] Demo video uploaded and accessible
- [ ] README.md updated with new branding
- [ ] ARCHITECTURE.md updated with AWS details
- [ ] All tests passing
- [ ] Security scans clean
- [ ] Screenshots captured and organized

### Submission Package
```
IntelPulse/
├── README.md (updated)
├── docs/
│   ├── IntelPulse_AWS_Codethon_Plan.md
│   ├── Guideline.md
│   ├── ARCHITECTURE.md (updated)
│   ├── PRODUCTIVITY_METRICS.md ✅
│   ├── AMAZON_Q_USAGE_REPORT.md ✅
│   ├── DEMO_VIDEO_SCRIPT.md ✅
│   ├── DEPLOYMENT_CHECKLIST.md ✅
│   ├── AWS_SETUP_GUIDE.md ✅
│   └── screenshots/
│       ├── architecture-diagram.png
│       ├── kiro-spec.png
│       ├── kiro-hooks.png
│       ├── aws-console.png
│       ├── bedrock-agents.png
│       └── demo-*.png
├── .kiro/
│   ├── steering/ (4 files)
│   └── hooks/ (3 files)
└── infra/ (CDK code)
```

### Submission Form
- **Application URL**: https://intelpulse.tech
- **GitHub URL**: https://github.com/manishjnv/IntelPulse
- **Demo Video URL**: [YouTube link]
- **Team Details**: [If team submission]
- **Theme**: Theme 3 - Intelligent Multi-Agent Domain Solutions

---

## 🎯 Success Metrics

### Target Score: 97/100

| Criteria | Points | Status |
|----------|--------|--------|
| Application Quality | 28/30 | ⏳ In Progress |
| Amazon Q Utilization | 30/30 | ⏳ In Progress |
| Productivity Demo | 19/20 | ⏳ In Progress |
| Innovation | 20/20 | ⏳ In Progress |

---

## 🆘 Quick Help

### Common Issues

**Issue**: CDK deploy fails
```bash
# Check AWS credentials
aws sts get-caller-identity

# Check Bedrock access
aws bedrock list-foundation-models --region ap-south-1

# Check CDK bootstrap
cdk bootstrap --show-template
```

**Issue**: Docker build fails
```bash
# Check Docker daemon
docker ps

# Check Dockerfile paths
ls docker/

# Build with verbose output
docker build --progress=plain -f docker/Dockerfile.api .
```

**Issue**: ECS task fails to start
```bash
# Check CloudWatch logs
aws logs tail /ecs/intelpulse-api --follow

# Check task definition
aws ecs describe-task-definition --task-definition intelpulse-api

# Check secrets
aws secretsmanager get-secret-value --secret-id intelpulse/production
```

**Issue**: Bedrock agent errors
```bash
# Check agent status
aws bedrock-agent get-agent --agent-id <AGENT_ID>

# Check Lambda logs
aws logs tail /aws/lambda/virustotal_lookup --follow

# Test Lambda directly
aws lambda invoke --function-name virustotal_lookup \
  --payload '{"ioc":"8.8.8.8","ioc_type":"ip"}' \
  response.json
```

---

## 📞 Resources

- **Main Plan**: docs/IntelPulse_AWS_Codethon_Plan.md
- **Guidelines**: docs/Guideline.md
- **Deliverables**: docs/HIGH_PRIORITY_DELIVERABLES.md
- **Migration**: MIGRATION_INSTRUCTIONS.md
- **Summary**: CODETHON_SUMMARY.md

---

## 🎉 Final Steps

1. Complete all phases above
2. Review submission checklist
3. Submit to codethon platform
4. Monitor application uptime
5. Prepare for presentation (if required)

---

**Good luck! 🚀**

**Remember**: Quality over speed. A complete, well-documented submission scores higher than a rushed one.

**Target**: 97/100 points
**Timeline**: 25 hours
**Outcome**: Top-tier codethon submission
