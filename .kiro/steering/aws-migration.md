---
inclusion: always
---

# AWS Migration Rules

## Codethon Requirements
This migration MUST demonstrably use these AWS services:
1. KIRO IDE — specs, steering files, hooks, agentic chat for all development
2. Amazon Q Developer — security scans, inline code suggestions
3. Amazon Bedrock Agent Core — multi-agent system for IOC analysis
4. AWS Transform — modernization assessment of Python/Node.js code

## Architecture Decisions
- Region: ap-south-1 (Mumbai) — lowest latency from Bengaluru
- TimescaleDB runs on EC2 (NOT RDS) because RDS lacks the extension
- New brand: IntelPulse on intelpulse.tech (separate from IntelPulse production)
- Caddy is replaced by ALB + ACM — remove caddy service from AWS deployment
- No data migration needed — seed fresh data via POST /feeds/trigger-all
- Google OAuth: create new OAuth client for intelpulse.tech

## Code Changes Scope
ONLY these files need modification:
- api/services/ai.py → Replace HTTP calls to AI_API_URL with boto3 Bedrock adapter
- api/routes/search.py → Add POST /search/agent-lookup using Bedrock Agent Runtime
- ui/src/app/(app)/search/page.tsx → Add "AI Agent Analysis" button + result display
- .env.example → Add AWS_REGION, BEDROCK_SUPERVISOR_AGENT_ID, BEDROCK_SUPERVISOR_ALIAS_ID

NEW files to create:
- infra/ → CDK stack (VPC, ECS, ALB, data services, IAM roles)
- api/services/bedrock_agents.py → Multi-agent invocation code
- infra/lambdas/ → Action group Lambda functions for Bedrock agents
- .github/workflows/deploy-aws.yml → ECR build + ECS deploy pipeline

## DO NOT Change
- docker-compose.yml — must still work for local dev
- Existing API routes/signatures — only ADD new endpoints
- Authentication flow — keep Google OAuth + OTP as-is
- Frontend design system — keep existing Tailwind + Recharts styling

## Branding Changes
- All "IntelPulse" references → "IntelPulse"
- Domain: IntelPulse.in → intelpulse.tech
- Logo/favicon: Update with IntelPulse branding
- Page titles, meta tags, documentation
