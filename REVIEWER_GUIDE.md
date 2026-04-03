# IntelPulse - AWS Codethon Reviewer Guide

**Project**: IntelPulse - Threat Intelligence Platform  
**Team**: [Your Team Name]  
**AWS Account**: 604275788592  
**Region**: us-east-1  
**Demo URL**: [Will be updated after deployment]

---

## 🚀 Quick Start for Reviewers

### Instant Access

🔗 **Demo URL**: [To be updated after deployment]  
🔓 **Authentication**: Demo mode enabled - no login required  
⏱️ **Setup Time**: 0 minutes - just click the link!

### What You'll See

When you access the application, you'll see:

- A blue banner indicating "Demo Mode Active"
- Full access to all features without authentication
- Pre-populated threat intelligence data

---

## 🎯 Key Features to Evaluate

### 1. Dashboard (Home Page)

- Real-time threat intelligence metrics
- Severity distribution charts
- Recent IOC activity
- Feed health monitoring

### 2. IOC Search

Navigate to: `/search`

- Full-text search across 13+ threat feeds
- Advanced filters (severity, type, date range)
- Live Internet Lookup (queries 12+ sources in real-time)
- **NEW**: AI Agent Analysis powered by Amazon Bedrock

### 3. AI-Powered Analysis (Bedrock Integration)

- Multi-agent system for IOC analysis
- Risk scoring and severity assessment
- MITRE ATT&CK technique mapping
- Recommended actions

### 4. Cyber News Feed

Navigate to: `/news`

- AI-enriched security news
- Relevance scoring
- Category filtering

### 5. Analytics

Navigate to: `/analytics`

- Threat visualization
- Geographic distribution
- Source reliability metrics

### 6. Case Management

Navigate to: `/cases`

- Create and track security incidents
- Link IOCs to cases
- Collaboration features

---

## 🏗️ AWS Services Demonstrated

### Core Services (Phase 1 - Infrastructure)

- ✅ **Amazon ECS Fargate** - Container orchestration (4 services)
- ✅ **Application Load Balancer** - Traffic distribution with health checks
- ✅ **Amazon VPC** - Network isolation (2 AZs, 4 subnets, NAT Gateway)
- ✅ **Amazon EC2** - TimescaleDB hosting (t3.medium)
- ✅ **Amazon ElastiCache** - Redis for session management (cache.t3.micro)
- ✅ **Amazon OpenSearch Service** - Full-text search and analytics (t3.small.search)
- ✅ **Amazon ECR** - Container image registry (3 repositories)
- ✅ **AWS Secrets Manager** - Secure credential storage
- ✅ **Amazon CloudWatch** - Logging and monitoring

### AI Services (Phase 2 - Bedrock)

- ✅ **Amazon Bedrock Agent Core** - Multi-agent orchestration
  - Supervisor Agent: IntelPulse Threat Analyst (Claude 3.5 Sonnet)
  - Collaborator Agent 1: IOC Reputation Analyst (Claude 3.5 Haiku)
  - Collaborator Agent 2: Threat Context Enricher (Claude 3.5 Haiku)
  - Collaborator Agent 3: Risk Scorer (Claude 3.5 Haiku)
- ✅ **Amazon Bedrock Knowledge Base** - MITRE ATT&CK data integration
- ✅ **AWS Lambda** - Action group functions (4 functions)
  - VirusTotal Lookup
  - AbuseIPDB Check
  - AlienVault OTX Lookup
  - Shodan Lookup

### Development Tools

- ✅ **KIRO IDE** - Spec-driven development with AI assistance
- ✅ **Amazon Q Developer** - Security scanning and code suggestions
- ✅ **AWS Transform** - Code modernization assessment

### CI/CD (Phase 3)

- ✅ **GitHub Actions** - Automated deployment pipeline
- ✅ **AWS CDK** - Infrastructure as Code (TypeScript)

---

## 📐 Architecture Overview

