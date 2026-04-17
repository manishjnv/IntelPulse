"""AI Settings API — admin-only platform-wide AI configuration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.database import get_db
from app.core.logging import get_logger
from app.core.redis import redis_client
from app.core.url_validation import UnsafeURLError, validate_outbound_url
from app.middleware.auth import require_admin
from app.models.models import AISetting, User

logger = get_logger(__name__)
env_settings = get_settings()

router = APIRouter(prefix="/ai-settings", tags=["ai-settings"])

# Redis key for daily usage counters
_DAILY_KEY_PREFIX = "ai_daily_usage"

# Fields that can be updated
_UPDATABLE_FIELDS = {
    "ai_enabled", "primary_provider", "primary_api_url", "primary_api_key",
    "primary_model", "primary_timeout", "fallback_providers",
    "feature_intel_summary", "feature_intel_enrichment", "feature_news_enrichment",
    "feature_live_lookup", "feature_report_gen", "feature_briefing_gen",
    "feature_kql_generation",
    "daily_limit_intel_summary", "daily_limit_intel_enrichment",
    "daily_limit_news_enrichment", "daily_limit_live_lookup",
    "daily_limit_report_gen", "daily_limit_briefing_gen",
    "daily_limit_kql_generation",
    "prompt_intel_summary", "prompt_intel_enrichment", "prompt_news_enrichment",
    "prompt_live_lookup", "prompt_report_gen", "prompt_briefing_gen",
    "prompt_kql_generation",
    "default_temperature", "default_max_tokens",
    "requests_per_minute", "batch_delay_ms",
    "cache_ttl_summary", "cache_ttl_enrichment", "cache_ttl_lookup",
    "model_intel_summary", "model_intel_enrichment", "model_news_enrichment",
    "model_live_lookup", "model_report_gen", "model_briefing_gen",
    "model_kql_generation",
}

# Optimal defaults — hardcoded in backend code (secure, not user-editable).
# Used by the reset-to-defaults endpoint to prevent misconfiguration.
AI_OPTIMAL_DEFAULTS: dict = {
    "ai_enabled": True,
    "primary_provider": "groq",
    "primary_api_url": "https://api.groq.com/openai/v1/chat/completions",
    "primary_model": "llama-3.3-70b-versatile",
    "primary_timeout": 30,
    "feature_intel_summary": True,
    "feature_intel_enrichment": True,
    "feature_news_enrichment": True,
    "feature_live_lookup": True,
    "feature_report_gen": True,
    "feature_briefing_gen": True,
    "feature_kql_generation": True,
    "daily_limit_intel_summary": 500,
    "daily_limit_intel_enrichment": 200,
    "daily_limit_news_enrichment": 300,
    "daily_limit_live_lookup": 100,
    "daily_limit_report_gen": 50,
    "daily_limit_briefing_gen": 20,
    "daily_limit_kql_generation": 100,
    "default_temperature": 0.3,
    "default_max_tokens": 800,
    "requests_per_minute": 30,
    "batch_delay_ms": 1000,
    "cache_ttl_summary": 3600,
    "cache_ttl_enrichment": 21600,
    "cache_ttl_lookup": 300,
    "model_intel_summary": "",
    "model_intel_enrichment": "",
    "model_news_enrichment": "",
    "model_live_lookup": "",
    "model_report_gen": "",
    "model_briefing_gen": "",
    "model_kql_generation": "",
    "prompt_intel_summary": "",
    "prompt_intel_enrichment": "",
    "prompt_news_enrichment": "",
    "prompt_live_lookup": "",
    "prompt_report_gen": "",
    "prompt_briefing_gen": "",
    "prompt_kql_generation": "",
}


async def _get_or_create_settings(db: AsyncSession) -> AISetting:
    """Get the singleton AI settings row, creating it if absent."""
    result = await db.execute(select(AISetting).where(AISetting.key == "default"))
    row = result.scalar_one_or_none()
    if not row:
        row = AISetting(key="default")
        # Seed from env vars so first load reflects current config
        row.ai_enabled = env_settings.ai_enabled
        row.primary_api_url = env_settings.ai_api_url
        row.primary_api_key = env_settings.ai_api_key
        row.primary_model = env_settings.ai_model
        row.primary_timeout = env_settings.ai_timeout

        # Seed fallback providers from env
        fallbacks = []
        if env_settings.cerebras_api_key:
            fallbacks.append({
                "name": "cerebras", "url": "https://api.cerebras.ai/v1/chat/completions",
                "key": env_settings.cerebras_api_key, "model": "llama3.1-8b",
                "timeout": 60, "enabled": True,
            })
        if env_settings.hf_api_key:
            fallbacks.append({
                "name": "huggingface", "url": "https://api-inference.huggingface.co/v1/chat/completions",
                "key": env_settings.hf_api_key, "model": "mistralai/Mistral-7B-Instruct-v0.3",
                "timeout": 60, "enabled": True,
            })
        row.fallback_providers = fallbacks
        db.add(row)
        await db.flush()
    return row


def _serialize(row: AISetting) -> dict:
    """Serialize AISetting to JSON-safe dict, masking API keys."""
    return {
        "ai_enabled": row.ai_enabled,
        "primary_provider": row.primary_provider,
        "primary_api_url": row.primary_api_url,
        "primary_api_key": _mask(row.primary_api_key),
        "primary_api_key_set": bool(row.primary_api_key),
        "primary_model": row.primary_model,
        "primary_timeout": row.primary_timeout,
        "fallback_providers": [
            {**p, "key": _mask(p.get("key", "")), "key_set": bool(p.get("key")), "key_masked": _mask(p.get("key", ""))}
            for p in (row.fallback_providers or [])
        ],
        "feature_intel_summary": row.feature_intel_summary,
        "feature_intel_enrichment": row.feature_intel_enrichment,
        "feature_news_enrichment": row.feature_news_enrichment,
        "feature_live_lookup": row.feature_live_lookup,
        "feature_report_gen": row.feature_report_gen,
        "feature_briefing_gen": row.feature_briefing_gen,
        "feature_kql_generation": row.feature_kql_generation,
        "daily_limit_intel_summary": row.daily_limit_intel_summary,
        "daily_limit_intel_enrichment": row.daily_limit_intel_enrichment,
        "daily_limit_news_enrichment": row.daily_limit_news_enrichment,
        "daily_limit_live_lookup": row.daily_limit_live_lookup,
        "daily_limit_report_gen": row.daily_limit_report_gen,
        "daily_limit_briefing_gen": row.daily_limit_briefing_gen,
        "daily_limit_kql_generation": row.daily_limit_kql_generation,
        "prompt_intel_summary": row.prompt_intel_summary,
        "prompt_intel_enrichment": row.prompt_intel_enrichment,
        "prompt_news_enrichment": row.prompt_news_enrichment,
        "prompt_live_lookup": row.prompt_live_lookup,
        "prompt_report_gen": row.prompt_report_gen,
        "prompt_briefing_gen": row.prompt_briefing_gen,
        "prompt_kql_generation": row.prompt_kql_generation,
        "default_temperature": row.default_temperature,
        "default_max_tokens": row.default_max_tokens,
        "requests_per_minute": row.requests_per_minute,
        "batch_delay_ms": row.batch_delay_ms,
        "cache_ttl_summary": row.cache_ttl_summary,
        "cache_ttl_enrichment": row.cache_ttl_enrichment,
        "cache_ttl_lookup": row.cache_ttl_lookup,
        "model_intel_summary": row.model_intel_summary,
        "model_intel_enrichment": row.model_intel_enrichment,
        "model_news_enrichment": row.model_news_enrichment,
        "model_live_lookup": row.model_live_lookup,
        "model_report_gen": row.model_report_gen,
        "model_briefing_gen": row.model_briefing_gen,
        "model_kql_generation": row.model_kql_generation,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _mask(key: str) -> str:
    if not key or len(key) < 8:
        return "***" if key else ""
    return key[:4] + "****" + key[-4:]


@router.get("")
async def get_ai_settings(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get current AI configuration (admin only)."""
    row = await _get_or_create_settings(db)
    await db.commit()
    data = _serialize(row)
    # Attach daily usage counters
    data["daily_usage"] = await _get_daily_usage()
    return data


