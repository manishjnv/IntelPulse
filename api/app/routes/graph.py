"""API routes for relationship graph exploration."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.http_cache import edge_cacheable
from app.core.redis import get_cached, set_cached, cache_key
from app.middleware.auth import require_viewer
from app.models.models import User, Relationship
from app.schemas import (
    GraphResponse,
    GraphNode,
    GraphEdge,
    GraphStatsResponse,
    RelatedIntelItem,
)
from app.services.graph import (
    get_entity_graph,
    get_related_intel,
    get_graph_stats,
    get_featured_entities,
)

router = APIRouter(prefix="/graph", tags=["Graph"])


@router.get("/explore", response_model=GraphResponse)
async def explore_graph(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_id: str = Query(..., description="Entity UUID or ID"),
    entity_type: str = Query(default="intel", description="intel | ioc | technique | cve"),
    depth: int = Query(default=1, ge=1, le=3, description="Traversal depth (1-3 hops)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max edges per hop"),
):
    """Explore the entity relationship graph from a starting node.

    Returns nodes and edges for D3/vis.js visualization.
    """
    ck = cache_key("graph", entity_id, entity_type, str(depth))
    cached = await get_cached(ck)
    if cached:
        return cached

    data = await get_entity_graph(db, entity_id, entity_type, depth=depth, limit=limit)

    response = GraphResponse(
        nodes=[GraphNode(**n) for n in data["nodes"]],
        edges=[GraphEdge(**e) for e in data["edges"]],
        center=data["center"],
        total_nodes=data["total_nodes"],
        total_edges=data["total_edges"],
    )

    await set_cached(ck, response.model_dump(), ttl=60)
    return response


@router.get("/related/{item_id}", response_model=list[RelatedIntelItem])
async def get_related_items(
    item_id: uuid.UUID,
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=50),
):
    """Get intel items related to a given intel item, ranked by relationship confidence."""
    ck = cache_key("related", str(item_id))
    cached = await get_cached(ck)
    if cached:
        return cached

    items = await get_related_intel(db, str(item_id), limit=limit)
    await set_cached(ck, items, ttl=60)
    return items


@router.get("/featured", dependencies=[Depends(edge_cacheable)])
async def graph_featured(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=12, ge=1, le=30),
):
    """Return most-connected entities for the Investigate empty state.

    Each entry carries enough to render a clickable chip AND to round-trip
    through /explore: `id` (prefixed), `type`, `label`, `degree`, plus type-
    specific fields like `severity`, `risk_score`, `ioc_type`, `tactic`.
    """
    ck = cache_key("graph_featured", str(limit))
    cached = await get_cached(ck)
    if cached:
        return cached

    featured = await get_featured_entities(db, limit=limit)
    payload = {"featured": featured}
    await set_cached(ck, payload, ttl=120)
    return payload


@router.get("/stats", response_model=GraphStatsResponse, dependencies=[Depends(edge_cacheable)])
async def graph_statistics(
    user: Annotated[User, Depends(require_viewer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get aggregate statistics about the relationship graph."""
    ck = cache_key("graph_stats")
    cached = await get_cached(ck)
    if cached:
        return cached

    stats = await get_graph_stats(db)
    await set_cached(ck, stats, ttl=120)
    return stats