### High-Level Architecture

```
Internet
    ↓
Application Load Balancer (HTTPS)
    ↓
┌─────────────────────────────────────────┐
│  ECS Fargate Cluster (Private Subnets)  │
│  ┌──────┐  ┌──────┐  ┌────────┐  ┌────┐│
│  │  UI  │  │ API  │  │ Worker │  │Sch.││
│  └──────┘  └──────┘  └────────┘  └────┘│
└─────────────────────────────────────────┘
         ↓           ↓           ↓
┌────────────────────────────────────────┐
│         Data Layer (Private)           │
│  ┌──────────┐  ┌───────┐  ┌──────────┐│
│  │TimescaleDB│  │ Redis │  │OpenSearch││
│  │   (EC2)   │  │(Cache)│  │(Managed) ││
│  └──────────┘  └───────┘  └──────────┘│
└────────────────────────────────────────┘
```

### Bedrock Multi-Agent System

```
User Query → Supervisor Agent (Claude 3.5 Sonnet)
                    ↓
        ┌───────────┼───────────┐
        ↓           ↓           ↓
   Reputation   Context     Risk
   Analyst      Enricher    Scorer
   (Haiku)      (Haiku)     (Haiku)
        ↓           ↓           ↓
   Lambda      Knowledge    Lambda
   Actions      Base        Actions
        ↓           ↓           ↓
   External    MITRE       Risk
   APIs        ATT&CK      Calc
```

---

## 🔍 Testing Scenarios

### Scenario 1: Search for a Known Malicious IP

1. Navigate to `/search`
2. Enter IP: `185.220.101.1` (known Tor exit node)
3. Click "Search"
4. Review results from multiple feeds
5. Click "AI Agent Analysis" to see Bedrock multi-agent analysis

### Scenario 2: Live Internet Lookup

1. Navigate to `/search`
2. Enter any IP, domain, or hash
3. Click "Live Internet Lookup"
4. Watch real-time queries to 12+ sources
5. Review aggregated results

### Scenario 3: View Threat Analytics

1. Navigate to `/analytics`
2. Explore severity distribution
3. Check geographic threat map
4. Review source reliability metrics

### Scenario 4: Create a Security Case

1. Navigate to `/cases`
2. Click "Create New Case"
3. Add title and description
4. Link IOCs from search results
5. Track investigation progress

---

## 📊 Demo Mode Implementation

### Why Demo Mode?

For the AWS Codethon submission, we've implemented demo mode to allow reviewers instant access without requiring:

- Google OAuth setup
- Email verification
- Account creation

### How It Works

**Backend** (`api/app/middleware/auth.py`):

```python
if settings.demo_mode:
    # Auto-authenticate as demo user
    return demo_user
```

**Frontend** (`ui/src/components/DemoBanner.tsx`):

- Displays prominent banner when `NEXT_PUBLIC_DEMO_MODE=true`
- Indicates authentication bypass for evaluation

**Configuration**:

- Environment variable: `DEMO_MODE=true`
- Demo user: `demo@intelpulse.tech`
- Role: Admin (full access)

### Production vs Demo

| Feature | Production | Demo Mode |
|---------|-----------|-----------|
| Authentication | Google OAuth + Email OTP | Bypassed |
| User Management | Full RBAC | Single demo user |
| Session Management | Redis-backed JWT | Auto-authenticated |
| Security | Full security controls | Evaluation-only |

---

## 🎥 Demo Video

[Link to demo video will be added]

**Video Highlights**:

- Architecture walkthrough
- Live feature demonstration
- Bedrock multi-agent system in action
- AWS service integration
- Code quality and best practices

---

## 📚 Additional Documentation

### Technical Documentation

- `ARCHITECTURE.md` - Detailed architecture diagrams
- `DEPLOYMENT_GUIDE.md` - Deployment instructions
- `docs/TECHNOLOGY.md` - Technology stack details
- `infra/DEPLOYMENT.md` - CDK deployment guide