@router.put("")
async def update_ai_settings(
    body: dict,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update AI configuration (admin only). Partial update — only send changed fields."""
    row = await _get_or_create_settings(db)

    for field, value in body.items():
        if field not in _UPDATABLE_FIELDS:
            continue

        # Validate types
        if field.startswith("feature_") and not isinstance(value, bool):
            continue
        if field.startswith("daily_limit_") and not isinstance(value, int):
            continue
        if field.startswith("cache_ttl_") and not isinstance(value, int):
            continue
        if field in ("default_temperature",) and not isinstance(value, (int, float)):
            continue
        if field in ("default_max_tokens", "requests_per_minute", "batch_delay_ms", "primary_timeout") and not isinstance(value, int):
            continue

        # Special handling for fallback_providers
        if field == "fallback_providers":
            if not isinstance(value, list):
                continue
            # Preserve existing keys if new entry sends empty key
            existing = {p.get("name"): p for p in (row.fallback_providers or [])}
            merged = []
            for p in value:
                if not isinstance(p, dict) or not p.get("name"):
                    continue
                # Preserve existing key if new entry sends empty or masked key
                new_key = p.get("key", "")
                if not new_key or "****" in new_key:
                    # Always fall back to existing real key; never store masked values
                    new_key = existing.get(p["name"], {}).get("key", "")
                merged.append({
                    "name": p.get("name", ""),
                    "url": p.get("url", ""),
                    "key": new_key,
                    "model": p.get("model", ""),
                    "timeout": int(p.get("timeout", 30)),
                    "enabled": bool(p.get("enabled", True)),
                })
            value = merged

        # Special handling for api key — don't overwrite with empty or masked value
        if field == "primary_api_key" and (not value or "****" in str(value)):
            continue

        setattr(row, field, value)

    row.updated_by = user.id
    row.updated_at = datetime.now(timezone.utc)

    if row.fallback_providers is not None:
        flag_modified(row, "fallback_providers")

    await db.commit()

    # Invalidate the cached settings in ai.py
    await _invalidate_ai_cache()

    data = _serialize(row)
    data["daily_usage"] = await _get_daily_usage()
    logger.info("ai_settings_updated", user=user.email)
    return data


@router.post("/test-provider")
async def test_ai_provider(
    body: dict,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Test an AI provider connection with a simple prompt."""
    import httpx

    url = body.get("url", "")
    key = body.get("key", "")
    model = body.get("model", "")
    timeout = int(body.get("timeout", 15))
    # Which provider to test: "primary" or fallback index (0, 1, ...)
    provider_type = body.get("provider_type", None)

    # Always resolve API keys from database when provider_type is specified
    # (frontend sends masked keys after save/reload)
    if provider_type is not None:
        row = await _get_or_create_settings(db)
        if str(provider_type) == "primary":
            key = row.primary_api_key or key
            if not url:
                url = row.primary_api_url or ""
            if not model:
                model = row.primary_model or ""
        else:
            try:
                idx = int(provider_type)
                fb = (row.fallback_providers or [])[idx]
                key = fb.get("key", "") or key
                if not url:
                    url = fb.get("url", "")
                if not model:
                    model = fb.get("model", "")
            except (ValueError, IndexError):
                pass
    elif key and "****" in key:
        # Fallback: old frontend without provider_type sent a masked key.
        # Try to match by URL to find the real key from the database.
        row = await _get_or_create_settings(db)
        primary_url = (row.primary_api_url or "").rstrip("/").replace("/chat/completions", "")
        test_url_base = url.rstrip("/").replace("/chat/completions", "")
        if primary_url and test_url_base and primary_url == test_url_base:
            key = row.primary_api_key or key
        else:
            for fb in (row.fallback_providers or []):
                fb_url_base = fb.get("url", "").rstrip("/").replace("/chat/completions", "")
                if fb_url_base and test_url_base and fb_url_base == test_url_base:
                    key = fb.get("key", "") or key
                    break

    logger.info("test_provider_request",
                provider_type=provider_type,
                url=url,
                model=model,
                key_len=len(key) if key else 0,
                key_masked="****" in key if key else False)

    if not url or not key or not model:
        raise HTTPException(400, "url, key, and model are required")

    # Ensure we hit the chat completions endpoint
    test_url = url.rstrip("/")
    # Gemini requires /openai/ in the path for OpenAI-compatible mode
    if "generativelanguage.googleapis.com" in test_url and "/openai" not in test_url:
        test_url = test_url.rstrip("/") + "/openai"
    if not test_url.endswith("/chat/completions"):
        test_url += "/chat/completions"

    # SSRF guard: reject private/internal targets before the outbound request.
    try:
        validate_outbound_url(test_url, require_https=True)
    except UnsafeURLError as exc:
        raise HTTPException(400, f"Refusing to contact unsafe URL: {exc}") from exc

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                test_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "Respond with exactly: OK"},
                        {"role": "user", "content": "Test"},
                    ],
                    "max_tokens": 10,
                    "temperature": 0,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info("test_provider_success", provider_type=provider_type, model=model)
                return {"success": True, "status": resp.status_code, "response": content.strip()[:100]}
            logger.warning("test_provider_fail", provider_type=provider_type, status=resp.status_code, error=resp.text[:200])
            return {"success": False, "status": resp.status_code, "error": resp.text[:200]}
    except httpx.TimeoutException:
        return {"success": False, "status": 0, "error": "Connection timed out"}
    except Exception as e:
        return {"success": False, "status": 0, "error": str(e)[:200]}


