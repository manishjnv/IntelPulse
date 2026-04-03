# Requirements Document: AWS Infrastructure Migration

## 1. Functional Requirements

### 1.1 Infrastructure Provisioning

**FR-1.1.1**: The system SHALL provision a VPC with CIDR 10.0.0.0/16 in ap-south-1 region with 2 availability zones.

**FR-1.1.2**: The system SHALL create 2 public subnets (10.0.1.0/24, 10.0.2.0/24) and 2 private subnets (10.0.10.0/24, 10.0.20.0/24).

**FR-1.1.3**: The system SHALL provision an EC2 t3.medium instance running TimescaleDB (PostgreSQL 16) in a private subnet.

**FR-1.1.4**: The system SHALL provision ElastiCache Redis 7 (cache.t3.micro) in a private subnet.

**FR-1.1.5**: The system SHALL provision AWS OpenSearch Service (t3.small.search, version 2.13) in a private subnet.

**FR-1.1.6**: The system SHALL create 3 ECR repositories: intelpulse/api, intelpulse/ui, intelpulse/worker.

**FR-1.1.7**: The system SHALL provision an ECS Fargate cluster with 4 services: api, ui, worker, scheduler.

**FR-1.1.8**: The system SHALL provision an internet-facing Application Load Balancer with ACM certificate for intelpulse.tech.

