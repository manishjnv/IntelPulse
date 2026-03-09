"""Entity normalisation — products, campaigns, and vendor resolution.

Centralises the blocklists, junk-pattern detection, product name
canonicalisation, campaign name normalisation, and vendor guessing
previously scattered in intel_extraction.py.
"""

from __future__ import annotations

import re

# ── Product blocklist: generic terms the AI hallucinates ──

PRODUCT_BLOCKLIST: set[str] = {
    "nim", "zig", "crystal", "ip cameras", "wikipedia", "python executables",
    "all mfa-enabled applications", "atm software and hardware",
    "desktop oss", "mobile platforms", "web browsers", "email and cloud-based services",
    "enterprise software and appliances", "tpms systems in modern cars",
    "ring doorbell cameras", "unknown product",
}

# Terms that signal a product name is actually a category/summary
PRODUCT_JUNK_PATTERNS = re.compile(
    r"\(\d+ zero-day|\(multiple |all .+ applications|generic|various",
    re.IGNORECASE,
)

# Campaign names to normalise to NULL
NULL_CAMPAIGN_NAMES: set[str] = {"unknown", "null", "n/a", "none", "", "unattributed"}

# ── Vendor lookup ────────────────────────────────────────

KNOWN_VENDORS: dict[str, str] = {
    "windows": "Microsoft", "office": "Microsoft", "exchange": "Microsoft",
    "azure": "Microsoft", "edge": "Microsoft", ".net": "Microsoft",
    "chrome": "Google", "android": "Google", "chromium": "Google",
    "ios": "Apple", "macos": "Apple", "safari": "Apple", "webkit": "Apple",
    "firefox": "Mozilla", "thunderbird": "Mozilla",
    "linux": "Linux Foundation", "kernel": "Linux Foundation",
    "apache": "Apache", "tomcat": "Apache", "struts": "Apache",
    "nginx": "F5/NGINX", "cisco": "Cisco", "fortinet": "Fortinet",
    "fortigate": "Fortinet", "fortios": "Fortinet",
    "palo alto": "Palo Alto Networks", "pan-os": "Palo Alto Networks",
    "vmware": "VMware/Broadcom", "esxi": "VMware/Broadcom",
    "ivanti": "Ivanti", "pulse": "Ivanti",
    "citrix": "Citrix", "netscaler": "Citrix",
    "confluence": "Atlassian", "jira": "Atlassian",
    "jenkins": "Jenkins", "wordpress": "WordPress",
    "oracle": "Oracle", "java": "Oracle",
    "adobe": "Adobe", "acrobat": "Adobe",
    "sap": "SAP", "ibm": "IBM",
    "juniper": "Juniper Networks", "sonicwall": "SonicWall",
    "zyxel": "Zyxel", "qnap": "QNAP", "synology": "Synology",
    "samsung": "Samsung", "huawei": "Huawei", "tp-link": "TP-Link",
    "d-link": "D-Link",
}


def is_junk_product(name: str) -> bool:
    """Return True if the product name is a known junk / generic entry."""
    n = name.strip().lower()
    if n in PRODUCT_BLOCKLIST:
        return True
    if PRODUCT_JUNK_PATTERNS.search(n):
        return True
    if len(n.split()) == 1 and len(n) < 12 and n.isalpha():
        return True
    return False


def normalize_product_name(name: str) -> str:
    """Canonicalize product name to reduce duplicates.

    Strips trailing version strings, collapses whitespace, applies
    intelligent title-casing that preserves acronyms.
    """
    n = name.strip()
    n = re.sub(r"\s+v?\d+[\d.x*]+\s*$", "", n, flags=re.IGNORECASE)
    n = re.sub(r"\s*\(\d{4}\)\s*$", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    words = n.split()
    result = []
    for w in words:
        if w.isupper() and len(w) > 1:
            result.append(w)
        elif "-" in w:
            result.append(w)
        else:
            result.append(w.capitalize() if w.islower() else w)
    return " ".join(result) if result else n


def normalise_campaign_name(name: str | None) -> str | None:
    """Normalise 'null', 'Unknown', etc. to None."""
    if name is None:
        return None
    if name.strip().lower() in NULL_CAMPAIGN_NAMES:
        return None
    return name.strip()


def guess_vendor(product_name: str) -> str | None:
    """Extract vendor from common product naming patterns."""
    name_lower = product_name.lower()
    for keyword, vendor in KNOWN_VENDORS.items():
        if keyword in name_lower:
            return vendor
    return None
