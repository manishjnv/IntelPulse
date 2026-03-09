"""Confidence normalisation."""

from __future__ import annotations

VALID_CONFIDENCE_LEVELS = {"high", "medium", "low"}


def normalize_confidence(value: str | None, default: str = "medium") -> str:
    """Clamp a confidence value to one of the valid levels."""
    if value in VALID_CONFIDENCE_LEVELS:
        return value
    return default
