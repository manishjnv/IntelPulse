---
inclusion: always
---

# Technology Stack

## Backend
- Python 3.12, FastAPI (async), SQLAlchemy (async), Pydantic v2
- Python RQ (Redis Queue) for background jobs
- APScheduler for cron-like feed scheduling
- Ruff for linting (see ruff.toml)

## Frontend
- Next.js 14, TypeScript, Tailwind CSS
- Recharts for charts, Zustand for state management
- Server-side rendering with API proxy via BACKEND_URL

## Data Layer
- PostgreSQL 16 + TimescaleDB extension (hypertables for time-series IOC data)
- OpenSearch 2.13 (full-text IOC search, analytics aggregations)
- Redis 7 (session store for iw_session cookie, RQ job queue)

## Infrastructure (current)
- Docker Compose (7 services) on Hostinger VPS
- Caddy 2 for reverse proxy + auto HTTPS
- Domain: IntelPulse.in (legacy)

## Infrastructure (AWS migration)
- Rebranded as IntelPulse
- Domain: intelpulse.tech

## Infrastructure (target — AWS codethon)
- ECS Fargate for 4 app services
- EC2 t3.medium for PostgreSQL+TimescaleDB (RDS lacks TimescaleDB support)
- AWS OpenSearch Service (managed)
- ElastiCache Redis 7 (managed)
- ALB + ACM for HTTPS, Route 53 for DNS
- Secrets Manager for env vars, ECR for container images
- Amazon Bedrock Agent Core for AI layer (replaces llama3)

## Conventions
- All Dockerfiles are in docker/
- DB init script: db/schema.sql
- API routes under api/routes/, services under api/services/
- Worker tasks under worker/
- Frontend pages under ui/src/app/(app)/
