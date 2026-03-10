"""Admin, user management, and platform setup endpoints."""

from __future__ import annotations

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from redis import Redis
from rq import Queue
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.middleware.auth import get_current_user, require_admin, require_viewer
from app.middleware.audit import log_audit
from app.models.models import User
from app.schemas import (
    UserResponse,
    UserUpdate,
    UserWithActivity,
    UserActivityStats,
    UserManagementStats,
    FeedStatusResponse,
    AuditLogResponse,
    AuditLogListResponse,
)
from app.services import database as db_service
from app.services.domain import get_domain_config

router = APIRouter(tags=["admin"])
settings = get_settings()


@router.get("/me", response_model=UserResponse)
async def get_me(user: Annotated[User, Depends(get_current_user)]):
    """Get current user info."""
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserWithActivity])
async def list_users(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """List all users with activity stats (admin only)."""
    users = await db_service.get_users(db)
    user_ids = [u.id for u in users]
    activity_map = await db_service.get_user_activity_stats(db, user_ids)

    results = []
    for u in users:
        stats_raw = activity_map.get(str(u.id), {})
        activity = UserActivityStats(
            total_actions=stats_raw.get("total_actions", 0),
            login_count=stats_raw.get("login_count", 0),
            last_action=stats_raw.get("last_action"),
            last_action_type=stats_raw.get("last_action_type"),
            actions_7d=stats_raw.get("actions_7d", 0),
        )
        results.append(UserWithActivity(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role,
            avatar_url=u.avatar_url,
            last_login=u.last_login,
            is_active=u.is_active,
            created_at=u.created_at,
            activity=activity,
        ))
    return results


@router.get("/users/stats", response_model=UserManagementStats)
async def get_user_stats(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get aggregate user management statistics (admin only)."""
    from datetime import timedelta, timezone
    from datetime import datetime as dt
    from sqlalchemy import select, func as sqlfunc
    from app.models.models import AuditLog

    users = await db_service.get_users(db)
    cutoff_7d = dt.now(timezone.utc) - timedelta(days=7)

    # Users active in last 7 days (had a login or action)
    active_7d_ids = set(
        row[0]
        for row in (
            await db.execute(
                select(AuditLog.user_id)
                .where(AuditLog.created_at >= cutoff_7d)
                .distinct()
            )
        ).all()
        if row[0] is not None
    )

    return UserManagementStats(
        total_users=len(users),
        active_users=sum(1 for u in users if u.is_active),
        admins=sum(1 for u in users if u.role == "admin"),
        analysts=sum(1 for u in users if u.role == "analyst"),
        viewers=sum(1 for u in users if u.role == "viewer"),
        active_7d=sum(1 for u in users if u.id in active_7d_ids),
        never_logged_in=sum(1 for u in users if u.last_login is None),
    )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    update: UserUpdate,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update user role and/or active status (admin only)."""
    target = await db_service.update_user(
        db,
        user_id,
        role=update.role.value if update.role else None,
        is_active=update.is_active,
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    await log_audit(
        db,
        user_id=str(user.id),
        action="update_user",
        resource_type="user",
        resource_id=str(user_id),
        details=update.model_dump(exclude_none=True),
    )
    return UserResponse.model_validate(target)


@router.get("/audit-log", response_model=AuditLogListResponse)
async def get_audit_log(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    user_id: uuid.UUID | None = None,
    action: str | None = None,
):
    """Paginated audit log viewer (admin only)."""
    logs, total = await db_service.get_audit_log(
        db, page=page, page_size=page_size, user_id=user_id, action=action
    )
    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(l) for l in logs],
        total=total,
        page=page,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.get("/feeds/status", response_model=list[FeedStatusResponse])
async def get_feed_status(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get status of all feed connectors."""
    from sqlalchemy import select
    from app.models.models import FeedSyncState

    result = await db.execute(select(FeedSyncState))
    feeds = result.scalars().all()
    return [FeedStatusResponse.model_validate(f) for f in feeds]


@router.post("/feeds/{feed_name}/trigger")
async def trigger_feed(
    feed_name: str,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Manually trigger a feed ingestion (admin only)."""
    valid_feeds = ["nvd", "cisa_kev", "urlhaus", "abuseipdb", "otx", "virustotal", "shodan"]
    if feed_name not in valid_feeds:
        raise HTTPException(status_code=400, detail=f"Invalid feed. Options: {valid_feeds}")

    redis_conn = Redis.from_url(settings.redis_url)
    q = Queue("high", connection=redis_conn)
    job = q.enqueue("worker.tasks.ingest_feed", feed_name, job_timeout=300)

    await log_audit(
        db,
        user_id=str(user.id),
        action="trigger_feed",
        resource_type="feed",
        resource_id=feed_name,
    )
    return {"status": "queued", "job_id": job.id, "feed": feed_name}


@router.post("/feeds/trigger-all")
async def trigger_all_feeds(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger all feed ingestions (admin only)."""
    redis_conn = Redis.from_url(settings.redis_url)
    q = Queue("default", connection=redis_conn)
    job = q.enqueue("worker.tasks.ingest_all_feeds", job_timeout=600)

    await log_audit(
        db, user_id=str(user.id), action="trigger_all_feeds", resource_type="feed"
    )
    return {"status": "queued", "job_id": job.id}


@router.post("/attack/remap")
async def remap_attack_techniques(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Re-map ALL intel items to ATT&CK techniques using updated keyword map (admin only).

    Clears all existing auto-mapped links and re-processes every intel item.
    Useful after updating the keyword/technique mapping dictionary.
    """
    redis_conn = Redis.from_url(settings.redis_url)
    q = Queue("low", connection=redis_conn)
    job = q.enqueue("worker.tasks.remap_all_intel_to_attack", job_timeout=600)

    await log_audit(
        db, user_id=str(user.id), action="attack_remap", resource_type="attack"
    )
    return {"status": "queued", "job_id": job.id}


@router.get("/setup/config")
async def get_setup_config(
    user: Annotated[User, Depends(require_admin)],
):
    """Get platform domain and deployment configuration (admin only).

    Returns the current platform configuration including domain,
    auth method, service connectivity, and feed API key status.
    """
    return get_domain_config()


@router.get("/setup/status")
async def get_setup_status(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get platform setup status — checklist of what's configured.

    Returns a structured checklist for the Settings > Setup page.
    """
    config = get_domain_config()

    checklist = [
        {
            "id": "database",
            "label": "PostgreSQL + TimescaleDB",
            "status": "configured",
            "description": f"Connected to {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}",
        },
        {
            "id": "redis",
            "label": "Redis Cache & Queue",
            "status": "configured",
            "description": f"Connected to {settings.redis_url}",
        },
        {
            "id": "opensearch",
            "label": "OpenSearch",
            "status": "configured",
            "description": f"Connected to {settings.opensearch_url}",
        },
        {
            "id": "auth",
            "label": "Authentication",
            "status": "configured" if config["auth"]["sso_configured"] else "development",
            "description": (
                f"Cloudflare Zero Trust SSO ({config['auth']['cf_team_name']})"
                if config["auth"]["sso_configured"]
                else "Development mode — no SSO configured"
            ),
        },
        {
            "id": "domain",
            "label": "Domain Configuration",
            "status": "configured" if settings.domain != "localhost" else "pending",
            "description": (
                f"UI: {settings.domain_ui} | API: {settings.domain_api}"
                if settings.domain != "localhost"
                else "Using localhost — set DOMAIN, DOMAIN_UI, DOMAIN_API in .env for production"
            ),
        },
        {
            "id": "feeds_free",
            "label": "Free Feeds (CISA KEV, NVD, URLhaus)",
            "status": "configured",
            "description": "No API key required — ready to ingest",
        },
        {
            "id": "feeds_api",
            "label": "API Key Feeds (AbuseIPDB, OTX)",
            "status": "configured" if (settings.abuseipdb_api_key and settings.otx_api_key) else "partial",
            "description": (
                "All API keys configured"
                if (settings.abuseipdb_api_key and settings.otx_api_key)
                else "Set ABUSEIPDB_API_KEY and OTX_API_KEY in .env"
            ),
        },
        {
            "id": "ai",
            "label": "AI Summarization",
            "status": "configured" if (settings.ai_enabled and settings.ai_api_url) else "optional",
            "description": (
                f"Model: {settings.ai_model} at {settings.ai_api_url}"
                if settings.ai_enabled
                else "Optional — set AI_API_URL and AI_API_KEY in .env"
            ),
        },
    ]

    return {
        "platform": config,
        "checklist": checklist,
        "ready": all(c["status"] in ("configured", "optional") for c in checklist),
    }


@router.post("/admin/reindex")
async def reindex_opensearch(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Rebuild the OpenSearch index with correct mapping and re-index all intel items.

    Fixes mapping mismatches where keyword fields were auto-detected as text.
    This operation may take a few minutes for large datasets.
    """
    import math
    from sqlalchemy import select, func
    from app.core.opensearch import rebuild_index, bulk_index_items
    from app.core.redis import invalidate_pattern
    from app.models.models import IntelItem

    # 1. Rebuild index with proper mapping
    rebuild_result = rebuild_index()

    # 2. Re-index all items from PostgreSQL in batches
    total = (await db.execute(select(func.count()).select_from(IntelItem))).scalar() or 0
    batch_size = 500
    pages = max(1, math.ceil(total / batch_size))
    indexed = 0
    errors = 0

    for page in range(pages):
        rows = (await db.execute(
            select(IntelItem)
            .order_by(IntelItem.ingested_at.asc())
            .offset(page * batch_size)
            .limit(batch_size)
        )).scalars().all()

        if not rows:
            break

        docs = []
        for item in rows:
            doc = {
                "id": str(item.id),
                "title": item.title,
                "summary": item.summary or "",
                "description": item.description or "",
                "ai_summary": item.ai_summary or "",
                "published_at": item.published_at.isoformat() if item.published_at else None,
                "ingested_at": item.ingested_at.isoformat() if item.ingested_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else (item.ingested_at.isoformat() if item.ingested_at else None),
                "severity": item.severity,
                "risk_score": item.risk_score,
                "confidence": item.confidence,
                "source_name": item.source_name,
                "source_url": item.source_url or "",
                "source_ref": item.source_ref or "",
                "source_reliability": item.source_reliability,
                "feed_type": item.feed_type,
                "asset_type": item.asset_type,
                "tlp": item.tlp or "white",
                "tags": list(item.tags) if item.tags else [],
                "geo": list(item.geo) if item.geo else [],
                "industries": list(item.industries) if item.industries else [],
                "cve_ids": list(item.cve_ids) if item.cve_ids else [],
                "affected_products": list(item.affected_products) if item.affected_products else [],
                "related_ioc_count": item.related_ioc_count or 0,
                "is_kev": item.is_kev or False,
                "exploit_available": item.exploit_available or False,
                "exploitability_score": item.exploitability_score,
                "source_hash": item.source_hash or "",
            }
            docs.append(doc)

        result = bulk_index_items(docs)
        indexed += result.get("indexed", 0)
        if result.get("errors"):
            errors += 1

    await log_audit(
        db,
        user_id=str(user.id),
        action="opensearch_reindex",
        details={
            "total_items": total,
            "indexed": indexed,
            "batch_errors": errors,
        },
    )

    # Flush all search caches so new mapping takes effect
    await invalidate_pattern("iw:search:*")
    await invalidate_pattern("iw:dashboard:*")
    await invalidate_pattern("iw:status_bar*")

    return {
        "rebuild": rebuild_result,
        "total_items": total,
        "indexed": indexed,
        "batch_errors": errors,
    }
