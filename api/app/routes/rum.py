"""Real-user web-vitals collection endpoint.

Accepts sendBeacon POSTs from the UI via `useReportWebVitals`. Writes a
structured log line per metric — aggregation is left to the log sink
(journald / CloudWatch). No DB write: this must stay cheap because every
pageview emits ~5 beacons and RUM traffic scales with user activity.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["rum"])


class WebVitalEvent(BaseModel):
    name: Literal[
        "FCP",
        "LCP",
        "CLS",
        "INP",
        "TTFB",
        "FID",
        "Next.js-hydration",
        "Next.js-route-change-to-render",
        "Next.js-render",
    ]
    value: float = Field(ge=0, le=600_000)
    id: str = Field(max_length=80)
    path: str = Field(max_length=200)
    rating: Literal["good", "needs-improvement", "poor"] | None = None


@router.post("/rum", status_code=204, include_in_schema=False)
async def record_web_vital(event: WebVitalEvent, request: Request) -> None:
    logger.info(
        "web_vital",
        metric=event.name,
        value=round(event.value, 2),
        rating=event.rating,
        path=event.path,
        id=event.id,
    )
