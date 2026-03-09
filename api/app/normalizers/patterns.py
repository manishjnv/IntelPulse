"""IOC pattern matching — compiled regexes for type detection.

Single source of truth for IOC type detection used by both the search
service and the worker IOC extraction pipeline.
"""

from __future__ import annotations

import re

# ── Compiled IOC regex patterns ──────────────────────────

IOC_PATTERNS: dict[str, re.Pattern[str]] = {
    "cve": re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE),
    "ip": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "domain": re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$"),
    "url": re.compile(r"^https?://", re.IGNORECASE),
    "hash_md5": re.compile(r"^[a-fA-F0-9]{32}$"),
    "hash_sha1": re.compile(r"^[a-fA-F0-9]{40}$"),
    "hash_sha256": re.compile(r"^[a-fA-F0-9]{64}$"),
    "email": re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"),
}

# Standalone CVE extractor (used by intel_extraction)
CVE_RE = re.compile(r"(CVE-\d{4}-\d{4,})", re.IGNORECASE)


def detect_ioc_type(query: str) -> str | None:
    """Auto-detect the type of an IOC from a query string."""
    q = query.strip()
    for ioc_type, pattern in IOC_PATTERNS.items():
        if pattern.match(q):
            return ioc_type
    return None
