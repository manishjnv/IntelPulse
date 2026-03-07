# IntelWatch — IOC Search Module

> Complete technical reference for the unified IOC Search: auto-detection, OpenSearch queries, live internet lookup, AI analysis, and result rendering.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Component File Map](#2-component-file-map)
3. [API Endpoints](#3-api-endpoints)
4. [IOC Auto-Detection](#4-ioc-auto-detection)
5. [OpenSearch Query Building](#5-opensearch-query-building)
6. [Search Aggregations](#6-search-aggregations)
7. [Live Internet Lookup](#7-live-internet-lookup)
8. [External Source Routing](#8-external-source-routing)
9. [AI Structured Analysis](#9-ai-structured-analysis)
10. [Caching Strategy](#10-caching-strategy)
11. [Constants & Thresholds Reference](#11-constants--thresholds-reference)
12. [IOC Search UI Layout](#12-ioc-search-ui-layout)
13. [Future Enhancements](#13-future-enhancements)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                   User Search Input                          │
│  Auto-detect IOC type → route to appropriate backend         │
└──────────────────────────┬───────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐  ┌────────────────────────────────────┐
│   OpenSearch Query   │  │      Live Internet Lookup          │
│  Full-text + type-   │  │  NVD │ AbuseIPDB │ VirusTotal     │
│  specific queries    │  │  Shodan │ URLhaus │ KEV │ OTX      │
│  Aggregations        │  │  AI Structured Analysis            │
│  PostgreSQL fallback │  │  Parallel execution (15s timeout)  │
└──────────┬──────────┘  └──────────────┬─────────────────────┘
           │                            │
           ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Routes (/search)                     │
│  POST /search │ GET /search/stats │ POST /search/live-lookup │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                  Next.js Search Page                          │
│  Auto-detect + debounce │ Filter pills │ Result table         │
│  Charts (donut + bar) │ Live lookup results                   │
│  AI StructuredIntelCards │ IOC enrichment panel               │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Component File Map

| Component | File |
|-----------|------|
| Backend search routes | `api/app/routes/search.py` |
| Search service | `api/app/services/search.py` |
| Live lookup service | `api/app/services/live_lookup.py` |
| Enrichment service | `api/app/services/enrichment.py` |
| Frontend search page | `ui/src/app/(app)/search/page.tsx` |
| StructuredIntelCards | `ui/src/components/StructuredIntelCards.tsx` |
| DonutChart | `ui/src/components/DonutChart.tsx` |
| HorizontalBarChart | `ui/src/components/HorizontalBarChart.tsx` |

---

## 3. API Endpoints

### `POST /api/v1/search`

Global IOC search with auto-detection.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | IOC value or keyword |
| `ioc_type` | string | Optional type override |
| `severity` | string | Filter by severity |
| `feed_type` | string | Filter by feed type |
| `sort_by` | string | Sort field |
| `sort_order` | string | asc / desc |
| `page` | int | Page number |
| `page_size` | int | Results per page |

### `GET /api/v1/search/stats`

Aggregation stats for populating the search UI filter sidebar.

### `POST /api/v1/search/live-lookup`

Live internet lookup against external sources.

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | IOC value |
| `ioc_type` | string | Optional type hint |

**Cache:** 600 seconds (10 minutes)

---

## 4. IOC Auto-Detection

Located in `api/app/services/search.py`. 8 regex patterns:

| Type | Pattern | Example |
|------|---------|---------|
| `cve` | `CVE-\d{4}-\d{4,7}` | CVE-2024-3094 |
| `ip` | IPv4 address regex | 8.8.8.8 |
| `domain` | Hostname-like pattern | evil.com |
| `url` | `https?://...` | https://malware.example.com/payload |
| `hash_md5` | 32 hex chars | d41d8cd98f00b204e9800998ecf8427e |
| `hash_sha1` | 40 hex chars | da39a3ee5e6b4b0d3255bfef95601890afd80709 |
| `hash_sha256` | 64 hex chars | e3b0c44298fc1c149afbf4c8996fb924... |
| `email` | Email pattern | actor@malware.org |

Detection is sequential — first match wins.

---

## 5. OpenSearch Query Building

The search service constructs type-specific queries:

### CVE Search
- Exact match on `cve_ids` field
- Plus full-text match on `title`, `description`, `ai_summary`

### IP / Domain / URL / Hash / Email
- Exact match on IOC value fields
- Related intel items through `intel_ioc_links` join
- Full-text search as fallback

### Keyword Search (no type detected)
- Multi-match on `title`, `summary`, `description`, `ai_summary`
- Boosted fields: title (3x), summary (2x), description (1x)

### Result Shape

Each result includes:
- Intel item data (title, severity, risk_score, source_name, etc.)
- Highlighted snippets (if available)
- Matched IOC type

---

## 6. Search Aggregations

The `/search/stats` endpoint returns:

| Aggregation | Description |
|-------------|-------------|
| `type_distribution` | IOC types in results |
| `severity_distribution` | Severity breakdown |
| `feed_distribution` | Feed types |
| `source_distribution` | Source names |
| `risk_stats` | Min, max, avg risk scores |
| `kev_count` | Number of KEV items |

---

## 7. Live Internet Lookup

Located in `api/app/services/live_lookup.py`.

### Process

1. Detect IOC type (auto or explicit)
2. Route to type-specific source list
3. Execute all source queries in **parallel** (asyncio.gather)
4. Collect results within 15-second timeout
5. Run AI structured analysis on aggregated results
6. Cache final response for 10 minutes

### Error Handling

- Per-source timeout: 15 seconds
- Per-source errors are captured but don't fail the overall lookup
- Result includes `sources_queried` and `errors` arrays

---

## 8. External Source Routing

| IOC Type | Sources Queried |
|----------|----------------|
| `cve` | NVD API + CISA KEV + Web Search |
| `ip` | AbuseIPDB + VirusTotal + Shodan InternetDB |
| `domain` | VirusTotal + Shodan DNS + Web Search |
| `hash_*` | VirusTotal |
| `url` | VirusTotal + URLhaus |
| `email` | Web Search |
| `keyword` | NVD + OTX + Web Search |

### Source Details

| Source | API | Timeout |
|--------|-----|---------|
| NVD | `services.nist.gov/rest/json/cves/2.0` | 15s |
| CISA KEV | Known Exploited Vulnerabilities catalog | 15s |
| AbuseIPDB | IP reputation check | 15s |
| VirusTotal | Multi-type lookups (IP/domain/URL/hash) | 15s |
| Shodan InternetDB | Open ports, CVEs, hostnames | 15s |
| URLhaus | URL/domain blacklist | 15s |
| OTX | AlienVault pulse search | 15s |

---

## 9. AI Structured Analysis

After live lookup sources return their results, the aggregated data is sent to the AI service for structured analysis.

### Invocation

Called via `_ai_analyze()` in `live_lookup.py`. Only runs if results are found AND `settings.ai_api_key` is set. **Does NOT use the 5-provider fallback chain** — makes a direct `httpx.AsyncClient` POST to `settings.ai_api_url`.

| Parameter | Value |
|-----------|-------|
| Model | `settings.ai_model` (fallback: `llama-3.3-70b-versatile`) |
| Temperature | 0.2 |
| Max tokens | 700 |
| HTTP timeout | 25 seconds |

### System Prompt (Prompt E)

```
You are an expert threat intelligence analyst. Analyze the given IOC lookup results
and produce a structured JSON analysis. Respond ONLY with valid JSON, no markdown,
no code blocks.

Required JSON structure:
{
  "summary": "2-4 sentence executive summary of what this IOC is and its risk level",
  "threat_actors": ["list of threat actors/groups associated, empty if none known"],
  "timeline": [{"date": "YYYY-MM-DD or description", "event": "what happened"}],
  "affected_products": ["vendor:product pairs or product names impacted"],
  "fix_remediation": "Specific recommended fix or remediation steps. Null if not applicable",
  "known_breaches": "Description of any known breaches or campaigns. Null if none",
  "key_findings": ["3-6 bullet point key findings, each a concise sentence"]
}

Rules: Be factual. Do not fabricate data. If information is not available, use empty
arrays or null. Keep it concise and actionable. Focus on what a SOC analyst needs to know.
```

### User Prompt

```
IOC: {query} (type: {ioc_type})

Live lookup results:
{context}
```

Context is built from up to 12 results with fields: source, title, description (truncated to 300 chars), CVE, CVSS, products, adversary, published, fix, ransomware, KEV, exploit.

### Response JSON Schema

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | 2-4 sentence executive summary |
| `threat_actors` | string[] | Associated threat actors/groups |
| `timeline` | array of `{date, event}` | Chronological events |
| `affected_products` | string[] | Vendor:product pairs |
| `fix_remediation` | string \| null | Remediation steps |
| `known_breaches` | string \| null | Known breach descriptions |
| `key_findings` | string[] | 3-6 concise bullet points |

Failure is silently caught — the response will simply omit the `ai_analysis` field.

---

## 9b. StructuredIntelCards Component

File: `ui/src/components/StructuredIntelCards.tsx`

Renders the AI analysis as visually styled cards.

### 7 Section Cards

| # | Section | Key | Color | Icon | Rendering |
|---|---------|-----|-------|------|-----------|
| 1 | AI Intelligence Summary | `summary` | purple | Sparkles | Full-width banner, paragraph text |
| 2 | Threat Actors | `threatActors` | orange | Crosshair | Grid card, Badge list |
| 3 | Affected Products | `affectedProducts` | cyan | Package | Grid card, Badge list |
| 4 | Known Breaches | `knownBreaches` | red | Skull | Grid card, paragraph text |
| 5 | Fix / Remediation | `fixRemediation` | emerald | Wrench | Grid card, paragraph text |
| 6 | Event Timeline | `timeline` | blue | Activity | Full-width, vertical line with date+event entries |
| 7 | Key Findings | `keyFindings` | amber | Lightbulb | Full-width, bulleted list |

### Variant: `full` vs `compact`

| Property | `full` (default) | `compact` |
|----------|-----|--------|
| Grid layout | `grid-cols-1 md:grid-cols-2` | `grid-cols-1` |
| Header font | `text-[10px]` | `text-[9px]` |
| Body font | `text-[11px]` | `text-[10px]` |
| Icon size | `h-3.5 w-3.5` | `h-3 w-3` |
| Summary label | "AI Intelligence Summary" | "Summary" |
| Padding | `py-3 px-4` | `py-2 px-3` |

---

## 9c. IOCSearchPopup Component

File: `ui/src/components/IOCSearchPopup.tsx`

Modal overlay triggered from IntelCard "Hunt" action or anywhere an IOC quick-search is needed.

**Props:** `keyword: string`, `onClose: () => void`

### Behavior

| Feature | Detail |
|---------|--------|
| Auto-search on mount | Immediately fires `api.liveLookup(keyword)` |
| Auto-select input | `inputRef.current.select()` after 100ms |
| Close on ESC | `window.addEventListener('keydown', ...)` |
| Close on backdrop click | Click detection on backdrop ref |
| Full search link | `/search?q={encodeURIComponent(query)}` |

### Rendering Flow

1. Modal overlay with search bar (pre-filled with keyword)
2. Live lookup fires immediately
3. Loading state with spinner
4. Results display:
   - Meta row: query, detected type, result count, source count
   - AI Summary block
   - AI Analysis: key findings list + fix/remediation
   - Results list: title, source, type, severity badge, risk score, description
   - Errors list (if any)
5. Footer: ESC hint + "Open in full search" permalink

---

## 10. Caching Strategy

| Endpoint | Cache TTL |
|----------|-----------|
| `POST /search` | No cache (real-time) |
| `GET /search/stats` | 60 seconds |
| `POST /search/live-lookup` | 600 seconds (10 min) |

---

## 11. Constants & Thresholds Reference

### IOC Type Colors (Frontend)

10 types with unique icons and colors:

| Type | Icon |
|------|------|
| `cve` | ShieldAlert |
| `ip` | Globe |
| `domain` | Globe |
| `url` | Link |
| `hash_md5` | Hash |
| `hash_sha1` | Hash |
| `hash_sha256` | Hash |
| `email` | Mail |
| `file` | File |
| `other` | HelpCircle |

### Sort Fields

7 sort options: risk, published, ingested, severity, confidence, reliability, title

### Debounce

Auto-search debounce: **400ms**

### URL Parameters

| Param | Purpose |
|-------|---------|
| `q` | Pre-fill search query |
| `hunt=1` | Auto-trigger live lookup |

### Example Queries (Empty State)

- `CVE-2024-3094`
- `8.8.8.8`
- `evil.com`
- Hash examples
- Feature highlights

### Severity Colors

| Severity | Hex |
|----------|-----|
| `critical` | `#ef4444` |
| `high` | `#f97316` |
| `medium` | `#eab308` |
| `low` | `#22c55e` |
| `info` | `#3b82f6` |

---

## 12. IOC Search UI Layout

Layout of `search/page.tsx` (~1200 lines):

1. **Header** — Title + quick stats (total items, avg risk, KEVs)
2. **Search Bar** — Input + chart toggle button + Search button
3. **Filter Pills** — Type, Severity, Feed type toggle pills
4. **Charts** (collapsible):
   - Type Distribution donut
   - Source Distribution horizontal bar
5. **Results Table** — Columns: Title/IOC, Type, Risk, Published, Ingested, Severity, Confidence, Source, Actions (Enrich/Copy/Detail)
6. **Pagination**
7. **Live Internet Lookup Results** (when triggered):
   - Sources queried badges
   - Errors (if any)
   - AI Structured Analysis via `StructuredIntelCards`
   - Result cards with severity badges, metadata, confidence bars
8. **Live Loading State** — Progress indicator
9. **Empty State** — Example queries and feature highlights
10. **Live Result Detail Panel** — Slide-over with full result details

---

## 13. Future Enhancements

- Saved searches with alerting
- Bulk IOC search (paste list)
- Search history with recent queries
- YARA rule search integration
- Sigma rule search integration
- Enrichment comparison across sources
- IOC reputation timeline
- API-based search for automation