### Development Documentation

- `.kiro/specs/aws-infrastructure-migration/` - Complete spec files
- `CURRENT_STATUS.md` - Project status and progress
- `SESSION_3_FINAL_SUMMARY.md` - Implementation summary

### AWS-Specific Documentation

- `docs/AWS_TRANSFORM_PYTHON.md` - Python modernization assessment
- `docs/AWS_TRANSFORM_NODEJS.md` - Node.js modernization assessment
- `docs/AMAZON_Q_SECURITY_SCAN.md` - Security scan results

---

## 🔐 Security Considerations

### Demo Mode Security

⚠️ **Important**: Demo mode is ONLY for evaluation purposes

**Security Measures**:

- Clearly marked with banner
- Environment variable controlled
- Separate from production configuration
- Easy to disable (`DEMO_MODE=false`)

**Production Deployment**:

- Demo mode disabled
- Full Google OAuth authentication
- Email OTP for additional security
- Redis-backed session management
- JWT with expiration
- Role-based access control (RBAC)

---

## 💡 Innovation Highlights

### 1. Multi-Agent AI System

- Supervisor-collaborator architecture
- Specialized agents for different analysis tasks
- Knowledge base integration (MITRE ATT&CK)
- Lambda action groups for external API calls

### 2. Spec-Driven Development

- Complete specification in `.kiro/specs/`
- Requirements → Design → Tasks workflow
- Property-based testing approach
- Comprehensive documentation

### 3. Infrastructure as Code

- AWS CDK (TypeScript)
- ~120 CloudFormation resources
- Automated deployment pipeline
- Cost-optimized architecture

### 4. Hybrid Data Architecture

- TimescaleDB for time-series IOC data
- OpenSearch for full-text search
- Redis for caching and sessions
- Optimized for threat intelligence workloads

---

## 📈 Performance Metrics

### Response Times (Target)

- Dashboard load: < 2 seconds
- IOC search: < 1 second
- Live lookup: < 5 seconds
- AI analysis: < 10 seconds

### Scalability

- Auto-scaling: 1-4 API tasks based on CPU
- Load balancer: Distributes traffic across tasks
- Caching: Redis reduces database load
- Async processing: Background workers for feeds

---

## 🐛 Known Limitations

### Demo Environment

- Limited to demo data (not production scale)
- Some external API keys may be rate-limited
- Demo mode bypasses authentication

### Future Enhancements

- HTTPS with custom domain (Task 16)
- Multi-region deployment
- Enhanced monitoring and alerting
- Backup and disaster recovery

---

## 📞 Support & Contact

### For Questions

- GitHub Repository: [Repository URL]
- Documentation: See `docs/` directory
- Architecture Diagrams: See `ARCHITECTURE.md`

### Evaluation Criteria

This project demonstrates:

1. ✅ Comprehensive AWS service integration
2. ✅ Production-ready architecture
3. ✅ Security best practices
4. ✅ Scalable and cost-optimized design
5. ✅ Innovation with Bedrock multi-agent system
6. ✅ Complete documentation
7. ✅ CI/CD automation
8. ✅ Code quality and testing

---

## 🎯 Quick Evaluation Checklist

- [ ] Access demo URL successfully
- [ ] Verify demo mode banner is visible
- [ ] Test IOC search functionality
- [ ] Try AI Agent Analysis (Bedrock)
- [ ] Explore dashboard and analytics
- [ ] Review architecture documentation
- [ ] Check AWS service integration
- [ ] Verify code quality and structure

---

**Thank you for reviewing IntelPulse!** 🚀

We've built a production-ready threat intelligence platform that demonstrates comprehensive AWS service integration, innovative use of Bedrock multi-agent systems, and best practices in cloud architecture and security.

---

**Last Updated**: 2026-04-03  
**Version**: 1.0  
**Status**: Ready for Review
