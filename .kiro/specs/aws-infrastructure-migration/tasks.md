# Tasks: AWS Infrastructure Migration

## Phase 1: AWS Infrastructure (Tasks 1-6)

- [ ] 1. Create CDK project scaffold
  - [ ] 1.1 Initialize CDK TypeScript project in infra/ directory
  - [ ] 1.2 Create IntelPulseStack class with basic structure
  - [ ] 1.3 Configure stack props: region ap-south-1, tags (Project=IntelPulse, Environment=production)
  - [ ] 1.4 Add CDK dependencies: @aws-cdk/aws-ec2, @aws-cdk/aws-ecs, @aws-cdk/aws-elasticloadbalancingv2
  - [ ] 1.5 Create bin/intelpulse.ts entry point
  - [ ] 1.6 Test CDK synth generates CloudFormation template

- [ ] 2. VPC and networking
  - [ ] 2.1 Create VPC with CIDR 10.0.0.0/16 in 2 AZs (ap-south-1a, ap-south-1b)
  - [ ] 2.2 Create 2 public subnets (10.0.1.0/24, 10.0.2.0/24)
  - [ ] 2.3 Create 2 private subnets (10.0.10.0/24, 10.0.20.0/24)
  - [ ] 2.4 Create Internet Gateway and attach to VPC
  - [ ] 2.5 Create 1 NAT Gateway in public subnet A
  - [ ] 2.6 Configure route tables for public and private subnets
  - [ ] 2.7 Create security groups: sg-alb, sg-ecs, sg-postgres, sg-redis, sg-opensearch
  - [ ] 2.8 Configure security group rules per design (ALB: 80/443 from 0.0.0.0/0, ECS: 3000/8000 from ALB, etc.)

- [ ] 3. Data tier - EC2 for TimescaleDB
  - [ ] 3.1 Create EC2 t3.medium instance in private subnet A
  - [ ] 3.2 Use Amazon Linux 2023 AMI
  - [ ] 3.3 Create EBS gp3 volume (50 GB) and attach to instance
  - [ ] 3.4 Create user data script to install Docker
  - [ ] 3.5 Add user data to run TimescaleDB container (timescale/timescaledb:latest-pg16)
  - [ ] 3.6 Copy db/schema.sql to EC2 and execute as init script
  - [ ] 3.7 Assign security group sg-postgres (inbound 5432 from sg-ecs)
  - [ ] 3.8 Tag instance: Name=intelpulse-timescaledb, Project=IntelPulse

- [ ] 4. Data tier - managed services
  - [ ] 4.1 Create ElastiCache Redis 7 cluster (cache.t3.micro, single-node)
  - [ ] 4.2 Place Redis in private subnet A with security group sg-redis
  - [ ] 4.3 Configure Redis: no AUTH token (or create AUTH token in Secrets Manager)
  - [ ] 4.4 Create OpenSearch Service domain (t3.small.search, single-node)
  - [ ] 4.5 Configure OpenSearch: engine version 2.13, VPC access, no fine-grained access control
  - [ ] 4.6 Place OpenSearch in private subnet A with security group sg-opensearch
  - [ ] 4.7 Tag all resources: Project=IntelPulse, Environment=production
  - [ ] 4.8 Output endpoints: Redis endpoint, OpenSearch endpoint

- [ ] 5. ECR repositories and image build script
  - [ ] 5.1 Create ECR repository: intelpulse/api
  - [ ] 5.2 Create ECR repository: intelpulse/ui
  - [ ] 5.3 Create ECR repository: intelpulse/worker
  - [ ] 5.4 Configure repository policies for ECS task pull access
  - [ ] 5.5 Create scripts/ecr-push.sh script
  - [ ] 5.6 Add ECR login command to script
  - [ ] 5.7 Add Docker build commands for all 3 images using existing Dockerfiles
  - [ ] 5.8 Add Docker tag commands (git SHA + latest)
  - [ ] 5.9 Add Docker push commands to ECR
  - [ ] 5.10 Test script builds and pushes images successfully