**FR-1.1.9**: The system SHALL configure ALB routing: /api/* → API service, /* → UI service.

**FR-1.1.10**: The system SHALL create Route 53 DNS records pointing intelpulse.tech to ALB.

### 1.2 Bedrock Multi-Agent System

**FR-1.2.1**: The system SHALL create a Bedrock supervisor agent named "IntelPulse Threat Analyst" using Claude 3.5 Sonnet.

**FR-1.2.2**: The system SHALL create 3 Bedrock collaborator agents: IOC Reputation Analyst, Threat Context Enricher, Risk Scorer.

**FR-1.2.3**: The system SHALL create 4 Lambda functions as action groups: virustotal_lookup, abuseipdb_check, otx_lookup, shodan_lookup.

**FR-1.2.4**: The system SHALL associate all collaborator agents with the supervisor agent.

**FR-1.2.5**: The system SHALL create a Bedrock Knowledge Base with MITRE ATT&CK STIX data for the Threat Context Enricher.

**FR-1.2.6**: The API SHALL provide a new endpoint POST /api/v1/search/agent-lookup for multi-agent IOC analysis.

**FR-1.2.7**: The agent response SHALL include: ioc, ioc_type, risk_score (0-100), severity, confidence (0-100), detections, mitre_techniques, threat_actors, recommended_actions, agent_trace.

**FR-1.2.8**: The UI SHALL display agent analysis results with risk score gauge, severity badge, MITRE technique chips, and agent trace timeline.


### 1.3 AI Layer Replacement

**FR-1.3.1**: The system SHALL replace self-hosted llama3 HTTP calls with Amazon Bedrock API calls.

**FR-1.3.2**: The Bedrock adapter SHALL support both text and structured JSON responses.

**FR-1.3.3**: The system SHALL maintain backward compatibility with local development using llama3.

**FR-1.3.4**: The system SHALL detect AI backend via environment variable (AI_API_URL = "bedrock" or empty).

**FR-1.3.5**: The system SHALL use Claude 3.5 Haiku as default model for standard AI analysis.

**FR-1.3.6**: The system SHALL use Claude 3.5 Sonnet for supervisor agent orchestration.

### 1.4 CI/CD Automation

**FR-1.4.1**: The system SHALL provide a GitHub Actions workflow triggered on push to aws-codethon branch.

**FR-1.4.2**: The workflow SHALL build 3 Docker images (api, ui, worker) and push to ECR.

**FR-1.4.3**: The workflow SHALL tag images with git SHA and 'latest'.

**FR-1.4.4**: The workflow SHALL update ECS services with force-new-deployment.

**FR-1.4.5**: The workflow SHALL run smoke tests against deployed health endpoints.

### 1.5 Secrets Management

**FR-1.5.1**: The system SHALL store all secrets in AWS Secrets Manager under key "intelpulse/production".

**FR-1.5.2**: Secrets SHALL include: database credentials, Redis URL, OpenSearch URL, API keys, OAuth credentials, Bedrock agent IDs.

**FR-1.5.3**: ECS tasks SHALL retrieve secrets via task definition secret references.

**FR-1.5.4**: Lambda functions SHALL retrieve API keys from Secrets Manager at runtime.

**FR-1.5.5**: No secrets SHALL be hardcoded in source code or Dockerfiles.

## 2. Non-Functional Requirements

### 2.1 Performance

**NFR-2.1.1**: API standard searches SHALL respond in p95 < 500ms.

**NFR-2.1.2**: Bedrock agent analysis SHALL complete in p95 < 8s.

**NFR-2.1.3**: Lambda action groups SHALL timeout at 25s (5s before Lambda 30s limit).

**NFR-2.1.4**: ECS API service SHALL auto-scale 1-4 tasks when CPU > 70%.

**NFR-2.1.5**: Database queries SHALL use indexes on ioc_value, ioc_type, severity, created_at.


### 2.2 Security

**NFR-2.2.1**: All data tier resources SHALL be in private subnets with no public IP addresses.

**NFR-2.2.2**: Security groups SHALL enforce least-privilege access (database only from ECS, etc.).

**NFR-2.2.3**: ALB SHALL terminate TLS using ACM certificate for intelpulse.tech.

**NFR-2.2.4**: All secrets SHALL be encrypted at rest using AWS KMS.

**NFR-2.2.5**: IAM roles SHALL follow least-privilege principle with no wildcard permissions.

**NFR-2.2.6**: API SHALL enforce rate limiting: 100 requests/minute per IP.

**NFR-2.2.7**: CORS SHALL be restricted to intelpulse.tech domain.

**NFR-2.2.8**: JWT tokens SHALL expire after 8 hours.

**NFR-2.2.9**: VPC Flow Logs SHALL be enabled for network monitoring.

**NFR-2.2.10**: CloudTrail SHALL be enabled for API audit logging.

### 2.3 Reliability

**NFR-2.3.1**: Critical services (API, UI) SHALL have tasks in multiple availability zones.

**NFR-2.3.2**: ECS SHALL automatically restart failed tasks.

**NFR-2.3.3**: ALB health checks SHALL remove unhealthy tasks from rotation.

**NFR-2.3.4**: Database SHALL have automated EBS snapshots daily.

**NFR-2.3.5**: Bedrock agent failures SHALL fallback to direct Bedrock calls.

**NFR-2.3.6**: Lambda action group failures SHALL not block agent analysis (partial results).

### 2.4 Maintainability

**NFR-2.4.1**: All AWS resources SHALL be defined in CDK TypeScript code.

**NFR-2.4.2**: All resources SHALL be tagged: Project=IntelPulse, Environment=production.

**NFR-2.4.3**: CloudWatch Logs retention SHALL be 30 days.

**NFR-2.4.4**: Infrastructure changes SHALL be version controlled in Git.

**NFR-2.4.5**: CDK stack SHALL support destroy and redeploy without data loss (stateful resources).

### 2.5 Cost

**NFR-2.5.1**: Total monthly AWS cost SHALL be under $250 for codethon deployment.

**NFR-2.5.2**: Single NAT Gateway SHALL be used (not multi-AZ) for cost savings.

**NFR-2.5.3**: Smallest viable instance types SHALL be used: t3.medium (DB), cache.t3.micro (Redis), t3.small.search (OpenSearch).

**NFR-2.5.4**: Worker tasks MAY use Fargate Spot for 70% cost reduction.

### 2.6 Compatibility

**NFR-2.6.1**: Docker Compose local development SHALL continue to work unchanged.

**NFR-2.6.2**: Existing API routes and signatures SHALL not be modified (only additions).

**NFR-2.6.3**: Authentication flow (Google OAuth + OTP) SHALL remain unchanged.

**NFR-2.6.4**: Frontend design system (Tailwind + Recharts) SHALL remain unchanged.

**NFR-2.6.5**: Database schema SHALL remain compatible with existing migrations.


## 3. Constraints

### 3.1 Technical Constraints

**C-3.1.1**: Region MUST be ap-south-1 (Mumbai) for lowest latency from Bengaluru.

**C-3.1.2**: TimescaleDB MUST run on EC2 (RDS does not support TimescaleDB extension).

**C-3.1.3**: Bedrock models MUST be Claude 3.5 Sonnet (supervisor) and Claude 3.5 Haiku (collaborators).

**C-3.1.4**: Lambda runtime MUST be Python 3.12.

**C-3.1.5**: CDK MUST be TypeScript (not Python or other languages).

**C-3.1.6**: Container images MUST use existing Dockerfiles in docker/ directory.

### 3.2 AWS Service Constraints

**C-3.2.1**: Bedrock Agent Core MUST be used (not standalone Bedrock API).

**C-3.2.2**: Multi-agent collaboration MUST use 1 supervisor + 3 collaborators.

**C-3.2.3**: Action groups MUST use Lambda functions (not inline code).

**C-3.2.4**: Knowledge Base MUST use OpenSearch Serverless (not S3 only).

**C-3.2.5**: ECS MUST use Fargate (not EC2 launch type).

### 3.3 Codethon Requirements

**C-3.3.1**: KIRO IDE MUST be used for all spec creation and development.

**C-3.3.2**: Amazon Q Developer MUST be used for security scans.

**C-3.3.3**: AWS Transform MUST be used for modernization assessment.

**C-3.3.4**: All development MUST be on aws-codethon branch.

**C-3.3.5**: Commit messages MUST follow conventional commits format.

### 3.4 Branding Constraints

**C-3.4.1**: All "IntelPulse" references MUST be changed to "IntelPulse".

**C-3.4.2**: Domain MUST be intelpulse.tech (not IntelPulse.in).

**C-3.4.3**: New Google OAuth client MUST be created for intelpulse.tech.

**C-3.4.4**: Logo, favicon, page titles MUST reflect IntelPulse branding.

## 4. Acceptance Criteria

### 4.1 Infrastructure Deployment

**AC-4.1.1**: CDK stack deploys successfully without errors.

**AC-4.1.2**: All 4 ECS services reach RUNNING state with healthy tasks.

**AC-4.1.3**: ALB health checks pass for API and UI services.

**AC-4.1.4**: Database is accessible from API service on port 5432.

**AC-4.1.5**: Redis is accessible from API and worker services on port 6379.

**AC-4.1.6**: OpenSearch is accessible from API and worker services on port 9200.

**AC-4.1.7**: https://intelpulse.tech loads UI successfully.

**AC-4.1.8**: https://intelpulse.tech/api/v1/health returns 200 OK.


### 4.2 Bedrock Multi-Agent System

**AC-4.2.1**: Supervisor agent and 3 collaborator agents are created and active.

**AC-4.2.2**: All 4 Lambda action groups deploy successfully.

**AC-4.2.3**: POST /api/v1/search/agent-lookup returns structured response for test IOC.

**AC-4.2.4**: Agent response includes all required fields: risk_score, severity, confidence, detections, mitre_techniques, threat_actors, recommended_actions, agent_trace.

**AC-4.2.5**: Risk score is integer 0-100.

**AC-4.2.6**: Severity is one of: critical, high, medium, low, info.

**AC-4.2.7**: Agent trace shows invocation of all 3 collaborator agents.

**AC-4.2.8**: UI displays agent results with risk gauge, severity badge, and MITRE chips.

### 4.3 AI Layer Replacement

**AC-4.3.1**: Bedrock adapter successfully replaces llama3 HTTP calls.

**AC-4.3.2**: Existing AI features (IOC analysis, news enrichment) work with Bedrock.

**AC-4.3.3**: Local development with docker-compose still works with llama3.

**AC-4.3.4**: No hardcoded API keys or secrets in source code.

### 4.4 CI/CD Pipeline

**AC-4.4.1**: GitHub Actions workflow triggers on push to aws-codethon branch.

**AC-4.4.2**: Workflow builds and pushes 3 images to ECR.

**AC-4.4.3**: Workflow updates ECS services successfully.

**AC-4.4.4**: Smoke tests pass after deployment.

**AC-4.4.5**: Deployment completes in under 15 minutes.

### 4.5 Security

**AC-4.5.1**: Amazon Q security scan shows no CRITICAL or HIGH severity issues.

**AC-4.5.2**: All data tier resources have no public IP addresses.

**AC-4.5.3**: Security group rules enforce least-privilege access.

**AC-4.5.4**: All secrets retrieved from Secrets Manager (verified in logs).

**AC-4.5.5**: ALB serves only HTTPS (HTTP redirects to HTTPS).

**AC-4.5.6**: IAM policies have no wildcard (*) permissions.

### 4.6 Performance

**AC-4.6.1**: API health check responds in < 100ms.

**AC-4.6.2**: IOC search responds in < 500ms (p95).

**AC-4.6.3**: Agent analysis completes in < 10s (p95).

**AC-4.6.4**: Load test with 100 concurrent requests succeeds.

### 4.7 Documentation

**AC-4.7.1**: AWS Transform assessment report generated for Python and Node.js code.

**AC-4.7.2**: Amazon Q security scan report captured with screenshots.

**AC-4.7.3**: Architecture diagrams updated in docs/ARCHITECTURE.md.

**AC-4.7.4**: Deployment guide created in docs/AWS_SETUP_GUIDE.md.

**AC-4.7.5**: All 16 tasks documented with completion status.
