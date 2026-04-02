# IntelPulse — Intel Items Module

> Complete technical reference for Intel Items: detail pages, AI enrichment, related items, IOC linking, export, and the unified intel data model.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [Intel List & Filters](#4-intel-list--filters)
5. [Intel Detail Page](#5-intel-detail-page)
6. [AI Enrichment](#6-ai-enrichment)
7. [Related Items Engine](#7-related-items-engine)
8. [IOC Linking & Enrichment](#8-ioc-linking--enrichment)
9. [Excel Export](#9-excel-export)
10. [Database Schema](#10-database-schema)
11. [Caching Strategy](#11-caching-strategy)
12. [Constants & Thresholds Reference](#12-constants--thresholds-reference)
13. [Intel List UI Layout](#13-intel-list-ui-layout)
14. [Intel Detail UI Layout](#14-intel-detail-ui-layout)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  intel_items │ iocs │ intel_ioc_links │ intel_attack_links    │
│  ──────────────────────────────────────────────              │
│  OpenSearch (full-text + aggregations)                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                 FastAPI Routes (/intel)                       │
│  List │ Stats │ Detail │ Enrichment │ Related │ IOCs │ Export │
│  Cache: Redis (30s–21600s)                                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                           │
│  Intel list (/intel) │ Intel detail (/intel/[id])             │
│  6-tab detail view │ Auto-refresh (30s) │ Excel export        │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend routes | `api/app/routes/intel.py` |
| Scoring service | `api/app/services/scoring.py` |
| Export service | `api/app/services/export.py` |
| AI service | `api/app/services/ai.py` |
| Enrichment service | `api/app/services/enrichment.py` |
| Intel list page | `ui/src/app/(app)/intel/page.tsx` |
| Intel detail page | `ui/src/app/(app)/intel/[id]/page.tsx` |
| IntelCard | `ui/src/components/IntelCard.tsx` |
| StructuredIntelCards | `ui/src/components/StructuredIntelCards.tsx` |

---

## 3. API Endpoints

### `GET /api/v1/intel`

Paginated intel items with 12 filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 20 | Items per page (max 100) |
| `severity` | string | — | Filter: critical, high, medium, low, info |
| `feed_type` | string | — | Filter: vulnerability, ioc, malware, etc. |
| `source_name` | string | — | Filter by source |
| `asset_type` | string | — | Filter: ip, domain, url, hash_*, email, cve |
| `is_kev` | bool | — | Only KEV items |
| `exploit_available` | bool | — | Only items with exploits |
| `query` | string | — | Full-text search |
| `geo` | string | — | Filter by geography |
| `industry` | string | — | Filter by industry |
| `sort_by` | string | `ingested_at` | Sort field |
| `sort_order` | string | `desc` | asc or desc |

**Cache:** 30 seconds

### `GET /api/v1/intel/stats`

Global stats for intel items.

**Response fields:**

| Field | Description |
|-------|-------------|
| `total` | Total intel items |
| `today` | Ingested in last 24h |
| `by_severity` | Counts per severity level |
| `kev_count` | KEV flagged items |
| `exploit_count` | Items with available exploits |
| `avg_risk` | Average risk score |
| `sources` | Distinct source count |
| `ai_enriched` | Items with AI summaries |
| `top_sources` | Top 10 sources with counts |
| `top_tags` | Top 15 tags |
| `top_cves` | Top 10 CVEs |
| `feed_type_counts` | Counts per feed type |
| `asset_type_counts` | Counts per asset type |

**Cache:** 60 seconds

### `GET /api/v1/intel/{id}`

Single intel item by UUID.

### `GET /api/v1/intel/{id}/enrichment`

AI-powered enrichment for a specific item.

**Cache:** 21600 seconds (6 hours)

**AI parameters:** `max_tokens=2000`, `temperature=0.2`

**System prompt generates a 10-field JSON schema:**
- Threat overview, technical analysis, affected products
- Exploitation context, remediation steps, detection guidance
- Threat actors, notable attacks, MITRE ATT&CK mapping
- Timeline of events

### `GET /api/v1/intel/{id}/related`

Related items using PostgreSQL array overlap (`&&` operator).

**Confidence scoring formula:**
```
score = (shared_cves × 40) + (shared_products × 30) + (shared_tags × 10)
```

**Cache:** 300 seconds

### `GET /api/v1/intel/{id}/iocs`

Linked IOCs with enrichment data (IPinfo, InternetDB, EPSS).

**Cache:** 120 seconds

### `GET /api/v1/intel/export`

Excel export with up to 5000 items.

---

## 4. Intel List & Filters

### Filter Options

| Filter | Values |
|--------|--------|
| Severity | critical, high, medium, low, info |
| Feed Type | vulnerability, ioc, malware, exploit, advisory, threat_actor, campaign |
| Asset Type | cve, ip, url, domain, hash_sha256, hash_md5, email, file, other |
| Sort | Most Recent, Highest Risk, Published Date, Lowest Risk, Severity |
| Quick Toggles | KEV Only, Exploit Only |

### Auto-Refresh

Intel list auto-refreshes every **30 seconds**.

---

## 5. Intel Detail Page

6-tab detail view (`intel/[id]/page.tsx`, ~1600 lines):

### Tab 1: Overview
- Executive Brief
- AI Summary
- Full Description
- StructuredIntelCards (parsed AI enrichment)
- Threat Actors (motivation emoji, confidence color, aliases, hunt link)
- Notable Attacks & Breaches (timeline with severity dots)
- Affected Products & Fix Versions table
- Source Info / Timestamps / Classification / Context metadata grid
- Exploitation Context

### Tab 2: ATT&CK
- MITRE ATT&CK mapped techniques
- AI-Inferred techniques with mitigations

### Tab 3: Timeline
Enhanced timeline with event types:
- disclosure, publication, patch, exploit, kev, advisory, update
- Color-coded dots per event type
- AI vs system source indicators

### Tab 4: Remediation
- Priority banner
- Remediation steps
- Workarounds
- Patch availability info
- Vendor references

### Tab 5: Related Intel
- Items linked by shared IOCs/CVEs/tags
- Confidence scores
- Link to investigation graph

### Tab 6: IOCs
- Stats summary (total, types, countries, vulnerabilities)
- IOC detail rows with expandable enrichment:
  - Geolocation (country, continent, ASN)
  - InternetDB (ports, vulnerabilities, CPEs, hostnames)
  - EPSS score

---

## 6. AI Enrichment

### Enrichment Endpoint

`GET /intel/{id}/enrichment` triggers on-demand AI analysis.

**System prompt schema (10 fields):**

| Field | Description |
|-------|-------------|
| `executive_summary` | 2-3 sentence executive brief for decision makers |
| `threat_actors` | Array of `{name, aliases[], motivation, confidence, description}` |
| `attack_techniques` | Array of `{technique_id, technique_name, tactic, description, mitigations[]}` |
| `affected_versions` | Array of `{product, vendor, versions_affected, fixed_version, patch_url, cpe}` |
| `timeline_events` | Array of `{date, event, description, type}` (types: disclosure/publication/patch/exploit/kev/advisory/update) |
| `notable_campaigns` | Array of `{name, date, description, impact}` |
| `exploitation_info` | `{epss_estimate, exploit_maturity, in_the_wild, ransomware_use, description}` |
| `remediation` | `{priority, guidance[], workarounds[], references[{title, url}]}` |
| `related_cves` | Array of CVE IDs |
| `tags_suggested` | Array of suggested tags |

**Full AI system prompt:**
```
You are an expert cyber threat intelligence analyst. Given an intel item, produce a
structured JSON enrichment analysis. Return ONLY valid JSON with these keys:
{
  "executive_summary": "2-3 sentence executive brief for decision makers",
  "threat_actors": [{"name": "...", "aliases": [...], "motivation": "financial/espionage/
    hacktivism/unknown", "confidence": "high/medium/low", "description": "..."}],
  "attack_techniques": [{"technique_id": "T1xxx", "technique_name": "...",
    "tactic": "...", "description": "...", "mitigations": [...]}],
  "affected_versions": [{"product": "...", "vendor": "...",
    "versions_affected": "...", "fixed_version": "...", "patch_url": "...", "cpe": "..."}],
  "timeline_events": [{"date": "YYYY-MM-DD", "event": "...", "description": "...",
    "type": "disclosure|publication|patch|exploit|kev|advisory|update"}],
  "notable_campaigns": [{"name": "...", "date": "...", "description": "...",
    "impact": "..."}],
  "exploitation_info": {"epss_estimate": 0.0-1.0,
    "exploit_maturity": "none/poc/weaponized/unknown", "in_the_wild": bool,
    "ransomware_use": bool, "description": "..."},
  "remediation": {"priority": "critical/high/medium/low", "guidance": [...],
    "workarounds": [...], "references": [{"title": "...", "url": "..."}]},
  "related_cves": ["CVE-YYYY-NNNNN"],
  "tags_suggested": ["tag1", "tag2"]
}
Rules: Only include data you are confident about. Leave arrays empty if unsure.
For CVEs, base analysis on known vulnerability data.
Be specific with version info. If unknown, set fixed_version to null.
EPSS estimate: provide your best estimate of exploitation probability (0-1 scale).
Return ONLY the JSON object, no markdown, no explanation.
```

**User prompt fields (built dynamically):**
- Title, Severity, Risk Score, Source, Feed Type, Published date
- Description (first 2000 chars)
- CVE IDs (first 10), Affected Products (first 10), Tags (first 15)
- Conditional fields: KEV status, exploit availability, exploitability score, geo, industries, AI summary

### AI Summary Generation (Worker)

Batch task `generate_ai_summaries` runs every **5 minutes**, processing up to 5 items per batch, ordered by risk score (highest first).

---

## 7. Related Items Engine

PostgreSQL array overlap query (`&&` operator) on:
- `cve_ids` — shared CVE references
- `affected_products` — shared product names
- `tags` — shared tags

**Confidence formula:**
```
confidence = (shared_cve_count × 40) + (shared_product_count × 30) + (shared_tag_count × 10)
```
Capped at 100.

---

## 8. IOC Linking & Enrichment

IOCs are extracted from intel items and linked via `intel_ioc_links`.

### IOC Enrichment Data

| Source | Data | IOC Types |
|--------|------|-----------|
| IPinfo Lite | Country, ASN, continent | IP addresses |
| Shodan InternetDB | Open ports, CVEs, CPEs, hostnames | IP addresses |
| FIRST EPSS | Exploit prediction scores | CVEs |

### Worker Tasks

| Task | Interval | Batch Size |
|------|----------|-----------|
| `extract_iocs` | 10 min | 500 |
| `enrich_ips_ipinfo` | 10 min | 100 |
| `enrich_ips_internetdb` | 10 min | 100 |
| `enrich_epss_scores` | 24 hours | 5000 |

---

## 9. Excel Export

`GET /intel/export` generates an Excel file using openpyxl.

### 22 Export Columns

| # | Column |
|---|--------|
| 1 | Title |
| 2 | Severity |
| 3 | Risk Score |
| 4 | Confidence |
| 5 | Source |
| 6 | Source URL |
| 7 | Feed Type |
| 8 | Asset Type |
| 9 | TLP |
| 10 | CVE IDs |
| 11 | Affected Products |
| 12 | Tags |
| 13 | Geo |
| 14 | Industries |
| 15 | KEV |
| 16 | Exploit Available |
| 17 | IOC Count |
| 18 | AI Summary |
| 19 | Published At |
| 20 | Ingested At |
| 21 | Updated At |
| 22 | Source Ref |

### Excel Styling

- Header: `#1F4E79` background, white bold text
- Severity cell coloring per row:
  - Critical → red fill, High → orange fill, Medium → yellow fill, Low → green fill, Info → blue fill
- Auto-width columns (max 50 chars per column)
- Freeze header row
- Auto-filter enabled

### IntelCard Component

Each `IntelCard` displays:
- **Risk tooltip:** 5-factor scoring description ("KEV, severity, reliability, freshness, prevalence")
- **AI indicator:** Purple `Cpu` icon when `ai_summary` present, plain text for `summary`
- **CVSS display:** Colored by exploitability score: `≥7` → red, `≥4` → yellow, else → green
- **Expanded metadata:** Published, Ingested, Source, Asset Type, TLP, Confidence, Reliability, Related IOCs, CVSS, Tags (first 3 + "+N"), Geo, Products (first 2 + "+N"), Source URL
- **Action URLs:**
  - Hunt: `/search?q={source_ref || cve_ids[0] || title}&hunt=1`
  - Investigate: `/investigate?id={id}&type=intel&depth=1`

---

## 10. Database Schema

See [THREAT-FEED.md](THREAT-FEED.md) §8 for `intel_items` table schema.

### `intel_ioc_links`

| Column | Type | Description |
|--------|------|-------------|
| `intel_id` | UUID | FK to intel_items |
| `intel_ingested_at` | TIMESTAMPTZ | Composite FK partner |
| `ioc_id` | UUID | FK to iocs |
| `relationship` | VARCHAR(50) | default 'associated' |
| `created_at` | TIMESTAMPTZ | |

---

## 11. Caching Strategy

| Endpoint | Cache TTL | Notes |
|----------|-----------|-------|
| `GET /intel` | 30s | Per filter combination |
| `GET /intel/stats` | 60s | Global stats |
| `GET /intel/{id}/enrichment` | 21600s (6h) | AI enrichment |
| `GET /intel/{id}/related` | 300s | Related items |
| `GET /intel/{id}/iocs` | 120s | Linked IOCs |

---

## 12. Constants & Thresholds Reference

### Filter Constants (Frontend)

| Constant | Values |
|----------|--------|
| `SEVERITY_OPTIONS` | critical, high, medium, low, info (5) |
| `FEED_TYPE_OPTIONS` | vulnerability, ioc, malware, exploit, advisory, threat_actor, campaign (7) |
| `ASSET_TYPE_OPTIONS` | cve, ip, url, domain, hash_sha256, hash_md5, email, file, other (9) |
| `SORT_OPTIONS` | Most Recent, Highest Risk, Published Date, Lowest Risk, Severity (5) |

### Polling

| Timer | Value |
|-------|-------|
| Auto-refresh | 30 seconds |

---

## 13. Intel List UI Layout

Layout of `intel/page.tsx` (~290 lines):

1. **Header** — Title + total count + Refresh/Export/Filters buttons
2. **Collapsible Filter Panel** — Search, Severity badges, Feed Type badges, Sort badges, Asset Type badges, KEV/Exploit quick toggles, Apply/Clear
3. **Active Filter Summary** — Shown when filter panel is closed
4. **Intel Card List** — `IntelCard` components (loading skeleton supported)
5. **Pagination** — Page navigation

---

## 14. Intel Detail UI Layout

Layout of `intel/[id]/page.tsx` (~1600 lines):

### Header
- Back button
- Title
- Severity/KEV/Exploit/TLP badges
- Source info and timestamps
- "Add to Report" action menu

### 6-Tab Navigation
- Overview | ATT&CK | Timeline | Remediation | Related Intel | IOCs

### Key Sub-Components
- `StructuredIntelCards` — Renders parsed AI enrichment data
- `EnhancedTimelineEvent` — Timeline entries with type-specific colors
- `IOCDetailRow` — Expandable IOC row with enrichment panel
- `Row` — Reusable key-value display

---

## 15. Future Enhancements

- Inline AI enrichment without navigating to detail
- IOC extraction preview on hover
- Custom tags/labels per user
- Bookmark/watchlist for items
- Side-by-side comparison of related items
- Automated weekly digest of critical items
