---
inclusion: always
---

# Coding Standards

## Python (backend)
- Use ruff for linting (config in ruff.toml)
- Type hints on all function signatures
- Async functions for all database/network operations
- Pydantic v2 models for request/response schemas
- Error handling: raise HTTPException with appropriate status codes

## TypeScript (frontend)
- Strict TypeScript — no `any` types
- React Server Components where possible (Next.js 14 app router)
- Zustand for client state, SWR or fetch for server state
- Tailwind CSS only — no inline styles or CSS modules

## Infrastructure
- CDK (TypeScript) preferred over raw CloudFormation
- All IAM roles follow least-privilege principle
- Tag all AWS resources: Project=IntelPulse, Environment=codethon
- Use Secrets Manager references in ECS task definitions, never hardcode

## Git
- Branch: aws-codethon (off main)
- Commit messages: conventional commits (feat:, fix:, infra:, docs:)
- PR back to main only after codethon submission
