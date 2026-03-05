"""CISA ICS Advisories feed connector — advisory feed.

Free, no API key required.  Fetches CISA ICS-CERT advisories from
their public RSS/Atom feed at
https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml

Populates feed_type: "advisory".
"""

from __future__ import annotations

import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from app.core.logging import get_logger
from app.services.feeds.base import BaseFeedConnector

logger = get_logger(__name__)

CISA_ADVISORIES_URL = "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml"


class CISAAdvisoriesConnector(BaseFeedConnector):
    FEED_NAME = "cisa_advisories"
    SOURCE_RELIABILITY = 95

    async def fetch(self, last_cursor: str | None = None) -> list[dict]:
        """Fetch CISA ICS advisories from RSS feed."""
        response = await self.client.get(
            CISA_ADVISORIES_URL,
            headers={"User-Agent": "IntelWatch/1.0 TI-Platform"},
        )
        response.raise_for_status()

        items: list[dict] = []
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as e:
            logger.error("cisa_advisories_parse_error", error=str(e))
            return []

        # RSS 2.0 → channel/item
        for item_el in root.findall(".//item"):
            item: dict = {}
            item["title"] = (item_el.findtext("title") or "").strip()
            item["link"] = (item_el.findtext("link") or "").strip()
            item["description"] = (item_el.findtext("description") or "").strip()
            item["pubDate"] = (item_el.findtext("pubDate") or "").strip()
            item["category"] = (item_el.findtext("category") or "").strip()
            if item["title"]:
                items.append(item)

        # If RSS 2.0 parsing yields nothing, try Atom namespace
        if not items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns):
                item = {}
                item["title"] = (entry.findtext("atom:title", namespaces=ns) or "").strip()
                link_el = entry.find("atom:link", ns)
                item["link"] = link_el.get("href", "") if link_el is not None else ""
                item["description"] = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
                item["pubDate"] = (entry.findtext("atom:updated", namespaces=ns) or "").strip()
                item["category"] = ""
                if item["title"]:
                    items.append(item)

        logger.info("cisa_advisories_fetch", total=len(items))

        # Incremental filter
        if last_cursor:
            try:
                cursor_dt = datetime.fromisoformat(last_cursor)
                items = [
                    i for i in items
                    if self._parse_date(i.get("pubDate"))
                    and self._parse_date(i.get("pubDate")) > cursor_dt
                ]
            except (ValueError, TypeError):
                pass

        if items:
            dates = [self._parse_date(i.get("pubDate")) for i in items]
            valid = [d for d in dates if d]
            if valid:
                self._next_cursor = max(valid).isoformat()

        return items

    def _parse_date(self, date_str: str | None) -> datetime | None:
        if not date_str:
            return None
        try:
            return parsedate_to_datetime(date_str).astimezone(timezone.utc)
        except Exception:
            pass
        # Attempt ISO format (Atom feeds)
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def _extract_cves(self, text: str) -> list[str]:
        if not text:
            return []
        return list(set(re.findall(r"CVE-\d{4}-\d{4,7}", text, re.IGNORECASE)))[:15]

    def _extract_icsa_id(self, link: str, title: str) -> str:
        """Extract ICSA/ICSMA ID from link or title."""
        combined = link + " " + title
        m = re.search(r"(ICS[AM]?-\d{2}-\d{3}-\d+)", combined, re.IGNORECASE)
        return m.group(1).upper() if m else ""

    def _classify_severity(self, title: str, desc: str) -> str:
        combined = (title + " " + desc).lower()
        if any(kw in combined for kw in (
            "critical", "remote code execution", "rce", "authentication bypass",
            "command injection", "unauthenticated",
        )):
            return "critical"
        if any(kw in combined for kw in (
            "high", "privilege escalation", "buffer overflow", "sql injection",
            "arbitrary", "improper authentication",
        )):
            return "high"
        if any(kw in combined for kw in (
            "medium", "denial of service", "dos", "xss", "cross-site",
            "information disclosure",
        )):
            return "medium"
        # Most ICS advisories are high severity by default
        return "high"

    def _extract_industries(self, title: str, desc: str) -> list[str]:
        combined = (title + " " + desc).lower()
        industries = []
        kw_map = {
            "energy": ["energy", "power", "grid", "electricity", "scada"],
            "manufacturing": ["manufacturing", "factory", "industrial"],
            "water": ["water", "wastewater", "utility"],
            "healthcare": ["healthcare", "medical", "hospital"],
            "transportation": ["transportation", "rail", "aviation"],
            "critical_infrastructure": ["critical infrastructure", "ics", "plc", "hmi"],
            "chemical": ["chemical", "oil", "gas", "petroleum"],
        }
        for industry, keywords in kw_map.items():
            if any(kw in combined for kw in keywords):
                industries.append(industry)
        if not industries:
            industries.append("critical_infrastructure")
        return industries[:5]

    def _extract_vendor(self, title: str) -> list[str]:
        """Try to extract vendor/product from title like 'Siemens SIMATIC S7-1200'."""
        # Pattern: often starts with vendor name
        m = re.match(r"^([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)", title)
        if m and len(m.group(1)) < 50:
            return [m.group(1).strip()]
        return []

    def normalize(self, raw_items: list[dict]) -> list[dict]:
        items = []
        for raw in raw_items:
            title = raw.get("title", "")
            link = raw.get("link", "")
            description = raw.get("description", "")
            pub_date = self._parse_date(raw.get("pubDate"))
            icsa_id = self._extract_icsa_id(link, title)
            cves = self._extract_cves(title + " " + description)
            severity = self._classify_severity(title, description)
            industries = self._extract_industries(title, description)
            products = self._extract_vendor(title)

            tags = ["advisory", "cisa", "ics"]
            if icsa_id:
                tags.append(icsa_id.lower())
            if "update" in title.lower():
                tags.append("update")
            category = raw.get("category", "").strip()
            if category:
                tags.append(category.lower().replace(" ", "_"))

            items.append({
                "id": uuid.uuid4(),
                "title": f"[CISA Advisory] {title[:120]}",
                "summary": f"Advisory: {icsa_id or 'N/A'} | CVEs: {', '.join(cves) if cves else 'N/A'} | Industries: {', '.join(industries[:3])}",
                "description": description[:2000] if description else f"CISA ICS Advisory: {title}",
                "published_at": pub_date,
                "ingested_at": self.now_utc(),
                "updated_at": self.now_utc(),
                "severity": severity,
                "risk_score": 0,
                "confidence": 90,
                "source_name": "CISA",
                "source_url": link,
                "source_reliability": self.SOURCE_RELIABILITY,
                "source_ref": icsa_id or link,
                "feed_type": "advisory",
                "asset_type": "cve" if cves else "other",
                "tlp": "TLP:CLEAR",
                "tags": tags[:15],
                "geo": [],
                "industries": industries,
                "cve_ids": cves,
                "affected_products": products[:5],
                "related_ioc_count": 0,
                "is_kev": False,
                "exploit_available": False,
                "exploitability_score": None,
                "source_hash": self.generate_hash("cisa_advisories", icsa_id or link),
            })

        logger.info("cisa_advisories_normalize", count=len(items))
        return items
