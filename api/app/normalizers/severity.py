"""Severity normalisation — single source of truth.

Provides score mapping (for risk scoring) and rank mapping (for merge
resolution in intel extraction), plus a priority→severity converter.
"""

from __future__ import annotations

# Score mapping used by the risk-scoring service (0-100 scale)
SEVERITY_SCORES: dict[str, int] = {
    "critical": 100,
    "high": 80,
    "medium": 50,
    "low": 25,
    "info": 10,
    "unknown": 0,
}

# Rank mapping for merge-conflict resolution (higher wins)
SEVERITY_RANK: dict[str, int] = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
    "info": 0,
    "unknown": -1,
}


def priority_to_severity(priority: str | None) -> str:
    """Map a news item's recommended_priority to a severity string."""
    mapping = {"critical": "critical", "high": "high", "medium": "medium", "low": "low"}
    return mapping.get((priority or "").lower(), "unknown")