- [ ] 6. ECS Fargate cluster and services
  - [ ] 6.1 Create ECS cluster: intelpulse-production
  - [ ] 6.2 Create Secrets Manager secret: intelpulse/production with all required values
  - [ ] 6.3 Create IAM task execution role with permissions: ecr:GetAuthorizationToken, ecr:BatchGetImage, logs:CreateLogStream, secretsmanager:GetSecretValue
  - [ ] 6.4 Create IAM task role for API with permissions: bedrock:InvokeModel, bedrock:InvokeAgent, secretsmanager:GetSecretValue
  - [ ] 6.5 Create task definition for API service (512 CPU, 1024 MB, port 8000, health check /api/v1/health)
  - [ ] 6.6 Create task definition for UI service (256 CPU, 512 MB, port 3000, env BACKEND_URL)
  - [ ] 6.7 Create task definition for worker service (256 CPU, 512 MB, no port)
  - [ ] 6.8 Create task definition for scheduler service (256 CPU, 512 MB, command override: python -m worker.scheduler)
  - [ ] 6.9 Create Application Load Balancer (internet-facing) in public subnets
  - [ ] 6.10 Request ACM certificate for intelpulse.tech (manual DNS validation)
  - [ ] 6.11 Create ALB listener HTTPS:443 with ACM certificate
  - [ ] 6.12 Create ALB listener HTTP:80 with redirect to HTTPS
  - [ ] 6.13 Create target group for API (port 8000, health check /api/v1/health)
  - [ ] 6.14 Create target group for UI (port 3000, health check /)
  - [ ] 6.15 Add listener rule: /api/* → API target group
  - [ ] 6.16 Add listener rule: /* → UI target group (default)
  - [ ] 6.17 Create Fargate service for API (desired count 1, auto-scaling 1-4 on CPU > 70%)
  - [ ] 6.18 Create Fargate service for UI (desired count 1)
  - [ ] 6.19 Create Fargate service for worker (desired count 1)
  - [ ] 6.20 Create Fargate service for scheduler (desired count 1)
  - [ ] 6.21 Verify all services reach RUNNING state with healthy tasks

## Phase 2: Bedrock Agent Core (Tasks 7-12)

- [ ] 7. Create Bedrock adapter - replace llama3
  - [ ] 7.1 Create api/services/bedrock_adapter.py file
  - [ ] 7.2 Implement BedrockAdapter class with boto3 bedrock-runtime client
  - [ ] 7.3 Implement ai_analyze() method for text responses
  - [ ] 7.4 Implement ai_analyze_structured() method for JSON responses
  - [ ] 7.5 Implement _parse_json_response() helper to extract JSON from code blocks
  - [ ] 7.6 Add error handling for Bedrock API errors
  - [ ] 7.7 Update api/services/ai.py to import and use bedrock_adapter
  - [ ] 7.8 Add environment variable detection: if AI_API_URL is "bedrock" or empty, use Bedrock
  - [ ] 7.9 Maintain backward compatibility with llama3 for local dev
  - [ ] 7.10 Add unit tests for bedrock_adapter with mocked boto3 client
  - [ ] 7.11 Update .env.example with AWS_REGION, AI_API_URL=bedrock

- [ ] 8. Create Lambda action groups for Bedrock agents
  - [ ] 8.1 Create infra/lambdas/virustotal_lookup/ directory
  - [ ] 8.2 Implement virustotal_lookup/handler.py with lambda_handler function
  - [ ] 8.3 Add logic to retrieve VIRUSTOTAL_API_KEY from Secrets Manager
  - [ ] 8.4 Add logic to call VirusTotal API v3 based on IOC type
  - [ ] 8.5 Add response transformation to standardized format
  - [ ] 8.6 Create infra/lambdas/abuseipdb_check/ directory
  - [ ] 8.7 Implement abuseipdb_check/handler.py for AbuseIPDB API v2
  - [ ] 8.8 Create infra/lambdas/otx_lookup/ directory
  - [ ] 8.9 Implement otx_lookup/handler.py for AlienVault OTX API
  - [ ] 8.10 Create infra/lambdas/shodan_lookup/ directory
  - [ ] 8.11 Implement shodan_lookup/handler.py for Shodan API
  - [ ] 8.12 Create requirements.txt for each Lambda (requests, boto3)
  - [ ] 8.13 Create CDK constructs to deploy all 4 Lambda functions
  - [ ] 8.14 Configure Lambda IAM role with secretsmanager:GetSecretValue permission
  - [ ] 8.15 Set Lambda timeout to 30s, memory to 256 MB
  - [ ] 8.16 Test each Lambda independently with sample events


- [ ] 9. Create Bedrock agents
  - [ ] 9.1 Upload MITRE ATT&CK STIX bundle (enterprise-attack.json) to S3
  - [ ] 9.2 Create Bedrock Knowledge Base with OpenSearch Serverless for MITRE data
  - [ ] 9.3 Create collaborator agent: "IOC Reputation Analyst" (Claude 3.5 Haiku)
  - [ ] 9.4 Configure IOC Reputation Analyst with instruction for reputation analysis
  - [ ] 9.5 Associate action groups with IOC Reputation Analyst: virustotal_lookup, abuseipdb_check, otx_lookup, shodan_lookup
  - [ ] 9.6 Create collaborator agent: "Threat Context Enricher" (Claude 3.5 Haiku)
  - [ ] 9.7 Configure Threat Context Enricher with instruction for MITRE ATT&CK mapping
  - [ ] 9.8 Associate Knowledge Base with Threat Context Enricher
  - [ ] 9.9 Create collaborator agent: "Risk Scorer" (Claude 3.5 Haiku)
  - [ ] 9.10 Configure Risk Scorer with instruction for risk assessment and severity calculation
  - [ ] 9.11 Create supervisor agent: "IntelPulse Threat Analyst" (Claude 3.5 Sonnet)
  - [ ] 9.12 Configure supervisor with instruction for multi-agent orchestration
  - [ ] 9.13 Associate all 3 collaborator agents with supervisor agent
  - [ ] 9.14 Create agent alias for supervisor agent
  - [ ] 9.15 Test supervisor agent with sample IOC query
  - [ ] 9.16 Verify agent trace shows invocation of all collaborators
  - [ ] 9.17 Add BEDROCK_SUPERVISOR_AGENT_ID and BEDROCK_SUPERVISOR_ALIAS_ID to Secrets Manager

- [ ] 10. Create agent invocation service
  - [ ] 10.1 Create api/services/bedrock_agents.py file
  - [ ] 10.2 Implement BedrockAgentService class with boto3 bedrock-agent-runtime client
  - [ ] 10.3 Implement invoke_threat_analysis() method
  - [ ] 10.4 Add logic to retrieve agent IDs from environment variables
  - [ ] 10.5 Add logic to invoke supervisor agent with formatted prompt
  - [ ] 10.6 Implement streaming response parsing
  - [ ] 10.7 Implement _parse_agent_response() to extract structured JSON
  - [ ] 10.8 Implement _extract_agent_trace() to capture agent invocation history
  - [ ] 10.9 Add error handling with fallback to direct Bedrock call
  - [ ] 10.10 Add unit tests with mocked bedrock-agent-runtime client
  - [ ] 10.11 Add integration test with actual agent invocation (manual)

- [ ] 11. Add agent-lookup API endpoint
  - [ ] 11.1 Create AgentLookupRequest Pydantic model (ioc: str, ioc_type: str)
  - [ ] 11.2 Create ThreatAnalysisResponse Pydantic model with all required fields
  - [ ] 11.3 Add POST /search/agent-lookup endpoint to api/routes/search.py
  - [ ] 11.4 Import BedrockAgentService in search.py
  - [ ] 11.5 Implement endpoint handler to call invoke_threat_analysis()
  - [ ] 11.6 Add try-except with fallback to direct Bedrock call on error
  - [ ] 11.7 Return structured response with status, analysis, engine fields
  - [ ] 11.8 Add endpoint to FastAPI router
  - [ ] 11.9 Test endpoint with curl/Postman
  - [ ] 11.10 Verify response includes all required fields
  - [ ] 11.11 Add API documentation in docstring

- [ ] 12. Update search UI for agent analysis
  - [ ] 12.1 Open ui/src/app/(app)/search/page.tsx
  - [ ] 12.2 Add "AI Agent Analysis" button next to "Live Internet Lookup"
  - [ ] 12.3 Create handleAgentAnalysis() function to call POST /api/v1/search/agent-lookup
  - [ ] 12.4 Add loading state with "Analyzing with multi-agent system..." message
  - [ ] 12.5 Create AgentResultCard component for displaying results
  - [ ] 12.6 Add risk score gauge (0-100) with color coding (red > 80, orange > 60, yellow > 40, green ≤ 40)
  - [ ] 12.7 Add severity badge with color coding (critical=red, high=orange, medium=yellow, low=blue, info=gray)
  - [ ] 12.8 Add confidence percentage display
  - [ ] 12.9 Add MITRE ATT&CK technique chips (clickable, link to attack.mitre.org)
  - [ ] 12.10 Add agent trace timeline showing which agents were invoked
  - [ ] 12.11 Add recommended actions list
  - [ ] 12.12 Style with existing Tailwind classes matching dashboard design
  - [ ] 12.13 Test UI with sample IOC
  - [ ] 12.14 Verify all fields display correctly


## Phase 3: AWS Transform + CI/CD (Tasks 13-16)

- [ ] 13. Run AWS Transform assessment
  - [ ] 13.1 Install AWS Transform CLI (atx) if not already installed
  - [ ] 13.2 Run assessment on Python backend: atx assess api/
  - [ ] 13.3 Review Python assessment report for FastAPI, SQLAlchemy, Pydantic recommendations
  - [ ] 13.4 Run assessment on Node.js frontend: atx assess ui/
  - [ ] 13.5 Review Node.js assessment report for Next.js, TypeScript recommendations
  - [ ] 13.6 Capture assessment reports as docs/AWS_TRANSFORM_PYTHON.md
  - [ ] 13.7 Capture assessment reports as docs/AWS_TRANSFORM_NODEJS.md
  - [ ] 13.8 Apply recommended changes that don't break functionality
  - [ ] 13.9 Test application after applying changes
  - [ ] 13.10 Document applied changes in commit message

- [ ] 14. Amazon Q security scan
  - [ ] 14.1 Open KIRO IDE with Amazon Q Developer extension
  - [ ] 14.2 Run command: "Amazon Q: Run Security Scan"
  - [ ] 14.3 Wait for scan to complete
  - [ ] 14.4 Review all findings (CRITICAL, HIGH, MEDIUM, LOW)
  - [ ] 14.5 Fix all CRITICAL severity issues
  - [ ] 14.6 Fix all HIGH severity issues
  - [ ] 14.7 Document MEDIUM and LOW issues for future work
  - [ ] 14.8 Capture screenshots of scan results
  - [ ] 14.9 Create docs/AMAZON_Q_SECURITY_SCAN.md with findings and fixes
  - [ ] 14.10 Re-run scan to verify fixes
  - [ ] 14.11 Commit security fixes with message: "fix: address Amazon Q security findings"

- [ ] 15. GitHub Actions CI/CD
  - [ ] 15.1 Create .github/workflows/deploy-aws.yml file
  - [ ] 15.2 Configure workflow trigger: push to aws-codethon branch
  - [ ] 15.3 Add job: checkout code
  - [ ] 15.4 Add step: configure AWS credentials from GitHub secrets
  - [ ] 15.5 Add step: login to ECR
  - [ ] 15.6 Add step: build API image with git SHA tag
  - [ ] 15.7 Add step: build UI image with git SHA tag
  - [ ] 15.8 Add step: build worker image with git SHA tag
  - [ ] 15.9 Add step: tag all images with 'latest'
  - [ ] 15.10 Add step: push all images to ECR
  - [ ] 15.11 Add step: update ECS API service with force-new-deployment
  - [ ] 15.12 Add step: update ECS UI service with force-new-deployment
  - [ ] 15.13 Add step: update ECS worker service with force-new-deployment
  - [ ] 15.14 Add step: update ECS scheduler service with force-new-deployment
  - [ ] 15.15 Add step: wait for services to stabilize (aws ecs wait services-stable)
  - [ ] 15.16 Add step: run smoke test (curl health endpoint)
  - [ ] 15.17 Add GitHub secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_ACCOUNT_ID
  - [ ] 15.18 Test workflow by pushing to aws-codethon branch
  - [ ] 15.19 Verify all steps complete successfully
  - [ ] 15.20 Verify services update and health checks pass

- [ ] 16. DNS and OAuth setup
  - [ ] 16.1 Create Route 53 hosted zone for intelpulse.tech (manual)
  - [ ] 16.2 Add A record (alias) pointing to ALB DNS name
  - [ ] 16.3 Verify DNS propagation: dig intelpulse.tech
  - [ ] 16.4 Request ACM certificate for intelpulse.tech (if not done in task 6)
  - [ ] 16.5 Complete DNS validation for ACM certificate
  - [ ] 16.6 Wait for certificate status: ISSUED
  - [ ] 16.7 Update ALB listener to use ACM certificate ARN
  - [ ] 16.8 Create new Google OAuth 2.0 client for intelpulse.tech
  - [ ] 16.9 Add authorized JavaScript origins: https://intelpulse.tech
  - [ ] 16.10 Add authorized redirect URIs: https://intelpulse.tech/api/v1/auth/google/callback
  - [ ] 16.11 Copy client ID and secret to Secrets Manager
  - [ ] 16.12 Update ECS API service to pick up new secrets
  - [ ] 16.13 Test Google OAuth login flow
  - [ ] 16.14 Verify successful login and session creation
  - [ ] 16.15 Document DNS and OAuth setup in docs/AWS_SETUP_GUIDE.md
