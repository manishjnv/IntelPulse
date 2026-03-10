# IntelWatch — TI Platform Context

## Project Overview
IntelWatch is a full-stack Threat Intelligence Platform. Mono-repo with 3 main services.

## Tech Stack
- **API**: FastAPI (Python 3.12), SQLAlchemy 2.0 async, Pydantic v2
- **UI**: Next.js 14 (App Router), TypeScript, Tailwind CSS, Zustand, shadcn/ui
- **Worker**: Python RQ + APScheduler
- **DB**: PostgreSQL 16 + TimescaleDB | Redis 7 | OpenSearch 2.13
- **Auth**: Google OAuth + Email OTP, 3 RBAC roles (admin/analyst/viewer)
- **Deploy**: Docker Compose on VPS (72.61.227.64), Cloudflare Tunnel

## Code Structure

```
api/
  app/
    main.py              — FastAPI app, mounts all routers
    core/                — config, database, redis, opensearch, logging
    middleware/           — auth.py (RBAC), audit.py (audit logging)
    models/models.py     — 24 SQLAlchemy models (IntelItem, NewsItem, IOC, Case, Report, etc.)
    schemas/__init__.py  — 60+ Pydantic response/request schemas
    routes/              — 16 route files, 133+ endpoints
    services/            — 21 service modules + 13 feed connectors in services/feeds/
    normalizers/         — 14 normalizer modules (3 phases: core → intelligence → export)
    prompts.py           — 9 AI prompt templates
  migrations/            — 7 Alembic-style SQL migrations
worker/
  tasks.py               — 20 task functions
  scheduler.py           — 28 scheduled jobs
  worker.py              — RQ worker bootstrap
ui/
  src/
    app/(app)/           — 18 page directories, 25 pages
    components/          — 29 components (charts/, ui/ subdirs)
    lib/api.ts           — 90+ API client functions (~1100 lines)
    lib/utils.ts         — Shared utilities
    types/index.ts       — 80+ TypeScript interfaces (~1200 lines)
    store/index.ts       — Zustand store
```

## Key Patterns
- Routes import services; services import models/schemas. Never import routes from services.
- All DB access is async (AsyncSession). Worker uses sync sessions via `async_session_factory` context manager.
- Normalizers are pure functions (no DB/IO) — imported by workers, routes, and services.
- Feed connectors extend `BaseFeedConnector` abstract class.
- UI pages use `api.ts` client functions (never raw `fetch`). Pages are server components; interactivity via client components.
- Redis caching via `get_cached()`/`set_cached()` with TTL in route handlers.

## Deployment
- VPS: 72.61.227.64, SSH: root, project at /opt/ti-platform
- CRITICAL: `docker compose up -d --build <service>` (NOT `restart` — that skips rebuild)
- For UI cache issues: `docker compose build --no-cache ui`
- API container Docker IP: 172.19.0.x (changes on rebuild)
- Git remote: https://github.com/manishjnv/ti-platform.git

## Database Summary (24 tables)
Core: `intel_items` (hypertable), `iocs`, `intel_ioc_links`, `news_items`, `detection_rules`
Intel Extraction: `intel_vulnerable_products`, `intel_threat_campaigns`
Case/Reports: `cases`, `case_items`, `case_activities`, `reports`, `report_items`
ATT&CK: `attack_techniques` (691 rows), `relationships`
System: `users`, `user_settings`, `notification_rules`, `notifications`, `audit_log`, `feed_sync_state`, `scoring_config`, `threat_briefings`
Views: `mv_daily_intel_stats`, `mv_ioc_stats`

## 14 Normalizer Modules (api/app/normalizers/)
Phase 1 — Core: categories, severity, confidence, patterns, entities, enrichment, text, geo
Phase 2 — Intelligence Models: ioc_lifecycle, diamond, killchain, correlation
Phase 3 — Output & Export: stix (STIX 2.1 bundles), rules (Sigma YAML)

## 13 Feed Connectors (api/app/services/feeds/)
abuseipdb, cisa_advisories, exploitdb, kev, malwarebazaar, mitre_attack, nvd, otx, shodan, threatfox, urlhaus, virustotal

## Route Files (api/app/routes/) — 133+ endpoints
admin (10), ai_settings (10), auth (7), cases (15), dashboard (4), enrichment (15),
graph (3), health (2), intel (7), iocs (3), news (19), notifications (12),
reports (12), search (3), settings (4), techniques (4)

## Current Platform Stats
- ~43,700 LOC across 156 files
- 570 news items, 22,372 intel items in production DB
- 28 scheduled jobs, 9 AI prompts, 12 feed connectors

## Testing
- **Framework**: pytest 9, pytest-asyncio, pytest-cov
- **Config**: `api/pyproject.toml` `[tool.pytest.ini_options]`, asyncio_mode="auto"
- **Test files**: `api/tests/` — conftest.py + 3 test modules
  - `test_normalizers.py` — 60+ tests across all 14 normalizer modules
  - `test_services.py` — 10 tests for scoring service
  - `test_routes.py` — 13 route smoke tests (mocked auth + DB + Redis)
- **Run locally**: `cd api && python -m pytest tests/ -v --tb=short`
- **Run on VPS**: `docker exec -w /app/api ti-platform-api-1 python -m pytest tests/ -v --tb=short`
- **Current**: 109 tests, all passing
- **Key fixtures** (conftest.py): `mock_user` (admin), `async_client` (httpx ASGI), `_mock_redis` (autouse)

## Known Gaps (prioritized)
P0: Visual graph explorer, TAXII 2.1 server, threat actor database, SOAR/playbook integration
P1: GreyNoise/Censys enrichment, Slack/Teams notifications, detection rule deployment, IOC lifecycle, dark web monitoring, scoring config UI
P2: Collaborative features, TLP enforcement, report approval workflow, custom dashboard widgets
P3: GraphQL API, sandbox integration, social media monitoring, multi-tenancy
