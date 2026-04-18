"""FastAPI application — IntelPulse Enterprise Threat Intelligence Platform API."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings
from app.core.logging import get_logger, setup_logging
from app.middleware.rate_limit import RateLimitMiddleware
from app.routes import health, intel, search, dashboard, admin, auth, techniques, graph, notifications, reports, iocs, news, cases, enrichment, ai_settings, demo, rum
from app.routes import settings as settings_route

settings = get_settings()
_startup_log = get_logger("startup")


# Queries that anonymous visitors hit on the top of the funnel. Priming Redis
# for these turns the first-user-after-deploy experience from ~1s (DB) to
# ~300ms (Redis) without changing any client behaviour. Kept to the default
# query shape (no filters, page=1) — priming every filter combo would thrash.
_WARMUP_URLS = (
    "http://localhost:8000/api/v1/intel?page_size=20",
    "http://localhost:8000/api/v1/news?page_size=20",
    "http://localhost:8000/api/v1/iocs?page_size=20",
    "http://localhost:8000/api/v1/dashboard",
    "http://localhost:8000/api/v1/dashboard/insights",
)


async def _warm_default_queries() -> None:
    """Fire-and-forget self-fetch to prime Redis for default list queries."""
    # Give uvicorn a moment to finish binding the port after lifespan start.
    await asyncio.sleep(2)
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            results = await asyncio.gather(
                *(client.get(u) for u in _WARMUP_URLS),
                return_exceptions=True,
            )
        ok = sum(1 for r in results if getattr(r, "status_code", 0) == 200)
        _startup_log.info("cache_warmup_done", ok=ok, total=len(_WARMUP_URLS))
    except Exception as e:
        # Warmup is best-effort; a failure here must not break the app.
        _startup_log.warning("cache_warmup_failed", error=str(e))


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Startup: ensure OpenSearch index exists
    try:
        from app.core.opensearch import ensure_index
        ensure_index()
    except Exception:
        pass  # Non-fatal on startup

    # Warm Redis for top-funnel default queries so the first user after a
    # deploy doesn't eat the ~1s cold DB hit. Scheduled as a background task
    # so it doesn't block the server from accepting traffic.
    asyncio.create_task(_warm_default_queries())

    yield

    # Shutdown
    from app.core.redis import redis_client
    await redis_client.close()


app = FastAPI(
    title="IntelPulse - Enterprise Threat Intelligence Platform",
    description="IntelPulse Threat Intelligence Platform API — live threat intel feeds, IOC search, risk scoring, analytics",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url="/api/redoc" if settings.environment != "production" else None,
)

# Security Headers & Rate Limiting
if settings.environment == "production":
    # Trusted host middleware — allow domain and direct IP access
    allowed_hosts = ["intelpulse.tech", "www.intelpulse.tech", "*.intelpulse.tech", "localhost", "*"]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Rate limiting
app.add_middleware(RateLimitMiddleware, calls=100, period=60)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Mount routes
PREFIX = settings.api_prefix
app.include_router(health.router, prefix=PREFIX)
app.include_router(auth.router, prefix=PREFIX)
app.include_router(intel.router, prefix=PREFIX)
app.include_router(search.router, prefix=PREFIX)
app.include_router(dashboard.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(techniques.router, prefix=PREFIX)
app.include_router(graph.router, prefix=PREFIX)
app.include_router(notifications.router, prefix=PREFIX)
app.include_router(reports.router, prefix=PREFIX)
app.include_router(iocs.router, prefix=PREFIX)
app.include_router(news.router, prefix=PREFIX)
app.include_router(cases.router, prefix=PREFIX)
app.include_router(settings_route.router, prefix=PREFIX)
app.include_router(enrichment.router, prefix=PREFIX)
app.include_router(ai_settings.router, prefix=PREFIX)
app.include_router(demo.router, prefix=PREFIX)
app.include_router(rum.router, prefix=PREFIX)


@app.get("/")
async def root():
    return {"message": "IntelPulse - Enterprise Threat Intelligence Platform API", "version": "1.0.0"}
