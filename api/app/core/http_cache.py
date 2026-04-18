"""HTTP edge-cache helpers for Cloudflare-hittable responses.

Some anonymous GET endpoints return identical bytes for every user (demo
mode authenticates everyone as the same admin user, so there is no
per-user variation). For those, a short-TTL `Cache-Control: public`
header lets Cloudflare serve repeat hits from the edge for all users in
the s-maxage window, falling back to stale-while-revalidate for another
5 min. The browser still revalidates per its own freshness window.

Use as a FastAPI route dependency:

    @router.get("/foo", dependencies=[Depends(edge_cacheable)])

Do NOT apply to user-scoped routes (notifications, admin audit, anything
reading cookies), exports, or mutating endpoints.
"""

from __future__ import annotations

from fastapi import Response

_EDGE_CACHE_HEADER = "public, s-maxage=30, stale-while-revalidate=300"


def edge_cacheable(response: Response) -> None:
    response.headers["Cache-Control"] = _EDGE_CACHE_HEADER
