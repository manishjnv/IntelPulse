# IntelWatch — IOC Database Module

> Complete technical reference for the IOC Database: extraction, enrichment pipelines, risk scoring, sortable browsable table, and enrichment slide-over panel.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [Database Schema](#3-database-schema)
4. [API Endpoints](#4-api-endpoints)
5. [IOC Extraction Pipeline](#5-ioc-extraction-pipeline)
6. [Enrichment Pipelines](#6-enrichment-pipelines)
7. [Worker Scheduled Tasks](#7-worker-scheduled-tasks)
8. [Risk Scoring](#8-risk-scoring)
9. [Constants & Reference Tables](#9-constants--reference-tables)
10. [IOC Database UI Layout](#10-ioc-database-ui-layout)
11. [Enrichment Slide-Over Panel](#11-enrichment-slide-over-panel)
12. [Hot IOCs Strip](#12-hot-iocs-strip)
13. [Caching & Performance](#13-caching--performance)
14. [Future Enhancements](#14-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                  Intel Item Ingestion                         │
│  Worker extracts IOCs from intel items → iocs table           │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐  ┌────────────────────────────────────┐
│  IOC Extraction       │  │      Enrichment Pipelines          │
│  Regex-based IOC      │  │  IPinfo → geolocation, ASN, org   │
│  detection from       │  │  InternetDB → ports, vulns, tags  │
│  intel item text      │  │  EPSS → exploit probability       │
│                       │  │  VirusTotal → reputation           │
│                       │  │  Shodan → service details           │
└──────────┬──────────┘  └──────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    PostgreSQL — iocs table                    │
│  type │ value │ risk_score │ enrichment_data (JSONB)          │
│  first_seen │ last_seen │ source_count │ is_kev               │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js IOC Database Page                    │
│  Sortable table │ Filter bar │ Risk gauge │ Hot IOCs strip    │
│  Enrichment slide-over │ Excel export                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend IOC routes | `api/app/routes/iocs.py` |
| Enrichment service | `api/app/services/enrichment.py` |
| Worker tasks (extraction + enrichment) | `worker/tasks.py` |
| Scheduler (job intervals) | `worker/scheduler.py` |
| Database schema | `db/schema.sql` |
| IPinfo migration | `db/migrations/006_ipinfo_enrichment.sql` |
| Frontend IOC Database page | `ui/src/app/(app)/iocs/page.tsx` |

---

## 3. Database Schema

### `iocs` table

```sql
CREATE TABLE iocs (
    id              SERIAL PRIMARY KEY,
    type            VARCHAR(50)    NOT NULL,
    value           TEXT           NOT NULL UNIQUE,
    risk_score      NUMERIC(5,2)  DEFAULT 0,
    first_seen      TIMESTAMPTZ   DEFAULT NOW(),
    last_seen       TIMESTAMPTZ   DEFAULT NOW(),
    source_count    INTEGER       DEFAULT 1,
    is_kev          BOOLEAN       DEFAULT FALSE,
    enrichment_data JSONB         DEFAULT '{}',
    created_at      TIMESTAMPTZ   DEFAULT NOW(),
    updated_at      TIMESTAMPTZ   DEFAULT NOW(),
    -- IPinfo Lite enrichment columns (migration 006)
    asn             VARCHAR(20),
    as_name         VARCHAR(200),
    as_domain       VARCHAR(200),
    country_code    VARCHAR(5),
    country         VARCHAR(100),
    continent_code  VARCHAR(5),
    continent       VARCHAR(50),
    enriched_at     TIMESTAMPTZ
);
```

### IPinfo Enrichment Indexes

```sql
CREATE INDEX idx_iocs_country_code ON iocs(country_code) WHERE country_code IS NOT NULL;
CREATE INDEX idx_iocs_asn          ON iocs(asn)          WHERE asn IS NOT NULL;
CREATE INDEX idx_iocs_enriched_at  ON iocs(enriched_at)  WHERE enriched_at IS NULL;
```

### `intel_ioc_links` table

```sql
CREATE TABLE intel_ioc_links (
    id            SERIAL PRIMARY KEY,
    intel_item_id INTEGER REFERENCES intel_items(id),
    ioc_id        INTEGER REFERENCES iocs(id),
    context       TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(intel_item_id, ioc_id)
);
```

### Indexes
- `idx_iocs_type` — B-tree on `type`
- `idx_iocs_value` — B-tree on `value`
- `idx_iocs_risk_score` — B-tree on `risk_score`

---

## 4. API Endpoints

### `GET /api/v1/iocs`

Paginated IOC listing with filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `page_size` | int | 50 | Items per page |
| `type` | string | — | Filter by IOC type |
| `search` | string | — | Text search on value |
| `sort_by` | string | risk_score | Sort field |
| `sort_order` | string | desc | asc / desc |
| `min_risk` | float | — | Minimum risk score |
| `max_risk` | float | — | Maximum risk score |
| `country_code` | string | — | Filter by country code (uppercased) |
| `asn` | string | — | Filter by ASN (uppercased) |

### `GET /api/v1/iocs/{id}`

Single IOC with full enrichment data.

### `GET /api/v1/iocs/stats`

Aggregation stats for the IOC database.

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `total_iocs` | int | Total IOC count |
| `type_distribution` | object | Count per IOC type |
| `risk_distribution` | object | `{critical, high, medium, low}` bucket counts |
| `source_distribution` | object | Count per source |
| `unique_sources` | int | Distinct source count |
| `avg_risk_score` | float | Rounded to 1 decimal |
| `recent_24h` | int | IOCs added in last 24 hours |
| `high_risk_count` | int | Critical + high risk count |
| `top_risky` | array | Top highest-risk IOCs |
| `tag_distribution` | object | Count per tag |
| `geo_distribution` | object | Geographic breakdown |
| `country_distribution` | array | Top countries `[{name, code, count}]` |
| `asn_distribution` | array | Top ASNs `[{asn, name, count}]` |
| `continent_distribution` | array | `[{name, code, count}]` |
| `enrichment_coverage` | object | `{enriched, total_ips}` |

### `GET /api/v1/iocs/enrich`

On-demand enrichment of a single IOC via VirusTotal + Shodan.

| Parameter | Type | Description |
|-----------|------|-------------|
| `value` | string | IOC value (required, max 2000) |
| `ioc_type` | string | IOC type (required, max 30) |

### `POST /api/v1/iocs/{id}/enrich`

Trigger on-demand enrichment for a stored IOC.

---

## 5. IOC Extraction Pipeline

### Scheduled Task: `extract_iocs`
- **Interval:** Every 10 minutes
- **Logic:** Scans recently ingested intel items, extracts IOC patterns using regex
- **Types extracted:** IPv4, domains, URLs, MD5, SHA1, SHA256, emails, CVEs
- **Deduplication:** UPSERTs on `value` — increments `source_count` and updates `last_seen`

### Extraction Flow

1. Query intel items ingested since last extraction run
2. For each item, scan `title`, `description`, `summary` fields
3. Apply regex patterns (same 8 patterns as IOC Search auto-detection)
4. Create IOC records with initial risk_score from parent intel item
5. Create `intel_ioc_links` entries to track provenance

---

## 6. Enrichment Pipelines

### IPinfo Enrichment
- **Source:** IPinfo API
- **Data stored as columns:** `asn`, `as_name`, `as_domain`, `country_code`, `country`, `continent_code`, `continent`, `enriched_at`
- **Continent mapping:** Uses `_CC_CONTINENT` lookup from country code
- **Country name:** Uses `_CC_NAMES` lookup or IPinfo `country_name` field
- **Applies to:** IP-type IOCs
- **Additional JSONB:** `enrichment_data.ipinfo` for region, city, lat/long, VPN/proxy/tor/hosting flags

### InternetDB Enrichment (Shodan)
- **Source:** Shodan InternetDB (free, no API key)
- **Data:** Open ports, known CVEs, hostnames, tags (e.g., "self-signed", "eol-product")
- **Applies to:** IP-type IOCs
- **Stored in:** `enrichment_data.internetdb`

### EPSS Enrichment
- **Source:** FIRST EPSS API
- **Data:** EPSS score (probability of exploitation in 30 days), percentile
- **Applies to:** CVE-type IOCs
- **Stored in:** `enrichment_data.epss`

### VirusTotal Enrichment
- **Source:** VirusTotal API v3
- **Data:** Detection ratio, reputation score, community votes
- **Applies to:** IP, domain, URL, hash IOCs
- **Stored in:** `enrichment_data.virustotal`

---

## 7. Worker Scheduled Tasks

| Task | Interval | Description |
|------|----------|-------------|
| `extract_iocs` | 10 min | Extract IOCs from new intel items |
| `enrich_ips_ipinfo` | 10 min | IPinfo geolocation for IP IOCs |
| `enrich_ips_internetdb` | 10 min | Shodan InternetDB for IP IOCs |
| `enrich_epss_scores` | 24 hours | EPSS scores for CVE IOCs |

All enrichment jobs process IOCs in batches to avoid API rate limits.

---

## 8. Risk Scoring

### Risk Buckets

| Bucket | Score Range | Used In |
|--------|------------|--------|
| `critical` | 80–100 | Stats API, frontend coloring |
| `high` | 60–79 | Stats API, frontend coloring |
| `medium` | 40–59 | Stats API, frontend coloring |
| `low` | 0–39 | Stats API, frontend coloring |

`high_risk_count` = critical + high counts.

### Scoring Factors

IOC risk scores derive from:

1. **Parent intel item risk score** — Initial seed from the highest-risk linked intel item
2. **Source count** — IOCs seen in multiple feeds score higher
3. **KEV status** — CISA KEV membership boosts score
4. **Enrichment signals:**
   - High EPSS score → boosts risk
   - VirusTotal detections → boosts risk
   - Tor/VPN network → boosts risk for IPs

Risk score range: 0.00 – 100.00

---

## 9. Constants & Reference Tables

### IOC Type Colors (Frontend)

11 IOC types with unique colors:

| Type | Color |
|------|-------|
| `ip` | Blue |
| `domain` | Purple |
| `url` | Cyan |
| `hash_md5` | Orange |
| `hash_sha1` | Amber |
| `hash_sha256` | Yellow |
| `email` | Pink |
| `cve` | Red |
| `file` | Green |
| `mutex` | Teal |
| `other` | Gray |

### Default Page Size

`pageSize = 50`

### Debounce

Search input debounce: **400ms**

### Sort Columns

10 sortable columns in the table:
- Type, Value, Risk Score, First Seen, Last Seen, Source Count, Is KEV, Country, ASN, Tags

---

## 10. IOC Database UI Layout

Layout of `iocs/page.tsx` (~1050 lines):

1. **Header** — "IOC Database" title + total count badge
2. **Hot IOCs Strip** — Horizontally scrolling strip of high-risk IOCs
3. **Filter Bar**:
   - Type filter dropdown
   - Search input (debounced 400ms)
   - Risk range slider
   - KEV toggle
4. **Stats Row** — Total IOCs, avg risk, KEV count, unique types
5. **Sortable Table** — 10 columns with click-to-sort headers
6. **Row Actions**:
   - View enrichment slide-over
   - Copy IOC value
   - Link to IOC Search
7. **Pagination** — Page controls with page size selector
8. **Enrichment Slide-Over** — Full enrichment details (see §11)

---

## 11. Enrichment Slide-Over Panel

When a user clicks an IOC row, a slide-over panel appears with:

### Risk Gauge
- **SVG half-arc gauge** rendering the risk score 0–100
- Color gradient: green (0–30) → yellow (30–60) → orange (60–80) → red (80–100)

### IOC Metadata
- Type, value, first seen, last seen
- Source count, KEV status
- Direct links to related intel items

### IPinfo Section (IP IOCs)
- Country flag + name
- City, region
- ASN + organization
- Map coordinates
- VPN/Proxy/Tor/Hosting flags

### InternetDB Section (IP IOCs)
- Open ports list (colored badges)
- Known CVEs
- Hostnames
- Tags (e.g., "self-signed", "eol-product")

### EPSS Section (CVE IOCs)
- EPSS score as percentage
- Percentile ranking
- Probability bar visualization

### VirusTotal Section
- Detection ratio (x/y engines)
- Reputation score
- Community votes (positive/negative)

### Actions
- Trigger manual re-enrichment
- Export enrichment data
- Link to full IOC Search live lookup

---

## 12. Hot IOCs Strip

A horizontally scrollable strip at the top of the IOC Database page showing the highest-risk IOCs:

- Displays top IOCs sorted by `risk_score DESC`
- Each card shows: IOC value (truncated), type badge, risk score, KEV indicator
- Click navigates to the enrichment panel
- Auto-refreshes with page data

---

## 13. Caching & Performance

| Aspect | Strategy |
|--------|----------|
| IOC listing | Direct SQL query, no cache (real-time) |
| Enrichment data | Stored in JSONB, queried with the IOC record |
| IPinfo API | Rate-limited batch processing |
| InternetDB | No API key required, generous limits |
| EPSS | Daily refresh, bulk API call |
| Frontend | Debounced search (400ms), optimistic UI |

### Batch Processing

Enrichment workers process IOCs in batches:
- IPinfo: up to 100 IPs per batch
- InternetDB: individual requests (no batch API)
- EPSS: bulk endpoint supports up to 1000 CVEs per request

---

## 14. Future Enhancements

- IOC aging / TTL-based archival
- IOC reputation history timeline
- Bulk IOC import (CSV/STIX)
- IOC tagging and classification
- IOC watchlists with notifications
- Historical enrichment comparison
- IOC relationship graph
- MISP format export