@router.get("/usage")
async def get_ai_usage(
    user: Annotated[User, Depends(require_admin)],
):
    """Get today's AI usage counters per feature."""
    return await _get_daily_usage()


@router.post("/reset-usage")
async def reset_ai_usage(
    user: Annotated[User, Depends(require_admin)],
):
    """Reset today's usage counters."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    features = [
        "intel_summary", "intel_enrichment", "news_enrichment",
        "live_lookup", "report_gen", "briefing_gen",
    ]
    r = redis_client
    for f in features:
        await r.delete(f"{_DAILY_KEY_PREFIX}:{f}:{today}")
    return {"reset": True}


@router.get("/defaults")
async def get_ai_defaults(
    user: Annotated[User, Depends(require_admin)],
):
    """Return the optimal default settings (read-only, hardcoded in backend)."""
    return AI_OPTIMAL_DEFAULTS


@router.get("/default-prompts")
async def get_default_prompts(
    user: Annotated[User, Depends(require_admin)],
):
    """Return the built-in system prompts for each AI feature (read-only reference)."""
    from app.prompts import get_all_prompts, PROMPT_REGISTRY

    all_prompts = get_all_prompts()
    # Return just prompt text keyed by feature name (backward-compatible format)
    return {feature: entry["prompt"] for feature, entry in all_prompts.items()}


@router.post("/reset-defaults")
async def reset_ai_defaults(
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Reset AI settings to optimal defaults. Preserves API keys and fallback providers."""
    row = await _get_or_create_settings(db)

    for field, value in AI_OPTIMAL_DEFAULTS.items():
        if field not in _UPDATABLE_FIELDS:
            continue
        # Never reset secrets
        if field in ("primary_api_key", "fallback_providers"):
            continue
        setattr(row, field, value)

    # Clear custom prompts
    for f in ("intel_summary", "intel_enrichment", "news_enrichment",
              "live_lookup", "report_gen", "briefing_gen"):
        setattr(row, f"prompt_{f}", None)

    row.updated_by = user.id
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await _invalidate_ai_cache()

    data = _serialize(row)
    data["daily_usage"] = await _get_daily_usage()
    logger.info("ai_settings_reset_to_defaults", user=user.email)
    return data


