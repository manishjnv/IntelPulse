# IntelWatch — Dashboard Module

> Complete technical reference for the Dashboard feature: KPI aggregation, threat insights, drill-down modals, polling, caching, and UI layout.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [Dashboard KPI Stats](#4-dashboard-kpi-stats)
5. [Threat Insights Engine](#5-threat-insights-engine)
6. [Insight Detail & Drill-Down](#6-insight-detail--drill-down)
7. [Executive Summaries](#7-executive-summaries)
8. [Feed Source Name Mapping](#8-feed-source-name-mapping)
9. [Database & Materialized Views](#9-database--materialized-views)
10. [Scheduling & Worker Tasks](#10-scheduling--worker-tasks)
11. [Caching Strategy](#11-caching-strategy)
12. [Constants & Thresholds Reference](#12-constants--thresholds-reference)
13. [Dashboard UI Layout](#13-dashboard-ui-layout)
14. [Status Bar (Header)](#14-status-bar-header)
15. [Future Enhancements](#15-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                        Scheduler                             │
│  refresh_materialized_views (every 2 min)                    │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL (TimescaleDB)                     │
│  intel_items │ iocs │ feed_sync_state │ reports │ cases      │
│  ───────────────────────────────────────────────────         │
│  mv_severity_distribution │ mv_top_risks (materialized)      │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Routes (/dashboard)                  │
│  /dashboard       │  /dashboard/insights                     │
│  /dashboard/insights/detail  │  /dashboard/insights/all      │
│  Cache: Redis (60s–300s)                                     │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    Next.js Frontend                           │
│  6 KPI stat cards │ Donuts │ Trend charts │ Ranked lists      │
│  Executive summaries │ Feed status │ Top risks table          │
│  InsightDetailModal │ ViewAllModal                            │
│  Polling: 60s (stats) │ 30s (unread) │ once (insights)       │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend route | `api/app/routes/dashboard.py` |
| Frontend page | `ui/src/app/(app)/dashboard/page.tsx` |
| StatCard | `ui/src/components/StatCard.tsx` |
| ThreatLevelBar | `ui/src/components/ThreatLevelBar.tsx` |
| DonutChart | `ui/src/components/DonutChart.tsx` |
| TrendLineChart | `ui/src/components/TrendLineChart.tsx` |
| RankedDataList | `ui/src/components/RankedDataList.tsx` |
| FeedStatusPanel | `ui/src/components/FeedStatusPanel.tsx` |
| InsightDetailModal | `ui/src/components/InsightDetailModal.tsx` |
| Zustand store | `ui/src/store/index.ts` |
| Types | `ui/src/types/index.ts` |

---

## 3. API Endpoints

### `GET /api/v1/dashboard`

Main KPI stats endpoint. Returns severity distribution, feed status, top risks.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | Auth: `require_viewer` |

**Cache:** 60 seconds (Redis)

**Response shape:**
```json
{
  "total_intel": 12500,
  "intel_24h": 340,
  "severity_distribution": {"critical": 120, "high": 450, ...},
  "feed_type_distribution": {"vulnerability": 5000, ...},
  "feed_status": [...],
  "top_risks": [...],
  "avg_risk_score": 42.5,
  "kev_count": 89,
  "exploit_count": 230,
  "sources": 12,
  "ai_enriched": 8500
}
```

### `GET /api/v1/dashboard/insights`

Comprehensive threat landscape aggregations. Heavy query, cached longer.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | Auth: `require_viewer` |

**Cache:** 300 seconds (Redis)

**Aggregation sections:**

| Section | Description | Limits |
|---------|-------------|--------|
| `trending_products` | Affected products by period | 7d / 30d / 90d / 1y |
| `threat_actors` | Extracted from titles/summaries | 47 regex patterns |
| `ransomware` | Ransomware group mentions | 23 known groups |
| `malware_families` | Malware family mentions | 65+ patterns |
| `exploit_summary` | EPSS metrics and exploit stats | — |
| `top_cves` | Most referenced CVEs | Max 12 |
| `executive_summaries` | Per feed-type summaries | 4 feed types |
| `threat_geography` | Country-level threat data | Top 15 |
| `target_industries` | Industry targeting | Top 15 |
| `attack_techniques` | ATT&CK technique mentions | 28 patterns |
| `ingestion_trend` | Daily ingestion for 30 days | 30 data points |

### `GET /api/v1/dashboard/insights/detail`

Entity drill-down for a specific insight item.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | required | `product` \| `threat_actor` \| `ransomware` \| `malware` \| `cve` |
| `name` | string | required | Entity name to drill into |

### `GET /api/v1/dashboard/insights/all`

All entities for a given type (expanded view).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `type` | string | required | Entity type |

**Returns:** Up to 50 entities.

---

## 4. Dashboard KPI Stats

The main `/dashboard` endpoint returns these KPI fields:

| KPI | Source Query | Display |
|-----|-------------|---------|
| Total Intel | `COUNT(*)` from `intel_items` | StatCard (default) |
| Last 24h | `COUNT(*) WHERE ingested_at >= now()-24h` | StatCard (danger if >500) |
| Avg Risk Score | `AVG(risk_score)` | StatCard with risk color |
| KEV Listed | `COUNT(*) WHERE is_kev = TRUE` | StatCard (warning) |
| Reports | From report stats | StatCard |
| Unread Alerts | Notification unread count | StatCard |

**StatCard variants:** `default`, `danger`, `warning`, `success`.

---

## 5. Threat Insights Engine

The `/dashboard/insights` endpoint performs multiple aggregation queries:

### Threat Actor Extraction

Scans `title`, `summary`, `description` fields using 47 regex patterns including:
- APT groups: APT28, APT29, Lazarus, Fancy Bear, Cozy Bear, etc.
- Cybercrime groups: FIN7, FIN8, Scattered Spider, etc.
- Nation-state actors: Sandworm, Turla, Kimsuky, etc.

### Ransomware Group Detection

23 known ransomware groups monitored:
- LockBit, BlackCat/ALPHV, Cl0p, Play, Royal, Black Basta, Akira, Medusa, etc.

### Malware Family Matching

65+ malware family patterns covering:
- RATs: Cobalt Strike, AsyncRAT, Remcos, NjRAT, QuasarRAT
- Stealers: RedLine, Raccoon, Vidar, Lumma, FormBook
- Loaders: QakBot, Emotet, IcedID, BumbleBee, SocGholish
- Banking: TrickBot, Dridex, Zeus/Zloader, Ursnif

### Product Period Filtering

`trending_products` supports 4 time windows:
- **7d** — Last 7 days (default)
- **30d** — Last 30 days
- **90d** — Last 90 days
- **1y** — Last year

---

## 6. Insight Detail & Drill-Down

**`InsightDetailModal`** — Opens when clicking on a product, threat actor, ransomware group, or malware family.

| Property | Description |
|----------|-------------|
| `detailType` | `product` \| `threat_actor` \| `ransomware` \| `malware` \| `cve` |
| `detailName` | Entity name clicked |

The modal calls `GET /dashboard/insights/detail?type={type}&name={name}` and displays:
- **4 Summary Cards:** Total Intel, Avg Risk, Exploits, CVEs
- Related intel items with severity and risk score
- Severity distribution bar with color coding
- CVE badges (each links to `/search?q={cve}`)
- AI-synthesized `StructuredIntelCards` (key findings built from summary stats)
- Risk color thresholds: `≥70` → red, `≥40` → orange, else → green
- Close mechanics: ESC key, backdrop click, X button
- Max height: `max-h-[90vh]` with scroll

**`ViewAllModal`** — "See All" button shows up to 50 entities for a given type.
- Displays: risk score, item count, up to 3 CVEs, 2 industries, 2 regions per entity
- Max height: `max-h-[85vh]`
- Click on entity opens `InsightDetailModal` for drill-down

---

## 7. Executive Summaries

The insights endpoint generates executive summaries for 4 intel feed types:

| Feed Type | Description | Metrics |
|-----------|-------------|---------|
| `threat_actor` | Threat actor landscape | total, recent_7d, avg_risk, severity breakdown, top items |
| `campaign` | Active campaigns | total, recent_7d, avg_risk, severity breakdown, top items |
| `exploit` | Exploit activity | total, recent_7d, avg_risk, severity breakdown, top items |
| `advisory` | Security advisories | total, recent_7d, avg_risk, severity breakdown, top items |

Each summary card shows:
- Total count and recent 7-day count
- Average risk score
- Mini severity distribution bar
- Top 5 items list

---

## 8. Feed Source Name Mapping

Hardcoded mapping from `feed_name` to display `source_name`:

| Feed Name | Source Display Name |
|-----------|-------------------|
| `nvd` | NVD |
| `cisa_kev` | CISA KEV |
| `urlhaus` | URLhaus |
| `abuseipdb` | AbuseIPDB |
| `otx` | OTX |
| `virustotal` | VirusTotal |
| `shodan` | Shodan |
| `threatfox` | ThreatFox |
| `malwarebazaar` | MalwareBazaar |

---

## 9. Database & Materialized Views

### Materialized Views

Two materialized views power fast dashboard loading:

#### `mv_severity_distribution`
```sql
SELECT severity, feed_type, COUNT(*) as count, AVG(risk_score) as avg_risk_score
FROM intel_items
WHERE ingested_at > NOW() - INTERVAL '30 days'
GROUP BY severity, feed_type;
```

#### `mv_top_risks`
```sql
SELECT id, ingested_at, title, severity, risk_score, source_name, feed_type,
       asset_type, cve_ids, is_kev, tags, published_at
FROM intel_items
WHERE risk_score >= 70
ORDER BY risk_score DESC, ingested_at DESC
LIMIT 100;
```

### Refresh Function
```sql
CREATE OR REPLACE FUNCTION refresh_dashboard_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_severity_distribution;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_top_risks;
END;
$$ LANGUAGE plpgsql;
```

---

## 10. Scheduling & Worker Tasks

| Task | Interval | Queue | Description |
|------|----------|-------|-------------|
| `refresh_materialized_views` | Every 2 minutes | `low` | Refreshes `mv_severity_distribution` and `mv_top_risks` |

---

## 11. Caching Strategy

| Endpoint | Cache TTL | Key Pattern |
|----------|-----------|-------------|
| `GET /dashboard` | 60 seconds | `dashboard_v1` |
| `GET /dashboard/insights` | 300 seconds | `dashboard_insights_v1` |
| `GET /status/bar` | 60 seconds | `status_bar_v3` |

All caching uses Redis via `get_cached` / `set_cached` helpers.

---

## 12. Constants & Thresholds Reference

### Severity Colors (Frontend)

| Severity | Hex Color |
|----------|-----------|
| `critical` | `#ef4444` |
| `high` | `#f97316` |
| `medium` | `#eab308` |
| `low` | `#22c55e` |
| `info` | `#3b82f6` |
| `unknown` | `#6b7280` |

### Feed Type Colors (Frontend)

| Feed Type | Hex Color |
|-----------|-----------|
| `vulnerability` | `#ef4444` |
| `ioc` | `#f97316` |
| `malware` | `#a855f7` |
| `exploit` | `#ec4899` |
| `advisory` | `#3b82f6` |
| `threat_actor` | `#14b8a6` |
| `campaign` | `#8b5cf6` |

### Risk Score Background Colors

| Threshold | Color Class |
|-----------|------------|
| `score >= 80` | Red background |
| `score >= 60` | Orange background |
| `score >= 40` | Yellow background |
| `score < 40` | Green background |

### Polling Intervals

| Data | Interval |
|------|----------|
| Dashboard stats | 60 seconds |
| Unread notification count | 30 seconds |
| Insights | Once on mount |

### Chart Dimensions

| Chart | Configuration |
|-------|--------------|
| DonutChart | Inner radius: 55, Outer radius: 80 |
| TrendLineChart | Height: 250px |
| RankedDataList | Max items: 10 |

---

## 13. Dashboard UI Layout

Top-to-bottom layout of `dashboard/page.tsx` (~1000 lines):

1. **Header Bar** — Page title + loading spinner
2. **KPI Stats Row** (6 columns) — Total Intel, Last 24h, Avg Risk, KEV Listed, Reports, Alerts
3. **Threat Level Bar** — High/Medium/Low aggregation visualization
4. **Two Donuts** (side by side) — Severity Breakdown + Intel by Category (Feed Type)
5. **Ingestion Trend** — 30-day line chart with exploit % and KEV % header stats
6. **Executive Summaries** — 2×2 grid: threat_actor, campaign, exploit, advisory cards (each shows total/recent_7d/avg_risk, severity mini-bar, top items)
7. **Most Impacted Products** — Period toggle (7d/30d/90d/1y), clickable product grid
8. **Threat Actors & Ransomware** — Side-by-side InsightRow components
9. **Malware, Infostealers & Botnets** — Grid layout
10. **Three-Column Grid** — Top Sources (RankedDataList) + Top CVEs (with KEV/Exploit/risk badges) + Feed Connectors (FeedStatusPanel)
11. **Highest Risk Items** — Table with Risk, Severity, Title, Source, Type, CVEs, KEV columns
12. **Modals** — InsightDetailModal + ViewAllModal for drill-down

**Helper components:** `EmptyState`, `RankedBarList`, `InsightRow`.

---

## 14. Status Bar (Header)

A lightweight global header bar providing real-time platform health.

### Endpoint: `GET /status/bar`

**Cache:** 60 seconds

**Response fields:**

| Field | Type | Source |
|-------|------|--------|
| `status` | `ok` \| `degraded` | Health check result |
| `postgres` | boolean | `SELECT 1` test |
| `redis` | boolean | `ping()` test |
| `opensearch` | boolean | `ping()` test |
| `total_intel` | int | `COUNT(*)` from `intel_items` |
| `intel_24h` | int | Ingested in last 24 hours |
| `critical_count` | int | Severity = critical |
| `high_count` | int | Severity = high |
| `active_feeds` | int | Status IN (success, running) |
| `total_feeds` | int | All feed rows |
| `last_feed_at` | ISO string | `MAX(last_success)` |
| `avg_risk_score` | float | `AVG(risk_score)` |
| `kev_count` | int | `COUNT(*) WHERE is_kev` |
| `attack_coverage_pct` | float | % of parent techniques with intel links |
| `attack_coverage_prev_pct` | float | Coverage 7 days ago (trend arrow) |
| `searches_today` | int | Audit log `action='search'` today |
| `sparkline` | int[24] | Hourly ingestion counts for last 24h |

### Status Bar UI Segments (HeaderStatusBar Component)

The `HeaderStatusBar` component renders 9 data segments with a 30-second polling interval:

1. **Health** — Postgres/Redis/OpenSearch individual status (tooltip on hover)
2. **Threat Level** — Label derived from `avg_risk_score`:
   - `≥75` → Critical (red), `≥55` → High (orange), `≥35` → Medium (yellow), `<35` → Low (green)
3. **Total Intel** — Total item count
4. **Critical/High** — Combined critical + high count (only if > 0)
5. **KEV** — KEV count badge (only if > 0)
6. **Sparkline** — SVG 24-hour ingestion mini-chart (MiniSparkline sub-component)
7. **Last Feed** — Relative timestamp of most recent feed sync
8. **ATT&CK Coverage** — Percentage with trend delta (TrendingUp/Down/Minus comparing current vs 7-day prior)
9. **Searches Today** — Count from audit log (only if > 0)

**Degraded state:** Shows "Degraded" when `status !== "ok"` OR `active_feeds === 0`.

### AI Summary Generation (Worker)

**Prompt A — Default Intel Summary**

- **Location:** `api/app/services/ai.py`
- **Trigger:** Scheduler every 5 min, batch of 5 items without `ai_summary`
- **Config:** `max_tokens=300`, `temperature=0.3`

**System prompt:**
```
You are a cybersecurity threat intelligence analyst. Provide a concise 2-3
sentence summary of the following threat intelligence item. Focus on impact,
affected systems, and recommended actions. Be direct and technical.
```

**User prompt format:**
```
Title: {title}
Severity: {severity}
Description: {description[:1000]}
Source: {source_name}
CVE IDs: {cve_ids[:5]}
```

### AI Fallback Provider Chain

| Priority | Provider | Model | Timeout |
|----------|----------|-------|---------|
| 1 | `groq-primary` | `llama-3.3-70b-versatile` (configurable) | 30s |
| 2 | `groq-llama3.1-8b` | `llama-3.1-8b-instant` | 30s |
| 3 | `cerebras` | `llama3.1-8b` | 60s |
| 4 | `groq-qwen3` | `qwen/qwen3-32b` | 30s |
| 5 | `huggingface` | `mistralai/Mistral-7B-Instruct-v0.3` | 60s |

Fallback triggers: HTTP 429, 503, 403.

---

## 15. Future Enhancements

- Real-time WebSocket push for dashboard updates
- Custom dashboard layouts per user
- Alert threshold configuration for KPI cards
- Trend comparison (week over week, month over month)
- PDF export of dashboard snapshot
- Custom date range selection for insights
