# IntelPulse — Threat Feed Module

> Complete technical reference for the Threat Feed page: unified intel browsing with filters, real-time freshness indicators, quick stats, and rich item cards.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints Used](#3-api-endpoints-used)
4. [Feed Ingestion Pipeline](#4-feed-ingestion-pipeline)
5. [Feed Sources & Schedule](#5-feed-sources--schedule)
6. [Risk Scoring Engine](#6-risk-scoring-engine)
7. [Deduplication Logic](#7-deduplication-logic)
8. [Database Schema](#8-database-schema)
9. [Caching Strategy](#9-caching-strategy)
10. [Constants & Thresholds Reference](#10-constants--thresholds-reference)
11. [Threat Feed UI Layout](#11-threat-feed-ui-layout)
12. [Future Enhancements](#12-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                         Scheduler                            │
│  12 feed connectors on independent schedules (15m → 24h)     │
└──────────────────────────┬───────────────────────────────────┘
                           │ RQ Jobs
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                     Worker Pipeline                           │
│  Fetch → Normalize → Score → Store (PostgreSQL) → Index (OS) │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                   FastAPI Routes (/intel)                     │
│  List (paginated) │ Stats │ Detail │ Enrichment │ Related    │
│  Cache: Redis (30s–300s)                                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               Next.js Threats Page (/threats)                 │
│  Quick stats bar │ Search + 6 filters │ Severity pills       │
│  Feed type pills │ Rich item cards │ Right sidebar analytics  │
│  Stale indicator (120s) │ Auto-refresh stats (60s)           │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend intel routes | `api/app/routes/intel.py` |
| Backend scoring | `api/app/services/scoring.py` |
| Worker tasks | `worker/tasks.py` |
| Scheduler | `worker/scheduler.py` |
| Feed connectors | `api/app/services/feeds/` |
| Frontend page | `ui/src/app/(app)/threats/page.tsx` |
| DonutChart | `ui/src/components/DonutChart.tsx` |
| Pagination | `ui/src/components/Pagination.tsx` |

---

## 3. API Endpoints Used

The Threats page consumes the Intel endpoints — see [INTEL-ITEMS.md](INTEL-ITEMS.md) for full endpoint docs. Key endpoints:

| Endpoint | Purpose | Cache |
|----------|---------|-------|
| `GET /api/v1/intel` | Paginated list with 12 filters | 30s |
| `GET /api/v1/intel/stats` | Quick stats bar data | 60s |

---

## 4. Feed Ingestion Pipeline

Each feed follows the same 5-step pipeline in `worker/tasks.py`:

```
1. Fetch        → connector.fetch_with_retry(last_cursor)
2. Normalize    → connector.normalize(raw_items)
3. Score        → batch_score(normalized)
4. Store        → _bulk_store(session, scored)  [PostgreSQL with dedup]
5. Index        → bulk_index_items(os_docs)     [OpenSearch]
```

**State tracking:** Each feed has a `feed_sync_state` row recording `status`, `last_cursor`, `items_fetched`, `items_stored`, `error_message`.

---

## 5. Feed Sources & Schedule

12 feed connectors with independent polling intervals:

| Feed | Interval | Queue | API Key Required |
|------|----------|-------|-----------------|
| NVD | 15 min | `default` | Optional (higher rate with key) |
| AbuseIPDB | 15 min | `default` | Yes |
| URLhaus | 30 min | `high` | No |
| OTX (AlienVault) | 30 min | `low` | Yes |
| ThreatFox | 30 min | `high` | No |
| MalwareBazaar | 30 min | `default` | No |
| CISA KEV | 60 min | `high` | No |
| VirusTotal | 60 min | `default` | Yes (free: 500 req/day) |
| Exploit-DB | 6 hours | `default` | No (RSS) |
| CISA Advisories | 6 hours | `default` | No (RSS) |
| Shodan | 12 hours | `low` | Yes (free: ~100 credits/month) |
| MITRE ATT&CK | 24 hours | `low` | No (GitHub raw JSON) |

**Total scheduled jobs:** 26 (12 feeds + 14 maintenance tasks)

**Self-healing watchdog:** Background thread checks every 120 seconds that all 26 jobs exist in Redis. Re-registers if any are missing (survives Redis flushes).

---

## 6. Risk Scoring Engine

Located in `api/app/services/scoring.py`.

### Default Weights

| Factor | Weight | Description |
|--------|--------|-------------|
| `kev_presence` | 25 | CISA Known Exploited Vulnerability |
| `severity` | 25 | Vendor-assigned severity |
| `source_reliability` | 15 | Source trust score (0–100) |
| `freshness` | 20 | Time since publication |
| `ioc_prevalence` | 15 | Number of associated IOCs |

### Severity Scores

| Severity | Score |
|----------|-------|
| `critical` | 100 |
| `high` | 80 |
| `medium` | 50 |
| `low` | 25 |
| `info` | 10 |
| `unknown` | 0 |

### Freshness Decay

| Age | Multiplier |
|-----|-----------|
| ≤ 1 day | 1.0 |
| ≤ 7 days | 0.9 |
| ≤ 30 days | 0.7 |
| ≤ 90 days | 0.4 |
| > 90 days | 0.1 |
| Unknown date | 0.3 |

### Factor Computation

| Factor | Formula |
|--------|--------|
| KEV presence | `1.0 if is_kev else 0` (binary) |
| Severity | `SEVERITY_SCORES[severity] / 100.0` (0–1 range) |
| Source reliability | `source_reliability / 100.0` (default raw = 50) |
| IOC prevalence | `min(ioc_count / 50.0, 1.0)` (capped at 50 IOCs) |
| Freshness | Decay table above |

### Score Computation

```
score = sum(weight[factor] × factor_value for each factor)
final = (score / total_weight) × 100.0
```

### Post-Normalization Boosts

| Condition | Bonus | Cap |
|-----------|-------|-----|
| `exploit_available = true` | +10 | 100 |
| `exploitability_score ≥ 9.0` | +5 | 100 |

Boosts are applied after normalization, each independently capped at 100.

---

## 7. Deduplication Logic

Uses `source_hash` (SHA-256 of source URL + title) with a UNIQUE index on the `intel_items` table. PostgreSQL `ON CONFLICT DO NOTHING` prevents duplicate inserts.

---

## 8. Database Schema

### `intel_items` (TimescaleDB hypertable)

| Column | Type | Constraints |
|--------|------|------------|
| `id` | UUID | PK (composite with `ingested_at`) |
| `title` | TEXT | NOT NULL |
| `summary` | TEXT | |
| `description` | TEXT | |
| `published_at` | TIMESTAMPTZ | |
| `ingested_at` | TIMESTAMPTZ | NOT NULL, partition key |
| `severity` | severity_level | ENUM |
| `risk_score` | SMALLINT | 0–100 |
| `confidence` | SMALLINT | 0–100, default 50 |
| `source_name` | VARCHAR(100) | NOT NULL |
| `source_url` | TEXT | |
| `source_reliability` | SMALLINT | 0–100, default 50 |
| `source_ref` | VARCHAR(500) | |
| `feed_type` | feed_type | ENUM |
| `asset_type` | asset_type | ENUM, default `other` |
| `tlp` | tlp_level | ENUM, default `TLP:CLEAR` |
| `tags` | TEXT[] | GIN indexed |
| `geo` | TEXT[] | GIN indexed |
| `industries` | TEXT[] | |
| `cve_ids` | TEXT[] | GIN indexed |
| `affected_products` | TEXT[] | |
| `related_ioc_count` | INT | default 0 |
| `is_kev` | BOOLEAN | default FALSE |
| `exploit_available` | BOOLEAN | default FALSE |
| `exploitability_score` | REAL | |
| `ai_summary` | TEXT | |
| `ai_summary_at` | TIMESTAMPTZ | |
| `source_hash` | VARCHAR(64) | Dedup key |

### `feed_sync_state`

| Column | Type | Description |
|--------|------|-------------|
| `feed_name` | VARCHAR(100) | PK |
| `last_run` | TIMESTAMPTZ | |
| `last_success` | TIMESTAMPTZ | |
| `last_cursor` | TEXT | Feed-specific cursor |
| `status` | sync_status | idle/running/success/failed |
| `items_fetched` | INT | |
| `items_stored` | INT | |
| `error_message` | TEXT | |
| `run_count` | INT | |

---

## 9. Caching Strategy

| Endpoint | Cache TTL | Key |
|----------|-----------|-----|
| `GET /intel` | 30 seconds | `intel_list_{hash}` |
| `GET /intel/stats` | 60 seconds | `intel_stats_v1` |

---

## 10. Constants & Thresholds Reference

### Severity Colors (Frontend)

| Severity | Hex |
|----------|-----|
| `critical` | `#ef4444` |
| `high` | `#f97316` |
| `medium` | `#eab308` |
| `low` | `#22c55e` |
| `info` | `#3b82f6` |
| `unknown` | `#6b7280` |

### TLP Colors

| Level | Color |
|-------|-------|
| `TLP:RED` | Red |
| `TLP:AMBER` | Amber |
| `TLP:GREEN` | Green |
| `TLP:CLEAR` | Slate |
| `TLP:WHITE` | Slate |

### Freshness Indicators

| Threshold | Label | Color |
|-----------|-------|-------|
| < 2 hours | Live | Green dot |
| < 24 hours | Recent | Blue dot |
| < 168 hours (1 week) | This Week | Yellow dot |
| > 168 hours | Older | Gray dot |

**`isNewItem`:** Items ingested within the last 2 hours are marked with a "NEW" badge.

### Sort Options

| Key | Label |
|-----|-------|
| `ingested_at` | Most Recent |
| `risk_score` | Highest Risk |
| `published_at` | Published Date |
| `risk_score_asc` | Lowest Risk |
| `severity` | Severity |

### Polling & Stale Detection

| Timer | Value |
|-------|-------|
| Stale indicator | 120 seconds |
| Stats refresh | 60 seconds |

---

## 11. Threat Feed UI Layout

Layout of `threats/page.tsx` (~870 lines):

### Header
- Title + loading indicator

### Quick Stats Bar (`QuickStatsBar`)
9 stat items: Total, Today, Critical, High, KEV, Exploits, Avg Risk, AI Enriched, Sources

### Filters
- Search input (debounced)
- Severity pill buttons (5 levels)
- Feed type pill buttons (7 types)
- Sort dropdown (5 options)
- KEV Only / Exploit Only toggle buttons

### Main Content (3/4 + 1/4 grid)

**Left Column — Item List:**
Each card displays:
- Risk score badge with color
- Freshness indicator dot
- Title (linked to detail)
- Severity / KEV / Exploit / TLP badges
- AI summary preview (truncated)
- CVE IDs, affected products, geo, industries, tags
- Action buttons: Hunt, Investigate, AI Enrich

**Right Sidebar:**
- Severity breakdown (`SeverityMiniBar`)
- Asset Types donut (clickable segments)
- Feed Type grid
- Top Sources list
- Top CVEs list
- Trending Tags

---

## 12. Future Enhancements

- Real-time WebSocket push for new high-severity items
- Saved filter views (bookmarkable)
- Customizable column display
- Inline AI enrichment preview
- Bulk export with selected filters
- Feed quality scoring and auto-weight adjustment