@router.get("/health")
async def ai_provider_health(
    user: Annotated[User, Depends(require_admin)],
):
    """Check health of all configured AI providers."""
    from app.services.ai import check_ai_health
    return await check_ai_health()


@router.post("/promote-fallback")
async def promote_fallback(
    body: dict,
    user: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Swap a fallback provider to primary (server-side, handles real keys)."""
    idx = body.get("index")
    if idx is None or not isinstance(idx, int):
        raise HTTPException(400, "index is required (integer)")

    row = await _get_or_create_settings(db)
    fallbacks = row.fallback_providers or []
    if idx < 0 or idx >= len(fallbacks):
        raise HTTPException(400, f"Invalid fallback index: {idx}")

    fb = fallbacks[idx]

    # Save current primary as fallback entry
    old_primary = {
        "name": row.primary_provider,
        "url": row.primary_api_url,
        "key": row.primary_api_key,
        "model": row.primary_model,
        "timeout": row.primary_timeout,
        "enabled": True,
    }

    # Promote fallback to primary
    row.primary_provider = fb.get("name", "")
    row.primary_api_url = fb.get("url", "")
    row.primary_api_key = fb.get("key", "")
    row.primary_model = fb.get("model", "")
    row.primary_timeout = int(fb.get("timeout", 30))

    # Replace the promoted fallback with old primary
    fallbacks[idx] = old_primary
    row.fallback_providers = fallbacks
    flag_modified(row, "fallback_providers")

    row.updated_by = user.id
    row.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await _invalidate_ai_cache()

    data = _serialize(row)
    data["daily_usage"] = await _get_daily_usage()
    logger.info("ai_fallback_promoted", index=idx, new_primary=row.primary_provider, user=user.email)
    return data


# ─── Helpers ─────────────────────────────────────────────

async def _get_daily_usage() -> dict:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    features = [
        "intel_summary", "intel_enrichment", "news_enrichment",
        "live_lookup", "report_gen", "briefing_gen",
    ]
    r = redis_client
    usage = {}
    for f in features:
        val = await r.get(f"{_DAILY_KEY_PREFIX}:{f}:{today}")
        usage[f] = int(val) if val else 0
    return usage


async def _invalidate_ai_cache():
    """Clear the cached AI settings so ai.py reloads from DB on next call."""
    r = redis_client
    await r.delete("ai_settings_cache")


# ──────────────────────────────────────────────────────────────────
# Multi-agent pipeline introspection + token-usage telemetry
# (used by the AI Configuration panel to visualise routing + costs)
# ──────────────────────────────────────────────────────────────────

# Short Redis TTL for the agent-catalog response — Bedrock agent state
# ("PREPARED", alias id, collaborator count) is ~static, don't hammer the
# control-plane API on every UI poll.
_PIPELINE_CACHE_KEY = "ai_settings:pipeline"
_PIPELINE_CACHE_TTL = 60  # seconds


@router.get("/pipeline")
async def get_pipeline_config():
    """Return the multi-agent routing + agent-catalog snapshot.

    Anonymous-accessible on purpose — the AI Configuration panel needs it
    and the site runs in demo_mode where require_admin would admit
    everyone anyway. Exposes only public IDs / flag state / alias names.
    """
    import json

    cached = await redis_client.get(_PIPELINE_CACHE_KEY)
    if cached:
        return json.loads(cached)

    s = env_settings
    # Routing map — which feature takes which path today.
    routing = [
        {
            "feature": "News Enrichment",
            "path": "agent" if s.ai_use_agents else "single-shot",
            "model": "Supervisor+IOC-Analyst+Risk-Scorer" if s.ai_use_agents else s.ai_model or "amazon.nova-lite-v1:0",
            "flag": "AI_USE_AGENTS",
            "flag_value": bool(s.ai_use_agents),
        },
        {
            "feature": "IOC Live Lookup",
            "path": "agent + single-shot fallback" if s.ai_use_agents_for_ioc else "single-shot",
            "model": "Supervisor+IOC-Analyst" if s.ai_use_agents_for_ioc else s.ai_model or "amazon.nova-lite-v1:0",
            "flag": "AI_USE_AGENTS_FOR_IOC",
            "flag_value": bool(s.ai_use_agents_for_ioc),
        },
        {"feature": "Intel Summary",       "path": "single-shot", "model": s.ai_model or "amazon.nova-lite-v1:0", "flag": None, "flag_value": None},
        {"feature": "Intel Enrichment",    "path": "single-shot", "model": s.ai_model or "amazon.nova-lite-v1:0", "flag": None, "flag_value": None},
        {"feature": "Report Generation",   "path": "single-shot", "model": s.ai_model or "amazon.nova-lite-v1:0", "flag": None, "flag_value": None},
        {"feature": "Briefing Generation", "path": "single-shot", "model": s.ai_model or "amazon.nova-lite-v1:0", "flag": None, "flag_value": None},
        {"feature": "KQL Generation",      "path": "single-shot", "model": s.ai_model or "amazon.nova-lite-v1:0", "flag": None, "flag_value": None},
    ]

    # Agent catalog — query Bedrock control plane for live status.
    # Fail soft: if boto3 can't reach the control plane (perms, offline,
    # region), surface unknown-status entries rather than 5xx'ing.
    agents: list[dict] = []
    action_groups: list[dict] = []
    try:
        import boto3
        c = boto3.client("bedrock-agent", region_name=s.aws_region or "us-east-1")

        sup_id = s.bedrock_supervisor_agent_id or "FQBSERZQMP"
        sup_alias = s.bedrock_supervisor_alias_id or "HLSRFAFL42"

        try:
            a = c.get_agent(agentId=sup_id)["agent"]
            al = c.get_agent_alias(agentId=sup_id, agentAliasId=sup_alias)["agentAlias"]
            agent_version = al.get("routingConfiguration", [{}])[0].get("agentVersion", "DRAFT")
            try:
                collabs = c.list_agent_collaborators(agentId=sup_id, agentVersion=agent_version).get("agentCollaboratorSummaries", [])
            except Exception:
                collabs = []

            agents.append({
                "name": a.get("agentName", "Supervisor"),
                "role": "SUPERVISOR_ROUTER",
                "agent_id": sup_id,
                "alias_id": sup_alias,
                "alias_name": al.get("agentAliasName", ""),
                "status": a.get("agentStatus", "UNKNOWN"),
                "collaborators": len(collabs),
            })

            # Collaborators — pull their names / statuses too
            for sub in collabs:
                cid = sub.get("agentDescriptor", {}).get("aliasArn", "").split("/")[-3] if sub.get("agentDescriptor") else None
                sub_name = sub.get("collaboratorName") or "Collaborator"
                sub_status = "LINKED"
                if cid and len(cid) == 10:  # rough agentId shape
                    try:
                        sa = c.get_agent(agentId=cid)["agent"]
                        sub_name = sa.get("agentName", sub_name)
                        sub_status = sa.get("agentStatus", sub_status)
                    except Exception:
                        pass
                # Count action groups on this collaborator
                ag_count = 0
                if cid:
                    try:
                        ags = c.list_agent_action_groups(agentId=cid, agentVersion="DRAFT").get("actionGroupSummaries", [])
                        ag_count = len(ags)
                        for ag in ags:
                            action_groups.append({
                                "name": ag.get("actionGroupName", ""),
                                "state": ag.get("actionGroupState", "UNKNOWN"),
                                "agent": sub_name,
                            })
                    except Exception:
                        pass

                agents.append({
                    "name": sub_name,
                    "role": sub.get("relayConversationHistory") or "collaborator",
                    "agent_id": cid or "",
                    "status": sub_status,
                    "action_groups": ag_count,
                })

        except Exception as e:
            logger.warning("pipeline_agent_lookup_failed", error=str(e))
            agents.append({"name": "Supervisor", "agent_id": sup_id, "status": "UNREACHABLE", "error": str(e)[:120]})

    except ImportError:
        logger.warning("pipeline_boto3_missing")

    payload = {
        "routing": routing,
        "agents": agents,
        "action_groups": action_groups,
        "region": s.aws_region or "us-east-1",
        "primary_model": s.ai_model or "amazon.nova-lite-v1:0",
    }
    await redis_client.set(_PIPELINE_CACHE_KEY, json.dumps(payload), ex=_PIPELINE_CACHE_TTL)
    return payload


@router.get("/token-usage")
async def get_token_usage_endpoint(days: int = 7):
    """Return real-time Bedrock/agent token + cost aggregates.

    Counters are incremented on every successful invocation (see
    `app.core.ai_telemetry.track_invocation`). Values here are at most a
    few milliseconds stale — no response caching.
    """
    from app.core.ai_telemetry import get_token_usage
    return await get_token_usage(days=days)
